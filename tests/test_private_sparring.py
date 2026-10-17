"""Private workspace opponents use the same preparation contract as native calls/MCP."""
from unittest import TestCase
from arena.core import ROOT, ArenaError, read_json, scratch_directory
from arena.preparation import Preparation
from arena.presets import simple_scenario
from test_calibration import FixtureEngine
from test_teams import scenario as team_scenario, team as team_build


class PrivateSparringTests(TestCase):
    def test_fixed_roster_selects_two_distinct_own_entrypoints_and_reverses_sides(self):
        with scratch_directory() as out:
            engine=FixtureEngine();tools=Preparation(out,ROOT/'docs',engine,simple_scenario())
            tools.call('write_file',{'path':'main.leek','content':'debug("A");'},'1')
            tools.call('write_file',{'path':'sparring.leek','content':'debug("B");'},'2')
            result=tools.call('test',{'opponent_entrypoint':'sparring.leek'},'call-1-tool-0')
            self.assertEqual(result['opponent'],'workspace')
            self.assertEqual(result['opponent_entrypoint'],'sparring.leek')
            self.assertEqual(engine.fights,2)
            for side,match in enumerate(result['matches']):
                info=read_json(out/match['artifact_dir']/'provenance.json')['submissions']
                self.assertEqual([s['entrypoint'] for s in info],['main.leek','sparring.leek'] if side==0 else ['sparring.leek','main.leek'])
                self.assertEqual(match['own_side'],side)
            tools.call('test',{'opponent_entrypoint':'sparring.leek'},'call-1-tool-0')
            self.assertEqual(engine.fights,2)

    def test_participant_opponent_mirrors_build_but_not_candidate_entrypoints(self):
        with scratch_directory() as out:
            tools=Preparation(out,ROOT/'docs',FixtureEngine(),team_scenario())
            for i,name in enumerate(('main.leek','healer.leek','sparring.leek'),1):
                tools.call('write_file',{'path':name,'content':'debug("'+name+'");'},str(i))
            tools.call('configure_team',team_build(),'4')
            original=(tools.workspace/'team.json').read_bytes()
            result=tools.call('test',{'opponent_entrypoint':'sparring.leek'},'call-1-tool-0')
            for side,match in enumerate(result['matches']):
                sources=read_json(out/match['artifact_dir']/'provenance.json')['submissions']
                own,opponent=sources[side]['team']['members'],sources[1-side]['team']['members']
                self.assertEqual([m['entrypoint'] for m in own],['main.leek','healer.leek'])
                self.assertEqual([m['entrypoint'] for m in opponent],['sparring.leek','sparring.leek'])
                self.assertEqual([{k:v for k,v in m.items() if k!='entrypoint'} for m in own],
                                 [{k:v for k,v in m.items() if k!='entrypoint'} for m in opponent])
            self.assertEqual((tools.workspace/'team.json').read_bytes(),original)

    def test_other_sources_and_contradictory_opponent_selectors_are_rejected(self):
        with scratch_directory() as out:
            engine=FixtureEngine();tools=Preparation(out/'session',ROOT/'docs',engine,simple_scenario())
            tools.call('write_file',{'path':'main.leek','content':'// own'},'1')
            for arguments in ({'opponent_entrypoint':'../peer/main.leek'},
                              {'opponent_entrypoint':'missing.leek'},
                              {'opponent_id':'workspace'},
                              {'opponent_id':'passive','opponent_entrypoint':'main.leek'},
                              {'opponent_id':'another-participant'}):
                with self.assertRaises(ArenaError): tools.call('test',arguments,'call-1-tool-0')
            self.assertEqual(engine.fights,0)
