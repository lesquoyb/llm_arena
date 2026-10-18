import unittest
from arena.api_providers import APIProvider, request_snapshot


class ReasoningEffortTests(unittest.TestCase):
    def test_default_is_omitted_and_explicit_levels_reach_the_exact_request(self):
        history=[{'role':'user','content':'Compile a strategy.'}]
        for provider in ('openai','openai-compatible'):
            model={'id':'test','provider':provider,'model':'target','api_key_env':'ARENA_TEST_REASONING',
                   'endpoint':'http://127.0.0.1:11434/v1/chat/completions','parameters':{}}
            self.assertNotIn('reasoning_effort',APIProvider(model).payload(history,[],None))
            for effort in ('none','minimal','low','medium','high','xhigh','custom-endpoint-level'):
                selected={**model,'parameters':{'reasoning_effort':effort}}
                self.assertEqual(APIProvider(selected).payload(history,[],None)['reasoning_effort'],effort)
                self.assertEqual(request_snapshot(selected,history,[],None)['body']['reasoning_effort'],effort)
