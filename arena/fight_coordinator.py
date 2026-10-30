"""Own engine scheduling/publication on a thread independent of conversations."""
import copy
import threading


class FightCoordinator:
    def __init__(self, out, config, engine, callback=None):
        self.out=out;self.config=copy.deepcopy(config);self.engine=engine;self.callback=callback
        self.wake=threading.Event();self.stop=threading.Event();self.error=None
        self.thread=threading.Thread(target=self.run,name='arena-fight-coordinator',daemon=True)

    def notify(self):
        self.check();self.wake.set()

    def check(self):
        if self.error is not None:raise self.error

    def run(self):
        from .experiment import Journal
        from .execution_control import _journal,poll
        from .activity import _provider_yielder,_activity_name
        from .greedy import evaluate
        journal=None;tokens=[]
        try:
            # SQLite connections and verification caches stay with their owner.
            # This journal only appends engine events; it never edits sessions.
            journal=Journal(self.out)
            tokens=[(_journal,_journal.set(journal)),
                    (_provider_yielder,_provider_yielder.set(lambda:self.stop.is_set() or self.wake.is_set())),
                    (_activity_name,_activity_name.set('engine-activity.json'))]
            print('[arena] Independent fight coordinator started.',flush=True)
            while not self.stop.is_set():
                self.wake.clear()
                poll(self.out,self.config.get('_parallel_fights',self.config.get('parallel_fights',1)))
                if getattr(journal,'_manual_fight_retry_pending',False):
                    from .fight_recovery import run
                    result=run(self.out,engine=self.engine,journal=journal,cooperative=True)
                    if not result.get('deferred'):journal._manual_fight_retry_pending=False
                generations={state.get('generation',0) for state in journal.metadata().values() if state.get('submission')}
                for generation in sorted(generations,reverse=True):
                    if self.stop.is_set():break
                    evaluate(self.engine,self.config,self.out,journal,generation)
                if self.callback and not self.stop.is_set():self.callback(journal)
                self.wake.wait(.5)
        except BaseException as error:
            self.error=error
            import traceback
            traceback.print_exc()
        finally:
            if journal is not None:
                try:journal.verification.flush()
                finally:journal.db.close()
            for variable,token in reversed(tokens):variable.reset(token)
            print('[arena] Independent fight coordinator stopped.',flush=True)

    def __enter__(self):
        self.thread.start();return self

    def __exit__(self,kind,*args):
        self.stop.set();self.wake.set();self.thread.join()
        if kind is None:self.check()
