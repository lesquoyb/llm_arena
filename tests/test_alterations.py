import copy
import unittest

from arena.components import catalog, describe
from arena.core import ArenaError, ROOT, read_json, scratch_directory, submission
from arena.presets import dream_team_scenario
from arena.public_teams import scenario_from_snapshot
from arena.stats import STATS, member_stats, to_realistic


def public_snapshot():
    return read_json(ROOT/'tests/fixtures/dream-team-public.json')


class AlterationTests(unittest.TestCase):
    def test_bundled_public_preset_is_ready_and_validates_offline(self):
        original = dream_team_scenario()
        converted = to_realistic(original)
        self.assertEqual([m['name'] for m in converted['member_stats']],
                         ['Pink', 'CoLeek', 'Veggy', 'Zombizou'])
        self.assertEqual([member_stats(converted, i) for i in range(4)],
                         [member_stats(original, i) for i in range(4)])

    def test_public_catalog_corrects_stale_generator_values(self):
        data = catalog()
        self.assertEqual(dict(data['382']['stats'])['life'], 80)
        self.assertEqual(dict(data['382']['stats'])['science'], 20)
        self.assertNotIn('tp', dict(data['315']['stats']))
        self.assertEqual(data['382']['capacity'], 320)

    def test_charge_deficit_refund_and_exact_capacity_boundary(self):
        # Public client: losses refund one quarter of their weighted value.
        info = describe([{'template': 382, 'stats': {'tp': 1, 'life': 12,
            'wisdom': -4, 'science': -2, 'frequency': -5}}], 301)
        self.assertEqual(info['alterations'], [{'template': 382, 'charge': 185, 'capacity': 320}])
        self.assertEqual(info['bonuses']['life'], 92)
        # SSD: capacity 260. Do not round 260.25 down to a legal 260.
        describe([{'template': 315, 'stats': {'life': 260}}], 301)
        with self.assertRaisesRegex(ArenaError, '260.25 exceeds capacity 260'):
            describe([{'template': 315, 'stats': {'life': 261, 'science': -1}}], 301)
        for delta in ({'tp': 2}, {'life': True}, {'life': 1.5}, {'unknown': 1}):
            with self.subTest(delta=delta), self.assertRaises(ArenaError):
                describe([{'template': 315, 'stats': delta}], 301)
        with self.assertRaisesRegex(ArenaError, 'requires level'):
            describe([{'template': 382, 'stats': {'life': 1}}], 1)
        describe([{'template': 290}], 301)  # An instance may be unaltered.

    def test_real_public_team_recomputes_all_totals_without_snapshot_exemption(self):
        snapshot = public_snapshot()
        original = scenario_from_snapshot(snapshot)
        before = copy.deepcopy(original)
        converted = to_realistic(original)
        self.assertEqual(original, before)
        self.assertEqual(converted['stats_mode'], 'realistic-v1')
        for i, (spec, leek) in enumerate(zip(converted['member_stats'], snapshot['leeks'])):
            self.assertEqual(sum(spec['capital'].values()), 1780)
            expected = {k: leek['total_' + k] for k in STATS}
            self.assertEqual(member_stats(converted, i), expected)
            self.assertEqual(spec['components'], original['member_stats'][i]['components'])
            self.assertNotIn('stats', spec)
        # Calculation uses the build, without trusting source metadata or its totals.
        original.pop('source')
        self.assertEqual(to_realistic(original)['member_stats'], converted['member_stats'])
        original['member_stats'][0]['stats']['life'] += 1
        with self.assertRaisesRegex(ArenaError, 'Pink: life.*cannot be obtained'):
            to_realistic(original)
        self.assertEqual(original['member_stats'][0]['stats']['life'], snapshot['leeks'][0]['total_life'] + 1)

    def test_old_saved_preset_recovers_component_instances_locally(self):
        from arena.core import write_json
        scenario = scenario_from_snapshot(public_snapshot())
        for member in scenario['member_stats']:
            del member['components']
        with scratch_directory() as tmp:
            path = tmp/'dream-team.json'
            write_json(path, {'status': 'ready', 'scenario': scenario})
            loaded = dream_team_scenario(path)
            self.assertEqual(sum(to_realistic(loaded)['member_stats'][0]['capital'].values()), 1780)

    def test_conversion_api_rejects_invalid_capital_equipment_and_alterations(self):
        from arena_web.server import Application
        from arena_web.data import Store
        with scratch_directory() as tmp:
            app = Application(Store(tmp/'runs', tmp/'ui'))
            scenario = scenario_from_snapshot(public_snapshot())
            result = app.post('/api/stats/realistic', {'scenario': scenario})['scenario']
            self.assertEqual(result['stats_mode'], 'realistic-v1')
            for bad in ('capital', 'alteration', 'equipment'):
                changed = copy.deepcopy(scenario)
                spec = changed['member_stats'][0]
                if bad == 'capital':
                    spec['stats']['strength'] += 1000
                elif bad == 'alteration':
                    spec['components'][0]['stats']['tp'] += 100
                else:
                    spec['weapons'] = [37, 38, 45, 151, 153]
                with self.subTest(bad=bad), self.assertRaises(ArenaError):
                    app.post('/api/stats/realistic', {'scenario': changed})

    @unittest.skipUnless((ROOT/'.arena/engine.json').exists(), 'Build engine')
    def test_native_fight_retains_every_public_member_stat(self):
        from arena.engine import Engine
        from arena_web.metrics import combat_stats
        scenario = to_realistic(scenario_from_snapshot(public_snapshot()))
        scenario['max_turns'] = 1
        source = ROOT/'examples/strategies/passive'
        with scratch_directory() as tmp:
            result = Engine().fight([source]*2, [submission(source)]*2, scenario, 101, tmp/'fight')
            self.assertEqual(result['status'], 'completed')
            native = read_json(tmp/'fight/scenario.json')
            outcome = read_json(tmp/'fight/outcome.json')
            actual = {e['name']: e for e in outcome['fight']['leeks']}
            for side in range(2):
                for i, spec in enumerate(scenario['member_stats']):
                    entity = native['entities'][side][i]
                    self.assertEqual({k: entity[k] for k in STATS}, member_stats(scenario, i))
                    visible = [k for k in STATS if k not in ('cores', 'ram')]
                    self.assertEqual({k: actual[entity['name']][k] for k in visible},
                                     {k: member_stats(scenario, i)[k] for k in visible})
            self.assertEqual(combat_stats(outcome, native)['operation_limits'], [8000000, 12000000])
