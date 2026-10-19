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

## Automatic optimization

Select **Automatic optimization** and an analyst participant. The analyst reviews
the target's trajectory and chooses its own diagnosis and changes to the system
prompt, reference documents or registered tool selection. No fixed edit categories
are assigned. Tool implementation requests remain reports for human review.

Each candidate is evaluated with fresh target conversations. Validity, paired
combat scores, convergence and target token penalties determine whether it replaces
the best candidate. Laya diagnostics never enter this decision.

The search organizes attempts in two ways:

- **Exploitation** starts from the best measured candidate.
- **Exploration** may start from another valid archived candidate, including a
  previously rejected one, to explore a different hypothesis. With no alternative
  yet, it starts from the best candidate and asks for a different hypothesis.

The default exploration probability is 20%. Choices use the saved search seed and
attempt number. The analyst receives recent attempts and a bounded excerpt from
the latest rejected trajectory. It remains free to choose what to modify. There
is no Q table, diagnostic state classifier or model weight training in new studies.
Old frozen studies retain their original search protocol on resume; fork to use
the current optimizer.

Candidate diffs identify the actual starting candidate. Acceptance compares the
result against the best candidate, even when exploration started elsewhere.
**Optimization progress** shows objective values, strategy, starting candidate and
keep/reject decisions. The default candidate limit is empty. Plateau stopping
waits at least 10 attempts and stops after 8 attempts without an accepted objective
improvement greater than 0.001. Counts, threshold and exploration are configurable.
Disable plateau stopping for manual stopping; spending limits still apply.

## Independent Laya diagnostics

Install into Arena's environment:

```powershell
.\.venv\Scripts\python.exe -m pip install ".[calibration]"
```

```bash
.venv/bin/python -m pip install '.[calibration]'
```

Laya observations are enabled in new configurations and can be disabled. First use
downloads the selected checkpoint from Hugging Face; later runs use cached weights. They run
locally, using readable reasoning only by default. Optional **Analyst summary**
evidence makes a separate factual-summary call, with its usual tokens/costs; that
summary session never receives Laya results. OpenAI encrypted reasoning cannot be
read. Missing reasoning, missing Laya or inference failure saves an unavailable
observation and does not block the optimization.

For each reasoning message, typed `choice` questions assess task understanding,
language/API problems, tool use, response to results, and progress. Each dimension
includes insufficient-evidence/no-visible-problem choices. Full choice probability
distributions are retained and averaged across messages. Long messages use Laya's
window scan; it picks the most-confident window per question. These distributions
are hypotheses, not verified engine findings or calibrated confidence.

Receipts in `trials/NNN/diagnostics/SESSION.json` save all questions, distributions,
per-message answers, input usage, windows, model revision, package version and
inference duration. They are **human-only**: excluded from the analyst prompt,
recent-experience data, objective, candidate acceptance and plateau stopping.
There are no hosted Laya calls. The CPU default leaves GPU memory for Ollama.

**Independent Laya observations** appears alongside **Analyst findings & changes**.
For a proposal, it shows Laya's observations of the proposal's starting candidate,
so you compare diagnoses of the same trajectory. The saved raw records are
inspectable. The analyst is not asked to agree with Laya, and no automatic
agreement judgment is fabricated. A separately selected candidate can still be
inspected through its transcript and saved diagnostic files.

To diagnose an already exported conversation without rerunning its target:

```powershell
.\.venv\Scripts\python.exe -m arena calibrate diagnose-conversation "conversation.json" --out "laya-diagnostic"
```

This saves a human-only receipt in `laya-diagnostic/diagnostics/conversation.json`.
It does not send anything to an analyst or change the original calibration.

The previous Laya scalar-scoring feature remains readable for old studies and
available through retrospective `score-conversation`; new optimization uses combat
results and keeps Laya purely observational.

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
3. In **Automatic optimization**, the analyst reviews that observation, proposes
   prompt/document changes, then the tool evaluates a fresh candidate under the
   same protocol. It keeps or rejects the candidate and continues automatically,
   stopping on an objective plateau, an optional candidate limit or manual stop. The baseline counts as the
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


## Interpreting diagnostics, opponents and proposal checks

A displayed diagnostic percentage is the mean of Laya's per-message class
weights. It is not the fraction of the task understood, a session success rate,
or the probability that code is correct. Documentation-only reasoning messages
have the same weight as a detailed task explanation. Reasoning-only input excludes
compiler results, tool results and code. Long messages use Laya's most-confident
window per question. The model has not been calibrated on Arena conversations.

**Inspect Laya input and per-message results** exposes the saved questions,
reasoning evidence, individual answers, windows and aggregation, including for
older studies. Final compilation is shown separately as a measured engine fact,
not inferred from Laya. A correct final script does not prove no previous errors.

The default opponent panel is `passive`, `single-shot`, `rush`; `turret` and
`human-weapon` are additional selectable references. Saved configurations may use
other subsets. **Fight results for the evaluated candidate** shows the actual
opponents, panel, repetition, round and win/draw/loss counts from recorded fights.
Draws earn half a point, so score is not win rate. Preparation fights are excluded.

New authoring material uses isolated language examples instead of a ready-made
move-and-shoot strategy. The complete feature showcase remains available to humans
under `examples/strategies/feature-showcase`, outside the model documentation corpus.
Old studies retain their frozen copies, including any previous combat examples.

The analyst is explicitly instructed not to insert complete combat implementations
or fully prescribed tactical recipes into prompts/documents. An additional
**experimental Laya proposal check** is optional and disabled by default. It checks
cumulative added material against the initial study, covering successive edits.
All detected risks must be at most 0.2 for approval; any risk at least 0.8 rejects;
intermediate values require review. Unavailable or ambiguous checks never approve
a proposal. The analyst can repair within its configured retry budget; otherwise
the study blocks before evaluating that proposal, preserving completed work and
the proposal draft. This guard is separate from human-only trajectory diagnostics;
its rejection feedback can be sent to the analyst to revise its proposal.

Local spot checks showed false alarms on general workflow instructions and moderate
risk on complete code. This is not a validated detector or a guarantee against
solution leakage. Inspect the stored `guard.json` and `guards/` receipts. The normal
syntax/API examples in documentation remain allowed. Existing material in a study's
initial baseline is not certified by this check.

## Recover the analyst's changes

Calibration writes isolated candidate snapshots, not repository source files.
The default `calibrations/` directory is ignored by Git. For candidate 3, for example:

- `calibrations/STUDY/trials/002/calibration.json`: configuration, including `config.prompt` and reference-document overrides.
- `calibrations/STUDY/trials/002/corpus/`: actual frozen documents used by the target.
- `calibrations/STUDY/proposals/002/proposal.json`: analyst proposal; a blocked proposal can instead have `proposal-draft.json`.

Open the study and candidate, then choose **Download this candidate's learning
material** in its review card, or **Download selected learning material** above
the candidate selector. This downloads a ZIP with:

- `system-prompt.txt`, `tools.json` and a reusable `calibration.json`.
- `docs/` containing documents changed since the study's initial candidate,
  including inherited edits rather than only the last proposal's changes.
- `documents.patch`, generated against the current local repository contents.
- `manifest.json` identifying the candidate, evaluation status and current-best flag.

Exporting a rejected or untested proposal does not certify it as the best version.
The export makes no model calls and applies nothing to the repository. After
extracting the ZIP, inspect its files. To apply its document patch from the
repository root:

```powershell
git apply --check "C:\path\to\export\documents.patch"
git apply "C:\path\to\export\documents.patch"
```

Skip these commands if the patch is empty. The check can fail if repository files
changed after export. The system prompt is exported separately; it does not patch
Python source or change global Arena defaults. Copy it into a new study, or use the
exported configuration through `arena calibrate run` as described in the ZIP README.
