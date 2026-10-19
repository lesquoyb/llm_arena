"""Read-only accounting from provider receipts, never from conversation copies."""
from decimal import Decimal
from arena.usage import amount


FIELDS = ('input_tokens', 'output_tokens', 'cached_input_tokens', 'reasoning_tokens', 'cache_creation_input_tokens')


def summarize(receipts):
    result = {field: 0 for field in FIELDS}
    result.update(responses=0, missing_usage=0, missing_cache_usage=0, missing_reasoning_usage=0, reported_cost_usd='0', cost_adjustment_usd='0', missing_cache_creation_usage=0)
    for receipt in receipts:
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
