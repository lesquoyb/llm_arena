"""Transport recovery cannot accumulate model-stop submission penalties."""
from contextlib import closing
from unittest import TestCase,mock
from arena.api_providers import ProviderFailure
from arena.core import ROOT,read_json,scratch_directory
from arena.experiment import Journal,run_session
from arena.providers import MockProvider
from arena.retries import prepare_retry
from arena.submission_stops import completed_turn


class SubmissionStopTransportTests(TestCase):
    def test_only_explicit_completed_turns_are_counted(self):
        for reason in ('stop','end_turn','completed','STOP','end','stop_sequence'):
            self.assertTrue(completed_turn({'stop_reason':reason}))
        for reason in (None,'length','max_tokens','max_output_tokens','error','tool_calls'):
            self.assertFalse(completed_turn({'stop_reason':reason}))

    def test_timeout_preserves_streak_and_retry_uses_a_neutral_notice(self):
        with scratch_directory() as out:
            config=read_json(ROOT/'configs/offline-demo.json');config['budget_per_session']={}
            model={'id':'stop','provider':'mock','profile':'empty'}
            journal=Journal(out)
            with closing(journal.db):
                write={'role':'assistant','tool_calls':[{'name':'write_file','arguments':{'path':'main.leek','content':'// saved'}}]}
                stop={'role':'assistant','stop_reason':'stop','tool_calls':[]}
                with mock.patch.object(MockProvider,'respond',side_effect=[write,stop,ProviderFailure('backend timeout',uncertain=False,retryable=True)]):
                    run_session('stop-r0',model,config,out,journal,None)
                state=journal.state('stop-r0')
                self.assertEqual(state['status'],'provider_unavailable')
                self.assertEqual(state['submission_reminders'],1)
                self.assertEqual(state['consecutive_submission_reminders'],1)
                self.assertNotIn('submission',state)
                before={key:state.get(key) for key in ('calls','completed_calls','steps','wall_seconds','input_tokens','output_tokens','cost_spent','submission_reminders','consecutive_submission_reminders')}
                state=prepare_retry(journal,'stop-r0',config)
                self.assertEqual({key:state.get(key) for key in before},before)
                self.assertTrue(state['history'][-1]['provider_recovery'])
                self.assertNotIn('Reminder',state['history'][-1]['content'])
                submit={'role':'assistant','tool_calls':[{'name':'submit','arguments':{}}]}
                with mock.patch.object(MockProvider,'respond',side_effect=[stop,submit]):
                    run_session('stop-r0',model,config,out,journal,None)
                state=journal.state('stop-r0')
                self.assertEqual(state['status'],'submitted')
                self.assertEqual(state['submission_reminders'],2)
                self.assertFalse(state.get('automatic_submission'))
                reminders=[m for m in state['history'] if m.get('submission_reminder')]
                self.assertEqual(len(reminders),2)
                self.assertIn('Reminder 1 of 3',reminders[0]['content'])
                self.assertIn('Reminder 2 of 3',reminders[1]['content'])
                self.assertTrue(all('not a reviewer' not in m['content'] for m in reminders))
                journal.verify()

    def test_incomplete_response_does_not_freeze_saved_files(self):
        for reason in (None,'length','max_tokens'):
            with self.subTest(reason=reason),scratch_directory() as out:
                config=read_json(ROOT/'configs/offline-demo.json');config['budget_per_session']={}
                journal=Journal(out)
                with closing(journal.db):
                    responses=[{'role':'assistant','tool_calls':[{'name':'write_file','arguments':{'path':'main.leek','content':'// saved'}}]},
                               {'role':'assistant','tool_calls':[],'stop_reason':reason}]
                    with mock.patch.object(MockProvider,'respond',side_effect=responses):
                        run_session('stop-r0',{'id':'stop','provider':'mock','profile':'empty'},config,out,journal,None)
                    state=journal.state('stop-r0')
                    self.assertEqual(state['status'],'provider_unavailable')
                    self.assertEqual(state.get('submission_reminders',0),0)
                    self.assertNotIn('submission',state)
                    self.assertEqual(state['completed_calls'],2)
                    journal.verify()

    def test_previous_reset_marker_restores_saved_streak_without_changing_other_counts(self):
        from arena.submission_stops import restore_interrupted_streak
        state={'consecutive_submission_reminders':0,'submission_reminders':4,'interrupted_stop_streak':2,'calls':10,'steps':7}
        self.assertEqual(restore_interrupted_streak(state)['restored'],2)
        self.assertEqual(state,{'consecutive_submission_reminders':2,'submission_reminders':4,'calls':10,'steps':7})
        self.assertIsNone(restore_interrupted_streak(state))
