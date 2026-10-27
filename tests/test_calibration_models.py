from unittest import TestCase,mock
from arena.core import ArenaError,read_json,scratch_directory,write_json
from arena.calibration import defaults,experiment_config
from arena.calibration_models import effective_analyst
from arena.experiment import Journal,initial_state
from arena_web.calibration import Workshop
from arena_web.data import Store
from test_model_probe import model


class CalibrationModelTests(TestCase):
    def test_analyst_replacement_preserves_original_inputs_and_records_history(self):
        with scratch_directory() as root:
            store=Store(root/'runs',root/'settings');workshop=Workshop(root/'studies',store)
            before={**model(),'id':'before'};after={**model(),'id':'after','model':'after'}
            store.save_participant(after)
            value=defaults();value.update(analyst=before,spending={'allow_paid_calls':True,'max_total_usd':'1'})
            directory=workshop.root/'study';write_json(directory/'input.json',value)
            write_json(directory/'study.json',{'config':value,'status':'blocked'})
            workshop.set_analyst_model('study','after')
            self.assertEqual(effective_analyst(value,directory),after)
            self.assertEqual(read_json(directory/'input.json'),value)
            self.assertEqual(workshop.model_roles('study')['history'][0]['previous'],before)
            folder=directory/'proposals/001';folder.mkdir(parents=True)
            journal=Journal(folder)
            try:
                state=initial_state('analyst-r0',before,experiment_config(value));state.update(status='needs_reconciliation',in_flight=True)
                journal.save('analyst-r0',state,'fixture')
            finally:journal.db.close()
            with self.assertRaisesRegex(ArenaError,'Resolve interrupted requests'):
                workshop.set_analyst_model('study','after')

    def test_linked_calibration_keeps_origin_and_separate_frozen_configuration(self):
        with scratch_directory() as root:
            store=Store(root/'runs',root/'settings');workshop=Workshop(root/'studies',store)
            value=defaults();source=workshop.root/'source'
            write_json(source/'trials/000/calibration.json',{'config':value})
            with mock.patch('arena_web.calibration.subprocess.Popen'):
                result=workshop.start(value,False,origin={'study':'source','candidate':1})
            directory=workshop.root/result['id']
            self.assertEqual(read_json(directory/'origin.json'),{'study':'source','candidate':1})
            self.assertEqual(read_json(source/'trials/000/calibration.json')['config'],value)

    def test_provider_switch_projects_visible_answers_without_foreign_native_state(self):
        import copy,json
        from arena.calibration_models import portable_analyst_history
        from arena.api_providers import APIProvider
        history=[{'role':'user','content':'Review the evidence.'},
                 {'role':'assistant','native':{'responses_output':[
                     {'type':'reasoning','encrypted_content':'opaque-private-marker'},
                     {'type':'message','role':'assistant','content':[{'type':'output_text','text':'Earlier proposal.'}]}]}},
                 {'role':'user','content':'Revise that proposal.'}]
        original=copy.deepcopy(history)
        for provider in ('anthropic','gemini','openai-compatible'):
            spec={**model(),'provider':provider,'max_output_tokens':1000}
            view=portable_analyst_history(history,spec)
            payload=APIProvider(spec).payload(view,[],16)
            self.assertIn('Earlier proposal.',json.dumps(payload))
            self.assertNotIn('opaque-private-marker',json.dumps(payload))
            self.assertNotIn('responses_output',json.dumps(payload))
        self.assertEqual(history,original)
