# Recovering a stalled conversation

Every conversation without a frozen submission has **Pause conversation** and
**Resume / send message** controls. Pausing interrupts its response socket when
available and prevents further calls and tools. Connecting requests can take up
to their connection timeout to stop. Other conversations and fights continue.

Resume keeps the existing files, history, usage and remaining budgets. An optional
message is added before the next model request, after any already-received tools
are completed. Resuming an active request queues the message until its receipt is
consumed; it does not send a second copy of that request.

The provider inactivity threshold defaults to five minutes. An interrupted free
request can recover automatically. Retryable provider failures and completed turns
that repeatedly produce no files or submission are retried after two minutes,
then four minutes, then five minutes (three automatic recoveries maximum).
Manual pauses, automatic-retry pauses and exhausted budgets suppress automatic
requests. External requests whose billing is unknown still require reconciliation;
their cost and token usage are never silently replaced with zero.

A frozen submission cannot be edited by these controls. **Restart preparation**
remains available for eligible failed preparations and archives the earlier attempt.

## Independent fight scheduling

During preparation, a dedicated fight coordinator discovers committed frozen
submissions every half second. It runs tournament and reference batches while the
conversation coordinator handles replies, tools, pauses and recovery messages.
Neither coordinator waits for a progress callback from the other. The existing
round boundary still waits for the round's preparation and evaluation work.

The fight coordinator owns its SQLite connection and verification caches. It
only appends engine events; session checkpoints remain owned by the conversation
coordinator. Completed fight artifacts remain immutable and are reused on resume.
Engine activity is written separately so conversation updates cannot overwrite
the visible fight-worker status.

The run log emits provider dispatch/completion/receipt events and a heartbeat
every 30 seconds. If the conversation coordinator stops advancing for two minutes,
thread stacks are added to the log to identify its wait. Apply runner updates by
stopping the existing worker, pulling the branch, restarting the web server and
resuming the existing competition. Existing workers keep their loaded code.

## Slow feedback tools

Feedback listings filter the frozen calendar by trajectory and selected round
before opening results. Only the requested page is read; inspecting one fight
opens only that result. Archives without a calendar keep the legacy reader.
Prior submission lookups use the compact session metadata index, with a fallback
for archives created before that index existed.

Each session's `tool-progress.json` and run log identify reservation, execution,
result preparation and publication separately. Timings include SQLite calls,
SQLite wall/CPU time and SQLite errors. SQLite wall time includes lock waits and
database I/O, so a large value alone does not establish a lock problem. Provider
receipts also record how long a completed response waited for the coordinator.
