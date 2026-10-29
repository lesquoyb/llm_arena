"""Resizable engine workers; publication and checkpoints stay on the coordinator."""
from collections import deque
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
import time
import threading

from .activity import operation, poll_provider_failures, provider_work_ready
from .core import read_json, write_json
from .execution_control import poll


def run(jobs, execute, save, *, limit=1, out, kind, generation=0, retry=None):
    jobs=iter(jobs);retries=deque();pools=[];pending={};ready=deque();exhausted=False;error=None
    limit=poll(out,limit);pool=ThreadPoolExecutor(max_workers=limit,thread_name_prefix='arena-fight');pools.append(pool)
    from .worker_resources import host_memory, children_cpu_seconds, thread_cpu_seconds, cpu_capacity
    from . import io_metrics
    from .fight_history import History
    batch_wall_started=time.time();batch_started=time.monotonic();python_started=time.process_time();children_started=children_cpu_seconds()
    coordinator_ident=threading.get_ident();coordinator_native=threading.get_native_id();coordinator_started=time.thread_time();capacity=cpu_capacity()
    history=History(out,str(batch_wall_started));io_baseline={};last_performance=None
    throughput_path=out/'fight-throughput.json'
    throughput=read_json(throughput_path) if throughput_path.exists() else {}
    last_progress=0;publishing_seconds=0;phase_seconds={};finished_workers=0;jvm_starts=0;jvm_reuses=0
    guard=threading.RLock();stop_heartbeat=threading.Event();publication={}
    def snapshot(force=False):
        nonlocal last_progress,last_performance
        if not force and time.monotonic()-last_progress<.2:return
        fights=[{'participants':job['participants'],'seed':job['seed'],'started_at':started,
                 'phase':'ready_to_save' if future.done() else job.get('phase','preparing'),
                 'phase_started_at':job.get('phase_started_at',started),'retry':job.get('_retry',0)}
                for future,(job,started) in [*pending.items(),*ready]]
        write_json(out/'activity.json',{'kind':kind,'generation':generation,'started_at':batch_wall_started,'batch_started_at':batch_wall_started,'parallel_fights':limit,
            'publishing_seconds':publishing_seconds,'retrying_fights':len(retries),'computing_workers':sum(not future.done() for future in pending),'publication_queue':len(ready)+sum(future.done() for future in pending),
            'phase_seconds':phase_seconds,'finished_workers':finished_workers,'jvm_starts':jvm_starts,'jvm_reuses':jvm_reuses,'publication':publication,
            'fights':fights,'participants':list(dict.fromkeys(sid for item in fights for sid in item['participants']))})
        if throughput:write_json(throughput_path,throughput)
        if pending or ready or finished_workers:
            coordinator_cpu=thread_cpu_seconds(coordinator_ident,coordinator_native)
            last_performance={'generation':generation,'kind':kind,'parallel_fights':limit,
                'finished_workers':finished_workers,'jvm_starts':jvm_starts,'jvm_reuses':jvm_reuses,'publication_seconds':publishing_seconds,'phase_seconds':phase_seconds,
                'wall_seconds':time.monotonic()-batch_started,'python_cpu_seconds':time.process_time()-python_started,
                'children_cpu_seconds':None if children_started is None else children_cpu_seconds()-children_started,
                'host_memory':host_memory(),'occupied_phases':{name:sum(item['phase']==name for item in fights) for name in {item['phase'] for item in fights}},
                'observed_at':time.time(),'scope':'Latest engine batch; phase durations are summed worker time, not wall-clock duration.',
                'computing_workers':sum(not future.done() for future in pending),'publication_queue':len(ready)+sum(future.done() for future in pending),
                'coordinator_cpu_seconds':None if coordinator_cpu is None else max(0,coordinator_cpu-coordinator_started),
                'cpu_capacity':capacity,'io':io_metrics.snapshot(io_baseline)}
            write_json(out/'fight-performance.json',last_performance)
            history.observe(last_performance,throughput)
        last_progress=time.monotonic()
    def progress(force=False):
        with guard:snapshot(force)
    def heartbeat():
        while not stop_heartbeat.wait(.5):
            try:progress(True)
            except OSError:pass
    ticker=threading.Thread(target=heartbeat,name='arena-fight-progress',daemon=True)
    def publish(job,result):
        nonlocal publishing_seconds,finished_workers,publication,jvm_starts,jvm_reuses
        with guard:publication={'participants':job['participants'],'seed':job['seed'],'started_at':time.time()}
        job['timings']={**job.get('timings',{}),'publication_wait_seconds':max(0,time.time()-job.get('finished_at',time.time()))}
        started=time.monotonic()
        try:save(job,result)
        finally:
            with guard:publication={};publishing_seconds+=time.monotonic()-started
        with guard:
            finished_workers+=1
            reused=result.get('timings',{}).get('jvm_reused') if isinstance(result,dict) else None
            if reused is True:jvm_reuses+=1
            elif reused is False:jvm_starts+=1
        for key,value in {**(result.get('timings',{}) if isinstance(result,dict) else {}),**job.get('timings',{})}.items():
            if key.endswith('_seconds') and isinstance(value,(int,float)):
                with guard:phase_seconds[key]=phase_seconds.get(key,0)+value
        if retry and result.get('status') in {'timeout','engine_error'} and job.get('_retry',0)<2:
            replacement=retry(job)
            replacement['_retry']=job.get('_retry',0)+1
            retries.append(replacement)
    with operation(out,kind,generation=generation,parallel_fights=limit),io_metrics.capture() as io_baseline:
        ticker.start()
        try:
            while pending or ready or not exhausted or retries:
                updated=poll(out,limit)
                if updated!=limit:
                    pool.shutdown(wait=False)
                    limit=updated;pool=ThreadPoolExecutor(max_workers=limit,thread_name_prefix='arena-fight');pools.append(pool)
                # Finished jobs free compute slots immediately. Keep a bounded
                # publication queue so slow persistence cannot grow RAM without limit.
                for future in list(pending):
                    if future.done():
                        with guard:ready.append((future,pending.pop(future)))
                while len(pending)<limit and len(ready)+len(pending)<2*limit and (not exhausted or retries):
                    if provider_work_ready():exhausted=True;retries.clear();break
                    job=retries.popleft() if retries else next(jobs,None)
                    if job is None:exhausted=True;break
                    job['phase']=job.get('phase','preparing');job['phase_started_at']=time.time()
                    started=time.time();future=pool.submit(execute,job)
                    def finished(future,job=job):
                        job.update(finished_at=time.time(),phase='ready_to_save',phase_started_at=time.time())
                        if not future.cancelled() and future.exception() is None:
                            result=future.result()
                            if isinstance(result,dict) and result.get('status'):
                                from .fight_throughput import add
                                with guard:add(throughput,result,job['finished_at'])
                    future.add_done_callback(finished)
                    with guard:pending[future]=(job,started)
                progress()
                poll_provider_failures()
                if ready:
                    with guard:future,(job,_)=ready.popleft()
                    publish(job,future.result())
                elif pending:
                    wait(pending,timeout=.2,return_when=FIRST_COMPLETED)
                else:break
                progress()
        except BaseException as failure:error=failure
        finally:
            # Finish already dispatched work even on stop/failure; retries not
            # dispatched remain failed records for the next attempt or Resume.
            for future,(job,_) in [*ready,*list(pending.items())]:
                try:publish(job,future.result())
                except BaseException as failure:
                    if error is None:error=failure
            with guard:pending.clear();ready.clear()
            for executor in pools:executor.shutdown(wait=True)
            stop_heartbeat.set();ticker.join()
            progress(True)
            if last_performance:history.observe(last_performance,throughput,force=True)
        if error is not None:raise error
