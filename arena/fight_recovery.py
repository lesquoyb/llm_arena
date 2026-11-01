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


def run(directory, *, engine=None, journal=None, cooperative=False, include_ready=False):
    out=Path(directory).resolve();metadata=read_json(out/'experiment.json')
    if 'config' not in metadata:raise ArenaError('Fight recovery requires an original model competition')
    engine=engine or Engine()
    if not engine_compatible(metadata['engine'],engine.identity):raise ArenaError('Restore the original game engine before retrying fights')
    engine.allow_updated_runner=True
    owns_journal=journal is None
    from .round_runtime import RoundClock
    with experiment_lock(out) if owns_journal else nullcontext(), RoundClock(out) if owns_journal else nullcontext():
        journal=journal or Journal(out);token=_journal.set(journal)
        validator=None
        from .activity import _provider_yielder, provider_work_ready
        recovery_yielder=_provider_yielder.set(lambda:not include_ready and any((out/'recovery-commands').glob('*.json'))) if owns_journal else None
        try:
            if owns_journal and provider_work_ready():return {'deferred':True,'no_model_requests':True,'remaining_failed':0}
            config=effective(out,metadata['config']);roster=snapshot(out) or {}
            config['_scenario_changes']=roster.get('scenario_changes',[])
            from .scenario_rules import generation_of, scenario_for
            withdrawn=set(roster.get('withdrawn',[]))
            parallel_fights=roster.get('parallel_fights',config.get('_parallel_fights',config.get('parallel_fights',1)))
            from .execution_control import poll
            poll(out,parallel_fights)
            include_ready=include_ready or getattr(journal,'_include_ready_fights',False)
            initial_retry_epoch=getattr(journal,'_fight_retry_epoch',0)
            done=getattr(journal,'_manual_recovery_done',set())
            pending_jobs=getattr(journal,'_manual_pending_jobs',{})
            failures=getattr(journal,'_manual_failures',{})
            journal._manual_recovery_done=done;journal._manual_pending_jobs=pending_jobs;journal._manual_failures=failures
            states=journal.metadata();anchor=next(iter(states),None)
            if owns_journal and include_ready:
                from .submission_validation import SubmissionValidator
                validator=SubmissionValidator(out,engine,[sid for sid,state in states.items() if state.get('submission')])
                validator.thread.start()
            if anchor:journal.record(anchor,'engine_only_recovery_started',{'no_model_requests':True,'engine':engine.identity})
            if include_ready:
                from .greedy import evaluate
                config['_parallel_fights']=parallel_fights
                for generation in sorted({state.get('generation',0) for state in states.values() if state.get('submission')},reverse=True):
                    value=evaluate(engine,config,out,journal,generation,final=True)
                    if value and (value.get('deferred') or value.get('pending') or value.get('retry_pending')):
                        return {'deferred':True,'no_model_requests':True,'remaining_failed':value.get('failed',0)}
            from .tournament import run_tournament
            tournaments={}
            for root in [out/'tournament',*sorted(out.glob('g*-tournament'))]:
                if not (root/'experiment.json').exists():continue
                if cooperative and str(root) in done:
                    tournaments[root.name]=read_json(root/'report.json');continue
                frozen=read_json(root/'experiment.json');manifest=frozen['manifest']
                manifest={**manifest,'strategies':[{**source,'path':str(root/'submissions'/source['id'])} for source in manifest['strategies']]}
                from .run_memory import shared
                caches=shared(out,'verified_tournament_records')
                tournaments[root.name]=run_tournament(engine,manifest,root,resume=True,parallel_fights=parallel_fights,verified_cache=caches.setdefault(str(root),{}))
                value=tournaments[root.name]
                if value.get('deferred') or (cooperative and (value.get('pending') or value.get('retry_pending'))):return {'deferred':True,'no_model_requests':True,'remaining_failed':0}
                done.add(str(root))
            jobs=[]
            from .fight_store import FightStore, attempt_path, scratch, stage_records, stored_sources
            for root in sorted((out/'evaluations').glob('g*-*')):
                store,entries=stage_records(root)
                stage=root.relative_to(out).as_posix()
                for key,(location,record) in entries.items():
                    path=root/'records'/(key+'.json')
                    if cooperative and str(path) in done:continue
                    from .activity import provider_work_ready
                    if provider_work_ready():return {'deferred':True,'no_model_requests':True,'remaining_failed':0}
                    if str(path) in pending_jobs:continue
                    if record['result'].get('status')=='completed':
                        done.add(str(path));continue
                    sid=record['session']
                    if states.get(sid,{}).get('model') in withdrawn:continue
                    work=(out/record['artifact_dir']).resolve()
                    if not work.is_relative_to(out):raise ArenaError('Invalid stored fight path')
                    inner=record['artifact_dir'][len(stage)+1:] if record['artifact_dir'].startswith(stage+'/') else None
                    stored=store is not None and inner is not None and store.exists(inner+'/provenance.json')
                    provenance=store.get_json(inner+'/provenance.json') if stored else read_json(work/'provenance.json');infos=provenance['submissions']
                    for side,info in enumerate(infos,1):
                        if stored:
                            hashes,_=stored_sources(store,f'{inner}/strategies/{side}')
                            if hashes!=info['files']:raise ArenaError('Frozen fight source changed')
                        elif submission(work/'strategies'/str(side),info['entrypoint'])!=info:raise ArenaError('Frozen fight source changed')
                    stage_scenario=scenario_for(config,generation_of(root.name))
                    scenario=make_scenario(stage_scenario,[info['entrypoint'] for info in infos],record['seed'],[info.get('team') for info in infos])
                    saved=store.get_json(inner+'/scenario.json') if stored else read_json(work/'scenario.json')
                    if saved!=scenario or provenance['scenario_sha256']!=digest(scenario):raise ArenaError('Frozen fight scenario changed')
                    stage_store=store or FightStore.at(root,create=True)
                    pending_jobs[str(path)]={'record':record,'record_path':path,'legacy_record':None if isinstance(location,str) else location,
                                 'infos':infos,'source':work,'source_inner':inner if stored else None,'store':stage_store,'stage':root,'scenario':stage_scenario,
                                 'work':attempt_path(stage_store,root,work),
                                 'generation':states.get(sid,{}).get('generation',int(root.name.split('-')[0][1:])),
                                 'seed':record['seed'],'participants':[sid,record['opponent']]}
            jobs=list(pending_jobs.values())
            def execute(job):
                from .fight_phases import callback
                def update(name):job.update(phase=name,phase_started_at=time.time())
                token=callback.set(update)
                try:
                    with scratch() as folder, scratch() as sources:
                        if job['source_inner']:
                            # Stored fights: materialize the executed sources again.
                            for side in (1,2):job['store'].materialize(f"{job['source_inner']}/strategies/{side}",sources/str(side))
                            paths=[sources/str(side) for side in (1,2)]
                        else:paths=[job['source']/'strategies'/str(side) for side in (1,2)]
                        result=engine.fight(paths,job['infos'],job['scenario'],job['seed'],folder)
                        job['store'].ingest(job['work'].relative_to(job['stage']).as_posix(),folder)
                        return result
                finally:callback.reset(token)
            def save(job,result):
                record={**job['record'],'result':result,'artifact_dir':job['work'].relative_to(out).as_posix(),
                        'retry_attempt':job.get('_retry',0),'retry_pending':result.get('status') in {'timeout','engine_error'} and job.get('_retry',0)<2}
                job['store'].put_json('records/'+job['record_path'].name,record)
                # The stored record supersedes the legacy file, as an overwrite did.
                if job.get('legacy_record'):Path(job['legacy_record']).unlink(missing_ok=True)
                key=str(job['record_path'])
                if result.get('status')=='completed' or job.get('_retry',0)>=2:
                    done.add(key);pending_jobs.pop(key,None);failures[key]=result.get('status')!='completed'
                else:
                    pending_jobs[key]={**job,'work':attempt_path(job['store'],job['stage'],job.get('_attempt_base',job['work'])),'_retry':job.get('_retry',0)+1,'legacy_record':None}
                sid=record['session']
                if sid in states:journal.record(sid,'engine_fixture_retried',record)
            def retry(job):
                base=job.get('_attempt_base',job['work'])
                return {**job,'work':attempt_path(job['store'],job['stage'],base),'_attempt_base':base}
            from .fight_pool import run as run_fights
            for generation in sorted({job['generation'] for job in jobs}):
                run_fights([job for job in jobs if job['generation']==generation],execute,save,
                           limit=parallel_fights,out=out,kind='reference_fight',generation=generation,retry=retry)
                if provider_work_ready():break
            if provider_work_ready():return {'deferred':True,'no_model_requests':True,'remaining_failed':0}
            if cooperative:
                if pending_jobs or getattr(journal,'_fight_retry_epoch',0)!=initial_retry_epoch:return {'deferred':True}
                receipt={'remaining_failed':sum(value.get('failed',0) for value in tournaments.values())+sum(failures.values()),'no_model_requests':True,'deferred':False}
                write_json(out/'fight-retry-progress.json',receipt)
                if anchor:journal.record(anchor,'engine_only_recovery_finished',receipt)
                return receipt
            remaining=sum(report.get('failed',0) for report in tournaments.values())
            panels={}
            for root in sorted((out/'evaluations').glob('g*-*')):
                records={key:record for key,(location,record) in stage_records(root)[1].items()}
                if records:
                    write_json(root/'results.json',records);panels[root.name]=records
                    remaining+=sum(record['result'].get('status')!='completed' for record in records.values())
            summary=read_json(out/'report.json') if (out/'report.json').exists() else {}
            if 'tournament' in tournaments:summary['tournament']=tournaments['tournament']
            if validator:
                validator.close()
                if validator.error is not None:raise validator.error
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
            if anchor:journal.record(anchor,'engine_only_recovery_finished',receipt)
            return receipt
        finally:
            if validator and validator.thread.is_alive():validator.close(cancel=True)
            if recovery_yielder is not None:_provider_yielder.reset(recovery_yielder)
            from .fight_store import release
            release(out/'evaluations')
            _journal.reset(token)
            if owns_journal:journal.db.close()
