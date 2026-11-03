from unittest import TestCase, mock
from arena.calibration_diagnostics import defaults, diagnose, QUESTIONS
from arena.core import scratch_directory


class IndependentDiagnosticTests(TestCase):
    def test_missing_readable_reasoning_is_recorded_without_inference(self):
        with scratch_directory() as out, mock.patch('arena.calibration_diagnostics.agent') as agent:
            result=diagnose(out,'target',{'history':[{'role':'assistant','content':'Done'}]},defaults(),{})
            self.assertEqual(result['status'],'unavailable')
            self.assertEqual(result['audience'],'human_only')
            agent.assert_not_called()

    def test_probability_distributions_and_observations_are_persisted_once(self):
        class Judge:
            revision='fixture'
            def predict_long(self,state,questions,**kwargs):
                return {'answers':{key:{'probabilities':{label:1/len(q['criteria']) for label in q['criteria']}} for key,q in questions.items()},'usage':{'windows':1}}
        state={'history':[{'role':'assistant','native':{'reasoning_content':'Inspect the failure and correct the plan.'}}]}
        with scratch_directory() as out, mock.patch('arena.calibration_diagnostics.agent',return_value=Judge()) as agent, mock.patch('arena.calibration_diagnostics.importlib.metadata.version',return_value='fixture'):
            result=diagnose(out,'target',state,defaults(),{})
            self.assertEqual(result['status'],'completed')
            self.assertEqual(set(result['distributions']),set(QUESTIONS))
            for values in result['distributions'].values(): self.assertAlmostEqual(sum(values.values()),1)
            self.assertEqual(diagnose(out,'target',state,defaults(),{}),result)
            self.assertEqual(agent.call_count,1)

    def test_analyst_evidence_omits_saved_diagnostics_and_judge_scores(self):
        import json
        from arena.calibration import analyst_context,defaults as config_defaults
        from arena.experiment import Journal
        from arena.core import write_json
        with scratch_directory() as out:
            journal=Journal(out)
            try:
                journal.save('target',{'generation':0,'history':[{'role':'assistant','native':{'reasoning_content':'Investigate the syntax.'}}]},'session_created')
            finally: journal.db.close()
            write_json(out/'diagnostics/target.json',{'private_diagnosis':'HUMAN_ONLY_SENTINEL'})
            report={'replicates':[{'replicate':0,'rounds':[{'training':{'score':.5},'validation':{'secret':'HUMAN_ONLY_SENTINEL'},'judge_score':'HUMAN_ONLY_SENTINEL','diagnostics':'HUMAN_ONLY_SENTINEL'}]}]}
            with mock.patch('arena.calibration.original_documents',return_value={}):
                evidence=analyst_context(out,config_defaults(),report)
            self.assertNotIn('HUMAN_ONLY_SENTINEL',json.dumps(evidence))
            self.assertIn('Investigate the syntax',json.dumps(evidence))
