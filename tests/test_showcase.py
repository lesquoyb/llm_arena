import unittest

from arena.core import ROOT, load_manifest, read_json, scratch_directory, write_json
from arena.engine import Engine
from arena.preparation import Preparation
from arena.equipment import catalog
from arena.tournament import run_tournament
from arena_web.replay import describe


class ShowcaseTests(unittest.TestCase):
    def test_native_weapons_chips_and_summon_callback(self):
        catalogs = {kind: catalog(ROOT / 'docs/leekscript-v1', kind)
                    for kind in ('weapons', 'chips')}
        self.assertEqual(catalogs['weapons']['37']['name'], 'pistol')
        self.assertNotIn('1', catalogs['weapons'])
        with scratch_directory() as tmp:
            run_tournament(Engine(), load_manifest(ROOT / 'examples/showcase/tournament.json'), tmp / 'run')
            outcomes = list((tmp / 'run').rglob('outcome.json'))
            self.assertEqual(len(outcomes), 2)
            for path in outcomes:
                outcome = read_json(path)
                fight = outcome['fight']
                actions = fight['actions']
                self.assertFalse(any(a[0] in (1000, 1002) for a in actions))
                self.assertTrue(any(a[0] == 9 and a[4] == 1 for a in actions))
                self.assertTrue({1, 6, 19, 24, 40}.issubset({a[1] for a in actions if a[0] == 12}))
                self.assertTrue({1, 2}.issubset({a[1] for a in actions if a[0] == 13}))
                self.assertTrue({10, 16, 103, 5}.issubset({a[0] for a in actions}))
                summons = {l['id'] for l in fight['leeks'] if l.get('summon')}
                self.assertTrue(summons)
                self.assertTrue(any(a[0] == 7 and a[1] in summons for a in actions))
                self.assertIn('bulb turn', str(outcome['logs']))
                labels = str(describe(fight, catalogs)['events'])
                self.assertIn('equips pistol', labels)
                self.assertIn('uses shock', labels)
                self.assertIn('summons Scout bulb', labels)

    def test_models_can_page_their_own_training_logs(self):
        with scratch_directory() as tmp:
            tools = Preparation(tmp, ROOT / 'docs', None, {})
            artifact = tmp / 'tools/call-1-tool-1-side-0'
            write_json(artifact / 'cached.json', {'artifact_dir': 'training-artifact'})
            write_json(tmp / 'training-artifact/outcome.json', {
                'logs': {'0': {'1': [[0, 1, 'hello from debug']]}}, 'turn_metrics': []})
            page = tools.call('read_replay', {'test_id': 'call-1-tool-1', 'section': 'logs'}, '2')
            self.assertIn('hello from debug', page['content'])
            self.assertFalse(page['truncated'])
            page = tools.call('read_replay', {'test_id': 'call-1-tool-1', 'section': 'logs', 'limit': 4}, '2')
            self.assertTrue(page['truncated'])
            self.assertEqual(page['next_offset'], 4)
