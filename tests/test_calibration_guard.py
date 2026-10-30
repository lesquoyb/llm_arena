from unittest import TestCase,mock
from arena.calibration import defaults
from arena.calibration_guard import defaults as guard_defaults,review
from arena.core import scratch_directory


class ProposalGuardTests(TestCase):
    def test_ambiguous_and_rejected_proposals_are_not_approved_and_receipts_are_cached(self):
        class Judge:
            revision='fixture'
            def __init__(self,value): self.value=value
            def predict_long(self,state,questions,**kwargs):
                return {'answers':{key:({'probabilities':{'coding_workflow':1-self.value,'battle_tactics':self.value},'choice':'battle_tactics' if self.value>.5 else 'coding_workflow'} if question['type']=='choice' else {'noul':self.value}) for key,question in questions.items()},'usage':{'windows':1},'extra_metadata':{'preserved':True}}
        before=defaults();after={**before,'prompt':before['prompt']+'\nA candidate addition.'}
        for probability,status in [(.1,'approved'),(.5,'needs_review'),(.9,'rejected')]:
            with self.subTest(probability=probability),scratch_directory() as out,mock.patch('arena.calibration_guard.agent',return_value=Judge(probability)) as loader:
                settings={**guard_defaults(),'enabled':True}
                result=review(before,after,out,settings)
                self.assertEqual(result['status'],status)
                self.assertEqual(result['observations'][0]['response']['extra_metadata'],{'preserved':True})
                self.assertEqual(review(before,after,out,settings),result)
                self.assertEqual(loader.call_count,1)

    def test_workflow_probability_is_not_interpreted_as_battle_risk(self):
        before=defaults();after={**before,'prompt':before['prompt']+'\nRead docs, save, compile and submit before the budget expires.'}
        response={'answers':{'provided_solution':{'noul':.6614},
                  'prescribed_strategy':{'type':'choice','choice':'coding_workflow',
                    'probabilities':{'coding_workflow':.9346,'battle_tactics':.0654}}}}
        with scratch_directory() as out,mock.patch('arena.calibration_guard.agent') as loader:
            loader.return_value.predict_long.return_value=response
            result=review(before,after,out,guard_defaults())
            self.assertEqual(result['status'],'needs_review')
            self.assertAlmostEqual(result['observations'][0]['risks']['prescribed_strategy'],.0654)
            self.assertEqual(result['observations'][0]['response'],response)
            self.assertEqual(result['questions']['prescribed_strategy']['type'],'choice')

    def test_unavailable_guard_never_reports_approval(self):
        before=defaults();after={**before,'prompt':before['prompt']+'\nAn addition.'}
        with scratch_directory() as out,mock.patch('arena.calibration_guard.agent',side_effect=RuntimeError('Unavailable')):
            self.assertEqual(review(before,after,out,guard_defaults())['status'],'unavailable')
