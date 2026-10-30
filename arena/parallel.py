"""Concurrent transports; the coordinator owns tools, checkpoints and SQLite."""
from collections import deque
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
import time
import threading
from urllib.parse import urlsplit
from .endpoints import is_loopback


class Requests:
    def __init__(self, limit, tasks=(), out=None):
        self.limit=limit
        self.out=out;self.endpoint_limits={};self.limits_checked=0
        self.pool=ThreadPoolExecutor(max_workers=limit,thread_name_prefix='arena-provider')
        self.pending={}
        self.deferred=set()
        self.local_owners={}
        self.models=dict(tasks)
        self.finished=set()

    def local_key(self, model):
        endpoint=model.get('endpoint','')
        if model.get('provider')!='mock' and is_loopback(endpoint):
            parsed=urlsplit(endpoint)
            return parsed.scheme,parsed.port or (443 if parsed.scheme=='https' else 80)
        return None

    @staticmethod
    def model_key(model):
        # Group repetitions and parameter variants for ordering and local model
        # residency. This key never imposes a remote per-model request limit.
        from .api_providers import DEFAULT_ENDPOINTS
        endpoint=(model.get('endpoint') or DEFAULT_ENDPOINTS.get(model.get('provider'),'')).rstrip('/')
        for suffix in ('/chat/completions','/responses'):
            if endpoint.endswith(suffix):endpoint=endpoint[:-len(suffix)];break
        return (model.get('provider'),endpoint,model.get('model',model['id']))

    def can_start(self, sid, model):
        from .provider_limits import endpoint, configured, limit
        if self.out is not None and time.monotonic()-self.limits_checked>=.5:
            self.endpoint_limits=configured(self.out);self.limits_checked=time.monotonic()
        cap=limit(model,self.endpoint_limits)
        busy=sum(endpoint(context['model'])==endpoint(model) and not context['future'].done() for context in self.pending.values())
        if cap is not None and busy>=cap:return False
        key=self.local_key(model)
        return len(self.pending)<self.limit and (key is None or self.local_owners.get(key,self.model_key(model))==self.model_key(model))

    def release(self, sid):
        self.finished.add(sid)
        self.local_owners={key:owner for key,owner in self.local_owners.items() if any(
            other not in self.finished and self.local_key(model)==key and self.model_key(model)==owner
            for other,model in self.models.items())}

    def other_reservations(self, sid, journal):
        from .usage import amount
        return sum(amount((journal.state(other) or {}).get('money_reserved','0')) for other in self.pending if other!=sid)

    def submit(self, sid, context):
        key=self.local_key(context['model'])
        self.models[sid]=context['model']
        if key is not None:self.local_owners[key]=self.model_key(context['model'])
        context['submitted_at']=time.monotonic()
        from .core import write_json
        status_path=context.get('request_status_path')
        receipt={'call':context.get('request_call'),'started_at':time.time()}
        def publish(phase):
            if status_path is not None:
                try:write_json(status_path,{**receipt,'phase':phase,'updated_at':time.time()})
                except OSError:pass
        publish('waiting')
        print(f'[provider] {sid} request={receipt["call"]} dispatched; inactivity_timeout={context["model"].get("inactivity_timeout_seconds",300)}s',flush=True)
        from .provider_watchdog import RequestControl, request_control
        context['control']=RequestControl()
        def respond():
            token=request_control.set(context['control'])
            phase='completed'
            try:
                return context['provider'].respond(context['history'],context['session_tools'],context['output_limit'])
            except BaseException:
                phase='failed'
                raise
            finally:
                request_control.reset(token)
                context['completed_at']=time.monotonic()
                publish(phase)
                print(f'[provider] {sid} request={receipt["call"]} transport={phase}',flush=True)
        context['future']=self.pool.submit(respond)
        self.pending[sid]=context

    def ready(self, sid):
        return sid in self.pending and self.pending[sid]['future'].done()


def ordered_tasks(tasks, order='models', *, serial=False):
    """A scheduling preference never prevents otherwise available concurrency."""
    fixed=[];groups={}
    for task in tasks:
        if task[1].get('provider')=='mock':fixed.append(task);continue
        groups.setdefault(Requests.model_key(task[1]),deque()).append(task)
    if order=='repetitions':return fixed+[task for group in groups.values() for task in group]
    result=list(fixed)
    while any(groups.values()):
        for group in groups.values():
            if not group:continue
            # Even sequential local runs finish a loaded model before switching.
            count=len(group) if serial and is_loopback(group[0][1].get('endpoint','')) else 1
            for _ in range(count):result.append(group.popleft())
    return result


def prepare(tasks, config, out, journal, engine, interrupt=None, on_progress=None, *, independent_fights=False):
    """Expose dispatch/recovery before starting tools, transports or fight work."""
    from .activity import operation
    from .experiment import TERMINAL
    tasks=list(tasks)
    states=journal.metadata()
    primary_generations={states.get(sid,{}).get('generation',0) for sid,_ in tasks}
    # Resume existing later-round transports before auditing/draining old rounds.
    # Their preparation context is already frozen in their own checkpoint.
    models={model['id']:model for model in config['models']}
    scheduled={sid for sid,_ in tasks}
    from .roster import active
    for sid,state in states.items():
        if (sid not in scheduled and state.get('status')=='running' and not state.get('submission')
                and state.get('parent') and states.get(state['parent'],{}).get('submission')
                and state.get('model') in models and active(config,state)):
            tasks.append((sid,models[state['model']]));scheduled.add(sid)
    # Frozen preparations have no work to dispatch. Do not load their potentially
    # large histories just to return immediately from run_session.
    finished=[sid for sid,_ in tasks if states.get(sid,{}).get('submission') and states[sid].get('status') in {'submitted','budget_exhausted'}]
    tasks=[(sid,model) for sid,model in tasks if sid not in finished]
    pending=[sid for sid,_ in tasks if states.get(sid,{}).get('status') not in TERMINAL]
    with operation(out,'scheduling_preparations',
                   generation=max((states.get(sid,{}).get('generation',0) for sid,_ in tasks),default=0),
                   conversations_to_resume=len(pending)):
        from .core import ArenaError, submission
        for sid in finished:
            info=states[sid]['submission']
            if submission(out/'sessions'/sid/'submission',info['entrypoint'])!=info:raise ArenaError('Archived session submission changed')
        if independent_fights:
            from .fight_coordinator import FightCoordinator
            from .execution_control import _journal
            with FightCoordinator(out,config,engine,on_progress) as fights:
                token=_journal.set(None)
                try:return _prepare(tasks,config,out,journal,engine,interrupt,primary_generations=primary_generations,fight_coordinator=fights)
                finally:_journal.reset(token)
        return _prepare(tasks,config,out,journal,engine,interrupt,on_progress,primary_generations=primary_generations)


def _prepare(tasks, config, out, journal, engine, interrupt=None, on_progress=None, *, primary_generations=None, fight_coordinator=None):
    """Finish one round before its caller starts the next round's preparation."""
    from .experiment import run_session, TERMINAL, provider_response
    limit=config.get('_parallel_requests',config.get('parallel_requests',1))
    tasks=ordered_tasks(tasks,config.get('_request_order',config.get('request_order','models')),serial=limit==1)
    regular_progress=on_progress
    def progress():
        if fight_coordinator is not None:
            fight_coordinator.notify()
            return
        if getattr(journal,'_manual_fight_retry_pending',False):
            from .fight_recovery import run as recover_fights
            result=recover_fights(out,engine=engine,journal=journal,cooperative=True)
            if not result.get('deferred'):journal._manual_fight_retry_pending=False
        # Recovered later-round sessions may finish while the controller is
        # still visiting an older round. Plan their fights immediately too.
        if primary_generations is not None:
            from .greedy import evaluate
            states=journal.metadata()
            extra={states[sid].get('generation',0) for sid,_ in tasks if sid in states}-primary_generations
            for generation in sorted(extra,reverse=True):evaluate(engine,config,out,journal,generation)
        if regular_progress:regular_progress()
    on_progress=progress
    dispatcher=Requests(limit,tasks,out=out)
    journal.requests=dispatcher
    queue=deque(tasks);models=dict(tasks)
    coordinator=threading.get_ident()
    from .conversation_recovery import automatic_due, recover, commands
    retry_waiting={}
    def queue_recoveries():
        from .retry_policy import apply
        for sid,paused in apply(out,journal):
            if not paused and sid in models:schedule_retry(sid,models[sid])
        for sid in list(retry_waiting):
            state=journal.metadata(sid).get(sid,{})
            if state.get('automatic_retries_paused') or state.get('conversation_paused'):retry_waiting.pop(sid,None)
        # A manual command can target a failed conversation from a later round.
        # Admit its saved task now instead of waiting for old fight queues to drain.
        from .core import read_json
        from .roster import active
        catalog={model['id']:model for model in config['models']}
        for path in (out/'recovery-commands').glob('*.json'):
            sid=read_json(path).get('session')
            if sid in models:continue
            state=journal.metadata(sid).get(sid,{})
            if state.get('model') in catalog and active(config,state):
                model=catalog[state['model']];tasks.append((sid,model))
                models[sid]=model;dispatcher.models[sid]=model
        for sid,model in commands(out,journal,config,tasks,dispatcher.pending):
            retry_waiting.pop(sid,None);dispatcher.finished.discard(sid)
            if sid not in {item[0] for item in queue}:queue.append((sid,model))
        for sid,(model,due) in list(retry_waiting.items()):
            if time.time()<due:continue
            state=journal.state(sid)
            if state and state.get('status') in {'provider_unavailable','no_submission'}:
                recover(sid,state,config,out,journal,automatic=True)
                dispatcher.finished.discard(sid)
                if sid not in {item[0] for item in queue}:queue.append((sid,model))
            retry_waiting.pop(sid,None)
    def schedule_retry(sid,model):
        state=journal.state(sid)
        due=automatic_due(state,config,journal.state(state['parent']) if state.get('parent') else None)
        if due is not None and sid not in retry_waiting:
            retry_waiting[sid]=(model,due)
            state['automatic_retry_at']=due
            journal.save(sid,state,'automatic_retry_scheduled',{'retry_at':due,'attempt':state.get('automatic_retry_attempts',0)+1})
    def drain_failures():
        if threading.get_ident()!=coordinator:return
        queue_recoveries()
        # Long engine batches must not delay the visibility of failed requests.
        # Successful receipts keep their normal tool/coordinator ordering.
        for sid,context in list(dispatcher.pending.items()):
            future=context['future']
            if not future.done() or future.exception() is None:continue
            state=journal.state(sid)
            if state is None:continue
            provider_response(sid,state,models[sid],config,journal)
            if state['status'] in TERMINAL:
                dispatcher.release(sid);schedule_retry(sid,models[sid])
            if sid not in {item[0] for item in queue}:queue.append((sid,models[sid]))
    from .activity import _provider_poller,_provider_yielder
    poll_token=_provider_poller.set(drain_failures)
    yield_token=_provider_yielder.set(lambda:any(dispatcher.ready(sid) for sid in dispatcher.pending) or
        any(sid not in dispatcher.pending and dispatcher.can_start(sid,model) for sid,model in queue))
    initial_progress=True
    last_retry_progress=0
    next_idle_progress=0
    try:
        while queue or dispatcher.pending or retry_waiting or any((out/'recovery-commands').glob('*.json')):
            if fight_coordinator is not None:fight_coordinator.check()
            from .runner_diagnostics import pulse
            pulse('scheduling_preparations',queued=len(queue),requests=len(dispatcher.pending),
                  ready_replies=sum(dispatcher.ready(sid) for sid in dispatcher.pending),retries=len(retry_waiting))
            queue_recoveries()
            from .execution_control import poll as poll_execution
            poll_execution(out,config.get('_parallel_fights',config.get('parallel_fights',1)))
            if queue and not dispatcher.pending and not any(dispatcher.can_start(sid,model) for sid,model in queue):
                # A stale local residency marker must never leave a fully idle
                # scheduler spinning. No request is running, so releasing it is safe.
                owners=list(dispatcher.local_owners.values())
                dispatcher.local_owners.clear()
                saved=journal.metadata()
                if saved:
                    sid=next(iter(saved));state=journal.state(sid)
                    journal.save(sid,state,'provider_scheduler_recovered',{
                        'reason':'No in-flight requests and all queued conversations blocked by local residency',
                        'previous_local_models':[list(owner) for owner in owners],
                        'queued_sessions':[sid for sid,_ in queue],'counters_preserved':True})
            for _ in range(len(queue)):
                sid,model=queue.popleft()
                if journal.metadata(sid).get(sid,{}).get('conversation_paused'):
                    if sid in dispatcher.pending:
                        if dispatcher.ready(sid):
                            state=journal.state(sid)
                            provider_response(sid,state,model,config,journal)
                        else:continue
                    dispatcher.release(sid)
                    retry_waiting.pop(sid,None)
                    continue
                if sid in dispatcher.pending and not dispatcher.ready(sid):continue
                if sid not in dispatcher.pending and (not dispatcher.can_start(sid,model) or (sid in dispatcher.deferred and dispatcher.pending)):
                    queue.append((sid,model));continue
                before=journal.metadata(sid).get(sid,{})
                run_session(sid,model,config,out,journal,engine,interrupt)
                state=journal.metadata(sid).get(sid)
                if state and state['status'] in TERMINAL:
                    dispatcher.release(sid)
                    schedule_retry(sid,model)
                    if on_progress and before.get('status') not in TERMINAL:on_progress()
                elif sid not in dispatcher.pending:
                    queue.append((sid,model))
            # Start/restart transports before draining already-submitted fights.
            # The readiness hook yields immediately if any conversation can advance.
            if initial_progress and on_progress:
                initial_progress=False
                on_progress()
            # Responses can arrive while serialized tools or available fights run.
            queued={sid for sid,_ in queue}
            for sid in dispatcher.pending:
                if dispatcher.ready(sid) and sid not in queued:queue.append((sid,models[sid]))
            runnable=any(sid not in dispatcher.pending and dispatcher.can_start(sid,model) for sid,model in queue)
            ready=any(dispatcher.ready(sid) for sid in dispatcher.pending)
            if on_progress and not runnable and not ready and time.monotonic()>=next_idle_progress and (dispatcher.pending or retry_waiting):
                # A yielded batch is still pending work. Refill engine workers
                # while transports wait, rather than waiting for another submission.
                on_progress()
                next_idle_progress=time.monotonic()+1
            if not queue and not dispatcher.pending and retry_waiting:
                if time.monotonic()-last_retry_progress>=1:
                    from .core import write_json
                    write_json(out/'activity.json',{'kind':'retry_backoff','started_at':time.time(),
                        'next_retry_at':min(due for _,due in retry_waiting.values()),
                        'participants':list(retry_waiting),'retry_count':len(retry_waiting)})
                    last_retry_progress=time.monotonic()
                time.sleep(.2)
            if not any(dispatcher.ready(sid) for sid in dispatcher.pending) and dispatcher.pending:
                wait([context['future'] for context in dispatcher.pending.values()],timeout=.2,return_when=FIRST_COMPLETED)
    finally:
        # Stop schedules no further tools or calls. Keep any replies already paid
        # for, including their pending tool calls, before releasing the journal.
        try:
            import sys
            if sys.exc_info()[0] is not None:
                if fight_coordinator is not None:fight_coordinator.stop.set()
                for context in dispatcher.pending.values():
                    if context.get('control'):context['control'].cancel()
            dispatcher.pool.shutdown(wait=True)
            for sid in list(dispatcher.pending):
                state=journal.state(sid)
                if state:provider_response(sid,state,models[sid],config,journal)
        finally:
            journal.requests=None
            _provider_poller.reset(poll_token)
            _provider_yielder.reset(yield_token)
