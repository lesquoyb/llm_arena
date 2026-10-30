"""An expired UI token is rejected before any action is dispatched."""
import json
import threading
import unittest
from types import SimpleNamespace
from unittest import mock
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from arena_web.server import Server


class SessionTokenTests(unittest.TestCase):
    def test_expired_token_has_a_specific_code_and_never_executes_the_action(self):
        app=SimpleNamespace(token='current-token',post=mock.Mock(return_value={'saved':True}))
        app.get=lambda route,query:{'token':app.token}
        with Server(('127.0.0.1',0),app) as server:
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            base=f'http://127.0.0.1:{server.server_port}'
            def post(token):
                return urlopen(Request(base+'/api/competition',data=b'{}',headers={
                    'Content-Type':'application/json','X-Arena-Token':token}))
            try:
                with self.assertRaises(HTTPError) as failure:post('old-token')
                with failure.exception as response:
                    self.assertEqual(response.code,403)
                    self.assertEqual(json.loads(response.read())['code'],'stale_arena_token')
                app.post.assert_not_called()
                with urlopen(base+'/api/bootstrap') as response:token=json.loads(response.read())['token']
                with post(token) as response:self.assertTrue(json.loads(response.read())['saved'])
                app.post.assert_called_once_with('/api/competition',{})
            finally:
                server.shutdown();thread.join(timeout=2)
