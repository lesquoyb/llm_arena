"""Failed provider attempts do not consume the completed-response call budget."""
from unittest import TestCase, mock
from arena.core import ROOT,read_json,scratch_directory
from arena.experiment import Journal,run_session
from arena.api_providers import ProviderFailure
from arena.budget_context import progress
from arena.call_counts import completed_calls


class CallCountTests(TestCase):
    def test_unreachable_provider_can_retry_with_one_response_budget(self):
        model={'id':'fixture','provider':'openai-compatible','model':'fixture','endpoint':'http://localhost:11434/v1/chat/completions',
               'api_key_env':'ARENA_FIXTURE','pricing':{'date':'2026-10-27','currency':'USD','input_per_million':'0','output_per_million':'0'}}
        config=read_json(ROOT/'configs/offline-demo.json')
        config.update(models=[model],spending={'allow_paid_calls':True},budget_per_session={'max_calls':1})
        answer={'role':'assistant','tool_calls':[{'name':'write_file','arguments':{'path':'main.leek','content':'// fixture'}},
                                               {'name':'submit','arguments':{}}],
                'usage':{'input_tokens':10,'output_tokens':10},'cost_usd':'0'}
        with scratch_directory() as root:
            journal=Journal(root)
            try:
                with mock.patch('arena.experiment.APIProvider.respond',side_effect=ProviderFailure('Connection refused')):
                    run_session('fixture-r0',model,config,root,journal,None)
                state=journal.state('fixture-r0')
                self.assertEqual((state['calls'],state['completed_calls']),(1,0))
                self.assertEqual(progress(state,config['budget_per_session'])['limits']['calls']['remaining'],1)
                state['status']='running';journal.save('fixture-r0',state,'retry')
                with mock.patch('arena.experiment.APIProvider.respond',return_value=answer):
                    run_session('fixture-r0',model,config,root,journal,None)
                state=journal.state('fixture-r0')
                self.assertEqual(state['status'],'submitted')
                self.assertEqual((state['calls'],state['completed_calls']),(2,1))
                journal.verify()
            finally:journal.db.close()

    def test_legacy_counts_are_reconstructed_from_own_receipts(self):
        with scratch_directory() as root:
            journal=Journal(root)
            try:
                state={'calls':1,'history':[]}
                journal.save('fixture',state,'provider_failure')
                self.assertEqual(completed_calls(state,journal.db,'fixture'),0)
                journal.save('fixture',state,'model_response',{'role':'assistant','content':'receipt'})
                self.assertEqual(completed_calls(state,journal.db,'fixture'),1)
                self.assertNotIn('completed_calls',journal.state('fixture'))
            finally:journal.db.close()
