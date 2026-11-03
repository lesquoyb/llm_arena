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
            result.append({key:value for key,value in message.items() if key!='inherited_from_session'})
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


def active_analyst_session(directory, default='analyst-r0'):
    path=Path(directory)/'active-analyst.json'
    return read_json(path)['session'] if path.exists() else default


def replace_active_analyst_sessions(study, config, model):
    """Start the chosen analyst afresh, retaining prior analysis and any receipts."""
    from .core import write_json
    from .experiment import Journal,initial_state
    from .calibration import analyst_experiment_config
    import re
    root=Path(study);manifest=read_json(root/'study.json');folders=[]
    if manifest.get('active_proposal',0)>manifest.get('active_trial',0):
        folder=root/'proposals'/f"{manifest['active_proposal']:03}"
        if not (folder/'proposal.json').exists():folders.append((folder,'analyst-r0'))
    trial=root/'trials'/f"{manifest.get('active_trial',0):03}"
    folders.extend((path.parent,'summary-r0') for path in trial.glob('judge_summaries/*/journal.sqlite') if not (path.parent/'summary.json').exists())
    retired=[]
    for folder,default in folders:
        if not (folder/'journal.sqlite').is_file():continue
        journal=Journal(folder)
        try:
            journal.verify()
            sid=active_analyst_session(folder,default);old=journal.state(sid)
            if not old:continue
            prefix=default.rsplit('-r',1)[0]
            numbers=[int(match[1]) for name in journal.states() if (match:=re.fullmatch(re.escape(prefix)+r'-r(\d+)',name))]
            successor=prefix+'-r'+str(max(numbers,default=0)+1)
            state=initial_state(successor,model,analyst_experiment_config(config))
            state['history']=[{**copy.deepcopy(message),'inherited_from_session':sid} for message in old['history']]
            state['history'].append({'role':'user','content':'You are the replacement analyst. Independently review the supplied evidence and previous visible discussion; earlier proposals are not approved conclusions. Return your own complete response following the original system instructions.'})
            state['calibration']={'tools':[],'previous_sessions':[],'stream_responses':config.get('stream_responses',True)}
            state['model_descriptor']=copy.deepcopy(model)
            state['supersedes_analyst_session']=sid
            state['history_policy']='inherited-analyst-evidence'
            journal.save(successor,state,'analyst_replacement_created',{'previous_session':sid,'previous_request_preserved':True,'reservation_released':False})
            write_json(folder/'active-analyst.json',{'session':successor,'previous_session':sid})
            retired.append({'directory':folder.relative_to(root).as_posix(),'session':sid,'successor':successor,'reserved_usd':old.get('money_reserved','0')})
        finally:journal.db.close()
    return retired
