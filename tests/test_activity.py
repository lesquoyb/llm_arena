"""Progress uses active membership and never treats stale engine markers as work."""
import time
import unittest
from contextlib import closing
from arena.core import ROOT,read_json,write_json,scratch_directory
from arena.experiment import Journal,initial_state
from arena.roster import update
from arena.activity import operation,session_root
from arena_web.data import Store
from arena_web.activity import status


class ActivityTests(unittest.TestCase):
    def test_withdrawn_unsubmitted_models_do_not_inflate_round_progress(self):
        with scratch_directory() as root:
            store=Store(root/'runs',root/'settings');out=store.runs/'run';out.mkdir()
            config=read_json(ROOT/'configs/offline-complete.json')
            config['models']=[{'id':'model-'+str(index),'provider':'mock','profile':'single-shot'} for index in range(12)]
            write_json(out/'experiment.json',{'config':config})
            journal=Journal(out)
            with closing(journal.db):
                for index,model in enumerate(config['models']):
                    sid=model['id']+'-r0';state=initial_state(sid,model,config)
                    if index<4:state.update(status='submitted',submission={'entrypoint':'main.leek'},validity='valid')
                    if index==4:state['in_flight']=True
                    journal.save(sid,state,'model_intent' if index==4 else 'session_created',{})
                update(out,journal,config,[],[model['id'] for model in config['models'][:10]])
            with operation(out,'tournament_fight',generation=0,participants=['model-0-r0','model-1-r0']):
                report=status(store,'run',{'status':'running','started_at':0})
                self.assertEqual((report['participants'],report['withdrawn'],report['ready_participants']),(10,2,4))
                self.assertEqual((report['strategies_ready'],report['strategies_validated'],report['strategies_expected']),(4,4,10))
                self.assertEqual(report['operation']['kind'],'tournament_fight')
                self.assertEqual(report['active'][0]['model'],'model-4')
                phases={item['session']:item['phase'] for item in report['preparations']}
                self.assertEqual(phases['model-4-r0'],'active')
                self.assertEqual(phases['model-5-r0'],'waiting')
                self.assertEqual(phases['model-0-r0'],'ready')
                restarted=status(store,'run',{'status':'running','started_at':time.time()+1})
                self.assertFalse(restarted['active'])
                self.assertFalse(restarted['operation'])
                stopped=status(store,'run',{'status':'stopped','started_at':0})
                self.assertFalse(stopped['operation'])
                self.assertFalse(stopped['active'])
            self.assertEqual(store.listing()[0]['models'],10)

    def test_submission_breakdown_separates_repetitions_and_fixed_references(self):
        with scratch_directory() as root:
            store=Store(root/'runs',root/'settings');out=store.runs/'run';out.mkdir()
            config=read_json(ROOT/'configs/offline-complete.json');config['replicates']=6
            config['models']=[{'id':'model-'+str(i),'provider':'openai-compatible'} for i in range(5)]+[
                {'id':'reference-'+str(i),'provider':'mock','profile':'saved-strategy'} for i in range(5)]
            write_json(out/'experiment.json',{'config':config,'fixed_reference_repetitions':1})
            journal=Journal(out)
            with closing(journal.db):
                for model in config['models']:
                    state=initial_state(model['id']+'-r0',model,config)
                    state.update(status='submitted',submission={'entrypoint':'main.leek'})
                    if model['id']=='model-0':state['validity']='invalid'
                    journal.save(model['id']+'-r0',state,'session_created')
            value=status(store,'run')
            self.assertEqual(value['strategies_expected'],35)
            self.assertEqual(value['strategies_checked'],1)
            self.assertEqual(value['strategies_valid'],0)
            self.assertEqual(value['strategies_invalid'],1)
            self.assertEqual(value['strategies_awaiting_check'],9)
            available=(10*9+(10 if config['include_mirrors'] else 0))*len(config['seeds'])
            expected=(35*34+(35 if config['include_mirrors'] else 0))*len(config['seeds'])
            self.assertEqual(value['tournament_pending_available'],available)
            self.assertEqual(value['tournament_waiting_submissions'],expected-available)
            self.assertEqual(sum(row['expected'] for row in value['submission_breakdown'] if row['fixed']),5)

    def test_transient_operation_closes_even_when_worker_raises(self):
        with scratch_directory() as root:
            with self.assertRaisesRegex(RuntimeError,'interrupted'):
                with operation(root,'checkpoint_verification'):
                    self.assertEqual(read_json(root/'activity.json')['kind'],'checkpoint_verification')
                    raise RuntimeError('interrupted')
            self.assertEqual(read_json(root/'activity.json')['kind'],'idle')
            self.assertEqual(session_root(root/'sessions'/'one'),root)
            self.assertEqual(session_root(root/'standalone'),root/'standalone')

    def test_billing_review_and_received_replies_are_not_active_network_requests(self):
        with scratch_directory() as root:
            store=Store(root/'runs',root/'settings');out=store.runs/'run';out.mkdir()
            config=read_json(ROOT/'configs/offline-complete.json')
            write_json(out/'experiment.json',{'config':config})
            journal=Journal(out)
            with closing(journal.db):
                for index,model in enumerate(config['models']):
                    sid=model['id']+'-r0';state=initial_state(sid,model,config)
                    state.update(in_flight=True,status='needs_reconciliation' if index==0 else 'running')
                    journal.save(sid,state,'model_intent',{})
                    if index==1:write_json(out/'sessions'/sid/'request-status.json',{'phase':'completed','updated_at':time.time()})
            report=status(store,'run',{'status':'running','started_at':0})
            self.assertEqual(report['failed_preparations'],1)
            self.assertEqual(len(report['active']),1)
            self.assertEqual(report['active'][0]['kind'],'provider_receipt_waiting')
            self.assertFalse(any(item['kind']=='model_request' for item in report['active']))
