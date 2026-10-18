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
