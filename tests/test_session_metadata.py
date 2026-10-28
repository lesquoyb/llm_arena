"""Dashboard metadata must stay faithful to authoritative checkpoints."""
import json
import unittest
from contextlib import closing

from arena.core import ArenaError, ROOT, read_json, scratch_directory
from arena.experiment import Journal, initial_state
from arena_web.data import Store


class SessionMetadataTests(unittest.TestCase):
    def test_index_and_legacy_cache_follow_checkpoint_updates(self):
        with scratch_directory() as root:
            out=root/'run';out.mkdir()
            config=read_json(ROOT/'configs/offline-complete.json')
            store=Store(root,root/'settings')
            journal=Journal(out)
            with closing(journal.db) as db:
                state=initial_state('fixture-r0',config['models'][0],config)
                state['history'].append({'role':'user','content':'reference material '*1000})
                journal.save('fixture-r0',state,'fixture',{})
                fields=('model','status','steps')
                indexed=store.states(out,fields)
                db.execute('DELETE FROM session_metadata');db.commit()
                self.assertEqual(store.states(out,fields),indexed)
                self.assertEqual(store.states(out,fields),indexed)
                state['steps']=7
                journal.save('fixture-r0',state,'changed',{})
                self.assertEqual(store.states(out,fields)['fixture-r0']['steps'],7)
                # Old writers may leave an index whose fingerprint no longer matches.
                db.execute("UPDATE session_metadata SET checkpoint_sha256='stale',metadata='{}'");db.commit()
                self.assertEqual(store.states(out,fields)['fixture-r0']['steps'],7)
                journal.verify()
                journal.save('fixture-r0',state,'restored',{})
                db.execute('UPDATE session_metadata SET metadata=?',(json.dumps({'model':'wrong'}),));db.commit()
                with self.assertRaisesRegex(ArenaError,'metadata index'):
                    journal.verify()
