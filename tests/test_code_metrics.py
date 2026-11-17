"""Static AI size and engine operations aggregated for complexity views."""
import unittest

from arena.core import scratch_directory, write_json
from arena_web.code_metrics import measure, submission_metrics
from arena_web.fights import expand


class CodeMetricsTests(unittest.TestCase):
    def test_counts_code_reachable_from_the_entrypoint_without_comments(self):
        with scratch_directory() as root:
            (root / 'main.leek').write_text(
                '// header comment\n'
                'include("lib/helpers.leek")\n'
                '\n'
                '/* block\n   comment */\n'
                'function main() {\n'
                '    var url = "http://not-a-comment"; // trailing\n'
                '    return helper(url)\n'
                '}\n', encoding='utf-8')
            (root / 'lib').mkdir()
            (root / 'lib/helpers.leek').write_text('function helper(x) {\n  return x\n}\nclass Unit {\n}\n', encoding='utf-8')
            # A sparring opponent for preparation tests is not part of the fighting AI.
            (root / 'sparring.leek').write_text('function idle() {\n}\n' * 50, encoding='utf-8')
            value = measure(root, 'main.leek')
            self.assertEqual(value['files'], 2)
            self.assertEqual(value['lines'], 5 + 5)
            self.assertEqual(value['functions'], 2)
            self.assertEqual(value['classes'], 1)

    def test_includes_cannot_leave_the_submission_and_missing_code_is_unknown(self):
        with scratch_directory() as root:
            (root / 'secret.leek').write_text('var a = 1\n' * 9, encoding='utf-8')
            (root / 'submission').mkdir()
            (root / 'submission/main.leek').write_text('include("../secret.leek")\nvar b = 2\n', encoding='utf-8')
            self.assertEqual(measure(root / 'submission', 'main.leek')['lines'], 2)
            self.assertIsNone(measure(root / 'submission', 'absent.leek'))
            self.assertIsNone(submission_metrics(root, None))
            self.assertEqual(submission_metrics(root, {'entrypoint': 'main.leek', 'sha256': 'x' * 64})['files'], 1)


class OperationGroupTests(unittest.TestCase):
    def test_fight_groups_sum_operations_per_side_and_follow_orientation(self):
        from arena_web.data import Store
        with scratch_directory() as root:
            store = Store(root / 'runs', root / 'state')
            run = store.runs / 'run'
            write_json(run / 'experiment.json', {'manifest': {'strategies': []}})
            def record(name, sides, winner, ops, turns, limits=(0, 0)):
                write_json(run / f'tournament/records/{name}.json', {
                    'match': {'sides': sides, 'seed': {'one': 1, 'two': 2}[name], 'mirror': False}, 'directory': f'matches/{name}',
                    'result': {'status': 'completed', 'winner_side': winner, 'turns': turns,
                               'team_metrics': {str(side): {'operations': ops[side], 'errors': 0, 'operation_limit_hits': limits[side]}
                                                for side in (0, 1)}}})
            record('one', ['a', 'b'], 0, (1000, 10), 4, (1, 0))
            # Same pair, reversed sides: folded into the a-vs-b group with its operations swapped back.
            record('two', ['b', 'a'], 1, (30, 3000), 6)
            groups = store.fight_groups('run')
            self.assertEqual(groups['columns'][-6:], ['operations_a', 'operations_b', 'measured_turns', 'measured_fights',
                                                      'operation_limit_hits_a', 'operation_limit_hits_b'])
            [row] = groups['rows']
            self.assertEqual(groups['ids'][row[3]], 'a')
            self.assertEqual(row[13:], [4000, 40, 10, 2, 1, 0])
            expanded = list(expand(groups))
            self.assertEqual(sum(match['count'] for match in expanded), 2)
            # Totals ride on one outcome only, so per-model sums do not double count.
            carried = [match['operations'] for match in expanded if 'operations' in match]
            self.assertEqual(carried, [{'sides': [4000, 40], 'turns': 10, 'fights': 2, 'limit_hits': [1, 0]}])


if __name__ == '__main__':
    unittest.main()
