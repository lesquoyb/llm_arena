"""Rolling physical engine completions, separate from cached logical fixtures."""
import time


def add(buckets, result, now=None):
    now=time.time() if now is None else now
    second=int(now)
    for key in list(buckets):
        if int(key)<=second-60:del buckets[key]
    row=buckets.setdefault(str(second),{'engine':0,'cache':0,'failed':0})
    if result.get('reference_cache',{}).get('hit'):row['cache']+=1
    elif result.get('status')=='completed':row['engine']+=1
    else:row['failed']+=1


def rate(buckets, now=None):
    now=time.time() if now is None else now
    recent=[row for second,row in buckets.items() if int(now)-60<int(second)<=int(now)]
    return {name+'_per_minute':sum(row.get(name,0) for row in recent) for name in ('engine','cache','failed')}
