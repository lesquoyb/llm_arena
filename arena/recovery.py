"""Explicit recovery without discarding checkpoints or concealing provenance changes."""
from .core import ArenaError, digest
from .usage import amount


def engine_compatible(previous, current):
    # Application updates and host runtime changes do not replace the game engine.
    ignored = {'runner_sha256', 'java_version', 'python_version', 'platform', 'worker_execution', 'worker_transport_sha256'}
    # An added JVM transport changes the bridge directory hash, while the game
    # adapter, pinned jar and build overlay remain byte-for-byte unchanged.
    if (previous.get('adapter_sha256') and previous.get('adapter_sha256')==current.get('adapter_sha256')
            and previous.get('jar_sha256')==current.get('jar_sha256')
            and previous.get('build_script_sha256')==current.get('build_script_sha256')):
        ignored.add('bridge_sha256')
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


def reconcile(journal, sid, cost, note, *, automatic=False):
    import copy
    if not isinstance(note, str) or not note.strip():
        raise ArenaError('Explain how the request cost was checked')
    original = journal.state(sid)
    if not original or not needs_reconciliation(original):
        raise ArenaError('This conversation has no request awaiting reconciliation')
    charge = amount(cost)
    state = copy.deepcopy(original)
    from .submission_stops import restore_interrupted_streak
    restored=restore_interrupted_streak(state)
    if restored:journal.save(sid,state,'submission_counter_restored',restored)
    state['cost_spent'] = str(amount(state.get('cost_spent', '0')) + charge)
    state.update(in_flight=False, money_reserved='0', reservation_unbounded=False)
    if automatic and original.get('in_flight'):
        state['token_usage_known']=False
        state['missing_usage_calls']=state.get('missing_usage_calls',0)+1
    # A received response still has pending tools; continue them without resending it.
    state['status'] = 'running' if state.get('pending') else 'provider_unavailable'
    if state.get('pending'):
        state['retry_count'] = state.get('retry_count', 0) + 1
    state.pop('failure', None)
    journal.save(sid, state, 'billing_reconciled', {'cost_usd': str(charge), 'note':note.strip(),
        'previous_checkpoint_sha256':digest(original), 'previous_status':original['status'],
        'response_received':bool(state.get('pending')), 'usage_counters_preserved':True, 'automatic':automatic})
    for child_id, child in journal.states().items():
        if (child.get('parent') == sid and child.get('status') == 'no_submission'
                and not child.get('calls') and not child.get('submission')):
            child['retry_parent_refresh'] = True
            journal.save(child_id, child, 'branch_waiting_retry', {'parent':sid})
    return state


def zero_cost_requests(model):
    """Only explicit all-zero prices establish that an unknown request costs zero."""
    from .usage import effective_pricing
    pricing=effective_pricing(model)
    return bool(pricing is not None and all(key in pricing for key in ('input_per_million','output_per_million')) and
                all(amount(pricing.get(key,pricing['input_per_million']))==0 for key in
                    ('input_per_million','output_per_million','cached_input_per_million','cache_creation_per_million')))


def recover_zero_cost_requests(journal, models):
    """Audit recovery of interrupted free requests; never fabricate token usage."""
    by_id={model['id']:model for model in models}
    for sid,state in journal.states().items():
        model=by_id.get(state.get('model'))
        if model and zero_cost_requests(model) and needs_reconciliation(state) and amount(state.get('money_reserved','0'))==0:
            reconcile(journal,sid,'0','Automatically resolved: all configured request prices are zero; token usage of the interrupted request remains unknown.',automatic=True)
