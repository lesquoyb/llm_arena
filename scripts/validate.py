#!/usr/bin/env python3
"""Run the same engine, integration and resume checks on Windows and Linux."""
import datetime
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from arena.core import read_json


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("runs") / (
        "validation-" + datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S") + f"-{os.getpid()}")
    if not out.is_absolute():
        out = ROOT / out
    env = {**os.environ, "PYTHONUTF8": "1"}
    def run(*args):
        subprocess.run([sys.executable, *map(str, args)], cwd=ROOT, env=env, check=True)
    run("-m", "arena", "doctor")
    run("-m", "unittest", "discover", "-s", "tests", "-v")
    run("-m", "arena", "verify", "examples/strategies/rush", "examples/strategies/single-shot", "--out", out / "verify")
    tournament = out / "tournament"
    args = ("-m", "arena", "tournament", "examples/tournament.json", "--out", tournament)
    run(*args)
    report = read_json(tournament / "report.json")
    if report["completed"] != 18 or report["failed"] or report["pending"]:
        raise SystemExit(f"Incomplete tournament: {report}")
    def snapshot():
        return {p.relative_to(tournament).as_posix(): (p.stat().st_mtime_ns, p.stat().st_size)
                for p in tournament.glob("matches/*/attempt-*/*") if p.is_file()}
    before = snapshot()
    run(*args, "--resume")
    if before != snapshot():
        raise SystemExit("Resume changed match artifacts or created a new attempt")
    print("18 matches completed; resume reused every match.")


if __name__ == "__main__":
    main()
