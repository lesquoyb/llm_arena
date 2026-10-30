"""Independent run-log heartbeat, including stacks when the coordinator stalls."""
import faulthandler
import threading
import time

_active=None


def pulse(kind, **counts):
    if _active is not None:_active.pulse(kind, **counts)


class Diagnostics:
    def __init__(self, interval=30, stalled_after=120):
        self.interval=interval;self.stalled_after=stalled_after
        self.owner=threading.get_ident();self.lock=threading.Lock()
        self.updated=time.monotonic();self.kind='starting';self.counts={}
        self.last_log=None;self.last_dump=None;self.stop=threading.Event()
        self.thread=threading.Thread(target=self.watch,name='arena-run-log',daemon=True)

    def pulse(self, kind, **counts):
        # Worker/ticker activity must not mask a blocked coordinator.
        if threading.get_ident()!=self.owner:return
        with self.lock:
            self.updated=time.monotonic();self.kind=kind;self.counts=counts

    def sample(self):
        now=time.monotonic()
        with self.lock:age=now-self.updated;kind=self.kind;counts=dict(self.counts)
        if self.last_log is None or now-self.last_log>=self.interval:
            details=' '.join(f'{key}={value}' for key,value in counts.items())
            print(f'[arena] phase={kind} coordinator_idle_seconds={age:.1f} {details}',flush=True)
            self.last_log=now
        if age>=self.stalled_after and (self.last_dump is None or now-self.last_dump>=self.stalled_after):
            print('[arena] Coordinator has not advanced; thread stacks follow in this run log.',flush=True)
            faulthandler.dump_traceback(all_threads=True)
            self.last_dump=now

    def watch(self):
        while not self.stop.wait(1):self.sample()

    def __enter__(self):
        global _active
        _active=self;self.sample();self.thread.start()
        return self

    def __exit__(self,*args):
        global _active
        self.stop.set();self.thread.join();_active=None
