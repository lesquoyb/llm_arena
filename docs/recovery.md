# Resume a competition

Click **Resume** to continue interrupted work and retry failed conversations. Saved files, conversation histories, usage counters, submitted strategies and completed matches are retained. **Retry conversation** restricts generation to the selected model's conversation and its dependent rounds.

Application updates no longer require starting over in the web interface. Continuations record the original and current identities in the journal and show a notice in the competition. Documentation remains the frozen copy from the original run. New rounds use the installed prompt and tools, so a continuation across versions should not be treated as an unchanged benchmark. Changes to the game engine, build rules or competition settings still require restoring the original environment or starting a separate run.

## A request exceeds the context window

An API test with a short prompt can succeed while the saved conversation is too
large. Errors such as `invalid_request_prompt_too_long` and
`context_length_exceeded` are context failures, not rate limits.

**Resume** and **Retry conversation** detect these recorded errors and restart
request context with the original instructions and a continuation message. The
model is told to inspect its current saved files and continue the same round.
Previous tool exchanges remain in the conversation and journal, but are no longer
resent to the provider. Saved files, team configuration, submissions and completed
matches stay intact. Usage counters and preparation limits are not reset. This is
an audited context restart, not a semantic summary of the omitted exchanges.

The recovery panel shows the latest provider error and keeps its open/closed state
during live refresh. The resume preview lists which conversations will retry and
why others are blocked. Failed requests without a response do not consume the
completed model-call quota; immutable request attempt IDs are still retained.

## Resolve request billing

An interrupted external request may have been charged even if no usable response was received. Missing usage metadata can also leave a received response waiting for reconciliation.

1. Stop the competition if it is still running.
2. Click **Resolve billing** in the competition header or its conversation. **Resume** also lists unresolved requests.
3. Check the provider's usage dashboard. Enter the additional cost for this unresolved request and a verification note. Enter zero for a confirmed uncharged request or a local provider.
4. Click **Record and unlock**, then **Resume** or **Retry conversation**.

A saved response continues with its pending tools. An unknown response is requested again and may incur a new charge. Recorded charges are added once; usage counters and earlier costs are preserved. Reconciliation does not invent missing token counts.

Command line: `python -m arena experiment resume RUN_DIRECTORY --allow-updated-runner` allows an audited application update. Without the flag, identity checks remain strict. Billing reconciliation is available through the web interface.

## A failed participant keeps its place

Available fights in the current round can finish while other participants prepare. If an initial participant fails to submit, improvement rounds do not start with a smaller pool. The job ends in **Waiting for recovery**, retaining every submission and completed fight. The same round barrier applies to subsequent improvement rounds. Use **Retry conversation** or **Resume** to recover the participant.

HTTP failure details include the actual request endpoint, HTTP status, provider/proxy validation fields and a request ID when supplied. Open **Provider error details** in the failed conversation. A bare `Bad Request` does not identify an unsupported field; endpoint-specific diagnostics are needed before changing request settings.

For an old run showing only `branch_unavailable`, open its conversation and use **Copy provider diagnostics**. The diagnostic follows the parent chain to the original attempt and includes its endpoint, model, public failure and request structure. It excludes authorization headers, prompt contents and source contents. **Open original failure** opens that ancestor conversation. Copying diagnostics makes no provider request and incurs no API charge.

## Isolate a generic Responses HTTP 400

In a failed Responses conversation, **Test API** sends one explicitly authorized diagnostic using the key already configured in this server session. Choose **Minimal prompt + one simple tool** first; then, if accepted, compare **Current prompt + full arena tool set**. Minimal mode omits the legacy `reasoning.encrypted_content` include; current mode preserves the normal adapter request. Both retain the saved effective model/effort and use an output cap of 1,024 tokens.

This is a billed request: reservations, spending/token/call limits and usage accounting apply. It never executes returned tools or changes saved conversation history, files or submissions. Diagnostics have separate call/cost counters and journal events. An ambiguous transport failure keeps its reservation for billing reconciliation. Probe results are included in **Copy provider diagnostics**.

A rejected minimal request points to the provider/model/request options rather than the competition scenario or complex tool set. An accepted minimal request and rejected full request narrow the problem to differences in the complete request; acceptance alone does not prove an entire tool conversation works.

## Parallel requests

When parallel preparation is enabled, Stop stops scheduling new calls/tools and
waits for already dispatched provider requests to return or reach their configured
timeout. Their replies, costs and pending tool calls are saved before stopping;
Resume consumes them without sending the same request again. A forced process
termination can leave several unknown requests, each requiring reconciliation.
The default concurrency remains one. Loopback models sharing a server port are
prepared sequentially even if the competition allows more concurrent requests.

## Change participants without restarting

Stop the competition, then open **More → Edit participants**. Uncheck an unavailable
model to withdraw it, and check existing profiles to add participants or reactivate
withdrawn ones. Save, then **Resume** the same competition. At least one participant
must remain active. The catalog contains reusable profiles, including reference
strategies; add a reference profile from Participants first if needed. Built-in
references adapt to the selected scenario when added, preserving their code. Shared
rosters use the competition equipment; open-team scenarios get a validated fixed
reference team. Strategies imported from a previous run retain their original
scenario requirement.

Withdrawn participants keep their histories, usage, frozen submissions and completed
fights. They no longer block progression or start further preparation. Unplayed
fixtures involving their submitted versions are cancelled, not recorded as defeats.
Reactivation makes those fixtures eligible again. New participants prepare missing
rounds and play new fixtures; existing models do not regenerate frozen strategies.
Older rounds can gain fights, but feedback already sent stays unchanged. Comparisons
therefore describe the opponents actually faced, rather than a constant pool.

Each change is an immutable `participants_updated` journal event containing the
profile snapshots, active/withdrawn IDs, revision and round. The original experiment
configuration stays unchanged. Changes require the competition to be stopped; exports
are read-only. Previously uncertain charges remain in accounting after withdrawal.

### Freeze preparation while keeping a strategy in the pool

In **Edit participants**, expand **Freeze preparation** for a participant with a
submitted strategy. Freeze **No feedback**, **With feedback**, or both. Resume the
competition. Future preparation in that track reuses its preceding submitted source
and team without making model calls. A pending, unsubmitted preparation also reuses
its parent submission; its edits and prior charges stay recorded. Resolve any unknown
in-flight request before freezing that track.

Frozen versions continue fighting. `track_frozen` records identify the exact source
session, submission hash and participant-change revision. Each reused conversation
is labelled **Manually frozen**, and exports identify its source. Unchecking the
option enables preparation in subsequent rounds; already submitted versions remain
immutable.

## Inspect observed errors

The competition **Errors** tab reads existing journal receipts and fight metrics.
Filter by model and round to inspect tool-call error rates, unknown tools, invalid
arguments, compilation checks and compiler error counts, invalid team drafts, runtime
errors and provider failures. Warnings are excluded from compiler error counts.
Repeated attempts count separately. Tool failures can also represent missing files,
access restrictions or operational problems, so these are not a direct hallucination
score. API and malformed-response incidents are listed separately from tool errors.

Recent incidents link to their conversation and give the journal event number. The
full receipts remain in the Journal. **Download errors CSV** exports one summary row
per conversation; this table is also available as `errors.csv` in benchmark exports.
Runtime execution errors across tournament/reference fights and preparation tests are
separate counters. Models' written claims are not counted as executed errors.

### Interrupted requests with zero configured prices

If all configured input, output, cached-input and cache-write rates are zero, an
unknown request outcome cannot add a monetary charge in arena accounting.
Timeouts and unreadable responses therefore remain retryable provider failures,
without a billing reconciliation step. Missing token usage remains unknown.
A successful free response with missing usage can still execute its saved tools.

Resume also resolves older zero-price interruptions automatically, with a saved
`billing_reconciled` event marked `automatic: true`. Existing successful
submissions, usage counters and completed fights are retained. This rule uses
explicit rates, not the current displayed cost: a paid request with a displayed
cost of zero can still require review, as can a nonzero outstanding reservation.

### Resume phases and browser disconnects

Resume verifies saved work before preparing new requests. Activity distinguishes
checking completed fights, preparing a provider request, waiting for its response
and executing a fight. An unchanged completed opponent pool is checked once per
runner invocation; adding a submitted entrant schedules its missing fixtures.

A browser cancelling a page request can close its HTTP socket while the server is
writing. This does not cancel the competition worker. Disconnected GET and POST
clients are handled without attempting to send a second error response.

### Automatic context-window recovery

A definite provider context-length rejection, including Mistral's
`invalid_request_prompt_too_long` / code `3059`, now rebases and retries during
execution. No Retry click is needed for a new overflow. The new request keeps the
original instructions and scenario, feedback permissions, saved files and team.
Earlier exchanges remain in the journal, but are omitted from the request; the
model is told to read its current files and continue the same preparation round.
Usage and preparation budgets do not reset. The `context_rebased` event records
that recovery was automatic.

There is at most one automatic rebase between accepted responses. If the reduced
request is still too large, or there are no tool/model exchanges to remove, the
conversation stops with an explicit recovery explanation rather than looping.
Existing paused conversations can be continued with Resume or Retry; their
previously implemented manual recovery remains supported.

### Provider interruptions and submission reminders

A timeout, unreadable response, or response lacking a normal completion reason
does not count as the model ending its turn. Transport failures, reconciliation
and retries preserve both submission-reminder counters, including the consecutive
streak. Retrying the same conversation never grants a fresh reminder allowance. A retry after an interruption can add a neutral provider-recovery notice
without a submission warning. Missing completion reasons and token-truncated
responses preserve their received output and usage, and pause for retry rather
than automatically freezing saved code.

Only an explicit normal end-turn without tool calls triggers a submission reminder.
The reminder records its originating model call and completion reason. The
existing fallback for repeated confirmed model stops still applies; configured
preparation-budget exhaustion continues to follow its separate snapshot policy.

Resuming a target in calibration also preserves its reminder counters. If an
outstanding `interrupted_stop_streak` marker from the previous implementation
records an incorrectly cleared streak, its saved value is restored with a
`submission_counter_restored` audit event. Historical messages are retained.
