# Complete experiment with strategy improvement

On native Windows, follow the [PowerShell guide](windows.md) and replace `python`
with `.\.venv\Scripts\python.exe`, omitting the `source` command.

```bash
source .venv/bin/activate
python -m arena experiment plan configs/offline-complete.json
python -m arena experiment run configs/offline-complete.json --out runs/complete-demo
python -m arena experiment resume runs/complete-demo
python -m arena experiment export runs/complete-demo --out runs/complete-export
```

The demo creates two initial strategy conversations, then control and feedback branches from
each. Mocks provide predefined strategies; engine diagnostics and matches are
real. Each pair inherits exactly the same initial strategy code and conversation before the
improvement message.

Preparation uses seed 17 and passive in both positions. Feedback uses seed 101.
Final evaluation uses seed 301, which session tools cannot request. Submissions
are frozen before each round. Feedback contains pseudonymized results, own
metrics and bounded numerical replay excerpts, without opponent code, internal
paths or system logs.

The schedule contains 4 initial strategy matches, 16 contemporary improved strategy matches and 60 reference
matches. The initial strategy and both improvement branches face the same frozen initial strategy panel and fixed controls
in both positions. Contemporary self-matches are separate mirrors. Reference
panel results retain the initial strategy anchor of each trajectory.

## Reports and artifacts

- `report.json` and `report.md`: execution summary.
- `tournament/` and `g1-tournament/`: separate contemporary standings and matrices.
- `evaluations/g0-panel` and `g1-panel`: common reference opponents and fixtures.
- `feedback/`: the actual information sent only to feedback branches.
- `analysis.json/csv/md/html`: strategy/model/generation/panel scores, paired effects and costs.
- `journal.sqlite` and `artifacts/`: checkpoints, calls, usage, lineage and hashed records.
- `export.json`: file inventory and SHA-256 hashes for the exported copy.

Missing submissions, invalid code and infrastructure failures remain visible.
Scores describe submitted strategies, not an overall performance measure with
an invented penalty for absent generations. Model aggregates give equal weight
to independent conversations. The matrices retain matches between repetitions
of the same model.

Exploratory intervals resample paired conversations while keeping their fixtures
together. They are conditional on the fixed panel and do not model every opponent
dependency. The one-repetition demo provides no scientific comparison of real
models. Mock cost zero is marked as simulation; unknown costs do not enter the
Pareto frontier.

Exports contain the sources and results needed for independent reading.
Original paths are provenance, not reading dependencies. Resume still requires
the recorded runtime; Windows and Linux runs are not silently merged.

## MCP

```bash
python -m arena experiment init configs/offline-demo.json --out runs/mcp-preparation
python -m arena mcp serve --experiment runs/mcp-preparation --session mock-single-r0
```

The stdio server uses MCP SDK 1.30.0 with locked dependencies. It exposes the
same eight tools and journaled execution as native providers. It requires an
open session without a pending provider response, takes the writer lock and
applies quotas. `submit` closes the session. Java workers do not receive provider keys.

## Optional Docker backend

```bash
bash scripts/build-worker.sh
export ARENA_WORKER_BACKEND=docker
export ARENA_WORKER_IMAGE="$(cat .arena/worker-image.txt)"
python -m arena fight examples/strategies/rush examples/strategies/passive
```

The image uses a verified JDK and a digest-pinned Debian base. Network is disabled;
the root filesystem is read-only; the worker runs as non-root without capabilities,
with 768 MB memory and a process limit. Mounts expose only the read-only engine
runtime and the match work directory. Backend and image identity are recorded;
do not switch them when resuming. Docker image construction is a Linux tool.
Rebuild the image if it is absent in a new environment.

Workers use a shared JVM startup profile (tier 1 compilation) for short processes.
`ARENA_JVM_PROFILE=full` restores full HotSpot compilation. The profile is recorded
and cannot change on resume; timings from different profiles are not merged.

## Installation paths

The Linux bootstrap prepares Java, Gradle, `.venv`, MCP and an editable install.
`ARENA_PROJECT_ROOT` selects checkout resources; `ARENA_STATE_ROOT` separates
engine state from source. Do not move a recorded runtime without setup.
The runner fingerprint covers packages and prompts. Scientific identity and
Python/Java/platform provenance are separate, but resume checks both.

The [local interface](ui.md) provides the same workflows with request inspection,
source history, match filters and statistics. [Provider settings](providers.md)
cover real API activation, prices and spending limits.
