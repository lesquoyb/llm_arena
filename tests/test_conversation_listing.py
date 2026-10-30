"""The transcript listing must not wait for all competition fight artifacts."""
import unittest
from contextlib import closing
from unittest import mock
from arena.core import ROOT,read_json,scratch_directory,write_json
from arena.experiment import Journal,initial_state
from arena_web.data import Store


class ConversationListingTests(unittest.TestCase):
    def test_tail_is_one_page_and_skips_optional_fight_diagnostics(self):
        with scratch_directory() as root:
            store=Store(root/'runs',root/'settings');out=store.runs/'run';out.mkdir()
            config=read_json(ROOT/'configs/offline-complete.json')
            write_json(out/'experiment.json',{'config':config})
            journal=Journal(out)
            with closing(journal.db):
                state=initial_state('fixture-r0',config['models'][0],config)
                state['history'] += [{'role':'user','content':str(index)} for index in range(90)]
                journal.save('fixture-r0',state,'fixture')
                with mock.patch.object(store,'session_diagnostics',side_effect=AssertionError('full fight scan')):
                    page=store.conversation('run','fixture-r0',tail=True,include_diagnostics=False)
                self.assertEqual(len(page['messages']),25)
                self.assertEqual(page['offset'],page['total']-25)
                self.assertIsNone(page['diagnostics'])
                # Callers cannot mutate a cached checkpoint, and saves invalidate it.
                preview=store.session('run','fixture-r0');preview['history'].clear()
                self.assertEqual(len(store.session('run','fixture-r0')['history']),91)
                state['history'].append({'role':'user','content':'new'})
                journal.save('fixture-r0',state,'changed')
                self.assertEqual(len(store.session('run','fixture-r0')['history']),92)

    def test_nested_activity_restores_the_coordinator_phase(self):
        from arena.activity import operation
        with scratch_directory() as root:
            with operation(root,'checking_fights'):
                with operation(root,'tournament_fight'):
                    self.assertEqual(read_json(root/'activity.json')['kind'],'tournament_fight')
                self.assertEqual(read_json(root/'activity.json')['kind'],'checking_fights')
            self.assertEqual(read_json(root/'activity.json')['kind'],'idle')
