"""Physical execution rates must not count reference cache hits as engine work."""
import unittest
from arena.fight_throughput import add, rate


class FightThroughputTests(unittest.TestCase):
    def test_rolling_window_separates_cache_and_failed_attempts(self):
        buckets={}
        add(buckets,{'status':'completed'},100)
        add(buckets,{'status':'completed','reference_cache':{'hit':True}},101)
        add(buckets,{'status':'timeout'},102)
        self.assertEqual(rate(buckets,103),{'engine_per_minute':1,'cache_per_minute':1,'failed_per_minute':1})
        self.assertEqual(rate(buckets,160),{'engine_per_minute':0,'cache_per_minute':1,'failed_per_minute':1})
        self.assertEqual(rate(buckets,163),{'engine_per_minute':0,'cache_per_minute':0,'failed_per_minute':0})
        add(buckets,{'status':'completed'},164)
        self.assertEqual(list(buckets),['164'])
