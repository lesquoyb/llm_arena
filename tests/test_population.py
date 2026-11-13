import contextlib
import io
import unittest

from arena.core import ArenaError, ROOT, read_json, scratch_directory
from arena.experiment import Journal, plan, run, validate_config
from arena.feedback import access_for
from arena.population import select
from arena.submitted_versions import OwnSubmissions


def config():
    c = read_json(ROOT/'configs/offline-complete.json')
    c.update(models=[c['models'][1]], replicates=3, generations=3,
             improvement_conditions=['feedback'], evolutionary={'replace': 1, 'cross_models': False})
    c['scenario']['max_turns'] = 1
    return c


class PopulationTests(unittest.TestCase):
    def test_selection_keeps_best_slots_and_uses_two_distinct_parents(self):
        models = {model: {'id': model} for model in ('a', 'b')}
        entrants = [{'id': f'{model}-r{i}', 'replicate': i, 'model': model}
                    for model in models for i in range(3)]
        states = {e['id']: {'validity': 'valid'} for e in entrants}
        records = [{'session': e['id'], 'opponent': 'fixed', 'seed': 1, 'side': side,
                    'result': {'status': 'completed', 'winner_side': (
                        1-side if e['replicate'] == 0 else -1 if e['replicate'] == 1 else side)}}
                   for e in entrants for side in (0, 1)]
        for cross in (False, True):
            with self.subTest(cross=cross):
                rows = select({'replace': 1, 'cross_models': cross}, entrants, models, states,
                              records, 1, ['fixed'], [1])['population']
                children = [r for r in rows if 'replaces' in r]
                self.assertEqual([r['replaces'] for r in children], ['a-r0', 'b-r0'])
                self.assertEqual(len(rows), 6)
                for child in children:
                    first, second = child['parents']
                    self.assertEqual(first, child['model']+'-r2')
                    self.assertNotEqual(first, second)
                    self.assertFalse(second.endswith('-r0'))
                    self.assertEqual(first[0] != second[0], cross)
        with self.assertRaisesRegex(ArenaError, 'Complete the shared selection panel'):
            select({'replace': 1, 'cross_models': False}, entrants, models, states,
                   records[:-1], 1, ['fixed'], [1])

    def test_configuration_and_preparation_budget_count(self):
        c = config()
        validate_config(c)
        p = plan(c)
        self.assertEqual(p['sessions'], 5)
        self.assertEqual(p['offspring_per_round'], 1)
        self.assertEqual(p['max_preparation_matches'], 20)
        c['evolutionary']['replace'] = 2
        with self.assertRaisesRegex(ArenaError, 'keep at least two parents'):
            validate_config(c)
        c['evolutionary'] = {'replace': 1, 'cross_models': True}
        with self.assertRaisesRegex(ArenaError, 'two generating models'):
            validate_config(c)

    @unittest.skipUnless((ROOT/'.arena/engine.json').exists(), 'Build engine')
    def test_three_rounds_freeze_parents_and_resume_without_more_calls(self):
        c = config()
        with scratch_directory() as directory, contextlib.redirect_stdout(io.StringIO()):
            out = directory/'run'
            report = run(c, out)
            self.assertFalse(report['incomplete'])
            self.assertEqual(report['sessions'], 9)
            self.assertEqual(report['generation'], 2)
            journal = Journal(out)
            try:
                states = journal.states()
                children = [s for s in states.values() if len(s.get('parents', [])) == 2]
                self.assertEqual(len(children), 2)
                for child in children:
                    self.assertEqual(len(child['history'][0]['crossover_parents']), 2)
                    sources = OwnSubmissions(out, child)
                    versions = sources.versions()
                    self.assertEqual([row['session'] for row in versions], child['parents'])
                    for index in (1, 2):
                        data = sources.call('read_submitted_file', {
                            'round': child['generation'], 'parent': index, 'path': 'main.leek'})
                        self.assertTrue(data['content'])
                    with self.assertRaises(ArenaError):
                        sources.call('read_submitted_file', {'round': child['generation'], 'path': 'main.leek'})
                    fights = access_for(out, child).call('list_past_fights', {'limit': 100})
                    self.assertEqual({row['own_submission']['parent'] for row in fights['matches']}, {1, 2})
                self.assertEqual(len([s for s in states.values() if s.get('manual_frozen')]), 4)
            finally:
                journal.db.close()
            decisions = [read_json(out/'selection'/f'g{i}.json') for i in (1, 2)]
            resumed = run(c, out, resume=True)
            self.assertEqual(resumed['model_calls'], report['model_calls'])
            self.assertEqual(resumed['evolution']['selections'], decisions)

    @unittest.skipUnless((ROOT/'.arena/engine.json').exists(), 'Build engine')
    def test_cross_model_children_can_read_foreign_parent_but_not_other_sources(self):
        c = config()
        c['models'].append({**c['models'][0], 'id': 'other'})
        c['generations'] = 2
        c['evolutionary']['cross_models'] = True
        with scratch_directory() as directory, contextlib.redirect_stdout(io.StringIO()):
            out = directory/'run'
            report = run(c, out)
            self.assertFalse(report['incomplete'])
            self.assertEqual(report['sessions'], 12)
            journal = Journal(out)
            try:
                states = journal.states()
                children = [s for s in states.values() if s.get('replaces')]
                self.assertEqual(len(children), 2)
                for child in children:
                    own, foreign = child['parents']
                    self.assertEqual(states[own]['model'], child['model'])
                    self.assertNotEqual(states[foreign]['model'], child['model'])
                    sources = OwnSubmissions(out, child)
                    self.assertEqual([row['session'] for row in sources.versions()], [own, foreign])
                    self.assertTrue(sources.call('read_submitted_file', {
                        'round': 1, 'parent': 2, 'path': 'main.leek'})['content'])
                    with self.assertRaises(ArenaError):
                        sources.call('read_submitted_file', {'round': 1, 'parent': 3, 'path': 'main.leek'})
            finally:
                journal.db.close()
