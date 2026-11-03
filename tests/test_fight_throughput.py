"""Physical execution rates must not count reference cache hits as engine work."""
import unittest
from arena.fight_throughput import add, rate


def expected(engine=0, cache=0, failed=0, turns=0, operations=0):
    return {'engine_per_minute':engine,'cache_per_minute':cache,'failed_per_minute':failed,
            'turns_per_minute':turns,'operations_per_minute':operations}


class FightThroughputTests(unittest.TestCase):
    def test_rolling_window_separates_cache_and_failed_attempts(self):
        buckets={}
        add(buckets,{'status':'completed','turns':7,'team_metrics':{'0':{'operations':40},'1':{'operations':2}}},100)
        add(buckets,{'status':'completed','turns':9,'reference_cache':{'hit':True}},101)
        add(buckets,{'status':'timeout','turns':3},102)
        self.assertEqual(rate(buckets,103),expected(engine=1,cache=1,failed=1,turns=7,operations=42))
        self.assertEqual(rate(buckets,160),expected(cache=1,failed=1))
        self.assertEqual(rate(buckets,163),expected())
        add(buckets,{'status':'completed'},164)
        self.assertEqual(list(buckets),['164'])


if __name__ == '__main__':
    unittest.main()
