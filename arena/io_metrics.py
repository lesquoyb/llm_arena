"""Small process-local I/O counters, enabled only while a fight batch runs."""
import threading
from contextlib import contextmanager

_lock=threading.Lock()
_users=0
enabled=False
_values={}


def begin():
    global _users,enabled
    with _lock:_users+=1;enabled=True;return dict(_values)


def end():
    global _users,enabled
    with _lock:_users=max(0,_users-1);enabled=bool(_users)


def add(name,seconds):
    if not enabled:return
    with _lock:
        _values[name+'_calls']=_values.get(name+'_calls',0)+1
        _values[name+'_seconds']=_values.get(name+'_seconds',0)+seconds


def snapshot(baseline=None):
    with _lock:current=dict(_values)
    return {key:value-(baseline or {}).get(key,0) for key,value in current.items()}


@contextmanager
def capture():
    baseline=begin()
    try:yield baseline
    finally:end()
