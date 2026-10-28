"""Frozen participant reuse preserves code and never invokes a provider."""
import copy
from unittest import TestCase, mock
from arena.core import ROOT, ArenaError, scratch_directory, read_json
from arena.experiment import Journal, run_session, validate_config
from arena.reference_strategies import participant, for_scenario
from arena.presets import simple_scenario, participant_scenario, dream_team_scenario
from arena_web.data import Store


class SavedStrategyTests(TestCase):
    def test_reuse_ignores_preparation_budgets_and_can_be_imported_again(self):
        with scratch_directory() as root:
            scenario=simple_scenario()
            model=participant('turret','fixed',scenario)
            config=read_json(ROOT/'configs/offline-demo.json')
            config.update(models=[model],scenario=scenario)
            config['budget_per_session']={'max_calls':1,'max_agent_steps':1}
            out=root/'runs'/'source';out.mkdir(parents=True)
            from arena.core import write_json
            write_json(out/'experiment.json',{'config':config})
            journal=Journal(out)
            try:
                with mock.patch('arena.experiment.provider_response',side_effect=AssertionError('No inference')):
                    run_session('fixed-r0',model,config,out,journal,None)
                    run_session('fixed-r0',model,config,out,journal,None)
                state=journal.state('fixed-r0')
                self.assertEqual(state['calls'],0)
                self.assertEqual(state['submission'],model['strategy']['submission'])
                self.assertEqual(state['status'],'submitted')
            finally:
                journal.db.close()
            store=Store(root/'runs',root/'ui')
            store.import_strategy('source','fixed-r0','copy')
            copied=next(row for row in store.catalog() if row['id']=='copy')
            self.assertEqual(copied['strategy']['files'],model['strategy']['files'])
            self.assertTrue(store.versions('source','fixed-r0')['versions'])
            with self.assertRaisesRegex(ArenaError,'already exists'):
                store.import_strategy('source','fixed-r0','copy')

    def test_fingerprint_and_scenario_changes_are_rejected_before_launch(self):
        config=read_json(ROOT/'configs/offline-demo.json')
        config['scenario']=simple_scenario()
        config['models']=[participant('turret','fixed',config['scenario'])]
        changed=copy.deepcopy(config)
        changed['models'][0]['strategy']['files']['main.leek']+='\n// tampered'
        with self.assertRaisesRegex(ArenaError,'fingerprint'):
            validate_config(changed)
        config['scenario']['max_turns']+=1
        with self.assertRaisesRegex(ArenaError,'original scenario'):
            validate_config(config)

    def test_catalog_reference_adapts_to_scenario_without_changing_source_or_profile(self):
        from arena.saved_strategy import validate
        original=participant('passive','reference-passive',simple_scenario())
        before=copy.deepcopy(original)
        shared=simple_scenario();shared['max_turns']=333
        for scenario in (shared,dream_team_scenario(),participant_scenario()):
            adapted=for_scenario(original,scenario)
            validate(adapted,scenario)
            self.assertEqual(original,before)
            self.assertEqual(adapted['strategy']['files']['main.leek'],original['strategy']['files']['main.leek'])
            if scenario.get('team_selection'):
                self.assertEqual(len(adapted['strategy']['submission']['team']['members']),scenario['team_size'])
            else:
                self.assertNotIn('team.json',adapted['strategy']['files'])

    def test_imported_submission_is_not_rebound_and_reference_tampering_is_rejected(self):
        from arena.saved_strategy import validate
        original=participant('passive','reference-passive',simple_scenario())
        imported=copy.deepcopy(original)
        imported['strategy']['origin']={'run':'source','session':'source-r0'}
        scenario=simple_scenario();scenario['max_turns']=333
        with self.assertRaisesRegex(ArenaError,'original scenario'):
            validate(for_scenario(imported,scenario),scenario)
        original['strategy']['files']['main.leek']+='tampered'
        with self.assertRaisesRegex(ArenaError,'fingerprint'):
            for_scenario(original,scenario)

    def test_draft_and_existing_roster_bind_default_reference(self):
        from arena.core import write_json,digest
        from arena.experiment import initial_state
        from arena.roster import update
        scenario=simple_scenario();scenario['max_turns']=333
        original=participant('passive','reference-passive',simple_scenario())
        config=read_json(ROOT/'configs/offline-demo.json')
        config.update(scenario=scenario,models=[original])
        with scratch_directory() as root:
            store=Store(root/'runs',root/'ui')
            write_json(store.state/'participants.json',[original])
            draft=store.save_draft(config)
            self.assertEqual(draft['config']['models'][0]['strategy']['scenario_sha256'],digest(scenario))
            existing=copy.deepcopy(config)
            existing['models']=[{'id':'healthy','provider':'mock','profile':'single-shot'}]
            out=store.runs/'existing';out.mkdir()
            journal=Journal(out)
            try:
                journal.save('healthy-r0',initial_state('healthy-r0',existing['models'][0],existing),'session_created')
                change=update(out,journal,existing,[original],['healthy','reference-passive'])
                self.assertEqual(change['models'][-1]['strategy']['scenario_sha256'],digest(scenario))
                journal.verify()
            finally:
                journal.db.close()
