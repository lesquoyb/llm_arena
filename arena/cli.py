from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from .core import ArenaError, DEFAULT_SCENARIO, ROOT, load_manifest, read_json, submission, write_json
from .engine import Engine, setup
from .tournament import report, run_tournament, schedule


def parser():
    p = argparse.ArgumentParser(description="Local LeekScript experiments and tournaments")
    commands = p.add_subparsers(dest="command", required=True)
    c = commands.add_parser("setup", help="Fetch the pinned engine, build its jar and the arena adapter")
    c.add_argument("--gradle")
    c = commands.add_parser("ui", help="Open the local browser interface")
    c.add_argument("--port", type=int, default=8765)
    c.add_argument("--runs", type=Path, help="Directory of competition artifacts (default: runs)")
    c.add_argument("--open", action="store_true", dest="open_browser")
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
    for name in ("plan", "run", "init"):
        action = actions.add_parser(name)
        action.add_argument("config", type=Path)
        if name in {"run", "init"}:
            action.add_argument("--out", type=Path, required=True)
    action = actions.add_parser('retry-fights',help='Retry frozen engine fixtures without making model requests')
    action.add_argument('directory',type=Path)
    action = actions.add_parser("retry", help="Continue one failed conversation, retaining completed submissions and matches")
    action.add_argument("directory", type=Path)
    action.add_argument("--session", required=True)
    action.add_argument("--reasoning-effort")
    action.add_argument("--allow-updated-runner", action="store_true")
    for name in ("resume", "status", "report"):
        action = actions.add_parser(name)
        action.add_argument("directory", type=Path)
        if name == "resume":
            action.add_argument("--allow-updated-runner", action="store_true")
    action = actions.add_parser("export")
    action.add_argument("directory", type=Path)
    action.add_argument("--out", type=Path, required=True)
    c = commands.add_parser("calibrate", help="Separate prompt calibration workshop")
    ca = c.add_subparsers(dest="calibration_action", required=True)
    ca.add_parser("example", help="Print an editable offline calibration configuration")
    action = ca.add_parser("serve", help="Open the standalone calibration interface")
    action.add_argument("--port", type=int, default=8766)
    action.add_argument("--out", type=Path, default=ROOT / "calibrations")
    action.add_argument("--open", action="store_true", dest="open_browser")
    action = ca.add_parser("run", help="Run or resume an immutable calibration study")
    action.add_argument("config", type=Path)
    action.add_argument("--out", type=Path, required=True)
    action.add_argument("--automatic", action="store_true")
    for name,help_text in [('score-conversation',"Score an exported conversation's readable reasoning with local Laya"),('diagnose-conversation','Save independent Laya choice diagnostics for an exported conversation')]:
        action = ca.add_parser(name, help=help_text)
        action.add_argument("conversation", type=Path)
        action.add_argument("--out", type=Path, required=True)
        action.add_argument("--model", choices=['convaiinnovations/laya','convaiinnovations/laya-multilingual','convaiinnovations/laya-typed-decisions'], default='convaiinnovations/laya')
        action.add_argument("--device", choices=['cpu','cuda','mps'], default='cpu')
    c = commands.add_parser("mcp", help="Preparation tools over MCP stdio")
    actions_mcp = c.add_subparsers(dest="mcp_action", required=True)
    action = actions_mcp.add_parser("serve")
    action.add_argument("--experiment", type=Path, required=True)
    action.add_argument("--session", required=True)
    action.add_argument("--reasoning-effort")
    action.add_argument("--allow-updated-runner", action="store_true")
    for name in ("analyze", "fight", "verify", "tournament"):
        c = commands.choices[name]
        c.add_argument("--out", type=Path)
        c.add_argument("--timeout", type=float, default=90, help="Whole-process deadline, seconds (not a per-turn budget)")
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        from .environment import load_dotenv
        load_dotenv()
        if args.command == "ui":
            from arena_web.server import serve
            if not 0 <= args.port <= 65535:
                raise ArenaError("Port must be between 0 and 65535")
            serve(args.port, args.runs, args.open_browser)
            return 0
        if args.command == "calibrate":
            from .calibration import defaults, study
            if args.calibration_action == "serve":
                from arena_web.calibration import serve
                serve(args.out, args.port, args.open_browser)
                return 0
            if args.calibration_action in {'score-conversation','diagnose-conversation'}:
                from .calibration_transcript import score,diagnose_export
                operation=score if args.calibration_action=='score-conversation' else diagnose_export
                result=operation(args.conversation,args.out,args.model,args.device)
                print(json.dumps(result,ensure_ascii=False,indent=2))
                return 0 if result['status']=='completed' else 1
            result = defaults() if args.calibration_action == "example" else study(read_json(args.config), args.out, args.automatic)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return int(result.get('status') == 'blocked')
        if args.command == "mcp":
            from .mcp_server import serve
            serve(args.experiment, args.session)
            return 0
        if args.command == "experiment":
            from .experiment import load_config, plan, run, status
            if args.action in {"plan", "run", "init"}:
                config = load_config(args.config.absolute())
                result = plan(config) if args.action == "plan" else run(config, args.out.absolute(), prepare_only=args.action == "init")
            elif args.action=='retry-fights':
                from .fight_recovery import run as retry_fights
                result=retry_fights(args.directory.absolute())
                print(json.dumps(result,ensure_ascii=False,indent=2))
                return int(bool(result['remaining_failed']))
            elif args.action in {"resume", "retry"}:
                directory = args.directory.absolute()
                result = run(read_json(directory / "experiment.json")["config"], directory, resume=True,
                             retry_session=args.session if args.action == "retry" else None,
                             allow_updated_runner=args.allow_updated_runner,
                             retry_reasoning_effort=getattr(args,"reasoning_effort",None))
            elif args.action == "status":
                result = status(args.directory.absolute())
            elif args.action == "export":
                from .exporting import export_experiment
                result = export_experiment(args.directory.absolute(), args.out.absolute())
            else:
                result = read_json(args.directory.absolute() / "report.json")
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return int(bool((result.get("tournament") or {}).get("failed")) or bool(result.get("assessment_failures"))
                       or bool(result.get("unresolved_sessions")) or bool(result.get("incomplete"))
                       or bool((result.get("evolution") or {}).get("incomplete")))
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
