import json
import os
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest import mock

from arena.api_providers import APIProvider, http_json, list_models, request_snapshot
from arena.core import ArenaError, ROOT, read_json
from arena.endpoints import validate_endpoint
from arena.experiment import validate_config
from test_providers import model


class LocalProviderTests(unittest.TestCase):
    def test_only_loopback_may_use_plain_http(self):
        for url in ('http://localhost:11434/v1/chat/completions', 'http://127.0.0.1:11434/v1/chat/completions',
                    'http://[::1]:11434/v1/chat/completions', 'https://example.test/v1/chat/completions'):
            config=read_json(ROOT/'configs/offline-demo.json')
            descriptor=dict(model('openai-compatible'),endpoint=url)
            config.update(models=[descriptor],spending={'allow_paid_calls':True})
            validate_config(config)
        for url in ('http://example.test/v1/chat/completions','http://192.168.1.5:11434/v1/chat/completions',
                    'http://localhost.example.test/api', 'http://127.0.0.1@example.test/api',
                    'http://user:password@localhost/api','http://localhost/api?key=secret',
                    'ftp://localhost/api', 'http://localhost:bad/api', 'http://0.0.0.0/api'):
            with self.subTest(url=url), self.assertRaises(ArenaError):
                validate_endpoint(url)

    def test_real_loopback_catalog_and_generation_without_key(self):
        seen=[]
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args): pass
            def do_GET(self):
                if self.path == '/redirect':
                    self.send_response(302);self.send_header('Location','http://example.invalid/models');self.end_headers();return
                seen.append((self.path,self.headers.get('Authorization')))
                body={'data':[{'id':'local-tool-model'}]}
                self.send_response(200);self.end_headers();self.wfile.write(json.dumps(body).encode())
            def do_POST(self):
                seen.append((self.path,self.headers.get('Authorization')))
                payload=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                if not payload['messages']: raise AssertionError('Missing prompt')
                body={'choices':[{'message':{'role':'assistant','content':'local response'},'finish_reason':'stop'}],
                      'usage':{'prompt_tokens':10,'completion_tokens':2}}
                self.send_response(200);self.end_headers();self.wfile.write(json.dumps(body).encode())
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            url=f'http://127.0.0.1:{server.server_port}/v1/chat/completions'
            descriptor=dict(model('openai-compatible'),endpoint=url)
            with mock.patch.dict(os.environ,{},clear=True):
                self.assertNotIn('Authorization',request_snapshot(descriptor,[],[],None)['headers'])
                catalog=list_models('openai-compatible',None,url)
                response=APIProvider(descriptor).respond([{'role':'user','content':'local test'}],[],None)
            self.assertEqual(catalog['models'][0]['id'],'local-tool-model')
            self.assertEqual(response['native']['content'],'local response')
            self.assertEqual(seen,[('/v1/models',None),('/v1/chat/completions',None)])
            with self.assertRaisesRegex(ArenaError,'HTTPS'):
                http_json(url.replace('/v1/chat/completions','/redirect'),None,{},1)
        finally:
            server.shutdown();thread.join();server.server_close()

    def test_remote_keys_and_transport_policy_remain_required(self):
        with self.assertRaisesRegex(ArenaError,'API key'):
            list_models('openai-compatible',None,'https://example.test/v1/chat/completions')
        with self.assertRaisesRegex(ArenaError,'HTTPS'):
            http_json('http://example.test/v1/models',None,{},1)
