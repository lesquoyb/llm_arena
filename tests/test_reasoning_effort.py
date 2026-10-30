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

    def test_rejected_frozen_effort_can_be_overridden_for_one_retry(self):
        from arena.core import ArenaError, scratch_directory
        from arena.experiment import Journal
        from arena.reasoning import validate_effort, apply_overrides
        from arena.retries import prepare_retry
        model={'id':'test','provider':'openai','model':'gpt-6.1-sol','parameters':{'reasoning_effort':'none'}}
        for value in ('none','minimal'):
            with self.assertRaises(ArenaError):validate_effort(model,value)
        with scratch_directory() as tmp:
            journal=Journal(tmp)
            try:
                original={'model':'test','status':'provider_unavailable','history':[],'calls':2,'pending':None}
                journal.save('test-r0',original,'fixture')
                state=prepare_retry(journal,'test-r0',{'models':[model],'budget_per_session':{}},'low')
                effective=apply_overrides(model,state)
                self.assertEqual(effective['parameters']['reasoning_effort'],'low')
                self.assertEqual(model['parameters']['reasoning_effort'],'none')
                self.assertEqual(state['calls'],2)
                self.assertEqual(APIProvider(effective).payload([],[],None)['reasoning'],{'effort':'low'})
                journal.verify()
            finally:journal.db.close()
