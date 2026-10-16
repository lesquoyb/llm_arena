# LLM Arena

<p align="center"><img src="docs/assets/arena-logo.png" alt="LLM Arena gladiator robot" width="360"></p>

Run and compare **LeekScript 4** strategies with the official Leek Wars engine,
pinned to commit `b99a174dd938260d9e47b2e65a208cb32230e26e`.

Participants write code through a shared tool interface. The runner records
prompts, source versions, usage and match results. Experiments can compare an
initial strategy with two improvement branches, with and without feedback.
The included demos use scripted mock participants and real Java matches. They
make no LLM calls and do not measure real model performance.

## Install and start

Requirements: Python 3.11 or later, Git and a full JDK 25. The bootstrap installs
Gradle 9.3.1 and locked Python dependencies. Run commands from the repository.

Windows PowerShell:

```powershell
py -3 scripts/bootstrap.py
.\.venv\Scripts\python.exe -m arena ui --open
```

Linux x86_64:

```bash
bash scripts/bootstrap-linux.sh
.venv/bin/python -m arena ui --open
```

The interface opens at **http://127.0.0.1:8765**. It provides participant and
price settings, competition management, full recorded conversations, source
history and diffs, schematic replays, match statistics and comparisons across
compatible experiments. No Node.js installation is needed to use it.

See the [Windows](docs/windows.md), [Linux](docs/linux.md) and [interface](docs/ui.md)
guides. Installation needs Internet access; mock experiments and matches run locally afterward.

## Command line

Use the Python executable inside `.venv`, or activate it before these commands:

```bash
python -m arena doctor
python -m arena analyze examples/strategies/rush
python -m arena fight examples/strategies/rush examples/strategies/passive
python -m arena plan examples/tournament.json
python -m arena tournament examples/tournament.json --out runs/my-first-tournament
python -m arena tournament examples/tournament.json --out runs/my-first-tournament --resume
```

The example tournament runs 12 ranked matches and 6 mirrors across two seeds.
Mirrors do not affect the ranked score. Finished match artifacts are verified
and reused on resume. Interrupted matches get a new attempt directory.
Only one process may write to a tournament at a time.

The complete mock experiment runs 80 evaluation matches plus requested preparation matches:

```bash
python -m arena experiment plan configs/offline-complete.json
python -m arena experiment run configs/offline-complete.json --out runs/complete-demo
python -m arena experiment resume runs/complete-demo
python -m arena experiment export runs/complete-demo --out runs/complete-export
```

Use a new output directory for a new experiment. Resume requires the recorded
code, runtime, configuration and sources. Existing archives remain readable after updates.

## Strategies and results

A strategy is a folder containing `main.leek` and optional `.leek` includes.
Includes stay inside that folder. Submissions are limited to 128 files and 2 MB.
Each member of a team runs the same entry point and can choose its role through
the game API. Manifest paths are relative to the manifest.

```json
{"id":"model-a-rep-1","path":"strategies/model-a-rep-1","entrypoint":"main.leek","model":"exact-model-id","replicate":1}
```

The manifest sets team size, turn limit (1 to 1,000), stats and equipment.
`entity.cores` sets the operation budget; `entity.ram` controls LeekScript memory.
The upstream example field `max_operations_per_entity` is not supported.
Custom maps can define `obstacles`, `team1` and `team2`. The default grid has
613 cells numbered 0 to 612. Without an explicit map, the seed determines placement.

Scores use `(wins + 0.5 * draws) / completed non-mirror matches`.
A strategy error remains a game result. Engine failures and whole-process
timeouts are unranked, rather than artificial losses. `--timeout 90` limits
the whole worker process, not one turn. Recorded timings are elapsed time, not CPU time.

Results include frozen sources, scenarios, raw outcomes, logs, compact results,
SHA-256 hashes and reports. Engine winners are 0 or 1 for the two sides and -1
for a draw; replay teams are numbered 1 and 2. The arena records duration up to the requested `max_turns` limit.
New UI competitions use the [Simple duel preset and character sheets](docs/ui.md#scenario-presets-and-character-sheets).

## Validation and documentation

```bash
python -m arena verify examples/strategies/rush examples/strategies/single-shot
python -m unittest discover -s tests -v
python scripts/validate.py
```

`validate.py` requires a built engine and checks a full 18-match tournament
and resume without recalculation. CI covers Linux and Windows. Provider adapters
use offline fixtures in CI; real API calls require explicit models, prices,
keys and paid-call authorization; spending limits are optional. Check the workflow result for the commit being used.

- [Realistic stats](docs/realistic-stats.md): official capital rules and per-leek builds.
- [Interface](docs/ui.md): matrix links, filters, files, requests, replays and statistics.
- [Full experiment](docs/complete-experiment.md): initial/improved strategies, MCP, exports and Docker.
- [Providers](docs/providers.md): OpenAI, Anthropic, Gemini, compatible APIs, seeds and billing.
- [Strategy authoring](docs/authoring.md) and [pinned API reference](docs/leekscript-v1/api.md).
- [Engine audit](docs/engine-audit.md), [experiment protocol](docs/protocol.md) and [implementation status](docs/implementation-status.md).

To generate a new API reference: `python -m arena docs --out docs/new-snapshot`.
The reference contains 378 functions and 416 constants; it is a signature and
value reference, not a complete description of every behavior.

Native Java workers have heap, output and time limits. An optional Docker
backend disables network access. This application is a local tool, not a public
service for hostile submissions. Python/JavaScript strategies remain future work;
TypeScript is outside the current scope.

See the [weapons, chips and summons example](examples/showcase/README.md) for a runnable mechanics demonstration.
