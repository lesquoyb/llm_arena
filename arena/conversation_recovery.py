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
    from .budget_context import tool_budget_exhausted
    if not restart and tool_budget_exhausted(state,config['budget_per_session']):
        state['status']='running';journal.save(sid,state,'budget_finalization_requested',{'counters_preserved':True})
    elif not restart and state['status']!='running':prepare_retry(journal,sid,config)
    state=journal.state(sid)
    if restart:
        # Old state remains in the journal; retain a browsable source archive too.
        target=out/'sessions'/sid/'restarts'/str(time.time_ns())
        write_json(target/'state.json',state)
        workspace=out/'sessions'/sid/'workspace'
        if workspace.exists():shutil.copytree(workspace,target/'workspace');shutil.rmtree(workspace)
        state.update(history=[copy.deepcopy(state['history'][0])],message_times=[],
                     pending=None,cursor=0,reserved=None,workspace_files={})
        from .usage import amount
        state['discarded_attempt_cost_usd']=str(amount(state.get('discarded_attempt_cost_usd','0'))+amount(state.get('cost_spent','0')))
        # calls is the monotonic transport sequence used in immutable tool paths.
        # completed_calls is the active-attempt metric; never reuse artifact IDs.
        state.update(status='running',completed_calls=0,steps=0,test_matches=0,replay_reads=0,
                     wall_seconds=0,cost_spent='0',input_tokens=0,output_tokens=0,
                     token_usage_known=False,missing_usage_calls=0,diagnostic_calls=0,
                     diagnostic_cost_usd='0',money_reserved='0',in_flight=False,reservation_unbounded=False)
        for field in ('failure','budget_stop','context_recoveries','submission_reminders','current_tool','automatic_retry_at'):
            state.pop(field,None)
        # Training fights of discarded attempts stay browsable under the archive,
        # while active statistics and preparation limits start afresh.
        state['attempt']=state.get('attempt',0)+1
        state['attempt_started_at']=time.time()

        state.pop('request_history_start',None)
        state.pop('consecutive_submission_reminders',None)
    state['automatic_retry_attempts']=previous_attempts+1 if automatic else 0
    state.pop('automatic_retry_at',None)
    if command_id:state['applied_recovery_commands']=[*state.get('applied_recovery_commands',[]),command_id][-50:]
    journal.save(sid,state,'conversation_restarted' if restart else 'conversation_recovery_requested',
                 {'automatic':automatic,'restart':restart,'counters_preserved':not restart,'attempt':state.get('attempt',0),'archive':target.relative_to(out).as_posix() if restart else None})


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
