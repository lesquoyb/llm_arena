# Multi-model benchmark plan

## Separate questions before spending tokens

Use a campaign with several linked experiments, rather than one growing league.
A participant ID identifies a complete configuration, not merely a model name.
For example, `qwen-temp0`, `qwen-temp07` and `gpt-low` are distinct variants.
Each variant has a pinned provider/model revision where available, parameters,
reasoning effort, prompt, enabled tools and resource policy. Keep aliases such as
`latest` out of a long campaign when a dated model is available.

| Experiment | Question | Suggested first design |
| --- | --- | --- |
| Pipeline pilot | Do providers, tools, stats and exports work? | 3 varied models, 1 replicate, 1 round; exclude from final analysis |
| Initial quality | Which configurations produce good strategies from scratch? | All variants, 3 independent conversations each, 1 round |
| Feedback ablation | Does feedback improve strategies, and for which models? | 4–6 representative variants, 5 independent initial strategies each, 2 total rounds, both tracks |
| Longer improvement | Does improvement continue or plateau? | Extend a separate exploratory subset to 3–5 rounds; calibration supports plateau stopping against built-in opponents |
| Parameter confirmation | Does an apparent parameter gain replicate? | Top configurations, 5–10 new conversations each, new evaluation seeds |

These are starting allocations, not a statistical power calculation. Use pilot
variation to choose the final replicate count. Reuse no pilot results as a
confirmatory test set. Define selection, stopping rules and primary metrics
before the confirmatory run. Keep rejected configurations and failed attempts.

Three repeats estimate variability poorly; one repeat cannot establish a stable
model ranking. Fresh conversations are not necessarily independent samples:
with temperature zero and a fixed supported model seed they may produce exactly
the same script. The classic competition repetition setting does not offset
model seeds automatically. For a variability study, omit a fixed provider seed
or explicitly block several seeds as separate profiles and preserve that mapping
in your campaign table. Use the same seed blocks across parameter conditions
where the provider supports it. OpenAI Responses and Anthropic do not provide
that seed control; do not treat a configured-but-ignored seed as effective.
Calibration does offset supported configured seeds by replicate. Exact repeats
are useful for reproducibility checks, but identical scripts do not create new
independent strategic evidence. The independent experimental units are generated strategies,
not individual fights, turns or the two starting sides of the same seed.

## Batches versus one competition

Prepare initial strategies in batches of about 5–10 variants. This keeps provider
outages and long preparations manageable. Use exactly the same scenario, prompt,
tools, stopping policy and engine. A profile may share an exact model ID with
other profiles while differing in parameters. Allocate provider calls over time
so model/provider/date are not confounded; record timestamps and API incidents.

Scores from different opponent pools are not comparable as a global ranking.
After preparation, copy every frozen submission and evaluate the combined pool
without any LLM calls. Use both starting sides and fresh evaluation seeds. Never
pick the best replicate of each model and present it as its typical performance.
Do not silently omit strategies that failed compilation or submission.

The current frozen tournament scheduler runs a complete round robin. With P
scripts and S seeds, that is P(P-1)S non-mirror fights. For 30 variants × 3
replicates and 5 seeds, P=90: 40,050 fights. These cost engine time, not LLM tokens.
A candidate-versus-fixed-anchor scheduler would reduce this to roughly 2PAS for A
anchors, but that scheduling mode is not currently exposed by the bundle helper.
Use a smaller screening seed set, then increase independent seeds for the final
comparison if engine time becomes substantial. A stable set of diverse reference
strategies is preferable to comparing scores from unrelated pools.

Start with Simple duel. Treat Dream team and AI-built teams as separate strata,
not interchangeable observations. AI-built teams measure build design plus
coding/tactics; shared teams isolate strategy programming more closely.

## Feedback deserves a separate experiment

A single model can validate the pipeline or answer a question about that model.
It cannot establish a general feedback effect: tool use, debugging, reasoning
and context handling vary between models. Select a documented, diverse subset
(for example two local models, two hosted models, and two reasoning settings),
including more than only the initial winners.

Both arms must start from the same frozen initial script, then use fresh
conversations. Pair feedback minus no-feedback within each initial replicate.
Evaluate both arms on the same fixed opponents and seeds. Report the paired
score gain, validity rate, cost increment and token increment. Longer tracks
remain separate after their first split; R3 feedback and no-feedback no longer
start from the same R2 script, so distinguish cumulative trajectory effects from
one-round effects.

Current classic competitions require both improvement conditions when enabled;
there is no single-track selector. The standalone calibration workshop instead
runs a single feedback trajectory against its registered built-in panel. It does
not yet accept an arbitrary library of other LLMs' frozen scripts as that panel.
A frozen strategy can enter a separate source-only tournament now. Importing it
as the starting checkpoint of a new editable LLM competition is not implemented.

## Observations to retain

| Level | Fields and interpretation |
| --- | --- |
| Variant | Provider, exact model, requested parameters/effort/seed, prompt/tool version, pricing date; note unsupported parameters and model aliases |
| Preparation | Replicate, round, condition, submission and compilation status, provider failures/retries, model/tool calls, preparation tests, elapsed wall time |
| Resources | Reported input/output, cached input, reasoning tokens, known/unknown usage, calculated USD, reservations; cache and reasoning are subsets, not extra totals |
| Strategy | Frozen files, team/equipment, source identity, origin run/session/round; archive all replicates |
| Fight | Unique fight ID, both sources, scenario, seed, starting side, opponent, result, turns, engine failure and elapsed time |
| Combat | Operations, error/operation-limit events, damage, healing, movement and actions where recorded; raw outcomes retain per-turn/per-leek detail |
| Improvement | Round scores, paired feedback gain, cost/token increments, convergence and regressions against own prior versions |

API response time includes input processing, network/queue time and generation.
Output tokens / response time is an end-to-end throughput proxy, not pure decode
speed or time-to-first-token. Do not compare local throughput without recording
hardware, quantization, context configuration and concurrency. Missing measurements
stay unknown. Freeze prices for the campaign, and retain the raw token counts.

Primary results should show validity/submission rate and score against a common
panel, with uncertainty across independent replicates. Also show API availability
separately. Retry temporary provider outages without regenerating healthy peers.
Do not turn an engine outage into a model loss. If a composite end-to-end score
counts model-produced invalid/missing strategies as zero, predeclare that rule and
show its components; current conditional tournament scores alone do not do this.

Bootstrap complete conversations/strategy replicates with all their paired
fixtures, not individual fights as if independent. Use paired resampling for
parameter and feedback comparisons when their design is paired. Report effect
sizes and intervals, not only a sorted league table. Identify exploratory
multiple comparisons; confirm chosen settings with fresh data. Keep separate
score-versus-cost/token plots rather than hiding trade-offs in one opaque score.

## Reuse frozen strategies without more model calls

To collect all frozen initial submissions from several batches automatically:

```powershell
.\.venv\Scripts\python.exe scripts/freeze_benchmark.py --initial-from runs/batch-a runs/batch-b --out benchmarks/final --seeds 701,702,703,704,705
.\.venv\Scripts\python.exe -m arena tournament benchmarks/final/manifest.json --out runs/final-frozen
```

`omissions.json` records initial sessions with no submission instead of silently
losing their failures. Invalid frozen code remains included. Keep sessions.csv
from the generation runs to analyze submission/validity rates.

For selected rounds, tracks or a specific subset, save a UTF-8 JSON selection,
for example `selection.json` at repository root:

```json
[
  {"run":"runs/batch-a", "session":"qwen-temp0-r0", "id":"qwen-temp0-rep1"},
  {"run":"runs/batch-b", "session":"gpt-low-r0", "id":"gpt-low-rep1"}
]
```

Run paths are relative to the selection file. Select all intended replicates;
include different round/track submissions as distinct IDs if that is the question.
The helper verifies archived source hashes, copies the complete submission with
team.json and retains origin metadata. It requires the same scenario across
selections. It creates a new folder and never changes the original runs.

```powershell
.\.venv\Scripts\python.exe scripts/freeze_benchmark.py selection.json --out benchmarks/final --seeds 701,702,703,704,705
.\.venv\Scripts\python.exe -m arena tournament benchmarks/final/manifest.json --out runs/final-frozen
```

The second command invokes only the engine, not model providers. Use fresh seeds
for generalization; replaying development seeds answers an in-sample question.
The interface can browse the resulting run, but there is no reusable static
participant type in the participant-profile editor yet.

## Export for analysis

Existing improvement runs already contain analysis.csv. It contains repeated
panel rows, so do not sum its costs or tokens across panels. The general helper
below also works for initial-only runs and combines multiple directories:

```powershell
.\.venv\Scripts\python.exe scripts/export_benchmark.py runs/batch-a runs/batch-b runs/final-frozen --out exports/campaign-01
```

Or omit positional directories to export all non-export-copy runs under `runs/`:

```powershell
.\.venv\Scripts\python.exe scripts/export_benchmark.py --runs runs --out exports/campaign-01
```

The output folder must be new. Tables use UTF-8 CSV with a BOM for Excel:

- `sessions.csv`: one generated conversation, configuration, resources and outcome.
- `fights.csv`: one participant appearance per fight side. Count distinct fight_id
  for unique fights; do not mistake two appearances for two fights.
- `scores.csv`: one participant × category × stage, with wins/draws/losses/failures.
  Training is separate; reference results count only the candidate. Mirrors are
  excluded from these scores.
- `runs.json`: run IDs mapped to original directories and engine/scenario identities.
- `README.txt`: table grain and missing-value conventions.

Blank cells mean unknown, not zero. Join within a run by run_id and participant;
join frozen strategies to their generation sessions with source_run_id and
source_session. Never sum
session costs/tokens after joining them onto multiple fights. Frozen-only
participants appear in fights/scores with origin metadata and have no new LLM
session or API cost. Category/stage distinguishes current tournaments, reference
panels and preparation tests. Do not average these categories together. All
per-turn raw outcomes remain in the run directories; the flat export currently
contains available team metrics, not a separate per-turn table.

## Historical sparring and limits

Currently test accepts passive or opponent_entrypoint from the model's own
workspace. A model can copy its own earlier script and test a revision against
it. It cannot test against another participant's earlier script. Past-fight tools
read its earlier tournament logs; they do not launch new fights.

A future historical-opponent tool should expose immutable opponent handles and
black-box fights, never opposing source or private logs, and only completed
rounds. This is an explicit experimental treatment: otherwise a nominal
no-feedback arm gains outcome feedback through unlimited historical sparring.
Record those tests separately, keep evaluation seeds held out and use the same
access policy for every model being compared. Offline evaluation can already
compare arbitrary frozen versions without giving that access to the target.

When optional preparation limits exist, they are explained at the start and
consumption/remaining resources are included in tool receipts. On exhaustion,
Arena already freezes the latest saved files without needing submit. They may
still be incomplete or invalid: saving a complete strategy early is important.
In unlimited sessions explicit submit remains required. submit is a tool call;
it can share a model response with writes, so it does not necessarily cost an
extra model API call.

For the main quality benchmark, prefer measuring resources and reporting their
trade-offs. A fixed-resource arm is a different question and should be labeled.
A call limit is not a token limit: one response can request multiple tools and
providers differ in batching. A token limit is not a context-window limit:
input usage includes repeated history and cached tokens over all requests.

Input admission uses a conservative serialized-request bound, not an exact
provider tokenizer. Output caps can cut a response or tool argument mid-stream;
there is no universally exact, graceful token stop across providers. Keep the
last successfully saved files, mark truncation/invalid outputs, and do not claim
the last version was validated. Unknown provider usage cannot support an exact
remaining-token estimate. A later last-valid-checkpoint mode would be a separate
submission policy; it is not the current latest-saved-file policy.

### Export results for analysis

Use **More > Download match results CSV** for individual matches, or
**More > Download results CSV** on a competition for participant results by
match category and stage, joined to the cost of generating each strategy.
For several competitions, use `scripts/export_benchmark.py` as described above.
The export contains:

- `results.csv`: wins, draws, losses, score, generation cost, tokens, preparation
  time and message counts for each participant/category/stage.
- `fights.csv`: match results and metrics, with one row per side. Count distinct
  `fight_id` values for the number of fights.
- `sessions.csv`: one preparation conversation per row, suitable for summing
  costs and tokens without counting them repeatedly across match stages.

`calls` counts provider calls; `messages` counts stored conversation messages,
including tool responses, with separate columns by role. `wall_seconds` is
recorded preparation time, including model and tool work, rather than the elapsed
calendar time of the whole competition. Unknown measurements remain blank.
Generation costs repeat across result stages: do not sum these repeated costs.
Include source competitions when exporting frozen strategies to join their
original generation costs. Static matches do not incur new model charges.

OpenAI Responses usage can distinguish regular input, cache reads and cache
writes. Cache writes are included in total input, not added to it. GPT-6.1 uses
a default cache-write price of 1.25 times the configured input price unless an
explicit cache-creation price is configured. Archived response receipts containing
`cache_write_tokens` are repriced in the UI and CSV without changing original
journals or spending checkpoints. This display correction does not retroactively
change historical budget decisions. Other provider pricing premiums still need
to be reflected in the configured prices.

Cache-write pricing reference: https://developers.openai.com/api/docs/models/gpt-6.1-sol
