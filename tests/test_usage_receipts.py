"""Receipt accounting must include cached input without adding it twice."""
import tempfile
import unittest
from pathlib import Path

from arena.experiment import Journal
from arena.usage import normalize, cost
from arena_web.accounting import summarize
from arena_web.data import Store


class UsageReceiptTests(unittest.TestCase):
    def test_cached_and_reasoning_are_subsets_of_input_and_output(self):
        usage = normalize('openai-responses', {
            'input_tokens': 700000, 'output_tokens': 26000,
            'input_tokens_details': {'cached_tokens': 623000},
            'output_tokens_details': {'reasoning_tokens': 20000}})
        total = summarize([{'usage': usage, 'cost_usd': '0.31'}])
        self.assertEqual(total['input_tokens'] + total['output_tokens'], 726000)
        self.assertEqual(total['cached_input_tokens'], 623000)
        self.assertEqual(total['reasoning_tokens'], 20000)
        self.assertEqual(total['reported_cost_usd'], '0.31')
        self.assertEqual(cost(usage, {'input_per_million':'1', 'cached_input_per_million':'0.1', 'output_per_million':'2'}), '0.1913')

    def test_received_usage_is_read_once_even_with_usage_event_and_copied_history(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            journal = Journal(root)
            try:
                response = {'usage': {'input_tokens': 100, 'output_tokens': 10,
                                     'cached_input_tokens': 90}, 'cost_usd': '0.01'}
                state = {'history': [response]}
                journal.save('initial', state, 'model_response', response)
                journal.save('initial', state, 'usage_event', response)
                journal.save('next', state, 'branch_created', {})
                journal.save('next', state, 'provider_probe_result', response)
                store = Store(root/'runs', root/'ui')
                for _ in range(2):
                    usage = store.usage_receipts(root)
                    self.assertEqual(usage['initial']['input_tokens'], 100)
                    self.assertEqual(usage['initial']['responses'], 1)
                    self.assertEqual(usage['next']['input_tokens'], 100)
            finally:
                journal.db.close()

    def test_missing_usage_does_not_erase_other_receipts(self):
        total = summarize([{'usage': {'input_tokens': 100, 'output_tokens':10}},
                           {'usage': {'input_tokens': None, 'output_tokens':None}}])
        self.assertEqual(total['input_tokens'], 100)
        self.assertEqual(total['missing_usage'], 1)
        self.assertEqual(total['missing_cache_usage'], 2)
