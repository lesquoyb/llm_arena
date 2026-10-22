"""Standalone workshop preserves exact prompts and serves lazy inspection records."""
from unittest import TestCase, mock

from arena.calibration import study
from arena.core import ArenaError, scratch_directory, write_json
from arena_web.calibration import Workshop
from arena_web.data import Store
from test_calibration import FixtureEngine, config


class CalibrationWebTests(TestCase):
    def test_study_inspection_lazy_blocks_fights_and_path_boundaries(self):
        with scratch_directory() as tmp, mock.patch('arena.calibration.Engine', FixtureEngine):
            workshop = Workshop(tmp/'studies', Store(tmp/'runs', tmp/'settings'))
            value = config()
            directory = workshop.root/'example'
            write_json(directory/'input.json', value)
            study(value, directory)
            query = {'study':['example'], 'trial':['trials/000'], 'session':['target-r0-g0']}
            self.assertEqual(workshop.listing()[0]['status'], 'completed')
            candidate = workshop.get('/api/candidate', query)
            self.assertEqual(candidate['config']['prompt'], value['prompt'])
            self.assertEqual(candidate['prompt_diff'], '')
            self.assertIsNone(candidate['analyst_directory'])
            missing={**query,'trial':['proposals/000'],'session':['analyst-r0']}
            self.assertEqual(workshop.get('/api/sessions',missing),[])
            with self.assertRaisesRegex(ArenaError,'No conversation has been recorded'):
                workshop.get('/api/conversation',missing)
            summary = workshop.get('/api/study', query)
            self.assertEqual(summary['trial_directories'], ['trials/000'])
            conversation = workshop.get('/api/conversation', {**query, 'offset':['0']})
            self.assertEqual(conversation['messages'][0]['role'], 'system')
            self.assertNotIn('value', conversation['messages'][0]['blocks'][0])
            prompt = workshop.get('/api/message', {**query, 'index':['0'], 'block':['0']})
            self.assertEqual(prompt['content'], value['prompt'])
            fights = workshop.get('/api/fights', query)
            self.assertEqual({m['panel'] for m in fights}, {'training', 'validation'})
            fight = workshop.get('/api/fight', {**query, 'path':[fights[0]['path']]})
            self.assertIn('events', fight)
            events = workshop.get('/api/events', query)
            event = workshop.get('/api/event', {**query, 'id':[str(events[0]['id'])]})
            self.assertTrue(event is None or isinstance(event, (dict, list)))
            for route, extra in [('/api/file', {'path':['../../input.json']}),
                                 ('/api/fight', {'path':['unknown']}),
                                 ('/api/message', {'session':['other'], 'index':['0'], 'block':['0']})]:
                with self.assertRaises(ArenaError): workshop.get(route, {**query, **extra})

    def test_target_continuation_preserves_pending_tools_and_rejects_uncertain_requests(self):
        from arena.experiment import Journal,initial_state
        from arena.calibration import experiment_config
        with scratch_directory() as tmp:
            workshop=Workshop(tmp/'studies',Store(tmp/'runs',tmp/'settings'))
            value=config();directory=workshop.root/'blocked';folder=directory/'trials/000'
            write_json(directory/'input.json',value)
            write_json(directory/'study.json',{'active_trial':0,'status':'blocked'})
            write_json(folder/'report.json',{'session':'target-r0-g0','status':'blocked'})
            journal=Journal(folder)
            try:
                state=initial_state('target-r0-g0',value['target'],experiment_config(value))
                state.update(status='no_submission',submission_reminders=3)
                journal.save('target-r0-g0',state,'fixture')
            finally: journal.db.close()
            write_json(folder/'report.json',{'session':'target-r0-g0','status':'completed'})
            with self.assertRaisesRegex(ArenaError,'already been evaluated'):
                workshop.recover_target('blocked')
            write_json(folder/'report.json',{'session':'target-r0-g0','status':'blocked'})
            workshop.recover_target('blocked','Inspect the saved code first.')
            journal=Journal(folder)
            try:
                state=journal.state('target-r0-g0')
                self.assertEqual(state['status'],'running')
                self.assertEqual(state['submission_reminders'],0)
                self.assertIn('Inspect the saved code first.',state['history'][-1]['content'])
                self.assertNotIn('submission',state)
                pending={'tool_calls':[{'name':'read_file','arguments':{'path':'main.leek'},'id':'pending'}]}
                state.update(pending=pending,cursor=0)
                journal.save('target-r0-g0',state,'fixture_pending')
            finally: journal.db.close()
            workshop.recover_target('blocked')
            journal=Journal(folder)
            try:
                state=journal.state('target-r0-g0');self.assertEqual(state['pending'],pending)
                state.update(status='needs_reconciliation',in_flight=True,money_reserved='0.1')
                journal.save('target-r0-g0',state,'fixture_uncertain')
            finally: journal.db.close()
            with self.assertRaisesRegex(ArenaError,'billing reconciliation'):
                workshop.recover_target('blocked')
            workshop.recover_target('blocked',reconciliation={'cost_usd':'0.02','note':'Checked provider receipt'})
            journal=Journal(folder)
            try:
                state=journal.state('target-r0-g0')
                self.assertFalse(state['in_flight'])
                self.assertEqual(state['cost_spent'],'0.02')
                self.assertEqual(state['pending'],pending)
            finally: journal.db.close()

    def test_human_acceptance_is_bound_to_the_blocked_proposal(self):
        from arena.core import read_json,file_hash
        with scratch_directory() as tmp:
            workshop=Workshop(tmp/'studies',Store(tmp/'runs',tmp/'settings'))
            directory=workshop.root/'blocked';folder=directory/'proposals/001'
            write_json(directory/'study.json',{'active_trial':0,'active_proposal':1,'status':'blocked'})
            write_json(folder/'proposal-draft.json',{'prompt':'General authoring instructions'})
            write_json(folder/'guard.json',{'identity':'specific-check','status':'rejected'})
            self.assertTrue(workshop.active_work(directory,read_json(directory/'study.json'))['guard_override_available'])
            workshop.accept_proposal('blocked')
            decision=read_json(folder/'guard-override.json')
            self.assertEqual(decision['draft_sha256'],file_hash(folder/'proposal-draft.json'))
            self.assertEqual(decision['guard_identity'],'specific-check')
            self.assertFalse((folder/'proposal.json').exists())
            write_json(folder/'proposal-draft.json',{'prompt':'A different proposal'})
            self.assertNotEqual(decision['draft_sha256'],file_hash(folder/'proposal-draft.json'))
            write_json(folder/'guard.json',{'identity':'failed-check','status':'unavailable'})
            with self.assertRaisesRegex(ArenaError,'No rejected proposal check'):
                workshop.accept_proposal('blocked')

    def test_worker_receives_credentials_without_saving_them(self):
        with scratch_directory() as tmp:
            workshop = Workshop(tmp/'studies', Store(tmp/'runs', tmp/'settings'))
            value = config()
            value['target'] = {'id':'local', 'provider':'openai-compatible', 'model':'qwen',
                               'endpoint':'http://127.0.0.1:11434/v1/chat/completions',
                               'api_key_env':'CALIBRATION_TEST_KEY',
                               'pricing':{'date':'2026-10-16','currency':'USD','input_per_million':'0','output_per_million':'0'}}
            value['spending'] = {'allow_paid_calls':True}
            with mock.patch('arena_web.calibration.subprocess.Popen') as launch:
                launch.return_value.poll.return_value = None
                workshop.start(value, False, 'local-study', {'local':'private-test-key'})
                self.assertEqual(launch.call_args.kwargs['env']['CALIBRATION_TEST_KEY'], 'private-test-key')
                self.assertNotIn('private-test-key', (workshop.root/'local-study/input.json').read_text())
                with self.assertRaisesRegex(ArenaError, 'running'): workshop.start(value, False)

    def test_analyst_proposal_has_readable_decision_and_comparison_data(self):
        with scratch_directory() as tmp, mock.patch('arena.calibration.Engine', FixtureEngine):
            workshop=Workshop(tmp/'studies',Store(tmp/'runs',tmp/'settings'))
            value=config()
            value.update(max_rounds=1,min_rounds=1)
            value['optimizer']['max_trials']=2
            value['analyst']={'id':'analyst','provider':'mock','profile':'single-shot'}
            directory=workshop.root/'automatic'
            write_json(directory/'input.json',value)
            study(value,directory,automatic=True)
            result=workshop.get('/api/proposal',{'study':['automatic'],'trial':['proposals/001']})
            self.assertFalse(result['baseline'])
            self.assertEqual(result['candidate'],2)
            self.assertEqual(result['decision'],'Rejected')
            self.assertIn('Offline fixture',result['rationale'])
            self.assertIn('Prefer simple',result['prompt_diff'])
            self.assertIsNotNone(result['metrics_before'])
            self.assertIsNotNone(result['metrics_after'])
            detail=workshop.get('/api/study',{'study':['automatic']})
            self.assertEqual(detail['proposals'][0]['directory'],'proposals/001')
            live=workshop.get('/api/live-response',{'study':['automatic'],'trial':['proposals/001'],'session':['analyst-r0']})
            self.assertEqual(live['role'],'analyst')
            self.assertIsNone(live['budget'])
            self.assertEqual(live['proposal_phase']['phase'],'ready')

class CalibrationSummaryTests(TestCase):
    def test_fight_summary_uses_recorded_opponents_and_outcomes(self):
        from arena.core import scratch_directory,write_json
        from arena.calibration import defaults
        from arena_web.calibration import Workshop
        with scratch_directory() as out:
            workshop=Workshop(out,store=object())
            trial=out/'sample/trials/000'
            write_json(trial/'calibration.json',{'config':defaults()})
            for index,winner in enumerate((0,-1,1)):
                write_json(trial/f'evaluations/training-target-r0-g0/records/{index}.json',{'session':'target-r0-g0','opponent':'passive','seed':101,'side':0,'result':{'status':'completed','winner_side':winner}})
            result=workshop.get('/api/fight-summary',{'study':['sample'],'trial':['trials/000']})
            self.assertEqual(len(result['rows']),1)
            self.assertEqual(result['rows'][0]['wins'],1)
            self.assertEqual(result['rows'][0]['draws'],1)
            self.assertEqual(result['rows'][0]['losses'],1)
            self.assertEqual(result['rows'][0]['round'],1)
            self.assertEqual(result['rows'][0]['opponent'],'passive')
