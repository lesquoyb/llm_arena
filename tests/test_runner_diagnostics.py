import unittest
from unittest import mock
from arena.runner_diagnostics import Diagnostics


class DiagnosticsTests(unittest.TestCase):
    def test_idle_coordinator_is_reported_without_waiting_for_it_to_respond(self):
        with mock.patch('arena.runner_diagnostics.time.monotonic',return_value=0),mock.patch('builtins.print') as log,mock.patch('arena.runner_diagnostics.faulthandler.dump_traceback') as stacks:
            monitor=Diagnostics(interval=30,stalled_after=120)
            monitor.sample()
            self.assertIn('phase=starting',log.call_args.args[0])
            with mock.patch('arena.runner_diagnostics.time.monotonic',return_value=121):monitor.sample()
            stacks.assert_called_once_with(all_threads=True)
            with mock.patch('arena.runner_diagnostics.time.monotonic',return_value=122):
                monitor.pulse('tournament_fight',computing=2);monitor.sample()
            self.assertEqual(monitor.kind,'tournament_fight')
            self.assertEqual(monitor.counts,{'computing':2})
            self.assertEqual(stacks.call_count,1)
