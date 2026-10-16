"""Offline G0 orchestration with transactional checkpoints and audit artifacts."""
from __future__ import annotations

import json
import re
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

from .core import (ArenaError, ROOT, digest, file_hash, is_link, file_lock, integer, read_json, submission,
                   tree_hash, validate_scenario, write_json)
from .engine import Engine
from .preparation import Preparation
from .providers import MockProvider, PROFILES
from .api_providers import APIProvider, ProviderFailure
from .tool_schemas import TOOLS
from .usage import amount, reservation
from .tournament import run_tournament

PROMPT = (ROOT / "prompts/g0.md").read_text(encoding="utf-8") if (ROOT / "prompts/g0.md").exists() else (
          "Write a LeekScript 4 strategy. Read authoring.md and submit main.leek.")
TERMINAL = {"submitted", "budget_exhausted", "no_submission", "generation_failed",
            "provider_unavailable", "needs_reconciliation"}


def load_config(path: Path) -> dict:
    return validate_config(read_json(path))


def validate_config(value: dict) -> dict:
    required = {"schema_version", "name", "models", "replicates", "budget_per_session",
                "spending", "seeds", "scenario", "include_mirrors"}
    optional = {"generations", "improvement_conditions", "prompt_language", "final_seeds"}
    if (not isinstance(value, dict) or not required <= set(value) or set(value) - required - optional or
            type(value["schema_version"]) is not int or value["schema_version"] not in (1, 2)):
        raise ArenaError("Unsupported offline experiment schema")
    spending = value["spending"]
    if not isinstance(spending, dict) or "allow_paid_calls" not in spending or set(spending) - {"allow_paid_calls", "max_total_usd"}:
        raise ArenaError("Invalid spending policy")
    if type(spending["allow_paid_calls"]) is not bool:
        raise ArenaError("allow_paid_calls must be explicit boolean")
    if "max_total_usd" in spending:
        amount(spending["max_total_usd"])
    if value.get("prompt_language", "en") not in {"en", "fr"}:
        raise ArenaError("Unsupported prompt language; current prompts are English (legacy fr configs remain loadable)")
    integer(value.get("generations", 1), 1, 2, "generations")
    if value.get("improvement_conditions", ["control", "feedback"]) != ["control", "feedback"]:
        raise ArenaError("G1 requires the paired control and feedback conditions")
    if not isinstance(value["name"], str) or not value["name"]:
        raise ArenaError("Experiment name is required")
    integer(value["replicates"], 1, 20, "replicates")
    models = value["models"]
    if not isinstance(models, list) or not models or len(models) > 20:
        raise ArenaError("Expected 1-20 models")
    if all(isinstance(m, dict) and m.get("provider") == "mock" for m in models) and spending != {"allow_paid_calls": False, "max_total_usd": 0}:
        raise ArenaError("Mock experiments must disable paid calls")
    ids = set()
    for model in models:
        if not isinstance(model, dict) or not {"id", "provider"} <= set(model):
            raise ArenaError("Invalid model fields")
        if (not isinstance(model["id"], str) or
                not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,39}", model["id"]) or model["id"] in ids):
            raise ArenaError("Invalid or duplicate model ID")
        ids.add(model["id"])
        if model["provider"] == "mock":
            if set(model) != {"id", "provider", "profile"} or model["profile"] not in PROFILES:
                raise ArenaError("Invalid mock profile")
        else:
            fields = {"id", "provider", "model", "api_key_env", "pricing"}
            if (model["provider"] not in {"openai", "openai-compatible", "anthropic", "gemini"} or not fields <= set(model)
                    or set(model) - fields - {"endpoint", "parameters", "timeout_seconds", "max_retries", "max_input_tokens_per_call", "max_output_tokens"}):
                raise ArenaError("Invalid API model configuration")
            if not spending["allow_paid_calls"] or ("max_total_usd" in spending and amount(spending["max_total_usd"]) == 0):
                raise ArenaError("Real providers require explicit paid activation and a positive ceiling if configured")
            if not isinstance(model["model"], str) or not model["model"]:
                raise ArenaError("An exact model identifier is required")
            if not isinstance(model["api_key_env"], str) or not re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", model["api_key_env"]):
                raise ArenaError("Invalid credential variable name")
            from .endpoints import validate_endpoint
            validate_endpoint(model.get("endpoint", "https://api.example.com"))
            if model["provider"] == "openai-compatible" and "endpoint" not in model:
                raise ArenaError("Compatible endpoints must be explicit")
            for key in ("max_input_tokens_per_call", "max_output_tokens"):
                if key in model:
                    integer(model[key], 1, 10_000_000, key)
            if model["provider"] == "anthropic" and "max_output_tokens" not in model:
                raise ArenaError("Anthropic requires an explicit maximum output per call (max_tokens)")
            integer(model.get("timeout_seconds", 60), 1, 3600, "timeout_seconds")
            integer(model.get("max_retries", 0), 0, 3, "max_retries")
            params = model.get("parameters", {})
            allowed = {"temperature", "top_p", "reasoning_effort", "seed"}
            if model["provider"] == "anthropic":
                allowed = {"temperature", "top_p", "thinking"}
            elif model["provider"] == "gemini":
                allowed = {"temperature", "top_p", "top_k", "seed", "thinking_config"}
            if not isinstance(params, dict) or set(params) - allowed:
                raise ArenaError("Unsupported provider parameters (Anthropic does not expose a seed)")
            if "seed" in params:
                integer(params["seed"], 0, 2**31 - 1, "model seed")
            pricing = model["pricing"]
            if (not isinstance(pricing, dict) or not {"date", "currency", "input_per_million", "output_per_million"} <= set(pricing)
                    or set(pricing) - {"date", "currency", "input_per_million", "output_per_million",
                                      "cached_input_per_million", "cache_creation_per_million"}):
                raise ArenaError("Dated pricing is required for paid calls")
            if pricing["currency"] != "USD" or not isinstance(pricing["date"], str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", pricing["date"]):
                raise ArenaError("Pricing requires date and USD currency")
            from datetime import date
            try:
                date.fromisoformat(pricing["date"])
            except ValueError:
                raise ArenaError("Invalid pricing date") from None
            for key in set(pricing) - {"date", "currency"}:
                amount(pricing[key])
    budget = value["budget_per_session"]
    if (not isinstance(budget, dict) or set(budget) - {"max_calls", "max_agent_steps", "max_test_matches", "max_wall_seconds",
                             "max_input_tokens", "max_output_tokens", "max_cost_usd"}):
        raise ArenaError("Invalid budgets; token budgets are unavailable for simulated usage")
    for key in set(budget) - {"max_cost_usd"}:
        integer(budget[key], 0 if key == "max_test_matches" else 1, 100_000_000, key)
    if "max_cost_usd" in budget:
        amount(budget["max_cost_usd"])
    seeds = value["seeds"]
    if not isinstance(seeds, list) or not seeds or len(seeds) > 100 or len(seeds) != len(set(seeds)):
        raise ArenaError("Invalid evaluation seeds")
    for seed in seeds:
        integer(seed, 1, 2**31 - 1, "seed")
        if seed == 17:
            raise ArenaError("Evaluation seeds must differ from preparation seed 17")
    final = value.get("final_seeds", [])
    if value.get("generations", 1) == 2 and not final:
        raise ArenaError("G1 requires separate final seeds")
    if not isinstance(final, list) or len(final) != len(set(final)) or len(final) > 100:
        raise ArenaError("Invalid final seeds")
    for seed in final:
        integer(seed, 1, 2**31 - 1, "final seed")
        if seed in seeds or seed == 17:
            raise ArenaError("Preparation, feedback and final seeds must be distinct")
    validate_scenario(value["scenario"])
    if type(value["include_mirrors"]) is not bool:
        raise ArenaError("include_mirrors must be boolean")
    return value


def plan(config: dict) -> dict:
    n = len(config["models"]) * config["replicates"]
    evolved = config.get("generations", 1) == 2
    paid = [m for m in config["models"] if m["provider"] != "mock"]
    return {"sessions": n * (3 if evolved else 1), "generation": config.get("generations", 1) - 1,
            "provider": "mixed" if paid else "mock", "simulated": not paid,
            "ranked_matches_if_all_submit": n * (n - 1) * len(config["seeds"]),
            "mirrors_if_all_submit": n * len(config["seeds"]) if config["include_mirrors"] and n >= 2 else 0,
            "g1_contemporary_matches": (2*n*(2*n-1) + (2*n if config["include_mirrors"] else 0)) *
                                      len(config.get("final_seeds", [])) if evolved else 0,
            "common_reference_matches": 3*n*(n+3)*2*len(config.get("final_seeds", [])) if evolved else 0,
            "max_preparation_matches": (n * (3 if evolved else 1) * config["budget_per_session"]["max_test_matches"]) if "max_test_matches" in config["budget_per_session"] else None,
            "max_cost_usd": config["spending"].get("max_total_usd"),
            "financial_ceiling": ("best_effort_with_reservations" if "max_total_usd" in config["spending"] else "unlimited") if paid else "no_paid_calls",
            "required_keys": sorted({m["api_key_env"] for m in paid})}


@contextmanager
def experiment_lock(out: Path):
    with file_lock(out / ".lock"):
        yield


class Journal:
    def __init__(self, out):
        self.out = out
        self.db = sqlite3.connect(out / "journal.sqlite")
        version = self.db.execute("PRAGMA user_version").fetchone()[0]
        if version not in (0, 1, 2):
            self.db.close()
            raise ArenaError("Unsupported journal schema version")
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.execute("CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, state TEXT NOT NULL)")
        self.db.execute("CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, session TEXT, kind TEXT, payload TEXT)")
        self.db.execute("CREATE TABLE IF NOT EXISTS objects (id TEXT PRIMARY KEY, kind TEXT, parent TEXT, artifact TEXT, sha256 TEXT)")
        self.db.execute("PRAGMA user_version=2")
        self.db.commit()

    def state(self, sid):
        row = self.db.execute("SELECT state FROM sessions WHERE id=?", (sid,)).fetchone()
        return json.loads(row[0]) if row else None

    def save(self, sid, state, kind, payload=None):
        times = state.setdefault("message_times", [None] * len(state.get("history", [])))
        times.extend([time.time()] * (len(state.get("history", [])) - len(times)))
        if kind == "session_created" and times:
            times[0] = time.time()
        artifact = self.out / "artifacts" / (digest(payload) + ".json")
        if artifact.exists():
            if read_json(artifact) != payload:
                raise ArenaError("Journal artifact changed")
        else:
            write_json(artifact, payload)
        reference = {"at": time.time(), "artifact": artifact.relative_to(self.out).as_posix(),
                     "sha256": file_hash(artifact)}
        checkpoint = self.out / "artifacts" / (digest(state) + ".json")
        if not checkpoint.exists():
            write_json(checkpoint, state)
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO sessions VALUES (?,?)", (sid, json.dumps(state)))
            self.db.execute("INSERT INTO events(session,kind,payload) VALUES (?,?,?)",
                            (sid, kind, json.dumps(reference)))
            event_id = self.db.execute("SELECT last_insert_rowid()").fetchone()[0]
            self.db.execute("INSERT OR REPLACE INTO objects VALUES (?,?,?,?,?)",
                            (f"{sid}/{kind}/{event_id}", kind, sid, reference["artifact"], reference["sha256"]))
            self.db.execute("INSERT OR REPLACE INTO objects VALUES (?,?,?,?,?)",
                            (sid, "Session", state.get("parent"), checkpoint.relative_to(self.out).as_posix(), file_hash(checkpoint)))
            category = {"model_intent": "ModelCall", "model_response": "ModelCall",
                        "tool_reserved": "ToolCall", "tool_result": "ToolCall",
                        "usage_event": "UsageEvent", "submission_assessment": "Submission",
                        "branch_created": "FeedbackArtifact", "reference_match": "Match"}.get(kind)
            if category:
                identifier = f"{sid}/{category}/{state.get('calls', 0)}/{state.get('cursor', 0)}"
                self.db.execute("INSERT OR REPLACE INTO objects VALUES (?,?,?,?,?)",
                                (identifier, category, sid, reference["artifact"], reference["sha256"]))

    def verify(self):
        for artifact, expected in self.db.execute("SELECT artifact,sha256 FROM objects"):
            if file_hash(self.out / artifact) != expected:
                raise ArenaError("Journal artifact was modified")
        for sid, raw in self.db.execute("SELECT id,state FROM sessions"):
            row = self.db.execute("SELECT artifact FROM objects WHERE id=? AND kind='Session'", (sid,)).fetchone()
            if row and read_json(self.out / row[0]) != json.loads(raw):
                raise ArenaError("Journal session checkpoint was modified")

    def states(self):
        return {sid: json.loads(raw) for sid, raw in self.db.execute("SELECT id,state FROM sessions ORDER BY id")}


def _finish(sid, state, tools, journal, reason):
    if state.get("pending"):
        for index, call in enumerate(state["pending"]["tool_calls"][state["cursor"]:], state["cursor"]):
            call_id = f"call-{state['calls']}-tool-{index}"
            state["history"].append({"role": "tool", "name": call["name"], "call_id": call_id,
                                     "provider_call_id": call.get("id", call_id),
                                     "result": {"error": "Session finished before tool execution"}})
        state["cursor"] = len(state["pending"]["tool_calls"])
    try:
        result = tools.call("submit", {}, "final")
        state["submission"] = result["submission"]
        state["status"] = reason
    except (ArenaError, OSError):
        state["status"] = "no_submission"
    state["pending"] = None
    journal.save(sid, state, "finished", reason)


def provider_response(sid, state, model, config, journal):
    paid = model["provider"] != "mock"
    if state.get("in_flight") and paid:
        state["status"] = "needs_reconciliation"
        journal.save(sid, state, "remote_state_unknown")
        return None
    if paid:
        budget = config["budget_per_session"]
        try:
            bound = reservation(model, state["history"], TOOLS,
                                (budget["max_output_tokens"] - state.get("output_tokens", 0)) if "max_output_tokens" in budget else None)
        except ArenaError:
            state["status"] = "budget_exhausted"
            return None
        spent = amount(state.get("cost_spent", "0"))
        total = sum(amount(s.get("cost_spent", "0")) + amount(s.get("money_reserved", "0"))
                    for s in journal.states().values())
        remaining = []
        if "max_cost_usd" in budget:
            remaining.append(amount(budget["max_cost_usd"]) - spent)
        if "max_total_usd" in config["spending"]:
            remaining.append(amount(config["spending"]["max_total_usd"]) - total)
        if any(value <= 0 for value in remaining):
            state["status"] = "budget_exhausted"
            return None
        state["reservation_unbounded"] = bound["cost_bound"] is None and not remaining
        if bound["cost_bound"] is None and remaining:
            bound["cost_bound"] = str(min(remaining))
        if (("max_input_tokens" in budget and state.get("input_tokens", 0) + bound["input_bound"] > budget["max_input_tokens"])
                or (bound["cost_bound"] is not None and any(amount(bound["cost_bound"]) > value for value in remaining))):
            state["status"] = "budget_exhausted"
            return None
        state["money_reserved"] = bound["cost_bound"] or "0"
    else:
        bound = None
    state["calls"] += 1
    state["in_flight"] = True
    from .api_providers import request_snapshot
    output_limit = bound["output_bound"] if paid else model.get("max_output_tokens")
    request = request_snapshot(model, state["history"], TOOLS, output_limit)
    journal.save(sid, state, "model_intent", {"model": model, "reservation": bound, "request": request})
    provider = APIProvider(model) if paid else MockProvider(model["profile"])
    started = time.monotonic()
    try:
        response = (provider.respond(state["history"], TOOLS, bound["output_bound"]) if paid
                    else provider.respond(state["history"], TOOLS, output_limit))
    except ProviderFailure as error:
        state["status"] = "needs_reconciliation" if error.uncertain else "provider_unavailable"
        state["in_flight"] = error.uncertain
        if not error.uncertain:
            state["money_reserved"] = "0"
            state["reservation_unbounded"] = False
        state["failure"] = {"message": str(error), "phase": "provider request", "at": time.time(), "uncertain": error.uncertain, "retryable": error.retryable}
        journal.save(sid, state, "provider_failure", {"error": str(error),
                                                    "uncertain": error.uncertain, "retryable": error.retryable})
        return None
    except (KeyError, ValueError, TypeError, ArenaError) as error:
        state["status"] = "needs_reconciliation" if paid else "generation_failed"
        state["in_flight"] = paid
        state["failure"] = {"message": "The provider returned an unreadable response (" + type(error).__name__ + "). Inspect the recorded response in the journal; billing may need reconciliation.", "phase": "provider response", "at": time.time()}
        journal.save(sid, state, "malformed_provider_response", {"error_type": type(error).__name__,
                                                               "response": getattr(provider, "last_response", None)})
        return None
    state["in_flight"] = False
    response["elapsed_seconds"] = time.monotonic() - started
    if paid:
        usage = response["usage"]
        known = (response["cost_usd"] is not None and usage["input_tokens"] is not None
                 and usage["output_tokens"] is not None)
        if known:
            state["token_usage_known"] = True
            state["input_tokens"] = state.get("input_tokens", 0) + usage["input_tokens"]
            state["output_tokens"] = state.get("output_tokens", 0) + usage["output_tokens"]
            state["cost_spent"] = str(amount(state.get("cost_spent", "0")) + amount(response["cost_usd"]))
            state["money_reserved"] = "0"
            state["reservation_unbounded"] = False
            if (("max_input_tokens" in budget and state["input_tokens"] > budget["max_input_tokens"])
                    or ("max_output_tokens" in budget and state["output_tokens"] > budget["max_output_tokens"])
                    or ("max_cost_usd" in budget and amount(state["cost_spent"]) > amount(budget["max_cost_usd"]))):
                state["status"] = "budget_exhausted"
        else:
            state["token_usage_known"] = False
            state["status"] = "needs_reconciliation"
    state.pop("failure", None)
    state["history"].append(response)
    state["pending"], state["cursor"] = response, 0
    # Receipt, conversation, usage counters and released reservation commit together.
    journal.save(sid, state, "model_response", response)
    if paid:
        journal.save(sid, state, "usage_event", {"usage": response["usage"], "cost_usd": response["cost_usd"],
                                               "request_id": response.get("request_id")})
    return response


def execute_tool(sid, state, tools, journal, call, call_id, budget):
    if state["status"] != "running":
        raise ArenaError("Session is closed")
    if (state.get("reserved") != call_id and
            (state["steps"] >= budget.get("max_agent_steps", float("inf")) or
             (call["name"] == "test" and state["test_matches"] + 2 > budget.get("max_test_matches", float("inf"))))):
        raise ArenaError("Tool budget exhausted")
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
                             "provider_call_id": call.get("id", call_id),
                             "name": call["name"], "result": result})
    state["cursor"] += 1
    state["reserved"] = None
    state["workspace_files"] = workspace_files(tools.workspace)
    if call["name"] == "submit" and "submission" in result:
        state["submission"], state["status"] = result["submission"], "submitted"
    journal.save(sid, state, "tool_result", result)
    return result


def initial_state(sid, model, config):
    from .briefing import briefing, participant_scenario
    return {"model": model["id"], "replicate": int(sid.split("-r")[-1].split("-")[0]),
            "generation": 0, "condition": "initial", "status": "running",
            "history": [{"role": "user", "content": PROMPT, "budgets": config["budget_per_session"],
                         "scenario": participant_scenario(config["scenario"]), "briefing": briefing(config["scenario"]), "equipment_ids": {"weapons": "Use the item field in leekscript-v1/weapons.json (for example pistol = 37), not its object key or template", "chips": "Use the object key/id in leekscript-v1/chips.json (for example shock = 1); replay chip actions use template IDs"}, **({"team_instructions":
                         "Choose 1..scenario.team_size members using configure_team after writing their sources. "
                         "Each member can use a different entrypoint and equipment. When independent_builds is true, freely choose each member level (1–301), capital and components; supply level and capital explicitly. Reference member stats and components are not imposed on your team; omitted components mean none. Use preview_build to calculate final stats and costs, then validate_team to check the complete draft without changing files. Read the pinned equipment catalogs; "
                         "respect slot limits and allowlists; realistic mode also enforces equipment level. Stats follow scenario.stats_mode: per-member capital in realistic-v1 plus optional components (item-template IDs or {template, stats} alteration instances; eight slots, recovery components cost three; no duplicates; alteration charge must fit capacity), or raw stats in free mode. When require_capital is true you must explicitly allocate capital for every member; raw stats and inherited allocations are not accepted. Otherwise omit to inherit default member builds. Read corpus/stat-rules.json and corpus/component-rules.json (current public stats, levels, capacities and alteration weights). Configure the team before test or submit. "
                         "Improvements inherit team.json and may revise it with the same tool."}
                         if config["scenario"].get("team_selection") else {})}],
            "calls": 0, "steps": 0, "test_matches": 0, "wall_seconds": 0,
            "pending": None, "cursor": 0, "workspace_files": {}}


def workspace_files(directory):
    files = {}
    if is_link(directory):
        raise ArenaError("Working source links are not allowed")
    for path in sorted(directory.rglob("*")):
        if is_link(path):
            raise ArenaError("Working source links are not allowed")
        if path.is_file() and (path.suffix == ".leek" or path == directory / "team.json"):
            files[path.relative_to(directory).as_posix()] = file_hash(path)
    return files


def verify_workspace(state, tools):
    actual = workspace_files(tools.workspace)
    expected = state.get("workspace_files", actual)
    if actual != expected:
        # Recover a write that completed before its tool-result checkpoint.
        import hashlib
        calls = (state.get("pending") or {}).get("tool_calls", [])
        call = calls[state["cursor"]] if state.get("reserved") and state["cursor"] < len(calls) else {}
        args = call.get("arguments")
        candidate = dict(expected)
        if call.get("name") == "write_file" and isinstance(args, dict) and isinstance(args.get("content"), str):
            from .preparation import local_path
            name = local_path(tools.workspace, args["path"]).relative_to(tools.workspace).as_posix()
            candidate[name] = hashlib.sha256(args["content"].encode()).hexdigest()
        if call.get("name") == "configure_team" and isinstance(args, dict):
            content = json.dumps(args, ensure_ascii=False, indent=2) + "\n"
            candidate["team.json"] = hashlib.sha256(content.encode()).hexdigest()
        if actual != candidate:
            raise ArenaError("Working sources changed outside the recorded tools")
    state["workspace_files"] = actual


def run_session(sid, model, config, out, journal, engine, interrupt=None):
    state = journal.state(sid) or initial_state(sid, model, config)
    directory = out / "sessions" / sid
    tools = Preparation(directory, out / "corpus", engine, config["scenario"])
    if state["status"] in TERMINAL:
        if "submission" in state and submission(directory / "submission", state["submission"]["entrypoint"]) != state["submission"]:
            raise ArenaError("Archived session submission changed")
        return
    verify_workspace(state, tools)
    budget = config["budget_per_session"]
    started = time.monotonic()
    previous = state["wall_seconds"]
    journal.save(sid, state, "session_started")
    try:
        while state["status"] == "running":
            state["wall_seconds"] = previous + time.monotonic() - started
            if state["wall_seconds"] >= budget.get("max_wall_seconds", float("inf")):
                _finish(sid, state, tools, journal, "budget_exhausted")
                break
            if state["pending"] is None:
                if state["calls"] >= budget.get("max_calls", float("inf")):
                    _finish(sid, state, tools, journal, "budget_exhausted")
                    break
                response = provider_response(sid, state, model, config, journal)
                if response is None:
                    if state["status"] == "budget_exhausted":
                        _finish(sid, state, tools, journal, "budget_exhausted")
                    break
                if state["status"] != "running":
                    if state["status"] == "budget_exhausted":
                        _finish(sid, state, tools, journal, "budget_exhausted")
                    break
                if interrupt:
                    interrupt("response", sid)
            calls = state["pending"]["tool_calls"]
            while state["cursor"] < len(calls) and state["status"] == "running":
                state["wall_seconds"] = previous + time.monotonic() - started
                if state["wall_seconds"] >= budget.get("max_wall_seconds", float("inf")):
                    _finish(sid, state, tools, journal, "budget_exhausted")
                    break
                call = calls[state["cursor"]]
                call_id = f"call-{state['calls']}-tool-{state['cursor']}"
                if state.get("reserved") != call_id and (
                        state["steps"] >= budget.get("max_agent_steps", float("inf")) or
                        (call["name"] == "test" and state["test_matches"] + 2 > budget.get("max_test_matches", float("inf")))):
                    _finish(sid, state, tools, journal, "budget_exhausted")
                    break
                execute_tool(sid, state, tools, journal, call, call_id, budget)
                if interrupt:
                    interrupt("tool", sid)
            if state["status"] != "running" and state.get("pending"):
                for index in range(state["cursor"], len(calls)):
                    call = calls[index]
                    call_id = f"call-{state['calls']}-tool-{index}"
                    state["history"].append({"role": "tool", "name": call["name"], "call_id": call_id,
                                             "provider_call_id": call.get("id", call_id),
                                             "result": {"error": "Session closed; tool was not executed"}})
                state["cursor"] = len(calls)
                journal.save(sid, state, "cancelled_remaining_tools")
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


def run(config: dict, out: Path, resume=False, interrupt=None, prepare_only=False, retry_session=None) -> dict:
    validate_config(config)
    if retry_session and not resume:
        raise ArenaError("Retry requires an existing experiment")
    out = out.resolve()
    engine = Engine()
    docs = ROOT / "docs"
    corpus_files = [docs / "authoring.md", *sorted((docs / "leekscript-v1").rglob("*")),
                    *sorted((docs / "corpus").rglob("*"))]
    corpus_hash = digest({p.relative_to(docs).as_posix(): file_hash(p)
                          for p in corpus_files if p.is_file()})
    identity = {"schema_version": 2, "config": config, "engine": engine.identity,
                "scientific_identity": engine.scientific_identity,
                "runtime_provenance": engine.runtime_provenance,
                "artifact_provenance": engine.artifact_provenance,
                "catalogs": {"training": {"seed_ids": {"train-17": 17}, "opponent": "passive",
                                          "scenario_sha256": digest(config["scenario"])},
                             "feedback": {"seeds": config["seeds"], "scenario_sha256": digest(config["scenario"])},
                             "final": {"seeds": config.get("final_seeds", []), "scenario_sha256": digest(config["scenario"])}},
                "prompt_sha256": digest(PROMPT), "corpus_sha256": corpus_hash,
                "prompts_sha256": tree_hash(ROOT / "prompts"),
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
            if not resume:
                journal.db.execute("INSERT OR REPLACE INTO objects VALUES (?,?,?,?,?)",
                                   ("experiment", "Experiment", None, "experiment.json", file_hash(out / "experiment.json")))
                journal.db.commit()
            if resume:
                journal.verify()
            if retry_session:
                from .retries import prepare_retry
                prepare_retry(journal, retry_session, config)
            allow_extend = any(s.get('retry_count') for s in journal.states().values())
            if prepare_only:
                for model in config["models"]:
                    for replicate in range(config["replicates"]):
                        sid = f"{model['id']}-r{replicate}"
                        directory = out / "sessions" / sid
                        directory.mkdir(parents=True, exist_ok=True)
                        journal.save(sid, initial_state(sid, model, config), "session_created")
                return {"initialized": True, "sessions": list(journal.states())}
            for model in config["models"]:
                for replicate in range(config["replicates"]):
                    sid = f"{model['id']}-r{replicate}"
                    if not retry_session or sid == retry_session:
                        run_session(sid, model, config, out, journal, engine, interrupt)
            states = {sid: state for sid, state in journal.states().items() if state.get("generation", 0) == 0}
            assessments = {}
            for sid, state in states.items():
                if "submission" not in state:
                    assessments[sid] = {"status": "no_submission"}
                    continue
                directory = out / "sessions" / sid
                cached = directory / "assessment.json"
                if cached.exists():
                    if state.get("assessment_sha256") and file_hash(cached) != state["assessment_sha256"]:
                        raise ArenaError("Submission assessment changed")
                    assessments[sid] = read_json(cached)
                else:
                    target = Preparation._attempt(directory / "assessment")
                    assessments[sid] = engine.analyze(directory / "submission", state["submission"]["entrypoint"], target)
                    write_json(cached, assessments[sid])
                state["validity"] = assessments[sid]["status"]
                state["assessment_sha256"] = file_hash(cached)
                journal.save(sid, state, "submission_assessment", assessments[sid])
            entrants = [{"id": sid, "model": state["model"], "replicate": state["replicate"],
                         "path": str(out / "sessions" / sid / "submission"), "submission": state["submission"]}
                        for sid, state in states.items() if "submission" in state]
            tournament = None
            if len(entrants) >= 2:
                manifest = {"name": config["name"], "seeds": config["seeds"],
                            "scenario": config["scenario"], "include_mirrors": config["include_mirrors"],
                            "strategies": entrants}
                tournament = run_tournament(engine, manifest, out / "tournament", (out / "tournament").exists(), allow_extend=allow_extend)
            simulated = all(m["provider"] == "mock" for m in config["models"])
            summary = {"simulated": simulated, "generation": 0, "sessions": len(states),
                       "with_submission": len(entrants),
                       "no_submission": sum("submission" not in s for s in states.values()),
                       "budget_exhausted": sum(s["status"] == "budget_exhausted" for s in states.values()),
                       "valid_submissions": sum(a["status"] == "valid" for a in assessments.values()),
                       "invalid_submissions": sum(a["status"] == "invalid" for a in assessments.values()),
                       "assessment_failures": sum(a["status"] not in {"valid", "invalid", "no_submission"}
                                                  for a in assessments.values()),
                       "model_calls": sum(s["calls"] for s in states.values()),
                       "tool_calls": sum(s["steps"] for s in states.values()),
                       "preparation_matches_reserved": sum(s["test_matches"] for s in states.values()),
                       "known_cost_subtotal_usd": str(sum(amount(s.get("cost_spent", "0")) for s in states.values())),
                       "reserved_usd": None if any(s.get("reservation_unbounded") for s in states.values()) else str(sum(amount(s.get("money_reserved", "0")) for s in states.values())),
                       "cost_usd": None if any(s["status"] == "needs_reconciliation" or amount(s.get("money_reserved", "0")) > 0
                                              for s in states.values()) else str(sum(amount(s.get("cost_spent", "0")) for s in states.values())),
                       "cost_status": "simulation" if simulated else "calculated_or_reserved",
                       "input_tokens": None if simulated or any(s["calls"] and not s.get("token_usage_known") for s in states.values())
                                       else sum(s.get("input_tokens", 0) for s in states.values()),
                       "output_tokens": None if simulated or any(s["calls"] and not s.get("token_usage_known") for s in states.values())
                                        else sum(s.get("output_tokens", 0) for s in states.values()),
                       "tournament": tournament,
                       "incomplete": any("submission" not in s for s in states.values()),
                       "unresolved_sessions": [sid for sid,s in states.items() if s["status"] == "needs_reconciliation"]}
            if config.get("generations", 1) == 2:
                from .evolution import run_evolution
                summary["evolution"] = run_evolution(config, out, journal, engine, entrants, interrupt, retry_session=retry_session, allow_extend=allow_extend)
                summary["generation"] = 1
                summary["sessions"] = len(journal.states())
                summary["cost_usd"] = summary["evolution"]["cost_usd"]
                final_states = journal.states()
                summary["model_calls"] = sum(s["calls"] for s in final_states.values())
                summary["tool_calls"] = sum(s["steps"] for s in final_states.values())
                summary["preparation_matches_reserved"] = sum(s["test_matches"] for s in final_states.values())
                summary["unresolved_sessions"] = [sid for sid,s in final_states.items() if s["status"] == "needs_reconciliation"]
                summary["with_submission"] = sum("submission" in s for s in final_states.values())
                summary["no_submission"] = sum("submission" not in s for s in final_states.values())
                summary["valid_submissions"] = sum(s.get("validity") == "valid" for s in final_states.values())
                summary["invalid_submissions"] = sum(s.get("validity") == "invalid" for s in final_states.values())
                summary["budget_exhausted"] = sum(s["status"] == "budget_exhausted" for s in final_states.values())
                summary["assessment_failures"] = sum("submission" in s and s.get("validity") not in {"valid", "invalid"}
                                                    for s in final_states.values())
                summary["incomplete"] = summary["evolution"]["incomplete"]
                summary["known_cost_subtotal_usd"] = summary["evolution"]["known_cost_subtotal_usd"]
                summary["reserved_usd"] = summary["evolution"]["reserved_usd"]
                for key in ("input_tokens", "output_tokens"):
                    summary[key] = None if simulated or any(s["calls"] and not s.get("token_usage_known")
                                                           for s in final_states.values()) else sum(s.get(key, 0) for s in final_states.values())
            summary["session_failures"] = [{"session": sid, "status": state["status"], **state["failure"]}
                                            for sid, state in journal.states().items() if state.get("failure")]
            write_json(out / "report.json", summary)
            rows = ["| Session | Status | Validity | Calls | Tools |",
                    "|---|---|---|---:|---:|"]
            rows.extend(f"| {sid} | {s['status']} | {assessments[sid]['status']} | {s['calls']} | {s['steps']} |"
                        for sid, s in states.items())
            (out / "report.md").write_text(
                "# " + config["name"] + ("\n\nMock providers, real matches. No API calls.\n\n" if simulated
                                        else "\n\nAPI providers, real matches. See the journal and usage records.\n\n")
                + f"G0 sessions: {len(states)} ; G0 submissions: {len(entrants)}.\n\n"
                + ("Unknown tokens; provider cost: 0 (mock run).\n\n" if simulated
                   else f"Calculated cost: {summary['cost_usd']} USD; see usage and reservations.\n\n")
                + "\n".join(rows) + "\n\n"
                + "Tournament scores cover available submissions; missing ones are counted above.\n\n"
                + ("[Match report](tournament/report.md)\n" if tournament else "Tournament not run: fewer than two submissions.\n"),
                encoding="utf-8")
            if "evolution" in summary:
                with (out / "report.md").open("a", encoding="utf-8") as stream:
                    stream.write("\n[Comparaison G0/G1 sur panel commun](analysis.md) · [HTML](analysis.html) · [CSV](analysis.csv)\n")
            return summary
        finally:
            journal.db.close()
