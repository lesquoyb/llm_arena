"""Reference replay cache integrity and input identity."""
import tempfile
import unittest
from pathlib import Path

from arena.core import ROOT, copy_submission, digest, file_hash, make_scenario, read_json, submission, write_json
from arena.reference_cache import fight


class FixtureEngine:
    identity = {'fixture': 'reference-cache'}
    timeout = 1

    def __init__(self, root):
        self.reference_cache_directory = root / 'cache'
        self.calls = 0

    def fight(self, sources, infos, config, seed, work):
        self.calls += 1
        for side, (source, info) in enumerate(zip(sources, infos), 1):
            copy_submission(source, work / 'strategies' / str(side), info)
        scenario = make_scenario(config, [info['entrypoint'] for info in infos], seed, [info.get('team') for info in infos])
        write_json(work / 'scenario.json', scenario)
        write_json(work / 'provenance.json', {'engine': self.identity, 'submissions': infos, 'scenario_sha256': digest(scenario)})
        write_json(work / 'outcome.json', {'winner': -1})
        result = {'status': 'completed', 'elapsed_seconds': 3, 'outcome_sha256': file_hash(work / 'outcome.json')}
        write_json(work / 'result.json', result)
        return result


class ReferenceCacheTests(unittest.TestCase):
    def test_reuse_invalidation_corruption_and_portable_snapshots(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sources = [root / 'a', root / 'b']
            for index, source in enumerate(sources):
                source.mkdir()
                (source / 'main.leek').write_text('var value = ' + str(index) + ';')
            infos = [submission(source, 'main.leek') for source in sources]
            scenario = read_json(ROOT / 'configs/offline-complete.json')['scenario']
            engine = FixtureEngine(root)
            def run(name, seed=101, config=None, paths=None, submissions=None):
                return fight(engine, paths or sources, submissions or infos, config or scenario, seed, root / name)
            first = run('first')
            cached = run('cached')
            self.assertEqual(engine.calls, 1)
            self.assertTrue(cached['reference_cache']['hit'])
            self.assertEqual(cached['elapsed_seconds'], 0)
            self.assertEqual(cached['reference_cache']['original_elapsed_seconds'], 3)
            run('seed', seed=102)
            run('reversed', paths=list(reversed(sources)), submissions=list(reversed(infos)))
            engine.timeout = 2
            run('timeout')
            engine.identity = {'fixture': 'changed'}
            run('engine')
            self.assertEqual(engine.calls, 5)
            engine.timeout = 1
            engine.identity = {'fixture': 'reference-cache'}
            entry = engine.reference_cache_directory / first['reference_cache']['key']
            (entry / 'files/outcome.json').write_text('{}')
            run('repaired')
            self.assertEqual(engine.calls, 6)
            self.assertEqual(read_json(root / 'first/outcome.json'), {'winner': -1})
            self.assertEqual(submission(root / 'cached/strategies/1', 'main.leek'), infos[0])
            self.assertEqual(file_hash(root / 'cached/outcome.json'), cached['outcome_sha256'])

    def test_simultaneous_identical_requests_compute_once(self):
        from concurrent.futures import ThreadPoolExecutor
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            source=root/'source';source.mkdir()
            (source/'main.leek').write_text('var v = 1;')
            infos=[submission(source,'main.leek')]*2
            scenario=read_json(ROOT/'configs/offline-complete.json')['scenario']
            engine=FixtureEngine(root)
            with ThreadPoolExecutor(max_workers=4) as pool:
                results=list(pool.map(lambda index:fight(engine,[source,source],infos,scenario,101,root/str(index)),range(4)))
            self.assertEqual(engine.calls,1)
            self.assertEqual(sum(result['reference_cache']['hit'] for result in results),3)
