"""Accepting an additional engine version must not invalidate old valid proofs."""
import unittest
from unittest import mock
from arena.core import DEFAULT_SCENARIO,scratch_directory,write_json,submission,make_scenario,digest,file_hash,ArenaError
from arena.tournament import verify_record
from arena.verification_cache import VerificationCache,fingerprint


class ResumeEngineReceiptTests(unittest.TestCase):
    def test_old_runner_replay_is_not_copied_to_seed_an_incompatible_cache_key(self):
        from arena.reference_cache import seed
        from types import SimpleNamespace
        with scratch_directory() as root:
            work=root/'match';write_json(work/'provenance.json',{'engine':{'runner':'old'}})
            engine=SimpleNamespace(identity={'runner':'new'},timeout=90,reference_cache_directory=root/'cache')
            infos=[{'entrypoint':'main.leek'},{'entrypoint':'main.leek'}]
            with mock.patch('arena.reference_cache.shutil.copytree',side_effect=AssertionError('Old replay copied for a new runner cache key')):
                seed(engine,infos,DEFAULT_SCENARIO,101,work)
            self.assertFalse((root/'cache').exists())
    def test_expanded_engine_history_reuses_proof_but_removed_engine_and_edits_are_rejected(self):
        with scratch_directory() as root:
            work=root/'matches/one';strategies={};infos=[]
            for side,name in enumerate(('a','b'),1):
                source=work/'strategies'/str(side);source.mkdir(parents=True)
                (source/'main.leek').write_text('var value = 1;')
                info=submission(source);infos.append(info);strategies[name]={'submission':info}
            old={'runner_sha256':'old','jar_sha256':'pinned'};new={'runner_sha256':'new','jar_sha256':'pinned'}
            scenario=make_scenario(DEFAULT_SCENARIO,['main.leek','main.leek'],101,[None,None])
            write_json(work/'outcome.json',{'winner':0})
            result={'status':'completed','outcome_sha256':file_hash(work/'outcome.json')}
            write_json(work/'result.json',result);write_json(work/'scenario.json',scenario)
            write_json(work/'provenance.json',{'engine':old,'submissions':infos,'scenario_sha256':digest(scenario)})
            record={'directory':'matches/one','match':{'sides':['a','b'],'seed':101,'mirror':False},'result':result}
            context={'strategies':strategies,'engines':[old],'experiment':{'manifest':{'scenario':DEFAULT_SCENARIO}},'hashes':VerificationCache(root)}
            verify_record(root,record,context=context);context['hashes'].flush()
            if fingerprint(work/'outcome.json') is None:self.skipTest('Filesystem change stamps unavailable')
            resumed={**context,'engines':[new,old],'hashes':VerificationCache(root)}
            with mock.patch('arena.tournament.read_json',side_effect=AssertionError('Unchanged replay was reopened')):
                verify_record(root,record,context=resumed)
            self.assertEqual(resumed['hashes'].stats()['unchanged_fights'],1)
            self.assertEqual(resumed['hashes'].stats()['bytes_read'],0)
            removed={**context,'engines':[new],'hashes':VerificationCache(root)}
            with self.assertRaisesRegex(ArenaError,'provenance'):verify_record(root,record,context=removed)
            (work/'outcome.json').write_text('{"winner":1}')
            with self.assertRaisesRegex(ArenaError,'modified'):verify_record(root,record,context=resumed)
