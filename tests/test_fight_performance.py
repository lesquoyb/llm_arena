"""Compute/publication separation and bounded diagnostic samples."""
import tempfile
import threading
import time
import unittest
from pathlib import Path
from arena.core import read_json,write_json
from arena.fight_pool import run
from arena.fight_history import read
from arena import io_metrics


class FightPerformanceTests(unittest.TestCase):
    def test_compute_replacement_starts_while_a_result_is_publishing(self):
        replacement=threading.Event();saved=[]
        def execute(job):
            if job['seed']>=2:replacement.set()
            time.sleep(.01)
            return {'status':'completed'}
        def save(job,result):
            if not saved:self.assertTrue(replacement.wait(5),'Compute slots were held until publication')
            saved.append(job['seed'])
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            run([{'participants':['a','b'],'seed':i} for i in range(8)],execute,save,limit=2,out=root,kind='tournament_fight')
            self.assertEqual(sorted(saved),list(range(8)))
            latest=read_json(root/'fight-performance.json')
            self.assertEqual(latest['publication_queue'],0)
            self.assertEqual(latest['computing_workers'],0)
            self.assertGreater(latest['io']['json_write_calls'],0)
            self.assertTrue(read(root))
        self.assertFalse(io_metrics.enabled)

    def test_io_counters_are_disabled_outside_measurement(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'value.json'
            with io_metrics.capture() as baseline:
                write_json(path,{'value':1});self.assertEqual(read_json(path),{'value':1})
                measured=io_metrics.snapshot(baseline)
                self.assertEqual(measured['json_read_calls'],1)
                self.assertEqual(measured['json_parse_calls'],1)
                self.assertEqual(measured['json_write_calls'],1)
            before=io_metrics.snapshot();read_json(path)
            self.assertEqual(before,io_metrics.snapshot())
