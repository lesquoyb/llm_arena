# Providers and spending limits

Supported protocols: OpenAI Chat Completions, Anthropic Messages, native Google
Gemini `generateContent` and explicit OpenAI-compatible HTTPS endpoints.
The mock provider makes no network requests. CI and demos do not make paid calls.
API contracts are tested using offline fixtures.

## Model configuration

A real model needs an exact ID, key binding, output and admission limits, and
dated USD prices. This is a template, not an executable manifest:

```json
{
  "id": "participant",
  "provider": "openai",
  "model": "EXACT_MODEL_ID",
  "api_key_env": "ARENA_OPENAI_KEY",
  "max_input_tokens_per_call": 150000,
  "max_output_tokens": 12000,
  "timeout_seconds": 60,
  "max_retries": 1,
  "parameters": {"seed": 0},
  "pricing": {
    "date": "YYYY-MM-DD",
    "currency": "USD",
    "input_per_million": "OFFICIAL_PRICE",
    "output_per_million": "OFFICIAL_PRICE"
  }
}
```

Use `anthropic` with `ARENA_ANTHROPIC_KEY`, or `gemini` with `ARENA_GEMINI_KEY`.
Anthropic does not accept a seed. Gemini accepts IDs with or without the
`models/` prefix. A custom Gemini endpoint is an API root such as
`https://generativelanguage.googleapis.com/v1beta`.
OpenAI-compatible providers require a full endpoint, such as
`https://example.test/v1/chat/completions`, and Bearer authentication.
Embedded credentials and query parameters in endpoints are rejected.

Paid manifests must set `spending.allow_paid_calls=true`, a positive total
spending limit and per-session input, output and dollar limits. Missing settings
fail validation before calls. Model aliases and commercial prices are not hardcoded.
Verify IDs, supported parameters and prices with the provider.

Supply keys through server environment variables or the UI password field.
UI-entered keys stay in server memory and are not written to configurations.
In cloud settings, bind secrets to `api.openai.com`, `api.anthropic.com`,
`generativelanguage.googleapis.com` or the configured compatible host.
Use `ARENA_` variable names. Do not put keys in manifests, prompts or sources.

## Usage, costs and resume

Before a paid call, SQLite records an intent and reserves a conservative cost
bound. Limits apply per session and globally; an OS lock excludes a second
writer. UTF-8 request size and configured token bounds control admission.
These bounds are best effort across tokenizers and providers, not universal
billing guarantees. Decimal costs use returned usage and dated prices; they
are not confirmed invoices.

OpenAI prompt usage includes cache. Anthropic total input combines ordinary,
cache-read and cache-creation input. Gemini prompt usage includes cache;
`candidatesTokenCount + thoughtsTokenCount` gives billable output. OpenAI
reasoning tokens are already part of completion usage and are not added twice.
Unavailable usage stays `null`. Optional cache prices fall back to the ordinary
input price when omitted; ambiguous usage does not become zero.

Only an explicit HTTP 429 is retried, up to `max_retries` (0 to 3). Timeouts
after send, HTTP 5xx, malformed responses and unknown usage keep the reservation
and mark `needs_reconciliation`. Resume does not silently repeat that payment.
Check request IDs, logs and provider billing. No unsupported recovery or
idempotency guarantee is assumed.

Native continuation fields are retained: OpenAI tool calls, Anthropic tool-use
and thinking/signature blocks, and Gemini parts including `thoughtSignature`.
Improvement branches replay full copies of their parent history without replacing it
with a summary.

## Catalogs, seeds and request records

**Load models** uses GET `/v1/models` for OpenAI and Anthropic and GET
`/v1beta/models` for Gemini, with pagination. Gemini omits models without
`generateContent`. Compatible servers use the `/models` path corresponding to
their `/chat/completions` endpoint. Manual entry remains available when listing
is unsupported. Catalogs do not supply prices or prove tool compatibility.
Listing models does not start a generation.

New OpenAI and Gemini UI profiles default to seed 0. It is stored in
`parameters.seed` and sent in the native request. Existing profiles are not
changed automatically. Clear the seed field to omit it. Compatible server
support varies; Anthropic Messages exposes no seed and validation rejects it.
Some OpenAI models also reject seeds; omit the field rather than assuming
it is ignored.

A fixed seed is a reproducibility aid, not a guarantee. Compare all messages,
tools, parameters and backend/model versions. An identical system prompt alone
cannot establish or rule out context leakage. Adapters construct each request
from that session history, without shared mutable conversation memory. Paired
improved strategy branches intentionally inherit initial strategy context.

Each new call intent records the endpoint, full body and canonical JSON SHA-256
before execution. Authentication header values are redacted. Responses also
retain the request and available returned model version or OpenAI
`system_fingerprint`. Mock participants use the same
`respond(history, tools, output_limit)` interface and record their local requests.
Fixed controls supplied as `.leek` files do not have generation prompts.
Old archives are not rewritten to invent missing request records.

Official contract sources checked on 15 October 2026:

- [OpenAI request types and seed behavior](https://github.com/openai/openai-python/blob/main/src/openai/types/chat/completion_create_params.py).
- [Anthropic Messages request types](https://github.com/anthropics/anthropic-sdk-python/blob/main/src/anthropic/types/message_create_params.py).
- [Google GenerateContentConfig and seed behavior](https://github.com/googleapis/python-genai/blob/main/google/genai/types.py).

A live provider smoke test requires explicit keys, exact models, prices and a
spending limit. It is not part of standard CI.

## Optional token limits

New profiles have no local input or output token cap by default. Blank fields
are omitted from the configuration. OpenAI, Gemini and compatible APIs then use
their own output defaults and context limits. Anthropic requires `max_tokens`,
so its output cap must be entered explicitly. Existing profiles retain their caps.

Per-call input admission compares serialized UTF-8 request bytes to the configured
bound; it is not an exact tokenizer count. Conversation token caps are optional
and use returned usage. If a total output cap is set, each request is limited to
the remaining allowance. No minimum number of tokens is imposed.

Financial budgets remain required for paid calls. With no output cap, the runner
reserves all remaining funds while the call is in flight. Its cost is not bounded
in advance: one response may exceed the remaining financial budget. Usage is
reconciled on receipt and subsequent calls stop when the budget is exhausted.
Unknown outcomes keep the reservation and require reconciliation.

Model catalogs are fetched with the configured key and filtered for known
incompatible endpoints and image/audio/video/embedding models. Excluded IDs and
reasons remain visible. Unknown model IDs are retained; being listed does not
prove tool support or generation access. Loading the catalog makes no generation
request. The searchable list wraps long names and exact IDs.
