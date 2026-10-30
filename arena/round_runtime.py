"""Checkpointed round wall time: union of live lanes, never a span across restarts."""
import copy
import json
import sqlite3
import threading
import time
from contextlib import closing
from .core import read_json,write_json

_clocks={}
_guard=threading.Lock()
GAP=600


def phase(kind):
    if kind in {'idle',None}:return None
    if kind in {'checkpoint_verification','checking_fights','validation'}:return 'verification'
    if kind=='tournament_fight':return 'tournament'
    if kind in {'reference_fight','previous_round_fight'}:return 'references'
    if kind=='retry_backoff':return 'waiting'
    return 'preparation'


def mark(out,lane,generation,kind):
    with _guard:clock=_clocks.get(out.resolve())
    if clock:clock.mark(lane,generation,kind)


def estimate_history(out,cutoff):
    """Read timestamps only, never replay bodies or full conversation histories."""
    samples={}
    def add(generation,stamp):
        if isinstance(stamp,(float,int)) and stamp<=cutoff:
            samples.setdefault(str(generation+1),[]).append(stamp)
    database=out/'journal.sqlite'
    if database.is_file():
        with closing(sqlite3.connect(database.as_uri()+'?mode=ro',uri=True,timeout=2)) as db:
            indexed=db.execute("SELECT 1 FROM sqlite_master WHERE name='session_metadata'").fetchone()
            query="SELECT id,json_extract(metadata,'$.generation') FROM session_metadata" if indexed else "SELECT id,json_extract(state,'$.generation') FROM sessions"
            generations={sid:generation or 0 for sid,generation in db.execute(query)}
            for sid,stamp in db.execute("SELECT session,json_extract(payload,'$.at') FROM events WHERE session IS NOT NULL"):
                if sid in generations:add(generations[sid],stamp)
    for name in ('fight-performance-history.previous.jsonl','fight-performance-history.jsonl'):
        path=out/name
        if not path.is_file():continue
        with path.open(encoding='utf-8') as stream:
            for line in stream:
                try:
                    row=json.loads(line)
                    add(row['generation'],row['observed_at'])
                except (ValueError,KeyError,TypeError):continue
    result={}
    for number,stamps in samples.items():
        stamps=sorted(set(stamps))
        duration=sum(b-a for a,b in zip(stamps,stamps[1:]) if 0<=b-a<=GAP)
        result[number]={'active_seconds':duration,'estimated_seconds':duration,'phase_seconds':{}}
    return result


class RoundClock:
    def __init__(self,out,*,now=time.monotonic,wall=time.time):
        self.out=out;self.path=out/'round-runtime.json';self.now=now;self.wall=wall
        try:saved=read_json(self.path) if self.path.is_file() else {}
        except (OSError,ValueError):saved={}
        self.rounds=saved.get('rounds',{});self.history_complete=saved.get('history_estimate_complete',False)
        self.bootstrap=not self.history_complete
        self.lanes={};self.last=now();self.cutoff=saved.get('history_cutoff',wall());self.lock=threading.RLock()
        self.stop=threading.Event();self.thread=threading.Thread(target=self.watch,name='arena-round-clock',daemon=True)

    def tick(self):
        with self.lock:
            now=self.now();elapsed=now-self.last;self.last=now
            # A suspended process has no intervening ticks; never bridge that gap.
            if elapsed<0 or elapsed>GAP:return
            active={}
            for generation,category in self.lanes.values():
                if category:active.setdefault(str(generation+1),set()).add(category)
            for number,categories in active.items():
                row=self.rounds.setdefault(number,{'active_seconds':0,'estimated_seconds':0,'phase_seconds':{}})
                row['active_seconds']+=elapsed
                for category in categories:row['phase_seconds'][category]=row['phase_seconds'].get(category,0)+elapsed

    def mark(self,lane,generation,kind):
        with self.lock:
            self.tick()
            previous=self.lanes.get(lane,(0,None))
            self.lanes[lane]=(generation if generation is not None else previous[0],phase(kind))

    def snapshot(self,recording=True):
        with self.lock:
            self.tick()
            return {'schema_version':1,'observed_at':self.wall(),'gap_threshold_seconds':GAP,
                    'history_cutoff':self.cutoff,'history_estimate_complete':self.history_complete,
                    'recording':recording,'rounds':copy.deepcopy(self.rounds),
                    'lanes':[{'round':generation+1,'phase':category} for generation,category in self.lanes.values() if category]}

    def save(self,recording=True):
        value=self.snapshot(recording)
        try:write_json(self.path,value)
        except OSError:pass  # Timing telemetry must not change benchmark outcomes.

    def watch(self):
        if self.bootstrap:
            try:
                historical=estimate_history(self.out,self.cutoff)
                with self.lock:
                    for number,estimate in historical.items():
                        row=self.rounds.setdefault(number,{'active_seconds':0,'estimated_seconds':0,'phase_seconds':{}})
                        row['active_seconds']+=estimate['active_seconds'];row['estimated_seconds']+=estimate['estimated_seconds']
                    self.history_complete=True
            except (OSError,ValueError,sqlite3.Error):pass
        self.save();saved=self.now()
        while not self.stop.wait(1):
            self.tick()
            if self.now()-saved>=30:self.save();saved=self.now()

    def __enter__(self):
        with _guard:_clocks[self.out.resolve()]=self
        self.thread.start();return self

    def __exit__(self,*args):
        self.stop.set();self.thread.join();self.save(False)
        with _guard:_clocks.pop(self.out.resolve(),None)


def view(value,*,running,now=None,started_at=None):
    """Extrapolate at most one heartbeat gap; stopped jobs never accrue time."""
    value=copy.deepcopy(value);now=time.time() if now is None else now
    elapsed=now-value.get('observed_at',now)
    rows=value.get('rounds',{})
    current_worker=started_at is None or value.get('observed_at',0)>=started_at
    if running and current_worker and value.get('recording') and 0<=elapsed<=GAP:
        active={}
        for lane in value.get('lanes',[]):active.setdefault(str(lane['round']),set()).add(lane['phase'])
        for number,categories in active.items():
            row=rows.setdefault(number,{'active_seconds':0,'estimated_seconds':0,'phase_seconds':{}})
            row['active_seconds']+=elapsed
            for category in categories:row['phase_seconds'][category]=row['phase_seconds'].get(category,0)+elapsed
    return {'rounds':[{'round':int(number),**row} for number,row in sorted(rows.items(),key=lambda item:int(item[0]))],
            'gap_threshold_seconds':GAP,'phase_times_overlap':True}
