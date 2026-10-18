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
        with mock.patch('arena.api_providers.request.urlopen',side_effect=failure):
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
        with mock.patch('arena.api_providers.request.urlopen',side_effect=failure):
            with self.assertRaisesRegex(ProviderFailure,'unsupported field'):
                http_json('https://provider.test',{}, {},5)
