from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from .core import ArenaError, DEFAULT_SCENARIO, ROOT, load_manifest, read_json, submission, write_json
from .engine import Engine, setup
from .tournament import report, run_tournament, schedule


def parser():
    p = argparse.ArgumentParser(description="Local LeekScript arena — no provider/API calls")
    commands = p.add_subparsers(dest="command", required=True)
    c = commands.add_parser("setup", help="Fetch the pinned engine, build its jar and the arena adapter")
    c.add_argument("--gradle")
    commands.add_parser("doctor", help="Check engine artifact hashes and Java runtime")
    c = commands.add_parser("docs", help="Export a frozen API reference from the compiled engine")
    c.add_argument("--out", type=Path, required=True)
    c = commands.add_parser("plan", help="Validate a tournament and show its match count")
    c.add_argument("manifest", type=Path)
    c = commands.add_parser("analyze", help="Analyze a submission directory")
    c.add_argument("source", type=Path)
    c.add_argument("--entrypoint", default="main.leek")
    for name in ("fight", "verify"):
        c = commands.add_parser(name, help="Run one match" if name == "fight" else "Repeat a match and compare gameplay hashes")
        c.add_argument("left", type=Path)
        c.add_argument("right", type=Path)
        c.add_argument("--left-entry", default="main.leek")
        c.add_argument("--right-entry", default="main.leek")
        c.add_argument("--seed", type=int, default=101)
        c.add_argument("--scenario", type=Path, help="JSON object with team_size, max_turns, entity and optional map")
    c = commands.add_parser("tournament", help="Run a balanced round-robin, retaining all artifacts")
    c.add_argument("manifest", type=Path)
    c.add_argument("--resume", action="store_true")
    c = commands.add_parser("report", help="Rebuild tournament reports")
    c.add_argument("directory", type=Path)
    c = commands.add_parser("experiment", help="Unpaid offline mock sessions and real LeekScript tournaments")
    actions = c.add_subparsers(dest="action", required=True)
    for name in ("plan", "run"):
        action = actions.add_parser(name)
        action.add_argument("config", type=Path)
        if name == "run":
            action.add_argument("--out", type=Path, required=True)
    for name in ("resume", "status", "report"):
        action = actions.add_parser(name)
        action.add_argument("directory", type=Path)
    for name in ("analyze", "fight", "verify", "tournament"):
        c = commands.choices[name]
        c.add_argument("--out", type=Path)
        c.add_argument("--timeout", type=float, default=90, help="Whole-process deadline, seconds (not a per-turn budget)")
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == "experiment":
            from .experiment import load_config, plan, run, status
            if args.action in {"plan", "run"}:
                config = load_config(args.config.absolute())
                result = plan(config) if args.action == "plan" else run(config, args.out.absolute())
            elif args.action == "resume":
                directory = args.directory.absolute()
                result = run(read_json(directory / "experiment.json")["config"], directory, resume=True)
            elif args.action == "status":
                result = status(args.directory.absolute())
            else:
                result = read_json(args.directory.absolute() / "report.json")
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return int(bool((result.get("tournament") or {}).get("failed")) or bool(result.get("assessment_failures")))
        if args.command == "setup":
            setup(args.gradle)
            print("Engine built. Run: python -m arena doctor")
            return 0
        if args.command == "doctor":
            engine = Engine()
            print(json.dumps({"status": "ready", **engine.identity}, indent=2))
            return 0
        if args.command == "docs":
            result = Engine().export_docs(args.out.absolute())
            print(json.dumps(result, indent=2))
            return 0
        if args.command == "plan":
            manifest = load_manifest(args.manifest.absolute())
            matches = schedule(manifest)
            print(json.dumps({"strategies": len(manifest["strategies"]), "ranked_matches": sum(not m["mirror"] for m in matches),
                              "mirror_matches": sum(m["mirror"] for m in matches), "total": len(matches)}, indent=2))
            return 0
        if args.command == "report":
            result = report(args.directory.absolute())
        else:
            engine = Engine(args.timeout)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            out = (args.out or ROOT / "runs" / f"{args.command}-{stamp}").absolute()
            if args.command == "analyze":
                result = engine.analyze(args.source.absolute(), args.entrypoint, out)
            elif args.command == "tournament":
                result = run_tournament(engine, load_manifest(args.manifest.absolute()), out, args.resume)
            else:
                config = read_json(args.scenario) if args.scenario else DEFAULT_SCENARIO
                sources = [args.left.absolute(), args.right.absolute()]
                infos = [submission(sources[0], args.left_entry), submission(sources[1], args.right_entry)]
                if args.command == "fight":
                    result = engine.fight(sources, infos, config, args.seed, out)
                else:
                    out.mkdir(parents=True, exist_ok=False)
                    first = engine.fight(sources, infos, config, args.seed, out / "first")
                    second = engine.fight(sources, infos, config, args.seed, out / "second")
                    stable = first["status"] == second["status"] == "completed" and first["replay_sha256"] == second["replay_sha256"]
                    result = {"status": "reproducible" if stable else "mismatch_or_failure", "first": first, "second": second}
                    write_json(out / "verification.json", result)
            print(f"Artifacts: {out}")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return int(result.get("status") in {"invalid", "engine_error", "timeout", "mismatch_or_failure"} or result.get("failed", 0) > 0)
    except (ArenaError, OSError, ValueError, KeyError, TypeError) as e:
        print(f"Arena error: {e}")
        return 2
    except KeyboardInterrupt:
        print("Interrupted. Tournament artifacts are preserved; resume with the same manifest and --out PATH --resume.")
        return 130
