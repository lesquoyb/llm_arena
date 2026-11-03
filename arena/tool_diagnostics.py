"""Transient tool phases separate execution time from journal and SQLite work."""
import time
from .core import write_json
from .runner_diagnostics import pulse


class ToolTrace:
    def __init__(self, out, sid, name, call, sql, received_at=None):
        self.path=out/'sessions'/sid/'tool-progress.json'
        self.sid=sid;self.name=name;self.call=call;self.sql=sql
        self.started=time.monotonic();self.previous=self.started;self.phase=None;self.durations={}
        self.since_response=max(0,time.time()-received_at) if received_at is not None else None

    def step(self, phase):
        now=time.monotonic()
        if self.phase:self.durations[self.phase+'_seconds']=self.durations.get(self.phase+'_seconds',0)+now-self.previous
        self.previous=now;self.phase=phase
        pulse('tool_'+phase,session=self.sid,tool=self.name)
        value={'call':self.call,'name':self.name,'phase':phase,'updated_at':time.time(),
               'elapsed_seconds':now-self.started,'since_response_seconds':self.since_response,
               'timings':{**self.durations,**self.sql}}
        print(f'[tool] {self.sid} {self.call} {self.name} phase={phase} elapsed={now-self.started:.3f}s sqlite={self.sql["sqlite_wall_seconds"]:.3f}s',flush=True)
        # Telemetry failure must not change whether an executed tool is saved.
        try:write_json(self.path,value)
        except OSError:pass
