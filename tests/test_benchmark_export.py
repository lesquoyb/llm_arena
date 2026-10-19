"""Campaign exports preserve independent rows and missing provider usage."""
import csv
import unittest
from arena.benchmark_export import export
from arena.budget_context import progress
from arena.core import scratch_directory, write_json
from arena.experiment import Journal


class CampaignExportTests(unittest.TestCase):
    def test_two_same_named_runs_have_unique_fights_and_usage_is_not_zero(self):
        with scratch_directory() as out:
            roots=[out/'first'/'same-name',out/'second'/'same-name']
            for root in roots:
                root.mkdir(parents=True)
                write_json(root/'experiment.json',{'config':{'models':[{'id':'variant','provider':'openai','model':'example','parameters':{'temperature':0}}],'scenario':{}}})
                journal=Journal(root)
                try:
                    journal.save('variant-r0',{'model':'variant','replicate':0,'generation':0,'history':[],'status':'submitted','calls':1,'cost_spent':'0','token_usage_known':False},'session_created')
                finally: journal.db.close()
                write_json(root/'records/fight.json',{'match':{'sides':['variant-r0','fixed'],'seed':1,'mirror':False},
                    'directory':'matches/fight','result':{'status':'completed','winner_side':0,'turns':2,'team_metrics':{}}})
            result=export(roots,out/'csv')
            self.assertEqual(result['fight_appearances'],4)
            with (out/'csv/fights.csv').open(encoding='utf-8-sig',newline='') as stream: fights=list(csv.DictReader(stream))
            self.assertEqual(len({r['fight_id'] for r in fights}),2)
            self.assertEqual(len({r['run_id'] for r in fights}),2)
            with (out/'csv/sessions.csv').open(encoding='utf-8-sig',newline='') as stream: sessions=list(csv.DictReader(stream))
            self.assertTrue(all(r['input_tokens']=='' for r in sessions))
            self.assertTrue(all(r['usage_complete']=='False' for r in sessions))
            self.assertTrue(all(r['messages']=='0' for r in sessions))
            with (out/'csv/results.csv').open(encoding='utf-8-sig',newline='') as stream:
                results=list(csv.DictReader(stream))
            candidates=[row for row in results if row['participant']=='variant-r0']
            self.assertEqual(len(candidates),2)
            self.assertTrue(all(row['wins']=='1' and row['cost_usd']=='0' for row in candidates))
            self.assertTrue(all(row['input_tokens']=='' for row in candidates))

    def test_limit_receipts_distinguish_unknown_from_zero_and_unlimited(self):
        self.assertIsNone(progress({},{}))
        budget={'max_calls':3,'max_output_tokens':100,'max_cost_usd':'1'}
        value=progress({'calls':2,'output_tokens':30,'token_usage_known':True,'cost_spent':'0.2'},budget)['limits']
        self.assertEqual(value['calls']['remaining'],1)
        self.assertEqual(value['output_tokens']['remaining'],70)
        self.assertEqual(value['cost_usd']['remaining'],'0.8')
        self.assertIsNone(progress({'calls':1},budget)['limits']['output_tokens']['remaining'])
