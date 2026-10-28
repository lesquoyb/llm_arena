"""Context rejection recovery preserves the session and has a finite retry path."""
import copy
import unittest
from arena.context_recovery import recover_automatically


class AutomaticContextRecoveryTests(unittest.TestCase):
    def state(self):
        return {'status':'provider_unavailable','in_flight':False,'calls':8,'completed_calls':6,'steps':12,
                'cost_spent':'0.4','input_tokens':10000,'workspace_files':{'main.leek':'saved-hash'},
                'history':[{'role':'user','content':'Round 3 with feedback','scenario':{'fixed':True}},
                           {'role':'assistant','content':'Preparing strategy'},
                           {'role':'tool','name':'read_docs','result':{'content':'long documentation'}}],
                'failure':{'message':'Provider HTTP 400: invalid_request_prompt_too_long · code: 3059 · Prompt 256870 > 256000 maximum context length'}}

    def test_automatic_rebase_preserves_files_history_and_usage(self):
        state=self.state();before=copy.deepcopy(state)
        result=recover_automatically(state)
        self.assertTrue(result['automatic'])
        self.assertEqual(state['status'],'running')
        self.assertEqual(state['history'][:3],before['history'])
        for key in ('calls','completed_calls','steps','cost_spent','input_tokens','workspace_files'):
            self.assertEqual(state[key],before[key])
        active=state['history'][state['request_history_start']:]
        self.assertEqual(active[0],before['history'][0])
        self.assertEqual([m['role'] for m in active],['user','user'])
        self.assertIn('SAME preparation session',active[-1]['content'])
        self.assertEqual(state['context_recoveries'],1)
        state.update(status='provider_unavailable',failure=before['failure'])
        self.assertIsNone(recover_automatically(state))
        self.assertEqual(state['context_recoveries'],1)

    def test_uncertain_or_irreducible_requests_are_not_repeated(self):
        state=self.state();state['in_flight']=True
        self.assertIsNone(recover_automatically(state))
        state=self.state();state['history']=state['history'][:1]
        self.assertIsNone(recover_automatically(state))
        state=self.state();state['failure']={'message':'HTTP 429 quota exceeded'}
        self.assertIsNone(recover_automatically(state))
