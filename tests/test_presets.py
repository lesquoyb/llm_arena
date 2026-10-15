import copy
import unittest
from unittest import mock

from arena.core import ArenaError, ROOT, make_scenario, read_json, scratch_directory, submission, validate_scenario
from arena.engine import Engine
from arena.equipment import catalog
from arena.presets import simple_scenario
from arena.public_teams import fetch_snapshot, scenario_from_snapshot, RANKING, DREAM_LEEK_IDS
from arena.stats import STATS


def public_snapshot():
    base = simple_scenario()['entity']
    leeks = []
    for i in range(4):
        leeks.append({'id': 10+i, 'name': f'Public leek {i}', 'level': 301 if i == 0 else 300,
                      **{'total_'+key: base[key]+(i if key == 'strength' else 0) for key in STATS},
                      'weapons': [{'id': 123456+i, 'template': 37 if i % 2 == 0 else 45}],
                      'chips': [{'template': 3}] if i == 1 else []})
    composition = {'id': 91, 'name': 'Public four', 'talent': 1200, 'leeks': [{'id': l['id']} for l in leeks]}
    return {'fetched_at': '2026-10-15T00:00:00+00:00', 'rank': 1, 'ranking_path': RANKING,
            'ranking_entry': {'id': 9, 'talent': 1500}, 'team': {'id': 9, 'name': 'Public team', 'compositions': [composition]},
            'composition': composition, 'leeks': leeks}


class PresetTests(unittest.TestCase):
    def test_default_is_legal_direct_damage_duel_with_all_capital_spent(self):
        scenario = simple_scenario()
        validate_scenario(scenario)
        self.assertEqual((scenario['team_size'], scenario['entity']['level'], scenario['max_turns']), (1,300,1000))
        self.assertEqual(sum(scenario['member_stats'][0]['capital'].values()), 1680)
        self.assertEqual(scenario['entity']['chips'], [])
        weapons = catalog(ROOT/'docs/leekscript-v1', 'weapons')
        self.assertEqual(len(scenario['entity']['weapons']), 4)
        for identifier in scenario['entity']['weapons']:
            item = weapons[str(identifier)]
            self.assertEqual(item['area'], 1)
            self.assertEqual(item['launch_type'], 7)
            self.assertFalse(item['passive_effects'])
            self.assertTrue(all(e['id'] == 1 and e['turns'] == 0 for e in item['effects']))

    def test_public_import_preserves_individual_levels_totals_and_gear(self):
        snapshot = public_snapshot()
        scenario = scenario_from_snapshot(snapshot)
        self.assertEqual(scenario['stats_mode'], 'free')
        self.assertEqual(scenario['source']['snapshot'], snapshot)
        native = make_scenario(scenario, ['main.leek']*2, 101)
        for team in native['entities']:
            self.assertEqual([l['level'] for l in team], [301,300,300,300])
            self.assertEqual([l['weapons'] for l in team], [[37],[45],[37],[45]])
            self.assertEqual([l['chips'] for l in team], [[],[3],[],[]])
            self.assertEqual([l['strength'] for l in team], [600,601,602,603])
        missing = copy.deepcopy(snapshot)
        del missing['leeks'][0]['total_strength']
        with self.assertRaisesRegex(ArenaError, 'missing total_strength'):
            scenario_from_snapshot(missing)
        forbidden = copy.deepcopy(snapshot)
        forbidden['leeks'][0]['chips'] = [{'template': 418}]
        with self.assertRaisesRegex(ArenaError, 'non-player chips'):
            scenario_from_snapshot(forbidden)

    def test_fetch_uses_the_four_user_selected_public_leeks(self):
        snapshot = public_snapshot()
        leeks = [{**leek, 'id': identifier} for leek, identifier in zip(snapshot['leeks'], DREAM_LEEK_IDS)]
        payloads = {'farmer/get/512': {'id': 512},
                    **{'leek/get/'+str(l['id']): l for l in leeks}}
        fetch = mock.Mock(side_effect=payloads.__getitem__)
        result = fetch_snapshot(fetch)
        self.assertEqual([l['id'] for l in result['leeks']], list(DREAM_LEEK_IDS))
        self.assertEqual(len(fetch.call_args_list), 5)
        with self.assertRaisesRegex(ArenaError, 'does not match farmer'):
            fetch_snapshot(lambda path: {'id': 0})

    def test_long_native_match_has_complete_events_and_individual_loadouts(self):
        with scratch_directory() as tmp:
            passive = ROOT/'examples/strategies/passive'
            info = submission(passive)
            scenario = simple_scenario()
            out = tmp/'long'
            result = Engine().fight([passive]*2, [info]*2, scenario, 101, out)
            self.assertEqual(result['status'], 'completed')
            self.assertEqual(result['turns'], 1000)
            self.assertEqual(result['winner_side'], -1)
            outcome = read_json(out/'outcome.json')
            turns = {a[1] for a in outcome['fight']['actions'] if a[0] == 6}
            self.assertTrue(set(range(2,1001)).issubset(turns))
            imported = scenario_from_snapshot(public_snapshot())
            imported['max_turns'] = 1
            out = tmp/'team'
            Engine().fight([passive]*2,[info]*2,imported,101,out)
            native = read_json(out/'scenario.json')
            self.assertEqual([l['weapons'] for l in native['entities'][0]], [[37],[45],[37],[45]])
            self.assertEqual([l['chips'] for l in native['entities'][1]], [[],[3],[],[]])
