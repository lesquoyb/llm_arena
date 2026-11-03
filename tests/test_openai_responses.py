import copy
import unittest
from arena.api_providers import APIProvider, connection, request_snapshot
from arena.tool_schemas import TOOLS
from arena_web.provider_output import blocks, preview


class ResponsesTests(unittest.TestCase):
    def model(self):
        return {'id':'test','provider':'openai-compatible','model':'gpt-6.1-sol',
                'endpoint':'http://127.0.0.1:11434/v1/chat/completions','api_key_env':'ARENA_RESPONSES_TEST',
                'parameters':{'reasoning_effort':'high','seed':0},
                'pricing':{'input_per_million':'1','output_per_million':'2'}}

    def test_effort_and_tools_use_responses_with_exact_stateless_continuation(self):
        model=self.model();requests=[]
        reasoning={'type':'reasoning','id':'rs_1','summary':[{'type':'summary_text','text':'Inspect files'}],
                   'encrypted_content':'opaque'}
        call={'type':'function_call','id':'fc_1','call_id':'call_1','name':'list_files','arguments':'{}'}
        def transport(url,payload,headers,timeout):
            requests.append(copy.deepcopy(payload))
            self.assertTrue(url.endswith('/responses'))
            output=[reasoning,call] if len(requests)==1 else [{'type':'message','role':'assistant','content':[{'type':'output_text','text':'Done'}]}]
            return {'output':output,'status':'completed','usage':{'input_tokens':100,'output_tokens':20,
                'input_tokens_details':{'cached_tokens':10},'output_tokens_details':{'reasoning_tokens':5}}},'request-id'
        provider=APIProvider(model,transport)
        history=[{'role':'user','content':'Inspect files'}]
        first=provider.respond(history,TOOLS,1000)
        history.extend([first,{'role':'tool','name':'list_files','provider_call_id':'call_1','result':{'files':[]}}])
        second=provider.respond(history,TOOLS,1000)
        self.assertEqual(first['tool_calls'],[{'id':'call_1','name':'list_files','arguments':{}}])
        self.assertEqual(requests[0]['reasoning'],{'effort':'high'})
        self.assertEqual(requests[0]['tools'][0]['type'],'function')
        self.assertFalse(requests[0]['store'])
        self.assertNotIn('previous_response_id',requests[1])
        self.assertIn(reasoning,requests[1]['input'])
        self.assertIn({'type':'function_call_output','call_id':'call_1','output':'{"files":[]}'},requests[1]['input'])
        self.assertNotIn('seed',requests[0])
        self.assertTrue(first['adapter_notes'])
        self.assertEqual(first['usage']['reasoning_tokens'],5)
        self.assertEqual(first['usage']['input_tokens'],100)
        self.assertEqual(first['usage']['output_tokens'],20)
        self.assertEqual(preview(second)['output_text'],'Done')
        self.assertTrue(any(b['kind']=='opaque' for b in blocks(first)))
        self.assertEqual(request_snapshot(model,history,TOOLS,1000)['body']['reasoning'],{'effort':'high'})

    def test_explicit_none_keeps_chat_and_explicit_responses_supports_other_models(self):
        model=self.model();model['parameters']['reasoning_effort']='none'
        self.assertTrue(connection(model,None)[0].endswith('/chat/completions'))
        self.assertIn('messages',APIProvider(model).payload([],TOOLS,None))
        model.update(model='other-model',endpoint='http://127.0.0.1:11434/v1/responses')
        self.assertIn('input',APIProvider(model).payload([],TOOLS,None))
