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

    def launch(self, *, draft_id=None, run_id=None, confirm_paid=False, ceiling=None, retry_session=None, expected_config_sha256=None, allow_updated_runner=False, retry_reasoning_effort=None):
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
                from arena.roster import effective, snapshot
                config = effective(out, metadata['config'])
                roster = snapshot(out) or {}
                withdrawn = set(roster.get('withdrawn', []))
                frozen_tracks = roster.get('frozen_tracks', {})
                from arena.recovery import needs_reconciliation
                external = {m['id'] for m in config['models'] if m['provider'] != 'mock'}
                blocked = [sid for sid,state in self.store.states(out).items() if state['model'] not in withdrawn and needs_reconciliation(state, state['model'] in external)]
                if blocked:
                    raise ArenaError('Resolve billing in Conversations before resuming: ' + ', '.join(blocked))
                if retry_session is None:
                    from arena.retries import retry_reason
                    states = self.store.states(out)
                    failed = {sid: state for sid, state in states.items()
                              if state.get('status') in {'provider_unavailable', 'generation_failed', 'no_submission'}
                              and not state.get('submission') and state['model'] not in withdrawn and state.get('condition') not in frozen_tracks.get(state['model'],[])}
                    # Legacy checkpoints need receipt counts, not request sequence IDs.
                    from contextlib import closing
                    import sqlite3
                    from arena.call_counts import hydrate_calls
                    if failed:
                        with closing(sqlite3.connect((out / 'journal.sqlite').as_uri() + '?mode=ro', uri=True)) as db:
                            for sid, state in failed.items():
                                hydrate_calls(state, db, sid)
                    reasons = {sid: retry_reason(state, config['budget_per_session'], states.get(state.get('parent')))
                               for sid, state in failed.items()}
                    if failed and all(reasons.values()) and not any(state.get('status') == 'running' for state in states.values()):
                        raise ArenaError('No failed conversation can resume: ' + '; '.join(sid + ': ' + reason for sid, reason in reasons.items()))
            else:
                config = self.store.draft(draft_id)["config"]
                run_id = time.strftime("%Y%m%d-%H%M%S", time.gmtime()) + "-" + uuid4().hex[:8]
                out = self.store.runs / run_id
            if expected_config_sha256 is not None and expected_config_sha256 != digest(config):
                raise ArenaError('Participant settings changed after the launch preview. Reopen the launch dialog to review them.')
            if draft_id is None:
                from arena.roster import validate_effective
                validate_effective(config, withdrawn)
            else:
                validate_config(config)
            if retry_reasoning_effort is not None and retry_session is None:
                raise ArenaError('Choose a specific failed conversation to change reasoning effort')
            requested_models = [m for m in config['models'] if draft_id is not None or m['id'] not in withdrawn]
            if draft_id is None and retry_session is None:
                states = self.store.states(out)
                requested_models = [model for model in requested_models if not (
                    set(frozen_tracks.get(model['id'],[])) >= {'control','feedback'} and
                    all((states.get(f"{model['id']}-r{replicate}") or {}).get('submission') for replicate in range(config['replicates'])))]
            if retry_session is not None:
                if draft_id is not None or not isinstance(retry_session, str):
                    raise ArenaError('Retry requires an existing conversation')
                from arena.retries import retry_reason
                state = self.store.session(run_id, retry_session)
                if state['model'] in withdrawn: raise ArenaError('Reactivate this participant before retrying it')
                from contextlib import closing
                import sqlite3
                from arena.call_counts import hydrate_calls
                with closing(sqlite3.connect((out / 'journal.sqlite').as_uri() + '?mode=ro', uri=True)) as db:
                    hydrate_calls(state, db, retry_session)
                parent = self.store.session(run_id, state['parent']) if state.get('parent') else None
                reason = retry_reason(state, config['budget_per_session'], parent)
                if reason:
                    raise ArenaError(reason)
                requested_models = [m for m in requested_models if m['id'] == state['model']]
                if retry_reasoning_effort is not None and requested_models:
                    from arena.reasoning import validate_effort
                    validate_effort(requested_models[0], None if retry_reasoning_effort == 'provider-default' else retry_reasoning_effort)
                if not requested_models:
                    raise ArenaError('Conversation model is absent from the frozen configuration')
            paid = any(m["provider"] != "mock" for m in requested_models)
            configured_ceiling = config["spending"].get("max_total_usd")
            ceiling_matches = ((ceiling is None and configured_ceiling is None) or
                               (ceiling is not None and configured_ceiling is not None and amount(ceiling) == amount(configured_ceiling)))
            if paid and (confirm_paid is not True or not ceiling_matches):
                raise ArenaError("Confirm the spending limit before making API calls")
            env = dict(os.environ)
            for model in requested_models:
                if model["provider"] == "mock":
                    continue
                name = model["api_key_env"]
                secret = self.store.secrets.get(name) or os.environ.get(name)
                from arena.endpoints import optional_local_key
                if not secret and not optional_local_key(model):
                    raise ArenaError(f"Missing API key: {name}")
                if secret:
                    env[name] = secret
            from arena.engine import Engine
            engine = Engine()
            from arena.recovery import engine_compatible
            if draft_id is None and metadata["engine"] != engine.identity and not (
                    allow_updated_runner and engine_compatible(metadata['engine'], engine.identity)):
                raise ArenaError("The game engine or runtime changed. Restore the original engine to retain these match results.")
            identifier = uuid4().hex[:12]
            logs = self.store.state / "jobs"
            logs.mkdir(exist_ok=True)
            if draft_id is not None:
                manifest = logs / (identifier + ".json")
                write_json(manifest, config)
                args = ["experiment", "run", str(manifest), "--out", str(out)]
            else:
                args = (["experiment", "retry", str(out), "--session", retry_session] if retry_session
                        else ["experiment", "resume", str(out)])
            if retry_reasoning_effort is not None:
                args.extend(["--reasoning-effort", retry_reasoning_effort])
            if draft_id is None and allow_updated_runner:
                args.append("--allow-updated-runner")
            env["PYTHONUTF8"] = "1"
            env["ARENA_PROJECT_ROOT"] = str(ROOT)
            env["ARENA_STATE_ROOT"] = str(Path(engine.metadata["classes"]).parent)
            options = {"start_new_session": True} if os.name == "posix" else {
                "creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
            row = {"id": identifier, "run": run_id, "name": config["name"], "started_at": time.time(),
                   "status": "running", "resumed": draft_id is None, "retry_session": retry_session, "config_sha256": digest(config),
                   "log": identifier + ".log"}
            with (logs / row["log"]).open("wb") as log:
                if draft_id is not None:
                    self.store.inherit_workspace(draft_id,run_id)
                self.process = subprocess.Popen([sys.executable, "-m", "arena_web.worker", *args], cwd=ROOT,
                                                env=env, stdin=subprocess.DEVNULL, stdout=log,
                                                stderr=subprocess.STDOUT, **options)
            self.current = row
            self.rows.append(row)
            self._save()
            self.watcher = threading.Thread(target=self._watch, args=(self.process, row), daemon=True)
            self.watcher.start()
            return row

    def participants(self, run_id, selected, frozen_tracks=None):
        from contextlib import closing
        from arena.experiment import Journal, experiment_lock
        from arena.roster import update
        with self.lock:
            if self.process and self.process.poll() is None:
                raise ArenaError('Stop the running competition before editing its participants; checkpoints are retained')
            root = self.store.run_path(run_id)
            if (root / 'export.json').exists(): raise ArenaError('Exported archives are read-only')
            metadata = read_json(root / 'experiment.json')
            if 'config' not in metadata: raise ArenaError('Only model competitions support participant changes')
            with experiment_lock(root):
                journal = Journal(root)
                with closing(journal.db):
                    journal.verify()
                    change = update(root, journal, metadata['config'], self.store.catalog(), selected, frozen_tracks)
            return change

    def reconcile(self, run_id, sid, cost, note):
        from contextlib import closing
        from arena.experiment import Journal, experiment_lock
        from arena.recovery import reconcile
        with self.lock:
            if self.process and self.process.poll() is None:
                raise ArenaError('Stop the running competition before reconciling a request')
            root = self.store.run_path(run_id)
            if (root / 'export.json').exists():
                raise ArenaError('Exported archives are read-only')
            with experiment_lock(root):
                journal = Journal(root)
                with closing(journal.db):
                    journal.verify()
                    state = reconcile(journal, sid, cost, note)
            return {'session':sid, 'status':state['status']}

    def _watch(self, process, row):
        code = process.wait()
        with self.lock:
            report_path = self.store.runs / row['run'] / 'report.json'
            try: report = read_json(report_path) if report_path.exists() else {}
            except (OSError, ValueError, ArenaError): report = {}
            blocked = report.get('waiting_for_recovery') or report.get('incomplete')
            row.update(status="stopped" if row["status"] == "stopping" else "blocked" if code == 0 and blocked else "completed" if code == 0 else "failed",
                       returncode=code, finished_at=time.time())
            if row['status'] == 'blocked':
                row['note'] = 'Waiting for failed conversations to be recovered. Saved submissions and fights are retained.'
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
