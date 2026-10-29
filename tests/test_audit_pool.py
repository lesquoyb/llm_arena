"""Audit workers never own SQLite/publication and yield without losing checks."""
import threading
import time
import unittest
from arena.audit_pool import scan


class AuditPoolTests(unittest.TestCase):
    def test_provider_readiness_stops_dispatch_and_drains_dispatched_checks(self):
        coordinator=threading.get_ident();accepted=[];started=[]
        def check(value):
            started.append(value);time.sleep(.01);return value
        def accept(value):
            self.assertEqual(threading.get_ident(),coordinator);accepted.append(value)
        paused=scan(range(100),check,accept,interrupted=lambda:bool(accepted),workers=2)
        self.assertTrue(paused)
        self.assertEqual(sorted(accepted),sorted(started))
        self.assertLessEqual(len(started),2)

    def test_corrupt_artifact_failure_is_propagated(self):
        def check(value):raise ValueError('Corrupt artifact')
        with self.assertRaisesRegex(ValueError,'Corrupt artifact'):scan([1],check,lambda value:None)
