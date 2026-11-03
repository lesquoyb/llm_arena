"""Compact summaries preserve scores and refresh after engine recovery."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from arena.core import write_json
from arena.greedy import evaluate
from arena_web.data import Store


class SummaryIndexTests(unittest.TestCase):
    def test_compact_index_preserves_cache_counts_and_invalidates_on_repair(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);store=Store(root/'runs',root/'settings');run=root/'runs/example'
            write_json(run/'experiment.json',{'manifest':{'strategies':[]}})
            record={'match':{'sides':['a','b'],'seed':1,'mirror':False},'directory':'matches/one',
                    'result':{'status':'completed','winner_side':0,'reference_cache':{'hit':True},
                              'team_metrics':{'0':{'errors':2,'operation_limit_hits':1,'turns':[1,2,3]}}}}
            path=run/'tournament/records/one.json';write_json(path,record)
            first=store.matches('example',compact=True)
            result=first['matches'][0]['result']
            self.assertTrue(result['reference_cache']['hit'])
            self.assertEqual(result['team_metrics']['0'],{'errors':2,'operation_limit_hits':1})
            result['status']='caller mutation'
            self.assertEqual(store.matches('example',compact=True)['matches'][0]['result']['status'],'completed')
            record['result']={'status':'engine_error','error':'Unavailable'};write_json(path,record)
            self.assertEqual(store.matches('example',compact=True)['matches'][0]['result']['status'],'engine_error')

    def test_end_of_preparation_does_not_reuse_failed_batch_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            states={sid:{'model':sid,'replicate':0,'submission':{}} for sid in ('a','b')}
            journal=SimpleNamespace(metadata=lambda:states)
            config={'name':'fixture','models':[],'scenario':{},'include_mirrors':False,'seeds':[1]}
            failed={'completed':1,'failed':1,'pending':0,'cancelled':0,'retry_pending':0}
            repaired={**failed,'completed':2,'failed':0}
            with patch('arena.greedy.run_tournament',side_effect=[failed,repaired]) as run:
                evaluate(None,config,Path(directory),journal)
                evaluate(None,config,Path(directory),journal)
                self.assertEqual(run.call_count,1)
                self.assertEqual(evaluate(None,config,Path(directory),journal,final=True)['failed'],0)
                self.assertEqual(run.call_count,2)
