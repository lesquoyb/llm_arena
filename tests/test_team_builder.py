import copy
import unittest
from unittest import mock

from arena.core import ArenaError, ROOT, read_json, scratch_directory, validate_scenario
from arena.engine import Engine
from arena.preparation import Preparation
from arena.presets import participant_scenario, save_dream_team, dream_team_scenario
from arena_web.server import Application
from arena_web.data import Store
from test_presets import public_snapshot


def member():
    return {'name': 'Attacker', 'entrypoint': 'main.leek', 'capital': {'strength': 700, 'life': 570, 'cores': 140, 'tp': 150, 'mp': 120},
            'weapons': [37, 45, 151, 153], 'chips': []}


class TeamBuilderTests(unittest.TestCase):
    def test_preset_is_strict_and_tools_validate_without_mutation(self):
        scenario = participant_scenario()
        validate_scenario(scenario)
        self.assertEqual(scenario['team_size'], 4)
        for bad in ({'stats_mode': 'free'}, {'team_size': 5}, {'entity': {**scenario['entity'], 'level': 301}}):
            with self.assertRaises(ArenaError):
                validate_scenario({**scenario, **bad})
        with scratch_directory() as tmp:
            tools = Preparation(tmp, ROOT/'docs', None, scenario)
            receipt = tools.call('preview_build', {'capital': member()['capital']}, '1')
            self.assertTrue(receipt['valid'])
            self.assertEqual(receipt['remaining'], 0)
            self.assertEqual(receipt['stats']['life'], 2957)
            self.assertEqual(receipt['stats']['strength'], 600)
            self.assertEqual(receipt['chip_slots'], 6)
            preview = tools.call('preview_build', {'capital': {'tp': 165}}, '2')
            self.assertEqual(preview['next_increases']['tp']['capital_cost'], 35)
            valid = tools.call('validate_team', {'members': [member()]}, '3')
            self.assertTrue(valid['valid'])
            self.assertEqual(valid['missing_entrypoints'], ['main.leek'])
            self.assertFalse(valid['source_files_checked'])
            self.assertFalse((tools.workspace/'team.json').exists())
            self.assertEqual(list(tools.workspace.iterdir()), [])
            cases = [{'members': [member()]*5}, {'members': [{**member(), 'capital': {'life': 2000}}]},
                     {'members': [{k:v for k,v in member().items() if k != 'capital'}]},
                     {'members': [{**member(), 'chips': [1,3,19,8,2,21,7]}]},
                     {'members': [{**member(), 'chips': [418]}]},
                     {'members': [{**member(), 'weapons': [37,38,45,151,153]}]}]
            for case in cases:
                with self.subTest(case=case):
                    result = tools.call('validate_team', case, '4')
                    self.assertFalse(result['valid'])
                    self.assertTrue(result['errors'])
            tools.call('write_file', {'path': 'main.leek', 'content': '// passive'}, '5')
            saved = tools.call('configure_team', {'members': [member()]}, '6')
            self.assertTrue(saved['validation']['source_files_checked'])
            self.assertEqual(read_json(tools.workspace/'team.json')['members'], [member()])

    def test_saved_dream_team_is_local_and_refresh_is_explicit(self):
        with scratch_directory() as tmp:
            app = Application(Store(tmp/'runs', tmp/'ui'))
            with mock.patch('arena.public_teams.fetch_snapshot', side_effect=AssertionError('Automatic network call')):
                with mock.patch('arena.presets.dream_team_scenario', side_effect=ArenaError('needs real public snapshot')):
                    with self.assertRaisesRegex(ArenaError, 'real public snapshot'):
                        app.post('/api/dream-team', {})
                result = app.post('/api/dream-team', {'snapshot': public_snapshot()})
                self.assertEqual(app.post('/api/dream-team', {})['scenario'], result['scenario'])
            cached = read_json(tmp/'ui/dream-team-preset.json')
            self.assertEqual(cached['status'], 'ready')
            path = tmp/'bundled.json'
            saved = save_dream_team(public_snapshot(), path)
            self.assertEqual(dream_team_scenario(path), saved)
            updated = public_snapshot()
            updated['leeks'][0]['total_strength'] += 10
            with mock.patch('arena.public_teams.fetch_snapshot', return_value=updated) as fetch:
                refreshed = app.post('/api/dream-team', {'refresh': True})
                fetch.assert_called_once_with()
            self.assertNotEqual(refreshed['scenario']['source']['snapshot_sha256'], result['scenario']['source']['snapshot_sha256'])
            self.assertEqual(result['scenario']['member_stats'][0]['stats']['strength'], 600)

    def test_llm_team_test_runs_actual_configured_members(self):
        with scratch_directory() as tmp:
            scenario = participant_scenario()
            scenario['max_turns'] = 2
            tools = Preparation(tmp, ROOT/'docs', Engine(), scenario)
            tools.call('write_file', {'path':'main.leek', 'content':'// passive'}, '1')
            tools.call('configure_team', {'members':[member()]}, '2')
            result = tools.call('test', {}, 'call-1-tool-3')
            self.assertEqual(result['opponent'], 'passive')
            outcomes = list(tmp.rglob('scenario.json'))
            self.assertEqual(len(outcomes), 2)
            for path in outcomes:
                scenario = read_json(path)
                chosen = next(team for team in scenario['entities'] if len(team) == 1)
                self.assertEqual(chosen[0]['level'], 300)
                self.assertEqual(chosen[0]['strength'], 600)
                self.assertEqual(chosen[0]['weapons'], member()['weapons'])

    def test_mock_session_uses_preview_validation_and_records_explicit_builds(self):
        import contextlib
        import io
        from arena.experiment import run, Journal
        config = read_json(ROOT/'configs/offline-complete.json')
        config.update(models=[{'id':'builder', 'provider':'mock', 'profile':'single-shot'}],
                      generations=1, final_seeds=[], budget_per_session={})
        config['scenario'] = participant_scenario()
        config['scenario']['max_turns'] = 1
        with scratch_directory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            run(config, tmp/'run')
            journal = Journal(tmp/'run')
            try:
                state = journal.state('builder-r0')
                names = [m.get('name') for m in state['history'] if m.get('role') == 'tool']
                self.assertIn('preview_build', names)
                self.assertIn('validate_team', names)
                saved = read_json(tmp/'run/sessions/builder-r0/submission/team.json')
                self.assertEqual(len(saved['members']), 4)
                self.assertTrue(all('capital' in member for member in saved['members']))
                journal.verify()
            finally:
                journal.db.close()
