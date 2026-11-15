"""Saved connections share credentials without persisting entered secrets."""
import unittest
from arena.core import ArenaError, read_json, scratch_directory
from arena_web.data import Store


class SavedProviderTests(unittest.TestCase):
    def test_official_openai_uses_builtin_route_and_rejects_gateway_and_placeholder(self):
        from arena.api_providers import connection, list_models
        from unittest.mock import Mock
        spec = {'id': 'official', 'provider': 'openai', 'api_key_env': 'ARENA_OPENAI_KEY'}
        with scratch_directory() as root:
            store = Store(root/'runs', root/'settings')
            with self.assertRaisesRegex(ArenaError, 'actual OpenAI API key'):
                store.save_provider(spec, ' API ')
            with self.assertRaisesRegex(ArenaError, 'OpenAI-compatible'):
                store.save_provider({**spec, 'endpoint': 'https://example.com/v1/chat/completions'})
            store.save_provider(spec, ' fixture-key ')
            self.assertEqual(store.providers()[0]['spec'], spec)
            self.assertEqual(connection({**spec, 'model': 'gpt-6.1-sol'}, 'fixture-key')[0],
                             'https://api.openai.com/v1/responses')
            transport = Mock(return_value=({'data': []}, None))
            list_models('openai', store.secrets[spec['api_key_env']], transport=transport)
            self.assertEqual(transport.call_args.args[0], 'https://api.openai.com/v1/models')
            self.assertEqual(transport.call_args.args[2]['Authorization'], 'Bearer fixture-key')
            transport.reset_mock()
            with self.assertRaisesRegex(ArenaError, 'OpenAI-compatible'):
                list_models('openai', 'fixture-key', 'https://example.com/v1/responses', transport)
            transport.assert_not_called()

    def test_masked_keys_do_not_reach_transport_or_replace_saved_secret(self):
        from arena.api_providers import APIProvider, ProviderFailure, list_models, request_snapshot
        from unittest.mock import Mock
        spec = {'id': 'official', 'provider': 'openai', 'api_key_env': 'ARENA_OPENAI_KEY'}
        model = {**spec, 'model': 'gpt-6.1-sol'}
        transport = Mock()
        with scratch_directory() as root:
            store = Store(root/'runs', root/'settings')
            store.save_provider(spec, 'fixture-real-key')
            for masked in ('unav********gh', 'sk-abc…xyz', '[REDACTED]', 'unavailable'):
                with self.subTest(masked=masked):
                    with self.assertRaisesRegex(ArenaError, 'masked or unavailable'):
                        store.save_provider(spec, masked)
                    with self.assertRaisesRegex(ArenaError, 'masked or unavailable'):
                        list_models('openai', masked, transport=transport)
                    with self.assertRaisesRegex(ProviderFailure, 'masked or unavailable'):
                        APIProvider(model, transport=transport).respond([], [], None, key_override=masked)
            transport.assert_not_called()
            self.assertEqual(store.secrets['ARENA_OPENAI_KEY'], 'fixture-real-key')
            receipt = request_snapshot(model, [], [], None)
            self.assertEqual(receipt['headers']['Authorization'], 'Bearer [REDACTED]')
            self.assertFalse(receipt['credential_values_recorded'])

    def test_persistence_bulk_creation_and_atomic_validation(self):
        with scratch_directory() as root:
            store=Store(root/'runs',root/'settings')
            spec={'id':'groq','provider':'openai-compatible',
                  'endpoint':'https://api.groq.com/openai/v1/chat/completions','api_key_env':'ARENA_GROQ_KEY'}
            store.save_provider(spec,'fixture-secret')
            self.assertNotIn('fixture-secret',(store.state/'providers.json').read_text())
            self.assertTrue(store.providers()[0]['key_configured'])
            restarted=Store(root/'runs',root/'settings')
            self.assertEqual(restarted.providers()[0]['spec'],spec)
            self.assertFalse(restarted.providers()[0]['key_configured'])
            pricing={'currency':'USD','date':'2026-10-21','input_per_million':'1','output_per_million':'2'}
            rows=[{'id':'one','model':'model-one','pricing':pricing},
                  {'id':'two','model':'model-two','pricing':{**pricing,'output_per_million':'3'}}]
            self.assertEqual(store.create_provider_participants('groq',rows)['created'],['one','two'])
            saved=read_json(store.state/'participants.json')
            self.assertEqual(saved[-1]['api_key_env'],'ARENA_GROQ_KEY')
            with self.assertRaises(ArenaError):
                store.create_provider_participants('groq',[{**rows[0],'id':'new'},rows[1]])
            self.assertEqual(read_json(store.state/'participants.json'),saved)
            store.delete_provider('groq')
            self.assertEqual(store.providers(),[])
            self.assertEqual(read_json(store.state/'participants.json'),saved)
