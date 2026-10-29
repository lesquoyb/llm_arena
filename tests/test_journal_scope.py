"""Journal paging must use the same model/round/track/repetition scope as charts."""
import unittest
from arena.core import ROOT, read_json, scratch_directory, write_json
from arena.experiment import Journal, initial_state
from arena_web.data import Store


class JournalScopeTests(unittest.TestCase):
    def test_count_and_page_use_all_scope_dimensions(self):
        with scratch_directory() as root:
            store=Store(root/'runs',root/'settings');out=store.runs/'run'
            config=read_json(ROOT/'configs/offline-complete.json')
            write_json(out/'experiment.json',{'config':config})
            journal=Journal(out)
            try:
                for model in config['models']:
                    for replicate in range(2):
                        for generation,condition in ((0,'initial'),(1,'control'),(1,'feedback')):
                            sid=f"{model['id']}-r{replicate}"+(f'-g{generation}-{condition}' if generation else '')
                            state=initial_state(sid,model,config)
                            state.update(replicate=replicate,generation=generation,condition=condition)
                            journal.save(sid,state,'scope_fixture')
                            journal.record(sid,'scope_fixture',{'second':True})
            finally:journal.db.close()
            model=config['models'][0]['id'];sid=model+'-r1-g1-feedback'
            scope={'round':'2','track':'feedback','replicate':'2'}
            page=store.events('run',offset=1,limit=1,model=model,scope=scope)
            self.assertEqual(page['total'],2)
            self.assertEqual([row['session'] for row in page['events']],[sid])
            empty=store.events('run',model=model,scope={**scope,'round':'9'})
            self.assertEqual(empty,{'total':0,'events':[]})
