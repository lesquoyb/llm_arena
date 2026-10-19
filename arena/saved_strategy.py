"""Portable, immutable source participants. No inference calls are needed."""
import hashlib
from pathlib import PurePosixPath
from .core import ArenaError, digest, submission
from .preparation import local_path


def validate(model, scenario=None):
    if set(model) != {'id','provider','profile','strategy'} or model.get('profile') != 'saved-strategy':
        raise ArenaError('Invalid saved strategy participant')
    value=model['strategy']
    if not isinstance(value,dict) or set(value) != {'files','submission','scenario_sha256','origin'}:
        raise ArenaError('Invalid frozen strategy data')
    files=value['files']
    if not isinstance(files,dict) or not 1 <= len(files) <= 129:
        raise ArenaError('Invalid frozen source files')
    for name, content in files.items():
        path=PurePosixPath(name)
        if (not isinstance(content,str) or path.is_absolute() or '..' in path.parts or '\\' in name or ':' in name
                or str(path)!=name or not (name.endswith('.leek') or name=='team.json')):
            raise ArenaError('Invalid frozen source path or content')
    if sum(name.endswith('.leek') for name in files) > 128:
        raise ArenaError('Frozen strategy exceeds file quota')
    if sum(len(text.encode('utf-8')) for text in files.values()) > 2_000_000:
        raise ArenaError('Frozen strategy exceeds source quota')
    hashes={name:hashlib.sha256(text.encode('utf-8')).hexdigest() for name,text in files.items()}
    info=value['submission']
    if not isinstance(info,dict) or info.get('files')!=hashes or info.get('sha256')!=digest(hashes) or info.get('entrypoint') not in files or not info['entrypoint'].endswith('.leek'):
        raise ArenaError('Frozen strategy fingerprint mismatch')
    if scenario is not None and value['scenario_sha256']!=digest(scenario):
        raise ArenaError('Saved strategy '+model['id']+' requires its original scenario. Clone its source competition before selecting it.')
    return value


def restore(model, tools, state, sid, journal):
    value=validate(model,tools.scenario)
    from .experiment import workspace_files
    existing=workspace_files(tools.workspace)
    if any(value['submission']['files'].get(name)!=sha for name,sha in existing.items()):
        raise ArenaError('Saved strategy workspace was changed')
    for name,content in value['files'].items():
        path=local_path(tools.workspace,name)
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(content,encoding='utf-8',newline='')
    if submission(tools.workspace,value['submission']['entrypoint']) != value['submission']:
        raise ArenaError('Restored strategy differs from frozen submission')
    state['workspace_files']=workspace_files(tools.workspace)
    result=tools.call('submit',{'entrypoint':value['submission']['entrypoint']},'call-0-tool-0')
    if 'submission' not in result:
        raise ArenaError('Could not restore saved strategy')
    state['submission']=result['submission'];state['status']='submitted'
    state['saved_strategy_origin']=value['origin']
    state['history'].append({'role':'user','content':'A frozen strategy was restored and submitted without a model call. Its code and team remain unchanged in every round.','origin':value['origin']})
    journal.save(sid,state,'saved_strategy_restored',result)
