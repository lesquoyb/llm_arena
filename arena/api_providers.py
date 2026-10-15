"""Native provider adapters and model catalogs; no implicit paid activation."""
from __future__ import annotations
import json
import os
import time
from urllib import request, error, parse
from .core import ArenaError, digest
from .usage import normalize, cost


class ProviderFailure(ArenaError):
    def __init__(self, message, *, uncertain=False, retryable=False):
        super().__init__(message)
        self.uncertain, self.retryable = uncertain, retryable


def http_json(url, payload, headers, timeout):
    if parse.urlsplit(url).scheme != "https":
        raise ArenaError("Provider endpoints must use HTTPS")
    req = request.Request(url, data=json.dumps(payload).encode() if payload is not None else None,
                          headers=headers, method="POST" if payload is not None else "GET")
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
        if m["provider"] == "gemini":
            return gemini_payload(history, tools, output_limit, m.get("parameters", {}))
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
        endpoint, headers = connection(m, key)
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
        if m["provider"] == "gemini":
            self.last_response = {"raw": raw, "request_id": request_id, "sent_parameters": payload}
            candidate = (raw.get("candidates") or [{}])[0]
            content = candidate.get("content") or {"role": "model", "parts": []}
            native = {"role": "model", "parts": content.get("parts", [])}
            calls = []
            for index, part in enumerate(native["parts"]):
                call = part.get("functionCall")
                if call:
                    calls.append({"id": call.get("id", f"gemini-{len(history)}-{index}"),
                                  "name": call["name"], "arguments": call.get("args", {})})
            stop = candidate.get("finishReason") or raw.get("promptFeedback", {}).get("blockReason")
        elif anthropic:
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
        usage = normalize(m["provider"], raw.get("usageMetadata") if m["provider"] == "gemini" else raw.get("usage"))
        return {"role": "assistant", "provider": m["provider"], "simulated": False, "native": native,
                "tool_calls": calls, "stop_reason": stop, "usage": usage, "raw": raw,
                "request_id": request_id or raw.get("responseId"), "sent_parameters": payload,
                "request_sha256": digest(payload), "system_fingerprint": raw.get("system_fingerprint"),
                "model_version": raw.get("modelVersion") or raw.get("model"), "retries": retries,
                "cost_usd": cost(usage, m["pricing"]), "cost_status": "calculated_from_reported_usage"}


DEFAULT_ENDPOINTS = {"openai": "https://api.openai.com/v1/chat/completions",
                     "anthropic": "https://api.anthropic.com/v1/messages",
                     "gemini": "https://generativelanguage.googleapis.com/v1beta"}


def connection(model, key):
    provider = model["provider"]
    endpoint = model.get("endpoint") or DEFAULT_ENDPOINTS.get(provider)
    if not endpoint:
        raise ArenaError("An endpoint is required")
    headers = {"Content-Type": "application/json"}
    if provider == "gemini":
        endpoint = endpoint.rstrip("/") + "/models/" + parse.quote(model["model"].removeprefix("models/"), safe="") + ":generateContent"
        headers["x-goog-api-key"] = key
    elif provider == "anthropic":
        headers.update({"x-api-key": key, "anthropic-version": "2023-06-01"})
    else:
        headers["Authorization"] = "Bearer " + key
    return endpoint, headers


def gemini_payload(history, tools, output_limit, parameters):
    contents = []
    native_ids = {part["functionCall"].get("id") for item in history if item["role"] == "assistant"
                  for part in item.get("native", {}).get("parts", []) if "functionCall" in part}
    for item in history:
        if item["role"] == "user":
            parts = [{"text": json.dumps({k:v for k,v in item.items() if k != "role"}, ensure_ascii=False)}]
            role = "user"
        elif item["role"] == "assistant":
            contents.append(item["native"])
            continue
        elif item["role"] == "tool":
            result = {"name": item["name"], "response": {"result": item["result"]}}
            if item.get("provider_call_id") in native_ids:
                result["id"] = item["provider_call_id"]
            parts, role = [{"functionResponse": result}], "user"
        else:
            raise ArenaError("Unsupported Gemini message role")
        if contents and contents[-1]["role"] == role:
            contents[-1] = {**contents[-1], "parts": [*contents[-1]["parts"], *parts]}
        else:
            contents.append({"role": role, "parts": parts})
    mapping = {"top_p": "topP", "top_k": "topK", "thinking_config": "thinkingConfig"}
    generation = {mapping.get(k,k):v for k,v in parameters.items()}
    generation["maxOutputTokens"] = output_limit
    return {"contents": contents, "generationConfig": generation,
            "tools": [{"functionDeclarations": [{"name":t["name"], "description":t["description"],
                       "parametersJsonSchema":t["input_schema"]} for t in tools]}]}


def request_snapshot(model, history, tools, output_limit):
    if model["provider"] == "mock":
        from .providers import MockProvider
        body = MockProvider(model["profile"]).payload(history, tools, output_limit)
        endpoint, headers = "local:mock/" + model["profile"], {}
    else:
        body = APIProvider(model).payload(history, tools, output_limit)
        endpoint, headers = connection(model, "[REDACTED]")
    return {"method": "LOCAL" if model["provider"] == "mock" else "POST", "endpoint": endpoint,
            "headers": headers, "body": body, "body_sha256": digest(body),
            "credential_values_recorded": False}


def list_models(provider, key, endpoint=None, transport=http_json):
    if provider not in {"openai", "openai-compatible", "anthropic", "gemini"}:
        raise ArenaError("This protocol has no model catalog")
    if not key:
        raise ArenaError("Configure an API key to load models")
    spec = {"provider":provider, "model":"unused"}
    if endpoint:
        spec["endpoint"] = endpoint
    url, headers = connection(spec, key)
    parsed = parse.urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ArenaError("Use an HTTPS endpoint without credentials or query parameters")
    if provider == "gemini":
        base = url.rsplit("/models/", 1)[0] + "/models"
    else:
        suffix = "/messages" if provider == "anthropic" else "/chat/completions"
        if not url.endswith(suffix):
            raise ArenaError("Nonstandard endpoint path; enter the model ID manually")
        base = url[:-len(suffix)] + "/models"
    models, cursor = {}, None
    for _ in range(50):
        params = ({"pageSize":100} if provider == "gemini" else {"limit":100} if provider == "anthropic" else {})
        if cursor:
            params["pageToken" if provider == "gemini" else "after_id"] = cursor
        raw, _ = transport(base + ("?" + parse.urlencode(params) if params else ""), None, headers, 30)
        for row in raw.get("models" if provider == "gemini" else "data", []):
            if provider == "gemini" and "generateContent" not in row.get("supportedGenerationMethods", []):
                continue
            identifier = row.get("name") if provider == "gemini" else row.get("id")
            if isinstance(identifier, str):
                models[identifier] = {"id": identifier, "name": row.get("displayName", row.get("display_name", identifier))}
        previous = cursor
        cursor = raw.get("nextPageToken") if provider == "gemini" else raw.get("last_id") if raw.get("has_more") else None
        if not cursor:
            return {"models": sorted(models.values(), key=lambda row: row["id"]), "truncated": False}
        if cursor == previous:
            raise ArenaError("Model catalog pagination did not advance")
    return {"models": sorted(models.values(), key=lambda row: row["id"]), "truncated": True}
