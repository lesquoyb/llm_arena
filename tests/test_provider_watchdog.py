"""Real sockets: SSE keepalives do not reserve a provider slot indefinitely."""
import json
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from arena.api_providers import ProviderFailure,http_json
from arena.streaming import stream_json


class Progress:
    def publish(self,*args,**kwargs):pass


class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_POST(self):
        mode=json.loads(self.rfile.read(int(self.headers['Content-Length'])))['mode']
        if mode=='headers':time.sleep(2)
        self.send_response(429 if mode=='error-body' else 200)
        self.send_header('Content-Type','text/event-stream')
        self.end_headers()
        def event(value):
            self.wfile.write(('data: '+json.dumps(value)+'\n\n').encode());self.wfile.flush()
        try:
            if mode=='done':
                event({'choices':[{'delta':{'content':'complete'},'finish_reason':'stop'}]})
                self.wfile.write(b'data: [DONE]\n\n');self.wfile.flush();time.sleep(2)
            elif mode=='active':
                for _ in range(8):event({'choices':[{'delta':{'content':'x'}}]});time.sleep(.1)
                event({'choices':[{'delta':{},'finish_reason':'stop'}]})
            else:
                for _ in range(20):
                    self.wfile.write(b': heartbeat\n\n');self.wfile.flush();time.sleep(.1)
        except (BrokenPipeError,ConnectionResetError):pass


class ProviderWatchdogTests(unittest.TestCase):
    def setUp(self):
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        self.server.daemon_threads=True
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.url=f'http://127.0.0.1:{self.server.server_port}/v1/chat/completions'
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join()
    def test_heartbeats_pause_without_claiming_a_known_quota_error(self):
        with self.assertRaises(ProviderFailure) as caught:
            stream_json(self.url,{'mode':'idle'},{},3,Progress(),inactivity_timeout=.5)
        self.assertEqual(caught.exception.diagnostics['network_error'],'provider_inactivity_timeout')
        self.assertTrue(caught.exception.uncertain)
        self.assertNotIn('http_status',caught.exception.diagnostics)
    def test_manual_pause_closes_only_the_current_stream(self):
        from arena.provider_watchdog import RequestControl,request_control
        control=RequestControl();token=request_control.set(control)
        timer=threading.Timer(.2,control.cancel);timer.start()
        try:
            with self.assertRaises(ProviderFailure) as caught:
                stream_json(self.url,{'mode':'idle'},{},3,Progress(),inactivity_timeout=5)
            self.assertEqual(caught.exception.diagnostics['network_error'],'conversation_paused')
            self.assertTrue(caught.exception.uncertain)
        finally:
            timer.cancel();timer.join();request_control.reset(token)
    def test_manual_pause_also_interrupts_waiting_for_response_headers(self):
        from arena.provider_watchdog import RequestControl,request_control
        control=RequestControl();token=request_control.set(control)
        attached=threading.Event()
        attach=control.attach
        def connected(sock):
            attach(sock)
            if sock:attached.set()
        control.attach=connected
        def pause():
            if attached.wait(3):control.cancel()
        thread=threading.Thread(target=pause);thread.start()
        try:
            with self.assertRaises(ProviderFailure) as caught:
                http_json(self.url,{'mode':'headers'},{},5,inactivity_timeout=5)
            self.assertEqual(caught.exception.diagnostics['network_error'],'conversation_paused')
        finally:thread.join();request_control.reset(token)
    def test_active_output_can_run_longer_than_the_inactivity_threshold(self):
        result,_=stream_json(self.url,{'mode':'active'},{},3,Progress(),inactivity_timeout=.5)
        self.assertEqual(result['choices'][0]['message']['content'],'xxxxxxxx')
    def test_done_does_not_wait_for_server_connection_close(self):
        result,_=stream_json(self.url,{'mode':'done'},{},3,Progress(),inactivity_timeout=.5)
        self.assertEqual(result['choices'][0]['message']['content'],'complete')
    def test_stalled_error_body_preserves_known_http_status(self):
        with self.assertRaises(ProviderFailure) as caught:
            http_json(self.url,{'mode':'error-body'},{},3,inactivity_timeout=.5)
        self.assertEqual(caught.exception.diagnostics['http_status'],429)
        self.assertFalse(caught.exception.uncertain)
