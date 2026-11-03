"""Saved connections share credentials without persisting entered secrets."""
import unittest
from arena.core import ArenaError, read_json, scratch_directory
from arena_web.data import Store


class SavedProviderTests(unittest.TestCase):
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
