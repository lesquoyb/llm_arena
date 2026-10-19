"""OpenAI SSE transport with lossless final receipts and bounded live previews."""
import json
import time
from urllib import request, error
from .core import write_json
from .endpoints import validate_endpoint


class LiveResponse:
    def __init__(self, out, sid, call):
        self.path=out/'sessions'/sid/'live-response.json'
        self.call=call;self.updated=0
        self.publish({'phase':'waiting','text':'','reasoning':'','tools':[]},force=True)

    def publish(self, value, force=False):
        now=time.monotonic()
        if not force and now-self.updated < .4: return
        self.updated=now
        write_json(self.path,{'call':self.call,'updated_at':time.time(),**value})


def stream_json(url, payload, headers, timeout, progress):
    from .api_providers import ProviderFailure, LocalRedirectHandler
    validate_endpoint(url,allow_query=True)
    req=request.Request(url,data=json.dumps(payload).encode(),headers={**headers,'Accept':'text/event-stream'},method='POST')
    from urllib.parse import urlsplit
    open_url=request.build_opener(LocalRedirectHandler()).open if urlsplit(url).scheme=='http' else request.urlopen
    try:
        response=open_url(req,timeout=timeout)
    except error.HTTPError as exc:
        from .api_providers import raise_http_error
        raise_http_error(exc,url,headers)
    except (error.URLError,OSError,TimeoutError) as exc:
        raise ProviderFailure(f'Provider response unavailable ({type(exc).__name__})',uncertain=True) from None
    text='';reasoning='';tools={};usage=None;finish=None;metadata={};final=None;total=0;events=[]
    def update(force=False,phase='streaming'):
        progress.publish({'phase':phase,'text':text[-200000:],'reasoning':reasoning[-200000:],
                          'preview_truncated':len(text)>200000 or len(reasoning)>200000,
                          'tools':[{'name':v.get('function',{}).get('name',''),'arguments':v.get('function',{}).get('arguments','')[-4000:]} for v in tools.values()]},force=force)
    try:
        with response:
            if 'text/event-stream' not in response.headers.get('Content-Type','').lower():
                data=response.read(8_000_001)
                if len(data)>8_000_000: raise ValueError('Provider response exceeded quota')
                result=json.loads(data)
                progress.publish({'phase':'completed','text':'','reasoning':'','tools':[]},force=True)
                return result,response.headers.get('x-request-id')
            for raw_line in response:
                total+=len(raw_line)
                if total>8_000_000: raise ValueError('Provider stream exceeded quota')
                line=raw_line.decode('utf-8').strip()
                if not line.startswith('data:'): continue
                data=line[5:].strip()
                if not data or data=='[DONE]': continue
                event=json.loads(data);events.append(event)
                kind=event.get('type','')
                if kind in {'response.completed','response.incomplete'}:
                    final=dict(event['response'])
                elif kind in {'error','response.failed'}:
                    raise ValueError('Provider stream failed: '+str(event.get('error') or event.get('response',{}).get('error') or event))
                elif kind=='response.output_text.delta': text+=event.get('delta','')
                elif kind in {'response.reasoning_summary_text.delta','response.reasoning_text.delta'}: reasoning+=event.get('delta','')
                elif kind=='response.output_item.added' and event.get('item',{}).get('type')=='function_call':
                    item=event['item'];tools[event.get('output_index',0)]={'id':item.get('call_id'),'type':'function','function':{'name':item.get('name',''),'arguments':item.get('arguments','')}}
                elif kind=='response.function_call_arguments.delta':
                    tool=tools.setdefault(event.get('output_index',0),{'type':'function','function':{'name':'','arguments':''}})
                    tool['function']['arguments']+=event.get('delta','')
                if event.get('usage') is not None: usage=event['usage']
                for choice in event.get('choices',[]):
                    if choice.get('index',0)!=0: continue
                    delta=choice.get('delta',{})
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
    except (OSError,TimeoutError,ValueError,KeyError,TypeError) as exc:
        update(True,'interrupted')
        raise ProviderFailure(f'Provider stream interrupted ({type(exc).__name__}): {str(exc)[:500]}',uncertain=True) from None
