"""Read existing artifacts without changing a journal or its checkpoints."""
from __future__ import annotations

import copy
from contextlib import closing
import difflib
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import threading
import time
from uuid import uuid4

from arena.core import ArenaError, ROOT, STATE_ROOT, digest, is_link, read_json, write_json
from arena.experiment import plan, validate_config
from arena.preparation import local_path


TERMINAL = {"submitted", "budget_exhausted", "no_submission", "generation_failed",
            "provider_unavailable", "needs_reconciliation"}


def safe_path(root: Path, name: str) -> Path:
    path = local_path(root, name)
    if not path.resolve().is_relative_to(root.resolve()):
        raise ArenaError("Chemin hors du dossier autorisé")
    return path


def history_writes(history):
    """A proposal becomes a version only after a successful write tool receipt."""
    pending, generation = [], 0
    for index, message in enumerate(history):
        if message.get("role") == "user":
            generation = message.get("generation", generation)
        elif message.get("role") == "assistant":
            pending = list(message.get("tool_calls") or [])
        elif message.get("role") == "tool":
            match = next((i for i, call in enumerate(pending)
                          if call.get("id") == message.get("provider_call_id")), None)
            if match is None:
                match = next((i for i, call in enumerate(pending) if call.get("name") == message.get("name")), None)
            if match is None:
                continue
            call = pending.pop(match)
            args, result = call.get("arguments") or {}, message.get("result") or {}
            if (call.get("name") == "write_file" and not result.get("error")
                    and isinstance(args.get("content"), str) and isinstance(args.get("path"), str)):
                content = args["content"]
                expected = hashlib.sha256(content.encode("utf-8")).hexdigest()
                if result.get("sha256") != expected:
                    continue
                yield {"message": index, "generation": generation, "path": args["path"],
                       "content": content, "sha256": expected}


class Store:
    def __init__(self, runs: Path | None = None, state: Path | None = None):
        self.runs = (runs or ROOT / "runs").resolve()
        self.state = (state or STATE_ROOT / "ui").resolve()
        self.runs.mkdir(parents=True, exist_ok=True)
        self.state.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.secrets = {}
        self._cache = {}

    def json(self, path, default=None):
        if any(is_link(p) for p in [path, *path.parents]):
            raise ArenaError("Les liens ne sont pas consultables")
        if not path.is_file():
            return default
        stat = path.stat()
        stamp = (stat.st_mtime_ns, stat.st_size)
        with self.lock:
            cached = self._cache.get(path)
            if cached and cached[0] == stamp:
                return copy.deepcopy(cached[1])
            value = read_json(path)
            # Do not retain large replay/history objects in the metadata cache.
            if stat.st_size < 200_000:
                if len(self._cache) > 256:
                    self._cache.clear()
                self._cache[path] = (stamp, value)
            return copy.deepcopy(value)

    def catalog(self):
        with self.lock:
            value = self.json(self.state / "participants.json")
            if value is None:
                value = [{"id": "mock-repair", "provider": "mock", "profile": "repair-and-submit"},
                         {"id": "mock-single", "provider": "mock", "profile": "single-shot"}]
            return value

    def participants(self):
        return [{"spec": m, "key_configured": bool(self.secrets.get(m.get("api_key_env")) or
                                                    os.environ.get(m.get("api_key_env", "")))}
                for m in self.catalog()]

    def validate_model(self, model):
        config = read_json(ROOT / "configs/offline-complete.json")
        config["models"] = [model]
        if model.get("provider") != "mock":
            config["spending"] = {"allow_paid_calls": True, "max_total_usd": "1"}
            config["budget_per_session"].update(max_input_tokens=1_000_000, max_output_tokens=100_000, max_cost_usd="1")
        validate_config(config)

    def save_participant(self, model, secret=None):
        self.validate_model(model)
        if secret is not None and (not isinstance(secret, str) or len(secret) > 8192):
            raise ArenaError("Clé API invalide")
        if secret and not model.get("api_key_env", "").startswith("ARENA_"):
            raise ArenaError("Utiliser un nom de variable commençant par ARENA_ pour une clé saisie ici")
        with self.lock:
            models = self.catalog()
            models = [m for m in models if m["id"] != model["id"]] + [model]
            write_json(self.state / "participants.json", models)
            if secret:
                self.secrets[model["api_key_env"]] = secret
        return {"saved": model["id"]}

    def delete_participant(self, identifier):
        with self.lock:
            write_json(self.state / "participants.json", [m for m in self.catalog() if m["id"] != identifier])
        return {"deleted": identifier}

    def drafts(self):
        return [self.json(p) for p in sorted((self.state / "competitions").glob("*.json"))]

    def save_draft(self, config, identifier=None):
        validate_config(config)
        identifier = identifier or uuid4().hex[:12]
        path = safe_path(self.state / "competitions", identifier + ".json")
        value = {"id": identifier, "updated_at": time.time(), "config": config}
        with self.lock:
            write_json(path, value)
        return {**value, "plan": plan(config)}

    def delete_draft(self, identifier):
        with self.lock:
            safe_path(self.state / "competitions", identifier + ".json").unlink(missing_ok=True)
        return {"deleted": identifier}

    def draft(self, identifier):
        result = self.json(safe_path(self.state / "competitions", identifier + ".json"))
        if result is None:
            raise ArenaError("Configuration introuvable")
        return result

    def run_path(self, identifier):
        root = safe_path(self.runs, identifier)
        if not (root / "experiment.json").is_file():
            raise ArenaError("Compétition introuvable")
        return root

    def run_paths(self):
        for base, dirs, files in os.walk(self.runs, followlinks=False):
            directory = Path(base)
            dirs[:] = [d for d in dirs if not is_link(directory / d) and d not in {".git", ".arena"}]
            if "experiment.json" in files:
                yield directory
                dirs[:] = []

    def states(self, root):
        path = root / "journal.sqlite"
        if not path.is_file() or is_link(path):
            return {}
        # mode=ro avoids schema migrations, checkpoint writes and creating missing DBs.
        with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=2)) as connection:
            if not connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='sessions'").fetchone():
                return {}
            return {sid: json.loads(raw) for sid, raw in connection.execute("SELECT id,state FROM sessions ORDER BY id")}

    def session(self, identifier, sid):
        result = self.states(self.run_path(identifier)).get(sid)
        if result is None:
            raise ArenaError("Session introuvable")
        return result

    def listing(self):
        rows = []
        for path in self.run_paths():
            identifier = path.relative_to(self.runs).as_posix()
            try:
                metadata = self.json(path / "experiment.json")
                config = metadata.get("config", metadata.get("manifest", {}))
                report = self.json(path / "report.json", {})
                rows.append({"id": identifier, "name": config.get("name", identifier),
                             "kind": "experiment" if "config" in metadata else "tournament",
                             "created_at": (path / "experiment.json").stat().st_mtime,
                             "archived": (path / "export.json").exists(),
                             "simulated": all(m.get("provider") == "mock" for m in config.get("models", []))
                                          if "models" in config else None,
                             "models": len(config.get("models", config.get("strategies", []))),
                             "replicates": config.get("replicates"), "report": report,
                             "complete": bool(report) and not any(report.get(k) for k in
                                  ("incomplete", "failed", "pending", "assessment_failures", "unresolved_sessions"))
                                         and not (report.get("evolution") or {}).get("incomplete")})
            except (OSError, ValueError, sqlite3.Error) as error:
                rows.append({"id": identifier, "name": identifier, "error": str(error), "complete": False})
        return sorted(rows, key=lambda r: r.get("created_at", 0), reverse=True)

    def detail(self, identifier):
        root = self.run_path(identifier)
        metadata = self.json(root / "experiment.json")
        states = self.states(root)
        sessions = []
        keys = ("model", "replicate", "generation", "condition", "parent", "parent_checkpoint_sha256",
                "status", "validity", "calls", "steps", "test_matches", "wall_seconds", "cost_spent",
                "money_reserved", "token_usage_known", "input_tokens", "output_tokens", "submission")
        for sid, state in states.items():
            sessions.append({"id": sid, **{k: state[k] for k in keys if k in state},
                             "messages": len(state.get("history", []))})
        return {"id": identifier, "metadata": metadata, "report": self.json(root / "report.json", {}),
                "analysis": self.json(root / "analysis.json"), "sessions": sessions,
                "g0": self.json(root / "tournament/report.json"),
                "g1": self.json(root / "g1-tournament/report.json"),
                "standings": self.json(root / "report.json", {}).get("standings"),
                "archived": (root / "export.json").exists()}

    def conversation(self, identifier, sid, offset=0, limit=25):
        state = self.session(identifier, sid)
        history = state.get("history", [])
        return {"total": len(history), "offset": offset, "messages": history[offset:offset + limit],
                "status": state["status"]}

    def events(self, identifier, sid=None, offset=0, limit=100):
        root = self.run_path(identifier)
        path = root / "journal.sqlite"
        if not path.exists():
            return {"total": 0, "events": []}
        with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=2)) as connection:
            if not connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='events'").fetchone():
                return {"total": 0, "events": []}
            clause, args = (" WHERE session=?", [sid]) if sid else ("", [])
            total = connection.execute("SELECT count(*) FROM events" + clause, args).fetchone()[0]
            rows = connection.execute("SELECT id,session,kind,payload FROM events" + clause +
                                      " ORDER BY id LIMIT ? OFFSET ?", [*args, limit, offset]).fetchall()
        return {"total": total, "events": [{"id": row[0], "session": row[1], "kind": row[2],
                                            **json.loads(row[3])} for row in rows]}

    def event(self, identifier, event_id):
        root = self.run_path(identifier)
        with closing(sqlite3.connect((root / "journal.sqlite").as_uri() + "?mode=ro", uri=True)) as connection:
            row = connection.execute("SELECT payload FROM events WHERE id=?", (event_id,)).fetchone()
        if not row:
            raise ArenaError("Événement introuvable")
        reference = json.loads(row[0])
        path = safe_path(root, reference["artifact"])
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != reference["sha256"]:
            raise ArenaError("L'empreinte de cet événement ne correspond plus au journal")
        return self.json(path)

    def versions(self, identifier, sid):
        history = self.session(identifier, sid).get("history", [])
        files, versions = {}, []
        for write in history_writes(history):
            files[write["path"]] = write["sha256"]
            versions.append({k: v for k, v in write.items() if k != "content"} |
                            {"index": len(versions), "files": sorted(files), "tree_sha256": digest(files)})
        return {"versions": versions, "basis": "Écritures confirmées par les outils ; les propositions en erreur sont exclues."}

    def source(self, identifier, sid, version, filename, previous=None):
        files, before, after = {}, {}, None
        writes = list(history_writes(self.session(identifier, sid).get("history", [])))
        if not 0 <= version < len(writes):
            raise ArenaError("Version introuvable")
        previous = version - 1 if previous is None else previous
        if previous < -1 or previous > version:
            raise ArenaError("Choisir une version antérieure pour la comparaison")
        for index, write in enumerate(writes[:version + 1]):
            files[write["path"]] = write["content"]
            if index == previous:
                before = dict(files)
            if index == version:
                after = dict(files)
        if filename not in after:
            raise ArenaError("Fichier absent de cette version")
        old, new = before.get(filename, ""), after[filename]
        lines = difflib.unified_diff(old.splitlines(keepends=True), new.splitlines(keepends=True),
                                     fromfile=f"v{previous + 1}/{filename}", tofile=f"v{version + 1}/{filename}")
        delta = "".join(line if line.endswith("\n") else line + "\n\\ No newline at end of file\n" for line in lines)
        return {"path": filename, "before": old, "after": new, "diff": delta,
                "sha256": hashlib.sha256(new.encode("utf-8")).hexdigest()}

    def files(self, identifier):
        root = self.run_path(identifier)
        result = []
        engine_folders = {}
        for base, dirs, names in os.walk(root, followlinks=False):
            folder = Path(base)
            dirs[:] = [d for d in dirs if not is_link(folder / d)]
            for name in names:
                path = folder / name
                if is_link(path) or name in {".lock", "journal.sqlite", "journal.sqlite-wal", "journal.sqlite-shm"}:
                    continue
                engine_data = False
                for parent in [folder, *folder.parents]:
                    if parent == root:
                        break
                    if parent.name == "data":
                        if parent not in engine_folders:
                            engine_folders[parent] = (parent.parent / "outcome.json").is_file()
                        engine_data = engine_folders[parent]
                        break
                result.append({"path": path.relative_to(root).as_posix(), "size": path.stat().st_size,
                               "engine_data": engine_data})
                if len(result) >= 50_000:
                    return {"files": result, "truncated": True}
        return {"files": sorted(result, key=lambda f: f["path"]), "truncated": False}

    def matches(self, identifier):
        root = self.run_path(identifier)
        rows = []
        for base in (root, root / "tournament", root / "g1-tournament",
                     root / "evaluations/g0-panel", root / "evaluations/g1-panel"):
            for path in sorted((base / "records").glob("*.json")):
                record = self.json(path)
                relative = base.relative_to(root).as_posix()
                match = record.get("match", {})
                sides = match.get("sides")
                if not sides:
                    sides = [record.get("session"), record.get("opponent")]
                    if record.get("side") == 1:
                        sides.reverse()
                work = base / record["directory"] if "directory" in record else safe_path(root, record["artifact_dir"])
                safe_path(root, work.relative_to(root).as_posix())
                rows.append({"path": work.relative_to(root).as_posix(), "stage": relative,
                             "sides": sides, "seed": match.get("seed", record.get("seed")),
                             "mirror": match.get("mirror", False), "result": record["result"]})
        for path in sorted((root / "sessions").glob("*/tools/**/result.json")):
            if (path.parent / "scenario.json").is_file():
                info = self.json(path.parent / "provenance.json", {})
                scenario = self.json(path.parent / "scenario.json", {})
                rows.append({"path": path.parent.relative_to(root).as_posix(), "stage": "préparation",
                             "sides": (["passive", path.relative_to(root).parts[1]] if "side-1" in path.as_posix()
                                       else [path.relative_to(root).parts[1], "passive"]),
                             "seed": scenario.get("random_seed"), "mirror": False,
                             "result": self.json(path), "provenance": info})
        return {"matches": rows}

    def match(self, identifier, name):
        root = self.run_path(identifier)
        work = safe_path(root, name)
        result = self.json(work / "result.json")
        if result is None:
            raise ArenaError("Combat introuvable")
        return {"result": result, "scenario": self.json(work / "scenario.json"),
                "provenance": self.json(work / "provenance.json"),
                "outcome": self.json(work / "outcome.json")}

    def statistics(self, identifier):
        from .metrics import competition_stats
        root = self.run_path(identifier)
        matches = self.matches(identifier)["matches"]
        paths = [safe_path(root, row["path"] + "/outcome.json") for row in matches]
        stamp = digest(matches), tuple((p.stat().st_mtime_ns, p.stat().st_size) if p.is_file() else None for p in paths)
        with self.lock:
            cache = getattr(self, "_statistics_cache", {})
            if identifier in cache and cache[identifier][0] == stamp:
                return copy.deepcopy(cache[identifier][1])
        result = competition_stats(matches, lambda name: self.json(safe_path(root, name + "/outcome.json")))
        with self.lock:
            if len(cache) >= 16:
                cache.clear()
            cache[identifier] = (stamp, result)
            self._statistics_cache = cache
        return result

    def aggregate(self, identifiers):
        groups, excluded = {}, []
        for identifier in dict.fromkeys(identifiers):
            detail = self.detail(identifier)
            if detail["archived"]:
                excluded.append({"run": identifier, "reason": "Copie exportée : exclue pour éviter le double comptage."})
                continue
            analysis = detail["analysis"]
            if not analysis:
                excluded.append({"run": identifier, "reason": "Pas de mesure sur le panel de stratégies fixes."})
                continue
            metadata, root = detail["metadata"], self.run_path(identifier)
            config = metadata["config"]
            initial_ids = {s["id"] for s in detail["sessions"] if s.get("generation", 0) == 0}
            opponents = {}
            for record in self.json(root / "evaluations/g1-panel/results.json", {}).values():
                if record["opponent"] not in initial_ids:
                    provenance = self.json(safe_path(root, record["artifact_dir"]) / "provenance.json", {})
                    index = 1 - record["side"]
                    sources = provenance.get("submissions", [])
                    opponents[record["opponent"]] = sources[index].get("sha256") if len(sources) == 2 else None
            if not opponents or any(value is None for value in opponents.values()):
                excluded.append({"run": identifier, "reason": "Provenance des adversaires fixes indisponible."})
                continue
            protocol = {"scenario": config["scenario"], "seeds": config.get("final_seeds"),
                        "engine": metadata.get("scientific_identity", metadata.get("engine")),
                        "opponents": opponents,
                        "preparation": {"budgets": config["budget_per_session"], "catalogs": metadata.get("catalogs"),
                                        "corpus_sha256": metadata.get("corpus_sha256"),
                                        "prompts_sha256": metadata.get("prompts_sha256", metadata.get("prompt_sha256"))},
                        "simulated": all(m["provider"] == "mock" for m in config["models"])}
            key = digest(protocol)[:16]
            group = groups.setdefault(key, {"id": key, "protocol": protocol, "runs": [], "series": [], "models": {}})
            group["runs"].append(identifier)
            models = {m["id"]: m for m in config["models"]}
            for row in analysis["rows"]:
                if row["panel"] != "controls":
                    continue
                descriptor = models.get(row["model"], {})
                model_key = digest({k: v for k, v in descriptor.items() if k != "api_key_env"})[:12]
                k = f"{row['model']}/{model_key}/g{row['generation']}/{row['condition']}"
                point = {**row, "run": identifier, "created_at": (root / "experiment.json").stat().st_mtime,
                         "model_signature": model_key, "model_id": descriptor.get("model", descriptor.get("profile")),
                         "participant": descriptor}
                group["series"].append(point)
                group["models"].setdefault(k, []).append(point)
        for group in groups.values():
            summaries = []
            for key, rows in group["models"].items():
                from decimal import Decimal
                totals = {k: sum(r[k] for r in rows) if all(r.get(k) is not None for r in rows) else None
                          for k in ("input_tokens", "output_tokens", "operations", "errors")}
                total_cost = (str(sum((Decimal(r["cost_usd"]) for r in rows), Decimal(0)))
                              if all(r.get("cost_usd") is not None for r in rows) else None)
                complete = [r for r in rows if r["score"] is not None and not r["failed"]]
                summaries.append({**totals, "cost_usd": total_cost, "key": key, "model": rows[0]["model"], "participant": rows[0]["participant"], "generation": rows[0]["generation"],
                                  "condition": rows[0]["condition"],
                                  "score": sum(r["score"] for r in complete) / len(complete) if complete else None,
                                  "conversations": len(complete), "excluded": len(rows) - len(complete),
                                  "runs": len({r["run"] for r in complete})})
            group["models"] = summaries
        return {"groups": list(groups.values()), "excluded": excluded,
                "explanation": "Moyenne à poids égal des conversations complètes, contre les mêmes stratégies fixes. "
                               "Scénario, seeds, adversaires, préparation, budgets, moteur et mode simulé/réel doivent correspondre. "
                               "Les protocoles différents restent séparés ; aucun classement global artificiel."}
