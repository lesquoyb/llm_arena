"""Retry frozen engine fixtures without running any model conversations."""
from pathlib import Path
from contextlib import nullcontext
import time
from .core import ArenaError, read_json, write_json, submission, make_scenario, digest
from .engine import Engine
from .experiment import Journal, experiment_lock
from .execution_control import _journal
from .recovery import engine_compatible
from .roster import effective, snapshot


def run(directory, *, engine=None, journal=None, cooperative=False):
    out=Path(directory).resolve();metadata=read_json(out/'experiment.json')
    if 'config' not in metadata:raise ArenaError('Fight recovery requires an original model competition')
    engine=engine or Engine()
    if not engine_compatible(metadata['engine'],engine.identity):raise ArenaError('Restore the original game engine before retrying fights')
    engine.allow_updated_runner=True
    owns_journal=journal is None
    with experiment_lock(out) if owns_journal else nullcontext():
        journal=journal or Journal(out);token=_journal.set(journal)
        try:
            config=effective(out,metadata['config']);withdrawn=set((snapshot(out) or {}).get('withdrawn',[]))
            from .execution_control import poll
            poll(out,config.get('parallel_fights',1))
            initial_retry_epoch=getattr(journal,'_fight_retry_epoch',0)
            done=getattr(journal,'_manual_recovery_done',set())
            pending_jobs=getattr(journal,'_manual_pending_jobs',{})
            failures=getattr(journal,'_manual_failures',{})
            journal._manual_recovery_done=done;journal._manual_pending_jobs=pending_jobs;journal._manual_failures=failures
            states=journal.metadata();anchor=next(iter(states),None)
            if anchor:journal.save(anchor,journal.state(anchor),'engine_only_recovery_started',{'no_model_requests':True,'engine':engine.identity})
            from .tournament import run_tournament
            tournaments={}
            for root in [out/'tournament',*sorted(out.glob('g*-tournament'))]:
                if not (root/'experiment.json').exists():continue
                if cooperative and str(root) in done:
                    tournaments[root.name]=read_json(root/'report.json');continue
                frozen=read_json(root/'experiment.json');manifest=frozen['manifest']
                manifest={**manifest,'strategies':[{**source,'path':str(root/'submissions'/source['id'])} for source in manifest['strategies']]}
                caches=getattr(journal,'_verified_tournament_records',{})
                journal._verified_tournament_records=caches
                tournaments[root.name]=run_tournament(engine,manifest,root,resume=True,parallel_fights=config.get('parallel_fights',1),verified_cache=caches.setdefault(str(root),{}))
                value=tournaments[root.name]
                if cooperative and (value.get('deferred') or value.get('pending') or value.get('retry_pending')):return {'deferred':True}
                done.add(str(root))
            jobs=[]
            for root in sorted((out/'evaluations').glob('g*-*')):
                for path in sorted((root/'records').glob('*.json')):
                    if cooperative and str(path) in done:continue
                    from .activity import provider_work_ready
                    if cooperative and provider_work_ready():return {'deferred':True}
                    if str(path) in pending_jobs:continue
                    record=read_json(path)
                    if record['result'].get('status')=='completed':
                        done.add(str(path));continue
                    sid=record['session']
                    if states.get(sid,{}).get('model') in withdrawn:continue
                    work=(out/record['artifact_dir']).resolve()
                    if not work.is_relative_to(out):raise ArenaError('Invalid stored fight path')
                    provenance=read_json(work/'provenance.json');infos=provenance['submissions']
                    for side,info in enumerate(infos,1):
                        if submission(work/'strategies'/str(side),info['entrypoint'])!=info:raise ArenaError('Frozen fight source changed')
                    scenario=make_scenario(config['scenario'],[info['entrypoint'] for info in infos],record['seed'],[info.get('team') for info in infos])
                    if read_json(work/'scenario.json')!=scenario or provenance['scenario_sha256']!=digest(scenario):raise ArenaError('Frozen fight scenario changed')
                    from .preparation import Preparation
                    target=Preparation._attempt(work)
                    pending_jobs[str(path)]={'record':record,'record_path':path,'infos':infos,'source':work,'work':target,
                                 'seed':record['seed'],'participants':[sid,record['opponent']]}
            jobs=list(pending_jobs.values())
            def execute(job):
                from .fight_phases import callback
                def update(name):job.update(phase=name,phase_started_at=time.time())
                token=callback.set(update)
                try:return engine.fight([job['source']/'strategies'/str(side) for side in (1,2)],job['infos'],config['scenario'],job['seed'],job['work'])
                finally:callback.reset(token)
            def save(job,result):
                record={**job['record'],'result':result,'artifact_dir':job['work'].relative_to(out).as_posix(),
                        'retry_attempt':job.get('_retry',0),'retry_pending':result.get('status') in {'timeout','engine_error'} and job.get('_retry',0)<2}
                write_json(job['record_path'],record)
                key=str(job['record_path'])
                if result.get('status')=='completed' or job.get('_retry',0)>=2:
                    done.add(key);pending_jobs.pop(key,None);failures[key]=result.get('status')!='completed'
                else:
                    from .preparation import Preparation
                    pending_jobs[key]={**job,'work':Preparation._attempt(job.get('_attempt_base',job['work'])),'_retry':job.get('_retry',0)+1}
                sid=record['session']
                if sid in states:journal.save(sid,journal.state(sid),'engine_fixture_retried',record)
            def retry(job):
                from .preparation import Preparation
                base=job.get('_attempt_base',job['work'])
                return {**job,'work':Preparation._attempt(base),'_attempt_base':base}
            from .fight_pool import run as run_fights
            run_fights(jobs,execute,save,limit=config.get('parallel_fights',1),out=out,kind='reference_fight',retry=retry)
            if cooperative:
                if pending_jobs or getattr(journal,'_fight_retry_epoch',0)!=initial_retry_epoch:return {'deferred':True}
                receipt={'remaining_failed':sum(value.get('failed',0) for value in tournaments.values())+sum(failures.values()),'no_model_requests':True,'deferred':False}
                write_json(out/'fight-retry-progress.json',receipt)
                if anchor:journal.save(anchor,journal.state(anchor),'engine_only_recovery_finished',receipt)
                return receipt
            remaining=sum(report.get('failed',0) for report in tournaments.values())
            panels={}
            for root in sorted((out/'evaluations').glob('g*-*')):
                records={path.stem:read_json(path) for path in sorted((root/'records').glob('*.json'))}
                if records:
                    write_json(root/'results.json',records);panels[root.name]=records
                    remaining+=sum(record['result'].get('status')!='completed' for record in records.values())
            summary=read_json(out/'report.json') if (out/'report.json').exists() else {}
            if 'tournament' in tournaments:summary['tournament']=tournaments['tournament']
            all_states=journal.states()
            if any(state.get('generation',0)>0 for state in all_states.values()):
                from .analysis import analyze_evolution
                sources=[{'id':sid,'model':state['model'],'replicate':state.get('replicate',0),
                          'generation':state.get('generation',0),'condition':state.get('condition','initial'),
                          'path':out/'sessions'/sid/'submission','submission':state['submission']}
                         for sid,state in all_states.items() if state.get('submission') and state['model'] not in withdrawn]
                later=[value for key,value in tournaments.items() if key!='tournament']
                contemporary=dict(later[-1]) if later else {}
                for key in ('completed','failed','pending'):contemporary[key]=sum(value.get(key,0) for value in later)
                evolved={key:record for name,records in panels.items() if name!='g0-panel' and name.endswith('-panel') for key,record in records.items()}
                evolution=analyze_evolution(config,out,all_states,[s for s in sources if not s['generation']],
                    [s for s in sources if s['generation']],panels.get('g0-panel',{}),evolved,contemporary)
                evolution['contemporaries']=contemporary;summary['evolution']=evolution;write_json(out/'evolution.json',evolution)
            blocked=[sid for sid,state in all_states.items() if state['model'] not in withdrawn and (not state.get('submission') or state.get('status')=='needs_reconciliation')]
            summary.update(waiting_for_recovery=bool(blocked),incomplete=bool(blocked or remaining or summary.get('assessment_failures') or summary.get('evolution',{}).get('incomplete')))
            if remaining and getattr(journal,'_fight_retry_epoch',0)!=initial_retry_epoch:
                from uuid import uuid4
                identifier=uuid4().hex
                write_json(out/'fight-retry-requests'/(identifier+'.json'),{'id':identifier,'requested_at':time.time(),'reason':'Manual retry requested during the previous recovery batch'})
            receipt={'remaining_failed':remaining,'no_model_requests':True,'finished_at':time.time()}
            summary['fight_recovery']=receipt;write_json(out/'report.json',summary);write_json(out/'fight-retry-report.json',receipt)
            if anchor:journal.save(anchor,journal.state(anchor),'engine_only_recovery_finished',receipt)
            return receipt
        finally:
            _journal.reset(token)
            if owns_journal:journal.db.close()
