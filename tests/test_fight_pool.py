"""Engine concurrency keeps journal and result publication on the coordinator."""
import tempfile
import threading
import unittest
from pathlib import Path
from arena.fight_pool import run
from arena.reference_strategies import repetitions


class FightPoolTests(unittest.TestCase):
    def test_fight_concurrency_has_no_arbitrary_upper_bound(self):
        from arena.core import ROOT, ArenaError, read_json
        from arena.experiment import validate_config
        value=read_json(ROOT/'configs/offline-complete.json')
        for workers in (17,50,256):
            value['parallel_fights']=workers;validate_config(value)
        for workers in (0,-1,True,1.5,'50'):
            value['parallel_fights']=workers
            with self.assertRaises(ArenaError):validate_config(value)

    def test_workers_overlap_and_save_on_coordinator(self):
        barrier=threading.Barrier(3)
        coordinator=threading.get_ident()
        saved=[]
        def execute(job):
            self.assertNotEqual(threading.get_ident(),coordinator)
            barrier.wait(timeout=10)
            return job['seed']
        def save(job,result):
            self.assertEqual(threading.get_ident(),coordinator)
            saved.append(result)
        with tempfile.TemporaryDirectory() as directory:
            jobs=[{'participants':['a','b'],'seed':i} for i in range(3)]
            run(jobs,execute,save,limit=3,out=Path(directory),kind='tournament_fight')
        self.assertEqual(sorted(saved),[0,1,2])

    def test_completed_peers_are_saved_when_one_worker_fails(self):
        barrier=threading.Barrier(2)
        saved=[]
        def execute(job):
            barrier.wait(timeout=10)
            if job['seed']==0:raise RuntimeError('worker failed')
            return job['seed']
        with tempfile.TemporaryDirectory() as directory:
            jobs=[{'participants':['a','b'],'seed':i} for i in range(2)]
            with self.assertRaisesRegex(RuntimeError,'worker failed'):
                run(jobs,execute,lambda job,result:saved.append(result),limit=2,
                    out=Path(directory),kind='reference_fight')
        self.assertIn(1,saved)

    def test_fixed_saved_code_has_one_sample_and_generated_models_keep_repetitions(self):
        config={'replicates':6}
        self.assertEqual(repetitions(config,{'provider':'mock','profile':'saved-strategy'}),1)
        self.assertEqual(repetitions(config,{'provider':'openai','model':'example'}),6)
        self.assertEqual(repetitions(config,{'provider':'mock','profile':'repair-and-submit'}),6)
        # Old immutable study schedules retain their original sample count.
        self.assertEqual(repetitions({**config,'_fixed_reference_repetitions':6},
                                     {'provider':'mock','profile':'saved-strategy'}),6)
