"""Frozen participant reuse preserves code and never invokes a provider."""
import copy
from unittest import TestCase, mock
from arena.core import ROOT, ArenaError, scratch_directory, read_json
from arena.experiment import Journal, run_session, validate_config
from arena.reference_strategies import participant
from arena.presets import simple_scenario
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
