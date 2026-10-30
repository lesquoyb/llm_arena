"""Rebase an oversized request without deleting its auditable conversation."""
import copy
import re


def context_overflow(state):
    failure = state.get('failure') or {}
    text = str(failure.get('message', '')) + ' ' + str(failure.get('diagnostics', {}))
    return bool(re.search(r'invalid_request_prompt_too_long|context_length_exceeded|maximum context length|prompt.{0,80}exceeds.{0,30}context', text, re.I))


def rebase(state):
    """Keep instructions and disk state; archive exchanges remain in history."""
    history = state['history']
    active = history[state.get('request_history_start', 0):]
    instructions = [copy.deepcopy(message) for message in active
                    if message.get('role') in {'system', 'user'} and not message.get('context_recovery')]
    paths = sorted(state.get('workspace_files', {}))
    reminder = {'role':'user', 'context_recovery':True, 'content':
        'The provider rejected the previous request because this conversation exceeded its context window. '
        'This is a continuation of the SAME preparation session, not a new round. '
        'Earlier tool exchanges are omitted from this request; your saved source files and configured team remain intact. '
        'Do not assume they were submitted or validated. Use list_files and read_file to inspect the CURRENT files, '
        'then continue improving, analyze the final saved source and submit. '
        'The original scenario, feedback access and remaining preparation limits still apply. '
        'This recovery does not reset usage or budgets. Saved file paths: ' + (', '.join(paths) or '(use list_files).')}
    state['request_history_start'] = len(history)
    history.extend(instructions + [reminder])
    state['context_recoveries'] = state.get('context_recoveries', 0) + 1
    return {'request_history_start':state['request_history_start'], 'archived_messages':len(active),
            'retained_instruction_messages':len(instructions), 'workspace_files':paths,
            'reason':'provider_context_length_exceeded', 'history_preserved':True}


def recover_automatically(state):
    """Retry a definite context rejection once; never loop on oversized instructions."""
    if state.get('status')!='provider_unavailable' or state.get('in_flight') or not context_overflow(state):
        return None
    active=state.get('history',[])[state.get('request_history_start',0):]
    if state.get('consecutive_context_recoveries',0)>=1 or not any(message.get('role') in {'assistant','tool'} for message in active):
        return None
    recovery=rebase(state)
    state.update(status='running',pending=None,cursor=0,reserved=None,
                 consecutive_context_recoveries=state.get('consecutive_context_recoveries',0)+1,
                 context_retry_pending=True)
    state.pop('failure',None)
    return {**recovery,'automatic':True,'usage_and_budgets_preserved':True}
