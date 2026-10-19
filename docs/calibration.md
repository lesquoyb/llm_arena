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

Select **Automatic prompt editing** and an analyst participant. The analyst
receives the incumbent prompt, permitted tools, training trajectory and bounded
conversation evidence. It proposes a replacement prompt, a set of existing registered tools and a rationale. It can also report missing tools, unclear documentation or inadequate error feedback through structured `tool_requests`.
It cannot change opponents, evaluation seeds or the target model. Validation and
audit results are omitted from its evidence. Evidence truncation is explicit;
full source records remain available for human inspection.

The search is a `(1+1)` elitist algorithm: evaluate a baseline, propose one
candidate from the accepted incumbent, evaluate it with fresh conversations,
then keep or reject it. The utility is:

```text
mean validation score
  - round_penalty * mean convergence round
  - token_penalty_per_million * mean target tokens / 1,000,000
```

A candidate must remain within `score_tolerance` of the incumbent for every
paired replicate and improve utility. An invalid candidate cannot replace a
valid incumbent. A score gain can therefore trade against convergence speed or
token use; set the two penalties to zero to optimize score alone. Token penalties
apply only to measured usage, and candidates with incomparable usage are not
ranked on fabricated token counts. All accepted and rejected trials are retained.

`max_trials` includes the baseline. Search `patience` stops after that many
consecutive rejections. Round patience is a separate setting. Analyst
`editor_retries` controls repairs of malformed proposals; these are real calls
and count toward costs. **Review change** shows the rationale, prompt diff and
tool/parameter changes. Select a proposal in the candidate menu to inspect the
analyst's own conversation and journal.

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

No token or call limits apply by default. Optional per-round budgets and a
study spending ceiling are available. The ceiling includes target and analyst
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
