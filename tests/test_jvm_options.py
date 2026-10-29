"""JVM tuning preserves legacy overrides and separates runtime from game rules."""
import unittest
from arena.core import ArenaError
from arena.jvm_options import settings
from arena.recovery import engine_compatible


class JVMOptionTests(unittest.TestCase):
    def test_pooled_default_and_explicit_legacy_profiles(self):
        profile,options,recycle=settings(True,{})
        self.assertEqual(profile,'throughput')
        self.assertIn('-Xms32m',options)
        self.assertNotIn('-XX:+DisableExplicitGC',options)
        self.assertEqual(recycle,32)
        self.assertEqual(settings(False,{})[0],'startup')
        for pooled in (False,True):
            self.assertEqual(settings(pooled,{'ARENA_JVM_PROFILE':'full'})[1],['-Xmx512m','-Dfile.encoding=UTF-8'])
            self.assertNotIn('-XX:TieredStopAtLevel=1',settings(pooled,{'ARENA_JVM_PROFILE':'optimizing'})[1])
        options.append('caller mutation')
        self.assertNotIn('caller mutation',settings(True,{})[1])

    def test_recycle_is_configurable_and_rejects_invalid_values(self):
        self.assertEqual(settings(True,{'ARENA_JVM_RECYCLE_MATCHES':'1024'})[2],1024)
        for value in ('0','-1','1.5','invalid'):
            with self.assertRaises(ArenaError):settings(True,{'ARENA_JVM_RECYCLE_MATCHES':value})
        with self.assertRaises(ArenaError):settings(True,{'ARENA_JVM_PROFILE':'invalid'})

    def test_runtime_tuning_can_resume_but_game_changes_cannot(self):
        before={'lock':'same-game','worker_jvm_profile':'startup'}
        after={**before,'worker_jvm_profile':'throughput','worker_jvm_options':['-Xms32m'],'worker_jvm_recycle_matches':256}
        self.assertTrue(engine_compatible(before,after))
        self.assertFalse(engine_compatible(before,{**after,'lock':'different-game'}))
