# Offline experiment with initial strategies

Use the project Python after installation:

```bash
python -m arena experiment plan configs/offline-demo.json
python -m arena experiment run configs/offline-demo.json --out runs/offline-demo-new
python -m arena experiment status runs/offline-demo-new
python -m arena experiment resume runs/offline-demo-new
python -m arena experiment report runs/offline-demo-new
```

This demo creates four independent conversations: two mock profiles with two
repetitions each. The repair profile writes invalid code, reads real engine
diagnostics, writes the rush control, tests both sides against passive, reads
replay metrics and submits. The second profile submits single-shot. These are
predefined scripts, not LLM-generated strategies.

initial strategy runs 12 ranked matches and 4 mirrors on seed 101. Preparation uses only seed
17 against passive. Mirrors do not affect scores. Missing and invalid submissions
remain visible; scores are conditional on the available valid submissions.

## Artifacts and resume

- `experiment.json`: frozen manifest, prompt, corpus, engine and runner identity.
- `corpus/`: the shared authoring guide and pinned reference material.
- `journal.sqlite`: transactional states, intents, responses, tool results, budgets and timestamps.
- `sessions/*/workspace`: session-owned working files.
- `sessions/*/submission`: frozen submitted sources.
- `sessions/*/conversation.json`: canonical conversation export.
- `sessions/*/tools`: diagnostics, preparation matches and replays.
- `report.md`, `report.json` and `tournament/`: execution and match results.

Saved responses and completed matches are reused after interruption. Interrupted
worker calls can create a new retained attempt. An OS lock excludes a second
writer. Resume rejects changed configuration, runtime, runner, corpus or frozen
sources. `report` reads the latest report; `status` can inspect interrupted work.
Paid APIs do not have an exactly-once billing guarantee: uncertain remote state
keeps its reservation and blocks automatic repetition.

## Tools and budgets

The shared tools are `list_files`, `read_file`, `write_file`, `read_docs`,
`analyze`, `test`, `read_replay` and `submit`. There is no shell tool. Paths must
stay inside the session, without links or traversal. Reads are paginated.
Sources are limited to 128 `.leek` files and 2 MB. A preparation test runs two
matches, one per side. Mocks receive the same prompts and tool schemas as real participants.

Budgets cover model calls, tool calls, preparation matches and accumulated time.
Time is checked between operations; a running operation can continue up to the
worker timeout (90 seconds by default). A hard kill can lose elapsed time since
the last checkpoint. Budget exhaustion submits the last saved state. Final
submission analysis is an evaluation step outside the preparation budget.

Mock token usage is `null`, since no provider tokenizer is used. API cost zero
is explicitly marked as simulation. Mock manifests must disable paid calls.

Native Java workers receive a minimal environment without provider keys, have
a 512 MB heap limit and are stopped with their children on timeout. Output is
limited to 8 MB per file, with OS enforcement on Linux and polling on Windows.
The process backend is not a complete OS sandbox for hostile public submissions.

## Related workflows

This manifest is initial-strategy-only. The [complete experiment](complete-experiment.md)
adds paired improved strategy branches, held-out seeds, MCP, exports and API adapters.
Mock failure profiles cover invalid/empty submissions, malformed tools, timeout,
rate limiting and exhausted budgets. The corpus covers the example functions;
it is not a complete description of every game behavior.
