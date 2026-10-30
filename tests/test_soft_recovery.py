"""Transient failures recover without losing history or overrunning retry limits."""
import unittest
from unittest import mock
from arena.core import scratch_directory, write_json, read_json
from arena.experiment import Journal, initial_state
from arena.conversation_recovery import commands
from arena.conversation_recovery import automatic_due


class SoftRecoveryTests(unittest.TestCase):
    def test_live_pause_is_consumed_without_waiting_for_a_provider_reply(self):
        from test_parallel_requests import config,CoordinatorEngine
        from arena.parallel import prepare
        from arena.provider_watchdog import request_control
        value=config();value['models']=value['models'][:1]
        model=value['models'][0];sid='one-r0'
        def respond(*args):
            control=request_control.get()
            if not control.cancelled.wait(3):raise RuntimeError('Pause did not cancel transport')
            control.check()
        with scratch_directory() as root:
            journal=Journal(root)
            def progress():
                if journal.requests.pending:
                    write_json(root/'recovery-commands'/'pause.json',{'id':'pause','session':sid,'action':'pause'})
            try:
                with mock.patch('arena.api_providers.APIProvider.respond',new=respond):
                    prepare([(sid,model)],value,root,journal,CoordinatorEngine(),on_progress=progress)
                state=journal.state(sid)
                self.assertTrue(state['conversation_paused'])
                self.assertFalse(state['in_flight'])
                self.assertEqual(state['failure']['diagnostics']['network_error'],'conversation_paused')
                journal.verify()
            finally:journal.db.close()

    def test_completed_text_without_submission_is_retried_after_two_minutes(self):
        state={'status':'no_submission','failure':{'phase':'submission','at':100,'retryable':False}}
        self.assertEqual(automatic_due(state,{'budget_per_session':{}}),220)
        state['automatic_retry_attempts']=3
        self.assertIsNone(automatic_due(state,{'budget_per_session':{}}))

    def test_manual_pause_and_budget_exhaustion_prevent_automatic_requests(self):
        state={'status':'provider_unavailable','failure':{'retryable':True,'at':100},'conversation_paused':True}
        self.assertIsNone(automatic_due(state,{'budget_per_session':{}}))
        state.pop('conversation_paused');state['completed_calls']=5
        self.assertIsNone(automatic_due(state,{'budget_per_session':{'max_calls':5}}))

    def test_pause_cancels_only_its_transport_and_resume_keeps_pending_tools(self):
        from test_parallel_requests import config
        value=config();model=value['models'][0];sid='one-r0'
        with scratch_directory() as root:
            journal=Journal(root)
            try:
                state=initial_state(sid,model,value)
                state['history'].append({'role':'assistant','content':'working'})
                journal.save(sid,state,'session_created')
                control=mock.Mock()
                path=root/'recovery-commands'/'pause.json'
                write_json(path,{'id':'pause','session':sid,'action':'pause'})
                self.assertEqual(commands(root,journal,value,[(sid,model)],{sid:{'control':control}}),[])
                control.cancel.assert_called_once()
                self.assertTrue(journal.state(sid)['conversation_paused'])
                write_json(path,{'id':'resume','session':sid,'action':'continue','message':'Please submit.'})
                self.assertEqual(commands(root,journal,value,[(sid,model)]),[(sid,model)])
                resumed=journal.state(sid)
                self.assertFalse(resumed['conversation_paused'])
                self.assertEqual(resumed['history'],state['history'])
                self.assertEqual(resumed['resume_message_pending'],'Please submit.')
                journal.verify()
            finally:journal.db.close()

    def test_resume_waits_for_active_receipt_instead_of_sending_a_duplicate(self):
        from test_parallel_requests import config
        value=config();model=value['models'][0];sid='one-r0'
        with scratch_directory() as root:
            journal=Journal(root)
            try:
                journal.save(sid,initial_state(sid,model,value),'session_created')
                path=root/'recovery-commands'/'continue.json'
                write_json(path,{'id':'resume','session':sid,'action':'continue','message':'Continue'})
                self.assertEqual(commands(root,journal,value,[(sid,model)],{sid:{}}),[])
                self.assertTrue(path.exists())
                self.assertNotIn('resume_message_pending',journal.state(sid))
            finally:journal.db.close()
