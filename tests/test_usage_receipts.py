"""Receipt accounting must include cached input without adding it twice."""
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from arena.experiment import Journal
from arena.usage import normalize, cost
from arena_web.accounting import summarize, token_budget_stop
from arena_web.data import Store


class UsageReceiptTests(unittest.TestCase):
    def test_competition_repricing_snapshots_catalog_rates_and_preserves_recorded_charges(self):
        from arena.core import read_json, write_json
        from arena_web.accounting import REPORT_PRICING
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            store = Store(base/'runs', base/'ui')
            root = store.runs/'run'
            pricing = {'currency':'USD','date':'2026-01-01','input_per_million':'2','output_per_million':'4'}
            model = {'id':'m','provider':'openai','model':'fixture','pricing':pricing}
            changed = {**pricing, 'input_per_million':'3','output_per_million':'6','cached_input_per_million':'1'}
            competitor = {**model,'id':'different','model':'frozen-model'}
            config = {'config':{'models':[model,competitor],'budget_per_session':{}}}
            write_json(root/'experiment.json', config)
            write_json(root/'report.json', {'cost_usd':'3.8'})
            write_json(store.state/'participants.json', [
                {**model,'pricing':changed},
                {**competitor,'model':'new-model','pricing':changed},
            ])
            journal = Journal(root)
            with closing(journal.db):
                state = {'model':'m','status':'submitted','history':[],'cost_spent':'3.8'}
                for cached, original in ((500_000,'2.2'), (None,'1.2'), (0,None)):
                    journal.save('m-r0', state, 'model_response', {
                        'usage':{'input_tokens':1_000_000,'output_tokens':50_000,
                                 'cached_input_tokens':cached,'cache_creation_input_tokens':0},
                        'cost_usd':original,
                    })
            self.assertFalse(store.report_pricing('run')['candidates'][1]['changed'])
            store.report_pricing('run', 'apply')
            self.assertEqual(read_json(root/REPORT_PRICING)['models'], {'m':changed})
            write_json(store.state/'participants.json', [{**model,'pricing':pricing}])
            detail = store.detail('run')['sessions'][0]
            self.assertEqual(detail['recorded_cost_spent'], '3.8')
            self.assertEqual(detail['cost_spent'], '3.9')
            receipts = detail['usage_receipts']
            self.assertEqual((receipts['repriced_responses'], receipts['unrepriced_responses']), (1, 2))
            self.assertEqual(store.listing()[0]['report']['cost_usd'], '3.9')
            self.assertEqual(read_json(root/'experiment.json'), config)
            self.assertEqual(read_json(root/'report.json')['cost_usd'], '3.8')
            store.report_pricing('run', 'reset')
            self.assertEqual(store.detail('run')['sessions'][0]['cost_spent'], '3.8')

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
                                     'cached_input_tokens': 90}, 'cost_usd': '0.01', 'stop_reason': 'max_tokens'}
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
                    self.assertEqual(usage['initial']['output_cutoffs'], 1)
                    self.assertEqual(usage['initial']['output_reasons_known'], 1)
                    self.assertEqual(usage['next']['input_tokens'], 100)
                    self.assertEqual(usage['next']['output_cutoffs'], 0)
            finally:
                journal.db.close()

    def test_token_stop_counts_only_terminal_attributed_stops(self):
        stop = {'code': 'input_tokens', 'token_limits': ['input_tokens', 'output_tokens']}
        self.assertEqual(token_budget_stop({'status': 'no_submission', 'budget_stop': stop}),
                         ['input_tokens', 'output_tokens'])
        self.assertEqual(token_budget_stop({'status': 'running', 'budget_stop': stop}), [])
        self.assertEqual(token_budget_stop({'status': 'budget_exhausted'}), [])
        self.assertEqual(token_budget_stop({'status': 'budget_exhausted', 'budget_stop': {
            'message': 'Preparation output_tokens limit reached (100 / 100).'}}), ['output_tokens'])
        total = summarize([{'preparation_response': True, 'finish_reason': 'MAX_TOKENS'},
                           {'preparation_response': True, 'stop_reason': 'end_turn'},
                           {'preparation_response': True}])
        self.assertEqual((total['output_cutoffs'], total['output_reasons_known'], total['preparation_responses']),
                         (1, 2, 3))

    def test_missing_usage_does_not_erase_other_receipts(self):
        total = summarize([{'usage': {'input_tokens': 100, 'output_tokens':10}},
                           {'usage': {'input_tokens': None, 'output_tokens':None}}])
        self.assertEqual(total['input_tokens'], 100)
        self.assertEqual(total['missing_usage'], 1)
        self.assertEqual(total['missing_cache_usage'], 2)

    def test_responses_cache_writes_explain_dashboard_cost(self):
        from arena.usage import effective_pricing
        usage = normalize('openai-responses', {
            'input_tokens':1605780, 'output_tokens':19959,
            'input_tokens_details':{'cached_tokens':1478144, 'cache_write_tokens':127393}})
        model = {'provider':'openai', 'model':'gpt-6.1-sol', 'pricing':{
            'input_per_million':'2','cached_input_per_million':'0.1','output_per_million':'10'}}
        self.assertEqual(usage['cache_creation_input_tokens'],127393)
        self.assertEqual(cost(usage,effective_pricing(model)),'0.6663729')
        self.assertNotIn('cache_creation_per_million',model['pricing'])
        model['pricing']['cache_creation_per_million']='3'
        self.assertEqual(effective_pricing(model)['cache_creation_per_million'],'3')

    def test_cache_write_detail_must_be_nonnegative_integer(self):
        for value in (-1, True, '12'):
            with self.assertRaisesRegex(Exception,'Invalid provider token detail'):
                normalize('openai-responses',{'input_tokens':100,'output_tokens':1,
                    'input_tokens_details':{'cache_write_tokens':value}})

    def test_old_raw_receipts_are_repriced_without_changing_archives(self):
        from arena.core import write_json
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/'run'
            root.mkdir()
            write_json(root/'experiment.json', {'config':{'models':[{
                'id':'third','provider':'openai','model':'gpt-6.1-sol',
                'pricing':{'input_per_million':'2','cached_input_per_million':'0.1','output_per_million':'10'}}]}})
            usage=normalize('openai-responses',{'input_tokens':1605780,'output_tokens':19959,
                'input_tokens_details':{'cached_tokens':1478144,'cache_write_tokens':127393}})
            usage['cache_creation_input_tokens']=None
            journal=Journal(root)
            try:
                journal.save('third-r0',{'model':'third','history':[]},'model_response',
                    {'usage':usage,'cost_usd':'0.6026764'})
            finally:
                journal.db.close()
            before={path:path.read_bytes() for path in root.rglob('*') if path.is_file()}
            store=Store(root.parent,Path(directory)/'ui')
            for _ in range(2):
                receipt=store.usage_receipts(root)['third-r0']
                self.assertEqual(receipt['cache_creation_input_tokens'],127393)
                self.assertEqual(receipt['cost_adjustment_usd'],'0.0636965')
                self.assertEqual(receipt['reported_cost_usd'],'0.6026764')
            self.assertTrue(all(path.read_bytes()==value for path,value in before.items()))

    def test_missing_reasoning_is_not_mistaken_for_a_reported_value(self):
        result=summarize([{'usage':{'input_tokens':100,'output_tokens':10}}])
        self.assertEqual(result['missing_reasoning_usage'],1)

    def test_metadata_cache_eviction_does_not_discard_usage_receipts(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            journal=Journal(root)
            try:
                journal.save('one',{'history':[]},'model_response',{
                    'usage':{'input_tokens':100,'output_tokens':10},'cost_usd':'0'})
            finally:
                journal.db.close()
            store=Store(root/'runs',root/'ui')
            first=store.usage_receipts(root)
            store._cache.clear()
            from unittest import mock
            with mock.patch.object(Path,'read_bytes',side_effect=AssertionError('Do not reread transport artifacts')):
                self.assertEqual(store.usage_receipts(root),first)
