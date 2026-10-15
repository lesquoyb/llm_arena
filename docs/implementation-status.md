# Implementation status

The [original roadmap](cloud-roadmap.md) describes the initial delivery plan.
Current usage is documented in the [README](../README.md), [complete experiment](complete-experiment.md)
and [interface guide](ui.md).

| Area | Implemented |
|---|---|
| Installation | Linux and native Windows bootstrap, pinned toolchains, checksum verification, CI, paths with spaces, stable build archives and strict runtime identity. |
| Storage | Validated manifests, SQLite schema migration 1 to 2, transactional checkpoints, lineage, hashed artifacts, single-writer lock and standalone exports. |
| Tools and MCP | Eight shared tools, pinned MCP SDK, stdio client tests, quotas, path isolation and Java workers without provider keys. |
| Documentation | Corpus index, rules, syntax and example API behavior; pinned signatures and equipment data. Three versioned French experiment prompts remain under `prompts/fr`. |
| Sessions | Mock participants, repair after real diagnostics, preparation tests and replays, missing/invalid submissions, failure profiles and resume. |
| Providers and costs | OpenAI, compatible endpoints, Anthropic and native Gemini; model catalogs, supported seeds, native history, usage/cache accounting, Decimal costs, reservations and uncertain-call handling. |
| G0/G1 | Paired control/feedback branches from the same G0 checkpoint; separate seeds; contemporary and common-panel evaluation. |
| Reports | JSON/CSV/Markdown/HTML, matrices, visible missing results, model aggregates, paired effects, exploratory intervals and cost/performance frontier. |
| Local interface | Participant and competition settings, launch/stop/resume, conversations and requests, source versions/diffs, file viewers, schematic replays, detailed metrics and cross-run comparisons. |

The corpus covers the included examples, not every API behavior. Mock strategies
are predefined scripts. Real-engine integration tests validate local execution;
provider adapters use offline contracts. Live API verification requires explicit
keys, exact models, prices and a spending limit and is excluded from standard CI.

Intervals are exploratory and conditional on the fixed reference panel. They
require at least two complete conversations per model; the one-repetition demo
has no interval. Costs use reported usage rather than confirmed invoices.
Missing usage stays unknown; uncertain calls retain reservations and are not
retried automatically.

Remaining scope: optional new strategy languages, public multiuser hosting,
distributed execution, advanced batch scheduling and opponent-source disclosure
conditions. The optional polyglot runtime is not validated. Check GitHub workflow
results for the commit being used. A saved cloud configuration must be published
through environment settings before it is available to a new environment.
