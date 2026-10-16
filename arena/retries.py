"""Audited continuation of a failed conversation; completed submissions are immutable."""
import copy
import time
from .core import ArenaError, digest
from .usage import amount


def retry_reason(state, budget=None, parent=None):
    if not state:
        return 'Conversation not found'
    if state.get('in_flight') or state.get('status') == 'needs_reconciliation' or amount(state.get('money_reserved', '0')) > 0:
        return 'Reconcile the previous request and its billing before retrying an unknown outcome'
    if state.get('submission'):
        return 'This conversation already has a frozen submission'
    if state.get('status') not in {'provider_unavailable', 'generation_failed', 'no_submission'}:
        return 'Only failed conversations without a submission can be retried'
    if state.get('parent') and not (parent or {}).get('submission'):
        return 'Recover the initial strategy before retrying its improvement conversation'
    budget = budget or {}
    if 'max_cost_usd' in budget and amount(state.get('cost_spent', '0')) >= amount(budget['max_cost_usd']):
        return 'The conversation has reached its configured API spending limit'
    for field, limit in [('calls', 'max_calls'), ('steps', 'max_agent_steps'), ('wall_seconds', 'max_wall_seconds'),
                         ('input_tokens', 'max_input_tokens'), ('output_tokens', 'max_output_tokens')]:
        if limit in budget and state.get(field, 0) >= budget[limit]:
            return f'The conversation has reached its configured {limit}; retry does not reset limits'
    return None


def prepare_retry(journal, sid, config):
    original = journal.state(sid)
    parent = journal.state(original['parent']) if original and original.get('parent') else None
    reason = retry_reason(original, config['budget_per_session'], parent)
    if reason:
        raise ArenaError(reason)
    state = copy.deepcopy(original)
    state.update(status='running', in_flight=False, money_reserved='0', reservation_unbounded=False,
                 retry_count=state.get('retry_count', 0) + 1)
    state.pop('failure', None)
    # An API rejection has no response to repair; resend the same history. If the
    # model stopped without submitting, explicitly ask it to continue that work.
    if original['status'] == 'no_submission':
        state['history'].append({'role':'user', 'content':
            'Continue from your existing files and conversation. The previous attempt did not produce a submission. '
            'Fix any tool errors and finish with submit. The scenario and preparation limits are unchanged.'})
        state['pending'], state['cursor'], state['reserved'] = None, 0, None
    journal.save(sid, state, 'retry_requested', {'session':sid, 'at':time.time(),
        'previous_status':original['status'], 'previous_checkpoint_sha256':digest(original),
        'attempt':state['retry_count'], 'history_and_counters_preserved':True})
    if original.get('generation', 0) == 0:
        for child_id, child in journal.states().items():
            if (child.get('parent') == sid and child.get('status') == 'no_submission'
                    and not child.get('calls') and not child.get('submission')):
                child['retry_parent_refresh'] = True
                journal.save(child_id, child, 'branch_waiting_retry', {'parent':sid})
    return state
