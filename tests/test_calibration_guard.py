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
                return {'answers':{key:{'noul':self.value} for key in questions},'usage':{'windows':1}}
        before=defaults();after={**before,'prompt':before['prompt']+'\nA candidate addition.'}
        for probability,status in [(.1,'approved'),(.5,'needs_review'),(.9,'rejected')]:
            with self.subTest(probability=probability),scratch_directory() as out,mock.patch('arena.calibration_guard.agent',return_value=Judge(probability)) as loader:
                settings={**guard_defaults(),'enabled':True}
                result=review(before,after,out,settings)
                self.assertEqual(result['status'],status)
                self.assertEqual(review(before,after,out,settings),result)
                self.assertEqual(loader.call_count,1)

    def test_unavailable_guard_never_reports_approval(self):
        before=defaults();after={**before,'prompt':before['prompt']+'\nAn addition.'}
        with scratch_directory() as out,mock.patch('arena.calibration_guard.agent',side_effect=RuntimeError('Unavailable')):
            self.assertEqual(review(before,after,out,guard_defaults())['status'],'unavailable')
