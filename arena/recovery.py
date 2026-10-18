"""Explicit recovery without discarding checkpoints or concealing provenance changes."""
from .core import ArenaError, digest
from .usage import amount


def engine_compatible(previous, current):
    # Application updates and host runtime changes do not replace the game engine.
    ignored = {'runner_sha256', 'java_version', 'python_version', 'platform'}
    return ({k:v for k,v in previous.items() if k not in ignored} ==
            {k:v for k,v in current.items() if k not in ignored})


def resume_compatible(previous, current):
    flexible = {'engine', 'scientific_identity', 'runtime_provenance', 'artifact_provenance',
                'prompt_sha256', 'prompts_sha256', 'corpus_sha256'}
    return (engine_compatible(previous['engine'], current['engine']) and
            {k:v for k,v in previous.items() if k not in flexible} ==
            {k:v for k,v in current.items() if k not in flexible})


def needs_reconciliation(state, external=True):
    return external and bool(state.get('in_flight') or state.get('status') == 'needs_reconciliation' or
                amount(state.get('money_reserved', '0')) > 0)


def reconcile(journal, sid, cost, note):
    import copy
    if not isinstance(note, str) or not note.strip():
        raise ArenaError('Explain how the request cost was checked')
    original = journal.state(sid)
    if not original or not needs_reconciliation(original):
        raise ArenaError('This conversation has no request awaiting reconciliation')
    charge = amount(cost)
    state = copy.deepcopy(original)
    state['cost_spent'] = str(amount(state.get('cost_spent', '0')) + charge)
    state.update(in_flight=False, money_reserved='0', reservation_unbounded=False)
    # A received response still has pending tools; continue them without resending it.
    state['status'] = 'running' if state.get('pending') else 'provider_unavailable'
    if state.get('pending'):
        state['retry_count'] = state.get('retry_count', 0) + 1
    state.pop('failure', None)
    journal.save(sid, state, 'billing_reconciled', {'cost_usd': str(charge), 'note':note.strip(),
        'previous_checkpoint_sha256':digest(original), 'previous_status':original['status'],
        'response_received':bool(state.get('pending')), 'usage_counters_preserved':True})
    for child_id, child in journal.states().items():
        if (child.get('parent') == sid and child.get('status') == 'no_submission'
                and not child.get('calls') and not child.get('submission')):
            child['retry_parent_refresh'] = True
            journal.save(child_id, child, 'branch_waiting_retry', {'parent':sid})
    return state
