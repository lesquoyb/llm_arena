# Resume a competition

Click **Resume** to continue interrupted work and retry failed conversations. Saved files, conversation histories, usage counters, submitted strategies and completed matches are retained. **Retry conversation** restricts generation to the selected model's conversation and its dependent rounds.

Application updates no longer require starting over in the web interface. Continuations record the original and current identities in the journal and show a notice in the competition. Documentation remains the frozen copy from the original run. New rounds use the installed prompt and tools, so a continuation across versions should not be treated as an unchanged benchmark. Changes to the game engine, build rules or competition settings still require restoring the original environment or starting a separate run.

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
