"""Small rolling samples for diagnosing throughput without scanning match files."""
import json
from .fight_throughput import rate


class History:
    def __init__(self,out,batch):
        self.path=out/'fight-performance-history.jsonl';self.batch=batch;self.previous=None;self.errors=0

    def observe(self,sample,throughput,force=False):
        now=sample['observed_at'];previous=self.previous
        if previous and now-previous['observed_at']<(.1 if force else 5):return
        interval=now-previous['observed_at'] if previous else None
        def delta(key):
            a,b=sample.get(key),previous.get(key) if previous else None
            return max(0,a-b) if a is not None and b is not None else None
        def differences(key):
            return {name:max(0,value-(previous or {}).get(key,{}).get(name,0)) for name,value in sample.get(key,{}).items()} if previous else {}
        row={'observed_at':now,'batch':self.batch,'generation':sample['generation'],'kind':sample['kind'],
             'interval_seconds':interval,'parallel_fights':sample['parallel_fights'],
             'computing_workers':sample['computing_workers'],'publication_queue':sample['publication_queue'],
             'occupied_phases':sample['occupied_phases'],'throughput':rate(throughput,now),
             'published_delta':delta('finished_workers'),'phase_seconds_delta':differences('phase_seconds'),
             'publication_seconds_delta':delta('publication_seconds'),
             'python_cpu_cores':delta('python_cpu_seconds')/interval if interval else None,
             'coordinator_cpu_cores':delta('coordinator_cpu_seconds')/interval if interval and delta('coordinator_cpu_seconds') is not None else None,
             'io_delta':differences('io'),'host_memory':sample['host_memory']}
        try:
            if self.path.exists() and self.path.stat().st_size>8_000_000:self.path.replace(self.path.with_suffix('.previous.jsonl'))
            with self.path.open('a',encoding='utf-8') as stream:stream.write(json.dumps(row,separators=(',',':'))+'\n')
        except OSError:self.errors+=1  # Optional telemetry never invalidates a fight.
        self.previous={**sample,'phase_seconds':dict(sample['phase_seconds']),'io':dict(sample['io'])}


def read(out,limit=120):
    path=out/'fight-performance-history.jsonl'
    if not path.exists():return []
    with path.open('rb') as stream:
        stream.seek(0,2);start=max(0,stream.tell()-1_000_000);stream.seek(start);lines=stream.read().splitlines()
    if start:lines=lines[1:]
    result=[]
    for line in lines[-limit:]:
        try:result.append(json.loads(line))
        except (ValueError,UnicodeError):continue  # A heartbeat may be appending.
    return result
