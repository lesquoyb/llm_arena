"""Engine-only retries inherit the current roster and live worker setting."""
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from arena.core import read_json, write_json
from arena.fight_recovery import run


class FightRecoveryWorkerTests(unittest.TestCase):
    def test_recovery_uses_roster_workers_and_live_override(self):
        for live,expected in ((None,4),(8,8)):
            with self.subTest(live=live),tempfile.TemporaryDirectory() as directory:
                root=Path(directory)
                write_json(root/'experiment.json',{'config':{'parallel_fights':1},'engine':{}})
                write_json(root/'tournament/experiment.json',{'manifest':{'strategies':[]}})
                if live:write_json(root/'execution-control.json',{'parallel_fights':live})
                journal=SimpleNamespace(out=root,metadata=lambda:{})
                engine=SimpleNamespace(identity={})
                with patch('arena.fight_recovery.engine_compatible',return_value=True), \
                     patch('arena.fight_recovery.effective',return_value={'parallel_fights':1}), \
                     patch('arena.fight_recovery.snapshot',return_value={'parallel_fights':4}), \
                     patch('arena.tournament.run_tournament',return_value={'failed':0,'pending':0}) as tournament:
                    result=run(root,engine=engine,journal=journal,cooperative=True)
                self.assertFalse(result['deferred'])
                self.assertEqual(tournament.call_args.kwargs['parallel_fights'],4)
                self.assertEqual(read_json(root/'activity.json')['parallel_fights'],expected)
