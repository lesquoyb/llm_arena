"""Recovery keeps receipts, counters and game-engine boundaries intact."""
import unittest
from contextlib import closing
from arena.core import ArenaError, scratch_directory
from arena.experiment import Journal
from arena.recovery import reconcile, engine_compatible, resume_compatible, needs_reconciliation


class RecoveryTests(unittest.TestCase):
    def test_application_updates_do_not_admit_changed_game_engines_or_settings(self):
        before = {'config':{'scenario':1}, 'engine':{'lock':'game-v1','runner_sha256':'old'},
                  'corpus_sha256':'old'}
        after = {**before, 'engine':{**before['engine'], 'runner_sha256':'new'}, 'corpus_sha256':'new'}
        self.assertTrue(resume_compatible(before, after))
        self.assertFalse(resume_compatible(before, {**after, 'config':{'scenario':2}}))
        self.assertFalse(engine_compatible(before['engine'], {**after['engine'], 'lock':'game-v2'}))

    def test_added_worker_transport_preserves_compatibility_only_for_same_adapter(self):
        before={'lock':'pinned','adapter_sha256':'adapter','jar_sha256':'jar',
                'build_script_sha256':'overlay','bridge_sha256':'old'}
        after={**before,'bridge_sha256':'with-worker','worker_execution':'pooled-classloader'}
        self.assertTrue(engine_compatible(before,after))
        for key in ('adapter_sha256','jar_sha256','build_script_sha256','lock'):
            self.assertFalse(engine_compatible(before,{**after,key:'changed'}))

    def test_reconciliation_preserves_received_response_and_is_not_charged_twice(self):
        with scratch_directory() as tmp:
            journal = Journal(tmp)
            with closing(journal.db):
                state = {'status':'needs_reconciliation', 'history':[{'role':'assistant'}],
                         'pending':{'tool_calls':[{'name':'submit'}]}, 'cursor':0,
                         'submission_reminders':3,'consecutive_submission_reminders':2,'calls':4, 'input_tokens':123, 'cost_spent':'1', 'money_reserved':'2', 'in_flight':False}
                journal.save('model-r0', state, 'fixture')
                journal.save('child', {'parent':'model-r0', 'status':'no_submission', 'calls':0}, 'fixture')
                recovered = reconcile(journal, 'model-r0', '.25', 'Checked provider dashboard')
                self.assertEqual(recovered['cost_spent'], '1.25')
                self.assertEqual(recovered['pending'], state['pending'])
                self.assertEqual(recovered['history'], state['history'])
                self.assertEqual(recovered['calls'], 4)
                self.assertEqual(recovered['input_tokens'], 123)
                self.assertEqual(recovered['submission_reminders'],3)
                self.assertEqual(recovered['consecutive_submission_reminders'],2)
                self.assertEqual(recovered['status'], 'running')
                self.assertEqual(recovered['retry_count'], 1)
                self.assertTrue(journal.state('child')['retry_parent_refresh'])
                self.assertFalse(needs_reconciliation(recovered))
                with self.assertRaises(ArenaError):
                    reconcile(journal, 'model-r0', '.25', 'Again')
                journal.verify()

    def test_unknown_response_can_be_retried_after_recording_the_charge(self):
        with scratch_directory() as tmp:
            journal = Journal(tmp)
            with closing(journal.db):
                state = {'status':'running', 'in_flight':True, 'pending':None, 'calls':1, 'history':[]}
                journal.save('model-r0', state, 'fixture')
                self.assertTrue(needs_reconciliation(state))
                self.assertFalse(needs_reconciliation(state, external=False))
                recovered = reconcile(journal, 'model-r0', 0, 'Confirmed uncharged')
                self.assertEqual(recovered['status'], 'provider_unavailable')
                self.assertEqual(recovered['calls'], 1)
                self.assertFalse(recovered['in_flight'])
