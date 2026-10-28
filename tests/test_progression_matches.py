"""Previous-version diagnostics are distinct from scored tournament fixtures."""
import unittest
from contextlib import closing

from arena.core import ROOT, read_json, scratch_directory, write_json
from arena.experiment import Journal, initial_state, plan
from arena_web.data import Store


class ProgressionMatchTests(unittest.TestCase):
    def test_classification_reuses_round_two_and_never_scores_extra_fights(self):
        with scratch_directory() as root:
            out=root/'run';out.mkdir()
            config=read_json(ROOT/'configs/offline-complete.json')
            config['models']=[{'id':name,'provider':'openai-compatible'} for name in ('a','b')]
            write_json(out/'experiment.json',{'config':config})
            journal=Journal(out)
            with closing(journal.db):
                for sid,model,generation in [('a-r0',config['models'][0],0),('b-r0',config['models'][1],0),('a-r0-g1-feedback',config['models'][0],1),('a-r0-g2-feedback',config['models'][0],2)]:
                    state=initial_state(sid,model,config);state['generation']=generation
                    journal.save(sid,state,'fixture',{})
            for stage,candidate,opponent in [('g1-panel','a-r0-g1-feedback','b-r0'),('g2-previous','a-r0-g2-feedback','a-r0-g1-feedback')]:
                work=out/'evaluations'/stage
                write_json(work/'records'/'fixture.json',{'session':candidate,'opponent':opponent,'side':0,'seed':101,'result':{'status':'completed','winner_side':0},'directory':'fixtures/attempt-1'})
            rows=Store(root,root/'settings').matches('run')['matches']
            self.assertEqual(len(rows),2)
            self.assertEqual({row['kind'] for row in rows},{'evaluation','progression'})
            self.assertTrue(all(row['previous_round_comparison'] for row in rows))
            self.assertTrue(all(not row['counts_toward_standings'] for row in rows))

    def test_plan_counts_only_additional_round_three_onward_fights(self):
        config=read_json(ROOT/'configs/offline-complete.json')
        config['models']=[{'id':'a','provider':'openai-compatible','api_key_env':'FIXTURE_KEY'},{'id':'reference','provider':'mock'}]
        config.update(generations=3,replicates=1,compare_previous_round=True,final_seeds=[101])
        self.assertEqual(plan(config)['previous_comparison_matches'],8)
        config['generations']=2
        self.assertEqual(plan(config)['previous_comparison_matches'],0)
