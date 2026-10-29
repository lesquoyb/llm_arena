"""Concurrency applies only to model transports; all checkpoints stay on the caller."""
import copy
import threading
import time
from unittest import TestCase,mock
from arena.core import ROOT,ArenaError,read_json,scratch_directory,submission,write_json
from arena.experiment import Journal,validate_config
from arena.parallel import prepare


class CoordinatorEngine:
    identity={'fixture':'coordinator'}
    def __init__(self):self.owner=threading.get_ident()
    def analyze(self,source,entrypoint,out):
        assert threading.get_ident()==self.owner
        info=submission(source,entrypoint)
        result={'status':'valid','success':True,'diagnostics':[],'diagnostic_messages':[],'source_sha256':info['sha256']}
        write_json(out/'result.json',result);write_json(out/'provenance.json',{'submission':info})
        return result


def config(local=False,budget=False):
    value=read_json(ROOT/'configs/offline-complete.json')
    value.update(generations=1,parallel_requests=2,budget_per_session={'max_calls':3},spending={'allow_paid_calls':True})
    if budget:value['spending']['max_total_usd']='.8'
    value['models']=[{'id':name,'provider':'openai-compatible','model':name,
        'endpoint':('http://localhost:11434/v1/chat/completions' if local else 'https://'+name+'.example/v1/chat/completions'),
        'api_key_env':'ARENA_PARALLEL_TEST','max_output_tokens':512,
        'pricing':{'currency':'USD','date':'2026-10-28','input_per_million':'0','output_per_million':'1000' if budget else '0'}} for name in ('one','two')]
    return value


class ParallelRequestsTests(TestCase):
    def exercise(self,value,root,stop=False):
        counts={};active=peak=0;guard=threading.Lock()
        barrier=threading.Barrier(2,timeout=10) if not value['spending'].get('max_total_usd') and not value['models'][0]['endpoint'].startswith('http://localhost') else None
        def respond(provider,history,tools,limit):
            nonlocal active,peak
            name=provider.model['id']
            with guard:active+=1;peak=max(active,peak);counts[name]=counts.get(name,0)+1
            try:
                if barrier:barrier.wait()
                else:time.sleep(.01)
                seen={message.get('name') for message in history if message['role']=='tool'}
                tool='write_file' if 'write_file' not in seen else 'analyze' if 'analyze' not in seen else 'submit'
                args={'path':'main.leek','content':'var owner = "'+name+'";'} if tool=='write_file' else {}
                return {'role':'assistant','content':'','native':{'role':'assistant','content':''},
                    'tool_calls':[{'id':'next-'+tool,'name':tool,'arguments':args}],
                    'usage':{'input_tokens':10,'output_tokens':1},'cost_usd':'.001' if value['spending'].get('max_total_usd') else '0'}
            finally:
                with guard:active-=1
        tasks=[(m['id']+'-r0',m) for m in value['models']]
        journal=Journal(root)
        try:
            def interrupt(kind,sid):
                if kind=='response':raise KeyboardInterrupt
            with mock.patch('arena.api_providers.APIProvider.respond',new=respond):
                if stop:
                    with self.assertRaises(KeyboardInterrupt):prepare(tasks,value,root,journal,CoordinatorEngine(),interrupt)
                    self.assertTrue(all(s['pending'] and not s['in_flight'] and s['completed_calls']==1 for s in journal.states().values()))
                prepare(tasks,value,root,journal,CoordinatorEngine())
            journal.verify()
            for sid,state in journal.states().items():
                self.assertEqual(state['status'],'submitted')
                self.assertEqual(state['completed_calls'],3)
                self.assertIn(state['model'],(root/'sessions'/sid/'submission/main.leek').read_text())
            self.assertEqual(counts,{'one':3,'two':3})
        finally:journal.db.close()
        return peak

    def test_serial_progress_yields_to_remaining_resumable_conversations(self):
        from arena.activity import provider_work_ready, _provider_yielder
        value=config();value['parallel_requests']=1
        states={};observations=[]
        journal=mock.Mock()
        journal.metadata.side_effect=lambda sid=None:dict(states) if sid is None else ({sid:states[sid]} if sid in states else {})
        def run_session(sid,*args):
            states[sid]={'status':'submitted'}
        with scratch_directory() as root, mock.patch('arena.experiment.run_session',side_effect=run_session):
            prepare([(m['id']+'-r0',m) for m in value['models']],value,root,journal,None,
                    on_progress=lambda:observations.append(provider_work_ready()))
        self.assertEqual(observations,[True,False])
        self.assertIsNone(_provider_yielder.get())

    def test_concurrent_remote_requests_keep_sources_and_journal_isolated(self):
        with scratch_directory() as root:self.assertEqual(self.exercise(config(),root),2)

    def test_local_models_and_shared_reservations_are_serialized_without_false_budget_exhaustion(self):
        for value in (config(local=True),config(budget=True)):
            with self.subTest(local=value['models'][0]['endpoint']),scratch_directory() as root:
                self.assertEqual(self.exercise(value,root),1)

    def test_stop_preserves_paid_responses_and_resume_does_not_repeat_them(self):
        with scratch_directory() as root:self.assertEqual(self.exercise(config(),root,stop=True),2)

    def test_optional_concurrency_is_bounded_and_defaults_to_serial(self):
        value=config();value.pop('parallel_requests');validate_config(value)
        for bad in (0,21,True,1.5,'2'):
            trial=copy.deepcopy(value);trial['parallel_requests']=bad
            with self.assertRaises(ArenaError):validate_config(trial)
        for order in ('models','repetitions'):
            validate_config({**value,'request_order':order})
        with self.assertRaises(ArenaError):validate_config({**value,'request_order':'random'})

    def test_same_remote_model_parameter_variants_can_fill_free_slots(self):
        from arena.parallel import Requests
        dispatcher=Requests(3)
        model=config()['models'][0]
        variant={**model,'id':'other-profile','parameters':{'temperature':.7}}
        try:
            dispatcher.pending['one-r0']={'model':model}
            self.assertTrue(dispatcher.can_start('one-r1',model))
            self.assertTrue(dispatcher.can_start('variant-r0',variant))
            self.assertTrue(dispatcher.can_start('two-r0',config()['models'][1]))
            dispatcher.pending.clear()
            self.assertTrue(dispatcher.can_start('variant-r0',variant))
        finally:dispatcher.pool.shutdown()

    def test_default_and_explicit_openai_routes_share_a_lane(self):
        from arena.parallel import Requests
        model={'id':'first','provider':'openai','model':'example'}
        explicit={**model,'id':'second','endpoint':'https://api.openai.com/v1/responses'}
        self.assertEqual(Requests.model_key(model),Requests.model_key(explicit))

    def test_order_is_a_preference_and_local_weights_stay_until_all_samples_finish(self):
        from arena.parallel import Requests,ordered_tasks
        one,two=config()['models']
        tasks=[('a0',one),('a1',one),('b0',two),('b1',two)]
        self.assertEqual([sid for sid,_ in ordered_tasks(tasks,'models')],['a0','b0','a1','b1'])
        self.assertEqual([sid for sid,_ in ordered_tasks(tasks,'repetitions')],['a0','a1','b0','b1'])
        one,two=config(local=True)['models']
        tasks=[('a0',one),('a1',one),('b0',two)]
        self.assertEqual([sid for sid,_ in ordered_tasks(tasks,'models',serial=True)],['a0','a1','b0'])
        dispatcher=Requests(3,tasks)
        try:
            key=dispatcher.local_key(one)
            dispatcher.local_owners[key]=dispatcher.model_key(one)
            self.assertTrue(dispatcher.can_start('a1',one))
            self.assertFalse(dispatcher.can_start('b0',two))
            dispatcher.release('a0')
            self.assertFalse(dispatcher.can_start('b0',two))
            dispatcher.release('a1')
            self.assertTrue(dispatcher.can_start('b0',two))
        finally:dispatcher.pool.shutdown()

    def test_failed_provider_releases_capacity_without_eliminating_healthy_peers(self):
        from arena.api_providers import ProviderFailure
        value=config()
        value['models'].append({**value['models'][1],'id':'three','model':'three'})
        def respond(provider,history,tools,limit):
            if provider.model['id']=='one':raise ProviderFailure('HTTP 429 fixture',retryable=True)
            seen={message.get('name') for message in history if message['role']=='tool'}
            tool='write_file' if 'write_file' not in seen else 'analyze' if 'analyze' not in seen else 'submit'
            args={'path':'main.leek','content':'var v = 1;'} if tool=='write_file' else {}
            return {'role':'assistant','native':{'role':'assistant','content':''},'tool_calls':[
                {'id':tool,'name':tool,'arguments':args}],'usage':{'input_tokens':10,'output_tokens':1},'cost_usd':'0'}
        with scratch_directory() as root:
            journal=Journal(root)
            try:
                with mock.patch('arena.api_providers.APIProvider.respond',new=respond):
                    prepare([(m['id']+'-r0',m) for m in value['models']],value,root,journal,CoordinatorEngine())
                states=journal.states()
                self.assertEqual(states['one-r0']['status'],'provider_unavailable')
                self.assertEqual(states['one-r0']['calls'],1)
                self.assertTrue(all(states[sid]['status']=='submitted' for sid in ('two-r0','three-r0')))
                journal.verify()
            finally:journal.db.close()

    def test_engine_batches_yield_to_a_ready_model_response(self):
        from arena.fight_pool import run as run_fights
        started=threading.Event();resumed=threading.Event();saved=[];observed=[]
        value=config()
        with scratch_directory() as root:
            journal=Journal(root)
            def respond(provider,history,tools,limit):
                seen={message.get('name') for message in history if message['role']=='tool'}
                if provider.model['id']=='two':
                    if not seen:
                        if not started.wait(10):raise RuntimeError('No engine fight started')
                    else:
                        if not resumed.is_set():observed.append(len(saved))
                        resumed.set()
                tool='write_file' if 'write_file' not in seen else 'analyze' if 'analyze' not in seen else 'submit'
                args={'path':'main.leek','content':'var v = 1;'} if tool=='write_file' else {}
                return {'role':'assistant','native':{'role':'assistant','content':''},'tool_calls':[
                    {'id':tool,'name':tool,'arguments':args}],'usage':{'input_tokens':10,'output_tokens':1},'cost_usd':'0'}
            def execute(job):
                if not resumed.is_set():
                    started.set();journal.requests.pending['two-r0']['future'].result(timeout=10)
                return job['seed']
            def progress():
                missing=[{'participants':['one-r0','one-r0'],'seed':i} for i in range(100) if i not in saved]
                run_fights(missing,execute,lambda job,result:saved.append(result),limit=2,out=root,kind='tournament_fight')
            try:
                with mock.patch('arena.api_providers.APIProvider.respond',new=respond):
                    prepare([(m['id']+'-r0',m) for m in value['models']],value,root,journal,CoordinatorEngine(),on_progress=progress)
                self.assertTrue(observed)
                self.assertLessEqual(observed[0],2)
                self.assertEqual(sorted(saved),list(range(100)))
                self.assertTrue(all(s['status']=='submitted' for s in journal.states().values()))
                journal.verify()
            finally:journal.db.close()
