# Implementation status

The [original roadmap](cloud-roadmap.md) describes the initial delivery plan.
Current usage is documented in the [README](../README.md), [complete experiment](complete-experiment.md)
and [interface guide](ui.md).

| Area | Implemented |
|---|---|
| Installation | Linux and native Windows bootstrap, pinned toolchains, checksum verification, CI, paths with spaces, stable build archives and strict runtime identity. |
| Storage | Validated manifests, SQLite schema migration 1 to 2, transactional checkpoints, lineage, hashed artifacts, single-writer lock and standalone exports. |
| Tools and MCP | Eight shared tools, pinned MCP SDK, stdio client tests, quotas, path isolation and Java workers without provider keys. |
| Documentation | Corpus index, rules, syntax and example API behavior; pinned signatures and equipment data. Three versioned French experiment prompts remain under `prompts/`. |
| Sessions | Mock participants, repair after real diagnostics, preparation tests and replays, missing/invalid submissions, failure profiles and resume. |
| Providers and costs | OpenAI, compatible endpoints, Anthropic and native Gemini; model catalogs, supported seeds, native history, usage/cache accounting, Decimal costs, reservations and uncertain-call handling. |
| initial/improved strategies | Paired control/feedback branches from the same initial strategy checkpoint; separate seeds; contemporary and common-panel evaluation. |
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

Participant team mode supports 1..maximum team size, per-member code and equipment,
per-member stats, level/slot/allowlist validation, journaled `configure_team`, hashed
`team.json`, per-member analysis and inherited improvement checkpoints. Shared
team mode remains the default. New UI competitions leave all preparation limits
blank; calls, tools, tests, tokens, time and cost remain recorded. Equipment
selectors show the complete pinned catalog and item definitions; field tips and
in-app document readers explain settings. Existing configurations keep their limits.

New competitions default to realistic-v1 stat builds: official base stats and
capital tiers pinned to the official client source. Per-leek base components add bonuses after capital allocation, with level, duplicate
and eight-slot validation. Realistic alteration rules are not modeled. Free mode and legacy scenarios retain raw stat values.
RAM help distinguishes tracked combat-script memory from LLM context and Java heap.
