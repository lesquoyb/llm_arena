"""Native provider adapters and model catalogs; no implicit paid activation."""
from __future__ import annotations
import json
import os
import re
import time
from urllib import request, error, parse
from .core import ArenaError, digest
from .usage import normalize, cost, effective_pricing
from .endpoints import validate_endpoint, optional_local_key


class ProviderFailure(ArenaError):
    def __init__(self, message, *, uncertain=False, retryable=False, diagnostics=None):
        super().__init__(message)
        self.uncertain, self.retryable = uncertain, retryable
        self.diagnostics = diagnostics or {}


class LocalRedirectHandler(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_endpoint(newurl, allow_query=True)
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if redirected and parse.urlsplit(newurl).netloc != parse.urlsplit(req.full_url).netloc:
            for name in ('Authorization', 'X-api-key', 'X-goog-api-key'):
                redirected.remove_header(name)
        return redirected


def http_json(url, payload, headers, timeout):
    validate_endpoint(url, allow_query=True)
    req = request.Request(url, data=json.dumps(payload).encode() if payload is not None else None,
                          headers=headers, method="POST" if payload is not None else "GET")
    try:
        open_url = (request.build_opener(LocalRedirectHandler()).open
                    if parse.urlsplit(url).scheme == 'http' else request.urlopen)
        with open_url(req, timeout=timeout) as response:
            body = response.read(8_000_001)
            if len(body) > 8_000_000:
                raise ProviderFailure("Provider response exceeded quota", uncertain=True)
            return json.loads(body), response.headers.get("x-request-id") or response.headers.get("request-id")
    except error.HTTPError as exc:
        raise_http_error(exc,url,headers)
    except (error.URLError, TimeoutError, OSError, ValueError) as exc:
        raise ProviderFailure(f"Provider response unavailable ({type(exc).__name__})", uncertain=True) from None


def raise_http_error(exc,url,headers):
    # Extract public validation fields, including proxy/FastAPI error formats.
    try: body = exc.read(16000).decode('utf-8', errors='replace')
    except OSError: body = ''
    def public(value):
        if isinstance(value, str): return value
        if isinstance(value, list): return ' · '.join(public(item) for item in value[:8])
        if isinstance(value, dict):
            parts = []
            for field in ('status', 'type', 'code', 'param', 'message', 'msg', 'detail', 'error', 'errors', 'loc'):
                if field in value:
                    part = public(value[field])
                    if part: parts.append(field + ': ' + part)
            return ' · '.join(parts)
        return str(value) if isinstance(value, (int, float)) else ''
    try: detail = public(json.loads(body))
    except ValueError:
        detail = body.strip() if '<html' not in body.lower() and '<!doctype' not in body.lower() else ''
    for header, value in headers.items():
        if header.lower() in {'authorization', 'x-api-key', 'x-goog-api-key'} and value:
            detail = detail.replace(value, '[REDACTED]').replace(value.removeprefix('Bearer '), '[REDACTED]')
    detail = re.sub(r'(?i)(key|api_key|token)=([^\s&]+)', r'\1=[REDACTED]', detail)[:2000]
    parsed = parse.urlsplit(url)
    diagnostics = {'http_status':exc.code, 'endpoint':parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, '', '')),
                   'request_id':(exc.headers or {}).get('x-request-id') or (exc.headers or {}).get('request-id'),
                   'provider_detail':detail or 'No public error detail was returned by the endpoint'}
    raise ProviderFailure(f"Provider HTTP {exc.code}" + (": " + detail if detail else ""), uncertain=exc.code >= 500,
                          retryable=exc.code == 429, diagnostics=diagnostics) from None


class APIProvider:
    def __init__(self, model, transport=http_json, stream_progress=None):
        self.model, self.transport = model, transport
        self.stream_progress = stream_progress

    def payload(self, history, tools, output_limit):
        result=self._payload(history,tools,output_limit)
        if self.model.get('_stream'):
            result['stream']=True
            from .openai_responses import uses_responses
            if not uses_responses(self.model): result['stream_options']={'include_usage':True}
        return result

    def _payload(self, history, tools, output_limit):
        from .openai_responses import uses_responses, payload as responses_payload
        if uses_responses(self.model):
            return responses_payload(self.model, history, tools, output_limit)
        from .model_content import history_view, message_text, tool_text
        history = history_view(history)
        m = self.model
        if m["provider"] == "gemini":
            return gemini_payload(history, tools, output_limit, m.get("parameters", {}))
        messages = []
        for item in history:
            if item["role"] == "system":
                if m["provider"] != "anthropic":
                    messages.append({"role": "system", "content": item["content"]})
            elif item["role"] == "user":
                messages.append({"role": "user", "content": message_text(item)})
            elif item["role"] == "assistant":
                native = item["native"]
                messages.append(native if m["provider"] == "anthropic" else
                                {k: v for k, v in native.items()
                                 if k in ({"role", "content", "tool_calls", "refusal", "audio", "function_call"}
                                          | ({"reasoning_content", "reasoning"} if m["provider"] == "openai-compatible" else set()))})
            elif item["role"] == "tool":
                content = tool_text(item["result"])
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
            if output_limit is None:
                raise ArenaError("Anthropic requires max_tokens; configure maximum output per call")
            payload.update(max_tokens=output_limit, tools=tools)
            system = "\n\n".join(item["content"] for item in history if item["role"] == "system")
            if system:
                payload["system"] = system
        else:
            if output_limit is not None:
                payload["max_completion_tokens"] = output_limit
            payload.update(tools=[{"type": "function", "function": {"name": t["name"],
                                  "description": t["description"], "parameters": t["input_schema"]}} for t in tools])
        if not tools: payload.pop("tools", None)
        return payload

    def respond(self, history, tools, output_limit):
        m = self.model
        key = os.environ.get(m["api_key_env"])
        if not key and not optional_local_key(m):
            raise ProviderFailure(f"Missing credential binding: {m['api_key_env']}")
        from .openai_responses import uses_responses
        anthropic = m["provider"] == "anthropic"
        endpoint, headers = connection(m, key)
        payload = self.payload(history, tools, output_limit)
        retries = []
        for attempt in range(m.get("max_retries", 0) + 1):
            try:
                if m.get('_stream') and self.stream_progress is not None:
                    from .streaming import stream_json
                    raw,request_id=stream_json(endpoint,payload,headers,m.get('timeout_seconds',60),self.stream_progress)
                else:
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
        elif uses_responses(m):
            from .openai_responses import unpack
            self.last_response = {"raw":raw, "request_id":request_id, "sent_parameters":payload}
            if raw.get('error') or raw.get('status') in {'failed','cancelled'}:
                detail = str(raw.get('error') or raw.get('status'))[:2000]
                if key: detail = detail.replace(key, '[REDACTED]')
                raise ProviderFailure('Responses request failed: ' + detail, uncertain=True)
            native, calls = unpack(raw)
            stop = raw.get('incomplete_details', {}).get('reason') if raw.get('incomplete_details') else raw.get('status')
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
        usage = normalize('openai-responses' if uses_responses(m) else m["provider"], raw.get("usageMetadata") if m["provider"] == "gemini" else raw.get("usage"))
        return {"role": "assistant", "provider": m["provider"], "simulated": False, "native": native,
                "tool_calls": calls, "stop_reason": stop, "usage": usage, "raw": raw,
                "request_id": request_id or raw.get("responseId"), "sent_parameters": payload,
                "request_sha256": digest(payload), "system_fingerprint": raw.get("system_fingerprint"),
                "adapter_notes": (["Responses API does not support seed; configured seed was not sent."] if uses_responses(m) and 'seed' in m.get('parameters', {}) else []),
                "api_protocol": "responses" if uses_responses(m) else "native",
                "model_version": raw.get("modelVersion") or raw.get("model"), "retries": retries,
                "cost_usd": cost(usage, effective_pricing(m)), "cost_status": "calculated_from_reported_usage"}


DEFAULT_ENDPOINTS = {"openai": "https://api.openai.com/v1/chat/completions",
                     "anthropic": "https://api.anthropic.com/v1/messages",
                     "gemini": "https://generativelanguage.googleapis.com/v1beta"}


def connection(model, key):
    provider = model["provider"]
    endpoint = model.get("endpoint") or DEFAULT_ENDPOINTS.get(provider)
    if not endpoint:
        raise ArenaError("An endpoint is required")
    # Some API gateways reject urllib's default Python user agent (Groq: 403/1010).
    headers = {"Content-Type": "application/json", "User-Agent": "LLMArena/1.0"}
    if provider == "gemini":
        endpoint = endpoint.rstrip("/") + "/models/" + parse.quote(model["model"].removeprefix("models/"), safe="") + ":generateContent"
        headers["x-goog-api-key"] = key
    elif provider == "anthropic":
        headers.update({"x-api-key": key, "anthropic-version": "2023-06-01"})
    elif key:
        headers["Authorization"] = "Bearer " + key
    from .openai_responses import endpoint as response_endpoint
    return response_endpoint(model, endpoint), headers


def gemini_payload(history, tools, output_limit, parameters):
    from .model_content import history_view, message_text
    history = history_view(history)
    contents = []
    native_ids = {part["functionCall"].get("id") for item in history if item["role"] == "assistant"
                  for part in item.get("native", {}).get("parts", []) if "functionCall" in part}
    for item in history:
        if item["role"] == "system":
            continue
        if item["role"] == "user":
            parts = [{"text": message_text(item)}]
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
    if output_limit is not None:
        generation["maxOutputTokens"] = output_limit
    payload = {"contents": contents, "generationConfig": generation,
            "tools": [{"functionDeclarations": [{"name":t["name"], "description":t["description"],
                       "parametersJsonSchema":t["input_schema"]} for t in tools]}]}
    system = "\n\n".join(item["content"] for item in history if item["role"] == "system")
    if system:
        payload["systemInstruction"] = {"parts": [{"text": system}]}
    if not tools: payload.pop("tools", None)
    return payload


def request_snapshot(model, history, tools, output_limit):
    if model["provider"] == "mock":
        from .providers import MockProvider
        body = MockProvider(model["profile"]).payload(history, tools, output_limit)
        endpoint, headers = "local:mock/" + model["profile"], {}
    else:
        body = APIProvider(model).payload(history, tools, output_limit)
        credential = (None if optional_local_key(model) and not os.environ.get(model.get("api_key_env", "")) else "[REDACTED]")
        endpoint, headers = connection(model, credential)
    return {"method": "LOCAL" if model["provider"] == "mock" else "POST", "endpoint": endpoint,
            "headers": headers, "body": body, "body_sha256": digest(body),
            "credential_values_recorded": False}


def model_exclusion(provider, row, identifier):
    """Exclude known non-chat catalogs; absence of metadata is not proof of support."""
    name = identifier.lower().removeprefix("models/")
    if provider == "gemini" and "generateContent" not in row.get("supportedGenerationMethods", []):
        return "No text generation endpoint"
    capabilities = row.get("capabilities", {})
    if isinstance(capabilities, dict) and any(capabilities.get(k) is False for k in ("chat", "tools", "function_calling")):
        return "Chat or tool calls explicitly unsupported"
    if re.search(r"(?:^|[-/_.])(embedding\w*|embed\w*|imagen\w*|image\w*|dall-e|whisper\w*|tts|transcrib\w*|moderation\w*|realtime|audio|veo\w*|video|music\w*|aqa)(?:$|[-/_.])", name):
        return "Image, audio, video, embedding or other non-agent model"
    if provider == "openai":
        if "search-preview" in name or "codex" in name or name.startswith(("o1-preview", "o1-mini")):
            return "Chat tool protocol not supported by this adapter"
        if name in {"babbage-002", "davinci-002", "gpt-3.5-turbo-instruct"} or "-instruct-" in name:
            return "Legacy completion endpoint"
        if re.match(r"(?:o1-pro|o3-pro|gpt-5(?:\.\d+)?-pro|.*deep-research)(?:$|-)", name):
            return "Requires an endpoint not implemented by this adapter"
    return None


def list_models(provider, key, endpoint=None, transport=http_json):
    if provider not in {"openai", "openai-compatible", "anthropic", "gemini"}:
        raise ArenaError("This protocol has no model catalog")
    spec = {"provider":provider, "model":"unused"}
    if endpoint:
        spec["endpoint"] = endpoint
    validate_endpoint(endpoint or DEFAULT_ENDPOINTS.get(provider, ""))
    if not key and not optional_local_key(spec):
        raise ArenaError("Configure an API key to load models")
    url, headers = connection(spec, key)
    validate_endpoint(url)
    if provider == "gemini":
        base = url.rsplit("/models/", 1)[0] + "/models"
    else:
        suffix = "/messages" if provider == "anthropic" else "/responses" if url.endswith("/responses") else "/chat/completions"
        if not url.endswith(suffix):
            raise ArenaError("Nonstandard endpoint path; enter the model ID manually")
        base = url[:-len(suffix)] + "/models"
    models, excluded, cursor = {}, {}, None
    def result(truncated):
        return {"models": sorted(models.values(), key=lambda row: row["id"]),
                "excluded": sorted(excluded.values(), key=lambda row: row["id"]),
                "truncated": truncated}
    for _ in range(50):
        params = ({"pageSize":100} if provider == "gemini" else {"limit":100} if provider == "anthropic" else {})
        if cursor:
            params["pageToken" if provider == "gemini" else "after_id"] = cursor
        raw, _ = transport(base + ("?" + parse.urlencode(params) if params else ""), None, headers, 30)
        for row in raw.get("models" if provider == "gemini" else "data", []):
            identifier = row.get("name") if provider == "gemini" else row.get("id")
            if isinstance(identifier, str):
                reason = model_exclusion(provider, row, identifier)
                if reason:
                    excluded[identifier] = {"id": identifier, "reason": reason}
                else:
                    models[identifier] = {"id": identifier, "name": row.get("displayName", row.get("display_name", identifier)),
                                          "availability": "Listed by API; chat and tool support unverified"}
        previous = cursor
        cursor = raw.get("nextPageToken") if provider == "gemini" else raw.get("last_id") if raw.get("has_more") else None
        if not cursor:
            return result(False)
        if cursor == previous:
            raise ArenaError("Model catalog pagination did not advance")
    return result(True)
