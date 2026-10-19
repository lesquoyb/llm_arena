import copy
import json
from pathlib import Path
from unittest import TestCase, mock

from arena.core import (ROOT, ArenaError, scratch_directory, read_json, write_json,
                        file_hash, make_scenario, copy_submission)
from arena.calibration import (defaults, validate, trial, study, plateau, objective, accept,
                               CalibrationFights, propose, study_spending)
from arena.experiment import Journal
from arena.preparation import Preparation
from arena.api_providers import APIProvider, ProviderFailure


class FixtureEngine:
    identity={'fixture':'calibration'}
    scientific_identity=identity
    def __init__(self): self.fights=0;self.analyses=0
    def analyze(self,source,entry,out):
        self.analyses+=1
        from arena.core import submission
        result={'status':'valid','success':True,'diagnostics':[], 'source_sha256':submission(source,entry)['sha256']}
        write_json(out/'result.json',result)
        write_json(out/'provenance.json',{'submission':submission(source,entry)})
        return result
    def fight(self,sources,infos,config,seed,out):
        self.fights+=1
        outcome={'fight':{'actions':[[6,1]],'leeks':[]},'winner':-1,'duration':1,'logs':{}}
        write_json(out/'outcome.json',outcome)
        write_json(out/'scenario.json',make_scenario(config,[i['entrypoint'] for i in infos],seed,[i.get('team') for i in infos]))
        write_json(out/'provenance.json',{'engine':self.identity,'submissions':infos})
        for i,(source,info) in enumerate(zip(sources,infos),1): copy_submission(Path(source),out/'strategies'/str(i),info)
        result={'status':'completed','winner_side':-1,'turns':1,'outcome_sha256':file_hash(out/'outcome.json')}
        write_json(out/'result.json',result)
        return result


def config():
    value=defaults()
    value.pop('rl')  # These fixtures exercise the legacy, frozen search protocol.
    value.update(max_rounds=5,min_rounds=3,patience=2,replicates=1,stop_on_plateau=True,opponents=['passive'],
                 training_seeds=[101],validation_seeds=[301],audit_seeds=[701])
    value['budget_per_session']={}
    value['optimizer']['round_penalty']=0.002
    return value


class CalibrationTests(TestCase):
    def test_defaults_start_with_one_short_observation_and_legacy_configs_still_load(self):
        value=defaults()
        self.assertEqual(value['max_rounds'],1)
        self.assertEqual(value['replicates'],1)
        self.assertFalse(value['stop_on_plateau'])
        self.assertEqual(value['budget_per_session']['max_calls'],8)
        self.assertEqual(value['optimizer']['round_penalty'],0)
        validate(value)
        value.pop('stop_on_plateau')
        validate(value)

    def test_rounds_plateau_frozen_sources_and_exact_resume_without_recomputation(self):
        with scratch_directory() as tmp:
            engine=FixtureEngine();value=config();out=tmp/'trial'
            report=trial(value,out,engine=engine)
            self.assertEqual(report['status'],'completed')
            self.assertEqual(len(report['replicates'][0]['rounds']),3)
            self.assertEqual(report['replicates'][0]['stop_reason'],'plateau')
            self.assertEqual(report['validation_score'],.5)
            self.assertIsNone(report['tokens'])
            self.assertTrue(report['simulated'])
            self.assertEqual(report['replicates'][0]['rounds'][1]['previous_versions']['score'],.5)
            journal=Journal(out)
            try:
                first=journal.state('target-r0-g0');last=journal.state('target-r0-g2')
                self.assertEqual(first['history'][0],{'role':'system','content':value['prompt']})
                self.assertFalse(any('validation-' in json.dumps(m) for m in last['history'] if m['role']=='user'))
                self.assertEqual(last['calibration']['previous_sessions'],['target-r0-g0','target-r0-g1'])
                access=CalibrationFights(out,last)
                listing=access.call('list_past_fights',{})
                self.assertEqual(listing['total'],4) # Previous round only: two training and two previous-version fights
                self.assertEqual(listing['round'],2)
                with self.assertRaises(ArenaError): access.call('read_past_fight',{'fight_id':'validation-secret'})
                tools=Preparation(tmp/'isolated',out/'corpus',engine,value['scenario'],feedback=access,allowed_tools=['submit'])
                with self.assertRaisesRegex(ArenaError,'disabled'): tools.call('list_past_fights',{},'1')
            finally: journal.db.close()
            counts=(engine.fights,engine.analyses)
            resumed=trial(value,out,resume=True,engine=engine)
            self.assertEqual(resumed,report)
            self.assertEqual((engine.fights,engine.analyses),counts)
            (out/'corpus/authoring.md').write_text('changed')
            with self.assertRaisesRegex(ArenaError,'Cannot resume'): trial(value,out,resume=True,engine=engine)

    def test_automatic_search_rejects_equal_candidates_retains_incumbent_and_audits_only_selected(self):
        with scratch_directory() as tmp, mock.patch('arena.calibration.Engine',FixtureEngine):
            value=config();value['analyst']=copy.deepcopy(value['target']);value['optimizer'].update(max_trials=5,patience=1)
            report=study(value,tmp/'study',True)
            self.assertEqual(report['status'],'completed')
            self.assertEqual(len(report['trials']),2)
            self.assertEqual([r['accepted'] for r in report['trials']],[True,False])
            self.assertEqual(report['incumbent'],0)
            self.assertEqual(report['audit'][0]['score'],.5)
            self.assertTrue((tmp/'study/proposals/001/proposal.json').is_file())
            self.assertFalse((tmp/'study/trials/001/evaluations/audit-target-r0-g2').exists())
            self.assertEqual(study(value,tmp/'study',True),report)

    def test_objective_requires_equal_score_before_token_saving_and_detects_late_convergence(self):
        value=config()
        def report(scores,tokens):
            r={'replicates':[{'rounds':[{'training':{'score':s},'validation':{'score':s},'validity':'valid',
                'input_tokens':tokens,'output_tokens':0,'cost_usd':'0'} for s in scores]}]}
            r.update(objective(r,value));return r
        baseline=report([.5,.8,.8],1000)
        lean=report([.5,.8,.8],500)
        self.assertTrue(accept(lean,baseline,value))
        self.assertFalse(accept(report([.4,.4,.4],1),baseline,value))
        self.assertEqual(report([.9,.4,.4],100)['convergence_round'],2)
        self.assertFalse(plateau([.1,.2,.3],value))
        self.assertTrue(plateau([.4,.4,.4],value))
        invalid=copy.deepcopy(lean);invalid['final_valid']=False
        self.assertFalse(accept(invalid,baseline,value))

    def test_system_prompt_is_native_for_all_protocols_and_empty_editor_tools_are_omitted(self):
        history=[{'role':'system','content':'SYSTEM EXACT'},{'role':'user','content':'TASK'}]
        for provider in ('openai','openai-compatible','anthropic','gemini'):
            payload=APIProvider({'provider':provider,'model':'fixture'}).payload(history,[],100)
            self.assertNotIn('tools',payload)
            if provider=='anthropic': self.assertEqual(payload['system'],'SYSTEM EXACT')
            elif provider=='gemini': self.assertEqual(payload['systemInstruction']['parts'],[{'text':'SYSTEM EXACT'}])
            else: self.assertEqual(payload['messages'][0],{'role':'system','content':'SYSTEM EXACT'})

    def test_seed_panels_and_api_activation_are_checked_before_work(self):
        value=config();value['validation_seeds']=[101]
        with self.assertRaisesRegex(ArenaError,'disjoint'): validate(value)
        value=config();value['tools']=['submit']
        with self.assertRaisesRegex(ArenaError,'write_file'): validate(value)
        value=config();value['optimizer']['parameter_grid']={'temperature':[0,.5]}
        with self.assertRaisesRegex(ArenaError,'native API'): validate(value)
        with scratch_directory() as tmp:
            with self.assertRaisesRegex(ArenaError,'analyst'): study(config(),tmp/'new',True)

    def test_uncertain_editor_receipt_is_never_reused_to_advance_the_search(self):
        with scratch_directory() as tmp:
            value=config();value['analyst']=copy.deepcopy(value['target'])
            folder=tmp/'proposal';folder.mkdir()
            journal=Journal(folder)
            state={'status':'needs_reconciliation','in_flight':True,'history':[], 'pending':{'native':{'content':'{}'}}}
            journal.save('analyst-r0',state,'fixture');journal.db.close()
            with self.assertRaisesRegex(ArenaError,'reconciliation'): propose(value,{},tmp,folder)

    def test_invalid_scripts_score_zero_without_meaningless_fights_and_return_compiler_feedback(self):
        class InvalidEngine(FixtureEngine):
            def analyze(self,source,entry,out):
                result=super().analyze(source,entry,out)
                result.update(status='invalid',success=False,diagnostics=[[0,'main.leek',1,1,1,2,35]])
                write_json(out/'result.json',result)
                return result
        with scratch_directory() as tmp:
            engine=InvalidEngine();value=config();out=tmp/'trial'
            report=trial(value,out,engine=engine)
            self.assertFalse(report['final_valid']);self.assertEqual(report['validation_score'],0)
            self.assertEqual(engine.fights,0)
            self.assertEqual(report['replicates'][0]['rounds'][0]['training']['invalid_forfeits'],2)
            journal=Journal(out)
            try:
                state=journal.state('target-r0-g1')
                instruction=next(m for m in state['history'] if m.get('generation')==1 and m['role']=='user')
                self.assertEqual(instruction['compilation'][0]['message'],'Expected a value or expression')
            finally:journal.db.close()

    def test_editor_repairs_malformed_json_once_and_does_not_repeat_a_saved_paid_response(self):
        with scratch_directory() as tmp:
            value=config();report=trial(value,tmp/'incumbent',engine=FixtureEngine())
            value['spending']={'allow_paid_calls':True}
            value['analyst']={'id':'editor','provider':'openai-compatible','model':'fixture','api_key_env':'ARENA_EDITOR_FIXTURE',
                'endpoint':'http://127.0.0.1:11434/v1/chat/completions',
                'pricing':{'date':'2026-10-16','currency':'USD','input_per_million':'0','output_per_million':'0'}}
            proposal={'prompt':value['prompt']+'\nUse simple steps.','tools':value['tools'],'rationale':'Fix observed syntax mistakes.'}
            def answer(text):
                return {'role':'assistant','native':{'role':'assistant','content':text},'tool_calls':[],
                        'usage':{'input_tokens':12,'output_tokens':3},'cost_usd':'0'}
            with mock.patch('arena.api_providers.APIProvider.respond',side_effect=[answer('not JSON'),answer(json.dumps(proposal))]) as respond:
                self.assertEqual(propose(value,report,tmp/'incumbent',tmp/'proposal'),proposal)
                self.assertEqual(respond.call_count,2)
                self.assertEqual(propose(value,report,tmp/'incumbent',tmp/'proposal'),proposal)
                self.assertEqual(respond.call_count,2)
            journal=Journal(tmp/'proposal')
            try:
                state=journal.state('analyst-r0')
                self.assertEqual(state['repair_attempts'],1)
                self.assertEqual(state['input_tokens'],24)
                self.assertEqual(state['status'],'submitted')
            finally:journal.db.close()
            write_json(tmp/'proposal/proposal.json',{**proposal,'prompt':'tampered'})
            with self.assertRaisesRegex(ArenaError,'changed'): propose(value,report,tmp/'incumbent',tmp/'proposal')

    def test_study_ceiling_includes_earlier_candidates_before_reserving_another_request(self):
        from arena.experiment import initial_state,provider_response
        from test_web import api_model
        with scratch_directory() as tmp:
            write_json(tmp/'study.json',{})
            for directory,cost in [('trials/000','0.08'),('proposals/001','0.01')]:
                (tmp/directory).mkdir(parents=True)
                journal=Journal(tmp/directory);journal.save('record',{'cost_spent':cost,'history':[]},'fixture');journal.db.close()
            directory=tmp/'trials/001';directory.mkdir()
            journal=Journal(directory)
            try:
                self.assertEqual(str(study_spending(journal)),'0.09')
                value=config();value['target']=api_model();value['spending']={'allow_paid_calls':True,'max_total_usd':'0.1'}
                from arena.calibration import experiment_config
                exp=experiment_config(value);state=initial_state('target-r0-g0',value['target'],exp)
                state['calibration']={'tools':value['tools'],'previous_sessions':[]}
                with mock.patch('arena.experiment.reservation',return_value={'cost_bound':'0.02','input_bound':10,'output_bound':10}), mock.patch('arena.api_providers.APIProvider.respond') as respond:
                    self.assertIsNone(provider_response('target-r0-g0',state,value['target'],exp,journal))
                    self.assertEqual(state['status'],'budget_exhausted');respond.assert_not_called()
            finally:journal.db.close()

    def test_preparation_limits_are_explained_and_returned_in_calibration_tools(self):
        with scratch_directory() as tmp:
            value=config()
            value.update(max_rounds=1,min_rounds=1)
            value['budget_per_session']={'max_calls':8,'max_agent_steps':20,'max_test_matches':4}
            trial(value,tmp/'trial',engine=FixtureEngine())
            journal=Journal(tmp/'trial')
            try:
                history=journal.state('target-r0-g0')['history']
                instruction=next(message for message in history if message['role']=='user')
                self.assertEqual(instruction['preparation_budget']['limits']['calls']['remaining'],8)
                self.assertIn('Save a complete strategy early',instruction['budget_instructions'])
                receipts=[message['result'] for message in history if message['role']=='tool']
                self.assertTrue(receipts)
                self.assertTrue(all('preparation_budget' in result for result in receipts))
                self.assertLess(receipts[-1]['preparation_budget']['limits']['calls']['remaining'],8)
            finally:
                journal.db.close()


class NativeCalibrationTests(TestCase):
    def test_native_rounds_and_history_fights_resume_without_rewriting_completed_matches(self):
        value=config();value['scenario']['max_turns']=2
        with scratch_directory() as tmp:
            out=tmp/'native'
            report=study(value,out)
            self.assertEqual(report['status'],'completed')
            self.assertTrue(report['trials'][0]['report']['final_valid'])
            self.assertTrue(report['trials'][0]['report']['converged'])
            records=list(out.glob('trials/000/evaluations/*/records/*.json'))
            self.assertEqual(len(records),20) # 12 fixed-panel fights, six against prior versions, two audit
            before={p.relative_to(out).as_posix():(p.stat().st_mtime_ns,p.read_bytes()) for p in out.glob('**/outcome.json')}
            self.assertEqual(study(value,out),report)
            self.assertEqual(before,{p.relative_to(out).as_posix():(p.stat().st_mtime_ns,p.read_bytes()) for p in out.glob('**/outcome.json')})
