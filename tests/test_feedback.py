import json
import unittest
from arena.core import ArenaError, scratch_directory, write_json
from arena.feedback import FEEDBACK_NAMES, PastFights, access_for, available_tools
from arena.preparation import Preparation


class FeedbackAccessTests(unittest.TestCase):
    def records(self, out):
        for index in range(18):
            side = index % 2
            sides = ['parent-r0', 'peer-r0'] if side == 0 else ['peer-r0', 'parent-r0']
            base = out / 'tournament'
            directory = 'matches/fight-' + str(index)
            write_json(base / 'records' / f'{index:02}.json', {'match': {'sides': sides, 'mirror': False, 'seed': 999},
                'directory': directory, 'result': {'status': 'completed', 'winner_side': side, 'turns': 3,
                    'team_metrics': {str(side): {'operations': 123, 'errors': 0}}}})
            write_json(base / directory / 'outcome.json', {'fight': {'leeks': [{'id': 7, 'team': side+1, 'life': 100}],
                'actions': [[6, 2], [7, 7], [10, 7, 21, [20, 21]], [203, 'OPPONENT_SECRET']]},
                'turn_metrics': [{'turn': 2, 'entity': 7, 'side': side, 'operations': 123},
                                 {'turn': 2, 'entity': 8, 'side': 1-side, 'operations': 999}],
                'logs': {str(side+1): {'message': 'OWN_DEBUG'}, str(2-side): {'message': 'OPPONENT_SECRET'}}})
        write_json(out/'tournament/records/peer.json', {'match': {'sides': ['other-r0','peer-r0'], 'mirror':False}, 'result':{}})
        write_json(out/'tournament/records/mirror.json', {'match': {'sides': ['parent-r0','parent-r0'], 'mirror':True}, 'result':{}})
        write_json(out/'g1-tournament/records/future.json', {'match': {'sides': ['parent-r0','peer-r0'], 'mirror':False}, 'result':{}})

    def test_native_protocols_include_readable_summary_and_only_authorized_tools(self):
        from arena.api_providers import APIProvider
        for provider in ('openai', 'anthropic', 'gemini'):
            descriptor={'provider':provider,'model':'test'}
            history=[{'role':'user','content':'Your Round 1 tournament results: 1 win, 2 draws, 3 losses.',
                      'feedback':{'wins':1,'draws':2,'losses':3}}]
            for condition in ('control','feedback'):
                state={'generation':1,'condition':condition,'parent':'parent-r0'}
                payload=APIProvider(descriptor).payload(history,available_tools(state),100)
                text=json.dumps(payload)
                self.assertIn('Your Round 1 tournament results',text)
                self.assertEqual('list_past_fights' in text,condition=='feedback')

    def test_control_initial_and_forged_calls_are_denied_inside_service(self):
        with scratch_directory() as out:
            for state in ({'generation':0,'condition':'initial'}, {'generation':1,'condition':'control','parent':'parent-r0'},
                          {'generation':1,'condition':'feedback'}):
                self.assertIsNone(access_for(out,state))
                self.assertFalse(FEEDBACK_NAMES & {t['name'] for t in available_tools(state)})
                tools=Preparation(out/'session',out/'docs',None,{})
                for name in FEEDBACK_NAMES:
                    with self.assertRaisesRegex(ArenaError,'forbidden'):
                        tools.call(name, {'fight_id':'../tournament', 'condition':'feedback'}, 'call-1-tool-0')

    def test_session_runtime_enforces_permissions_and_records_tool_results(self):
        from unittest import mock
        from arena.core import ROOT, read_json
        from arena.experiment import Journal, initial_state, run_session
        from arena.providers import MockProvider
        original = MockProvider.respond
        def respond(provider, history, tools, limit):
            response=original(provider,history,tools,limit)
            response['tool_calls']=[{'name':'list_past_fights','arguments':{}}]
            return response
        def interrupt(kind, sid):
            if kind == 'tool':
                raise KeyboardInterrupt
        with scratch_directory() as out:
            self.records(out)
            config=read_json(ROOT/'configs/offline-demo.json')
            model=config['models'][0]
            journal=Journal(out)
            try:
                for condition in ('control','feedback'):
                    sid='parent-r0-g1-'+condition
                    state=initial_state(sid,model,config)
                    state.update(generation=1,condition=condition,parent='parent-r0')
                    journal.save(sid,state,'branch_created')
                    with mock.patch.object(MockProvider,'respond',respond), self.assertRaises(KeyboardInterrupt):
                        run_session(sid,model,config,out,journal,None,interrupt)
                    recorded=journal.state(sid)
                    result=recorded['history'][-1]['result']
                    if condition=='feedback':
                        self.assertEqual(result['total'],18)
                    else:
                        self.assertIn('forbidden',result['error'])
                    self.assertEqual(recorded['steps'],1)
            finally:
                journal.db.close()

    def test_failed_fight_without_replay_is_a_recoverable_tool_error(self):
        with scratch_directory() as out:
            write_json(out/'tournament/records/failed.json', {
                'match':{'sides':['parent-r0','peer-r0'],'mirror':False},
                'directory':'matches/failed', 'result':{'status':'timeout'}})
            access=PastFights(out,'parent-r0')
            fight=access.call('list_past_fights',{})['matches'][0]
            self.assertEqual(fight['result'],'unscored')
            for section in ('logs','actions','turns'):
                with self.assertRaisesRegex(ArenaError,'No replay'):
                    access.call('read_past_fight',{'fight_id':fight['fight_id'],'section':section})

    def test_feedback_only_reads_parent_round_and_own_logs_with_pagination(self):
        with scratch_directory() as out:
            self.records(out)
            state={'generation':1,'condition':'feedback','parent':'parent-r0'}
            access=access_for(out,state)
            self.assertTrue(FEEDBACK_NAMES <= {t['name'] for t in available_tools(state)})
            tools=Preparation(out/'session',out/'docs',None,{},feedback=access)
            listing=tools.call('list_past_fights',{'limit':1},'call-1-tool-0')
            self.assertEqual(listing['total'],18)
            self.assertEqual(listing['next_offset'],1)
            self.assertEqual(access.summary()['wins'],18)  # no old 16-fight truncation
            for row in access.call('list_past_fights',{'limit':100})['matches'][:2]:
                fight_id=row['fight_id']
                logs=access.call('read_past_fight',{'fight_id':fight_id,'section':'logs','limit':16000})
                self.assertIn('OWN_DEBUG',logs['content'])
                self.assertNotIn('OPPONENT_SECRET',logs['content'])
                turns=json.loads(access.call('read_past_fight',{'fight_id':fight_id,'section':'turns','limit':16000})['content'])
                self.assertEqual([v['operations'] for v in turns['metrics']],[123])
                actions=access.call('read_past_fight',{'fight_id':fight_id,'section':'actions','limit':16000})
                self.assertNotIn('OPPONENT_SECRET',actions['content'])
                self.assertIn('Movement: entity, destination cell, path',actions['content'])
                short=access.call('read_past_fight',{'fight_id':fight_id,'limit':10})
                self.assertEqual(short['next_offset'],10)
                self.assertTrue(short['truncated'])
            other_id=next(iter(PastFights(out,'other-r0').records()))
            for identifier in (other_id,'../tournament/records/00.json'):
                with self.assertRaisesRegex(ArenaError,'not available'):
                    access.call('read_past_fight',{'fight_id':identifier})
            with self.assertRaises(ArenaError):
                access.call('read_past_fight',{'fight_id':fight_id,'section':'source'})
