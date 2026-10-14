"""Offline G0 orchestration with transactional checkpoints and audit artifacts."""
from __future__ import annotations

import json
import re
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

from .core import (ArenaError, ROOT, digest, file_hash, integer, read_json, submission,
                   tree_hash, validate_scenario, write_json)
from .engine import Engine
from .preparation import Preparation
from .providers import MockProvider, PROFILES
from .tournament import run_tournament

PROMPT = ("Écris une stratégie LeekScript 4. Consulte authoring.md et leekscript-v1/api.md. "
          "Les outils portent uniquement sur tes fichiers et le catalogue de préparation : "
          "adversaire passif, seed 17, deux positions par test. Soumets main.leek. "
          "À la fin du budget, le dernier état est conservé, même invalide.")
TERMINAL = {"submitted", "budget_exhausted", "no_submission", "generation_failed"}


def load_config(path: Path) -> dict:
    return validate_config(read_json(path))


def validate_config(value: dict) -> dict:
    required = {"schema_version", "name", "models", "replicates", "budget_per_session",
                "spending", "seeds", "scenario", "include_mirrors"}
    if (not isinstance(value, dict) or set(value) != required or
            type(value["schema_version"]) is not int or value["schema_version"] != 1):
        raise ArenaError("Unsupported offline experiment schema")
    if value["spending"] != {"allow_paid_calls": False, "max_total_usd": 0}:
        raise ArenaError("Only unpaid mock experiments are supported")
    if not isinstance(value["name"], str) or not value["name"]:
        raise ArenaError("Experiment name is required")
    integer(value["replicates"], 1, 20, "replicates")
    models = value["models"]
    if not isinstance(models, list) or not models or len(models) > 20:
        raise ArenaError("Expected 1–20 models")
    ids = set()
    for model in models:
        if not isinstance(model, dict) or set(model) != {"id", "provider", "profile"}:
            raise ArenaError("Invalid model fields")
        if (not isinstance(model["id"], str) or
                not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,39}", model["id"]) or model["id"] in ids):
            raise ArenaError("Invalid or duplicate model ID")
        ids.add(model["id"])
        if model["provider"] != "mock" or model["profile"] not in PROFILES:
            raise ArenaError("Only supported mock profiles are allowed")
    budget = value["budget_per_session"]
    if not isinstance(budget, dict) or set(budget) != {"max_calls", "max_agent_steps", "max_test_matches", "max_wall_seconds"}:
        raise ArenaError("Invalid budgets; token budgets are unavailable for simulated usage")
    for key in budget:
        integer(budget[key], 0 if key == "max_test_matches" else 1, 100000, key)
    seeds = value["seeds"]
    if not isinstance(seeds, list) or not seeds or len(seeds) > 100 or len(seeds) != len(set(seeds)):
        raise ArenaError("Invalid evaluation seeds")
    for seed in seeds:
        integer(seed, 1, 2**31 - 1, "seed")
        if seed == 17:
            raise ArenaError("Evaluation seeds must differ from preparation seed 17")
    validate_scenario(value["scenario"])
    if type(value["include_mirrors"]) is not bool:
        raise ArenaError("include_mirrors must be boolean")
    return value


def plan(config: dict) -> dict:
    n = len(config["models"]) * config["replicates"]
    return {"sessions": n, "generation": 0, "provider": "mock", "simulated": True,
            "ranked_matches_if_all_submit": n * (n - 1) * len(config["seeds"]),
            "mirrors_if_all_submit": n * len(config["seeds"]) if config["include_mirrors"] else 0,
            "max_preparation_matches": n * config["budget_per_session"]["max_test_matches"],
            "max_cost_usd": 0, "required_keys": []}


@contextmanager
def experiment_lock(out: Path):
    # OS lock is released on crash; its file remains as harmless metadata.
    import fcntl
    with (out / ".lock").open("a") as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ArenaError("Another orchestrator is writing this experiment") from error
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


class Journal:
    def __init__(self, out):
        self.db = sqlite3.connect(out / "journal.sqlite")
        version = self.db.execute("PRAGMA user_version").fetchone()[0]
        if version not in (0, 1):
            self.db.close()
            raise ArenaError("Unsupported journal schema version")
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.execute("CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, state TEXT NOT NULL)")
        self.db.execute("CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, session TEXT, kind TEXT, payload TEXT)")
        self.db.execute("PRAGMA user_version=1")
        self.db.commit()

    def state(self, sid):
        row = self.db.execute("SELECT state FROM sessions WHERE id=?", (sid,)).fetchone()
        return json.loads(row[0]) if row else None

    def save(self, sid, state, kind, payload=None):
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO sessions VALUES (?,?)", (sid, json.dumps(state)))
            self.db.execute("INSERT INTO events(session,kind,payload) VALUES (?,?,?)",
                            (sid, kind, json.dumps({"at": time.time(), "data": payload})))

    def states(self):
        return {sid: json.loads(raw) for sid, raw in self.db.execute("SELECT id,state FROM sessions ORDER BY id")}


def _finish(sid, state, tools, journal, reason):
    try:
        result = tools.call("submit", {}, "final")
        state["submission"] = result["submission"]
        state["status"] = reason
    except (ArenaError, OSError):
        state["status"] = "no_submission"
    state["pending"] = None
    journal.save(sid, state, "finished", reason)


def run_session(sid, model, config, out, journal, engine, interrupt=None):
    state = journal.state(sid) or {
        "model": model["id"], "replicate": int(sid.rsplit("-r", 1)[1]), "status": "running",
        "history": [{"role": "user", "content": PROMPT, "budgets": config["budget_per_session"],
                     "scenario": config["scenario"]}],
        "calls": 0, "steps": 0, "test_matches": 0, "wall_seconds": 0,
        "pending": None, "cursor": 0}
    directory = out / "sessions" / sid
    tools = Preparation(directory, out / "corpus", engine, config["scenario"])
    if state["status"] in TERMINAL:
        if "submission" in state and submission(directory / "submission", state["submission"]["entrypoint"]) != state["submission"]:
            raise ArenaError("Archived session submission changed")
        return
    budget = config["budget_per_session"]
    started = time.monotonic()
    previous = state["wall_seconds"]
    journal.save(sid, state, "session_started")
    try:
        while state["status"] == "running":
            state["wall_seconds"] = previous + time.monotonic() - started
            if state["wall_seconds"] >= budget["max_wall_seconds"]:
                _finish(sid, state, tools, journal, "budget_exhausted")
                break
            if state["pending"] is None:
                if state["calls"] >= budget["max_calls"]:
                    _finish(sid, state, tools, journal, "budget_exhausted")
                    break
                journal.save(sid, state, "model_intent", {"provider": "mock", "profile": model["profile"]})
                response = MockProvider().respond(model["profile"], state["history"])
                state["calls"] += 1
                state["history"].append(response)
                state["pending"], state["cursor"] = response, 0
                journal.save(sid, state, "model_response", response)
                if interrupt:
                    interrupt("response", sid)
            calls = state["pending"]["tool_calls"]
            while state["cursor"] < len(calls) and state["status"] == "running":
                state["wall_seconds"] = previous + time.monotonic() - started
                if state["wall_seconds"] >= budget["max_wall_seconds"]:
                    _finish(sid, state, tools, journal, "budget_exhausted")
                    break
                call = calls[state["cursor"]]
                call_id = f"call-{state['calls']}-tool-{state['cursor']}"
                if state.get("reserved") != call_id and (
                        state["steps"] >= budget["max_agent_steps"] or
                        (call["name"] == "test" and state["test_matches"] + 2 > budget["max_test_matches"])):
                    _finish(sid, state, tools, journal, "budget_exhausted")
                    break
                # Reservation persists before executing a tool. Resume reuses it.
                if state.get("reserved") != call_id:
                    state["steps"] += 1
                    state["test_matches"] += 2 if call["name"] == "test" else 0
                    state["reserved"] = call_id
                    journal.save(sid, state, "tool_reserved", call)
                try:
                    result = tools.call(call["name"], call["arguments"], call_id)
                except (ArenaError, OSError, ValueError, KeyError, TypeError) as error:
                    result = {"error": str(error)}
                state["history"].append({"role": "tool", "call_id": call_id,
                                         "name": call["name"], "result": result})
                state["cursor"] += 1
                state["reserved"] = None
                if call["name"] == "submit" and "submission" in result:
                    state["submission"], state["status"] = result["submission"], "submitted"
                journal.save(sid, state, "tool_result", result)
                if interrupt:
                    interrupt("tool", sid)
            if state["status"] == "running":
                if not calls:
                    _finish(sid, state, tools, journal, "submitted")
                else:
                    state["pending"] = None
                    journal.save(sid, state, "turn_completed")
    finally:
        state["wall_seconds"] = previous + time.monotonic() - started
        journal.save(sid, state, "session_checkpoint")
        write_json(directory / "conversation.json", state["history"])


def status(out: Path) -> dict:
    if not (out / "journal.sqlite").exists():
        raise ArenaError("Experiment journal is missing")
    connection = sqlite3.connect(f"file:{out / 'journal.sqlite'}?mode=ro", uri=True)
    try:
        states = {sid: json.loads(raw) for sid, raw in connection.execute("SELECT id,state FROM sessions ORDER BY id")}
    finally:
        connection.close()
    return {"sessions": states}


def run(config: dict, out: Path, resume=False, interrupt=None) -> dict:
    validate_config(config)
    out = out.resolve()
    engine = Engine()
    docs = ROOT / "docs"
    corpus_files = [docs / "authoring.md", *sorted((docs / "leekscript-v1").rglob("*"))]
    corpus_hash = digest({p.relative_to(docs).as_posix(): file_hash(p)
                          for p in corpus_files if p.is_file()})
    identity = {"schema_version": 1, "config": config, "engine": engine.identity,
                "prompt_sha256": digest(PROMPT), "corpus_sha256": corpus_hash,
                "provider_fixtures": {name: file_hash(ROOT / "examples/strategies" / name / "main.leek")
                                      for name in ("rush", "single-shot", "passive")}}
    if resume:
        if not out.is_dir():
            raise ArenaError("Experiment does not exist")
    else:
        out.mkdir(parents=True, exist_ok=False)
    with experiment_lock(out):
        if resume:
            if read_json(out / "experiment.json") != identity:
                raise ArenaError("Cannot resume: configuration, runner, engine, prompt or corpus changed")
            if tree_hash(out / "corpus") != identity["corpus_sha256"]:
                raise ArenaError("Frozen documentation changed")
        else:
            import shutil
            for source in corpus_files:
                if source.is_file():
                    target = out / "corpus" / source.relative_to(docs)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, target)
            write_json(out / "experiment.json", identity)
        journal = Journal(out)
        try:
            for model in config["models"]:
                for replicate in range(config["replicates"]):
                    sid = f"{model['id']}-r{replicate}"
                    run_session(sid, model, config, out, journal, engine, interrupt)
            states = journal.states()
            assessments = {}
            for sid, state in states.items():
                if "submission" not in state:
                    assessments[sid] = {"status": "no_submission"}
                    continue
                directory = out / "sessions" / sid
                cached = directory / "assessment.json"
                if cached.exists():
                    assessments[sid] = read_json(cached)
                else:
                    target = Preparation._attempt(directory / "assessment")
                    assessments[sid] = engine.analyze(directory / "submission", state["submission"]["entrypoint"], target)
                    write_json(cached, assessments[sid])
            entrants = [{"id": sid, "model": state["model"], "replicate": state["replicate"],
                         "path": str(out / "sessions" / sid / "submission"), "submission": state["submission"]}
                        for sid, state in states.items() if "submission" in state]
            tournament = None
            if len(entrants) >= 2:
                manifest = {"name": config["name"], "seeds": config["seeds"],
                            "scenario": config["scenario"], "include_mirrors": config["include_mirrors"],
                            "strategies": entrants}
                tournament = run_tournament(engine, manifest, out / "tournament", (out / "tournament").exists())
            summary = {"simulated": True, "generation": 0, "sessions": len(states),
                       "with_submission": len(entrants),
                       "no_submission": sum(s["status"] == "no_submission" for s in states.values()),
                       "budget_exhausted": sum(s["status"] == "budget_exhausted" for s in states.values()),
                       "valid_submissions": sum(a["status"] == "valid" for a in assessments.values()),
                       "invalid_submissions": sum(a["status"] == "invalid" for a in assessments.values()),
                       "assessment_failures": sum(a["status"] not in {"valid", "invalid", "no_submission"}
                                                  for a in assessments.values()),
                       "model_calls": sum(s["calls"] for s in states.values()),
                       "tool_calls": sum(s["steps"] for s in states.values()),
                       "preparation_matches_reserved": sum(s["test_matches"] for s in states.values()),
                       "cost_usd": "0", "cost_status": "simulation",
                       "input_tokens": None, "output_tokens": None, "tournament": tournament}
            write_json(out / "report.json", summary)
            rows = ["| Session | État | Validité | Appels | Outils |",
                    "|---|---|---|---:|---:|"]
            rows.extend(f"| {sid} | {s['status']} | {assessments[sid]['status']} | {s['calls']} | {s['steps']} |"
                        for sid, s in states.items())
            (out / "report.md").write_text(
                "# " + config["name"] + "\n\nFournisseurs simulés, combats réels. Aucun appel API.\n\n"
                + f"Sessions : {len(states)} ; soumissions : {len(entrants)}.\n\n"
                + "Tokens inconnus ; coût fournisseur : 0 (simulation).\n\n"
                + "\n".join(rows) + "\n\n"
                + "Les scores du tournoi concernent les soumissions présentes ; les absences restent comptées ci-dessus.\n\n"
                + ("[Rapport des combats](tournament/report.md)\n" if tournament else "Tournoi non exécuté : moins de deux soumissions.\n"),
                encoding="utf-8")
            return summary
        finally:
            journal.db.close()
