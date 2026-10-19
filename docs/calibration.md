# Prompt calibration

This separate workshop compares system prompts, available Arena tools and model
parameters. It uses the installed engine and saved participant profiles, but
keeps its studies separate from competitions. It does not train model weights.

## Start

After the normal [installation](../README.md#install-and-start), run from the
repository:

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m arena calibrate serve --open
```

Linux:

```bash
.venv/bin/python -m arena calibrate serve --open
```

The workshop listens on `http://127.0.0.1:8766`. No Node.js is required.
Generated studies are saved under `calibrations/`, which Git ignores. Use
`--out PATH` to choose another directory. Keep that directory to retain prompts,
conversations, code, evaluation records and costs.

## Manual workflow

1. Select the target participant. Saved participants come from the main Arena
   interface. Provider configuration also accepts an unsaved model. For Ollama,
   use the OpenAI compatible protocol and its local HTTP endpoint.
2. Edit the initial system prompt and enable the tools the model should have.
   `write_file` and `submit` are required. Disabled tools are rejected by the
   dispatcher, including when the model guesses a tool name.
3. Choose a scenario, fixed opponents, seeds, replicates and round settings.
   The included opponents are deterministic scripted strategies: `passive`,
   `single-shot` and `rush`. Scenario JSON remains editable.
4. Run the calibration. Each replicate starts independently. Each strategy round uses a fresh conversation with the system prompt, scenario, explicit phase instruction and a short previous-round training summary; previous model messages are not resent. The previous submitted code stays in the workspace. The model
   prepares and submits one strategy per round. That frozen strategy plays both
   sides against the fixed panel; only then can the model revise it next round.
5. Inspect the score chart and each round's conversation, journal, files and
   fights. Reasoning means the reasoning returned by the provider, when exposed.
   Expand messages to load their full contents; read/write exchanges include
   recorded text or diffs. Preparation tests are separate from evaluation.
6. Choose **Edit selected prompt** to start a fresh study from a candidate.
   The original study stays unchanged and becomes the comparison baseline.
   Deltas appear only when the model, scenario, panels, round settings and runner
   match. **Inspect prompt** shows the actual native system message.

Mock participants let you test the workflow offline. Their fixed responses do
not measure learning or real model quality. Mock token usage is not measured.

## Reopen and export a previous calibration

Start `python -m arena calibrate serve --open` from the same repository. The study
list reads the saved `calibrations/` directory, including studies created through
the CLI. Click the study name, select a **Candidate**, then a **Round or analyst
session**. **Conversation**, **Journal**, **Saved files** and **Fights** inspect the
saved records without resuming the run or making model calls. Avoid **Resume** if
you only want to inspect it.

If you used another output location, pass its parent collection directory:

```powershell
.\.venv\Scripts\python.exe -m arena calibrate serve --out "D:\experiments\calibrations" --open
```

Each immediate child containing `input.json` or `study.json` is a study. Keep the
whole study folder; the SQLite journal alone does not contain every code/replay
artifact. Files in `calibrations/` are local and are not pushed to GitHub.

**Export conversation JSON** downloads the selected session's complete committed
conversation, including system/user prompts, model outputs, tool calls/results,
timestamps, and a separate readable-reasoning array. It exports every page, not
just the currently visible messages. Duplicated transport requests are excluded.
**Inspect available reasoning** shows message/character counts and the actual
readable reasoning without inference. Character counts are not token estimates.

To measure what Laya actually reads from that export, install `.[calibration]`
and run (adjust the downloaded filename):

```powershell
.\.venv\Scripts\python.exe -m arena calibrate score-conversation "conversation.json" --out "laya-review"
```

The command runs local Laya on readable reasoning only, reports score, input
tokens, token windows and inference duration, and saves the detailed receipt in
`laya-review/judge/conversation.json`. It makes no target/analyst calls, runs no
fights and leaves the original study unchanged. Different exports need separate
review output directories. OpenAI encrypted reasoning cannot be scored this way.

## Scores, convergence and held-out fights

Each win earns 1 point, each draw 0.5 and each loss 0. Scores average the two
starting sides and all opponents/seeds. A script that fails compilation forfeits
its evaluation and scores zero. Its diagnostics return to the next round.

Training results return to the target in readable text. Enabled past-fight tools
can inspect any completed earlier training round in the same replicate and candidate. Omit `round` in `list_past_fights` for the previous round, or pass a round number from `available_rounds`. Every response identifies the round and provides the matching `read_submitted_file` call. Source-version tools can read your own earlier submissions by round, without exposing results.
Validation and audit records remain inaccessible through those tools.
Optional fights against earlier versions show whether the model beats its own
older strategies; they do not change the fixed-panel training score.

A plateau requires the minimum number of rounds, no improvement greater than
`min_improvement` for `patience` rounds, and a stable recent score range within
that threshold. A falling or oscillating score is not automatically a plateau.
The **Round stopping rule** selects one of three modes:

- **Stop on plateau**: stop when the stability condition is met, or at the maximum.
- **Run the specified number of rounds**: ignore early plateaus and complete the
  requested number. The maximum is not restricted to 100 rounds.
- **Continue until I press Stop**: no round limit or plateau stop. This is available
  for manual prompt studies with one replicate. Completed rounds remain visible
  and can be inspected or resumed after Stop. The final audit runs when a finite
  candidate finishes; an interrupted open-ended study has no final audit.

In JSON, set `stop_on_plateau` to `false` for a fixed count, and additionally
`max_rounds` to `null` for manual stopping. Automatic analyst/grid selection needs
finite trials so it can compare candidates and move to the next proposal.

For finite trials, `max_rounds` is a hard stop; the interface reports **Not reached** when no plateau
was established. Convergence is the earliest round after which training scores
stay within the threshold of the final score. A capped trial receives a
convergence penalty rather than claiming convergence.

Training, validation and audit seeds must be disjoint. Validation scores select
candidates; audit fights run only after choosing the winner. Audit scores never
feed prompt editing or selection. Replicates use independent conversations;
when a model seed is configured, its replicate offset stays the same across
candidates. Provider seeds do not guarantee identical remote outputs.

## Automatic prompt editing

Select **Reinforcement learning** and an analyst participant. The analyst
receives the incumbent prompt, permitted tools, training trajectory and bounded
conversation evidence. It proposes a replacement prompt, a set of existing registered tools and a rationale. It can also report missing tools, unclear documentation or inadequate error feedback through structured `tool_requests`.
It cannot change opponents, evaluation seeds or the target model. Validation match details and audit results are omitted from its evidence. The controller and analyst receive aggregate learning rewards from prior revisions. Evidence truncation is explicit;
full source records remain available for human inspection.

The automatic workflow now uses a **contextual bandit**, a one-step reinforcement
learning controller. It learns which editing action to ask the analyst to take:
language/API guidance, strategy, tools, compression or exploration. Context is the
incumbent's validity and performance band. The analyst edits the prompt and/or
reference documents; the target runs a fresh observation; the measured reward
updates the selected action value:

```text
reward = candidate utility - incumbent utility  # combat/conversation modes
# Hybrid: combat gain first, Laya gain for equivalent combat scores.
Q(context, action) += learning_rate * (reward - Q(context, action))
```

Invalid code receives reward -1; restoring validity receives +1. All action types
are explored at least once in a context, then epsilon-greedy selection balances
learned values and random exploration. The seed, action, reward, learned values,
accepted/rejected candidates and recent failed hypotheses are saved. Resume does
not apply rewards twice. This trains the editing controller, not the target or
analyst model weights; it is not PPO or a fine-tuning pipeline.

The default has **no candidate limit** (`optimizer.max_trials: null`). It stops
on a reward plateau after at least 10 editing episodes, with no reward improvement
over 0.001 in the latest 8 episodes and every action explored in the current
context. These thresholds, learning rate and exploration probability are editable.
Disable **Stop on reward plateau** to run until manually stopped. An optional
candidate limit includes the baseline; the study spending ceiling still applies.
A plateau is a practical stopping rule, not proof of an optimum.

The best candidate remains protected by validity and paired score checks. Utility
uses evaluation score, optional Laya reward, convergence penalty and token penalty.
All trials remain inspectable even when the incumbent does not change. Old saved
configurations without `rl` keep the original rejection/patience search.

**Learning progress** shows rewards, editing actions, exploration and learned
values. **Review change** shows rationale, diffs and tool requests. Select a
proposal to inspect the analyst conversation. Recommendations do not modify
executable tools automatically.

## Optional local Laya reward

Install into the same virtual environment as Arena:

```powershell
.\.venv\Scripts\python.exe -m pip install ".[calibration]"
```

```bash
.venv/bin/python -m pip install '.[calibration]'
```

This pins the Python Laya package. Its first use downloads model weights from
Hugging Face. The selected checkpoint, resolved model revision, package version,
rubric, evidence fingerprint, scores and elapsed inference time are recorded.
CPU is the default, leaving GPU memory for Ollama. There are no hosted Laya calls.

Choose a reward source:

- **Combat score**: actual matches, with no Laya inference.
- **Combat score + Laya tie-break**: Laya breaks combat-score ties within the
  configured tolerance. A judge preference cannot override a combat regression
  outside that tolerance.
- **Laya conversation score**: no automatic training/validation/audit fights.
  Compilation still runs; invalid code cannot replace valid code. Preparation
  tests explicitly requested by the target can still run. This mode measures a
  reasoning-quality proxy, not combat performance or held-out validation.

Laya receives either **readable reasoning only**, excluding code/tool payloads,
or a **factual trajectory summary** written by the configured analyst. Summary
mode adds real analyst calls with their usual tokens/costs, also for local
providers. Those calls have their own journal under `judge_summaries/`. OpenAI's
encrypted reasoning is never decoded or scored. If no readable reasoning is
available, scoring blocks with an explanation: choose summary mode or combat
scoring instead of inventing a score.

The ordinal rubric rates unproductive, partially productive or productive
reasoning. Laya returns the expected level in [0, 2], divided by 2 for [0, 1].
Only provider-exposed reasoning is available; hidden internal reasoning is never reconstructed. Every reasoning message is scanned with `predict_long`; Laya selects the most
confident window within each message, and Arena averages messages. Summary mode
scores the summary the same way. This avoids silent long-input truncation, but
is not a holistic code review or an explanation-generating judge. Scores can
reward plausible reasoning that is wrong. Compare them against actual fights
before relying on them as the sole learning signal.

**Inspect Laya scores and rubric** exposes the per-message scores, windows,
confidence and aggregation. Full receipts are in each trial's `judge/` directory.
Analyst summaries are retained next to their journals. Local Laya inference uses
no provider output tokens; its elapsed time is recorded separately.

## Parameter sweeps

Select **Model parameter sweep** and supply a JSON grid, for example:

```json
{ "temperature": [0, 0.3, 0.7], "top_p": [0.9, 1] }
```

The runner evaluates the Cartesian combinations deterministically, bounded by
`max_trials`. Supported grid keys are `temperature`, `top_p` and `seed`, subject
to provider capabilities. No analyst is required. The same selection and audit
rules apply. Repeated runs and several seeds help distinguish a useful change
from sampling noise; a single higher score is not statistical proof.

## Costs, resuming and command line

API calls, including local servers, require explicit activation. Credentials can
come from saved participant settings, environment variables or the optional
password fields. Password fields are passed to worker memory, not study JSON.
Do not put API keys inside provider JSON.

Quick diagnosis defaults to 8 model calls, 20 tool calls and 4 preparation fights
per round. No token limit is set. Clear the limits for unlimited preparation. A
study spending ceiling is also available. The ceiling includes target and analyst
calls across candidates. Costs use participant pricing; unknown token usage
stays unknown rather than becoming zero. Analyst and target usage are recorded
separately. The convergence objective uses target tokens, not analyst tokens.

**Stop** preserves completed work. **Resume** uses the exact frozen configuration
and verifies engine, corpus and artifacts. Known retryable provider failures can
resume; an uncertain in-flight paid request blocks rather than risking an
unnoticed duplicate charge. Fork a study to change its configuration.

Use **Export configuration** for a UTF-8 JSON configuration, then:

```bash
python -m arena calibrate run calibration.json --out calibrations/manual-01
python -m arena calibrate run calibration.json --out calibrations/automatic-01 --automatic
```

Repeat the same command to resume. `python -m arena calibrate example` prints an
offline example configuration. In old Windows PowerShell, prefer browser export
to shell redirection, which can produce UTF-16 files.

The workshop reuses Arena's registered tool contracts and permission checks.
It does not connect arbitrary external MCP servers. Adding a new tool requires
implementing and registering it in Arena before enabling it in a calibration.

## Tool improvement reports

The analyst can produce two independent outputs: an executable candidate (a new
prompt and selection of registered tools), and recommendations for development.
A recommendation has `kind` (`new_tool`, `tool_change`, `documentation` or
`error_feedback`), `problem` and `proposed_change`; optional fields are `tool`,
`evidence` (session/round/message references) and `expected_benefit`.

Choose **Tool improvement report** in the study inspector to read recommendations
from all proposals, including candidates that were rejected. **Review change**
also includes that candidate's requests. Files are retained in
`proposals/NNN/tool-requests.json` and `tool-requests.md`. Reports are advisory:
they do not install tools, execute code or automatically alter the benchmark.
The analyst may keep the prompt unchanged and report a tool limitation instead.

A coding agent could implement a recommendation in a separate branch, followed
by review and a fresh study. This integration is not implemented. Changing a
tool changes the experimental environment; start a new study rather than treating
that change as a prompt-only candidate or silently modifying a running study.

For a first automatic run, select a real target and an analyst, keep the fixed
opponents, choose finite rounds (for example 8), and set 3 candidates including
the baseline. Two replicates give a first check of variability. Enable the API
calls checkbox and check the pricing and spending fields. To optimize final
score alone, set both convergence and token penalties to zero; add them later
if faster convergence or lower token use is part of the objective. A trial can
still finish at its maximum without establishing a plateau.

### Optimize the reference documents too

The **Reference documents** editor changes the Markdown learning material served
by `read_docs`, including `authoring.md`, component guidance, the language cheat
sheet and tutorials. Selecting a document preserves edits to the previous one.
Fork an existing candidate to carry its prompt and document edits into a new
manual study. Exporting the configuration includes `reference_documents`, a map
of paths to complete replacement text. Unlisted paths keep their original text.

The automatic analyst receives the reference texts as well as the prompt and
training trajectory. It can propose document replacements using the same
`reference_documents` field. The existing paired candidate evaluation accepts or
rejects the prompt/document package together. Candidate review exposes unified
diffs for each changed document. Every trial freezes and fingerprints its own
corpus; rejected candidates never edit the repository or the incumbent corpus.
Generated API/equipment catalogs, rule JSON, opponents, seeds and executable tools
are excluded from document editing. Tool changes remain structured requests for
human review. The analyst receives additional input tokens for these documents;
target usage counts only documents it actually reads.

Static opponent IDs now include `turret` and `human-weapon` alongside `passive`,
`single-shot` and `rush`. These are useful reference behaviors, not an established
ordering of human ability. `human-weapon` ports one Apache-2.0 weapon-selection
heuristic; it does not reproduce the upstream AI's full team and chip logic.

### Follow a study and find the analyst's conclusions

Preparation budgets have separate model-call, tool-call and preparation-fight
fields. A short-trial preset fills 8 calls, 20 tools and 4 fights. The first target
message contains these limits and instructions to save a complete strategy early.
Tool results return the remaining budget. The inspection view displays the same
counters; an empty field means unlimited.

After launch, setup collapses to make room for study progress. In automatic mode,
the analyst runs after a complete candidate trajectory, including its configured
rounds and replicates or plateau stopping. Finishing one conversation does not
necessarily finish that trajectory. Manual mode never runs an analyst by itself.

**Analyst findings & changes** shows the proposal rationale, system-prompt and
Markdown-document diffs, tool requests, validation metrics and the kept/rejected
decision. The analyst proposes changes; the paired validation objective makes the
decision. Candidate review buttons select another review. **Inspect analyst
conversation** opens its complete recorded exchanges. Raw review data remains
available for copying.

The conversation has a bounded scrolling area, Markdown text formatting and
**Top**, **Latest** and **Follow live** controls. Streaming is enabled by default
for OpenAI Chat Completions, OpenAI Responses and compatible Ollama servers in
calibration. Exposed reasoning is separately expandable; encrypted or unexposed
reasoning cannot be displayed as readable thoughts. Partial tool arguments are
previewed but never executed until the provider completes its response. Final
usage and the received stream events are retained in the normal response archive.
Interrupted streams keep a bounded partial preview and require reconciliation
when the remote outcome is uncertain; they are not silently repeated.

Anthropic and Gemini currently update after each complete response. Disable
**Stream responses** for a compatible endpoint that does not implement streaming.
The live display uses a small, throttled worker snapshot rather than rewriting
the full conversation for every token. Archived messages, token usage and cost
accounting are committed through the normal journal after completion.


### Script rounds, repetitions and prompt optimization iterations

These are three separate loops:

1. A **script round** prepares, freezes and evaluates a strategy. Later rounds
   inherit its script and training feedback. The system prompt and reference
   documents remain unchanged within that candidate, while the round instruction
   and feedback change.
2. A **fresh repetition** restarts that candidate from scratch, without the scripts
   or feedback of other repetitions. It repeats the complete configured sequence
   of script rounds.
3. In **Reinforcement learning**, the analyst reviews that observation, proposes
   prompt/document changes, then the tool evaluates a fresh candidate under the
   same protocol. It keeps or rejects the candidate and continues automatically,
   stopping on a reward plateau, an optional candidate limit or manual stop. The baseline counts as the
   first candidate. A rejected proposal does not replace the incumbent.

The new default is **Quick diagnosis**: one script round, one repetition and a
short preparation budget. The analyst can propose a change immediately after
that observation. This is useful for correcting the starting instructions. The
convergence penalty is zero because a single round cannot establish convergence.
Use **Learning curve** later to evaluate up to ten script-improvement rounds per
prompt, with plateau stopping. Increase repetitions when checking robustness.

For example, 10 rounds and 1 repetition means one candidate with ten successive
script versions under the same system prompt, followed by an analyst proposal.
It does not mean ten revisions of the system prompt. Five prompt candidates with
those settings can require up to 50 target preparations, plus analyst calls.

Previously saved studies retain their frozen settings. Fork/edit their
configuration and choose Quick diagnosis to start the shorter protocol; changing
the defaults does not alter an ongoing study. Manual editing remains available
and does not call the analyst or start the next candidate automatically.
