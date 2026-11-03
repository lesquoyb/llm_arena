import io
import json
import unittest
from urllib.error import HTTPError
from unittest import mock
from arena.api_providers import http_json, ProviderFailure


class ProviderErrorDetailsTests(unittest.TestCase):
    def test_proxy_validation_fields_and_request_location_are_kept_without_secrets(self):
        body=json.dumps({'detail':[{'loc':['body','instructions'],'msg':'Missing field; token=credential'}]}).encode()
        failure=HTTPError('https://provider.test/v1/responses',400,'Bad Request',{'x-request-id':'req-test'},io.BytesIO(body))
        with mock.patch('arena.api_providers.open_provider_response',side_effect=failure):
            with self.assertRaises(ProviderFailure) as caught:
                http_json('https://provider.test/v1/responses',{}, {'Authorization':'Bearer credential'},5)
        self.assertIn('instructions',str(caught.exception))
        self.assertIn('Missing field',str(caught.exception))
        self.assertNotIn('credential',str(caught.exception))
        self.assertEqual(caught.exception.diagnostics['request_id'],'req-test')
        self.assertEqual(caught.exception.diagnostics['endpoint'],'https://provider.test/v1/responses')
        self.assertFalse(caught.exception.uncertain)

    def test_string_errors_are_not_silently_discarded(self):
        failure=HTTPError('https://provider.test',400,'Bad Request',None,io.BytesIO(b'{"error":"unsupported field"}'))
        with mock.patch('arena.api_providers.open_provider_response',side_effect=failure):
            with self.assertRaisesRegex(ProviderFailure,'unsupported field'):
                http_json('https://provider.test',{}, {},5)

    def test_network_failures_distinguish_not_sent_from_unknown_delivery(self):
        import socket,ssl
        from urllib.request import Request
        from urllib.error import URLError
        from arena.api_providers import open_provider_response
        cases=[(socket.gaierror(-2,'fixture'),'dns_resolution_failed',False),
               (ConnectionRefusedError(),'connection_refused',False),
               (ssl.SSLCertVerificationError(1,'fixture'),'tls_certificate_verification_failed',False),
               (TimeoutError(),'connection_timeout',True)]
        for reason,code,uncertain in cases:
            with self.subTest(code=code),mock.patch('arena.api_providers.request.build_opener') as opener:
                opener.return_value.open.side_effect=URLError(reason)
                with self.assertRaises(ProviderFailure) as caught:
                    open_provider_response(Request('https://api.mistral.ai/v1/chat/completions'),5)
                self.assertEqual(caught.exception.diagnostics['network_error'],code)
                self.assertEqual(caught.exception.uncertain,uncertain)

    def test_failure_after_redirect_keeps_billing_uncertain(self):
        from urllib.request import Request
        from urllib.error import URLError
        from arena.api_providers import open_provider_response
        def opener(handler):
            handler.followed=True
            result=mock.Mock()
            result.open.side_effect=URLError(ConnectionRefusedError())
            return result
        with mock.patch('arena.api_providers.request.build_opener',side_effect=opener):
            with self.assertRaises(ProviderFailure) as caught:
                open_provider_response(Request('https://api.mistral.ai/v1/chat/completions'),5)
        self.assertTrue(caught.exception.uncertain)
        self.assertEqual(caught.exception.diagnostics['request_delivery'],'unknown')
