"""Concurrent transports; the coordinator alone owns tools, files and SQLite."""
from collections import deque
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
import time
from urllib.parse import urlsplit
from .endpoints import is_loopback


class Requests:
    def __init__(self, limit):
        self.limit=limit
        self.pool=ThreadPoolExecutor(max_workers=limit,thread_name_prefix='arena-provider')
        self.pending={}
        self.deferred=set()
        self.local_owners={}

    def local_key(self, model):
        endpoint=model.get('endpoint','')
        if model.get('provider')!='mock' and is_loopback(endpoint):
            parsed=urlsplit(endpoint)
            return parsed.scheme,parsed.port or (443 if parsed.scheme=='https' else 80)
        return None

    def can_start(self, sid, model):
        key=self.local_key(model)
        return len(self.pending)<self.limit and (key is None or self.local_owners.get(key,sid)==sid)

    def release(self, sid):
        self.local_owners={key:owner for key,owner in self.local_owners.items() if owner!=sid}

    def other_reservations(self, sid, journal):
        from .usage import amount
        return sum(amount((journal.state(other) or {}).get('money_reserved','0')) for other in self.pending if other!=sid)

    def submit(self, sid, context):
        key=self.local_key(context['model'])
        if key is not None:self.local_owners[key]=sid
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


def prepare(tasks, config, out, journal, engine, interrupt=None, on_progress=None):
    """Finish one round before its caller starts the next round's preparation."""
    from .experiment import run_session, TERMINAL, provider_response
    tasks=sorted(tasks,key=lambda item:item[1].get('provider')!='mock')
    limit=config.get('parallel_requests',1)
    if limit==1:
        for sid,model in tasks:
            before=journal.metadata(sid).get(sid,{})
            run_session(sid,model,config,out,journal,engine,interrupt)
            if on_progress and before.get('status') not in TERMINAL:on_progress()
        return
    dispatcher=Requests(limit)
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
