import copy
import hashlib
import json
import unittest
from unittest import mock
from arena.core import scratch_directory
from arena.experiment import Journal
from arena.preparation import Preparation
from arena.api_providers import APIProvider
from arena_web.data import Store
from test_web import fixture, write_history


class ToolExchangeTests(unittest.TestCase):
    def test_diff_uses_the_correct_successful_write_and_never_later_workspace_contents(self):
        with scratch_directory() as tmp:
            store=Store(tmp/'runs',tmp/'ui');root=fixture(store)
            history=write_history('var a = 1\n')+write_history('rejected',False)+write_history('var a = 2\n')
            journal=Journal(root); state=journal.state('mock-repair-r0');state['history']=history
            journal.save('mock-repair-r0',state,'fixture');journal.db.close()
            view=store.conversation('example','mock-repair-r0')
            self.assertEqual(view['messages'][5]['file_exchange']['path'],'main.leek')
            self.assertTrue(view['messages'][5]['file_exchange']['saved'])
            diff=store.tool_exchange('example','mock-repair-r0',5)
            self.assertEqual(diff['before'],'var a = 1\n')
            self.assertEqual(diff['after'],'var a = 2\n')
            self.assertIn('-var a = 1',diff['diff']);self.assertIn('+var a = 2',diff['diff'])
            self.assertNotIn('rejected',diff['diff'])
            self.assertFalse(store.tool_exchange('example','mock-repair-r0',3)['saved'])

    def test_old_read_receipts_are_matched_by_call_id_not_list_position(self):
        with scratch_directory() as tmp:
            store=Store(tmp/'runs',tmp/'ui');root=fixture(store)
            history=[{'role':'assistant','tool_calls':[
                {'id':'a','name':'read_docs','arguments':{'path':'authoring.md','offset':4000,'limit':500}},
                {'id':'b','name':'read_docs','arguments':{'path':'corpus/rules.md','offset':0,'limit':500}}]},
                {'role':'tool','name':'read_docs','provider_call_id':'b','result':{'content':'RULES','truncated':True,'next_offset':5}},
                {'role':'tool','name':'read_docs','provider_call_id':'a','result':{'content':'LANGUAGE','truncated':False,'next_offset':None}}]
            journal=Journal(root); state=journal.state('mock-repair-r0');state['history']=history
            journal.save('mock-repair-r0',state,'fixture');journal.db.close()
            result=store.tool_exchange('example','mock-repair-r0',2)
            self.assertEqual(result['path'],'authoring.md');self.assertEqual(result['offset'],4000)
            self.assertEqual(result['end_offset'],4008);self.assertEqual(result['content'],'LANGUAGE')
            self.assertIsNone(result['total_characters'])
            self.assertEqual(store.tool_exchange('example','mock-repair-r0',1)['path'],'corpus/rules.md')

    def test_read_pagination_gives_an_executable_continuation_and_default_includes_authoring(self):
        with scratch_directory() as tmp:
            (tmp/'docs').mkdir();(tmp/'docs/guide.md').write_text('a'*17005)
            tools=Preparation(tmp/'session',tmp/'docs',None,{})
            page=tools.call('read_docs',{'path':'guide.md'},'1')
            self.assertEqual(page['returned_characters'],16000)
            self.assertEqual(page['total_characters'],17005)
            self.assertEqual(page['reading_status'],'partial')
            last=tools.call(page['continuation']['tool'],page['continuation']['arguments'],'2')
            self.assertEqual(last['returned_characters'],1005)
            self.assertIsNone(last['next_offset']);self.assertIsNone(last['continuation'])
            write=tools.call('write_file',{'path':'main.leek','content':'var a = 1'},'3')
            self.assertEqual(write['path'],'main.leek');self.assertTrue(write['created'])
            self.assertEqual(write['characters'],9)
            write=tools.call('write_file',{'path':'main.leek','content':'var a = 2'},'4')
            self.assertFalse(write['created'])

    def test_oversized_document_pages_are_capped_and_remain_continuable(self):
        with scratch_directory() as tmp:
            (tmp/'docs').mkdir()
            content = 'var x = 1;\n' * 5000
            (tmp/'docs/guide.md').write_text(content, encoding='utf-8')
            tools = Preparation(tmp/'session', tmp/'docs', None, {})
            first = tools.call('read_docs', {'path':'guide.md'}, '1')
            second = tools.call('read_docs', {'path':'guide.md', 'offset':16000, 'limit':45000}, '2')
            self.assertEqual(second['content'], content[16000:32000])
            self.assertEqual(second['returned_characters'], 16000)
            self.assertEqual(second['continuation']['arguments'], {'path':'guide.md', 'offset':32000, 'limit':16000})
            self.assertEqual(first['next_offset'], second['offset'])
            for arguments, field in [({'offset':-1}, 'offset'), ({'offset':True}, 'offset'),
                                     ({'limit':0}, 'limit'), ({'limit':'45000'}, 'limit')]:
                with self.assertRaisesRegex(Exception, 'Invalid '+field+':'):
                    tools.call('read_docs', {'path':'guide.md', **arguments}, 'invalid')

    def test_compatible_reasoning_is_retained_across_requests_and_recorded_on_each_turn(self):
        model={'id':'local','provider':'openai-compatible','model':'local','api_key_env':'ARENA_TEST_LOCAL_KEY',
               'endpoint':'http://127.0.0.1:11434/v1/chat/completions',
               'pricing':{'date':'2026-10-16','currency':'USD','input_per_million':'0','output_per_million':'0'}}
        requests=[]
        def transport(endpoint,payload,headers,timeout):
            requests.append(copy.deepcopy(payload));turn=len(requests)
            return {'choices':[{'message':{'role':'assistant','content':'', 'reasoning_content':f'Reasoning {turn}',
                'tool_calls':[{'id':f'call{turn}','type':'function','function':{'name':'read_docs','arguments':json.dumps({'path':'authoring.md'})}}]},'finish_reason':'tool_calls'}],
                'usage':{'prompt_tokens':5,'completion_tokens':3}},f'request{turn}'
        provider=APIProvider(model,transport)
        history=[{'role':'user','content':'Write LeekScript 4.'}]
        first=provider.respond(history,[],100)
        history.extend([first,{'role':'tool','name':'read_docs','provider_call_id':'call1','result':{'content':'Use var.'}}])
        snapshot=copy.deepcopy(history)
        second=provider.respond(history,[],100)
        history.append(second)
        self.assertEqual(history[:-1],snapshot)
        self.assertEqual(first['native']['reasoning_content'],'Reasoning 1')
        self.assertEqual(second['native']['reasoning_content'],'Reasoning 2')
        self.assertEqual(requests[1]['messages'][1]['reasoning_content'],'Reasoning 1')
        with scratch_directory() as tmp:
            store=Store(tmp/'runs',tmp/'ui');root=fixture(store)
            journal=Journal(root);state=journal.state('mock-repair-r0');state['history']=history
            journal.save('mock-repair-r0',state,'fixture');journal.db.close()
            view=store.conversation('example','mock-repair-r0')
            for index,text in [(1,'Reasoning 1'),(3,'Reasoning 2')]:
                self.assertEqual(view['messages'][index]['output_blocks'][0]['kind'],'reasoning')
                self.assertEqual(store.output_block('example','mock-repair-r0',index,0)['value'],text)
