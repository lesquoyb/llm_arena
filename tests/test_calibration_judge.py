from unittest import TestCase, mock
from arena.calibration import defaults
from arena.calibration_judge import evaluate
from arena.core import ArenaError, scratch_directory


class LocalJudgeTests(TestCase):
    def test_only_readable_reasoning_is_sent_and_cached_scores_are_not_recomputed(self):
        class Judge:
            revision='fixture-revision'
            def __init__(self): self.inputs=[]
            def predict_long(self,state,questions,**kwargs):
                self.inputs.append(state)
                return {'answers':{'quality':{'score':1.5}},'usage':{'windows':2}}
        engine=Judge();config=defaults();config['evaluation']['mode']='conversation'
        state={'history':[{'role':'assistant','native':{'reasoning_content':'Inspect diagnostics before correcting the syntax.',
                 'content':'CODE_MUST_NOT_REACH_LAYA','tool_calls':[{'function':{'name':'write_file','arguments':'PRIVATE_CODE'}}]}},
                 {'role':'tool','name':'read_file','result':{'content':'PRIVATE_FILE'}}]}
        with scratch_directory() as out, mock.patch('arena.calibration_judge.agent',return_value=engine), mock.patch('arena.calibration_judge.importlib.metadata.version',return_value='fixture'):
            receipt=evaluate(out,'target',state,config['evaluation'],config)
            self.assertEqual(receipt['score'],.75)
            self.assertEqual(receipt['revision'],'fixture-revision')
            self.assertNotIn('PRIVATE',str(engine.inputs))
            self.assertNotIn('CODE_MUST',str(engine.inputs))
            self.assertIn('Inspect diagnostics',str(engine.inputs))
            self.assertEqual(evaluate(out,'target',state,config['evaluation'],config),receipt)
            self.assertEqual(len(engine.inputs),1)

    def test_encrypted_openai_reasoning_is_not_scored(self):
        state={'history':[{'role':'assistant','native':{'responses_output':[{'type':'reasoning','encrypted_content':'opaque','summary':[]}]}}]}
        config=defaults()
        with scratch_directory() as out, self.assertRaisesRegex(ArenaError,'No readable reasoning'):
            evaluate(out,'target',state,config['evaluation'],config)
