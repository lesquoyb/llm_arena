"""Team rosters in fight feedback, participant build limits and the later-round team prompt."""
import copy
import json
import unittest

from arena.core import ArenaError, DEFAULT_SCENARIO, ROOT, scratch_directory, write_json
from arena.feedback import PastFights
from arena.teams import team_preview, validate_team


def member(name, side, level=300, weapons=(37,), chips=(3,)):
    return {'id': side * 2 + 1, 'name': name, 'team': side + 1, 'level': level, 'life': 2957, 'strength': 600,
            'wisdom': 10, 'agility': 20, 'resistance': 30, 'science': 40, 'magic': 50, 'frequency': 100,
            'cores': 5, 'ram': 6, 'tp': 14, 'mp': 6, 'weapons': list(weapons), 'chips': list(chips), 'components': [],
            'ai': 'secret_entrypoint.leek', 'farmer': side + 1, 'type': 1}


class FightTeamsTests(unittest.TestCase):
    def test_teams_section_shows_both_rosters_with_public_stats_and_equipment(self):
        with scratch_directory() as out:
            write_json(out / 'tournament/records/one.json', {
                'match': {'sides': ['parent-r0', 'peer-r0'], 'mirror': False}, 'directory': 'matches/one',
                'result': {'status': 'completed', 'winner_side': 1, 'turns': 5}})
            write_json(out / 'tournament/matches/one/scenario.json', {'entities': [
                [member('Side 1 / 1 · Mine', 0)], [member('Side 2 / 1 · Theirs', 1, weapons=(37, 45)), member('Side 2 / 2 · Healer', 1, chips=())]]})
            write_json(out / 'tournament/matches/one/outcome.json', {'fight': {'leeks': [
                {'id': 0, 'name': 'Side 1 / 1 · Mine'}, {'id': 1, 'name': 'Side 2 / 1 · Theirs'}, {'id': 2, 'name': 'Side 2 / 2 · Healer'}]}})
            access = PastFights(out, 'parent-r0')
            fight_id = access.call('list_past_fights', {})['matches'][0]['fight_id']
            page = access.call('read_past_fight', {'fight_id': fight_id, 'section': 'teams', 'limit': 16000})
            self.assertNotIn('secret_entrypoint', page['content'])
            value = json.loads(page['content'])
            self.assertEqual(value['own_side'], 0)
            mine, theirs = value['teams']
            self.assertTrue(mine['yours'])
            self.assertFalse(theirs['yours'])
            self.assertEqual(len(theirs['members']), 2)
            leek = theirs['members'][0]
            self.assertEqual(leek['entity_id'], 1)
            self.assertEqual(leek['characteristics']['agility'], 20)
            self.assertEqual(leek['characteristics']['ram'], 6)
            self.assertEqual([item['id'] for item in leek['weapons']], [37, 45])
            self.assertTrue(all(item['name'] for item in leek['weapons'] + leek['chips']))
            self.assertEqual(theirs['members'][1]['chips'], [])

    def test_teams_section_without_a_recorded_scenario_is_a_recoverable_error(self):
        with scratch_directory() as out:
            write_json(out / 'tournament/records/one.json', {
                'match': {'sides': ['parent-r0', 'peer-r0'], 'mirror': False}, 'directory': 'matches/one',
                'result': {'status': 'completed', 'winner_side': 0, 'turns': 5}})
            access = PastFights(out, 'parent-r0')
            fight_id = access.call('list_past_fights', {})['matches'][0]['fight_id']
            with self.assertRaisesRegex(ArenaError, 'No team record'):
                access.call('read_past_fight', {'fight_id': fight_id, 'section': 'teams'})


class ParticipantBuildTests(unittest.TestCase):
    def test_participants_cannot_set_raw_stats(self):
        scenario = copy.deepcopy(DEFAULT_SCENARIO)
        scenario['team_selection'] = {'mode': 'participant'}
        team = {'members': [{'entrypoint': 'main.leek', 'weapons': [37], 'chips': [], 'stats': {'life': 99999}}]}
        with self.assertRaisesRegex(ArenaError, 'raw stats'):
            validate_team(team, scenario, {'main.leek'}, ROOT / 'docs/leekscript-v1')

    def test_preview_warns_about_unspent_capital_unused_slots_and_missing_members(self):
        config = json.loads((ROOT / 'configs/offline-complete.json').read_text(encoding='utf-8'))
        scenario = copy.deepcopy(config['scenario'])
        scenario.update(stats_mode='realistic-v1', team_size=2,
                        team_selection={'mode': 'participant', 'require_capital': True, 'independent_builds': True,
                                        'max_weapons': 4, 'max_chips': 50})
        team = {'members': [{'entrypoint': 'main.leek', 'level': 300, 'weapons': [37], 'chips': [],
                             'capital': {'life': 100, 'ram': 20}}]}
        validate_team(team, scenario, {'main.leek'}, ROOT / 'docs/leekscript-v1')
        warnings = team_preview(team, scenario, {'main.leek'})['warnings']
        text = ' '.join(warnings)
        self.assertIn('1 of 2 possible members', text)
        self.assertIn('capital points unspent', text)
        self.assertIn('weapon slots unused', text)
        self.assertIn('chip slot', text)
        over = {'members': [{**team['members'][0], 'capital': {'life': 1000, 'strength': 1000}}]}
        with self.assertRaisesRegex(ArenaError, 'uses 2000; level 300 permits 1680'):
            validate_team(over, scenario, {'main.leek'}, ROOT / 'docs/leekscript-v1')


class LaterRoundPromptTests(unittest.TestCase):
    def test_round_prompts_state_that_the_team_can_change_without_file_jargon(self):
        revision = (ROOT / 'prompts/team-revision.md').read_text(encoding='utf-8')
        self.assertIn('not locked', revision)
        self.assertIn('configure_team', revision)
        for name in ('feedback.md', 'control.md', 'team-revision.md', 'team-feedback.md'):
            self.assertNotIn('team.json', (ROOT / 'prompts' / name).read_text(encoding='utf-8'))
        self.assertIn('section "teams"', (ROOT / 'prompts/team-feedback.md').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
