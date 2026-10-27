"""Explicit analyst replacements; target changes start a separate calibration."""
import copy
from pathlib import Path
from .core import read_json,digest


def study_root(directory):
    directory=Path(directory).resolve()
    return next((path for path in (directory,*directory.parents) if (path/'study.json').is_file()),None)


def effective_analyst(config, directory, apply_input_policy=True):
    root=study_root(directory)
    path=root/'role-models.json' if root else None
    saved=read_json(path) if path and path.exists() else {}
    model=copy.deepcopy(saved.get('analyst',config.get('analyst')))
    policy=root/'analyst-runtime.json' if root else None
    if model and apply_input_policy and policy and policy.exists():
        settings=read_json(policy)
        if settings.get('analyst_sha256')==digest(model):
            limit=settings['max_input_tokens_per_call']
            if limit is None:model.pop('max_input_tokens_per_call',None)
            else:model['max_input_tokens_per_call']=limit
    return model


def portable_analyst_history(history, model):
    """Replay visible analyst answers without foreign provider-native signatures."""
    from arena_web.provider_output import blocks
    result=[]
    for message in history:
        if message['role'] in {'system','user'}:
            result.append(message)
        elif message['role']=='assistant':
            pieces=[]
            for block in blocks(message):
                if block['kind']=='text':
                    value=block['value'];pieces.append(value if isinstance(value,str) else value.get('text','') if isinstance(value,dict) else '')
            text='\n'.join(pieces).strip()
            if not text:continue
            if model['provider']=='gemini':native={'role':'model','parts':[{'text':text}]}
            elif model['provider']=='anthropic':native={'role':'assistant','content':[{'type':'text','text':text}]}
            else:native={'role':'assistant','content':text}
            result.append({'role':'assistant','content':text,'native':native,'tool_calls':[]})
        elif message['role']=='tool':
            # Analysts have no executable tools. Preserve unexpected results as evidence.
            import json
            result.append({'role':'user','content':'Archived tool result: '+message.get('name','')+'\n'+json.dumps(message.get('result'),ensure_ascii=False)})
    return result
