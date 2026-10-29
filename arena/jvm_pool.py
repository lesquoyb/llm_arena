"""Reusable JVM slots with a fresh game/compiler classloader per fight."""
import atexit
import base64
import os
from pathlib import Path
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import weakref
from .core import STATE_ROOT


_pools=weakref.WeakSet()
_registry_lock=threading.Lock()
_reaper=None
_shutdown=threading.Event()

def _reap():
    while not _shutdown.wait(1):
        with _registry_lock:values=list(_pools)
        for pool in values:pool.prune()

def _close_all():
    _shutdown.set()
    with _registry_lock:values=list(_pools)
    for pool in values:pool.close()

atexit.register(_close_all)


class Worker:
    def __init__(self, engine):
        self.root=Path(tempfile.mkdtemp(prefix='jvm-',dir=STATE_ROOT/'tmp'))
        self.process=None;self.messages=queue.Queue();self.jobs=0;self.used=time.monotonic()
        try:
            shutil.copytree(engine.metadata['data'],self.root/'data')
            args=[engine.metadata['java'],*engine.worker_options,'-Djava.system.class.loader=arena.bridge.ArenaWorker$DispatchLoader','-cp',os.pathsep.join([engine.metadata['classes'],engine.metadata['jar']]),'arena.bridge.ArenaWorker']
            if os.name=='posix':args=[sys.executable,str(Path(__file__).with_name('worker_limits.py')),*args]
            allowed={'PATH','JAVA_HOME','SYSTEMROOT','WINDIR','TEMP','TMP','TMPDIR','LANG','LC_ALL','TZ'}
            self.stderr=(self.root/'worker-startup.log').open('ab')
            self.process=subprocess.Popen(args,cwd=self.root,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.stderr,
                env={key:value for key,value in os.environ.items() if key.upper() in allowed},**({'start_new_session':True} if os.name=='posix' else {}))
            def read():
                try:
                    for line in self.process.stdout:self.messages.put(line.decode('utf-8',errors='replace').strip())
                finally:self.messages.put('EXIT')
            self.reader=threading.Thread(target=read,name='arena-jvm-control',daemon=True);self.reader.start()
        except BaseException:
            self.close();raise

    def wait(self, expected, deadline, work, timeout):
        from .engine import OUTPUT_LIMIT, WorkerOutputLimit
        def oversized(path):
            try:return path.stat().st_size>OUTPUT_LIMIT
            except FileNotFoundError:return False  # The next request removes the previous outcome.
        while True:
            if any(oversized(path) for path in (work/'stdout.log',work/'stderr.log',self.root/'outcome.json')):
                raise WorkerOutputLimit('Worker output exceeded 8 MB per file')
            remaining=deadline-time.monotonic()
            if remaining<=0:raise subprocess.TimeoutExpired('pooled JVM fight',timeout)
            try:message=self.messages.get(timeout=min(.05,remaining))
            except queue.Empty:
                if self.process.poll() is not None:return False
                continue
            if message==expected:return True
            if message=='EXIT':return False

    def close(self):
        from .engine import stop_worker
        if self.process is not None:
            stop_worker(self.process)
            for stream in (self.process.stdin,self.process.stdout):
                if stream:
                    try:stream.close()
                    except OSError:pass
            if hasattr(self,'reader'):self.reader.join(timeout=1)
        if hasattr(self,'stderr'):self.stderr.close()
        shutil.rmtree(self.root,ignore_errors=True)


class Pool:
    def __init__(self, engine, recycle=32):
        self.engine=engine;self.recycle=recycle;self.idle=[];self.all=set();self.lock=threading.Lock()
        (STATE_ROOT/'tmp').mkdir(parents=True,exist_ok=True)
        global _reaper
        with _registry_lock:
            _pools.add(self)
            if _reaper is None:
                _reaper=threading.Thread(target=_reap,name='arena-jvm-idle-reaper',daemon=True);_reaper.start()

    def __del__(self):
        try:self.close()
        except Exception:pass  # Interpreter shutdown may already have torn down imports.

    def prune(self):
        with self.lock:
            expired=[worker for worker in self.idle if time.monotonic()-worker.used>30]
            self.idle=[worker for worker in self.idle if worker not in expired]
            for worker in expired:self.all.discard(worker)
        for worker in expired:worker.close()

    def close(self):
        with self.lock:workers=list(self.all);self.all.clear();self.idle.clear()
        for worker in workers:worker.close()

    def run(self, work, mode, argument, timings):
        from .engine import stop_worker
        from .worker_resources import process_cpu_seconds
        from .fight_phases import phase
        started=time.monotonic();deadline=started+self.engine.timeout;worker=None;reuse=False
        with self.lock:
            while self.idle:
                candidate=self.idle.pop()
                if candidate.process.poll() is None:worker=candidate;reuse=True;break
                self.all.discard(candidate);candidate.close()
        try:
            if worker is None:
                phase('starting_jvm');worker=Worker(self.engine)
                with self.lock:self.all.add(worker)
                if not worker.wait('READY',deadline,work,self.engine.timeout):
                    from .worker_resources import log_tail
                    raise OSError('Persistent JVM exited during startup: '+log_tail(worker.root/'worker-startup.log'))
            timings['jvm_reused']=reuse;timings['jvm_pid']=worker.process.pid
            timings['jvm_slot_preparation_seconds']=time.monotonic()-started
            before=process_cpu_seconds(worker.process)
            phase('engine');command=[mode,argument,str(work.resolve())]
            worker.process.stdin.write(('\t'.join(base64.b64encode(value.encode()).decode() for value in command)+'\n').encode());worker.process.stdin.flush()
            completed=worker.wait('DONE',deadline,work,self.engine.timeout)
            if not completed:
                worker.process.wait()
                if (worker.root/'outcome.json').is_file():shutil.copyfile(worker.root/'outcome.json',work/'outcome.json')
            worker.jobs+=1
            return 0 if completed else worker.process.returncode
        finally:
            timings['java_process_seconds']=time.monotonic()-started
            if worker is not None:
                if sys.exc_info()[0] is not None:
                    stop_worker(worker.process)
                    if not (work/'stderr.log').is_file():
                        from .worker_resources import log_tail
                        (work/'stderr.log').write_text(log_tail(worker.root/'worker-startup.log'),encoding='utf-8')
                after=process_cpu_seconds(worker.process)
                if after is not None and 'before' in locals() and before is not None:timings['java_cpu_seconds']=max(0,after-before)
                if (self.recycle and worker.jobs>=self.recycle) or worker.process.poll() is not None:
                    with self.lock:self.all.discard(worker)
                    worker.close()
                else:
                    worker.used=time.monotonic()
                    with self.lock:self.idle.append(worker)
