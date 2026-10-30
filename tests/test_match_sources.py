import hashlib
import unittest
from arena.core import ArenaError,scratch_directory,write_json,submission
from arena_web.data import Store


class ExecutedMatchSourcesTests(unittest.TestCase):
    def test_preview_uses_match_snapshot_and_checks_its_fingerprint(self):
        with scratch_directory() as root:
            store=Store(root/'runs',root/'settings');out=store.runs/'run'
            write_json(out/'experiment.json',{'config':{}})
            work=out/'matches'/'fight'/'attempt-1'
            infos=[]
            for side in (1,2):
                directory=work/'strategies'/str(side);directory.mkdir(parents=True)
                (directory/'main.leek').write_text('var side = '+str(side)+';\n',encoding='utf-8')
                infos.append(submission(directory))
            write_json(work/'result.json',{'status':'completed'})
            write_json(work/'provenance.json',{'submissions':infos})
            relative=work.relative_to(out).as_posix()
            sources=store.match_sources('run',relative)
            self.assertEqual(len(sources),2)
            self.assertTrue(all(source['available'] for source in sources))
            for side in (0,1):
                source=store.match_source('run',relative,side)
                self.assertIn('side = '+str(side+1),source['content'])
                self.assertEqual(hashlib.sha256(source['content'].encode()).hexdigest(),source['sha256'])
                with self.assertRaises(ArenaError):store.match_source('run',relative,side,'../../experiment.json')
            (work/'strategies/1/main.leek').write_text('changed',encoding='utf-8')
            with self.assertRaisesRegex(ArenaError,'fingerprint'):
                store.match_source('run',relative,0)
            with self.assertRaises(ArenaError):store.match_source('run',relative,2)
