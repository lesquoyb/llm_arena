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
