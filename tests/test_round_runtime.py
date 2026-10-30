import sqlite3
import unittest
from arena.core import scratch_directory,write_json
from arena.round_runtime import RoundClock,estimate_history,view


class RoundRuntimeTests(unittest.TestCase):
    def test_restart_never_bridges_an_interruption_even_shorter_than_ten_minutes(self):
        with scratch_directory() as out:
            stamp=[0]
            clock=RoundClock(out,now=lambda:stamp[0],wall=lambda:stamp[0])
            clock.mark('conversation',0,'scheduling_preparations');stamp[0]=10;clock.save(False)
            stamp[0]=310
            resumed=RoundClock(out,now=lambda:stamp[0],wall=lambda:stamp[0])
            resumed.mark('conversation',0,'scheduling_preparations');stamp[0]=315
            self.assertEqual(resumed.snapshot()['rounds']['1']['active_seconds'],15)

    def test_concurrent_phases_count_round_total_once_and_rounds_separately(self):
        with scratch_directory() as out:
            stamp=[0];clock=RoundClock(out,now=lambda:stamp[0],wall=lambda:stamp[0])
            clock.mark('conversation',0,'scheduling_preparations');stamp[0]=5
            clock.mark('engine',0,'tournament_fight');stamp[0]=15
            first=clock.snapshot()['rounds']['1']
            self.assertEqual(first['active_seconds'],15)
            self.assertEqual(first['phase_seconds'],{'preparation':15,'tournament':10})
            clock.mark('engine',1,'reference_fight');stamp[0]=20
            snapshot=clock.snapshot()
            self.assertEqual(snapshot['rounds']['1']['active_seconds'],20)
            self.assertEqual(snapshot['rounds']['2']['active_seconds'],5)

    def test_suspended_process_gap_and_stopped_job_are_not_extrapolated(self):
        with scratch_directory() as out:
            stamp=[0];clock=RoundClock(out,now=lambda:stamp[0],wall=lambda:stamp[0])
            clock.mark('engine',0,'tournament_fight');stamp[0]=5;clock.tick()
            stamp[0]=1005;clock.tick();stamp[0]=1010
            snapshot=clock.snapshot()
            self.assertEqual(snapshot['rounds']['1']['active_seconds'],10)
            self.assertEqual(view(snapshot,running=False,now=1020)['rounds'][0]['active_seconds'],10)
            self.assertEqual(view(snapshot,running=True,now=1020)['rounds'][0]['active_seconds'],20)
            self.assertEqual(view(snapshot,running=True,now=2000)['rounds'][0]['active_seconds'],10)

    def test_historical_estimate_uses_timestamps_and_rejects_ten_minute_gaps(self):
        with scratch_directory() as out:
            with sqlite3.connect(out/'journal.sqlite') as db:
                db.execute('CREATE TABLE session_metadata(id TEXT,metadata TEXT)')
                db.execute('CREATE TABLE events(session TEXT,payload TEXT)')
                db.execute('INSERT INTO session_metadata VALUES (?,?)',('s','{"generation":0}'))
                db.executemany('INSERT INTO events VALUES (?,?)',[('s','{"at":'+str(stamp)+'}') for stamp in (100,130,1000,1020)])
            path=out/'fight-performance-history.jsonl'
            path.write_text('{"observed_at":110,"generation":0}\n{"observed_at":200,"generation":1}\n{"observed_at":250,"generation":1}\ntruncated\n')
            result=estimate_history(out,1100)
            self.assertEqual(result['1']['active_seconds'],50)
            self.assertEqual(result['2']['active_seconds'],50)
            self.assertEqual(result['1']['estimated_seconds'],50)
