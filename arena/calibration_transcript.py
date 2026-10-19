"""Portable transcript snapshots and local, retrospective reasoning assessment."""
import json
from pathlib import Path

from .core import ArenaError, read_json


def export(state):
    from arena_web.provider_output import blocks
    messages, reasoning = [], []
    times = state.get('message_times', [])
    for index, message in enumerate(state.get('history', [])):
        # Transport receipts duplicate the complete request context; they are not turns.
        messages.append({k:v for k,v in message.items() if k not in {'raw','sent_parameters','response_artifact'}} |
                        {'index':index, 'recorded_at':times[index] if index < len(times) else None})
        if message.get('role') == 'assistant':
            values = [b['value'] for b in blocks(message) if b['kind']=='reasoning' and b['readable']]
            if values: reasoning.append({'message_index':index, 'reasoning':values})
    serialized = json.dumps(reasoning, ensure_ascii=False)
    return {'schema_version':1, 'session':state.get('id'), 'status':state.get('status'),
            'messages':messages, 'readable_reasoning':reasoning,
            'statistics':{'messages':len(messages), 'assistant_messages':sum(m.get('role')=='assistant' for m in messages),
                          'reasoning_messages':len(reasoning), 'serialized_reasoning_characters':len(serialized) if reasoning else 0,
                          'reasoning_tokens':None,
                          'note':'Character count is not a token count. Actual Laya input tokens and windows are measured by score-conversation. Encrypted reasoning is not readable. This is a snapshot; streaming output not yet committed is excluded.'}}


def score(source, out, model='convaiinnovations/laya', device='cpu'):
    from .calibration_judge import defaults, evaluate
    value=read_json(Path(source))
    messages=value.get('messages') if isinstance(value,dict) else None
    if not isinstance(messages,list) or not all(isinstance(m,dict) and m.get('role') in {'system','user','assistant','tool'} for m in messages):
        raise ArenaError('Expected an exported conversation JSON with a messages array')
    settings={**defaults(),'mode':'conversation','model':model,'device':device}
    out=Path(out).resolve()
    out.mkdir(parents=True,exist_ok=True)
    receipt=evaluate(out,'conversation',{'history':messages},settings,{'evaluation':settings})
    return {'status':'completed','score':receipt['score'],'reasoning_messages':len(receipt['exchanges']),
            'input_tokens':sum((r.get('usage') or {}).get('input_tokens',0) for r in receipt['exchanges']),
            'windows':sum((r.get('usage') or {}).get('windows',0) for r in receipt['exchanges']),
            'seconds':receipt['seconds'],'model':receipt['model'],'revision':receipt['revision'],
            'receipt':str(out/'judge/conversation.json'),
            'note':'Local reasoning-quality proxy. No target calls, analyst calls, fights or changes to the original calibration.'}
