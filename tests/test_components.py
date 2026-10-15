import copy
import unittest

from arena.components import catalog, describe, add_bonuses
from arena.core import ArenaError, ROOT, make_scenario, scratch_directory, submission, read_json
from arena.presets import simple_scenario, participant_scenario
from arena.stats import member_stats, realistic_stats
from arena.teams import build_preview, validate_team
from arena.preparation import Preparation
from arena.public_teams import scenario_from_snapshot


class ComponentTests(unittest.TestCase):
    def test_public_levels_match_every_pinned_template(self):
        data = catalog()
        self.assertEqual(len(data), 52)
        self.assertTrue(all(type(row['level']) is int and 1 <= row['level'] <= 301 for row in data.values()))
        self.assertEqual(data['313']['level'], 11)
        self.assertEqual(data['406']['slots'], 3)
        self.assertEqual(data['407']['level'], 1)

    def test_duplicates_slots_levels_and_penalties(self):
        for pieces, level, message in [([290,290],300,'twice'), ([1],300,'Unknown'),
            ([290],40,'requires level 41'), ([406,407,290,313,321],300,'capacity'),
            ([True],300,'integer'), ([{'template':290}],300,'base component IDs')]:
            with self.subTest(pieces=pieces), self.assertRaisesRegex(ArenaError, message):
                describe(pieces, level)
        self.assertEqual(describe([406,407,290,313],300)['slots_used'],8)
        # Different tiers are distinct templates.
        self.assertEqual(describe([290,291,292],300)['bonuses']['cores'],20)
        values = add_bonuses(realistic_stats(300, {}), describe([317,372],300)['bonuses'])
        self.assertEqual(values['resistance'],-30)
        self.assertEqual(values['science'],-60)
        with self.assertRaisesRegex(ArenaError, 'life after components'):
            add_bonuses(realistic_stats(82, {}),describe([376],82)['bonuses'])

    def test_preview_capital_chip_capacity_and_frozen_team(self):
        scenario = participant_scenario()
        plain = build_preview(scenario, 0, {'strength':700})
        boosted = build_preview(scenario, 0, {'strength':700}, [313,290,317])
        self.assertEqual(boosted['remaining'],plain['remaining'])
        self.assertEqual(boosted['next_increases'],plain['next_increases'])
        self.assertEqual(boosted['chip_slots'],10)
        self.assertEqual(boosted['stats']['cores'],plain['stats']['cores']+4)
        team = {'members':[{'entrypoint':'main.leek','capital':{'strength':700},
            'weapons':[], 'chips':[1,2,3,4,5,6,7], 'components':[313,290,317]}]}
        # Check both readonly tool validation and the saved source/receipt path.
        with scratch_directory() as tmp:
            tools=Preparation(tmp/'session',ROOT/'docs',None,scenario)
            preview=tools.call('preview_build',{'capital':{'strength':700},'components':[313,290,317]},'1')
            self.assertEqual(preview['stats'],boosted['stats'])
            report=tools.call('validate_team',team,'2')
            self.assertTrue(report['valid'],report)
            tools.call('write_file',{'path':'main.leek','content':'// component fixture'},'3')
            tools.call('configure_team',team,'4')
            frozen=tools.call('submit',{},'5')['submission']
            self.assertEqual(frozen['team'],team)
            native=make_scenario(scenario,['main.leek']*2,101,[team,None])
            self.assertEqual(native['entities'][0][0]['ram'],10)
            self.assertEqual(native['entities'][0][0]['components'],[313,290,317])
            self.assertEqual(native['entities'][0][0]['resistance'],-30)
        no_ram=copy.deepcopy(team)
        no_ram['members'][0]['components']=[]
        with self.assertRaisesRegex(ArenaError,'RAM 6'):
            validate_team(no_ram,scenario,{'main.leek':''},ROOT/'docs/leekscript-v1')

    def test_default_bonus_once_and_public_totals_preserved(self):
        scenario=simple_scenario()
        scenario['member_stats'][0]['components']=[313,317]
        scenario['entity'].update(member_stats(scenario,0))
        from arena.core import validate_scenario
        validate_scenario(scenario)
        native=make_scenario(scenario,['main.leek']*2,101)
        self.assertEqual(native['entities'][0][0]['ram'],10)
        self.assertEqual(native['entities'][0][0]['mp'],7)
        from test_presets import public_snapshot
        snapshot=public_snapshot()
        snapshot['leeks'][0]['components']=[None,{'id':123,'template':313,'stats':{'ram':1}}]
        imported=scenario_from_snapshot(snapshot)
        self.assertEqual(imported['member_stats'][0]['components'],[{'template':313,'stats':{'ram':1}}])
        self.assertEqual(member_stats(imported,0)['ram'],snapshot['leeks'][0]['total_ram'])
        self.assertEqual(make_scenario(imported,['main.leek']*2,101)['entities'][0][0]['ram'],snapshot['leeks'][0]['total_ram'])

    @unittest.skipUnless((ROOT/'.arena/engine.json').exists(),'Build engine')
    def test_native_combat_uses_components_and_core_operation_budget(self):
        from arena.engine import Engine
        from arena_web.metrics import combat_stats
        scenario=simple_scenario()
        scenario['max_turns']=1
        scenario['member_stats'][0]['components']=[313,290,317,372]
        scenario['entity'].update(member_stats(scenario,0))
        source=ROOT/'examples/strategies/passive'
        with scratch_directory() as tmp:
            result=Engine().fight([source]*2,[submission(source)]*2,scenario,101,tmp/'fight')
            self.assertEqual(result['status'],'completed')
            outcome=read_json(tmp/'fight/outcome.json')
            native=read_json(tmp/'fight/scenario.json')
            entity=outcome['fight']['leeks'][0]
            self.assertEqual(entity['strength'],660)
            self.assertEqual(entity['resistance'],-30)
            self.assertEqual(entity['science'],-60)
            self.assertEqual(combat_stats(outcome,native)['operation_limits'],[9000000])
