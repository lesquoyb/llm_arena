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
