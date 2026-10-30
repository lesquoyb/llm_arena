"""Per-conversation automatic retry switches, adjustable without restarting a run."""
from .core import read_json


def policies(out):
    return {path.stem:read_json(path) for path in (out/'retry-policies').glob('*.json')}


def apply(out,journal):
    changed=[]
    for sid,policy in policies(out).items():
        metadata=journal.metadata(sid).get(sid)
        paused=policy['paused']
        if metadata is None or bool(metadata.get('automatic_retries_paused'))==paused:continue
        state=journal.state(sid);state['automatic_retries_paused']=paused
        if paused:state.pop('automatic_retry_at',None)
        journal.save(sid,state,'automatic_retry_policy_changed',{'paused':paused,'requested_at':policy['requested_at'],'counters_preserved':True})
        changed.append((sid,paused))
    return changed
