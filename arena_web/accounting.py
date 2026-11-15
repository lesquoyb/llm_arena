"""Read-only accounting from provider receipts, never from conversation copies."""
from decimal import Decimal
from arena.usage import amount


FIELDS = ('input_tokens', 'output_tokens', 'cached_input_tokens', 'reasoning_tokens', 'cache_creation_input_tokens')


def summarize(receipts):
    from arena.submission_stops import output_limited
    result = {field: 0 for field in FIELDS}
    result.update(responses=0, missing_usage=0, missing_cache_usage=0, missing_reasoning_usage=0, reported_cost_usd='0', cost_adjustment_usd='0', missing_cache_creation_usage=0)
    result.update(output_cutoffs=0, output_reasons_known=0, preparation_responses=0)
    for receipt in receipts:
        if receipt.get('preparation_response'):
            result['preparation_responses'] += 1
            if receipt.get('stop_reason') or receipt.get('finish_reason'):
                result['output_reasons_known'] += 1
                result['output_cutoffs'] += int(output_limited(receipt))
        usage = receipt.get('usage')
        if not isinstance(usage, dict):
            continue
        result['responses'] += 1
        if usage.get('cache_creation_input_tokens') is None:
            result['missing_cache_creation_usage'] += 1
        result['cost_adjustment_usd'] = str(Decimal(result['cost_adjustment_usd']) + Decimal(receipt.get('cost_adjustment_usd', '0')))
        if any(usage.get(field) is None for field in FIELDS[:2]):
            result['missing_usage'] += 1
        if usage.get('cached_input_tokens') is None:
            result['missing_cache_usage'] += 1
        if usage.get('reasoning_tokens') is None:
            result['missing_reasoning_usage'] += 1
        for field in FIELDS:
            result[field] += usage.get(field) or 0
        if receipt.get('cost_usd') is not None:
            result['reported_cost_usd'] = str(amount(result['reported_cost_usd']) + amount(receipt['cost_usd']))
    return result


def token_budget_stop(state):
    """An attributable local stop, including a failed automatic submission."""
    if state.get('status') not in {'budget_exhausted', 'no_submission'}:
        return []
    stop = state.get('budget_stop') or {}
    reasons = stop.get('token_limits') or [stop.get('code')]
    known = [code for code in ('input_admission', 'input_tokens', 'output_tokens') if code in reasons]
    if known or stop.get('code'):
        return known
    message = stop.get('message', '').lower()
    if 'session input token limit' in message or message.startswith('preparation input_tokens limit'):
        return ['input_tokens']
    if message == 'output token budget exhausted' or message.startswith('preparation output_tokens limit'):
        return ['output_tokens']
    return []
