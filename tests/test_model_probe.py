from unittest import TestCase,mock
from arena.core import scratch_directory,read_json
from arena_web.data import Store
from arena_web.model_probe import probe_model
from arena.api_providers import APIProvider,ProviderFailure


def model():
    return {'id':'fixture','provider':'openai-compatible','model':'fixture','endpoint':'http://localhost:11434/v1/chat/completions',
            'api_key_env':'ARENA_PROBE_FIXTURE','parameters':{'temperature':.2},
            'pricing':{'date':'2026-10-27','currency':'USD','input_per_million':'0','output_per_million':'0'}}


class ModelProbeTests(TestCase):
    def test_small_request_receipts_and_session_keys_do_not_leak(self):
        with scratch_directory() as root:
            store=Store(root/'runs',root/'settings')
            answer={'usage':{'input_tokens':10,'output_tokens':2},'cost_usd':'0','tool_calls':[]}
            for mode,cap in [('text',16),('tools',128)]:
                with mock.patch('arena_web.model_probe.APIProvider') as provider:
                    provider.return_value.respond.return_value=answer
                    result=probe_model(store,model(),mode,'fixture-secret')
                    self.assertTrue(result['accepted'])
                    self.assertEqual(provider.return_value.respond.call_args.args[-1],cap)
                    self.assertEqual(provider.return_value.respond.call_args.kwargs['key_override'],'fixture-secret')
                    self.assertEqual(provider.call_args.args[0]['max_retries'],0)
                    self.assertEqual(provider.call_args.args[0]['parameters'],{} if mode=='text' else {'temperature':.2})
            receipts=list((store.state/'model-probes').glob('*.json'))
            self.assertEqual(len(receipts),2)
            self.assertTrue(all('fixture-secret' not in path.read_text() for path in receipts))

    def test_failed_probe_is_saved_without_assuming_zero_cost(self):
        with scratch_directory() as root:
            store=Store(root/'runs',root/'settings')
            with mock.patch('arena_web.model_probe.APIProvider.respond',side_effect=ProviderFailure('Rate limited',retryable=True)):
                result=probe_model(store,model())
            self.assertFalse(result['accepted'])
            self.assertIsNone(result['cost_usd'])
            self.assertTrue(result['retryable'])
            self.assertEqual(read_json(next((store.state/'model-probes').glob('*.json')))['error'],'Rate limited')

    def test_mistral_uses_its_supported_output_cap_field(self):
        spec={**model(),'endpoint':'https://api.mistral.ai/v1/chat/completions'}
        payload=APIProvider(spec).payload([{'role':'user','content':'OK'}],[],16)
        self.assertEqual(payload['max_tokens'],16)
        self.assertNotIn('max_completion_tokens',payload)
