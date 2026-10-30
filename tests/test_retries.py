import copy
import unittest
from unittest import mock

from arena.core import ArenaError, ROOT, file_hash, read_json, scratch_directory
from arena.experiment import Journal, run
from arena.presets import simple_scenario
from arena.providers import MockProvider
from arena.retries import prepare_retry, retry_reason


class RetryTests(unittest.TestCase):
    def test_only_safe_unsubmitted_failures_are_retryable(self):
        base={'status':'provider_unavailable','calls':2,'steps':1,'wall_seconds':3,
              'money_reserved':'0','in_flight':False,'history':[{'role':'user','content':'original'}]}
        self.assertIsNone(retry_reason(base,{'max_calls':3}))
        for extra in ({'status':'running'}, {'status':'needs_reconciliation'}, {'in_flight':True},
                      {'money_reserved':'0.1'}, {'submission':{'sha256':'frozen'}}):
            self.assertIsNotNone(retry_reason({**base,**extra}))
        self.assertIn('max_calls',retry_reason(base,{'max_calls':2}))
        self.assertIn('initial strategy',retry_reason({**base,'parent':'a-r0'}))
        self.assertIsNone(retry_reason({**base,'parent':'a-r0'},parent={'submission':{'sha256':'valid'}}))
        with scratch_directory() as tmp:
            journal=Journal(tmp)
            try:
                journal.save('a-r0',base,'provider_failure',{'error':'429'})
                old=journal.state('a-r0')
                state=prepare_retry(journal,'a-r0',{'budget_per_session':{}})
                self.assertEqual(state['history'],old['history'])
                self.assertEqual(state['calls'],2)
                self.assertEqual(state['wall_seconds'],3)
                self.assertEqual(state['retry_count'],1)
                self.assertEqual(state['status'],'running')
                self.assertTrue(any(row[0]=='retry_requested' for row in journal.db.execute('SELECT kind FROM events')))
            finally: journal.db.close()

    def test_failed_requests_do_not_exhaust_completed_response_budget(self):
        state = {'status':'provider_unavailable', 'calls':8, 'completed_calls':2,
                 'steps':1, 'wall_seconds':3, 'money_reserved':'0', 'in_flight':False}
        self.assertIsNone(retry_reason(state, {'max_calls':3}))
        self.assertIn('max_calls', retry_reason({**state, 'completed_calls':3}, {'max_calls':3}))
        with scratch_directory() as tmp:
            journal = Journal(tmp)
            try:
                legacy = {key:value for key,value in state.items() if key != 'completed_calls'}
                journal.save('legacy-r0', legacy, 'provider_failure', {'error':'429'})
                recovered = prepare_retry(journal, 'legacy-r0', {'budget_per_session':{'max_calls':3}})
                self.assertEqual(recovered['calls'], 8)
                self.assertEqual(recovered['completed_calls'], 0)
                self.assertEqual(recovered['status'], 'running')
            finally:
                journal.db.close()

    def test_context_overflow_rebases_request_but_preserves_history_and_files(self):
        from arena.context_recovery import context_overflow
        with scratch_directory() as tmp:
            journal = Journal(tmp)
            try:
                history = [{'role':'user', 'content':'Original scenario and round instructions'},
                           {'role':'assistant', 'native':{'role':'assistant', 'content':'Prior work'}},
                           {'role':'tool', 'name':'read_docs', 'result':{'content':'long document'}}]
                state = {'status':'provider_unavailable', 'calls':8, 'completed_calls':2,
                         'steps':4, 'wall_seconds':10, 'money_reserved':'0', 'in_flight':False,
                         'history':history, 'workspace_files':{'main.leek':'saved-hash'},
                         'failure':{'message':'Provider HTTP 400: invalid_request_prompt_too_long: Prompt 261507 > 256000 maximum context length'}}
                journal.save('target-r0', state, 'provider_failure', state['failure'])
                before = journal.state('target-r0')
                recovered = prepare_retry(journal, 'target-r0', {'budget_per_session':{'max_calls':3}})
                self.assertTrue(context_overflow(before))
                self.assertEqual(recovered['history'][:len(history)], before['history'])
                self.assertEqual(recovered['workspace_files'], before['workspace_files'])
                self.assertEqual(recovered['steps'], 4)
                self.assertEqual(recovered['completed_calls'], 2)
                active = recovered['history'][recovered['request_history_start']:]
                self.assertEqual(active[0], history[0])
                self.assertEqual([message['role'] for message in active], ['user', 'user'])
                self.assertIn('main.leek', active[-1]['content'])
                self.assertIn('SAME preparation session', active[-1]['content'])
                journal.verify()
            finally:
                journal.db.close()

    @unittest.skipUnless((ROOT/'.arena/engine.json').exists(),'Build engine')
    def test_retry_recovers_one_model_and_dependent_branches_without_repeating_peers_or_matches(self):
        config=read_json(ROOT/'configs/offline-complete.json')
        config.update(name='Selective retry fixture',replicates=1,seeds=[101],final_seeds=[301],include_mirrors=False)
        config['scenario']=simple_scenario();config['scenario']['max_turns']=1
        config['models']=[{'id':'alpha','provider':'mock','profile':'single-shot'},
                          {'id':'beta','provider':'mock','profile':'repair-and-submit'},
                          {'id':'flaky','provider':'mock','profile':'rate-limit'}]
        config['budget_per_session']={'max_calls':12,'max_agent_steps':30,'max_test_matches':0,'max_wall_seconds':90}
        with scratch_directory() as tmp:
            out=tmp/'experiment'
            first=run(copy.deepcopy(config),out)
            self.assertTrue(first['incomplete'])
            journal=Journal(out)
            before=journal.states();journal.db.close()
            self.assertEqual(before['flaky-r0']['status'],'provider_unavailable')
            self.assertTrue(first['waiting_for_recovery'])
            self.assertNotIn('flaky-r0-g1-control',before)
            self.assertTrue(all(state.get('generation',0)==0 for state in before.values()))
            peers={sid:state for sid,state in before.items() if state['model']!='flaky'}
            artifacts={p:(file_hash(p),p.stat().st_mtime_ns) for p in out.rglob('*')
                       if p.is_file() and ('matches' in p.parts or 'submission' in p.parts)}
            original=MockProvider.respond
            retried=[]
            def recovered(provider,history,tools,limit):
                retried.append(provider.profile)
                if provider.profile=='rate-limit':
                    return original(MockProvider('single-shot'),history,tools,limit)
                # Healthy initial conversations stay frozen; their improvement
                # conversations are now created only after the failed peer recovers.
                self.assertTrue(any(m.get('generation',0)>0 for m in history if m.get('role')=='user'))
                return original(provider,history,tools,limit)
            with mock.patch.object(MockProvider,'respond',recovered):
                result=run(copy.deepcopy(config),out,resume=True,retry_session='flaky-r0')
            self.assertFalse(result['incomplete'],result)
            self.assertTrue(retried)
            after=Journal(out)
            try:
                after.verify()
                states=after.states()
                self.assertEqual({sid:states[sid] for sid in peers},peers)
                self.assertTrue(states['flaky-r0-g1-control'].get('submission'))
                self.assertTrue(states['flaky-r0-g1-feedback'].get('submission'))
                self.assertEqual(states['flaky-r0']['retry_count'],1)
            finally: after.db.close()
            for path, snapshot in artifacts.items():
                self.assertEqual((file_hash(path),path.stat().st_mtime_ns),snapshot,str(path))
            self.assertTrue(list((out/'tournament/history').glob('*.json')))
            self.assertTrue(list((out/'g1-tournament/history').glob('*.json')))
            with mock.patch.object(MockProvider,'respond',side_effect=AssertionError('Already completed')):
                resumed=run(copy.deepcopy(config),out,resume=True)
            self.assertFalse(resumed['incomplete'])
