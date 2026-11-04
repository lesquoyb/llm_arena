"""Supervise local experiments (one process per competition), using the CLI checkpoints."""
from __future__ import annotations

import os
import json
import re
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


def failure_reason(log_path, report=None):
    """The error that ended a failed job, read from the end of its run log."""
    try:
        with open(log_path, 'rb') as handle:
            handle.seek(0, os.SEEK_END); handle.seek(max(0, handle.tell() - 20000))
            tail = handle.read().decode('utf-8', 'replace')
            lines = [line.strip() for line in tail.splitlines() if line.strip()]
    except OSError:
        tail, lines = '', []
    for line in reversed(lines):
        if line.startswith('Arena error:'):
            return line
    # An unexpected exception ends with "Type: message" after its traceback.
    for line in reversed(lines):
        if re.match(r'^[\w.]*(?:Error|Exception|ExceptionGroup|Interrupt):', line):
            return 'Runner error: ' + line[:500]
    failures = (report or {}).get('session_failures')
    if not failures:
        # CLI workers can exit nonzero after printing a structured incomplete
        # report, without a traceback. JSON diagnostic fields are not errors.
        for match in reversed(list(re.finditer(r'"session_failures"\s*:\s*', tail))):
            try:
                failures, _ = json.JSONDecoder().raw_decode(tail[match.end():])
            except ValueError:
                continue
            if isinstance(failures, list):
                break
    if isinstance(failures, list):
        messages = [f'{item.get("session", "unknown session")}: {item["message"]}'
                    for item in failures if isinstance(item, dict) and item.get('message')]
        if messages:
            return ('Conversation failed: ' + '; '.join(messages))[:1500]
    return 'The runner stopped with an error; see the run log.'


class Jobs:
    def __init__(self, store):
        self.store = store
        self.lock = threading.RLock()
        # Several competitions may run at once; each owns its own process.
        # process/current keep the most recently started one for callers that
        # only follow a single job.
        self.process = None
        self.current = None
        self.active = {}
        self.watcher = None
        self.path = store.state / "jobs.json"
        self.rows = read_json(self.path) if self.path.exists() else []
        for row in self.rows:
            if row["status"] in {"running", "stopping"}:
                row["status"] = "interrupted"
                row["note"] = "The server was interrupted. Check the log before resuming."

    def _entries(self):
        entries = list(getattr(self, "active", {}).values())
        if self.process is not None and self.current is not None and all(process is not self.process for process, _ in entries):
            entries.append((self.process, self.current))
        return entries

    def running(self, run_id=None):
        """(process, row) of the live job of a competition, or of any competition."""
        for process, row in self._entries():
            if process.poll() is None and (run_id is None or row.get('run') == run_id):
                return process, row
        return None, None

    def listing(self):
        with self.lock:
            rows = []
            for original in reversed(self.rows):
                row = dict(original)
                # Repair previously saved misleading notes for existing runs,
                # without rewriting their logs or experiment artifacts.
                if row.get('status') == 'failed' and re.match(r'^Runner error:\s*["{\[]', row.get('note', '')):
                    path = self.store.state / 'jobs' / row['log']
                    try: stamp = (path.stat().st_mtime_ns, path.stat().st_size)
                    except OSError: stamp = None
                    cache = self.__dict__.setdefault('_failure_notes', {})
                    key = (row['id'], stamp)
                    if key not in cache: cache[key] = failure_reason(path)
                    row['note'] = cache[key]
                rows.append(row)
            return rows

    def _save(self):
        write_json(self.path, self.rows)

    def launch(self, *, draft_id=None, run_id=None, confirm_paid=False, ceiling=None, retry_session=None, expected_config_sha256=None, allow_updated_runner=False, retry_reasoning_effort=None):
        with self.lock:
            if (draft_id is None) == (run_id is None):
                raise ArenaError("Choose a configuration or a competition to resume")
            if run_id is not None and self.running(run_id)[0] is not None:
                raise ArenaError("This competition is already running. Wait for it or stop it.")
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
                from arena.recovery import needs_reconciliation, zero_cost_requests
                external = {m['id'] for m in config['models'] if m['provider'] != 'mock'}
                free = {m['id'] for m in config['models'] if zero_cost_requests(m)}
                from arena.session_metadata import FIELDS
                states=self.store.states(out,FIELDS)
                blocked = [sid for sid,state in states.items() if state['model'] not in withdrawn and needs_reconciliation(state, state['model'] in external) and (state['model'] not in free or amount(state.get('money_reserved','0'))>0)]
                if blocked:
                    raise ArenaError('Resolve billing in Conversations before resuming: ' + ', '.join(blocked))
                for state in states.values():
                    if state['model'] in free and state.get('status')=='needs_reconciliation' and amount(state.get('money_reserved','0'))==0:
                        state.update(status='provider_unavailable' if state.get('in_flight') else 'running',in_flight=False)
                if retry_session is None:
                    from arena.retries import retry_reason
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
                    from arena.budget_context import tool_budget_exhausted
                    if failed and all(reasons.values()) and not any(state.get('status') == 'running' or tool_budget_exhausted(state,config['budget_per_session']) for state in states.values()):
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
                from arena.reference_strategies import repetitions
                sampled={**config,'_fixed_reference_repetitions':metadata.get('fixed_reference_repetitions',config['replicates'])}
                requested_models = [model for model in requested_models if not (
                    set(frozen_tracks.get(model['id'],[])) >= set(config.get('improvement_conditions',['control','feedback'])) and
                    all((states.get(f"{model['id']}-r{replicate}") or {}).get('submission') for replicate in range(repetitions(sampled,model))))]
            if retry_session is not None:
                if draft_id is not None or not isinstance(retry_session, str):
                    raise ArenaError('Retry requires an existing conversation')
                from arena.retries import retry_reason
                state = self.store.session(run_id, retry_session)
                if state['model'] in free and state.get('status')=='needs_reconciliation' and amount(state.get('money_reserved','0'))==0:
                    state.update(status='provider_unavailable' if state.get('in_flight') else 'running',in_flight=False)
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
            # Progress lines must reach the run log as they are printed.
            env["PYTHONUNBUFFERED"] = "1"
            env["ARENA_PROJECT_ROOT"] = str(ROOT)
            env["ARENA_STATE_ROOT"] = str(Path(engine.metadata["classes"]).parent)
            options = {"start_new_session": True} if os.name == "posix" else {
                "creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
            row = {"id": identifier, "run": run_id, "name": config["name"], "started_at": time.time(),
                   "status": "running", "resumed": draft_id is None, "retry_session": retry_session, "config_sha256": digest(config),
                   "log": identifier + ".log"}
            if draft_id is None:
                write_json(out/'activity.json',{'kind':'starting','started_at':row['started_at']})
            with (logs / row["log"]).open("wb") as log:
                if draft_id is not None:
                    self.store.inherit_workspace(draft_id,run_id)
                self.process = subprocess.Popen([sys.executable, "-m", "arena_web.worker", *args], cwd=ROOT,
                                                env=env, stdin=subprocess.DEVNULL, stdout=log,
                                                stderr=subprocess.STDOUT, **options)
            self.current = row
            self.active[run_id] = (self.process, row)
            self.rows.append(row)
            self._save()
            self.watcher = threading.Thread(target=self._watch, args=(self.process, row), daemon=True)
            self.watcher.start()
            return row

    def recover_conversation(self, run_id, sid, action='continue', message=None):
        if action not in {'continue','restart','pause'}:raise ArenaError('Unknown recovery action')
        if message is not None and (not isinstance(message,str) or len(message)>12000):raise ArenaError('Resume message must be text of at most 12000 characters')
        message=message.strip() if message else None
        with self.lock:
            root=self.store.run_path(run_id)
            state=self.store.session(run_id,sid)
            metadata=read_json(root/'experiment.json')
            if 'config' not in metadata or (root/'export.json').exists():raise ArenaError('Only original competitions can be recovered')
            from arena.retries import retry_reason
            from arena.roster import effective, active
            config=effective(root,metadata['config'])
            parent=self.store.session(run_id,state['parent']) if state.get('parent') else None
            # The coordinator reconciles explicit zero-price requests on launch.
            # Permit enqueueing them without asking the user to confirm a zero bill.
            from arena.recovery import zero_cost_requests, needs_reconciliation
            model=next(model for model in config['models'] if model['id']==state['model'])
            if zero_cost_requests(model) and needs_reconciliation(state) and amount(state.get('money_reserved','0'))==0:
                state={**state,'in_flight':False,'money_reserved':'0',
                       'status':'running' if state.get('pending') else 'provider_unavailable'}
            if state.get('submission'):raise ArenaError('This conversation already has a frozen submission')
            process,current=self.running(run_id)
            running=process is not None
            live=running and current['status']=='running'
            reason=retry_reason(state,{} if action=='restart' else config['budget_per_session'],parent)
            if action=='pause' or (action=='continue' and state.get('status')=='running' and (live or not state.get('in_flight'))):reason=None
            from arena.budget_context import tool_budget_exhausted
            if reason and (action=='restart' or not tool_budget_exhausted(state,config['budget_per_session'])):raise ArenaError(reason)
            if not active(config,state):raise ArenaError('Reactivate this participant before retrying it')
            process,current=self.running(run_id)
            running=process is not None
            if running and current['status']!='running':
                raise ArenaError('This competition is stopping')
            identifier=uuid4().hex
            write_json(root/'recovery-commands'/(identifier+'.json'),{'id':identifier,'session':sid,'action':action,'message':message,'requested_at':time.time()})
            write_json(root/'conversation-controls'/(sid+'.json'),{'paused':action=='pause','requested_at':time.time()})
            if not running and action!='pause':
                try:self.launch(run_id=run_id,confirm_paid=True,ceiling=config['spending'].get('max_total_usd'),allow_updated_runner=True)
                except BaseException:
                    (root/'recovery-commands'/(identifier+'.json')).unlink(missing_ok=True)
                    raise
            return {'id':identifier,'status':'queued','session':sid}

    def provider_limits(self, run_id, limits=None):
        from arena.provider_limits import endpoint, configured, limit, validate
        root=self.store.run_path(run_id)
        metadata=read_json(root/'experiment.json')
        if 'config' not in metadata:raise ArenaError('Only model competitions have provider limits')
        models=metadata['config']['models']
        known={endpoint(model) for model in models if model['provider']!='mock'}
        if limits is not None:
            if (root/'export.json').exists():raise ArenaError('Exported archives are read-only')
            validate(limits)
            if set(limits)-known:raise ArenaError('Unknown provider endpoint')
            write_json(root/'provider-control.json',{'endpoint_limits':limits,'requested_at':time.time()})
        saved=configured(root)
        return {'endpoints':[{'endpoint':key,'limit':limit(next(model for model in models if endpoint(model)==key),saved),
                              'models':[model['id'] for model in models if endpoint(model)==key]} for key in sorted(known)]}

    def retry_policy(self, run_id, sid, paused):
        if not isinstance(paused,bool):raise ArenaError('Expected a retry pause switch')
        root=self.store.run_path(run_id)
        if (root/'export.json').exists():raise ArenaError('Exported archives are read-only')
        state=self.store.session(run_id,sid)
        if state.get('submission'):raise ArenaError('This conversation already has a frozen submission')
        policy={'paused':paused,'requested_at':time.time()}
        write_json(root/'retry-policies'/(sid+'.json'),policy)
        return {'session':sid,**policy}

    def execution_control(self, run_id, parallel_fights):
        from arena.core import integer
        integer(parallel_fights,1,None,'parallel_fights')
        with self.lock:
            root=self.store.run_path(run_id)
            if (root/'export.json').exists():raise ArenaError('Exported archives are read-only')
            if 'config' not in read_json(root/'experiment.json'):raise ArenaError('Only managed model competitions support this action')
            command={'id':uuid4().hex,'parallel_fights':parallel_fights,'requested_at':time.time()}
            write_json(root/'execution-requests'/(command['id']+'.json'),command)
            write_json(root/'execution-control.json',command)
            return {**command,'status':'requested'}

    def retry_fights(self, run_id, *, include_ready=False):
        with self.lock:
            root=self.store.run_path(run_id)
            if (root/'export.json').exists():raise ArenaError('Exported archives are read-only')
            if 'config' not in read_json(root/'experiment.json'):raise ArenaError('Only managed model competitions support this action')
            process,current=self.running(run_id)
            if process is not None:
                if current['status']!='running':
                    raise ArenaError('This competition is stopping')
                command={'id':uuid4().hex,'requested_at':time.time(),'include_ready':include_ready}
                write_json(root/'fight-retry-requests'/(command['id']+'.json'),command)
                return {'status':'queued','no_model_requests':True}
            from arena.engine import Engine
            from arena.recovery import engine_compatible
            engine=Engine();metadata=read_json(root/'experiment.json')
            if not engine_compatible(metadata['engine'],engine.identity):raise ArenaError('Restore the original game engine before retrying fights')
            identifier=uuid4().hex[:12];logs=self.store.state/'jobs';logs.mkdir(exist_ok=True)
            env=dict(os.environ);env.update(PYTHONUTF8='1',PYTHONUNBUFFERED='1',ARENA_PROJECT_ROOT=str(ROOT),ARENA_STATE_ROOT=str(Path(engine.metadata['classes']).parent))
            options={'start_new_session':True} if os.name=='posix' else {'creationflags':subprocess.CREATE_NEW_PROCESS_GROUP}
            row={'id':identifier,'run':run_id,'name':metadata.get('config',{}).get('name',run_id),'started_at':time.time(),
                 'status':'running','mode':'retry_fights','log':identifier+'.log'}
            with (logs/row['log']).open('wb') as log:
                self.process=subprocess.Popen([sys.executable,'-m','arena_web.worker','experiment','retry-fights',str(root),*(['--include-ready'] if include_ready else [])],
                    cwd=ROOT,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,**options)
            self.current=row;self.active[run_id]=(self.process,row);self.rows.append(row);self._save()
            self.watcher=threading.Thread(target=self._watch,args=(self.process,row),daemon=True);self.watcher.start()
            return row

    def compact_storage(self, run_id):
        """Move a stopped competition's fight folders into its SQLite stores."""
        with self.lock:
            root=self.store.run_path(run_id)
            if (root/'export.json').exists():raise ArenaError('Exported archives are read-only')
            if self.running(run_id)[0] is not None:raise ArenaError('Stop the competition before compacting its storage')
            identifier=uuid4().hex[:12];logs=self.store.state/'jobs';logs.mkdir(exist_ok=True)
            env=dict(os.environ);env.update(PYTHONUTF8='1',PYTHONUNBUFFERED='1',ARENA_PROJECT_ROOT=str(ROOT))
            options={'start_new_session':True} if os.name=='posix' else {'creationflags':subprocess.CREATE_NEW_PROCESS_GROUP}
            metadata=read_json(root/'experiment.json')
            row={'id':identifier,'run':run_id,'name':metadata.get('config',metadata.get('manifest',{})).get('name',run_id),'started_at':time.time(),
                 'status':'running','mode':'compact_storage','log':identifier+'.log'}
            with (logs/row['log']).open('wb') as log:
                self.process=subprocess.Popen([sys.executable,'-m','arena','storage','compact',str(root)],
                    cwd=ROOT,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,**options)
            self.current=row;self.active[run_id]=(self.process,row);self.rows.append(row);self._save()
            self.watcher=threading.Thread(target=self._watch,args=(self.process,row),daemon=True);self.watcher.start()
            return row

    def participants(self, run_id, selected, frozen_tracks=None, compare_previous_round=None, parallel_fights=None, request_order=None, parallel_requests=None, rule_change=None, max_retries=None):
        from contextlib import closing
        from arena.experiment import Journal, experiment_lock
        from arena.roster import update
        with self.lock:
            if self.running(run_id)[0] is not None:
                raise ArenaError('Stop the running competition before changing participant or metric-collection settings; checkpoints are retained')
            root = self.store.run_path(run_id)
            if (root / 'export.json').exists(): raise ArenaError('Exported archives are read-only')
            metadata = read_json(root / 'experiment.json')
            if 'config' not in metadata: raise ArenaError('Only model competitions support participant changes')
            with experiment_lock(root):
                journal = Journal(root, audit_cache=False)
                with closing(journal.db):
                # The runner audits the whole journal when it resumes; repeating
                # that here made a settings change wait up to a minute.
                    change = update(root, journal, metadata['config'], self.store.catalog(), selected, frozen_tracks, compare_previous_round, parallel_fights, request_order, parallel_requests, rule_change, max_retries)
            if parallel_fights is not None:self.execution_control(run_id,parallel_fights)
            return change

    def reconcile(self, run_id, sid, cost, note):
        from contextlib import closing
        from arena.experiment import Journal, experiment_lock
        from arena.recovery import reconcile
        with self.lock:
            if self.running(run_id)[0] is not None:
                raise ArenaError('Stop the running competition before reconciling a request')
            root = self.store.run_path(run_id)
            if (root / 'export.json').exists():
                raise ArenaError('Exported archives are read-only')
            with experiment_lock(root):
                journal = Journal(root, audit_cache=False)
                with closing(journal.db):
                # The runner audits the whole journal when it resumes; repeating
                # that here made a settings change wait up to a minute.
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
            if row.get('mode')=='compact_storage':
                row['status']='stopped' if row['status']=='stopped' else 'completed' if code==0 else 'failed'
                row['note']='Fight folders moved into SQLite stores.' if code==0 else 'Compaction stopped; stored fights are kept and the command can be run again.'
            elif row.get('mode')=='retry_fights':
                if row['status']!='stopped':row['status']='completed' if code==0 else 'failed'
                row['note']='Engine fight recovery finished; model conversations were not resumed.'
            if row['status'] == 'failed' and not row.get('note'):
                row['note'] = failure_reason(self.store.state / 'jobs' / row['log'], report)
            if row['status'] == 'blocked' and row.get('mode')!='retry_fights':
                row['note'] = ('Engine fights remain incomplete. Retry failed fights, then resume to continue the next round.'
                               if not report.get('blocked_sessions') and ((report.get('tournament') or {}).get('failed') or ((report.get('evolution') or {}).get('contemporaries') or {}).get('failed'))
                               else 'Waiting for failed conversations to be recovered. Saved submissions and fights are retained.')
            self._save()
            root=self.store.runs/row['run']
            owner=self.active.get(row['run'],(None,None))[0]
            if owner is process:self.active.pop(row['run'],None)
            if (owner is process or self.process is process) and row['status']!='stopped' and any((root/'fight-retry-requests').glob('*.json')):
                self.retry_fights(row['run'],include_ready=any(read_json(path).get('include_ready') for path in (root/'fight-retry-requests').glob('*.json')))
            elif (owner is process or self.process is process) and row['status']!='stopped' and code==0 and any((root/'recovery-commands').glob('*.json')):
                metadata=read_json(root/'experiment.json')
                self.launch(run_id=row['run'],confirm_paid=True,ceiling=metadata.get('config',{}).get('spending',{}).get('max_total_usd'),allow_updated_runner=True)

    def stop(self, identifier):
        with self.lock:
            process, row = next(((process, row) for process, row in self._entries()
                                 if row.get('id') == identifier and process.poll() is None), (None, None))
            if process is None:
                raise ArenaError("This run is no longer active")
            row["status"] = "stopping"
            self._save()
            if os.name == "nt":
                try:
                    process.send_signal(signal.CTRL_BREAK_EVENT)
                except OSError:
                    from arena.engine import stop_worker
                    stop_worker(process)
            else:
                process.send_signal(signal.SIGINT)
            return row

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
            active = [(process, row) for process, row in self._entries() if process.poll() is None]
        for process, row in active:
            self.stop(row["id"])
        for process, row in active:
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                from arena.engine import stop_worker
                stop_worker(process)
        if self.watcher:
            self.watcher.join(timeout=5)
