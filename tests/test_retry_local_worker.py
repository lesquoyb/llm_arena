"""Recover a real worker after HTTP 429 using a local API fixture, never a paid model."""
import copy
import json
import threading
import unittest
from unittest import mock
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from arena.api_providers import APIProvider
from arena.core import ArenaError, ROOT, file_hash, read_json, scratch_directory
from arena.experiment import run
from arena.presets import simple_scenario
from arena_web.data import Store
from arena_web.jobs import Jobs


@unittest.skipUnless((ROOT/'.arena/engine.json').exists(),'Build engine')
class LocalRetryWorkerTests(unittest.TestCase):
    def test_worker_retries_only_rejected_model_and_needs_no_peer_keys(self):
        received=[]
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args): pass
            def do_POST(self):
                received.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
                self.send_response(429 if len(received)==1 else 200);self.end_headers()
                body={'error':{'status':'RESOURCE_EXHAUSTED','message':'Synthetic quota'}} if len(received)==1 else {
                    'choices':[{'finish_reason':'tool_calls','message':{'role':'assistant','content':None,'tool_calls':[
                        {'id':'write-1','type':'function','function':{'name':'write_file','arguments':json.dumps({'path':'main.leek','content':'// recovered passive'})}},
                        {'id':'submit-1','type':'function','function':{'name':'submit','arguments':'{}'}}]}}],
                    'usage':{'prompt_tokens':10,'completion_tokens':20}}
                self.wfile.write(json.dumps(body).encode())
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            with scratch_directory() as tmp:
                store=Store(tmp/'runs',tmp/'ui');out=store.runs/'quota'
                config=read_json(ROOT/'configs/offline-demo.json')
                config.update(name='Quota recovery',replicates=1,spending={'allow_paid_calls':True},seeds=[101],include_mirrors=False)
                config['scenario']=simple_scenario();config['scenario']['max_turns']=1
                config['models']=[{'id':'healthy','provider':'openai','model':'synthetic-peer','api_key_env':'ARENA_RETRY_PEER_KEY_MISSING',
                     'pricing':{'date':'2026-10-16','currency':'USD','input_per_million':'0','output_per_million':'0'}},
                    {'id':'local','provider':'openai-compatible','model':'fixture-model','api_key_env':'ARENA_RETRY_LOCAL_TEST_UNUSED',
                     'endpoint':f'http://127.0.0.1:{server.server_port}/v1/chat/completions','max_retries':0,
                     'pricing':{'date':'2026-10-16','currency':'USD','input_per_million':'0','output_per_million':'0'}}]
                config['budget_per_session']={}
                original=APIProvider.respond
                def first_attempt(provider,history,tools,limit):
                    if provider.model['id']=='healthy':
                        return {'role':'assistant','provider':'openai','simulated':False,
                            'native':{'role':'assistant','content':'synthetic peer'},
                            'tool_calls':[{'id':'peer-write','name':'write_file','arguments':{'path':'main.leek','content':'// frozen peer'}},
                                          {'id':'peer-submit','name':'submit','arguments':{}}],
                            'usage':{'input_tokens':10,'output_tokens':20},'cost_usd':'0'}
                    return original(provider,history,tools,limit)
                with mock.patch.object(APIProvider,'respond',first_attempt):
                    first=run(copy.deepcopy(config),out)
                self.assertTrue(first['incomplete'])
                old=store.session('quota','healthy-r0')
                source=out/'sessions/healthy-r0/submission/main.leek'
                snapshot=(file_hash(source),source.stat().st_mtime_ns)
                jobs=Jobs(store)
                try:
                    with self.assertRaisesRegex(ArenaError,'Confirm'):
                        jobs.launch(run_id='quota',retry_session='local-r0')
                    row=jobs.launch(run_id='quota',retry_session='local-r0',confirm_paid=True)
                    self.assertEqual(jobs.process.wait(timeout=60),0,jobs.log(row['id'])['content'])
                    jobs.watcher.join(timeout=5)
                    self.assertEqual(row['status'],'completed')
                    self.assertEqual(len(received),2)
                    self.assertEqual(received[0],received[1],'An HTTP rejection should resend the same prompt/history')
                    self.assertEqual(store.session('quota','healthy-r0'),old)
                    self.assertEqual((file_hash(source),source.stat().st_mtime_ns),snapshot)
                    self.assertEqual(store.session('quota','local-r0')['status'],'submitted')
                    self.assertEqual(read_json(out/'report.json')['with_submission'],2)
                finally: jobs.close()
        finally:
            server.shutdown();thread.join();server.server_close()
