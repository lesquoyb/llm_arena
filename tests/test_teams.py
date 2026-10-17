import copy
import json
import shutil
import unittest
from pathlib import Path
from unittest import mock

from arena.core import (ArenaError, DEFAULT_SCENARIO, ROOT, copy_submission,
                        make_scenario, read_json, scratch_directory, submission, write_json)
from arena.engine import Engine
from arena.experiment import (Journal, initial_state, run_session, validate_config,
                              verify_workspace, workspace_files)
from arena.preparation import Preparation
from arena.teams import validate_team
from arena_web.data import history_writes


def scenario():
    config = copy.deepcopy(DEFAULT_SCENARIO)
    config['team_selection'] = {'mode': 'participant', 'max_weapons': 2, 'max_chips': 2,
                                'allowed_weapons': [37, 408], 'allowed_chips': [3]}
    return config


def team():
    return {'members': [{'entrypoint': 'main.leek', 'weapons': [37], 'chips': [3]},
                        {'entrypoint': 'healer.leek', 'weapons': [408], 'chips': []}]}


class TeamTests(unittest.TestCase):
    def test_validation_rejects_limits_catalog_ids_level_and_source_escapes(self):
        data = ROOT / 'docs/leekscript-v1'
        files = {'main.leek': '', 'healer.leek': ''}
        self.assertEqual(validate_team(team(), scenario(), files, data), team())
        for members in ([], team()['members'] * 2,
                        [{'entrypoint': '../escape.leek', 'weapons': [], 'chips': []}],
                        [{'entrypoint': 'missing.leek', 'weapons': [], 'chips': []}],
                        [{'entrypoint': 'main.leek', 'weapons': [37, 408, 37], 'chips': []}],
                        [{'entrypoint': 'main.leek', 'weapons': [True], 'chips': []}],
                        [{'entrypoint': 'main.leek', 'weapons': [2], 'chips': []}]):
            with self.subTest(members=members), self.assertRaises(ArenaError):
                validate_team({'members': members}, scenario(), files, data)
        unrestricted = scenario()
        unrestricted['team_selection'].pop('allowed_weapons')
        for weapon in (99999, 48):  # Unknown ID and known weapon above level 100.
            with self.subTest(weapon=weapon), self.assertRaises(ArenaError):
                validate_team({'members': [{'entrypoint': 'main.leek', 'weapons': [weapon], 'chips': []}]}, unrestricted, files, data)

    def test_selection_is_frozen_copied_and_applied_when_sides_swap(self):
        with scratch_directory() as tmp:
            tools = Preparation(tmp / 'session', ROOT / 'docs', None, scenario())
            for name in ('main.leek', 'healer.leek'):
                tools.call('write_file', {'path': name, 'content': '// fixture'}, '1')
            with self.assertRaisesRegex(ArenaError, 'Choose a team'):
                tools.call('submit', {}, '2')
            receipt = tools.call('configure_team', team(), '3')
            info = tools.call('submit', {}, '4')['submission']
            self.assertEqual(info['team'], team())
            self.assertIn('team.json', info['files'])
            target = tmp / 'copy'
            copy_submission(tools.directory / 'submission', target, info)
            self.assertEqual(submission(target), info)
            one = {'members': team()['members'][:1]}
            for teams in ([team(), one], [one, team()]):
                built = make_scenario(scenario(), ['main.leek'] * 2, 101, teams)
                self.assertEqual([len(t) for t in built['entities']], [len(t['members']) for t in teams])
                for side, choice in enumerate(teams):
                    for entity, member in zip(built['entities'][side], choice['members']):
                        self.assertEqual(entity['ai'], member['entrypoint'])
                        self.assertEqual(entity['weapons'], member['weapons'])
                        self.assertEqual(entity['chips'], member['chips'])
                        self.assertEqual(entity['life'], DEFAULT_SCENARIO['entity']['life'])
            history = [{'role': 'assistant', 'tool_calls': [{'name': 'configure_team', 'arguments': team()}]},
                       {'role': 'tool', 'name': 'configure_team', 'result': receipt}]
            self.assertEqual(list(history_writes(history))[0]['path'], 'team.json')
            write_json(target / 'team.json', one)
            with self.assertRaises(ArenaError):
                copy_submission(target, tmp / 'tampered', info)
            with self.assertRaisesRegex(ArenaError, 'disabled'):
                make_scenario(DEFAULT_SCENARIO, ['main.leek'] * 2, 101, [team(), None])

    def test_journal_recovers_team_write_but_rejects_unrecorded_changes(self):
        with scratch_directory() as tmp:
            tools = Preparation(tmp, ROOT / 'docs', None, scenario())
            tools.call('write_file', {'path': 'main.leek', 'content': '// fixture'}, '1')
            state = {'workspace_files': workspace_files(tools.workspace), 'cursor': 0,
                     'reserved': 'call-1-tool-0', 'pending': {'tool_calls': [
                         {'name': 'configure_team', 'arguments': {'members': team()['members'][:1]}}]}}
            tools.call('configure_team', state['pending']['tool_calls'][0]['arguments'], 'call-1-tool-0')
            verify_workspace(state, tools)
            state['reserved'] = None
            write_json(tools.workspace / 'team.json', {'members': []})
            with self.assertRaisesRegex(ArenaError, 'outside the recorded tools'):
                verify_workspace(state, tools)

    def test_mock_uses_shared_team_tool_and_journals_selection(self):
        config = read_json(ROOT / 'configs/offline-demo.json')
        config['scenario'] = scenario()
        validate_config(config)
        with scratch_directory() as tmp:
            shutil.copytree(ROOT / "docs/leekscript-v1", tmp / "corpus/leekscript-v1")
            journal = Journal(tmp)
            try:
                engine = mock.Mock()
                engine.analyze.return_value = {'status': 'valid'}
                model = {'id': 'fixture', 'provider': 'mock', 'profile': 'single-shot'}
                run_session('fixture-r0', model, config, tmp, journal, engine)
                state = journal.state('fixture-r0')
                self.assertEqual(state['status'], 'submitted')
                self.assertIn('team', state['submission'])
                self.assertIn('team_instructions', state['history'][0])
                self.assertTrue(any(m.get('name') == 'configure_team' for m in state['history']))
                self.assertIn('team.json', list(history_writes(state['history']))[-1]['path'])
                journal.verify()
            finally:
                journal.db.close()

@unittest.skipUnless((ROOT / '.arena/engine.json').exists(), 'Build engine')
class TeamEngineTests(unittest.TestCase):
    def test_real_engine_uses_per_member_scripts_and_swapped_equipment(self):
        with scratch_directory() as tmp:
            source = tmp / 'source'
            source.mkdir()
            (source / 'main.leek').write_text('// stationary member')
            (source / 'healer.leek').write_text('// another member')
            write_json(source / 'team.json', team())
            config = scenario()
            config['max_turns'] = 1
            engine = Engine()
            info = submission(source)
            assessed = engine.analyze(source, 'main.leek', tmp / 'assessment')
            self.assertEqual(assessed['status'], 'valid')
            self.assertEqual(assessed['member_analyses']['healer.leek']['status'], 'valid')
            opponent = ROOT / 'examples/strategies/passive'
            opponent_info = submission(opponent)
            for side in (0, 1):
                sources, infos = ([source, opponent], [info, opponent_info]) if side == 0 else ([opponent, source], [opponent_info, info])
                out = tmp / ('match-' + str(side))
                result = engine.fight(sources, infos, config, 101, out)
                self.assertEqual(result['status'], 'completed')
                entities = read_json(out / 'scenario.json')['entities'][side]
                self.assertEqual([e['ai'] for e in entities], ['main.leek', 'healer.leek'])
                self.assertEqual([e['weapons'] for e in entities], [[37], [408]])
                self.assertIn('team.json', read_json(out / 'provenance.json')['submissions'][side]['files'])
            (source / 'healer.leek').write_text('var = ???')
            assessed = engine.analyze(source, 'main.leek', tmp / 'invalid-assessment')
            self.assertEqual(assessed['status'], 'invalid')

    def test_team_inheritance_and_unlimited_mock_conversations_in_complete_experiment(self):
        import contextlib
        import io
        from arena.experiment import run
        config = read_json(ROOT / 'configs/offline-complete.json')
        config['models'] = [{'id': 'fixture', 'provider': 'mock', 'profile': 'single-shot'}]
        config['scenario'] = scenario()
        config['scenario']['max_turns'] = 1
        config['budget_per_session'] = {}
        with scratch_directory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            out = tmp / 'experiment'
            result = run(config, out)
            self.assertFalse(result['evolution']['incomplete'])
            for sid in ('fixture-r0', 'fixture-r0-g1-control', 'fixture-r0-g1-feedback'):
                info = submission(out / 'sessions' / sid / 'submission')
                self.assertIn('team', info)
                self.assertEqual(len(info['team']['members']), 2)
            journal = Journal(out)
            try:
                for condition in ('control', 'feedback'):
                    state = journal.state('fixture-r0-g1-' + condition)
                    writes = list(history_writes(state['history']))
                    self.assertEqual(state['history_policy'], 'fresh-round')
                    # Only this round's configuration is in its conversation.
                    self.assertGreaterEqual(sum(w['path'] == 'team.json' for w in writes), 1)
                journal.verify()
            finally:
                journal.db.close()
            self.assertEqual(run(config, out, resume=True)['evolution']['incomplete'], False)
