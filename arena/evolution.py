"""Paired G1 branches and shared reference evaluation; opponents stay private."""
from __future__ import annotations
import copy
from pathlib import Path
from .core import ROOT, ArenaError, copy_submission, digest, make_scenario, read_json, submission, write_json
from .preparation import Preparation
from .tournament import run_tournament


def feedback_for(sid, tournament):
    """Bounded whitelist; no opponent code, paths, seeds or system logs."""
    rows = []
    for path in sorted((tournament / "records").glob("*.json")):
        record = read_json(path)
        match, result = record["match"], record["result"]
        if match["mirror"] or sid not in match["sides"]:
            continue
        side = match["sides"].index(sid)
        opponent = match["sides"][1 - side]
        metric = result.get("team_metrics", {}).get(str(side), {})
        rows.append({"opponent": "opponent-" + digest(opponent)[:8],
                     "status": result["status"], "winner": "draw" if result.get("winner_side") == -1
                     else "self" if result.get("winner_side") == side else "opponent",
                     "operations": metric.get("operations"), "errors": metric.get("errors"),
                     "operation_limit_hits": metric.get("operation_limit_hits"),
                     "turns": result.get("turns")})
        if result["status"] == "completed":
            outcome = read_json(tournament / record["directory"] / "outcome.json")
            actions = outcome.get("fight", {}).get("actions", [])
            rows[-1]["replay_excerpt"] = [a for a in actions if isinstance(a, list) and
                                         all(type(v) in (int, float, bool) or v is None for v in a)][:4]
    return {"matches": rows[:16], "truncated": len(rows) > 16,
            "note": "Opponents may improve. Their scripts remain private."}


def references(engine, config, out, journal, entrants, label, panel):
    """Both positions, identical reference opponents and final seeds for each branch."""
    root = out / "evaluations" / label
    root.mkdir(parents=True, exist_ok=True)
    results = {}
    for entrant in entrants:
        for opponent in panel:
            for seed in config["final_seeds"]:
                for side in (0, 1):
                    sources = [entrant, opponent] if side == 0 else [opponent, entrant]
                    key = digest({"entrant": entrant["id"], "opponent": opponent["id"], "seed": seed, "side": side})[:24]
                    cached = root / "records" / (key + ".json")
                    if cached.exists():
                        record = read_json(cached)
                        work = out / record["artifact_dir"]
                        from .core import file_hash
                        if record["result"]["status"] == "completed":
                            if file_hash(work / "outcome.json") != record["result"]["outcome_sha256"]:
                                raise ArenaError("Reference outcome changed")
                            if read_json(work / "result.json") != record["result"]:
                                raise ArenaError("Reference result changed")
                            scenario = make_scenario(config["scenario"], [s["submission"]["entrypoint"] for s in sources], seed, [s["submission"].get("team") for s in sources])
                            provenance = read_json(work / "provenance.json")
                            if (read_json(work / "scenario.json") != scenario or provenance["engine"] != engine.identity
                                    or provenance["submissions"] != [s["submission"] for s in sources]):
                                raise ArenaError("Reference provenance changed")
                            for index, source in enumerate(sources, 1):
                                if submission(work / "strategies" / str(index), source["submission"]["entrypoint"]) != source["submission"]:
                                    raise ArenaError("Reference source changed")
                        else:
                            cached = None
                    if not cached or not cached.exists():
                        work = Preparation._attempt(root / "matches" / key)
                        result = engine.fight([Path(s["path"]) for s in sources], [s["submission"] for s in sources],
                                              config["scenario"], seed, work)
                        record = {"session": entrant["id"], "opponent": opponent["id"], "seed": seed,
                                  "side": side, "result": result, "artifact_dir": work.relative_to(out).as_posix()}
                        write_json(root / "records" / (key + ".json"), record)
                        journal.save(entrant["id"], journal.state(entrant["id"]), "reference_match", record)
                    results[key] = record
    write_json(root / "results.json", results)
    return results


def run_evolution(config, out, journal, engine, initial, interrupt=None):
    from .experiment import run_session, PROMPT
    from .analysis import analyze_evolution
    models = {m["id"]: m for m in config["models"]}
    initial_states = {s["id"]: journal.state(s["id"]) for s in initial}
    branches = []
    for parent in initial:
        parent_state = initial_states[parent["id"]]
        if parent_state["status"] == "needs_reconciliation":
            continue
        for condition in config["improvement_conditions"]:
            sid = parent["id"] + "-g1-" + condition
            if journal.state(sid) is None:
                state = copy.deepcopy(parent_state)
                state.update(generation=1, condition=condition, parent=parent["id"],
                             parent_checkpoint_sha256=digest(parent_state), status="running",
                             calls=0, steps=0, test_matches=0, wall_seconds=0, pending=None, cursor=0,
                             in_flight=False, money_reserved="0", reservation_unbounded=False, cost_spent="0", input_tokens=0, output_tokens=0)
                state["token_usage_known"] = False
                state.pop("submission", None)
                state.pop("reserved", None)
                state.pop("assessment_sha256", None)
                state.pop("validity", None)
                state.pop("failure", None)
                prompt_path = ROOT / "prompts" / ("feedback.md" if condition == "feedback" else "control.md")
                message = {"role": "user", "content": prompt_path.read_text(encoding="utf-8"), "generation": 1,
                           "condition": condition, "budgets": config["budget_per_session"]}
                if condition == "feedback":
                    message["feedback"] = feedback_for(parent["id"], out / "tournament")
                    write_json(out / "feedback" / (sid + ".json"), message["feedback"])
                state["history"].append(message)
                copy_submission(Path(parent["path"]), out / "sessions" / sid / "workspace", parent["submission"])
                journal.save(sid, state, "branch_created", {"parent": parent["id"],
                                                          "checkpoint_sha256": state["parent_checkpoint_sha256"],
                                                          "condition": condition})
            run_session(sid, models[parent_state["model"]], config, out, journal, engine, interrupt)
            state = journal.state(sid)
            if "submission" in state:
                directory = out / "sessions" / sid
                cached = directory / "assessment.json"
                from .core import file_hash
                if cached.exists():
                    if state.get("assessment_sha256") and file_hash(cached) != state["assessment_sha256"]:
                        raise ArenaError("G1 assessment changed")
                    assessment = read_json(cached)
                else:
                    assessment = engine.analyze(directory / "submission", state["submission"]["entrypoint"],
                                                Preparation._attempt(directory / "assessment"))
                    write_json(cached, assessment)
                state["validity"] = assessment["status"]
                state["assessment_sha256"] = file_hash(cached)
                journal.save(sid, state, "submission_assessment", assessment)
                branches.append({"id": sid, "path": out / "sessions" / sid / "submission",
                                 "submission": state["submission"], "model": state["model"],
                                 "replicate": state["replicate"], "parent": parent["id"], "condition": condition})
    for parent_sid, parent_state in list(journal.states().items()):
        if parent_state.get("generation", 0) != 0 or "submission" in parent_state:
            continue
        for condition in config["improvement_conditions"]:
            sid = parent_sid + "-g1-" + condition
            if journal.state(sid) is None:
                skipped = copy.deepcopy(parent_state)
                skipped.update(parent=parent_sid, generation=1, condition=condition, status="no_submission",
                               calls=0, steps=0, test_matches=0, cost_spent="0", money_reserved="0")
                journal.save(sid, skipped, "branch_unavailable", {"reason": "No G0 submission"})
    contemporaries = None
    if len(branches) >= 2:
        manifest = {"name": config["name"] + "-G1", "seeds": config["final_seeds"], "scenario": config["scenario"],
                    "include_mirrors": config["include_mirrors"],
                    "strategies": [{**s, "path": str(s["path"])} for s in branches]}
        contemporaries = run_tournament(engine, manifest, out / "g1-tournament", (out / "g1-tournament").exists())
    panel = [dict(s, path=s["path"]) for s in initial]
    for name in ("rush", "single-shot", "passive"):
        source = ROOT / "examples/strategies" / name
        target = out / "controls" / name
        info = submission(source)
        if not target.exists():
            copy_submission(source, target, info)
        elif submission(target) != info:
            raise ArenaError("Frozen control changed")
        panel.append({"id": "fixed-" + name, "path": target, "submission": info})
    baseline = references(engine, config, out, journal, initial, "g0-panel", panel)
    evolved = references(engine, config, out, journal, branches, "g1-panel", panel)
    result = analyze_evolution(config, out, journal.states(), initial, branches, baseline, evolved, contemporaries)
    result["contemporaries"] = contemporaries
    write_json(out / "evolution.json", result)
    return result
