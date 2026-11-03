"""Fast resume still rejects changed files, bindings and source directory entries."""
from pathlib import Path
import os
import tempfile
import unittest
from unittest.mock import patch
from arena.core import file_hash,write_json
from arena.verification_cache import VerificationCache,fingerprint


class VerificationCacheTests(unittest.TestCase):
    def test_persisted_hash_is_reused_but_preserved_mtime_cannot_hide_an_edit(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);path=root/'result.json';path.write_bytes(b'first')
            first=VerificationCache(root);expected=first.hash(path);first.flush()
            if fingerprint(path) is None:self.skipTest('Filesystem change stamps unavailable')
            again=VerificationCache(root)
            with patch('arena.verification_cache.file_hash',side_effect=AssertionError('Unchanged file reread')):
                self.assertEqual(again.hash(path),expected)
            stamp=path.stat();path.write_bytes(b'other');os.utime(path,ns=(stamp.st_atime_ns,stamp.st_mtime_ns))
            self.assertNotEqual(again.hash(path),expected)
            self.assertEqual(again.hash(path),file_hash(path))

    def test_receipt_tracks_bindings_files_and_added_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);work=root/'match';sources=work/'strategies/1';sources.mkdir(parents=True)
            code=sources/'main.leek';code.write_text('var x = 1')
            cache=VerificationCache(root);cache.hash(code)
            cache.remember_receipt(work,'binding',[code],{sources:fingerprint(sources,directory=True)})
            cache.flush();cache=VerificationCache(root)
            if fingerprint(code) is None or fingerprint(sources,directory=True) is None:self.skipTest('Filesystem change stamps unavailable')
            self.assertTrue(cache.checked_receipt(work,'binding'))
            self.assertFalse(cache.checked_receipt(work,'different scenario or source'))
            (sources/'extra.leek').write_text('var y = 2')
            self.assertFalse(cache.checked_receipt(work,'binding'))
            code.unlink()
            self.assertFalse(cache.checked_receipt(work,'binding'))

    def test_full_audit_bypasses_derived_hash_and_record_caches(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);path=root/'record.json';value={'result':'completed'};write_json(path,value)
            cache=VerificationCache(root);cache.remember_record(path,value);cache.flush()
            with patch.dict(os.environ,{'ARENA_FULL_AUDIT':'1'}):
                full=VerificationCache(root)
                self.assertEqual(full.read_record(path),value)
                self.assertEqual(full.hash(path),file_hash(path))
                self.assertEqual(full.stats()['cached_records'],0)
                self.assertEqual(full.stats()['computed_hashes'],1)

    def test_derived_cache_connections_do_not_lock_run_cleanup(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);path=root/'file';path.write_bytes(b'value')
            cache=VerificationCache(root);cache.hash(path);cache.flush()
            cache.path.unlink()
            self.assertFalse(cache.path.exists())

    def test_cached_session_proof_does_not_hide_database_or_metadata_changes(self):
        import json
        from arena.experiment import Journal
        from arena.core import ArenaError
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);journal=Journal(root)
            try:
                journal.save('model',{'model':'model','status':'submitted','calls':3,'history':[]},'fixture')
                journal.verify()
                original=journal.db.execute("SELECT state FROM sessions WHERE id='model'").fetchone()[0]
                changed=json.loads(original);changed['calls']=4
                with journal.db:journal.db.execute("UPDATE sessions SET state=? WHERE id='model'",(json.dumps(changed),))
                with self.assertRaisesRegex(ArenaError,'checkpoint'):journal.verify()
                with journal.db:journal.db.execute("UPDATE sessions SET state=? WHERE id='model'",(original,))
                with journal.db:journal.db.execute("UPDATE session_metadata SET metadata='{}' WHERE id='model'")
                with self.assertRaisesRegex(ArenaError,'metadata index'):journal.verify()
            finally:journal.db.close()

    def test_evidence_event_preserves_frozen_session_checkpoint(self):
        from arena.experiment import Journal
        with tempfile.TemporaryDirectory() as directory:
            journal=Journal(Path(directory))
            try:
                state={'model':'model','status':'submitted','calls':7,'history':[{'role':'user','content':'keep'}]}
                journal.save('model',state,'fixture')
                before=journal.db.execute("SELECT state FROM sessions WHERE id='model'").fetchone()[0]
                journal.record('model','reference_match',{'result':'complete'})
                after=journal.db.execute("SELECT state FROM sessions WHERE id='model'").fetchone()[0]
                self.assertEqual(before,after)
                journal.verify()
            finally:journal.db.close()

    def test_damaged_derived_index_falls_back_to_original_records(self):
        import sqlite3
        from contextlib import closing
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);path=root/'record.json';value={'result':'completed'};write_json(path,value)
            if fingerprint(path) is None:self.skipTest('Filesystem change stamps unavailable')
            cache=VerificationCache(root);cache.remember_record(path,value);cache.flush()
            with closing(sqlite3.connect(cache.path)) as db:
                with db:db.execute("UPDATE verification_entries SET payload='{}' WHERE kind='record'")
            damaged=VerificationCache(root)
            self.assertEqual(damaged.read_record(path),value)
            self.assertGreater(damaged.stats()['cache_errors'],0)
            damaged.remember_record(path,value);damaged.flush()
            repaired=VerificationCache(root)
            self.assertEqual(repaired.read_record(path),value)
            self.assertEqual(repaired.stats()['cache_errors'],0)
