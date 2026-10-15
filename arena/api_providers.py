"""OpenAI Chat Completions and Anthropic Messages; no implicit paid activation."""
from __future__ import annotations
import json
import os
import time
from urllib import request, error, parse
from .core import ArenaError
from .usage import normalize, cost


class ProviderFailure(ArenaError):
    def __init__(self, message, *, uncertain=False, retryable=False):
        super().__init__(message)
        self.uncertain, self.retryable = uncertain, retryable


def http_json(url, payload, headers, timeout):
    if parse.urlsplit(url).scheme != "https":
        raise ArenaError("Provider endpoints must use HTTPS")
    req = request.Request(url, data=json.dumps(payload).encode(), headers=headers, method="POST")
    try:
        with request.urlopen(req, timeout=timeout) as response:
            body = response.read(8_000_001)
            if len(body) > 8_000_000:
                raise ProviderFailure("Provider response exceeded quota", uncertain=True)
            return json.loads(body), response.headers.get("x-request-id") or response.headers.get("request-id")
    except error.HTTPError as exc:
        # Do not store or print headers, request bodies or credential-bearing error bodies.
        raise ProviderFailure(f"Provider HTTP {exc.code}", uncertain=exc.code >= 500,
                              retryable=exc.code == 429) from None
    except (error.URLError, TimeoutError, OSError, ValueError) as exc:
        raise ProviderFailure(f"Provider response unavailable ({type(exc).__name__})", uncertain=True) from None


class APIProvider:
    def __init__(self, model, transport=http_json):
        self.model, self.transport = model, transport

    def payload(self, history, tools, output_limit):
        m = self.model
        messages = []
        for item in history:
            if item["role"] == "user":
                messages.append({"role": "user", "content": json.dumps(
                    {k: v for k, v in item.items() if k != "role"}, ensure_ascii=False)})
            elif item["role"] == "assistant":
                native = item["native"]
                messages.append(native if m["provider"] == "anthropic" else
                                {k: v for k, v in native.items()
                                 if k in {"role", "content", "tool_calls", "refusal", "audio", "function_call"}})
            elif item["role"] == "tool":
                content = json.dumps(item["result"], ensure_ascii=False)
                if m["provider"] == "anthropic":
                    block = {"type": "tool_result", "tool_use_id": item["provider_call_id"], "content": content}
                    if messages and messages[-1]["role"] == "user" and isinstance(messages[-1]["content"], list):
                        messages[-1]["content"].append(block)
                    else:
                        messages.append({"role": "user", "content": [block]})
                else:
                    messages.append({"role": "tool", "tool_call_id": item["provider_call_id"], "content": content})
        payload = {"model": m["model"], "messages": messages, **m.get("parameters", {})}
        if m["provider"] == "anthropic":
            payload.update(max_tokens=output_limit, tools=tools)
        else:
            payload.update(max_completion_tokens=output_limit,
                           tools=[{"type": "function", "function": {"name": t["name"],
                                  "description": t["description"], "parameters": t["input_schema"]}} for t in tools])
        return payload

    def respond(self, history, tools, output_limit):
        m = self.model
        key = os.environ.get(m["api_key_env"])
        if not key:
            raise ProviderFailure(f"Missing credential binding: {m['api_key_env']}")
        anthropic = m["provider"] == "anthropic"
        endpoint = m.get("endpoint", "https://api.anthropic.com/v1/messages" if anthropic
                         else "https://api.openai.com/v1/chat/completions")
        headers = {"Content-Type": "application/json"}
        if anthropic:
            headers.update({"x-api-key": key, "anthropic-version": "2023-06-01"})
        else:
            headers["Authorization"] = "Bearer " + key
        payload = self.payload(history, tools, output_limit)
        retries = []
        for attempt in range(m.get("max_retries", 0) + 1):
            try:
                raw, request_id = self.transport(endpoint, payload, headers, m.get("timeout_seconds", 60))
                break
            except ProviderFailure as failure:
                if not failure.retryable or failure.uncertain or attempt == m.get("max_retries", 0):
                    raise
                retries.append({"attempt": attempt + 1, "error": str(failure)})
                time.sleep(min(2 ** attempt, 4))
        if anthropic:
            self.last_response = {"raw": raw, "request_id": request_id, "sent_parameters": payload}
            native = {"role": "assistant", "content": raw["content"]}
            calls = [{"id": b["id"], "name": b["name"], "arguments": b["input"]}
                     for b in raw["content"] if b["type"] == "tool_use"]
            stop = raw.get("stop_reason")
        else:
            self.last_response = {"raw": raw, "request_id": request_id, "sent_parameters": payload}
            native = raw["choices"][0]["message"]
            calls = []
            for call in native.get("tool_calls") or []:
                try:
                    arguments = json.loads(call["function"]["arguments"])
                except ValueError:
                    arguments = None
                calls.append({"id": call["id"], "name": call["function"]["name"], "arguments": arguments})
            stop = raw["choices"][0].get("finish_reason")
        usage = normalize(m["provider"], raw.get("usage"))
        return {"role": "assistant", "provider": m["provider"], "simulated": False, "native": native,
                "tool_calls": calls, "stop_reason": stop, "usage": usage, "raw": raw,
                "request_id": request_id, "sent_parameters": payload,
                "retries": retries,
                "cost_usd": cost(usage, m["pricing"]), "cost_status": "calculated_from_reported_usage"}
