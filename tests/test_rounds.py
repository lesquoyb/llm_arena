"""Persistent improvement tracks and configurable calibration stopping rules."""
import contextlib
import io
from unittest import TestCase, mock

from arena.core import ROOT, ArenaError, scratch_directory, read_json, write_json, digest
from arena.experiment import run, Journal, plan, validate_config
from arena.calibration import trial
from arena.feedback import access_for, available_tools
from arena_web.data import Store
from test_calibration import FixtureEngine, config as calibration_config


class RoundEngine(FixtureEngine):
    timeout = 1
    runtime_provenance = {}
    artifact_provenance = {}
    def fight(self, sources, infos, config, seed, out):
        result = super().fight(sources, infos, config, seed, out)
        provenance = read_json(out/'provenance.json')
        provenance['scenario_sha256'] = digest(read_json(out/'scenario.json'))
        write_json(out/'provenance.json', provenance)
        result['team_metrics'] = {str(i):dict(operations=0, errors=0, operation_limit_hits=0) for i in (0,1)}
        write_json(out/'result.json', result)
        return result


def competition(rounds):
    value = read_json(ROOT/'configs/offline-complete.json')
    value.update(generations=rounds, replicates=1, include_mirrors=False)
    value['scenario']['max_turns'] = 1
    for model in value['models']: model['profile'] = 'single-shot'
    return value


class RoundTests(TestCase):
    def test_four_competition_rounds_keep_two_linear_tracks_and_resume_all_matches(self):
        with scratch_directory() as tmp, contextlib.redirect_stdout(io.StringIO()), mock.patch('arena.experiment.Engine', RoundEngine):
            value = competition(4)
            report = run(value, tmp/'run')
            self.assertEqual(report['sessions'], 14)
            self.assertEqual(report['generation'], 3)
            self.assertFalse(report['incomplete'])
            journal = Journal(tmp/'run')
            try:
                states = journal.states()
                for model in value['models']:
                    root = model['id']+'-r0'
                    for generation in range(1,4):
                        for condition in ('control','feedback'):
                            sid = f'{root}-g{generation}-{condition}'
                            state = states[sid]
                            parent = root if generation==1 else f'{root}-g{generation-1}-{condition}'
                            self.assertEqual(state['parent'], parent)
                            self.assertEqual(state['generation'], generation)
                            access = access_for(tmp/'run', state)
                            self.assertEqual(access is not None, condition=='feedback')
                            if access:
                                self.assertEqual(access.root.name, 'tournament' if generation==1 else f'g{generation-1}-tournament')
                                self.assertGreater(access.call('list_past_fights',{})['total'], 0)
                            else:
                                self.assertNotIn('list_past_fights', [t['name'] for t in available_tools(state)])
                self.assertEqual({r['generation'] for r in report['evolution']['rows']}, {0,1,2,3})
            finally: journal.db.close()
            before = {p:(p.read_bytes(),p.stat().st_mtime_ns) for p in (tmp/'run').rglob('outcome.json')}
            resumed = run(value,tmp/'run',resume=True)
            self.assertEqual(resumed['generation'], 3)
            self.assertTrue(all((p.read_bytes(),p.stat().st_mtime_ns)==data for p,data in before.items()))
            store=Store(tmp,tmp/'settings')
            matches=store.matches('run')['matches']
            self.assertTrue({'g1-tournament','g2-tournament','g3-tournament'} <= {m['stage'] for m in matches})
            self.assertEqual(plan(value)['sessions'],14)

    def test_unbounded_competition_has_a_durable_round_boundary_and_resumes(self):
        with scratch_directory() as tmp, contextlib.redirect_stdout(io.StringIO()), mock.patch('arena.experiment.Engine', RoundEngine):
            value=competition(None)
            def stop(kind,sid):
                if kind=='response' and '-g2-' in sid: raise KeyboardInterrupt
            with self.assertRaises(KeyboardInterrupt): run(value,tmp/'run',interrupt=stop)
            saved=read_json(tmp/'run/report.json')
            self.assertEqual(saved['generation'],1)
            self.assertIsNone(plan(value)['sessions'])
            self.assertIsNone(plan(value)['common_reference_matches'])
            def stop_later(kind,sid):
                if kind=='response' and '-g3-' in sid: raise KeyboardInterrupt
            with self.assertRaises(KeyboardInterrupt): run(value,tmp/'run',resume=True,interrupt=stop_later)
            self.assertEqual(read_json(tmp/'run/report.json')['generation'],2)

    def test_calibration_fixed_rounds_ignore_plateau_and_unbounded_can_resume(self):
        with scratch_directory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            value=calibration_config();value.update(max_rounds=5,stop_on_plateau=False)
            report=trial(value,tmp/'fixed',engine=RoundEngine())
            self.assertEqual(len(report['replicates'][0]['rounds']),5)
            value['max_rounds']=1000
            from arena.calibration import validate
            validate(value)
            value['max_rounds']=None
            original = RoundEngine.analyze
            def stop(engine,source,entry,out):
                if 'target-r0-g3' in str(out): raise KeyboardInterrupt
                return original(engine,source,entry,out)
            with mock.patch.object(RoundEngine,'analyze',stop):
                with self.assertRaises(KeyboardInterrupt): trial(value,tmp/'manual',engine=RoundEngine())
            self.assertEqual(len(read_json(tmp/'manual/progress.json')['rounds']),3)
            def stop_later(engine,source,entry,out):
                if 'target-r0-g4' in str(out): raise KeyboardInterrupt
                return original(engine,source,entry,out)
            with mock.patch.object(RoundEngine,'analyze',stop_later):
                with self.assertRaises(KeyboardInterrupt): trial(value,tmp/'manual',resume=True,engine=RoundEngine())
            self.assertEqual(len(read_json(tmp/'manual/progress.json')['rounds']),4)

    def test_retry_in_later_round_keeps_completed_work_and_continues_descendants(self):
        from arena.providers import MockProvider
        from arena.api_providers import ProviderFailure
        original = MockProvider.respond
        failed = False
        def respond(provider, history, tools, output_limit):
            nonlocal failed
            last = next((m for m in reversed(history) if m.get('role')=='user'), {})
            if not failed and last.get('generation') == 2 and last.get('condition') == 'feedback':
                failed = True
                raise ProviderFailure('temporary quota', uncertain=False, retryable=True)
            return original(provider,history,tools,output_limit)
        with scratch_directory() as tmp, contextlib.redirect_stdout(io.StringIO()), mock.patch('arena.experiment.Engine',RoundEngine):
            value=competition(4);value['models']=value['models'][:1]
            with mock.patch.object(MockProvider,'respond',respond):
                report=run(value,tmp/'run')
            self.assertTrue(report['incomplete'])
            journal=Journal(tmp/'run')
            try:
                sid=next(sid for sid,s in journal.states().items() if s['status']=='provider_unavailable')
            finally: journal.db.close()
            before={p:(p.read_bytes(),p.stat().st_mtime_ns) for p in (tmp/'run').rglob('outcome.json')}
            report=run(value,tmp/'run',resume=True,retry_session=sid)
            self.assertFalse(report['incomplete'])
            self.assertEqual(report['generation'],3)
            self.assertEqual(report['sessions'],7)
            self.assertTrue(all((p.read_bytes(),p.stat().st_mtime_ns)==data for p,data in before.items()))

    def test_configuration_accepts_many_rounds_but_rejects_invalid_values(self):
        self.assertEqual(validate_config(competition(1000))['generations'],1000)
        for count in (0,-1,True,1.5):
            with self.assertRaises(ArenaError): validate_config(competition(count))


class NativeRoundTests(TestCase):
    def test_three_rounds_with_real_engine(self):
        if not (ROOT/'.arena/engine.json').exists(): self.skipTest('Build engine')
        with scratch_directory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            value=competition(3);value['models']=value['models'][:1]
            report=run(value,tmp/'run')
            self.assertEqual(report['sessions'],5)
            self.assertEqual(report['generation'],2)
            self.assertFalse(report['incomplete'])
            self.assertTrue((tmp/'run/g2-tournament/report.json').is_file())
