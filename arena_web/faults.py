"""Observed authoring failures, reconstructed from immutable tool receipts."""
import json
import copy
import sqlite3
import hashlib
from contextlib import closing
from arena.core import ArenaError, digest
from .performance import measure
from arena.tool_schemas import TOOLS
from .data import safe_path


@measure('faults')
def report(store, identifier):
    root=store.run_path(identifier)
    states=store.states(root,('model','generation','condition','manual_frozen'))
    database=root/'journal.sqlite'
    if not database.exists():return {'sessions':[],'incidents':[]}
    with closing(sqlite3.connect(database.as_uri()+'?mode=ro',uri=True)) as db:
        latest=db.execute("SELECT coalesce(max(id),0) FROM events WHERE kind IN ('tool_reserved','tool_result','provider_failure','malformed_provider_response','conversation_restarted')").fetchone()[0]
    signature=digest({'event':latest,'states':{sid:{key:value for key,value in row.items() if key!='messages'} for sid,row in states.items()}})
    revision=digest({'authoring':signature,'fights':store.revision(root,include_events=False,include_reports=False)})
    with store.lock:
        cached=getattr(store,'_fault_cache',{}).get(identifier)
    if cached and cached[0]==revision:return copy.deepcopy(cached[1])
    rows,incidents=authoring(store,root,states,signature)
    from .fights import side_metrics
    cutoffs={sid:state.get('attempt_started_at',0) for sid,state in store.states(root,('attempt_started_at',)).items()}
    for (sid,kind),(errors,limits) in side_metrics(store,root,cutoffs).items():
        if sid not in rows:continue
        field='preparation_runtime_errors' if kind=='training' else 'progression_runtime_errors' if kind=='progression' else 'runtime_errors'
        rows[sid][field]+=errors
        rows[sid]['operation_limit_hits']+=limits
    for row in rows.values():
        row['tool_error_rate']=row['tool_errors']/row['tool_calls'] if row['tool_calls'] else None
        row['compile_failure_rate']=row['failed_analyses']/row['completed_analyses'] if row['completed_analyses'] else None
    result={'sessions':list(rows.values()),'incidents_total':len(incidents),'incidents':[{**row,'message':row['message'][:2000]} for row in incidents[-200:]]}
    with store.lock:
        if not hasattr(store,'_fault_cache'):store._fault_cache={}
        store._fault_cache[identifier]=(revision,copy.deepcopy(result))
    return result


@measure('authoring_faults')
def authoring(store,root,states,signature):
    with store.lock:cached=getattr(store,'_authoring_faults',{}).get(str(root))
    if cached and cached[0]==signature:return copy.deepcopy(cached[1])
    names={tool['name'] for tool in TOOLS}
    rows={sid:{'session':sid,'model':state['model'],'round':state.get('generation',0)+1,
               'condition':state.get('condition','initial'),'manual_frozen':bool(state.get('manual_frozen')),
               **{key:0 for key in ('tool_calls','tool_errors','unknown_tools','invalid_arguments','other_tool_errors',
                                   'analyses','completed_analyses','analysis_infrastructure_failures','failed_analyses','compiler_errors','invalid_teams','provider_failures','malformed_responses','runtime_errors','preparation_runtime_errors','progression_runtime_errors','operation_limit_hits')}}
          for sid,state in states.items()}
    incidents=[];pending={}
    path=root/'journal.sqlite'
    with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)) as db:
        events=db.execute("WITH restarts AS (SELECT session,max(id) AS cutoff FROM events WHERE kind='conversation_restarted' GROUP BY session) SELECT e.id,e.session,e.kind,e.payload FROM events e LEFT JOIN restarts r ON r.session=e.session WHERE e.id > coalesce(r.cutoff,0) AND e.kind IN ('tool_reserved','tool_result','provider_failure','malformed_provider_response') ORDER BY e.id").fetchall()
    decoded=[(event,sid,kind,json.loads(reference)) for event,sid,kind,reference in events if sid in rows]
    projected={}
    for projection,kinds in (('tool_name',{'tool_reserved'}),('fault',{'tool_result','provider_failure','malformed_provider_response'})):
        refs=[(reference['sha256'],lambda reference=reference:safe_path(root,reference['artifact'])) for _,_,kind,reference in decoded if kind in kinds]
        projected[projection]=store.receipts.many(projection,refs,project_tool_name if projection=='tool_name' else project_fault)
    for event,sid,kind,reference in decoded:
        value=projected['tool_name' if kind=='tool_reserved' else 'fault'][reference['sha256']];row=rows[sid]
        if kind=='tool_reserved':pending[sid]=value;continue
        incident={'event':event,'session':sid,'model':row['model'],'round':row['round'],'condition':row['condition'],'at':reference.get('at')}
        if kind=='malformed_provider_response':
            row['malformed_responses']+=1
            incidents.append({**incident,'category':'malformed_response','tool':'','message':'Unreadable provider response: '+str(value.get('error_type','unknown'))});continue
        if kind=='provider_failure':
            row['provider_failures']+=1
            incidents.append({**incident,'category':'provider_failure','tool':'','message':value.get('error','Provider failure')});continue
        call=pending.pop(sid,{})
        name=call.get('name','unknown');row['tool_calls']+=1
        error=value.get('error')
        if error:
            row['tool_errors']+=1
            if name not in names:category='unknown_tools'
            elif any(word in str(error).lower() for word in ('argument','parameter','invalid offset','invalid limit','invalid page','unexpected field','unknown field')):category='invalid_arguments'
            else:category='other_tool_errors'
            row[category]+=1;incidents.append({**incident,'category':category,'tool':name,'message':str(error)})
        if name=='analyze' and not error:
            row['analyses']+=1
            from arena.compiler_diagnostics import compilation_rows
            diagnostics=[entry for entry in value.get('diagnostic_messages',compilation_rows(value)) if entry.get('severity')=='error']
            if value.get('status') in {'valid','invalid'} or diagnostics:
                row['completed_analyses']+=1
            else:row['analysis_infrastructure_failures']+=1
            if value.get('status')=='invalid' or diagnostics:
                row['failed_analyses']+=1;row['compiler_errors']+=len(diagnostics)
                incidents.append({**incident,'category':'compilation','tool':name,'message':'\n'.join(str(entry.get('message','')) for entry in diagnostics) or 'Compilation failed; inspect the analysis receipt'})
        if name=='validate_team' and value.get('valid') is False:
            row['invalid_teams']+=1
            incidents.append({**incident,'category':'team_validation','tool':name,'message':'\n'.join(map(str,value.get('errors',[])))})
    result=(rows,incidents)
    saved=copy.deepcopy(result)
    with store.lock:
        if not hasattr(store,'_authoring_faults'):store._authoring_faults={}
        store._authoring_faults[str(root)]=(signature,saved)
    return result


def project_tool_name(value):
    return {'name':value.get('name','unknown')}


def project_fault(value):
    from arena.compiler_diagnostics import compilation_rows
    return {**{field:value[field] for field in ('error','errors','valid','status','error_type') if field in value},
            'diagnostic_messages':value.get('diagnostic_messages',compilation_rows(value))}
