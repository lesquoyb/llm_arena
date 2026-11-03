import unittest
from unittest import mock
from arena.core import ROOT, scratch_directory
from arena.experiment import Journal, load_config, run
from arena_web.data import Store
from arena_web.jobs import Jobs
from arena_web.provider_probe import probe


@unittest.skipUnless((ROOT/'.arena/engine.json').exists(),'Build engine')
class ProviderProbeTests(unittest.TestCase):
    def test_probe_is_accounted_and_never_executes_returned_tools(self):
        with scratch_directory() as tmp:
            store=Store(tmp/'runs',tmp/'ui');root=store.runs/'probe'
            config=load_config(ROOT/'configs/offline-demo.json')
            config.update(replicates=1,spending={'allow_paid_calls':True})
            config['models']=[{'id':'target','provider':'openai-compatible','model':'gpt-6.1-sol',
                'endpoint':'http://127.0.0.1:11434/v1/responses','api_key_env':'ARENA_PROBE_TEST',
                'parameters':{'reasoning_effort':'low'},'pricing':{'date':'2026-10-19','currency':'USD','input_per_million':'1','output_per_million':'2'}}]
            run(config,root,prepare_only=True)
            journal=Journal(root)
            try:
                state=journal.state('target-r0');history=state['history']
                state.update(status='provider_unavailable',failure={'message':'Bad Request'})
                journal.save('target-r0',state,'provider_failure',{'error':'Bad Request'})
            finally:journal.db.close()
            jobs=Jobs(store)
            response={'id':'probe','status':'completed','output':[{'type':'function_call','name':'arena_probe','call_id':'probe-call','arguments':'{"value":"ok"}'}],
                      'usage':{'input_tokens':100,'output_tokens':20,'input_tokens_details':{'cached_tokens':0}}}
            with mock.patch('arena_web.provider_probe.http_json',return_value=(response,'request-id')) as transport:
                result=probe(jobs,'probe','target-r0','minimal',True)
            self.assertTrue(result['accepted'])
            sent=transport.call_args.args[1]
            self.assertEqual(sent['max_output_tokens'],1024)
            self.assertNotIn('include',sent)
            self.assertEqual(len(sent['tools']),1)
            state=store.session('probe','target-r0')
            self.assertEqual(state['history'],history)
            self.assertEqual(state['status'],'provider_unavailable')
            self.assertEqual(state['diagnostic_calls'],1)
            self.assertEqual(state['calls'],1)
            self.assertGreater(float(state['cost_spent']),0)
            self.assertEqual(state['cost_spent'],state['diagnostic_cost_usd'])
            self.assertFalse(list((root/'sessions/target-r0').glob('workspace/*')))
            self.assertTrue(store.provider_diagnostics('probe','target-r0')['api_tests'])
