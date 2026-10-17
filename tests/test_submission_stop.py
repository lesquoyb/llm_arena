"""A provider stop is not an explicit submission, even when files already exist."""
from unittest import TestCase, mock

from arena.core import ROOT, scratch_directory
from arena.experiment import Journal, load_config, run_session
from arena.providers import MockProvider


class SubmissionStopTests(TestCase):
    def run_responses(self, responses, check):
        with scratch_directory() as out:
            config = load_config(ROOT/'configs/offline-demo.json')
            config['budget_per_session'] = {}
            journal = Journal(out)
            try:
                with mock.patch.object(MockProvider, 'respond', side_effect=[{'role':'assistant', **response} for response in responses]):
                    run_session('stop-r0', {'id':'stop','provider':'mock','profile':'empty'}, config, out, journal, None)
                state = journal.state('stop-r0')
                check(state)
                journal.verify()
                # Terminal sessions never call the provider again on resume.
                with mock.patch.object(MockProvider, 'respond', side_effect=AssertionError('Unexpected repeated call')):
                    run_session('stop-r0', {'id':'stop','provider':'mock','profile':'empty'}, config, out, journal, None)
            finally:
                journal.db.close()

    def test_stop_after_writing_requires_explicit_submit_and_preserves_reasoning(self):
        responses = [
            {'tool_calls':[{'name':'write_file','arguments':{'path':'main.leek','content':'// strategy'}}]},
            {'tool_calls':[], 'reasoning':'I think I am done.', 'finish_reason':'stop'},
            {'tool_calls':[{'name':'submit','arguments':{}}]},
        ]
        def check(state):
            self.assertEqual(state['status'], 'submitted')
            self.assertEqual(state['calls'], 3)
            self.assertEqual(state['submission_reminders'], 1)
            assistant = [m for m in state['history'] if m['role']=='assistant']
            self.assertEqual(assistant[1]['reasoning'], 'I think I am done.')
            self.assertEqual(assistant[2]['tool_calls'][0]['name'], 'submit')
            self.assertTrue(any(m['role']=='user' and 'not submitted' in m.get('content','') for m in state['history']))
        self.run_responses(responses, check)

    def test_repeated_stops_never_implicitly_submit_existing_files(self):
        responses = [{'tool_calls':[{'name':'write_file','arguments':{'path':'main.leek','content':'// strategy'}}]}]
        responses += [{'tool_calls':[], 'finish_reason':'stop'} for _ in range(4)]
        def check(state):
            self.assertEqual(state['status'], 'no_submission')
            self.assertNotIn('submission', state)
            self.assertEqual(state['submission_reminders'], 3)
            self.assertIn('three reminders', state['failure']['message'])
            self.assertIn('Arena stopped', state['history'][-1]['content'])
        self.run_responses(responses, check)

    def test_interrupted_response_resumes_with_one_reminder_and_no_repeated_call(self):
        with scratch_directory() as out:
            config = load_config(ROOT/'configs/offline-demo.json')
            config['budget_per_session'] = {}
            model = {'id':'stop','provider':'mock','profile':'empty'}
            journal = Journal(out)
            try:
                def interrupt(kind, sid):
                    if kind == 'response':
                        raise KeyboardInterrupt
                with mock.patch.object(MockProvider, 'respond', return_value={'role':'assistant','tool_calls':[], 'stop_reason':'stop'}):
                    with self.assertRaises(KeyboardInterrupt):
                        run_session('stop-r0', model, config, out, journal, None, interrupt)
                responses = [
                    {'role':'assistant','tool_calls':[{'name':'write_file','arguments':{'path':'main.leek','content':'// resumed'}}]},
                    {'role':'assistant','tool_calls':[{'name':'submit','arguments':{}}]},
                ]
                with mock.patch.object(MockProvider, 'respond', side_effect=responses) as respond:
                    run_session('stop-r0', model, config, out, journal, None)
                state = journal.state('stop-r0')
                self.assertEqual(state['status'], 'submitted')
                self.assertEqual(respond.call_count, 2)
                self.assertEqual(state['calls'], 3)
                self.assertEqual(state['submission_reminders'], 1)
                self.assertEqual(sum(m.get('role')=='user' and 'Reminder 1 of 3' in m.get('content','') for m in state['history']), 1)
                journal.verify()
            finally:
                journal.db.close()
