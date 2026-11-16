import contextlib
import io
import unittest
from unittest import mock

from arena.core import ROOT, copy_submission, read_json, scratch_directory, submission
from arena.experiment import initial_state, run, run_session, status
from arena.preparation_reuse import slots, stage
from arena_web.data import Store


@unittest.skipUnless((ROOT / '.arena/engine.json').is_file(), 'Build engine')
class PreparationReuseTests(unittest.TestCase):
    def test_reused_preparations_are_restored_in_their_round_without_transport(self):
        config = read_json(ROOT/'configs/offline-complete.json')
        historical = {
            'id':'saved', 'provider':'openai', 'model':'historical', 'api_key_env':'TEST_REUSE_KEY',
            'pricing':{'currency':'USD', 'date':'2026-10-14', 'input_per_million':'1', 'output_per_million':'1'},
        }
        fresh = {**historical, 'id':'fresh', 'parameters':{'reasoning_effort':'high'}}
        config.update(models=[historical, fresh], spending={'allow_paid_calls':True, 'max_total_usd':'0.1'},
                      reuse_preparations={'source':'original','models':['saved']}, improvement_conditions=['feedback'])
        config['scenario']['max_turns'] = 1
        source_code = ROOT/'examples/strategies/rush'
        info = submission(source_code)
        with scratch_directory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            source, snapshot, target = tmp/'original', tmp/'snapshot', tmp/'rerun'
            states = {}
            for generation in (0, 1):
                for sid, _, _, track in slots(config, generation):
                    copy_submission(source_code, source/'sessions'/sid/'submission', info)
                    state = initial_state(sid, historical, config)
                    state.update(generation=generation, condition=track, status='submitted', submission=info,
                                 calls=3, completed_calls=3, steps=7, input_tokens=100, output_tokens=20,
                                 wall_seconds=15, cost_spent='0.25', token_usage_known=True)
                    if generation:
                        state.update(parent='saved-r0', lineage_root='saved-r0')
                    states[sid] = state
            receipts = {sid:{'responses':3,'input_tokens':100,'output_tokens':20,'cost_adjustment_usd':'0.01'} for sid in states}
            stage(config, source, snapshot, states, receipts, lambda sid: dict(states[sid]))
            calls = []

            def fake_transport(sid, model, prepared, *args):
                self.assertEqual(model, fresh)
                self.assertTrue(sid.startswith('fresh-'))
                calls.append(sid)
                return run_session(sid, {**model,'provider':'mock','profile':'single-shot'}, prepared, *args)

            with mock.patch('arena.experiment.run_session', side_effect=fake_transport):
                result = run(config, target, reuse_snapshot=snapshot)
                self.assertFalse(result['incomplete'])
                self.assertEqual(set(calls), {'fresh-r0','fresh-r0-g1-feedback'})
                self.assertGreater(result['tournament']['completed'], 0)
                self.assertGreater(result['evolution']['contemporaries']['completed'], 0)
                resumed = run(config, target, resume=True)
                self.assertFalse(resumed['incomplete'])
            restored = status(target)['sessions']
            for sid in states:
                actual = restored[sid]
                self.assertEqual(actual['reused_from'], {'run':'original','session':sid})
                for key in ('submission','calls','completed_calls','steps','input_tokens','output_tokens','wall_seconds','cost_spent'):
                    self.assertEqual(actual[key], states[sid][key])
            store = Store(tmp, tmp/'settings')
            self.assertEqual(store.usage_receipts(target)['saved-r0'], receipts['saved-r0'])
