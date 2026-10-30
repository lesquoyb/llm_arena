"""Bounded live progress reads: no conversations or replay bodies are loaded."""
import time
from arena.roster import effective, snapshot
from arena.fight_throughput import rate


def planning_snapshot(store, path):
    stamp=(path.stat().st_mtime_ns,path.stat().st_size) if path.is_file() else None
    with store.lock:cached=getattr(store,'_activity_plans',{}).get(path)
    if cached and cached[0]==stamp:return cached[1]
    value=store.json(path,{})
    compact={'models':{source['id']:source.get('model',source['id']) for source in value.get('manifest',{}).get('strategies',[])},
             'sides':[match['sides'] for match in value.get('schedule',[])]}
    with store.lock:
        if not hasattr(store,'_activity_plans'):store._activity_plans={}
        store._activity_plans[path]=(stamp,compact)
        while len(store._activity_plans)>16:store._activity_plans.pop(next(iter(store._activity_plans)))
    return compact


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
    engine_operation=store.json(root/'engine-activity.json',{}) if running else {}
    if (engine_operation.get('kind') not in {None,'idle'} and
            engine_operation.get('started_at',0)>=(job or {}).get('started_at',0)):
        operation=engine_operation
    if operation.get('started_at',0)<(job or {}).get('started_at',0):operation={}
    busy=operation.get('kind') not in {None,'idle','starting'}
    generation=max((state.get('generation',0) for state in states.values()),default=0)
    # Competition progress follows saved sessions; historical engine work has
    # its own round and must not move the progress counters backwards.
    work_generation=operation.get('generation') if busy else None
    current={sid:state for sid,state in states.items() if state.get('generation',0)==generation}
    multiplier=len(config.get('improvement_conditions',['control','feedback'])) if generation else 1
    from arena.reference_strategies import repetitions
    config['_fixed_reference_repetitions']=metadata.get('fixed_reference_repetitions',config.get('replicates',1))
    per_model={model['id']:repetitions(config,model)*multiplier for model in config.get('models',[]) if model['id'] in models}
    expected=sum(per_model.values())
    ready=sum(bool(state.get('submission')) for state in current.values())
    assessed=sum(bool(state.get('submission')) and state.get('validity') in {'valid','invalid'} for state in current.values())
    valid=sum(bool(state.get('submission')) and state.get('validity')=='valid' for state in current.values())
    invalid=sum(bool(state.get('submission')) and state.get('validity')=='invalid' for state in current.values())
    breakdown=[]
    for model in config.get('models',[]):
        if model['id'] not in models:continue
        fixed=model.get('provider')=='mock' and model.get('profile')=='saved-strategy'
        breakdown.append({'model':model['id'],'fixed':fixed,'repetitions':repetitions(config,model),
                          'tracks':multiplier,'expected':per_model[model['id']],
                          'submitted':sum(bool(state.get('submission')) for state in current.values() if state['model']==model['id'])})
    ready_models=sum(sum(bool(state.get('submission')) for state in current.values() if state['model']==model)>=per_model[model] for model in models)
    activity=[]
    if running:
        for sid,state in states.items():
            if state.get('in_flight') and state.get('status')=='running':
                activity.append({'session':sid,'model':state['model'],'kind':'model_request'})
            elif state.get('status')=='running' and state.get('reserved'):
                activity.append({'session':sid,'model':state['model'],'kind':'tool',**(state.get('current_tool') or {})})
    errors=sum(state.get('status') in {'provider_unavailable','generation_failed','no_submission','needs_reconciliation'} and not state.get('submission') for state in states.values())
    tournament=root/('tournament' if generation==0 else f'g{generation}-tournament')
    report=store.json(tournament/'report.json',{})
    finished=report.get('completed',0)+report.get('failed',0)
    seeds=config.get('seeds',[]) if generation==0 else config.get('final_seeds',[])
    possible=expected*(expected-1)*len(seeds)+(expected*len(seeds) if config.get('include_mirrors') else 0)
    available=ready*(ready-1)*len(seeds)+(ready*len(seeds) if config.get('include_mirrors') else 0)
    planning=planning_snapshot(store,tournament/'experiment.json')
    planned_models=planning['models']
    planned_count=sum(not any(planned_models.get(side) in withdrawn for side in sides) for sides in planning['sides']) if withdrawn else len(planning['sides'])
    unrecorded=max(0,planned_count-finished-report.get('cancelled',0))
    unscheduled=max(0,available-planned_count)
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
                transport=store.json(root/'sessions'/item['session']/'request-status.json',{})
                if item['kind']=='model_request' and transport.get('updated_at',0)>=(item.get('started_at') or 0) and transport.get('phase') in {'completed','failed'}:
                    item['kind']='provider_receipt_waiting'
                    item['transport_phase']=transport['phase']
                live=root/'sessions'/item['session']/'live-response.json'
                if item['kind'] in {'model_request','provider_receipt_waiting'} and live.is_file():
                    progress_path=live.with_name('live-progress.json')
                    if progress_path.is_file():
                        progress=store.json(progress_path,{})
                        stamp=progress.get('progress_at')
                    else:stamp=live.stat().st_mtime
                    if stamp and stamp>=(item.get('started_at') or 0):item['stream_updated_at']=stamp
    activity=[item for item in activity if item.get('started_at') is not None and item['started_at']>=(job or {}).get('started_at',0)]
    profiles={model['id']:model for model in config.get('models',[])}
    for item in activity:
        if item['kind']=='model_request':
            item['inactivity_timeout_seconds']=profiles.get(item['model'],{}).get('inactivity_timeout_seconds',300)
            item['no_output_since']=item.get('stream_updated_at') or item.get('started_at')
    active_ids={item['session'] for item in activity}
    preparing_ids=set(operation.get('participants',[])) if running and operation.get('kind') in {
        'request_preparation','preparation_analysis','preparation_fight','validation'} else set()
    preparations=[]
    for sid,state in current.items():
        phase=('ready' if state.get('submission') else 'attention' if state.get('status') in
               {'provider_unavailable','generation_failed','no_submission','needs_reconciliation'}
               else 'active' if sid in active_ids or sid in preparing_ids else 'waiting')
        preparations.append({'session':sid,'model':state['model'],'phase':phase})
    waiting=[{'model':model,'count':max(0,per_model[model]-sum(state['model']==model for state in current.values()))} for model in models]
    waiting=[item for item in waiting if item['count']]
    return {'labels':{sid:{'model':state['model'],'round':state.get('generation',0)+1,'condition':state.get('condition','initial'),'replicate':state.get('replicate',0)} for sid,state in states.items()}, 'running':running,'job_status':(job or {}).get('status'),'job_note':(job or {}).get('note'),
            'requested_parallel_fights':store.json(root/'execution-control.json',{}).get('parallel_fights',roster.get('parallel_fights',config.get('parallel_fights',1))),
            'parallel_requests':roster.get('parallel_requests',config.get('parallel_requests',1)),'round':generation+1,'work_round':work_generation+1 if work_generation is not None else None,'rounds':config.get('generations',1),'participants':len(models),
            'withdrawn':len(withdrawn),'ready_participants':ready_models,'strategies_ready':ready,
            'strategies_expected':expected,'strategies_validated':assessed,'strategies_checked':assessed,
            'strategies_valid':valid,'strategies_invalid':invalid,'strategies_awaiting_check':ready-assessed,
            'throughput':rate(store.json(root/'fight-throughput.json',{})),
            'submission_breakdown':breakdown,'failed_preparations':errors,
            'tournament_completed':report.get('completed',0),'tournament_failed':report.get('failed',0),
            'tournament_total':max(finished+report.get('pending',0),possible),
            'tournament_scheduled_pending':unrecorded+report.get('failed',0),'tournament_pending_available':unrecorded+unscheduled+report.get('failed',0),'tournament_waiting_submissions':max(0,possible-available),
            'tournament_scheduled':planned_count,'tournament_unscheduled_available':unscheduled,
            'tournament_planned_submissions':sum(model not in withdrawn for model in planned_models.values()),
            'preparations':preparations,'waiting_preparations':waiting,'operation':operation if running else {},'active':activity,'last_event':last_event,'observed_at':time.time()}
