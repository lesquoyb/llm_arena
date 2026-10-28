"""Small transient coordinator status, separate from immutable fight artifacts."""
from contextlib import contextmanager
from contextvars import ContextVar
import time
from .core import write_json


_operations=ContextVar('arena_operations',default=())


@contextmanager
def operation(out, kind, **details):
    started=time.time()
    value={'kind':kind,'started_at':started,**details}
    parents=_operations.get()
    token=_operations.set((*parents,(out.resolve(),value)))
    try:
        write_json(out/'activity.json',value)
        yield
    finally:
        _operations.reset(token)
        parent=next((entry for path,entry in reversed(parents) if path==out.resolve()),None)
        write_json(out/'activity.json',parent or {**value,'kind':'idle','previous_kind':kind,'finished_at':time.time()})


def session_root(directory):
    return directory.parent.parent if directory.parent.name=='sessions' else directory


_provider_poller=ContextVar('arena_provider_poller',default=None)


def poll_provider_failures():
    """Called only on the coordinator; engine threads have no poller context."""
    callback=_provider_poller.get()
    if callback is not None:callback()


_provider_yielder=ContextVar('arena_provider_yielder',default=None)


def provider_work_ready():
    callback=_provider_yielder.get()
    return bool(callback and callback())
