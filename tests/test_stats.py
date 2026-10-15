import copy
import unittest
from arena.core import ArenaError, DEFAULT_SCENARIO, ROOT, make_scenario, validate_scenario
from arena.stats import RULES, default_capital, realistic_stats, stat_bonus, total_capital
from arena.teams import validate_team


def realistic():
    value = copy.deepcopy(DEFAULT_SCENARIO)
    value['stats_mode'] = 'realistic-v1'
    value['member_stats'] = [{'capital': {'strength': 100}}, {'capital': {'wisdom': 100, 'life': 100}}]
    value['entity'].update(realistic_stats(100, value['member_stats'][0]['capital']))
    return value


class RealisticStatsTests(unittest.TestCase):
    def test_official_level_and_conversion_boundaries(self):
        for level, capital in [(1,50), (2,55), (50,295), (99,540), (100,590), (200,1135), (300,1680), (301,1780)]:
            self.assertEqual(total_capital(level), capital)
            self.assertLessEqual(sum(default_capital(level).values()), capital)
        for capital, bonus in [(1,2), (100,200), (250,350), (300,400), (700,600), (703,601)]:
            self.assertEqual(stat_bonus('strength', capital), bonus)
        self.assertEqual(stat_bonus('life',250),1000)
        self.assertEqual(stat_bonus('life',251),1003)
        self.assertEqual(stat_bonus('cores',19),0)
        self.assertEqual(stat_bonus('cores',20),1)
        self.assertEqual(stat_bonus('cores',540),9)
        self.assertEqual(realistic_stats(301,{})['life'],1000)
        self.assertEqual(realistic_stats(1,{})['ram'],6)

    def test_rejects_impossible_capital_and_forged_default_stats(self):
        for level, capital in [(0,{}),(302,{}),(100,{'strength':591}),(100,{'strength':300,'life':300}),
                               (100,{'strength':True}),(100,{'strength':-1}),(100,{'unknown':1})]:
            with self.subTest(level=level,capital=capital), self.assertRaises(ArenaError):
                realistic_stats(level,capital)
        config=realistic()
        config['entity']['strength']=100000
        with self.assertRaisesRegex(ArenaError,'must match'):
            validate_scenario(config)

    def test_per_member_builds_apply_to_both_sides_and_allow_team_overrides(self):
        config=realistic()
        validate_scenario(config)
        baseline=make_scenario(config,['main.leek']*2,101)
        for side in baseline['entities']:
            self.assertEqual(side[0]['strength'],200)
            self.assertEqual(side[1]['wisdom'],200)
            self.assertEqual(side[1]['life'],797)
        config['team_selection']={'mode':'participant'}
        chosen={'members':[{'entrypoint':'main.leek','weapons':[37],'chips':[], 'capital':{'agility':100}}]}
        for teams in ([chosen,None],[None,chosen]):
            actual=make_scenario(config,['main.leek']*2,101,teams)
            side=actual['entities'][0 if teams[0] else 1]
            self.assertEqual(side[0]['agility'],200)
            self.assertEqual(side[0]['strength'],0)
        bad=copy.deepcopy(chosen)
        bad['members'][0]['stats']={'strength':100000}
        with self.assertRaises(ArenaError): validate_team(bad,config)
        bad=copy.deepcopy(chosen)
        bad['members'][0]['capital']={'strength':590,'life':1}
        with self.assertRaises(ArenaError): validate_team(bad,config)

    def test_realistic_equipment_level_applies_to_defaults_and_model_choices(self):
        from arena.core import ROOT
        for kind, identifier in [('weapons',48),('chips',76)]:
            config=realistic()
            config['entity'][kind]=[identifier]
            with self.subTest(kind=kind), self.assertRaisesRegex(ArenaError,'requires level'):
                validate_scenario(config)
            config=realistic()
            config['team_selection']={'mode':'participant'}
            member={'entrypoint':'main.leek','weapons':[], 'chips':[],kind:[identifier]}
            with self.assertRaisesRegex(ArenaError,'higher level'):
                validate_team({'members':[member]},config,{'main.leek':''},ROOT/'docs/leekscript-v1')
            config['stats_mode']='free'
            config.pop('member_stats')
            config['entity'][kind]=[identifier]
            validate_scenario(config)
            validate_team({'members':[member]},config,{'main.leek':''},ROOT/'docs/leekscript-v1')

    def test_legacy_free_scenarios_preserve_exact_entity_fields(self):
        actual=make_scenario(DEFAULT_SCENARIO,['main.leek']*2,101)
        self.assertNotIn('magic',actual['entities'][0][0])
        config=copy.deepcopy(DEFAULT_SCENARIO)
        config['member_stats']=[{'stats':{'strength':100000}},{'stats':{'wisdom':123}}]
        actual=make_scenario(config,['main.leek']*2,101)
        self.assertEqual(actual['entities'][0][0]['strength'],100000)
        self.assertEqual(actual['entities'][0][1]['wisdom'],123)
        from arena.stats import member_stats
        self.assertEqual(member_stats(config,1,{'stats':{'strength':9}})['wisdom'],123)

@unittest.skipUnless((ROOT / '.arena/engine.json').exists(), 'Build engine')
class RealisticEngineTests(unittest.TestCase):
    def test_real_combat_uses_distinct_member_stats_and_operation_caps(self):
        from arena.core import ROOT, read_json, scratch_directory, submission
        from arena.engine import Engine
        from arena_web.metrics import combat_stats
        config=realistic()
        config['max_turns']=1
        config['member_stats'][0]['capital']['cores']=20
        config['member_stats'][1]['capital']['cores']=140
        config['entity'].update(realistic_stats(100,config['member_stats'][0]['capital']))
        source=ROOT/'examples/strategies/passive'
        with scratch_directory() as tmp:
            result=Engine().fight([source]*2,[submission(source)]*2,config,101,tmp/'match')
            self.assertEqual(result['status'],'completed')
            scenario=read_json(tmp/'match/scenario.json')
            recorded=read_json(tmp/'match/outcome.json')
            leeks={e['name']:e for e in recorded['fight']['leeks']}
            self.assertEqual(leeks['Side 1 / 1']['strength'],200)
            self.assertEqual(leeks['Side 1 / 2']['wisdom'],200)
            self.assertEqual(leeks['Side 1 / 2']['life'],797)
            self.assertIsNone(recorded['operations_limit_per_turn'])
            stats=combat_stats(recorded,scenario)
            self.assertEqual(stats['operation_limits'],[2000000,5000000])
            self.assertIsNone(stats['operations_limit_per_turn'])
            self.assertEqual({e['name']:e['operations_limit_per_turn'] for e in stats['entities']}['Side 1 / 2'],5000000)


class EquipmentCapacityTests(unittest.TestCase):
    def test_weapon_thresholds_ram_slots_and_special_items(self):
        from arena.equipment import validate_loadout
        for level, slots in [(1, 2), (99, 2), (100, 3), (199, 3), (200, 4), (301, 4)]:
            validate_loadout(level, {'ram': 6}, list(range(slots)), list(range(6)))
            with self.assertRaisesRegex(ArenaError, 'weapons'):
                validate_loadout(level, {'ram': 6}, list(range(slots + 1)), [])
        with self.assertRaisesRegex(ArenaError, 'RAM 6'):
            validate_loadout(100, {'ram': 6}, [], list(range(7)))
        with self.assertRaisesRegex(ArenaError, 'not player equipment'):
            validate_loadout(100, {'ram': 6}, [], [418])

    def test_default_and_selected_teams_enforce_each_members_ram(self):
        value = realistic()
        value['entity']['chips'] = [1, 3, 19, 8, 2, 21, 7]
        with self.assertRaisesRegex(ArenaError, 'RAM 6'):
            validate_scenario(value)
        value['entity']['chips'] = []
        selection = {'members': [{'entrypoint': 'main.leek', 'weapons': [],
                                 'chips': [1, 3, 19, 8, 2, 21, 7]}]}
        value['team_selection'] = {'mode': 'participant', 'max_chips': 32}
        with self.assertRaisesRegex(ArenaError, 'RAM 6'):
            validate_team(selection, value, {'main.leek': ''}, ROOT / 'docs/leekscript-v1')
        selection['members'][0]['capital'] = {'ram': 20}
        validate_team(selection, value, {'main.leek': ''}, ROOT / 'docs/leekscript-v1')
