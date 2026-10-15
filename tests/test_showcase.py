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

    def test_apocalypse_kills_enemies_without_killing_caster_in_free_mode(self):
        import copy
        from arena.core import DEFAULT_SCENARIO, submission
        with scratch_directory() as tmp:
            source = tmp / 'source'
            source.mkdir()
            (source / 'main.leek').write_text('useChip(CHIP_APOCALYPSE, getEntity())', encoding='utf-8')
            opponent = ROOT / 'examples/strategies/passive'
            scenario = copy.deepcopy(DEFAULT_SCENARIO)
            scenario['stats_mode'] = 'free'
            scenario['entity']['chips'] = [418]
            result = Engine().fight([source, opponent], [submission(source), submission(opponent)], scenario, 101, tmp / 'fight')
            self.assertEqual(result['status'], 'completed')
            self.assertEqual(result['winner_side'], 0)
            fight = read_json(tmp / 'fight/outcome.json')['fight']
            killed = {a[1] for a in fight['actions'] if a[0] == 5}
            enemies = {l['id'] for l in fight['leeks'] if l['team'] == 2}
            self.assertEqual(killed, enemies)
