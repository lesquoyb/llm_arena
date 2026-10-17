"""Lean model payloads retain source text and enforce own-version boundaries."""
import copy
import json
import sqlite3
from contextlib import closing
from unittest import TestCase

from arena.core import ArenaError, scratch_directory, submission, write_json
from arena.model_content import documentation, message_text, tool_text, page
from arena.submitted_versions import OwnSubmissions


class ModelContextTests(TestCase):
    def test_document_json_drops_provenance_and_formats_before_paging(self):
        original={'source_commit':'a'*40,'sources':[{'url':'https://source.invalid','sha256':'b'*64}],
                  'rules':{'life':100,'description':'Actual gameplay rule'}}
        text=documentation('corpus/rules.json',json.dumps(original,indent=2))
        self.assertEqual(json.loads(text),{'rules':original['rules']})
        self.assertNotIn('\n',text)
        first=page(text,{'limit':10},'read_docs',{'path':'corpus/rules.json'})
        self.assertTrue(first['truncated'])
        args=first['continuation']['arguments']
        chunks=[first['content']]
        while args:
            result=page(text,args,'read_docs',{'path':'corpus/rules.json'})
            chunks.append(result['content']);args=(result['continuation'] or {}).get('arguments')
        self.assertEqual(''.join(chunks),text)

    def test_hash_cleanup_does_not_consume_long_runs_of_ordinary_text(self):
        text='a'*17005
        self.assertEqual(documentation('guide.md',text),text)
        self.assertEqual(documentation('guide.md','Commit: `'+('a'*40)+'`.'),'Commit: .')
        code='```leekscript\nvar value = "'+('a'*64)+'";\n```'
        self.assertEqual(documentation('guide.md',code),code)

    def test_source_line_breaks_are_preserved_without_json_string_wrapping(self):
        code='if (true) {\n\tdebug("hello");\n}\n'
        result={'path':'main.leek','content':code,'sha256':'a'*64}
        original=copy.deepcopy(result)
        text=tool_text(result)
        self.assertEqual(text.split('\n',1)[1],code)
        self.assertNotIn('sha256',text)
        self.assertEqual(result,original)
        self.assertEqual(documentation('example.leek',code),code)
        self.assertTrue(message_text({'role':'user','content':'New round\nImprove now','generation':2}).startswith('New round\nImprove now\n'))

    def test_replay_continuation_keeps_test_side_and_section(self):
        result=page('x'*20000,{},'read_replay',{'test_id':'call-1-tool-0','side':1,'section':'logs'})
        self.assertTrue(result['truncated'])
        self.assertEqual(len(result['content']),16000)
        self.assertEqual(result['continuation']['arguments'],{'test_id':'call-1-tool-0','side':1,'section':'logs','offset':16000,'limit':16000})

    def test_only_own_prior_track_sources_can_be_read_and_hashes_are_verified(self):
        with scratch_directory() as out:
            states={}
            for sid,gen,parent,code in [('model-r0',0,None,'// initial'),
                                      ('model-r0-g1-control',1,'model-r0','// control'),
                                      ('model-r0-g1-feedback',1,'model-r0','// feedback secret')]:
                source=out/'sessions'/sid/'submission'
                source.mkdir(parents=True);(source/'main.leek').write_text(code)
                states[sid]={'model':'model','replicate':0,'generation':gen,'parent':parent,'submission':submission(source)}
            with closing(sqlite3.connect(out/'journal.sqlite')) as db, db:
                db.execute('CREATE TABLE sessions (id TEXT PRIMARY KEY,state TEXT)')
                db.executemany('INSERT INTO sessions VALUES (?,?)',[(sid,json.dumps(state)) for sid,state in states.items()])
            access=OwnSubmissions(out,{'model':'model','replicate':0,'generation':2,'parent':'model-r0-g1-control'})
            listing=access.call('list_submissions',{})
            self.assertEqual([row['round'] for row in listing['submissions']],[1,2])
            self.assertEqual(access.call('read_submitted_file',{'round':2,'path':'main.leek'})['content'],'// control')
            self.assertNotIn('sha256',json.dumps(listing))
            with self.assertRaises(ArenaError): access.call('read_submitted_file',{'round':3,'path':'main.leek'})
            with self.assertRaises(ArenaError): access.call('read_submitted_file',{'round':2,'path':'../model-r0-g1-feedback/main.leek'})
            (out/'sessions/model-r0-g1-control/submission/main.leek').write_text('// tampered')
            with self.assertRaisesRegex(ArenaError,'changed'): access.call('read_submitted_file',{'round':2,'path':'main.leek'})
            # Windows rejects deletion if any reader or the fixture kept a handle.
            (out/'journal.sqlite').unlink()
