"""Web control commands remain queued; only the runner edits checkpoints."""
import unittest
from unittest import mock
from arena.core import ArenaError,scratch_directory,write_json,read_json
from arena.experiment import Journal,initial_state
from arena_web.data import Store
from arena_web.jobs import Jobs
from test_parallel_requests import config


class ConversationControlTests(unittest.TestCase):
    def exercise(self, action, *, live, message=None):
        with scratch_directory() as root:
            store=Store(root/'runs',root/'ui');out=store.runs/'run';out.mkdir()
            value=config();value['spending']['max_total_usd']='1'
            write_json(out/'experiment.json',{'config':value})
            journal=Journal(out)
            try:
                state=initial_state('one-r0',value['models'][0],value)
                state.update(in_flight=live,conversation_paused=not live)
                journal.save('one-r0',state,'session_created')
                jobs=Jobs(store)
                if live:
                    jobs.process=mock.Mock();jobs.process.poll.return_value=None
                    jobs.current={'run':'run','status':'running'}
                with mock.patch.object(jobs,'launch') as launch:
                    result=jobs.recover_conversation('run','one-r0',action,message)
                    command=read_json(out/'recovery-commands'/(result['id']+'.json'))
                    self.assertEqual(command['action'],action)
                    self.assertEqual(command['message'],message)
                    self.assertEqual(journal.state('one-r0'),state)
                    if not live and action!='pause':
                        self.assertEqual(launch.call_args.kwargs['ceiling'],'1')
                    else:launch.assert_not_called()
            finally:journal.db.close()

    def test_pause_of_a_live_local_request_does_not_stop_the_competition(self):
        self.exercise('pause',live=True)

    def test_message_queues_behind_a_live_request(self):
        self.exercise('continue',live=True,message='Please use the tools and submit.')

    def test_resume_of_stopped_run_keeps_its_spending_ceiling(self):
        self.exercise('continue',live=False,message='Continue.')

    def test_invalid_messages_are_rejected_before_enqueuing(self):
        jobs=Jobs.__new__(Jobs)
        for message in (['not text'],'x'*12001):
            with self.assertRaises(ArenaError):jobs.recover_conversation('run','one','continue',message)
