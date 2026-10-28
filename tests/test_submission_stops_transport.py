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

    def test_timeout_resets_streak_and_retry_uses_a_neutral_notice(self):
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
                self.assertEqual(state['consecutive_submission_reminders'],0)
                self.assertNotIn('submission',state)
                state=prepare_retry(journal,'stop-r0',config)
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
                self.assertTrue(all('Reminder 1 of 3' in m['content'] for m in reminders))
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
