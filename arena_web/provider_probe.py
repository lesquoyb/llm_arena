"""One explicitly requested, accounted API diagnostic; never execute returned tools."""
import copy
import os
import time
from contextlib import closing
from arena.core import ArenaError
from arena.experiment import Journal, experiment_lock
from arena.api_providers import APIProvider, ProviderFailure, connection, http_json
from arena.openai_responses import uses_responses
from arena.reasoning import apply_overrides
from arena.recovery import needs_reconciliation
from arena.feedback import available_tools
from arena.usage import amount, reservation, normalize, cost, effective_pricing


def probe(jobs, run_id, sid, mode, confirm_paid):
    if confirm_paid is not True: raise ArenaError('Authorize this billed diagnostic request')
    if mode not in {'minimal','current'}: raise ArenaError('Choose minimal or current request')
    with jobs.lock:
        if jobs.process and jobs.process.poll() is None: raise ArenaError('Stop the competition before testing its provider')
        root = jobs.store.run_path(run_id)
        if (root/'export.json').exists(): raise ArenaError('Exported archives are read-only')
        metadata = jobs.store.json(root/'experiment.json')
        from arena.roster import effective
        config = effective(root,metadata['config'])
        if not config['spending'].get('allow_paid_calls'):
            raise ArenaError('API calls are not enabled for this competition')
        with experiment_lock(root):
            journal = Journal(root)
            with closing(journal.db):
                journal.verify()
                original = journal.state(sid)
                if not original: raise ArenaError('Conversation not found')
                if original.get('submission') or needs_reconciliation(original) or original.get('pending') or original.get('status') != 'provider_unavailable':
                    raise ArenaError('Choose a failed provider request with no pending response or billing')
                model = apply_overrides(next(m for m in config['models'] if m['id']==original['model']),original)
                if not uses_responses(model): raise ArenaError('This diagnostic currently supports the Responses protocol')
                key = jobs.store.secrets.get(model['api_key_env']) or os.environ.get(model['api_key_env'])
                from arena.endpoints import optional_local_key
                if not key and not optional_local_key(model): raise ArenaError('Configure the participant API key first')
                tools = ([{'name':'arena_probe','description':'Return the diagnostic value.',
                           'input_schema':{'type':'object','properties':{'value':{'type':'string'}},'required':['value'],'additionalProperties':False}}]
                         if mode=='minimal' else available_tools(original))
                history = ([{'role':'user','content':'Call arena_probe once with value "ok". Do not perform any other task.'}]
                           if mode=='minimal' else original['history'])
                cap = min(1024, model.get('max_output_tokens') or 1024)
                budget = config['budget_per_session']
                for counter, limit in [('calls','max_calls'),('input_tokens','max_input_tokens'),('output_tokens','max_output_tokens')]:
                    if limit in budget and original.get(counter,0)>=budget[limit]: raise ArenaError('Diagnostic would exceed '+limit)
                bound = reservation(model,history,tools,cap)
                if bound['cost_bound'] is None: raise ArenaError('Cannot reserve the diagnostic request cost')
                reserve = amount(bound['cost_bound'])
                spent = amount(original.get('cost_spent','0'))
                total = sum(amount(s.get('cost_spent','0'))+amount(s.get('money_reserved','0')) for s in journal.states().values())
                if ('max_cost_usd' in budget and spent+reserve>amount(budget['max_cost_usd']) or
                    'max_total_usd' in config['spending'] and total+reserve>amount(config['spending']['max_total_usd'])):
                    raise ArenaError('Diagnostic would exceed the configured spending limit')
                if 'max_input_tokens' in budget and original.get('input_tokens',0)+bound['input_bound']>budget['max_input_tokens']:
                    raise ArenaError('Diagnostic would exceed max_input_tokens')
                if 'max_output_tokens' in budget and original.get('output_tokens',0)+cap>budget['max_output_tokens']:
                    raise ArenaError('Diagnostic would exceed max_output_tokens')
                body = APIProvider(model).payload(history,tools,cap)
                if mode=='minimal': body.pop('include',None)
                url,headers = connection(model,key)
                state = copy.deepcopy(original)
                state.update(in_flight=True,money_reserved=str(reserve),reservation_unbounded=False)
                state['calls'] = state.get('calls',0)+1
                state['diagnostic_calls'] = state.get('diagnostic_calls',0)+1
                journal.save(sid,state,'provider_probe_intent',{'mode':mode,'endpoint':url,'request':body,
                    'output_cap':cap,'reserved_usd':str(reserve),'tools_will_not_execute':True})
                started = time.monotonic()
                try:
                    raw,request_id = http_json(url,body,headers,model.get('timeout_seconds',60))
                    usage = normalize('openai-responses',raw.get('usage'))
                    charge = cost(usage,effective_pricing(model))
                    received = isinstance(raw.get('output'),list) and not raw.get('error') and raw.get('status') not in {'failed','cancelled'}
                    result = {'mode':mode,'accepted':received,'endpoint':url,'request_id':request_id or raw.get('id'),
                        'status':raw.get('status'),'usage':usage,'cost_usd':charge,'tool_count':len(tools),
                        'reasoning':body.get('reasoning'),'include':body.get('include'),
                        'note':'No returned tools were executed; the saved conversation history and files are unchanged.'}
                    if raw.get('error'):
                        detail=str(raw['error'])[:2000]
                        result['provider_error']=detail.replace(key,'[REDACTED]') if key else detail
                    tokens_known = all(usage.get(field) is not None for field in ('input_tokens','output_tokens'))
                    if tokens_known:
                        for field in ('input_tokens','output_tokens'):
                            state[field] = state.get(field,0) + usage[field]
                    else:
                        state['missing_usage_calls'] = state.get('missing_usage_calls',0) + 1
                    state['token_usage_known'] = tokens_known and not state.get('missing_usage_calls') and bool(original.get('token_usage_known') or not any(m.get('role')=='assistant' for m in original.get('history',[])))
                    if charge is None:
                        state.update(in_flight=False,status='needs_reconciliation')
                    else:
                        state.update(in_flight=False,money_reserved='0',cost_spent=str(spent+amount(charge)))
                        state['diagnostic_cost_usd']=str(amount(state.get('diagnostic_cost_usd','0'))+amount(charge))
                except ProviderFailure as error:
                    result = {'mode':mode,'accepted':False,'error':str(error),'diagnostics':error.diagnostics,
                              'uncertain':error.uncertain,'endpoint':url,'tool_count':len(tools),'reasoning':body.get('reasoning')}
                    if error.uncertain:state.update(status='needs_reconciliation')
                    else:state.update(in_flight=False,money_reserved='0')
                result['elapsed_seconds']=time.monotonic()-started
                journal.save(sid,state,'provider_probe_result',result)
                return result
