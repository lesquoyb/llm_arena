import copy
import io
import json
import unittest
from unittest import mock
from urllib.error import HTTPError

from arena.api_providers import APIProvider, ProviderFailure, http_json
from arena.briefing import briefing, participant_scenario
from arena.core import ROOT, read_json, scratch_directory, submission, write_json
from arena.engine import Engine
from arena.experiment import Journal, initial_state
from arena.presets import simple_scenario, participant_scenario as team_scenario
from arena.public_teams import scenario_from_snapshot
from arena.tool_schemas import TOOLS
from arena_web.data import Store
from test_presets import public_snapshot
from test_web import fixture


class BriefingTests(unittest.TestCase):
    def test_english_prompt_explains_roster_ids_tools_and_omits_public_history(self):
        snapshot = public_snapshot()
        snapshot['leeks'][0]['fight_history'] = ['PRIVATE_ARCHIVE_MARKER'] * 10000
        scenario = scenario_from_snapshot(snapshot)
        frozen = copy.deepcopy(scenario)
        config = read_json(ROOT/'configs/offline-complete.json')
        config['scenario'] = scenario
        state = initial_state('fixture-r0', {'id':'fixture'}, config)
        message = state['history'][0]
        self.assertIn('You are preparing Round 1',message['content'])
        self.assertNotIn('source', message['scenario'])
        self.assertNotIn('PRIVATE_ARCHIVE_MARKER', json.dumps(message))
        self.assertEqual(scenario, frozen)
        self.assertEqual(len(message['briefing']['roster']), 4)
        self.assertEqual(message['briefing']['roster'][0]['weapons'][0], {'id':37,'name':'pistol'})
        self.assertIn('Runtime weapon IDs',message['briefing']['ids']['weapons'])
        self.assertIn('native engine',message['briefing']['tools'])
        self.assertIn('win=1',message['briefing']['objective'])
        self.assertIn('fixed',message['briefing']['team_mode'])
        self.assertIn('Choose 1',briefing(team_scenario())['team_mode'])
        descriptor={'provider':'gemini','model':'fixture'}
        payload = APIProvider(descriptor).payload(state['history'],TOOLS,None)
        self.assertNotIn('PRIVATE_ARCHIVE_MARKER',json.dumps(payload))

    def test_http_errors_include_public_reason_without_credential_or_raw_body(self):
        error = HTTPError('https://example.invalid',429,'error',{},io.BytesIO(json.dumps({
            'error':{'status':'RESOURCE_EXHAUSTED','message':'Quota exceeded; key=secret-fixture'},
            'echo':'must-not-be-recorded'}).encode()))
        with mock.patch('arena.api_providers.open_provider_response',side_effect=error):
            with self.assertRaises(ProviderFailure) as caught:
                http_json('https://example.invalid',{}, {'x-goog-api-key':'secret-fixture'},10)
        self.assertTrue(caught.exception.retryable)
        self.assertFalse(caught.exception.uncertain)
        self.assertIn('Quota exceeded',str(caught.exception))
        self.assertNotIn('secret-fixture',str(caught.exception))
        self.assertNotIn('must-not-be-recorded',str(caught.exception))

    def test_conversation_is_lightweight_with_exact_records_and_legacy_failure(self):
        with scratch_directory() as tmp:
            store=Store(tmp/'runs', tmp/'ui')
            root=fixture(store)
            journal=Journal(root)
            state=journal.state('mock-repair-r0')
            state['status']='provider_unavailable'
            state['history'][1]['sent_parameters']={'messages':['large-history']*1000}
            state['history'][1]['raw']={'large':'response'}
            # Emulate an archive made before failure and timestamp sidecars existed.
            state.pop('message_times', None)
            journal.save('mock-repair-r0',state,'provider_failure',{'error':'Provider HTTP 429: quota','retryable':True,'uncertain':False})
            journal.db.close()
            before=(root/'journal.sqlite').read_bytes()
            view=store.conversation('example','mock-repair-r0')
            self.assertEqual(view['failure']['message'],'Provider HTTP 429: quota')
            self.assertNotIn('sent_parameters',view['messages'][1])
            self.assertNotIn('raw',view['messages'][1])
            self.assertEqual(view['timeline'][2]['reply_to'],1)
            self.assertIn('large-history',json.dumps(store.message('example','mock-repair-r0',1)))
            self.assertEqual((root/'journal.sqlite').read_bytes(),before)

    @unittest.skipUnless((ROOT/'.arena/engine.json').exists(),'Build engine')
    def test_weapon_baselines_accept_dream_and_chosen_teams_including_unarmed(self):
        from arena.teams import validate_team
        dream=scenario_from_snapshot(public_snapshot())
        dream['member_stats'][0]['weapons']=[]
        dream['entity']['weapons']=[]
        chosen=team_scenario()
        for scenario in (dream,chosen):
            scenario['max_turns']=2
            for name in ('rush','single-shot'):
                source=ROOT/'examples/strategies'/name
                other=ROOT/'examples/strategies/passive'
                info=copy.deepcopy(submission(source))
                if scenario.get('team_selection'):
                    team={'members':[{'entrypoint':'main.leek','level':300,'capital':{},'weapons':[],'chips':[]},
                                     {'entrypoint':'main.leek','level':300,'capital':{'tp':65},'weapons':[37],'chips':[]}]}
                    validate_team(team,scenario,{'main.leek':''},ROOT/'docs/leekscript-v1')
                    # Supply a real team.json so the native path verifies its receipt.
                    with scratch_directory() as tmp:
                        work=tmp/'source';work.mkdir()
                        (work/'main.leek').write_bytes((source/'main.leek').read_bytes())
                        write_json(work/'team.json',team)
                        result=Engine().fight([work,other],[submission(work),submission(other)],scenario,101,tmp/'fight')
                        self.assertEqual(result['status'],'completed',result)
                        self.assertEqual(result['team_metrics']['0']['errors'],0)
                else:
                    with scratch_directory() as tmp:
                        result=Engine().fight([source,other],[info,submission(other)],scenario,101,tmp/'fight')
                        self.assertEqual(result['status'],'completed',result)
                        self.assertEqual(result['team_metrics']['0']['errors'],0)
