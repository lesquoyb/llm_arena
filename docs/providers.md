# Providers and spending limits

Supported protocols: OpenAI Chat Completions, Anthropic Messages, native Google
Gemini `generateContent` and explicit OpenAI-compatible endpoints (HTTPS remotely; HTTP on loopback).
The mock provider makes no network requests. CI and demos do not make paid calls.
API contracts are tested using offline fixtures.

## Model configuration

A real model needs an exact ID, key binding and dated USD prices. Output and
input admission limits are optional, except for Anthropic output. This is a template, not an executable manifest:

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

Paid manifests must set `spending.allow_paid_calls=true`. A total spending limit
and per-session input, output and dollar limits may be omitted. If a total
spending limit is configured, it must be positive. Model aliases and commercial prices are not hardcoded.
Verify IDs, supported parameters and prices with the provider.

For local use, copy `.env.example` to `.env` at the repository root and enter
one key per provider:

```dotenv
ARENA_OPENAI_KEY=your_openai_key
ARENA_GROQ_KEY=your_groq_key
ARENA_GEMINI_KEY=your_gemini_key
```

All `arena` commands load this file at startup, including the interface,
calibration workshop and their workers. Set each saved provider's API key
environment variable to the matching name (for example `ARENA_GROQ_KEY`). Restart
the application after editing the file. Loading uses the repository root,
regardless of the terminal's current directory. Existing process environment
variables take priority, including empty values.

Use one `NAME=value` assignment per line; blank lines, `#` comments and simple
single/double quoted values are supported. Values are literal: no shell commands,
variable expansion, escaped quotes or multiline values. `.env` is ignored by Git;
it contains plaintext secrets, so do not share it or include it in exports.
Only `.env.example` belongs in the repository.

You can also supply keys through server environment variables or the UI password field.
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

A live provider smoke test requires explicit keys, exact models, prices and
paid-call authorization. A spending limit is optional. It is not part of standard CI.

## Optional token limits

New profiles have no local input or output token cap by default. Blank fields
are omitted from the configuration. OpenAI, Gemini and compatible APIs then use
their own output defaults and context limits. Anthropic requires `max_tokens`,
so its output cap must be entered explicitly. Existing profiles retain their caps.

Per-call input admission compares serialized UTF-8 request bytes to the configured
bound; it is not an exact tokenizer count. Conversation token caps are optional
and use returned usage. If a total output cap is set, each request is limited to
the remaining allowance. No minimum number of tokens is imposed.

All preparation limits are optional: model calls, tool calls, test matches,
elapsed time, input/output tokens and cost. New UI competitions leave them blank.
A model call is one provider response, including each response after tool results.
A tool call is one requested action, such as writing code or running a test.
Without a limit, preparation continues until submission, an ordinary end of
conversation, a provider failure, or an explicit stop. API context limits and
required request parameters still apply. Resource usage and costs are always recorded.

Paid calls require explicit activation. Conversation and experiment financial
ceilings are optional. With no output cap but a financial ceiling, the runner
reserves the remaining funds while the call is in flight. Without either, its
pending cost is marked unknown. One response can exceed a configured financial
limit; usage is reconciled on receipt and subsequent calls stop when the limit
is exhausted. Unknown outcomes require reconciliation and are never retried blindly.
Existing manifests, demos and profiles retain their explicit limits.

Model catalogs are fetched with the configured key and filtered for known
incompatible endpoints and image/audio/video/embedding models. Excluded IDs and
reasons remain visible. Unknown model IDs are retained; being listed does not
prove tool support or generation access. Loading the catalog makes no generation
request. The searchable list wraps long names and exact IDs.

## Local Ollama

Start Ollama on the same machine as the arena server (`ollama serve` if it is
not already running), and download a model that supports tool calls with
`ollama pull <model>`.

In **Participants**, select **openai-compatible** and enter:

- Full API endpoint: `http://localhost:11434/v1/chat/completions`
- API key: leave blank. The environment-variable name may keep its default.
- Model: click **Load models** or enter the exact installed model name.
- Input/output prices: `0` for local inference.
- Output cap: optional; start with it blank. Increase the timeout if loading or
  running your local model takes longer than 60 seconds (up to 3600 seconds).

Save the participant and add it to a competition. The launch confirmation still
asks you to authorize API calls, including local inference. Tool support depends
on the installed model; listing a model does not guarantee it supports tools.

HTTP is accepted only on loopback (`localhost`, `127.0.0.1`, `[::1]`); remote
addresses require HTTPS. Local OpenAI-compatible servers may run without a key.
Other APIs still require their credential binding. Localhost refers to the machine
running the arena Python server; a cloud/container server does not reach your host
Ollama through its own localhost.

## Inspecting provider output

The journal keeps the full received JSON response and exact outgoing request. In Conversations, reasoning exposed by the provider, tool requests/results, provider-reported MCP/server tools, opaque signatures, alternatives and unknown blocks appear as collapsed rows. Expand a row to fetch its full recorded value. The complete provider response remains available, including fields the viewer does not understand. Valid JSON responses rejected by the provider-specific parser are accessible from the failure record even if no assistant message was created. HTTP errors retain sanitized error information rather than raw error bodies.

This records what the endpoint returns. Hidden internal reasoning cannot be retrieved from token counts, encrypted thinking blocks or signatures. OpenAI Chat Completions often reports reasoning token usage without readable reasoning. Anthropic can return thinking or redacted thinking blocks when enabled for a compatible model. Gemini can return thought summaries when requested; for supported models the participant's Model parameters JSON can include `{"thinking_config":{"includeThoughts":true}}`. Thinking settings and available output depend on the selected model; the viewer does not silently enable them or alter generation parameters. Compatible local servers may expose `reasoning_content` or `reasoning` fields, which are preserved and inspectable.

The Arena only executes its registered tools. An unknown function request is recorded and refused. External tools used inside a provider or proxy are visible only if that endpoint reports them; the journal cannot observe undisclosed remote activity. A provider-reported tool block is not proof that an Arena tool ran. Reasoning tokens are recorded separately in usage and remain part of the billed output according to the protocol's accounting rules.

The OpenAI compatible adapter retains provider-returned `reasoning_content` and
`reasoning` fields on prior assistant messages when sending the next request.
This preserves the reasoning/tool sequence for compatible local servers. The
journal keeps every response independently, including its native fields and raw
response; the conversation viewer loads each response's reasoning separately.

For the web recovery workflow, including **Resolve billing**, see [competition recovery](recovery.md).

## Investigate a slow local model

Improvement rounds start a fresh conversation. Within a preparation session, each request includes its growing history, including documentation pages, tool results and previous replies. Reading the entire API can therefore keep a large amount of text in subsequent requests. Prefer `lookup_api` to retrieve only relevant signatures.

New conversation messages show input/output token counts when reported, request characters, message count, local request setup time and total API response time. The displayed output-token rate divides output tokens by the full response time: it includes input processing, queueing and provider retries, rather than measuring decoder throughput alone. Character counts are not tokenizer counts. Local setup measures request construction and saving its intent, separately from waiting for the provider.

For Ollama, compare `ollama ps` before and during the slowdown. Check CPU/GPU placement and context allocation. Context growth, KV-cache memory pressure, partial CPU offload, prompt reprocessing and other workloads can reduce performance. Reasoning can also consume time beyond the visible answer. Arena cannot infer GPU saturation or actual decoder speed from a compatible API response that does not expose those measurements.

Round fights run as soon as their strategies are submitted and frozen. Improvement strategies can also face the frozen reference panel before other preparations finish. Results are saved immediately and reused on resume. Only the next round waits for the current round to finish; preparation tools expose feedback from previous rounds only. Preparation tests remain separate and do not count toward competition results.

## Requested reasoning effort

OpenAI and compatible profiles have a **Reasoning effort** selector. **Provider default** omits `reasoning_effort`; Arena does not silently select medium or maximum. Explicit values are sent unchanged. Available levels depend on the exact model and endpoint. JSON configurations can specify additional endpoint-specific effort values. In the participant editor, the reasoning selector is authoritative over the JSON field; saved custom values are retained in the selector.

The requested setting appears in the participant list, launch preview and recorded conversation requests. An endpoint may reject or ignore an unsupported setting, so the requested value does not prove the effective effort. An alias such as a Codex model name alone does not establish the API's default or supported levels. Inspect the exact endpoint/model documentation when choosing a level.

Anthropic `thinking` and Gemini `thinking_config` remain provider-specific JSON settings; they are displayed as configured without translating them into OpenAI effort levels. Setting effort does not expose hidden reasoning. Existing competitions retain their frozen participant settings; changing a reusable profile affects new launches, not an already running conversation.

## OpenAI Responses API

GPT-6 model IDs, including `gpt-6.1-sol`, use `/v1/responses` automatically when reasoning effort is not explicitly `none`. A configured endpoint ending in `/chat/completions` is changed to `/responses` on the same server. This retains function tools together with reasoning effort. An explicit `/responses` endpoint also works for other models; compatible servers must implement that protocol.

Responses requests send `reasoning.effort`, flat function-tool definitions and `max_output_tokens` when configured. They use `store: false` and replay only this conversation's output items and tool results. There is no `previous_response_id` or shared remote thread. Encrypted reasoning items are preserved for protocol continuation; they are not readable reasoning. Provider-exposed summaries, text, function calls and unknown output items remain inspectable in the conversation and journal. Input, cached input, output and reasoning token counts are normalized for accounting.

Responses does not support `seed`; it is omitted and a note is attached to each recorded response. The recorded request is authoritative. Explicit `reasoning_effort: none` keeps Chat Completions unless the endpoint explicitly selects Responses. Other models retain their existing Chat Completions behavior.

After a definitive HTTP 400 rejection, update the application and click **Retry conversation**. The saved conversation and other participants' results are retained; reasoning does not need to be disabled for this tools/endpoint incompatibility.

For `gpt-6.1-sol`, the API reports `low`, `medium`, `high` and `xhigh`. Neither `none` nor `minimal` is supported. The editor disables these choices for that exact model and rejects unsupported profile saves before an API call.

A running competition retains its original profile settings. **Retry conversation** now has an effort selector that explicitly overrides the saved effort for that failed conversation. The override is audited, does not rewrite the original configuration or affect other participants, and is inherited by future improvement branches from the recovered conversation. CLI equivalent: `python -m arena experiment retry RUN --session SESSION --reasoning-effort low --allow-updated-runner`. Use `--reasoning-effort provider-default` to explicitly omit an earlier effort setting.

## Ollama memory and context troubleshooting

During generation, run `ollama ps`. Its PROCESSOR column reports model placement,
not instantaneous utilization. `66%/34% CPU/GPU` means CPU offloading is active.
A context of 262144 reserves a large KV cache even before that many prompt tokens
are used. With 8 GB of VRAM, this can force model layers onto CPU. The SIZE column
includes the loaded allocation, so it is not by itself the model weight size.
A growing prompt then increases work per request; message counts alone do not
measure token work. The arena starts a fresh history at each improvement round,
then retains messages within that round.

Create a separate model with a smaller context for a pilot. In PowerShell:

```powershell
@'
FROM code-agent:latest
PARAMETER num_ctx 32768
'@ | Set-Content -Encoding utf8 Modelfile.arena
ollama create code-agent-32k -f Modelfile.arena
ollama stop code-agent:latest
```

Select `code-agent-32k` in a new participant and run a short pilot. Inspect
`ollama ps` again while it generates. A smaller context can improve placement;
full GPU placement is not guaranteed if the weights still do not fit. If needed,
try a smaller model or quantization. Do not treat a context change as the same
benchmark variant. Retain the original model for comparisons.

Check that the chosen context accommodates the real prompts, tool schemas,
tool results and output. Ollama can truncate prompts exceeding its context;
reducing context is not a lossless optimization. Each conversation's **Call
performance** disclosure shows reported input/output tokens, request time and
context message/character counts. The displayed tokens/s divides output tokens
by full request time, including prompt processing, and is not decode-only speed.
Compare calls with similar input/output lengths; total round time also includes
compilation, tests, file writes and checkpoint work.

See https://docs.ollama.com/context-length and https://docs.ollama.com/faq for
context memory, model placement and KV-cache settings. Cache quantization and
Flash Attention may help supported models, but should be recorded as separate
runtime settings when benchmarking.

## Test a saved model

In **Participants**, click **Test API**. Calibration setup and active studies also expose model tests. Each click sends one small request:

- **Connection** caps output at 16 tokens and omits optional generation parameters.
  It checks the key, endpoint and model access; reasoning models may return no
  visible text at this cap.
- **Tools** caps output at 128 tokens, keeps saved generation parameters and asks
  for one small `arena_probe` call. Returned tools are never executed. If no call
  is returned, the result says so rather than claiming tool compatibility.

The tests may incur provider charges. Automatic retries are disabled. Duration,
reported usage/cost and failure diagnostics are saved under
`.arena/ui/model-probes/`, separately from competition and calibration totals.
Keys are resolved from the existing session/environment configuration, never
written to these receipts. Unknown usage or cost stays unknown. Mistral requests
use its `max_tokens` output-cap field.
