"""Bounded request timings without prompts, credentials or artifact contents."""
from collections import deque
from contextvars import ContextVar
from functools import wraps
from contextlib import contextmanager
from threading import RLock
import time
from uuid import uuid4

_current=ContextVar('arena_web_performance',default=None)


class Profile:
    def __init__(self,route):
        self.id=uuid4().hex[:12];self.route=route;self.started=time.perf_counter()
        self.cpu_started=time.thread_time();self.at=time.time();self.metrics={};self.stack=[]
        self.status=None;self.response_bytes=0;self.memo={}

    def add(self,name,seconds):
        value=self.metrics.setdefault(name,{'calls':0,'seconds':0})
        value['calls']+=1;value['seconds']+=seconds

    def snapshot(self,finished=False):
        return {'id':self.id,'route':self.route,'at':self.at,'seconds':time.perf_counter()-self.started,
                'thread_cpu_seconds':time.thread_time()-self.cpu_started if finished else None,
                'status':self.status,'response_bytes':self.response_bytes,
                'active_stage':self.stack[-1] if self.stack else None,
                'stages':{name:dict(value) for name,value in self.metrics.copy().items()},'finished':finished}


class History:
    def __init__(self):self.lock=RLock();self.active={};self.recent=deque(maxlen=80)
    def snapshot(self):
        with self.lock:return {'active':[p.snapshot() for p in self.active.values()],'recent':list(self.recent)}


def measure(name):
    def decorate(function):
        @wraps(function)
        def wrapped(*args,**kwargs):
            with stage(name):return function(*args,**kwargs)
        return wrapped
    return decorate


@contextmanager
def stage(name):
    profile=_current.get()
    if profile is None:yield;return
    start=time.perf_counter();profile.stack.append(name)
    try:yield
    finally:
        profile.stack.pop();profile.add(name,time.perf_counter()-start)


class TimedRLock:
    def __init__(self):self.lock=RLock()
    def acquire(self,*args,**kwargs):
        with stage('store_lock_wait'):return self.lock.acquire(*args,**kwargs)
    def release(self):return self.lock.release()
    def __enter__(self):self.acquire();return self
    def __exit__(self,*args):self.release()


def request(function):
    @wraps(function)
    def wrapped(handler,*args,**kwargs):
        route=handler.path.split('?',1)[0]
        if not route.startswith('/api/') or route=='/api/performance':return function(handler,*args,**kwargs)
        history=handler.server.app.store.performance;profile=Profile(route)
        token=_current.set(profile)
        with history.lock:history.active[profile.id]=profile
        try:return function(handler,*args,**kwargs)
        finally:
            snapshot=profile.snapshot(finished=True)
            with history.lock:
                history.active.pop(profile.id,None);history.recent.appendleft(snapshot)
            _current.reset(token)
    return wrapped


def response(status,size):
    profile=_current.get()
    if profile:profile.status=status;profile.response_bytes=size


def request_cached(function):
    @wraps(function)
    def wrapped(self,*args,**kwargs):
        profile=_current.get()
        if profile is None:return function(self,*args,**kwargs)
        key=(id(self),function.__name__,args,tuple(sorted(kwargs.items())))
        if key not in profile.memo:profile.memo[key]=function(self,*args,**kwargs)
        return profile.memo[key]
    return wrapped
