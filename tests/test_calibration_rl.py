from unittest import TestCase
from arena import calibration_rl as rl
from arena.calibration import defaults, validate, accept


class ReinforcementLearningTests(TestCase):
    def test_all_actions_are_explored_and_rewards_update_the_selected_context(self):
        policy={};settings=rl.defaults();report={'final_valid':True,'validation_score':.5}
        seen=set()
        for episode in range(1,len(rl.ACTIONS)+1):
            action=rl.select(policy,report,settings,episode)
            self.assertNotIn(action['action'],seen)
            seen.add(action['action'])
            change=rl.update(policy,action,.4,settings)
            self.assertAlmostEqual(change['q_after'],.1)
        self.assertEqual(seen,set(rl.ACTIONS))
        self.assertEqual(set(policy['values']),{'medium'})

    def test_plateau_requires_exploration_and_a_sufficient_reward_history(self):
        settings={**rl.defaults(),'minimum_episodes':5,'plateau_patience':5}
        rows=[{'rl':{'context':'high','action':action,'reward':0}} for action in rl.ACTIONS]
        self.assertTrue(rl.converged(rows,settings))
        self.assertFalse(rl.converged(rows[:-1],settings))
        rows[-1]['rl']['reward']=.2
        self.assertFalse(rl.converged(rows,settings))
        settings['stop_on_plateau']=False
        self.assertFalse(rl.converged(rows,settings))

    def test_unlimited_candidates_and_optional_legacy_settings(self):
        value=defaults()
        self.assertIsNone(value['optimizer']['max_trials'])
        validate(value)
        value.pop('rl');value.pop('evaluation')
        validate(value)

    def test_hybrid_judge_only_breaks_equivalent_combat_scores(self):
        config=defaults();config['evaluation']['mode']='hybrid'
        def report(score,judge):
            return {'final_valid':True,'tokens':100,'utility':score+.05*judge,
                    'validation_score':score,'judge_score':judge,
                    'replicates':[{'rounds':[{'validation':{'score':score}}]}]}
        baseline=report(.5,.3)
        self.assertTrue(accept(report(.5,.8),baseline,config))
        self.assertFalse(accept(report(.4,1),baseline,config))
        self.assertTrue(accept(report(.6,0),baseline,config))
        invalid=report(.5,1);invalid['final_valid']=False
        self.assertFalse(accept(invalid,baseline,config))
