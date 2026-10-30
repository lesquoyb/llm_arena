"""The participant sees a task briefing; budget closure preserves saved sources."""
import unittest

from arena.api_providers import APIProvider
from arena.calibration import defaults, experiment_config, validate
from arena.core import ROOT, AUTOMATIC_ERROR_FILE, copy_submission, read_json, scratch_directory
from arena.experiment import Journal, initial_state, _finish
from arena.model_content import message_text
from arena.preparation import Preparation
from arena.presets import participant_scenario, simple_scenario
from arena.teams import build_preview, validate_team


class UserBriefingTests(unittest.TestCase):
    def test_open_team_context_is_readable_in_all_provider_protocols(self):
        value=defaults();value['scenario']=participant_scenario()
        message=initial_state('target-r0',value['target'],experiment_config(value))['history'][0]
        message['content']='You are preparing Round 1 of 3.'
        text=message_text(message)
        self.assertIn('Choose 1 to 4 members',text)
        self.assertIn('1 to 300',text)
        self.assertIn('Sources alone do not configure a team',text)
        self.assertIn('Members 1, 2, 3, 4:',text)
        self.assertEqual(text.count('life=2957'),1)
        self.assertIn('Preparation limits',text)
        self.assertNotIn('team_instructions',text)
        self.assertNotIn('"scenario":',text)
        self.assertIn('scenario',message)  # Original structured configuration remains archived.
        for protocol,model in [('openai-compatible','fixture'),('openai','gpt-6.1-sol'),('anthropic','fixture'),('gemini','fixture')]:
            with self.subTest(protocol=protocol):
                payload=APIProvider({'provider':protocol,'model':model}).payload([message],[],128)
                import json
                encoded=json.dumps(payload)
                self.assertIn('Your team: you must build it',encoded)
                self.assertNotIn('team_instructions',encoded)

    def test_fixed_roster_omits_unavailable_equipment_instructions(self):
        value=defaults();message=initial_state('target-r0',value['target'],experiment_config(value))['history'][0]
        message['content']='Prepare your strategy.'
        text=message_text(message)
        self.assertIn('Your fixed roster',text)
        self.assertIn('do not call configure_team',text)
        self.assertNotIn('Runtime chip IDs',text)
        self.assertNotIn('Use component template IDs',text)

    def test_budget_freezes_non_main_sources_and_incomplete_team_can_be_repaired(self):
        value=defaults();value['scenario']=participant_scenario();sid='target-r0'
        with scratch_directory() as tmp:
            tools=Preparation(tmp/'sessions'/sid,ROOT/'docs',None,value['scenario'])
            tools.call('write_file',{'path':'agent.leek','content':'var self = getEntity()\n'},'1')
            state=initial_state(sid,value['target'],experiment_config(value));journal=Journal(tmp)
            try:
                _finish(sid,state,tools,journal,'budget_exhausted')
                self.assertEqual(state['status'],'budget_exhausted')
                self.assertEqual(state['submission']['entrypoint'],'agent.leek')
                self.assertTrue(state['automatic_submission'])
                self.assertEqual(state['validity'],'invalid')
                self.assertIn('no team was configured',state['submission_configuration_error'])
                self.assertIn(AUTOMATIC_ERROR_FILE,state['submission']['files'])
                self.assertEqual(read_json(tools.directory/'assessment.json')['phase'],'team_configuration')
                next_tools=Preparation(tmp/'sessions/next',ROOT/'docs',None,value['scenario'])
                copy_submission(tools.directory/'submission',next_tools.workspace,state['submission'])
                next_tools.call('configure_team',{'members':[{'entrypoint':'agent.leek','level':300,
                    'capital':value['scenario']['member_stats'][0]['capital'],'weapons':[],'chips':[]}]},'2')
                repaired=next_tools.freeze_latest()['submission']
                self.assertIn('team',repaired)
                self.assertNotIn('configuration_error',repaired)
                self.assertNotIn(AUTOMATIC_ERROR_FILE,repaired['files'])
            finally:journal.db.close()

    def test_budget_closure_preserves_single_source_in_fixed_scenario(self):
        with scratch_directory() as tmp:
            tools=Preparation(tmp/'fixed',ROOT/'docs',None,simple_scenario())
            tools.call('write_file',{'path':'agent.leek','content':'var = invalid syntax\n'},'1')
            result=tools.freeze_latest()
            self.assertEqual(result['submission']['entrypoint'],'agent.leek')
            self.assertEqual((tools.directory/'submission/agent.leek').read_text(),'var = invalid syntax\n')
            self.assertNotIn('configuration_error',result)

    def test_open_team_tools_cannot_disable_team_configuration(self):
        from arena.core import ArenaError
        value=defaults();value['scenario']=participant_scenario();value['tools'].remove('configure_team')
        with self.assertRaisesRegex(ArenaError,'require configure_team'):validate(value)

    def test_open_preset_level_limit_is_consistent_with_preview_and_team_validation(self):
        scenario=participant_scenario();capital=scenario['member_stats'][0]['capital']
        self.assertEqual(build_preview(scenario,0,capital)['level'],300)
        from arena.core import ArenaError
        with self.assertRaises(ArenaError):build_preview(scenario,0,capital,level=301)
        with self.assertRaises(ArenaError):validate_team({'members':[{'entrypoint':'main.leek','level':301,'capital':capital,'weapons':[],'chips':[]}]},scenario,{'main.leek'},ROOT/'docs/leekscript-v1')
