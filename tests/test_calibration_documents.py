"""Candidate document text is isolated and fingerprinted with the trial."""
import json
from unittest import TestCase, mock
from arena.calibration_documents import effective, validate
from arena.core import ArenaError, ROOT, scratch_directory
from arena.calibration import trial
from test_calibration import FixtureEngine, config


class CalibrationDocumentTests(TestCase):
    def test_edits_are_served_from_the_frozen_corpus_and_do_not_touch_repository(self):
        value=config()
        before=(ROOT/'docs/authoring.md').read_bytes()
        value['reference_documents']={'authoring.md':'# Candidate\nUse LeekScript 4.\n'}
        with scratch_directory() as root:
            trial(value,root/'candidate',engine=FixtureEngine())
            self.assertEqual((root/'candidate/corpus/authoring.md').read_text(),value['reference_documents']['authoring.md'])
            trial(value,root/'candidate',resume=True,engine=FixtureEngine())
            self.assertEqual((ROOT/'docs/authoring.md').read_bytes(),before)
            (root/'candidate/corpus/authoring.md').write_text('Changed')
            with self.assertRaisesRegex(ArenaError,'frozen documentation changed'):
                trial(value,root/'candidate',resume=True,engine=FixtureEngine())

    def test_only_registered_markdown_learning_material_can_change(self):
        for path in ('../secret.md','leekscript-v1/api.json','corpus/stat-rules.json','new-tool.py'):
            with self.assertRaises(ArenaError):
                validate({path:'replacement'})
        self.assertIn('corpus/components.md',effective({}))

    def test_analyst_can_replace_documents_and_receives_the_frozen_text(self):
        from arena.calibration import propose
        value=config()
        value['reference_documents']={'authoring.md':'# Existing candidate material\n'}
        with scratch_directory() as root:
            report=trial(value,root/'incumbent',engine=FixtureEngine())
            value['analyst']={'id':'editor','provider':'openai','model':'editor',
                'api_key_env':'ARENA_EDITOR_KEY','pricing':{'input_per_million':'0','output_per_million':'0'}}
            value['spending']={'allow_paid_calls':True,'max_total_usd':'1'}
            proposal={'prompt':value['prompt'],'tools':value['tools'],'rationale':'Clarify compilation guidance',
                      'reference_documents':{'authoring.md':'# Revised candidate material\nCompile before submitting.\n'}}
            def response(sid,state,*args):
                evidence=json.loads(state['history'][1]['content'])['evidence']
                self.assertEqual(evidence['reference_documents']['authoring.md'],'# Existing candidate material\n')
                return {'role':'assistant','content':json.dumps(proposal)}
            with mock.patch('arena.calibration.provider_response',side_effect=response):
                actual=propose(value,report,root/'incumbent',root/'proposal')
            self.assertEqual(actual['reference_documents'],proposal['reference_documents'])
            self.assertEqual((root/'incumbent/corpus/authoring.md').read_text(),'# Existing candidate material\n')
