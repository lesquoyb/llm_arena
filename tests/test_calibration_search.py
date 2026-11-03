from unittest import TestCase
from arena.calibration_search import defaults, select, converged


class AnalystLedSearchTests(TestCase):
    def test_exploitation_uses_best_and_exploration_can_revisit_rejected_valid_candidates(self):
        trials=[{'report':{'final_valid':True}},{'report':{'final_valid':True}},{'report':{'final_valid':False}}]
        settings=defaults()
        self.assertEqual(select(trials,0,{**settings,'exploration':0},1)['parent'],0)
        choice=select(trials,0,{**settings,'exploration':1},1)
        self.assertEqual(choice['mode'],'exploration')
        self.assertEqual(choice['parent'],1)
        self.assertNotIn('language',choice['instruction'])

    def test_plateau_uses_objective_history_not_laya_diagnostics(self):
        settings={**defaults(),'minimum_episodes':2,'plateau_patience':2}
        rows=[{'search':{'improvement':0},'diagnostic':{'label':'bad'}},
              {'search':{'improvement':0},'diagnostic':{'label':'excellent'}}]
        self.assertTrue(converged(rows,settings))
        rows[-1]['search']['improvement']=.1
        self.assertFalse(converged(rows,settings))
