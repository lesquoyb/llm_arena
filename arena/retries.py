"""Audited continuation of a failed conversation; completed submissions are immutable."""
import copy
import time
from .core import ArenaError, digest
from .usage import amount
from .call_counts import completed_calls, hydrate_calls


def retry_reason(state, budget=None, parent=None):
    if not state:
        return 'Conversation not found'
    if state.get('in_flight') or state.get('status') == 'needs_reconciliation' or amount(state.get('money_reserved', '0')) > 0:
        return 'Reconcile the previous request and its billing before retrying an unknown outcome'
    if state.get('submission'):
        return 'This conversation already has a frozen submission'
    if state.get('status') not in {'provider_unavailable', 'generation_failed', 'no_submission'} and not (state.get('conversation_paused') and state.get('status')=='running'):
        return 'Only failed conversations without a submission can be retried'
    if state.get('parent') and not (parent or {}).get('submission'):
        return 'Recover the initial strategy before retrying its improvement conversation'
    budget = budget or {}
    if 'max_cost_usd' in budget and amount(state.get('cost_spent', '0')) >= amount(budget['max_cost_usd']):
        return 'The conversation has reached its configured API spending limit'
    for field, limit in [('calls', 'max_calls'), ('steps', 'max_agent_steps'), ('wall_seconds', 'max_wall_seconds'),
                         ('input_tokens', 'max_input_tokens'), ('output_tokens', 'max_output_tokens')]:
        value = completed_calls(state) if field == 'calls' else state.get(field, 0)
        if limit in budget and value >= budget[limit]:
            return f'The conversation has reached its configured {limit}; retry does not reset limits'
    return None


def prepare_retry(journal, sid, config, reasoning_effort=None):
    original = journal.state(sid)
    original_hash = digest(original)
    if original is not None:
        hydrate_calls(original, journal.db, sid)
    parent = journal.state(original['parent']) if original and original.get('parent') else None
    reason = retry_reason(original, config['budget_per_session'], parent)
    if reason:
        raise ArenaError(reason)
    state = copy.deepcopy(original)
    from .submission_stops import restore_interrupted_streak
    restored=restore_interrupted_streak(state)
    if restored:journal.save(sid,state,'submission_counter_restored',restored)
    previous_stop_streak=state.get('consecutive_submission_reminders',0)
    if reasoning_effort is not None:
        from .reasoning import validate_effort
        model = next(m for m in config['models'] if m['id'] == state['model'])
        effort = None if reasoning_effort == 'provider-default' else reasoning_effort
        validate_effort(model, effort)
        state['provider_parameter_overrides'] = {**state.get('provider_parameter_overrides', {}), 'reasoning_effort':effort}
    state.update(status='running', in_flight=False, money_reserved='0', reservation_unbounded=False,
                 retry_count=state.get('retry_count', 0) + 1)
    from .context_recovery import context_overflow, rebase
    if original['status'] == 'provider_unavailable' and context_overflow(original):
        recovery = rebase(state)
        journal.save(sid, state, 'context_rebased', recovery)
    state.pop('failure', None)
    # An API rejection has no response to repair; resend the same history. If the
    # model stopped without submitting, explicitly ask it to continue that work.
    from .submission_stops import output_limited, continue_output
    if output_limited(original.get('failure') or {}):
        # Older runners saved output limits as provider failures. Resume their
        # existing history with the same continuation used by current sessions.
        continue_output(state,original['failure'])
    elif (original.get('failure') or {}).get('incomplete_response') or (previous_stop_streak and original['status']!='no_submission'):
        state['history'].append({'role':'user','provider_recovery':True,'content':
            'The previous provider request failed or its response was incomplete. Continue the same preparation session from your current workspace. '
            'Saved files, tool access, recorded usage and remaining budgets are unchanged. '
            f'Submission reminders already issued in this streak: {previous_stop_streak}. '
            'This interruption does not count as a completed model turn.'})
    if original['status'] == 'no_submission':
        state['consecutive_submission_reminders']=0
        state['history'].append({'role':'user', 'content':
            'Continue from your existing files and conversation. The previous attempt did not produce a submission. '
            'Fix any tool errors and finish with submit. The scenario and preparation limits are unchanged.'})
        state['pending'], state['cursor'], state['reserved'] = None, 0, None
    journal.save(sid, state, 'retry_requested', {'session':sid, 'at':time.time(),
        'previous_status':original['status'], 'previous_checkpoint_sha256':original_hash,
        'attempt':state['retry_count'], 'history_and_counters_preserved':True,'previous_stop_streak':previous_stop_streak,'stop_streak_preserved':True,
        'provider_parameter_overrides':state.get('provider_parameter_overrides', {})})
    for child_id, child in journal.states().items():
        if (child.get('parent') == sid and child.get('status') == 'no_submission'
                and not child.get('calls') and not child.get('submission')):
            child['retry_parent_refresh'] = True
            journal.save(child_id, child, 'branch_waiting_retry', {'parent':sid})
    return state
