# Provider concurrency

In a competition, select **Provider limits** in the activity header. Set a maximum
number of simultaneous API requests for each endpoint. All models and repetitions
using that endpoint share the limit. The competition-wide request limit still
applies. Blank removes the endpoint limit.

Local endpoints default to one request at a time. Localhost, IPv4 loopback and IPv6
loopback aliases on the same port share one limit. Remote endpoints have no
additional limit by default. Adjustments take effect during the run; requests
already sent finish normally. These controls are saved for subsequent resumes.

In a conversation, **Pause automatic retries** prevents another automatic attempt
if a provider request fails. It does not cancel a request already sent or discard
files, usage or history. Other conversations continue. **Continue now** remains an
explicit manual retry. **Enable automatic retries** restores the automatic retry
policy; use **Continue now** to retry immediately if the competition has stopped.
The switch applies only to this conversation, not its later-round descendants.
