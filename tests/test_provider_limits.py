import tempfile
import unittest
from concurrent.futures import Future
from pathlib import Path
from arena.core import write_json
from arena.parallel import Requests
from arena.provider_limits import endpoint
from arena.conversation_recovery import automatic_due


class ProviderLimitTests(unittest.TestCase):
    def test_local_aliases_and_models_share_one_default_slot(self):
        one={'id':'one','provider':'openai-compatible','model':'qwen','endpoint':'http://localhost:11434/v1/chat/completions'}
        two={**one,'id':'two','endpoint':'http://127.0.0.1:11434/v1/responses'}
        self.assertEqual(endpoint(one),endpoint(two))
        requests=Requests(8,[('one',one),('two',two)])
        try:
            requests.pending['one']={'model':one,'future':Future()}
            self.assertFalse(requests.can_start('two',two))
            remote={**two,'endpoint':'https://example.org/v1/chat/completions'}
            self.assertTrue(requests.can_start('remote',remote))
        finally:requests.pool.shutdown()

    def test_live_limit_can_be_raised_without_restarting(self):
        model={'id':'one','provider':'openai-compatible','model':'qwen','endpoint':'http://localhost:11434/v1/chat/completions'}
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);requests=Requests(8,out=root)
            try:
                requests.pending['one']={'model':model,'future':Future()}
                self.assertFalse(requests.can_start('two',model))
                write_json(root/'provider-control.json',{'endpoint_limits':{endpoint(model):2}})
                requests.limits_checked=0
                self.assertTrue(requests.can_start('two',model))
            finally:requests.pool.shutdown()

    def test_pausing_automatic_retry_does_not_change_counters(self):
        state={'status':'provider_unavailable','automatic_retries_paused':True,'calls':5,'steps':8,
               'failure':{'retryable':True,'at':100}}
        self.assertIsNone(automatic_due(state,{'budget_per_session':{}}))
        self.assertEqual((state['calls'],state['steps']),(5,8))
