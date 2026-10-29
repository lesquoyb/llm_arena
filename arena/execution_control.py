"""Live engine controls; only the coordinator commits journal events."""
from contextvars import ContextVar
from .core import read_json, write_json, integer

_journal=ContextVar('arena_execution_journal',default=None)


def poll(out, default=1):
    path=out/'execution-control.json'
    value=read_json(path) if path.exists() else {}
    limit=value.get('parallel_fights',default)
    integer(limit,1,None,'parallel_fights')
    journal=_journal.get()
    if journal is not None and journal.out.resolve()==out.resolve():
        revision=value.get('id')
        if revision and revision!=getattr(journal,'_execution_revision',None):
            states=journal.metadata()
            if states:
                sid=next(iter(states));journal.save(sid,journal.state(sid),'execution_settings_applied',value)
                journal._execution_revision=revision
        requests=list((out/'fight-retry-requests').glob('*.json'))
        if requests:
            journal._ready_evaluations={}
            journal._fight_retry_epoch=getattr(journal,'_fight_retry_epoch',0)+1
            journal._manual_fight_retry_pending=True
            journal._manual_recovery_done=set()
            journal._manual_pending_jobs={}
            journal._manual_failures={}
            states=journal.metadata()
            for request in requests:
                command=read_json(request)
                if states:
                    sid=next(iter(states));journal.save(sid,journal.state(sid),'fight_retry_requested',command)
                write_json(out/'fight-retry-receipts'/request.name,{**command,'status':'accepted'})
                request.unlink()
    return limit
