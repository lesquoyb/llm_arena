"""Bounded live progress reads: no conversations or replay bodies are loaded."""
import re
import time
from arena.roster import effective, snapshot


def status(store, identifier, job=None):
    root=store.run_path(identifier)
    metadata=store.json(root/'experiment.json',{})
    config=effective(root,metadata.get('config',{})) if metadata.get('config') else {}
    roster=snapshot(root) or {}
    withdrawn=set(roster.get('withdrawn',[]))
    models=[model['id'] for model in config.get('models',[]) if model['id'] not in withdrawn]
    states=store.states(root,('model','replicate','generation','condition','status','submission','validity','in_flight','reserved','current_tool','wall_seconds','calls'))
    states={sid:state for sid,state in states.items() if state['model'] not in withdrawn}
    running=bool(job and job['status'] in {'running','stopping'})
    operation=store.json(root/'activity.json',{}) if running else {}
    if operation.get('started_at',0)<(job or {}).get('started_at',0):operation={}
    busy=operation.get('kind') not in {None,'idle','starting'}
    generation=max((state.get('generation',0) for state in states.values()),default=0)
    # A coordinator may still evaluate the preceding round while later branch
    # checkpoints already exist. Prefer its explicit work item in that case.
    if busy:
        if 'generation' in operation:generation=operation['generation']
        elif operation.get('participants'):
            match=re.search(r'-g(\d+)-(?:control|feedback)$',operation['participants'][0])
            generation=int(match[1]) if match else 0
    current={sid:state for sid,state in states.items() if state.get('generation',0)==generation}
    multiplier=len(config.get('improvement_conditions',['control','feedback'])) if generation else 1
    per_model=config.get('replicates',1)*multiplier
    expected=len(models)*per_model
    ready=sum(bool(state.get('submission')) for state in current.values())
    assessed=sum(bool(state.get('submission')) and state.get('validity') in {'valid','invalid'} for state in current.values())
    ready_models=sum(sum(bool(state.get('submission')) for state in current.values() if state['model']==model)>=per_model for model in models)
    activity=[]
    if running:
        for sid,state in states.items():
            if state.get('in_flight'):
                activity.append({'session':sid,'model':state['model'],'kind':'model_request'})
            elif state.get('status')=='running' and state.get('reserved'):
                activity.append({'session':sid,'model':state['model'],'kind':'tool',**(state.get('current_tool') or {})})
    errors=sum(state.get('status') in {'provider_unavailable','generation_failed','no_submission','needs_reconciliation'} and not state.get('submission') for state in current.values())
    tournament=root/('tournament' if generation==0 else f'g{generation}-tournament')
    report=store.json(tournament/'report.json',{})
    finished=report.get('completed',0)+report.get('failed',0)
    seeds=config.get('seeds',[]) if generation==0 else config.get('final_seeds',[])
    possible=expected*(expected-1)*len(seeds)+(expected*len(seeds) if config.get('include_mirrors') else 0)
    last_event=None
    database=root/'journal.sqlite'
    if database.exists():
        import sqlite3,json
        from contextlib import closing
        with closing(sqlite3.connect(database.as_uri()+'?mode=ro',uri=True,timeout=2)) as db:
            if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='events'").fetchone():
                row=db.execute('SELECT kind,payload FROM events ORDER BY id DESC LIMIT 1').fetchone()
                if row:
                    reference=json.loads(row[1]);last_event={'kind':row[0],'at':reference.get('at')}
    # Provider durations come from their own saved request intent, not process age.
    if activity and database.exists():
        with closing(sqlite3.connect(database.as_uri()+'?mode=ro',uri=True,timeout=2)) as db:
            for item in activity:
                row=db.execute("SELECT payload FROM events WHERE session=? AND kind=? ORDER BY id DESC LIMIT 1",
                               (item['session'],'model_intent' if item['kind']=='model_request' else 'tool_reserved')).fetchone()
                if row:item['started_at']=json.loads(row[0]).get('at')
                live=root/'sessions'/item['session']/'live-response.json'
                if item['kind']=='model_request' and live.is_file():
                    stamp=live.stat().st_mtime
                    if stamp>=(item.get('started_at') or 0):item['stream_updated_at']=stamp
    activity=[item for item in activity if item.get('started_at') is not None and item['started_at']>=(job or {}).get('started_at',0)]
    return {'labels':{sid:{'model':state['model'],'round':state.get('generation',0)+1,'condition':state.get('condition','initial'),'replicate':state.get('replicate',0)} for sid,state in states.items()}, 'running':running,'job_status':(job or {}).get('status'),'job_note':(job or {}).get('note'),
            'round':generation+1,'rounds':config.get('generations',1),'participants':len(models),
            'withdrawn':len(withdrawn),'ready_participants':ready_models,'strategies_ready':ready,
            'strategies_expected':expected,'strategies_validated':assessed,'failed_preparations':errors,
            'tournament_completed':report.get('completed',0),'tournament_failed':report.get('failed',0),
            'tournament_total':max(finished+report.get('pending',0),possible),
            'operation':operation if running else {},'active':activity,'last_event':last_event,'observed_at':time.time()}
