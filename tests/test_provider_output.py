import json
import unittest
from arena.core import ArenaError, scratch_directory
from arena.experiment import Journal
from arena_web.data import Store
from arena_web.provider_output import blocks, preview
from test_web import fixture


class ProviderOutputTests(unittest.TestCase):
    def test_anthropic_preserves_thinking_signatures_external_tools_and_unknown_blocks(self):
        parts=[{'type':'text','text':'Answer'}, {'type':'thinking','thinking':'Exposed thinking','signature':'SIGNED'},
               {'type':'redacted_thinking','data':'OPAQUE'},
               {'type':'mcp_tool_use','name':'remote_search','server_name':'external','input':{'q':'test'}},
               {'type':'mcp_tool_result','tool_use_id':'remote-id','content':[{'type':'text','text':'External result'}]},
               {'type':'future_block','payload':{'unknown':'PRESERVE'}}]
        message={'role':'assistant','native':{'role':'assistant','content':parts},'raw':{'content':parts,'stop_reason':'end_turn'}}
        parts_out=blocks(message)
        self.assertEqual([p['value'] for p in parts_out[:-1]],parts)
        self.assertEqual([p['kind'] for p in parts_out],['text','reasoning','opaque','provider_tool','provider_tool','other','raw'])
        listing=preview(message)
        self.assertEqual(listing['output_text'],'Answer')
        self.assertNotIn('SIGNED',json.dumps(listing))
        self.assertNotIn('Exposed thinking',json.dumps(listing))

    def test_reasoning_metadata_and_encryption_are_not_readable_thoughts(self):
        metadata=preview({'role':'assistant','native':{'reasoning':{'effort':'high'}}})
        self.assertFalse(metadata['output_blocks'][0]['readable'])
        self.assertIn('Reasoning data',metadata['output_blocks'][0]['label'])
        redacted=preview({'role':'assistant','native':{'content':[{'type':'redacted_thinking','data':'OPAQUE'}]}})
        self.assertEqual(redacted['output_blocks'][0]['kind'],'opaque')
        self.assertFalse(redacted['output_blocks'][0]['readable'])

    def test_gemini_thoughts_signatures_code_and_all_alternatives_remain_inspectable(self):
        native={'role':'model','parts':[{'thought':True,'text':'Exposed summary','thoughtSignature':'OPAQUE'},
                {'text':'Answer'}, {'functionCall':{'name':'unfamiliar_tool','args':{'x':1}},'thoughtSignature':'SIG'},
                {'executableCode':{'language':'PYTHON','code':'print(1)'}}, {'thoughtSignature':'ONLY_SIGNATURE'}]}
        raw={'candidates':[{'content':native},{'content':{'parts':[{'text':'Alternative answer'}]}}]}
        listing=preview({'role':'assistant','native':native,'raw':raw})
        self.assertEqual(listing['output_text'],'Answer')
        self.assertEqual([p['kind'] for p in listing['output_blocks']],['reasoning','text','tool_call','provider_tool','opaque','alternative','raw'])

    def test_conversation_is_small_lazy_and_exact_records_are_unchanged(self):
        with scratch_directory() as tmp:
            store=Store(tmp/'runs',tmp/'ui');root=fixture(store)
            thought='Exposed reasoning ' * 50000
            native={'role':'assistant','content':'Answer','reasoning_content':thought,
                    'tool_calls':[{'id':'tool-1','type':'function','function':{'name':'unknown_tool','arguments':json.dumps({'script':'x'*50000})}}],
                    'unexpected_metadata':{'value':'UNKNOWN'}}
            message={'role':'assistant','native':native,'raw':{'choices':[{'message':native}],'other_calls':[{'mcp':'external'}]},
                     'tool_calls':[{'id':'tool-1','name':'unknown_tool','arguments':{'script':'x'*50000}}],
                     'sent_parameters':{'messages':['exact request']}}
            journal=Journal(root)
            state=journal.state('mock-repair-r0');state['history']=[message,{'role':'tool','name':'unknown_tool','result':{'error':'Refused','content':'z'*50000}}]
            journal.save('mock-repair-r0',state,'model_response',message);journal.db.close()
            before=(root/'journal.sqlite').read_bytes()
            view=store.conversation('example','mock-repair-r0')
            self.assertLess(len(json.dumps(view)),10000)
            item=view['messages'][0]
            self.assertNotIn('native',item);self.assertNotIn('raw',item)
            block=next(b for b in item['output_blocks'] if b['kind']=='reasoning')
            self.assertEqual(store.output_block('example','mock-repair-r0',0,block['index'])['value'],thought)
            self.assertEqual(store.message('example','mock-repair-r0',0)['message'],message)
            self.assertTrue(view['messages'][1]['tool_error'])
            self.assertNotIn('result',view['messages'][1])
            self.assertEqual((root/'journal.sqlite').read_bytes(),before)
            with self.assertRaises(ArenaError):store.output_block('example','mock-repair-r0',0,999)

    def test_malformed_response_is_reachable_even_without_an_assistant_message(self):
        with scratch_directory() as tmp:
            store=Store(tmp/'runs',tmp/'ui');root=fixture(store)
            journal=Journal(root);state=journal.state('mock-repair-r0')
            state.update(status='needs_reconciliation',failure={'message':'Malformed response','phase':'provider response'})
            payload={'response':{'raw':{'unknown_output':'PRESERVED'}}}
            journal.save('mock-repair-r0',state,'malformed_provider_response',payload);journal.db.close()
            view=store.conversation('example','mock-repair-r0')
            self.assertEqual(view['failure_event']['kind'],'malformed_provider_response')
            self.assertEqual(store.event('example',view['failure_event']['id']),payload)
