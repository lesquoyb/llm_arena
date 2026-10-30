"""Engine dispatch commands do not require resuming provider conversations."""
import threading
import unittest
from unittest import mock
from types import SimpleNamespace
from arena.core import scratch_directory,write_json,read_json,submission
from arena.experiment import Journal,initial_state
from arena.submission_validation import SubmissionValidator
from arena_web.jobs import Jobs
from arena.fight_recovery import run
from test_parallel_requests import config


class RemainingFightsTests(unittest.TestCase):
    def test_live_force_command_is_queued_without_model_launch(self):
        with scratch_directory() as root:
            write_json(root/'experiment.json',{'config':{}})
            jobs=Jobs.__new__(Jobs);jobs.lock=threading.RLock();jobs.store=mock.Mock();jobs.store.run_path.return_value=root
            jobs.process=mock.Mock();jobs.process.poll.return_value=None;jobs.current={'run':'r','status':'running'}
            with mock.patch.object(jobs,'launch',side_effect=AssertionError('Model launch')):
                result=jobs.retry_fights('r',include_ready=True)
            self.assertTrue(result['no_model_requests'])
            commands=list((root/'fight-retry-requests').glob('*.json'))
            self.assertTrue(read_json(commands[0])['include_ready'])

    def test_ready_submissions_are_admitted_before_retrying_old_manifests(self):
        with scratch_directory() as root:
            write_json(root/'experiment.json',{'config':{},'engine':{}})
            journal=SimpleNamespace(out=root,metadata=lambda:{'s':{'model':'m','generation':3,'submission':{'sha256':'frozen'}}},record=mock.Mock(),states=lambda:{})
            engine=SimpleNamespace(identity={})
            with mock.patch('arena.fight_recovery.engine_compatible',return_value=True),mock.patch('arena.greedy.evaluate',return_value={'pending':1,'failed':0}) as evaluate:
                result=run(root,engine=engine,journal=journal,include_ready=True)
            self.assertTrue(result['deferred']);self.assertTrue(result['no_model_requests'])
            self.assertEqual(evaluate.call_args.args[-1],3)
            self.assertTrue(evaluate.call_args.kwargs['final'])

    def test_frozen_submission_is_validated_without_waiting_for_other_conversations(self):
        with scratch_directory() as root:
            value=config();journal=Journal(root);sid='one-r0'
            folder=root/'sessions'/sid/'submission';folder.mkdir(parents=True);(folder/'main.leek').write_text('var a=1;')
            state=initial_state(sid,value['models'][0],value);state.update(status='submitted',submission=submission(folder))
            journal.save(sid,state,'session_checkpoint')
            ready=threading.Event()
            class Engine:
                def analyze(self,*args):ready.set();return {'status':'valid'}
            worker=SubmissionValidator(root,Engine(),[sid]);worker.thread.start()
            try:
                self.assertTrue(ready.wait(3));worker.close()
                self.assertIsNone(worker.error)
                self.assertEqual(journal.state(sid)['validity'],'valid')
                self.assertEqual(journal.state(sid)['status'],'submitted')
                journal.verify()
            finally:
                if worker.thread.is_alive():worker.close(cancel=True)
                journal.db.close()
