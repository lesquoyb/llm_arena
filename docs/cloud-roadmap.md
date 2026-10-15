# Original implementation roadmap

This is a shortened English version of the handoff dated 13 October 2026,
starting from local commit `f6ddac5`. It records the original requirements,
not the current backlog. Many items below have since been delivered. See
[implementation status](implementation-status.md), the [README](../README.md)
and the [full guide](complete-experiment.md) for current behavior and commands.

## Goal and decisions

Deliver an auditable pipeline from configuration to independent conversations,
submissions, initial strategy, paired control/feedback branches, improved strategy, common reference evaluation
and reports. Build and validate offline with mocks before enabling paid providers.
Missing keys must not prevent development. Paid runs require exact models and
an explicit spending limit.

| Decision | Original requirement |
|---|---|
| Strategy language | LeekScript 4 only; Python/JavaScript later, no TypeScript. |
| Orchestrator | Python, reusing the existing engine and tournament runner. |
| Engine | Official generator at a pinned commit, not the website frontend. |
| Teams | Initially 2-vs-2 with identical stats/equipment and a shared entry point. |
| Preparation | The same versioned local documents and tools for every participant. |
| Repetitions | Independent conversations with the same prompt and resources. |
| Evaluation | All pairs, both sides for each seed, including repetitions of one model. |
| Mirrors | Separate diagnostics, excluded from the ranked score. |
| Improvement | Paired branches from the same initial strategy history and code, differing only in feedback. |
| Opponent code | Hidden in the main condition; disclosure could be a separate experiment. |
| Ranking | Matrices and descriptive scores first; Elo optional. |
| Initial interface | CLI and exported reports; the local web UI was added later. |

Model counts, repetition counts, turn limits, tokens and dollars are configurable.
Example budgets in this plan were not authorization for spending.

## Initial state and constraints

The initial runner already built the engine, analyzed strategies, ran symmetric
matches and round-robin tournaments, froze sources, exported signatures and
resumed completed match records. The original Windows verification had 11 passing
tests and 18 demo matches. Linux had not yet been checked. Demo strategies were
handwritten controls, not model outputs.

Keep these pins and semantics:

- Generator `b99a174dd938260d9e47b2e65a208cb32230e26e` and LeekScript
  `8152f399faf7b418bbc5b2216d755c3822cda23b`.
- JDK 25 and Gradle 9.3.1; the upstream wrapper is too old.
- Winners 0/1 and draw -1; replay teams 1/2.
- Duration can reach `max_turns + 1` at the turn limit.
- Operations derive from cores; do not use the ignored upstream example
  `max_operations_per_entity` field.
- Elapsed timings are not CPU timings. Polyglot safeguards are not LeekScript budgets.
- Resume must reject runtime/platform changes rather than silently merging them.

The initial gaps included provider orchestration, MCP, accounting, transactional
journals, OS writer locks, recursive fingerprints, output quotas and stronger
artifact checks. A separate Java process and heap limit were not a complete OS sandbox.

## Code map

| Module | Responsibility |
|---|---|
| `arena/core.py` | Validation, scenarios, source hashing and copies. |
| `arena/engine.py` | Build, runtime identity, Java workers and API export. |
| `arena/tournament.py` | Scheduling, resume, records and reports. |
| `arena/cli.py` | Public commands. |
| `engine/ArenaMain.java` | Generator adapter, include resolver and metrics. |
| `engine/leekscript.init.gradle` | Exclude the unused native polyglot binary. |
| `engine.lock.json` | Pinned tools and source commits. |
| `examples/tournament.json` | Twelve ranked matches and six mirrors. |
| `tests/test_arena.py` | Protocol and real-engine checks. |
| `docs/leekscript-v1/` | Pinned signatures and equipment reference. |

Later modules add experiments, preparation, providers, usage, analysis, exporting
and the `arena_web` interface. Scientific identity and runtime provenance remain separate.

## Delivery requirements

| Area | Required behavior and acceptance evidence |
|---|---|
| A: Portable build | Clean Linux build without local Windows files; real CI; 18 completed control matches; stable replay checks; resume without recalculation. Preserve source pins and verify downloaded tools. |
| B: Durable storage | Versioned manifests, SQLite transactions and migrations, stable IDs and lineage, hashed disk artifacts, atomic writes, OS writer lock and standalone exports. Interrupt critical steps, reject changed sources/configurations and refuse a second writer. |
| C: Preparation/MCP | Shared `list_files`, `read_file`, `write_file`, `read_docs`, `analyze`, `test`, `read_replay`, `submit`; bounded reads, quotas and isolated paths. Direct and MCP calls must agree. Validate with a real stdio client and real engine tests. |
| D: Corpus/prompts | Versioned index, rules, map/distance/visibility, stats/equipment, syntax/state/includes, example API behavior and source attribution. Verify examples in the pinned engine and mount identical hashed material for every participant. |
| E: Offline agent loop | Save initial prompts/settings; reserve and record call intents; save responses and usage before tools; validate/execute tool calls in order; freeze the final state. Cover repair, invalid/absent code, malformed tools, empty responses, budget exhaustion, rate limits, timeouts and interruption. Demonstrate the whole pipeline with mocks and real matches. |
| F: Providers/accounting | Exact model IDs, real supported parameters, tools, native continuation fields, output/time limits, typed failures and bounded retries. Record raw/normalized usage and dated prices. Reserve conservative global/session cost bounds; missing usage stays unknown. Unknown remote state keeps a reservation and blocks blind retries. Offline fixtures must cover calculations and errors; live smoke tests require explicit paid configuration. |
| G: Paired improvement | Separate preparation/feedback/final seeds; no held-out tool access or opponent source disclosure. Clone initial strategy code/history into equal-budget control and feedback branches. Preserve native context and lineage. Compare improved strategy on common frozen initial strategy/fixed opponents, separately from contemporary standings. Verify the whole initial/improved strategies cycle offline. |
| H: Analysis | Standalone Markdown/HTML and JSON/CSV; matrices, validity, missingness, errors, resource use, generation/model/scenario scores, paired effects and cost/performance curves. Equal-weight conversations; exploratory intervals respect pairs and fixtures. Unknown costs must not become zero in rankings. Totals must be traceable to artifacts. |

The session identity is `(model, repetition, generation, condition)` plus lineage.
Keep entities for experiments, sessions, calls, submissions, matches, usage and
feedback. States distinguish submitted, budget exhaustion, generation failure,
provider unavailability and billing reconciliation. Development interruption is
not automatically a model failure.

At budget exhaustion or a final message, freeze the last saved state rather than
choosing the best trial manually. Missing entry points remain `no_submission`.
Infrastructure retries use retained attempt directories. Replaying native history
must not silently replace a branch with a new conversation or summary.

Track actual experiment spend separately from hypothetical independent trajectory
costs so shared initial strategy calls are not charged twice. Preserve input/cache/output and
reasoning fields according to each provider contract. Limits may be best effort
when strict billing bounds are unavailable.

## Delivery order and completion criteria

1. Portable build, real integration tests and control tournament.
2. Durable sessions, preparation tools, corpus and MCP.
3. Complete offline multi-session experiment, budgets and resume.
4. One full provider adapter, then another protocol and a configurable compatible endpoint.
5. Paired initial/improved strategies evaluation and auditable cost/performance reports.

Keep existing commands working, add behavioral checks and document actual commands
and limitations at each stage. A completed implementation must run the entire
offline workflow from a clean checkout and make real adapters testable without
changing the core. A scientific multi-model benchmark still requires selected
models, keys, prices, repetitions and a spending limit.

The original deferred scope included new languages, a rich web UI, public hosting,
distributed execution, opponent code disclosure and advanced batching. The local
web UI was subsequently implemented. Other deferred work must be assessed from
current code and status rather than this historical plan.
