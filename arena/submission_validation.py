"""Compile frozen submissions independently of providers and fight dispatch."""
import queue
import threading
from .core import ArenaError,read_json,write_json,file_hash,submission


class SubmissionValidator:
    def __init__(self,out,engine,initial=()):
        self.out=out;self.engine=engine;self.queue=queue.Queue();self.seen=set();self.lock=threading.Lock()
        self.stop=threading.Event();self.finish=threading.Event();self.error=None
        self.thread=threading.Thread(target=self.run,name='arena-submission-validator',daemon=True)
        for sid in initial:self.submit(sid)

    def submit(self,sid):
        with self.lock:
            if sid not in self.seen:self.seen.add(sid);self.queue.put(sid)

    def run(self):
        from .experiment import Journal
        from .preparation import Preparation
        from .activity import operation,_activity_name
        journal=None;token=_activity_name.set('validation-activity.json')
        try:
            journal=Journal(self.out)
            while not self.stop.is_set():
                try:sid=self.queue.get(timeout=.1)
                except queue.Empty:
                    if self.finish.is_set():break
                    continue
                state=journal.state(sid)
                if not state or not state.get('submission'):continue
                directory=self.out/'sessions'/sid;cached=directory/'assessment.json'
                with operation(self.out,'validation',participants=[sid],generation=state.get('generation',0)):
                    if cached.is_file():
                        if state.get('assessment_sha256') and file_hash(cached)!=state['assessment_sha256']:raise ArenaError('Submission assessment changed')
                        result=read_json(cached)
                    else:
                        if submission(directory/'submission',state['submission']['entrypoint'])!=state['submission']:raise ArenaError('Archived submission changed')
                        result=self.engine.analyze(directory/'submission',state['submission']['entrypoint'],Preparation._attempt(directory/'assessment'))
                        write_json(cached,result)
                    sha=file_hash(cached)
                    if state.get('validity')!=result['status'] or state.get('assessment_sha256')!=sha:
                        state.update(validity=result['status'],assessment_sha256=sha)
                        journal.save(sid,state,'submission_assessment',result)
                        print(f'[validation] {sid}: {result["status"]}',flush=True)
        except BaseException as error:
            self.error=error
            import traceback
            traceback.print_exc()
        finally:
            if journal is not None:
                try:journal.verification.flush()
                finally:journal.db.close()
            _activity_name.reset(token)

    def close(self,cancel=False):
        if cancel:self.stop.set()
        self.finish.set();self.thread.join()
