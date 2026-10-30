"""A browser closing a response must not trigger a second write to that socket."""
import io
import unittest
from types import SimpleNamespace
from unittest import mock
from arena_web.server import Handler


class DisconnectedClientTests(unittest.TestCase):
    def handler(self, failure):
        handler=Handler.__new__(Handler)
        handler.path='/api/bootstrap';handler.close_connection=False
        handler.check_origin=mock.Mock();handler.headers_for=mock.Mock()
        handler.wfile=mock.Mock();handler.wfile.write.side_effect=failure
        handler.server=SimpleNamespace(app=SimpleNamespace(get=mock.Mock(return_value={'ok':True}),post=mock.Mock(return_value={'ok':True}),token='fixture-token'))
        return handler

    def test_get_response_disconnect_is_not_retried_as_an_error_response(self):
        for failure in (ConnectionAbortedError(10053,'browser closed'),ConnectionResetError('reset'),BrokenPipeError('pipe')):
            with self.subTest(failure=type(failure).__name__):
                handler=self.handler(failure);handler.do_GET()
                self.assertTrue(handler.close_connection)
                self.assertEqual(handler.wfile.write.call_count,1)
                self.assertEqual(handler.headers_for.call_count,1)

    def test_error_response_and_post_response_also_tolerate_disconnect(self):
        handler=self.handler(ConnectionAbortedError(10053,'closed'))
        handler.server.app.get.side_effect=ValueError('bad request')
        handler.do_GET()
        self.assertEqual(handler.wfile.write.call_count,1)
        self.assertTrue(handler.close_connection)
        handler=self.handler(ConnectionAbortedError(10053,'closed'))
        handler.headers={'X-Arena-Token':'fixture-token','Content-Type':'application/json','Content-Length':'2'}
        handler.rfile=io.BytesIO(b'{}');handler.do_POST()
        self.assertEqual(handler.wfile.write.call_count,1)
        self.assertTrue(handler.close_connection)
