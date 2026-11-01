"""Game-rule changes applied from a later round of a running competition."""
import unittest
from contextlib import closing
from types import SimpleNamespace
from unittest import mock
from pathlib import Path

from arena.core import ROOT, ArenaError, read_json, scratch_directory, write_json
from arena.experiment import Journal, initial_state
from arena.roster import snapshot, update
from arena.scenario_rules import generation_of, round_config, scenario_for


class ScenarioRuleTests(unittest.TestCase):
    def test_rounds_before_a_change_keep_the_original_scenario(self):
        config = {'scenario': {'max_turns': 1000}, '_scenario_changes': [
            {'from_generation': 4, 'stall_turns': 100}, {'from_generation': 6, 'stall_turns': None}]}
        self.assertNotIn('stall_turns', scenario_for(config, 3))
        self.assertEqual(scenario_for(config, 4)['stall_turns'], 100)
        self.assertEqual(scenario_for(config, 5)['stall_turns'], 100)
        self.assertNotIn('stall_turns', scenario_for(config, 6))
        self.assertEqual(config['scenario'], {'max_turns': 1000})
        self.assertEqual(round_config(config, 4)['scenario']['stall_turns'], 100)
        self.assertEqual((generation_of('g0-panel'), generation_of('g4-previous')), (0, 4))

    def test_change_is_journaled_from_the_next_round_without_touching_the_frozen_config(self):
        config = read_json(ROOT / 'configs/offline-complete.json')
        with scratch_directory() as root:
            write_json(root / 'experiment.json', {'config': config})
            original = (root / 'experiment.json').read_bytes()
            journal = Journal(root)
            with closing(journal.db):
                model = config['models'][0]
                state = initial_state(model['id'] + '-r0', model, config)
                state.update(status='submitted', generation=3)
                journal.save(model['id'] + '-r0', state, 'fixture')
                selected = [row['id'] for row in config['models']]
                change = update(root, journal, config, [], selected, rule_change={'stall_turns': 100})
                self.assertEqual(change['scenario_changes'], [{'from_generation': 4, 'stall_turns': 100}])
                # A later unrelated change keeps the rule; a new value replaces it for the same round.
                self.assertEqual(update(root, journal, config, [], selected)['scenario_changes'], change['scenario_changes'])
                self.assertEqual(update(root, journal, config, [], selected, rule_change={'stall_turns': 60})['scenario_changes'],
                                 [{'from_generation': 4, 'stall_turns': 60}])
                for bad in ({'stall_turns': 5}, {'max_turns': 10}, {}):
                    with self.assertRaises(ArenaError):
                        update(root, journal, config, [], selected, rule_change=bad)
                self.assertEqual(snapshot(root)['scenario_changes'][0]['stall_turns'], 60)
                journal.verify()
            self.assertEqual((root / 'experiment.json').read_bytes(), original)

    def test_round_tournament_and_briefing_use_the_rules_in_force(self):
        from arena import greedy
        from arena.user_briefing import render
        config = {**read_json(ROOT / 'configs/offline-complete.json'), '_scenario_changes': [{'from_generation': 1, 'stall_turns': 100}]}
        states = {sid: {'model': 'm', 'replicate': 0, 'generation': 1, 'parent': 'p', 'submission': {'entrypoint': 'main.leek'}} for sid in ('a', 'b')}
        with scratch_directory() as root, mock.patch('arena.greedy.run_tournament', return_value={'completed': 2}) as tournament:
            greedy.evaluate(None, config, root, SimpleNamespace(metadata=lambda: states), 1)
            self.assertEqual(tournament.call_args.args[1]['scenario']['stall_turns'], 100)
        # The provider-facing first message states the rule only where it applies.
        from arena.model_content import message_text
        message = initial_state('m-r0-g1-feedback', config['models'][0], round_config(config, 1))['history'][0]
        self.assertIn('100 consecutive turns', message_text(message))
        self.assertNotIn('consecutive turns', message_text(initial_state('m-r0', config['models'][0], config)['history'][0]))


if __name__ == '__main__':
    unittest.main()
