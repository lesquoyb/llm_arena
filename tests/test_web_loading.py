"""Heavy result artifacts must not be required for ordinary tab navigation."""
import unittest
from unittest.mock import patch
from arena.core import ROOT, read_json, write_json, scratch_directory
from arena.experiment import Journal, initial_state
from arena_web.data import Store
from arena_web.faults import report


class WebLoadingTests(unittest.TestCase):
    def test_source_inventory_keeps_user_tools_and_frozen_sources(self):
        with scratch_directory() as root:
            store=Store(root/'runs',root/'settings');out=store.runs/'run'
            write_json(out/'experiment.json',{'config':read_json(ROOT/'configs/offline-complete.json')})
            for name in ('sessions/one/workspace/tools/helper.leek','submissions/frozen/main.leek',
                         'sessions/one/tools/call-1-tool-0/result.json','tournament/matches/fight/result.json'):
                write_json(out/name,{})
            files={row['path'] for row in store.files('run',include_artifacts=False)['files']}
            self.assertIn('sessions/one/workspace/tools/helper.leek',files)
            self.assertIn('submissions/frozen/main.leek',files)
            self.assertNotIn('sessions/one/tools/call-1-tool-0/result.json',files)
            self.assertNotIn('tournament/matches/fight/result.json',files)
            self.assertGreater(len(store.files('run')['files']),len(files))

    def test_new_fight_reuses_authoring_receipts_but_updates_runtime_errors(self):
        with scratch_directory() as root:
            store=Store(root/'runs',root/'settings');out=store.runs/'run'
            config=read_json(ROOT/'configs/offline-complete.json');model=config['models'][0];sid=model['id']+'-r0'
            write_json(out/'experiment.json',{'config':config});journal=Journal(out)
            try:
                journal.save(sid,initial_state(sid,model,config),'fixture')
                journal.record(sid,'tool_reserved',{'name':'validate_team'})
                journal.record(sid,'tool_result',{'valid':False,'errors':['Level limit exceeded']})
            finally:journal.db.close()
            before=report(store,'run')
            self.assertEqual(before['incidents'][0]['message'],'Level limit exceeded')
            write_json(out/'tournament/records/fight.json',{'match':{'sides':[sid,'opponent'],'seed':1},
                'directory':'matches/fight','result':{'status':'completed','winner_side':0,'team_metrics':{'0':{'errors':3}}}})
            with patch('arena_web.faults.receipt',side_effect=AssertionError('Replayed unchanged authoring receipt')):
                after=report(store,'run')
            self.assertEqual(after['sessions'][0]['runtime_errors'],3)
            self.assertEqual(after['sessions'][0]['invalid_teams'],1)
