"""OpenAI SSE transport with lossless final receipts and bounded live previews."""
import json
import time
from urllib import request, error
from .core import write_json
from .endpoints import validate_endpoint


class LiveResponse:
    def __init__(self, out, sid, call):
        self.path=out/'sessions'/sid/'live-response.json'
        self.call=call;self.updated=0;self.progress_at=None;self.signature=None
        self.publish({'phase':'waiting','text':'','reasoning':'','tools':[]},force=True)

    def publish(self, value, force=False):
        now=time.monotonic()
        if not force and now-self.updated < .4: return
        self.updated=now
        signature=(value.get('text',''),value.get('reasoning',''),json.dumps(value.get('tools',[]),sort_keys=True),value.get('output_characters'))
        if signature!=self.signature and (value.get('text') or value.get('reasoning') or value.get('tools')):
            self.progress_at=time.time()
        self.signature=signature
        meta={'call':self.call,'updated_at':time.time(),'progress_at':self.progress_at,'phase':value.get('phase')}
        write_json(self.path,{**meta,**value})
        write_json(self.path.with_name('live-progress.json'),meta)


def stream_json(url, payload, headers, timeout, progress, *, inactivity_timeout=None):
    from .api_providers import ProviderFailure, open_provider_response
    validate_endpoint(url,allow_query=True)
    req=request.Request(url,data=json.dumps(payload).encode(),headers={**headers,'Accept':'text/event-stream'},method='POST')
    idle=inactivity_timeout or timeout
    started=time.monotonic()
    try:
        response=open_provider_response(req,min(timeout,idle))
    except error.HTTPError as exc:
        from .api_providers import raise_http_error
        raise_http_error(exc,url,headers,read_timeout=idle)
    text='';reasoning='';tools={};usage=None;finish=None;metadata={};final=None;total=0;events=[]
    def update(force=False,phase='streaming'):
        progress.publish({'phase':phase,'output_characters':len(text)+len(reasoning)+sum(len(v.get('function',{}).get('arguments','')) for v in tools.values()),'text':text[-200000:],'reasoning':reasoning[-200000:],
                          'preview_truncated':len(text)>200000 or len(reasoning)>200000,
                          'tools':[{'name':v.get('function',{}).get('name',''),'arguments':v.get('function',{}).get('arguments','')[-4000:]} for v in tools.values()]},force=force)
    try:
        from .provider_watchdog import InactivityGuard
        with response, InactivityGuard(response,idle,started_at=started) as guard:
            if 'text/event-stream' not in response.headers.get('Content-Type','').lower():
                data=response.read(8_000_001)
                if len(data)>8_000_000: raise ValueError('Provider response exceeded quota')
                result=json.loads(data)
                progress.publish({'phase':'completed','text':'','reasoning':'','tools':[]},force=True)
                return result,response.headers.get('x-request-id')
            for raw_line in response:
                guard.check()
                total+=len(raw_line)
                if total>8_000_000: raise ValueError('Provider stream exceeded quota')
                line=raw_line.decode('utf-8').strip()
                if not line.startswith('data:'): continue
                data=line[5:].strip()
                if data=='[DONE]':break
                if not data:continue
                event=json.loads(data);events.append(event)
                kind=event.get('type','')
                if (kind.endswith('.delta') and event.get('delta')) or kind in {'response.completed','response.incomplete'} or (event.get('usage') is not None and event['usage']!=usage):
                    guard.touch()
                if kind in {'response.completed','response.incomplete'}:
                    final=dict(event['response'])
                    break
                elif kind in {'error','response.failed'}:
                    raise ValueError('Provider stream failed: '+str(event.get('error') or event.get('response',{}).get('error') or event))
                elif kind=='response.output_text.delta': text+=event.get('delta','')
                elif kind in {'response.reasoning_summary_text.delta','response.reasoning_text.delta'}: reasoning+=event.get('delta','')
                elif kind=='response.output_item.added' and event.get('item',{}).get('type')=='function_call':
                    guard.touch()
                    item=event['item'];tools[event.get('output_index',0)]={'id':item.get('call_id'),'type':'function','function':{'name':item.get('name',''),'arguments':item.get('arguments','')}}
                elif kind=='response.function_call_arguments.delta':
                    tool=tools.setdefault(event.get('output_index',0),{'type':'function','function':{'name':'','arguments':''}})
                    tool['function']['arguments']+=event.get('delta','')
                if event.get('usage') is not None: usage=event['usage']
                for choice in event.get('choices',[]):
                    if choice.get('index',0)!=0: continue
                    delta=choice.get('delta',{})
                    if any(delta.get(key) for key in ('content','reasoning_content','reasoning','tool_calls')) or choice.get('finish_reason') is not None:guard.touch()
                    text+=delta.get('content') or ''
                    reasoning+=delta.get('reasoning_content') or delta.get('reasoning') or ''
                    for call in delta.get('tool_calls') or []:
                        tool=tools.setdefault(call['index'],{'type':'function','function':{'name':'','arguments':''}})
                        if call.get('id'): tool['id']=call['id']
                        function=call.get('function',{})
                        tool['function']['name']+=function.get('name') or ''
                        tool['function']['arguments']+=function.get('arguments') or ''
                    if choice.get('finish_reason') is not None: finish=choice['finish_reason']
                metadata.update({key:event[key] for key in ('id','model','created','system_fingerprint') if key in event})
                update()
            if final is None:
                if finish is None: raise ValueError('Provider stream ended without a completion receipt')
                message={'role':'assistant','content':text or None}
                if reasoning: message['reasoning_content']=reasoning
                if tools: message['tool_calls']=[tools[key] for key in sorted(tools)]
                final={**metadata,'choices':[{'index':0,'message':message,'finish_reason':finish}],'usage':usage}
            final['stream_events']=events
            update(True,'completed')
            return final,response.headers.get('x-request-id')
    except ProviderFailure:
        update(True,'interrupted')
        raise
    except (OSError,TimeoutError,ValueError,KeyError,TypeError) as exc:
        update(True,'interrupted')
        raise ProviderFailure(f'Provider stream interrupted ({type(exc).__name__}): {str(exc)[:500]}',uncertain=True) from None
