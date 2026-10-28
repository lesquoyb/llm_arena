"""Concurrent transports; the coordinator alone owns tools, files and SQLite."""
from collections import deque
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
import time
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
        def respond():
            try:
                return context['provider'].respond(context['history'],context['session_tools'],context['output_limit'])
            finally:
                context['completed_at']=time.monotonic()
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
    """Finish one round before its caller starts the next round's preparation."""
    from .experiment import run_session, TERMINAL, provider_response
    limit=config.get('parallel_requests',1)
    tasks=ordered_tasks(tasks,config.get('_request_order',config.get('request_order','models')),serial=limit==1)
    if limit==1:
        for sid,model in tasks:
            before=journal.metadata(sid).get(sid,{})
            run_session(sid,model,config,out,journal,engine,interrupt)
            if on_progress and before.get('status') not in TERMINAL:on_progress()
        return
    dispatcher=Requests(limit,tasks)
    journal.requests=dispatcher
    queue=deque(tasks);models=dict(tasks)
    try:
        while queue or dispatcher.pending:
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
