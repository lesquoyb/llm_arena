"""Concurrent transports; the coordinator owns tools, checkpoints and SQLite."""
from collections import deque
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
import time
import threading
from urllib.parse import urlsplit
from .endpoints import is_loopback


class Requests:
    def __init__(self, limit, tasks=()):
        self.limit=limit
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
        def respond():
            phase='completed'
            try:
                return context['provider'].respond(context['history'],context['session_tools'],context['output_limit'])
            except BaseException:
                phase='failed'
                raise
            finally:
                context['completed_at']=time.monotonic()
                publish(phase)
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


def prepare(tasks, config, out, journal, engine, interrupt=None, on_progress=None):
    """Expose dispatch/recovery before starting tools, transports or fight work."""
    from .activity import operation
    from .experiment import TERMINAL
    tasks=list(tasks)
    states=journal.metadata()
    pending=[sid for sid,_ in tasks if states.get(sid,{}).get('status') not in TERMINAL]
    with operation(out,'scheduling_preparations',
                   generation=max((states.get(sid,{}).get('generation',0) for sid,_ in tasks),default=0),
                   conversations_to_resume=len(pending)):
        return _prepare(tasks,config,out,journal,engine,interrupt,on_progress)


def _prepare(tasks, config, out, journal, engine, interrupt=None, on_progress=None):
    """Finish one round before its caller starts the next round's preparation."""
    from .experiment import run_session, TERMINAL, provider_response
    limit=config.get('_parallel_requests',config.get('parallel_requests',1))
    tasks=ordered_tasks(tasks,config.get('_request_order',config.get('request_order','models')),serial=limit==1)
    if limit==1:
        # A resumed fight backlog must not run before later resumable sessions.
        # There is no asynchronous dispatcher to provide this readiness signal.
        from .activity import _provider_yielder
        remaining=deque(tasks)
        token=_provider_yielder.set(lambda:any(
            journal.metadata(sid).get(sid,{}).get('status') not in TERMINAL
            for sid,_ in remaining))
        try:
            while remaining:
                sid,model=remaining.popleft()
                before=journal.metadata(sid).get(sid,{})
                run_session(sid,model,config,out,journal,engine,interrupt)
                if on_progress and before.get('status') not in TERMINAL:on_progress()
        finally:
            _provider_yielder.reset(token)
        return
    dispatcher=Requests(limit,tasks)
    journal.requests=dispatcher
    queue=deque(tasks);models=dict(tasks)
    coordinator=threading.get_ident()
    def drain_failures():
        if threading.get_ident()!=coordinator:return
        # Long engine batches must not delay the visibility of failed requests.
        # Successful receipts keep their normal tool/coordinator ordering.
        for sid,context in list(dispatcher.pending.items()):
            future=context['future']
            if not future.done() or future.exception() is None:continue
            state=journal.state(sid)
            if state is None:continue
            provider_response(sid,state,models[sid],config,journal)
            if state['status'] in TERMINAL:dispatcher.release(sid)
            if sid not in {item[0] for item in queue}:queue.append((sid,models[sid]))
    from .activity import _provider_poller,_provider_yielder
    poll_token=_provider_poller.set(drain_failures)
    yield_token=_provider_yielder.set(lambda:any(dispatcher.ready(sid) for sid in dispatcher.pending) or
        any(sid not in dispatcher.pending and dispatcher.can_start(sid,model) for sid,model in queue))
    initial_progress=True
    try:
        while queue or dispatcher.pending:
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
                if sid in dispatcher.pending and not dispatcher.ready(sid):continue
                if sid not in dispatcher.pending and (not dispatcher.can_start(sid,model) or (sid in dispatcher.deferred and dispatcher.pending)):
                    queue.append((sid,model));continue
                before=journal.metadata(sid).get(sid,{})
                run_session(sid,model,config,out,journal,engine,interrupt)
                state=journal.metadata(sid).get(sid)
                if state and state['status'] in TERMINAL:
                    dispatcher.release(sid)
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
            if not any(dispatcher.ready(sid) for sid in dispatcher.pending) and dispatcher.pending:
                wait([context['future'] for context in dispatcher.pending.values()],timeout=.2,return_when=FIRST_COMPLETED)
    finally:
        # Stop schedules no further tools or calls. Keep any replies already paid
        # for, including their pending tool calls, before releasing the journal.
        try:
            dispatcher.pool.shutdown(wait=True)
            for sid in list(dispatcher.pending):
                state=journal.state(sid)
                if state:provider_response(sid,state,models[sid],config,journal)
        finally:
            journal.requests=None
            _provider_poller.reset(poll_token)
            _provider_yielder.reset(yield_token)
