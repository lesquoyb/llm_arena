"""Supervise one local experiment at a time, using the existing CLI checkpoints."""
from __future__ import annotations

import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time
from uuid import uuid4

from arena.core import ArenaError, ROOT, digest, read_json, write_json
from arena.experiment import validate_config
from arena.usage import amount


class Jobs:
    def __init__(self, store):
        self.store = store
        self.lock = threading.RLock()
        self.process = None
        self.current = None
        self.watcher = None
        self.path = store.state / "jobs.json"
        self.rows = read_json(self.path) if self.path.exists() else []
        for row in self.rows:
            if row["status"] in {"running", "stopping"}:
                row["status"] = "interrupted"
                row["note"] = "The server was interrupted. Check the log before resuming."

    def listing(self):
        with self.lock:
            return list(reversed(self.rows))

    def _save(self):
        write_json(self.path, self.rows)

    def launch(self, *, draft_id=None, run_id=None, confirm_paid=False, ceiling=None):
        with self.lock:
            if (draft_id is None) == (run_id is None):
                raise ArenaError("Choose a configuration or a competition to resume")
            if self.process and self.process.poll() is None:
                raise ArenaError("A competition is already running. Wait for it or stop it.")
            if run_id is not None:
                out = self.store.run_path(run_id)
                metadata = read_json(out / "experiment.json")
                if "config" not in metadata or (out / "export.json").exists():
                    raise ArenaError("Only original experiments can be resumed here")
                config = metadata["config"]
            else:
                config = self.store.draft(draft_id)["config"]
                run_id = time.strftime("%Y%m%d-%H%M%S", time.gmtime()) + "-" + uuid4().hex[:8]
                out = self.store.runs / run_id
            validate_config(config)
            paid = any(m["provider"] != "mock" for m in config["models"])
            if paid and (confirm_paid is not True or ceiling is None or
                         amount(ceiling) != amount(config["spending"]["max_total_usd"])):
                raise ArenaError("Confirm the spending limit before making API calls")
            env = dict(os.environ)
            for model in config["models"]:
                if model["provider"] == "mock":
                    continue
                name = model["api_key_env"]
                secret = self.store.secrets.get(name) or os.environ.get(name)
                if not secret:
                    raise ArenaError(f"API key manquante : {name}")
                env[name] = secret
            from arena.engine import Engine
            engine = Engine()
            if draft_id is None and metadata["engine"] != engine.identity:
                raise ArenaError("This archive requires its original code and runtime. Clone its configuration for a new run.")
            identifier = uuid4().hex[:12]
            logs = self.store.state / "jobs"
            logs.mkdir(exist_ok=True)
            if draft_id is not None:
                manifest = logs / (identifier + ".json")
                write_json(manifest, config)
                args = ["experiment", "run", str(manifest), "--out", str(out)]
            else:
                args = ["experiment", "resume", str(out)]
            env["PYTHONUTF8"] = "1"
            env["ARENA_PROJECT_ROOT"] = str(ROOT)
            env["ARENA_STATE_ROOT"] = str(Path(engine.metadata["classes"]).parent)
            options = {"start_new_session": True} if os.name == "posix" else {
                "creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
            row = {"id": identifier, "run": run_id, "name": config["name"], "started_at": time.time(),
                   "status": "running", "resumed": draft_id is None, "config_sha256": digest(config),
                   "log": identifier + ".log"}
            with (logs / row["log"]).open("wb") as log:
                self.process = subprocess.Popen([sys.executable, "-m", "arena_web.worker", *args], cwd=ROOT,
                                                env=env, stdin=subprocess.DEVNULL, stdout=log,
                                                stderr=subprocess.STDOUT, **options)
            self.current = row
            self.rows.append(row)
            self._save()
            self.watcher = threading.Thread(target=self._watch, args=(self.process, row), daemon=True)
            self.watcher.start()
            return row

    def _watch(self, process, row):
        code = process.wait()
        with self.lock:
            row.update(status="stopped" if row["status"] == "stopping" else "completed" if code == 0 else "failed",
                       returncode=code, finished_at=time.time())
            self._save()

    def stop(self, identifier):
        with self.lock:
            if not self.current or self.current["id"] != identifier or self.process.poll() is not None:
                raise ArenaError("This run is no longer active")
            self.current["status"] = "stopping"
            self._save()
            if os.name == "nt":
                try:
                    self.process.send_signal(signal.CTRL_BREAK_EVENT)
                except OSError:
                    from arena.engine import stop_worker
                    stop_worker(self.process)
            else:
                self.process.send_signal(signal.SIGINT)
            return self.current

    def log(self, identifier):
        row = next((r for r in self.rows if r["id"] == identifier), None)
        if not row:
            raise ArenaError("Run not found")
        path = self.store.state / "jobs" / row["log"]
        with path.open("rb") as stream:
            stream.seek(max(0, path.stat().st_size - 128_000))
            content = stream.read().decode("utf-8", errors="replace")
        # A key accidentally echoed by a third party must not be returned by this endpoint.
        for secret in self.store.secrets.values():
            if secret:
                content = content.replace(secret, "[REDACTED]")
        for model in self.store.catalog():
            name = model.get("api_key_env", "")
            secret = self.store.secrets.get(name) or os.environ.get(name)
            if secret:
                content = content.replace(secret, "[REDACTED]")
        return {"job": row, "content": content}

    def close(self):
        with self.lock:
            active = self.current if self.process and self.process.poll() is None else None
        if active:
            self.stop(active["id"])
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                from arena.engine import stop_worker
                stop_worker(self.process)
        if self.watcher:
            self.watcher.join(timeout=5)
