"""Workspace metadata stays separate from immutable experiment inputs."""
import copy
import unittest

from arena.core import ArenaError, ROOT, read_json, scratch_directory, write_json
from arena.experiment import Journal, initial_state
from arena_web.data import Store


def competition(store, identifier, life=600, archived=False):
    config=read_json(ROOT/'configs/offline-complete.json')
    config['scenario']['entity']['life']=life
    root=store.runs/identifier
    write_json(root/'experiment.json',{'config':config,'engine':{'fixture':True}})
    write_json(root/'report.json',{'sessions':2,'cost_usd':'0.2'})
    if archived:write_json(root/'export.json',{'fixture':True})
    journal=Journal(root)
    try:
        for model in config['models']:
            sid=model['id']+'-r0'
            state=initial_state(sid,model,config)
            state.update(status='submitted',validity='valid',submission={'entrypoint':'main.leek','sha256':sid},
                         token_usage_known=True,input_tokens=10,output_tokens=2,cost_spent='0.1',history=[])
            journal.save(sid,state,'fixture')
    finally:journal.db.close()
    sides=[m['id']+'-r0' for m in config['models']]
    write_json(root/'tournament/records/fight.json',{'match':{'sides':sides,'seed':1,'mirror':False},
        'directory':'matches/fight','result':{'status':'completed','winner_side':0,'turns':2}})
    return root,config


class WorkspaceTests(unittest.TestCase):
    def test_membership_moves_without_changing_runs_and_delete_only_unassigns(self):
        with scratch_directory() as root:
            store=Store(root/'runs',root/'settings')
            run,config=competition(store,'run')
            frozen=read_json(run/'experiment.json')
            tests=store.save_workspace('Tests');bench=store.save_workspace('Benchmark')
            draft=store.save_draft(config,workspace_id=tests['id'])
            store.assign_workspace(tests['id'],runs=['run'])
            store.inherit_workspace(draft['id'],'new-run')
            self.assertEqual(store.workspace_index()['runs']['new-run'],tests['id'])
            store.assign_workspace(bench['id'],runs=['run'])
            self.assertEqual(store.workspace_runs(tests['id']),[])
            self.assertEqual(store.workspace_runs(bench['id'])[0]['id'],'run')
            self.assertEqual(read_json(run/'experiment.json'),frozen)
            store.delete_workspace(bench['id'])
            self.assertEqual(store.workspace_runs('unassigned')[0]['id'],'run')
            self.assertTrue(run.is_dir())
            self.assertEqual(store.draft(draft['id'])['workspace_id'],tests['id'])

    def test_aggregate_counts_resources_once_and_separates_protocols_and_export_copies(self):
        with scratch_directory() as root:
            store=Store(root/'runs',root/'settings');workspace=store.save_workspace('Campaign')
            for name,life,archived in [('a',600,False),('b',600,False),('different',601,False),('copy',600,True)]:
                competition(store,name,life,archived)
            store.assign_workspace(workspace['id'],runs=['a','b','different','copy'])
            result=store.workspace_summary(workspace['id'])
            self.assertEqual(result['totals']['competitions'],3)
            self.assertEqual(result['totals']['completed_matches'],3)
            self.assertEqual(result['totals']['sessions'],6)
            self.assertEqual(result['totals']['input_tokens'],60)
            self.assertEqual(result['totals']['known_cost_usd'],'0.6')
            self.assertEqual(len(result['groups']),2)
            pooled=next(group for group in result['groups'] if len(group['runs'])==2)
            self.assertEqual(pooled['models'][0]['score'],1)
            self.assertEqual(pooled['models'][0]['conversations'],2)
            self.assertEqual(len(result['excluded']),1)

    def test_atomic_member_validation_and_replace_keep_other_workspaces(self):
        with scratch_directory() as root:
            store=Store(root/'runs',root/'settings')
            for name in ('a','b'):competition(store,name)
            one=store.save_workspace('One');two=store.save_workspace('Two')
            store.assign_workspace(one['id'],runs=['a']);store.assign_workspace(two['id'],runs=['b'])
            before=copy.deepcopy(store.workspace_index())
            with self.assertRaises(ArenaError):store.assign_workspace(one['id'],runs=['b','../outside'],replace=True)
            self.assertEqual(store.workspace_index(),before)
            store.assign_workspace(one['id'],runs=[],replace=True)
            self.assertIsNone(store.workspace_index()['runs'].get('a'))
            self.assertEqual(store.workspace_index()['runs']['b'],two['id'])
            with self.assertRaises(ArenaError):store.save_workspace('two')

    def test_same_participant_versions_do_not_create_model_wins_and_losses(self):
        with scratch_directory() as root:
            store=Store(root/'runs',root/'settings')
            run,config=competition(store,'run')
            workspace=store.save_workspace('Campaign');store.assign_workspace(workspace['id'],runs=['run'])
            journal=Journal(run)
            try:
                state=initial_state('mock-repair-r0-g1-feedback',config['models'][0],config)
                state.update(model='mock-repair',generation=1,condition='feedback',status='submitted',
                             submission={'entrypoint':'main.leek','sha256':'next'})
                journal.save('mock-repair-r0-g1-feedback',state,'fixture')
            finally:journal.db.close()
            write_json(run/'tournament/records/internal.json',{'match':{'sides':['mock-repair-r0','mock-repair-r0-g1-feedback'],'seed':2},
                'directory':'matches/internal','result':{'status':'completed','winner_side':1}})
            result=store.workspace_summary(workspace['id'])
            self.assertEqual(result['totals']['completed_matches'],2)
            self.assertEqual(result['groups'][0]['internal_matches'],1)
            self.assertEqual(sum(row['wins'] for row in result['groups'][0]['models']),1)
            self.assertEqual(sum(row['losses'] for row in result['groups'][0]['models']),1)

    def test_frozen_tournament_preserves_origin_rounds_without_new_generation_cost(self):
        with scratch_directory() as root:
            store=Store(root/'runs',root/'settings');run=store.runs/'frozen'
            scenario=read_json(ROOT/'configs/offline-complete.json')['scenario']
            strategies=[{'id':sid,'submission':{'sha256':sid},'origin':{'variant':variant,'round':round_number}}
                        for sid,variant,round_number in [('old','a',1),('new','a',2),('other','b',1)]]
            write_json(run/'experiment.json',{'manifest':{'scenario':scenario,'strategies':strategies},'engine':{}})
            for name,sides in [('external',['new','other']),('internal',['old','new'])]:
                write_json(run/f'records/{name}.json',{'match':{'sides':sides,'seed':1},'directory':'matches/'+name,
                    'result':{'status':'completed','winner_side':0}})
            workspace=store.save_workspace('Frozen');store.assign_workspace(workspace['id'],runs=['frozen'])
            result=store.workspace_summary(workspace['id'])
            self.assertEqual(result['totals']['sessions'],0)
            self.assertEqual(result['totals']['frozen_strategies'],3)
            self.assertEqual(result['totals']['known_cost_usd'],'0')
            self.assertEqual(result['groups'][0]['internal_matches'],1)
            winner=next(row for row in result['groups'][0]['models'] if row['name']=='a')
            self.assertEqual(winner['round'],2)
            self.assertEqual(winner['wins'],1)
