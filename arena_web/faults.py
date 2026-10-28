"""Observed authoring failures, reconstructed from immutable tool receipts."""
import json
import copy
import sqlite3
from contextlib import closing
from arena.core import ArenaError, file_hash, read_json
from arena.tool_schemas import TOOLS
from .data import safe_path


def report(store, identifier):
    root=store.run_path(identifier)
    revision=store.revision(root)
    with store.lock:
        cached=getattr(store,'_fault_cache',{}).get(identifier)
    if cached and cached[0]==revision:return copy.deepcopy(cached[1])
    states=store.states(root,('model','generation','condition','manual_frozen'))
    names={tool['name'] for tool in TOOLS}
    rows={sid:{'session':sid,'model':state['model'],'round':state.get('generation',0)+1,
               'condition':state.get('condition','initial'),'manual_frozen':bool(state.get('manual_frozen')),
               **{key:0 for key in ('tool_calls','tool_errors','unknown_tools','invalid_arguments','other_tool_errors',
                                   'analyses','failed_analyses','compiler_errors','invalid_teams','provider_failures','malformed_responses','runtime_errors','preparation_runtime_errors','progression_runtime_errors','operation_limit_hits')}}
          for sid,state in states.items()}
    incidents=[];pending={}
    path=root/'journal.sqlite'
    if not path.exists():return {'sessions':list(rows.values()),'incidents':[]}
    with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)) as db:
        events=db.execute("SELECT id,session,kind,payload FROM events WHERE kind IN ('tool_reserved','tool_result','provider_failure','malformed_provider_response') ORDER BY id").fetchall()
    for event,sid,kind,reference in events:
        if sid not in rows:continue
        reference=json.loads(reference);path=safe_path(root,reference['artifact'])
        if file_hash(path)!=reference['sha256']:raise ArenaError('Tool receipt changed')
        value=read_json(path);row=rows[sid]
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
            if value.get('status')=='invalid' or diagnostics:
                row['failed_analyses']+=1;row['compiler_errors']+=len(diagnostics)
                incidents.append({**incident,'category':'compilation','tool':name,'message':'\n'.join(str(entry.get('message','')) for entry in diagnostics) or 'Compilation failed; inspect the analysis receipt'})
        if name=='validate_team' and value.get('valid') is False:
            row['invalid_teams']+=1
            incidents.append({**incident,'category':'team_validation','tool':name,'message':'\n'.join(map(str,value.get('errors',[])))})
    for fight in store.matches(identifier)['matches']:
        for side,sid in enumerate(fight['sides']):
            if sid not in rows or (fight['kind'] in {'evaluation','progression'} and fight.get('candidate')!=sid):continue
            metrics=fight['result'].get('team_metrics',{}).get(str(side),{})
            field='preparation_runtime_errors' if fight['kind']=='training' else 'progression_runtime_errors' if fight['kind']=='progression' else 'runtime_errors'
            rows[sid][field]+=metrics.get('errors',0)
            rows[sid]['operation_limit_hits']+=metrics.get('operation_limit_hits',0)
    for row in rows.values():
        row['tool_error_rate']=row['tool_errors']/row['tool_calls'] if row['tool_calls'] else None
        row['compile_failure_rate']=row['failed_analyses']/row['analyses'] if row['analyses'] else None
    result={'sessions':list(rows.values()),'incidents_total':len(incidents),'incidents':[{**row,'message':row['message'][:2000]} for row in incidents[-200:]]}
    with store.lock:
        if not hasattr(store,'_fault_cache'):store._fault_cache={}
        store._fault_cache[identifier]=(revision,copy.deepcopy(result))
    return result
