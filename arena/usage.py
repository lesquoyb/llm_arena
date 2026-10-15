"""Decimal accounting: unavailable usage is never zero."""
from decimal import Decimal, InvalidOperation
from .core import ArenaError


def amount(value):
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ArenaError("Invalid monetary amount") from None
    if not result.is_finite() or result < 0:
        raise ArenaError("Amounts must be finite and nonnegative")
    return result


def normalize(provider, raw):
    raw = raw or {}
    if provider == "gemini":
        fields = ("promptTokenCount", "candidatesTokenCount", "thoughtsTokenCount", "cachedContentTokenCount")
        for key in fields:
            if raw.get(key) is not None and (type(raw[key]) is not int or raw[key] < 0):
                raise ArenaError("Invalid Gemini token usage")
        # Gemini reports thought tokens separately; they are billable output.
        output = raw.get("candidatesTokenCount")
        return {"input_tokens": raw.get("promptTokenCount"),
                "output_tokens": output + raw.get("thoughtsTokenCount", 0) if output is not None else None,
                "cached_input_tokens": raw.get("cachedContentTokenCount", 0) if raw.get("promptTokenCount") is not None else None,
                "cache_creation_input_tokens": None, "reasoning_tokens": raw.get("thoughtsTokenCount"), "raw": raw}
    fields = ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens") if provider == "anthropic" else ("prompt_tokens", "completion_tokens")
    for key in fields:
        if raw.get(key) is not None and (type(raw[key]) is not int or raw[key] < 0):
            raise ArenaError("Invalid provider token usage")
    if provider == "anthropic":
        parts = [raw.get(k) for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")]
        total = sum(parts) if all(x is not None for x in parts) else None
        return {"input_tokens": total, "output_tokens": raw.get("output_tokens"),
                "cached_input_tokens": parts[1], "cache_creation_input_tokens": parts[2],
                "reasoning_tokens": None, "raw": raw}
    for mapping in (raw.get("prompt_tokens_details") or {}, raw.get("completion_tokens_details") or {}):
        for key in ("cached_tokens", "reasoning_tokens"):
            if mapping.get(key) is not None and (type(mapping[key]) is not int or mapping[key] < 0):
                raise ArenaError("Invalid provider token detail")
    return {"input_tokens": raw.get("prompt_tokens"), "output_tokens": raw.get("completion_tokens"),
            "cached_input_tokens": (raw.get("prompt_tokens_details") or {}).get("cached_tokens"),
            "cache_creation_input_tokens": None,
            "reasoning_tokens": (raw.get("completion_tokens_details") or {}).get("reasoning_tokens"), "raw": raw}


def cost(usage, pricing):
    if pricing is None or usage.get("input_tokens") is None or usage.get("output_tokens") is None:
        return None
    if (usage.get("cached_input_tokens") is None and "cached_input_per_million" in pricing and
            amount(pricing["cached_input_per_million"]) != amount(pricing["input_per_million"])):
        return None
    cached = usage.get("cached_input_tokens") or 0
    created = usage.get("cache_creation_input_tokens") or 0
    if min(cached, created) < 0 or cached + created > usage["input_tokens"]:
        raise ArenaError("Invalid cache usage")
    regular = usage["input_tokens"] - cached - created
    total = (regular * amount(pricing["input_per_million"]) +
             cached * amount(pricing.get("cached_input_per_million", pricing["input_per_million"])) +
             created * amount(pricing.get("cache_creation_per_million", pricing["input_per_million"])) +
             usage["output_tokens"] * amount(pricing["output_per_million"])) / Decimal(1_000_000)
    return str(total)


def reservation(model, history, tools, remaining_output):
    # Configured upper bounds, not a tokenizer-independent claim of strict billing.
    import json
    input_bound = model["max_input_tokens_per_call"]
    output_bound = min(model["max_output_tokens"], remaining_output)
    if output_bound <= 0:
        raise ArenaError("Output token budget exhausted")
    from .api_providers import APIProvider
    payload = APIProvider(model).payload(history, tools, output_bound)
    if len(json.dumps(payload, ensure_ascii=False).encode()) > input_bound:
        raise ArenaError("Request exceeds conservative UTF-8 input admission bound")
    p = model["pricing"]
    input_rate = max(amount(p.get(key, p["input_per_million"])) for key in
                     ("input_per_million", "cached_input_per_million", "cache_creation_per_million"))
    bound = (input_bound * input_rate + output_bound * amount(p["output_per_million"])) / Decimal(1_000_000)
    return {"input_bound": input_bound, "output_bound": output_bound, "cost_bound": str(bound),
            "strict": False, "basis": "configured input bound; provider billing not independently confirmed"}
