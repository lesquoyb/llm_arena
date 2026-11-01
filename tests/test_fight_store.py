"""Per-stage SQLite fight stores, compaction of legacy folders and indexed overviews."""
import contextlib
import io
import json
import unittest
from pathlib import Path

from arena.core import ArenaError, ROOT, load_manifest, read_json, scratch_directory, write_json
from arena.fight_store import FightStore, read_bytes, release, stage_records, verify_stored_fight


class FightStoreTests(unittest.TestCase):
    def test_contents_are_deduplicated_compressed_and_checked(self):
        with scratch_directory() as root:
            store = FightStore.at(root / 'stage', create=True)
            store.put_many([('matches/a/attempt-1/stdout.log', b''), ('matches/b/attempt-1/stdout.log', b''),
                            ('matches/a/attempt-1/outcome.json', b'{"fight": "' + b'x' * 5000 + b'"}')])
            self.assertEqual(store.db.execute('SELECT count(*) FROM blobs').fetchone()[0], 2)
            self.assertLess(store.path.stat().st_size, 60_000)
            self.assertEqual(read_bytes(root / 'stage/matches/a/attempt-1/stdout.log'), b'')
            self.assertEqual(store.list('matches/a'), ['matches/a/attempt-1/outcome.json', 'matches/a/attempt-1/stdout.log'])
            # A blob whose bytes no longer match their hash is rejected on read.
            sha = store.sha256('matches/a/attempt-1/outcome.json')
            import zlib
            with store.db:
                store.db.execute('UPDATE blobs SET data=? WHERE sha256=?', (zlib.compress(b'{}'), sha))
            store.verified.clear()
            with self.assertRaisesRegex(ArenaError, 'modified'):
                store.get('matches/a/attempt-1/outcome.json')
            with self.assertRaises(ArenaError):
                store.put('../escape.json', b'{}')

    def test_tournament_stores_fights_and_detects_changed_sources(self):
        from arena.engine import Engine
        from arena.tournament import report, run_tournament, verify_record
        manifest = load_manifest(ROOT / 'examples/tournament.json')
        manifest['strategies'] = manifest['strategies'][:2]
        manifest['seeds'] = [101]
        manifest['include_mirrors'] = False
        with scratch_directory() as root, contextlib.redirect_stdout(io.StringIO()):
            out = root / 'tournament'
            first = run_tournament(Engine(), manifest, out)
            self.assertEqual(first['completed'], 2)
            self.assertFalse((out / 'matches').exists() or (out / 'records').exists())
            store, records = stage_records(out)
            self.assertEqual(len(records), 2)
            self.assertEqual(report(out)['completed'], 2)
            name, record = next(iter(records.values()))
            source = next(path for path in store.list(record['directory'] + '/strategies/1'))
            store.put(source, b'// changed')
            with self.assertRaisesRegex(ArenaError, 'Frozen source was modified'):
                report(out)

    def test_compaction_moves_legacy_fights_and_keeps_them_verifiable(self):
        from arena.engine import Engine
        from arena.storage import compact, status
        from arena.tournament import report, run_tournament
        manifest = load_manifest(ROOT / 'examples/tournament.json')
        manifest['strategies'] = manifest['strategies'][:2]
        manifest['seeds'] = [101]
        with scratch_directory() as root, contextlib.redirect_stdout(io.StringIO()):
            run = root / 'run'
            write_json(run / 'experiment.json', {'manifest': {'strategies': []}})
            out = run / 'tournament'
            expected = run_tournament(Engine(), manifest, out)
            # Recreate the legacy layout from the stored fights.
            store, records = stage_records(out)
            for name in store.list('records') + store.list('matches'):
                path = out / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(store.get(name))
            release(out)
            (out / 'fights.sqlite').unlink()
            for suffix in ('-wal', '-shm'):
                Path(str(out / 'fights.sqlite') + suffix).unlink(missing_ok=True)
            self.assertTrue(status(run)['needs_compaction'])
            self.assertEqual(report(out)['completed'], expected['completed'])
            result = compact(run)
            self.assertGreater(result['files_stored'], 4)
            self.assertFalse((out / 'matches').exists())
            self.assertFalse(status(run)['needs_compaction'])
            self.assertEqual(report(out)['standings'], expected['standings'])


class IndexedOverviewTests(unittest.TestCase):
    def test_index_reads_stored_and_legacy_records_incrementally(self):
        from arena_web.data import Store
        with scratch_directory() as root:
            store = Store(root / 'runs', root / 'state')
            run = store.runs / 'run'
            write_json(run / 'experiment.json', {'manifest': {'strategies': []}})
            legacy = {'match': {'sides': ['a', 'b'], 'seed': 1, 'mirror': False}, 'directory': 'matches/one/attempt-1',
                      'result': {'status': 'completed', 'winner_side': 0, 'turns': 12}}
            write_json(run / 'tournament/records/one.json', legacy)
            fights = FightStore.at(run / 'tournament', create=True)
            fights.put_json('records/two.json', {**legacy, 'match': {**legacy['match'], 'seed': 2}, 'directory': 'matches/two/attempt-1',
                                                 'result': {'status': 'completed', 'winner_side': -1, 'turns': 1000}})
            groups = store.fight_groups('run')
            # A-vs-B fights of one pair fold into one group: one win for a, one draw.
            counts = [row[7:11] for row in groups['rows']]
            self.assertEqual(sorted(map(tuple, counts)), [(1, 0, 1, 0)])
            page = store.fight_page('run', {'kind': 'competition', 'outcome': 'draw'}, {})
            self.assertEqual([row['seed'] for row in page['matches']], [2])
            # A later stored record appears without rescanning legacy folders.
            fights.put_json('records/three.json', {**legacy, 'match': {**legacy['match'], 'seed': 3}, 'directory': 'matches/three/attempt-1'})
            self.assertEqual(store.fight_page('run', {'kind': 'competition'}, {})['total'], 3)
            lengths = store.fight_lengths('run')
            self.assertEqual(sum(row['fights'] for row in lengths['series'] if row['model'] == '*'), 3)
            release(run)


class FailedJobReasonTests(unittest.TestCase):
    def test_failed_job_reports_the_error_that_ended_it(self):
        from arena_web.jobs import failure_reason
        with scratch_directory() as root:
            log=root/'job.log'
            log.write_text('[arena] phase=idle\nArena error: Saved strategy x requires its original scenario.\n',encoding='utf-8')
            self.assertEqual(failure_reason(log),'Arena error: Saved strategy x requires its original scenario.')
            log.write_text('Traceback (most recent call last):\n  File "a.py", line 1 in run\nKeyError: \'scenario\'\n',encoding='utf-8')
            self.assertEqual(failure_reason(log),"Runner error: KeyError: 'scenario'")
            self.assertIn('run log',failure_reason(root/'missing.log'))


class StallRuleTests(unittest.TestCase):
    def test_scenario_field_is_optional_bounded_and_briefed(self):
        from arena.core import DEFAULT_SCENARIO, make_scenario, validate_scenario
        from arena.user_briefing import render
        self.assertNotIn('stall_turns', make_scenario(DEFAULT_SCENARIO, ['main.leek'] * 2, 101))
        scenario = {**DEFAULT_SCENARIO, 'stall_turns': 100}
        self.assertEqual(make_scenario(scenario, ['main.leek'] * 2, 101)['stall_turns'], 100)
        for bad in (5, 2000, True, 1.5):
            with self.assertRaises(ArenaError):
                validate_scenario({**DEFAULT_SCENARIO, 'stall_turns': bad})
        self.assertIn('100 consecutive turns', render({'scenario': scenario}))

    def test_declared_adapter_successor_keeps_old_competitions_resumable(self):
        from arena.recovery import engine_compatible
        compatibility = read_json(ROOT / 'engine/adapter-compatibility.json')['equivalents']
        current, entry = next(iter(compatibility.items()))
        base = {'jar_sha256': 'jar', 'build_script_sha256': 'build', 'bridge_sha256': 'a'}
        self.assertTrue(engine_compatible({**base, 'adapter_sha256': entry['previous'][0]},
                                          {**base, 'adapter_sha256': current, 'bridge_sha256': 'b'}))
        self.assertFalse(engine_compatible({**base, 'adapter_sha256': 'unknown'},
                                           {**base, 'adapter_sha256': current}))


class ParallelJobsTests(unittest.TestCase):
    def test_two_competitions_can_run_and_stop_independently(self):
        from unittest import mock
        from arena_web.data import Store
        from arena_web.jobs import Jobs
        with scratch_directory() as root:
            jobs = Jobs(Store(root / 'runs', root / 'state'))
            first, second = mock.Mock(), mock.Mock()
            for process in (first, second):
                process.poll.return_value = None
            jobs.active = {'a': (first, {'id': '1', 'run': 'a', 'status': 'running'}),
                           'b': (second, {'id': '2', 'run': 'b', 'status': 'running'})}
            jobs.rows = [row for _, row in jobs.active.values()]
            self.assertIs(jobs.running('a')[0], first)
            self.assertIs(jobs.running('b')[0], second)
            self.assertIsNone(jobs.running('c')[0])
            jobs.stop('2')
            self.assertEqual(jobs.active['b'][1]['status'], 'stopping')
            self.assertEqual(jobs.active['a'][1]['status'], 'running')
            first.send_signal.assert_not_called()


if __name__ == '__main__':
    unittest.main()


class EvaluationSealTests(unittest.TestCase):
    def test_completed_evaluation_is_reused_until_its_records_change(self):
        from unittest import mock
        from arena.core import copy_submission, submission
        from arena.evolution import references
        from test_roster import FixtureEngine
        config = {**read_json(ROOT / 'configs/offline-complete.json'), 'final_seeds': [101]}
        with scratch_directory() as out:
            sources = []
            for name in ('rush', 'passive'):
                info = submission(ROOT / 'examples/strategies' / name)
                copy_submission(ROOT / 'examples/strategies' / name, out / 'sources' / name, info)
                sources.append({'id': name, 'path': out / 'sources' / name, 'submission': info})
            journal = SimpleJournal(out)
            first = references(FixtureEngine(), config, out, journal, sources[:1], 'g1-panel', sources[1:])
            self.assertTrue((out / 'evaluations/g1-panel/seal.json').is_file())
            with mock.patch('arena.fight_store.verify_stored_fight', side_effect=AssertionError('re-checked a sealed fight')):
                self.assertEqual(references(FixtureEngine(), config, out, journal, sources[:1], 'g1-panel', sources[1:]), first)
            # Any record change (here a retry publishing a new record) breaks the seal.
            store = FightStore.at(out / 'evaluations/g1-panel', create=True)
            name = store.list('records')[0]
            store.put(name, store.get(name))
            from arena.run_memory import forget
            forget(out)  # A new process: only the seal could skip the checks.
            with mock.patch('arena.fight_store.verify_stored_fight') as verify:
                references(FixtureEngine(), config, out, journal, sources[:1], 'g1-panel', sources[1:])
                self.assertTrue(verify.called)
            release(out)


class TournamentSealTests(unittest.TestCase):
    def test_finished_round_is_not_rechecked_after_a_restart(self):
        from types import SimpleNamespace
        from unittest import mock
        from arena import greedy
        from arena.run_memory import forget
        config = read_json(ROOT / 'configs/offline-complete.json')
        states = {sid: {'model': 'm', 'replicate': 0, 'generation': 1, 'parent': 'p', 'submission': {'entrypoint': 'main.leek', 'sha256': sid}}
                  for sid in ('a', 'b')}
        journal = SimpleNamespace(metadata=lambda: states)
        expected = 2 * len(config['final_seeds']) + (2 * len(config['final_seeds']) if config['include_mirrors'] else 0)
        done = {'completed': expected, 'failed': 0, 'pending': 0}
        with scratch_directory() as out:
            (out / 'g1-tournament').mkdir()
            with mock.patch('arena.greedy.run_tournament', return_value=done):
                self.assertEqual(greedy.evaluate(None, config, out, journal, 1), done)
            self.assertTrue((out / 'g1-tournament/seal.json').is_file())
            forget(out)  # A new process: only the seal can skip the checks.
            with mock.patch('arena.greedy.run_tournament', side_effect=AssertionError('re-checked a sealed round')):
                self.assertEqual(greedy.evaluate(None, config, out, journal, 1), done)
            # A new or retried fight record breaks the seal.
            forget(out)
            write_json(out / 'g1-tournament/records/x.json', {})
            with mock.patch('arena.greedy.run_tournament', return_value=done) as tournament:
                greedy.evaluate(None, config, out, journal, 1)
                self.assertTrue(tournament.called)


class SimpleJournal:
    """Evaluation runs only append evidence through the journal."""
    def __init__(self, out):
        self.out = out
    def record(self, *args):
        pass
