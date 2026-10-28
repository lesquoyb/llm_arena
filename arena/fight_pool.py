"""Bounded engine workers; only the coordinator publishes records and journal events."""
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
import time

from .activity import operation, poll_provider_failures, provider_work_ready
from .core import write_json


def run(jobs, execute, save, *, limit=1, out, kind, generation=0):
    jobs=iter(jobs)
    with operation(out,kind,generation=generation,parallel_fights=limit):
        if limit==1:
            while not provider_work_ready():
                poll_provider_failures()
                job=next(jobs,None)
                if job is None:break
                started=time.time()
                write_json(out/'activity.json',{'kind':kind,'generation':generation,'started_at':started,
                    'parallel_fights':1,'fights':[{'participants':job['participants'],'seed':job['seed'],'started_at':started}],
                    'participants':job['participants']})
                save(job,execute(job))
            return
        with ThreadPoolExecutor(max_workers=limit,thread_name_prefix='arena-fight') as pool:
            pending={}
            exhausted=False
            error=None
            def progress():
                fights=[{'participants':job['participants'],'seed':job['seed'],'started_at':started}
                        for job,started in pending.values()]
                write_json(out/'activity.json',{'kind':kind,'generation':generation,'started_at':min(
                    (item['started_at'] for item in fights),default=time.time()),'parallel_fights':limit,
                    'fights':fights,'participants':list(dict.fromkeys(sid for item in fights for sid in item['participants']))})
            try:
                while pending or not exhausted:
                    while not exhausted and len(pending)<limit:
                        if provider_work_ready():exhausted=True;break
                        job=next(jobs,None)
                        if job is None:exhausted=True;break
                        pending[pool.submit(execute,job)]=(job,time.time())
                    progress()
                    if not pending:break
                    done,_=wait(pending,timeout=.2,return_when=FIRST_COMPLETED)
                    poll_provider_failures()
                    for future in done:
                        job,_=pending.pop(future)
                        save(job,future.result())
                    progress()
            except BaseException as failure:
                error=failure
            finally:
                # Preserve other completed work even when one worker fails. No
                # new jobs are started; each worker has its own process deadline.
                for future,(job,_) in list(pending.items()):
                    try:save(job,future.result())
                    except BaseException as failure:
                        if error is None:error=failure
                pending.clear()
                progress()
            if error is not None:raise error
