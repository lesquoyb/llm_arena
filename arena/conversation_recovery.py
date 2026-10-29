"""Coordinator-owned recovery; the web server only enqueues immutable commands."""
from __future__ import annotations
import copy
import shutil
import time
from .core import ArenaError, read_json, write_json
from .retries import prepare_retry, retry_reason


def automatic_due(state, config, parent=None):
    failure=state.get('failure') or {}
    if (state.get('status')!='provider_unavailable' or not failure.get('retryable')
            or retry_reason(state,config['budget_per_session'],parent) is not None):return None
    attempts=state.get('automatic_retry_attempts',0)
    if attempts>=3:return None
    return failure.get('at',time.time())+min(120,30*2**attempts)


def recover(sid, state, config, out, journal, *, restart=False, automatic=False, command_id=None):
    if state.get('submission') or state.get('in_flight'):
        raise ArenaError('Only an idle conversation without a frozen submission can be recovered')
    previous_attempts=state.get('automatic_retry_attempts',0)
    if state['status']!='running':prepare_retry(journal,sid,config)
    state=journal.state(sid)
    if restart:
        # Old state remains in the journal; retain a browsable source archive too.
        target=out/'sessions'/sid/'restarts'/str(time.time_ns())
        write_json(target/'state.json',state)
        workspace=out/'sessions'/sid/'workspace'
        if workspace.exists():shutil.copytree(workspace,target/'workspace');shutil.rmtree(workspace)
        state.update(history=[copy.deepcopy(state['history'][0])],message_times=[],
                     pending=None,cursor=0,reserved=None,workspace_files={})
        state.pop('request_history_start',None)
        state.pop('consecutive_submission_reminders',None)
    state['automatic_retry_attempts']=previous_attempts+1 if automatic else 0
    state.pop('automatic_retry_at',None)
    if command_id:state['applied_recovery_commands']=[*state.get('applied_recovery_commands',[]),command_id][-50:]
    journal.save(sid,state,'conversation_restarted' if restart else 'conversation_recovery_requested',
                 {'automatic':automatic,'restart':restart,'counters_preserved':True})


def commands(out, journal, config, tasks, pending=()):
    """Consume commands on the coordinator, never while their transport is active."""
    models=dict(tasks);queued=[]
    for path in sorted((out/'recovery-commands').glob('*.json')):
        command=read_json(path);sid=command.get('session')
        if sid not in models or sid in pending:continue
        try:
            state=journal.state(sid)
            if not state:raise ArenaError('Conversation not found')
            command_id=command.get('id',path.stem)
            if command_id not in state.get('applied_recovery_commands',[]):
                recover(sid,state,config,out,journal,restart=command['action']=='restart',command_id=command_id)
                queued.append((sid,models[sid]))
            result={'status':'applied'}
        except ArenaError as error:result={'status':'rejected','error':str(error)}
        write_json(out/'recovery-results'/path.name,{**command,**result,'at':time.time()})
        path.unlink()
    return queued
