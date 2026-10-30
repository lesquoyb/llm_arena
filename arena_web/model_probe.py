"""Small explicitly requested model probes, separate from competition budgets."""
import copy
import os
import time
from uuid import uuid4
from arena.core import ArenaError,write_json
from arena.api_providers import APIProvider,ProviderFailure,connection


def probe_model(store,model,mode='text',secret=None):
    if mode not in {'text','tools'}: raise ArenaError('Choose text or tools')
    store.validate_model(model)
    if model['provider']=='mock': raise ArenaError('Built-in strategies have no provider API to test')
    if secret is not None and (not isinstance(secret,str) or len(secret)>8192): raise ArenaError('Invalid API key')
    key=secret or store.secrets.get(model['api_key_env']) or os.environ.get(model['api_key_env'])
    spec=copy.deepcopy(model);spec.pop('_stream',None);spec['max_retries']=0
    cap=min(spec.get('max_output_tokens') or 128,128) if mode=='tools' else min(spec.get('max_output_tokens') or 16,16)
    omitted=list(spec.get('parameters',{})) if mode=='text' else []
    if mode=='text': spec['parameters']={}
    tools=[{'name':'arena_probe','description':'Confirm the diagnostic value.','input_schema':{'type':'object','properties':{'value':{'type':'string'}},'required':['value'],'additionalProperties':False}}] if mode=='tools' else []
    history=[{'role':'user','content':'Call arena_probe once with value "ok". Do nothing else.' if tools else 'Reply OK.'}]
    endpoint=connection(spec,key)[0]
    result={'id':uuid4().hex,'at':time.time(),'participant':model['id'],'provider':model['provider'],'model':model.get('model'),
            'endpoint':endpoint,'mode':mode,'output_cap':cap,'automatic_retries':0,'omitted_parameters':omitted,'pricing':model.get('pricing'),
            'note':'Connection mode omits optional generation parameters; tools mode keeps them. A small diagnostic request, outside competition/calibration budgets. Returned tools are never executed. A small output cap can yield no visible text on reasoning models.'}
    started=time.monotonic()
    try:
        response=APIProvider(spec).respond(history,tools,cap,key_override=key)
        result.update(accepted=True,request_id=response.get('request_id'),usage=response.get('usage'),cost_usd=response.get('cost_usd'),
                      finish_reason=response.get('finish_reason',response.get('stop_reason')),tool_call_returned=any(call.get('name')=='arena_probe' for call in response.get('tool_calls',[])),
                      tool_names=[call['name'] for call in response.get('tool_calls',[])],
                      tool_arguments_valid=any(call.get('name')=='arena_probe' and isinstance(call.get('arguments'),dict) and isinstance(call['arguments'].get('value'),str) for call in response.get('tool_calls',[])))
    except ProviderFailure as exc:
        result.update(accepted=False,error=str(exc),uncertain=exc.uncertain,retryable=exc.retryable,diagnostics=exc.diagnostics,cost_usd=None)
    except (ArenaError,ValueError,KeyError,TypeError) as exc:
        # An unreadable receipt may still have been charged; never invent zero usage.
        result.update(accepted=False,error='Unreadable probe response: '+type(exc).__name__,uncertain=True,cost_usd=None)
    result['seconds']=time.monotonic()-started
    write_json(store.state/'model-probes'/(result['id']+'.json'),result)
    return result
