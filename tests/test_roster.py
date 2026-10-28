import unittest
from contextlib import closing
from unittest import mock
from pathlib import Path
from arena.core import ROOT, ArenaError, read_json, write_json, scratch_directory, submission, copy_submission, make_scenario, digest, file_hash
from arena.experiment import Journal, initial_state, run
from arena.roster import update, snapshot, effective, active


class RosterTests(unittest.TestCase):
    def test_withdrawal_uses_profile_id_not_provider_model_name(self):
        config={'_withdrawn_models':['open-router-gemma']}
        model={'id':'open-router-gemma','provider':'openai-compatible','model':'google/gemma:free'}
        self.assertFalse(active(config,model))
        self.assertFalse(active(config,{'model':'open-router-gemma','generation':0}))
        self.assertFalse(active(config,{'id':'open-router-gemma-r0','model':'open-router-gemma'}))
        self.assertTrue(active(config,{'id':'mistral','provider':'openai-compatible','model':'codestral-latest'}))

    def test_add_withdraw_and_reactivate_preserve_config_and_checkpoint(self):
        config=read_json(ROOT/'configs/offline-complete.json')
        with scratch_directory() as root:
            write_json(root/'experiment.json',{'config':config})
            original=(root/'experiment.json').read_bytes()
            journal=Journal(root)
            with closing(journal.db):
                model=config['models'][0];sid=model['id']+'-r0'
                state=initial_state(sid,model,config);state['status']='provider_unavailable'
                journal.save(sid,state,'provider_failure',{'error':'429'})
                before=journal.state(sid)
                added={'id':'reference','provider':'mock','profile':'single-shot'}
                selected=[config['models'][1]['id'],'reference']
                change=update(root,journal,config,[added],selected)
                self.assertEqual(change['added'],['reference'])
                self.assertEqual(change['removed'],[model['id']])
                self.assertEqual(journal.state(sid),before)
                self.assertEqual((root/'experiment.json').read_bytes(),original)
                self.assertEqual(effective(root,config)['models'][-1],added)
                self.assertEqual(config['models'][-1]['id'],selected[0])
                change=update(root,journal,config,[],selected+[model['id']])
                self.assertEqual(change['withdrawn'],[])
                self.assertEqual(snapshot(root)['revision'],2)
                journal.verify()

    def test_invalid_changes_are_atomic_and_freezing_requires_a_submission(self):
        config=read_json(ROOT/'configs/offline-complete.json')
        with scratch_directory() as root:
            journal=Journal(root)
            with closing(journal.db):
                model=config['models'][0];sid=model['id']+'-r0'
                journal.save(sid,initial_state(sid,model,config),'session_created')
                for selected,tracks in [([],None),(['missing'],None),([model['id'],model['id']],None),([model['id']],{model['id']:['control']})]:
                    with self.assertRaises(ArenaError):update(root,journal,config,[],selected,tracks)
                    self.assertIsNone(snapshot(root))
                journal.verify()


class FixtureEngine:
    identity={'fixture':'roster'}
    scientific_identity={}
    runtime_provenance={}
    artifact_provenance={}
    timeout=1

    def analyze(self,source,entrypoint,out):
        result={'status':'valid','success':True,'diagnostics':[],'diagnostic_messages':[],
                'source_sha256':submission(source,entrypoint)['sha256']}
        write_json(out/'result.json',result)
        write_json(out/'provenance.json',{'submission':submission(source,entrypoint)})
        return result

    def fight(self,paths,infos,scenario,seed,out):
        for side,(path,info) in enumerate(zip(paths,infos),1):copy_submission(Path(path),out/'strategies'/str(side),info)
        actual=make_scenario(scenario,[info['entrypoint'] for info in infos],seed,[info.get('team') for info in infos])
        write_json(out/'scenario.json',actual)
        write_json(out/'provenance.json',{'engine':self.identity,'submissions':infos,'scenario_sha256':digest(actual)})
        write_json(out/'outcome.json',{'winner':-1})
        metrics={key:0 for key in ('operations','errors','operation_limit_hits','stack_overflows','damage_dealt','damage_taken','healing_given','healing_received','ai_turns')}
        result={'status':'completed','winner_side':-1,'turns':1,'team_metrics':{'0':metrics,'1':metrics},'outcome_sha256':file_hash(out/'outcome.json')}
        write_json(out/'result.json',result)
        return result


class RosterProgressionTests(unittest.TestCase):
    def test_recovery_and_frozen_control_keep_existing_lineages(self):
        config=read_json(ROOT/'configs/offline-complete.json')
        config.update(generations=3,include_mirrors=False,budget_per_session={'max_calls':8,'max_agent_steps':20,'max_test_matches':0})
        config['models']=[{'id':'healthy','provider':'mock','profile':'single-shot'},
                          {'id':'gemma','provider':'mock','profile':'rate-limit'}]
        with scratch_directory() as root, mock.patch('arena.experiment.Engine',FixtureEngine):
            out=root/'run'
            self.assertTrue(run(config,out)['waiting_for_recovery'])
            original=(out/'experiment.json').read_bytes()
            journal=Journal(out)
            with closing(journal.db):
                healthy=journal.state('healthy-r0')
                reference={'id':'reference','provider':'mock','profile':'single-shot'}
                update(out,journal,config,[reference],['healthy','reference'],{'healthy':['control']})
            result=run(config,out,resume=True)
            self.assertFalse(result['incomplete'],result)
            self.assertEqual((out/'experiment.json').read_bytes(),original)
            journal=Journal(out)
            with closing(journal.db):
                states=journal.states();journal.verify()
                self.assertEqual(states['healthy-r0']['calls'],healthy['calls'])
                self.assertEqual(states['gemma-r0']['calls'],1)
                self.assertFalse(any(sid.startswith('gemma-r0-g') for sid in states))
                for generation in (1,2):
                    frozen=states[f'healthy-r0-g{generation}-control']
                    self.assertTrue(frozen['manual_frozen'])
                    self.assertEqual(frozen['completed_calls'],0)
                    self.assertEqual(frozen['submission'],healthy['submission'])
                    self.assertTrue(states[f'healthy-r0-g{generation}-feedback']['completed_calls'])
                    self.assertTrue(states[f'reference-r0-g{generation}-control']['submission'])
