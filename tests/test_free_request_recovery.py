"""Zero configured prices must not turn unknown tokens into a billing block."""
import unittest
from contextlib import closing
from arena.core import scratch_directory
from arena.experiment import Journal
from arena.recovery import recover_zero_cost_requests,zero_cost_requests
from arena.session_metadata import project
from arena_web.data import Store


class FreeRequestRecoveryTests(unittest.TestCase):
    def test_only_explicit_zero_prices_can_skip_financial_review(self):
        model={'id':'free','provider':'openai-compatible','pricing':{'input_per_million':0,'output_per_million':0}}
        self.assertTrue(zero_cost_requests(model))
        self.assertFalse(zero_cost_requests({'id':'unknown','provider':'openai-compatible'}))
        self.assertFalse(zero_cost_requests({**model,'pricing':{**model['pricing'],'cached_input_per_million':1}}))
        with scratch_directory() as root:
            journal=Journal(root)
            with closing(journal.db):
                for name in ('free','paid'):
                    journal.save(name+'-r0',{'model':name,'status':'needs_reconciliation','in_flight':True,'calls':2,'money_reserved':'0','cost_spent':'0','history':[]},'interrupted')
                recover_zero_cost_requests(journal,[model,{'id':'paid','pricing':{'input_per_million':1,'output_per_million':1}}])
                recovered=journal.state('free-r0')
                self.assertEqual(recovered['status'],'provider_unavailable')
                self.assertEqual(recovered['calls'],2)
                self.assertFalse(recovered['token_usage_known'])
                self.assertEqual(recovered['cost_spent'],'0')
                self.assertEqual(journal.state('paid-r0')['status'],'needs_reconciliation')
                count=journal.db.execute("SELECT count(*) FROM events WHERE kind='billing_reconciled'").fetchone()[0]
                recover_zero_cost_requests(journal,[model])
                self.assertEqual(journal.db.execute("SELECT count(*) FROM events WHERE kind='billing_reconciled'").fetchone()[0],count)
                journal.verify()

    def test_replay_calls_are_counted_from_executed_history_in_old_and_new_journals(self):
        state={'model':'fixture','status':'submitted','history':[
            {'role':'assistant','tool_calls':[{'name':'read_replay'}]},
            {'role':'tool','name':'read_replay','result':{}},
            {'role':'tool','name':'read_past_fight','result':{'error':'not found'}},
            {'role':'tool','name':'write_file','result':{}},
        ]}
        self.assertEqual(project(state)['replay_reads'],2)
        with scratch_directory() as root:
            journal=Journal(root)
            with closing(journal.db):
                journal.save('fixture-r0',state,'fixture')
                store=Store(root/'runs',root/'settings')
                self.assertEqual(store.states(root,('replay_reads',))['fixture-r0']['replay_reads'],2)
                journal.db.execute('DELETE FROM session_metadata');journal.db.commit()
                self.assertEqual(store.states(root,('replay_reads',))['fixture-r0']['replay_reads'],2)
