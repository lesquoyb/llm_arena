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

from arena.core import ArenaError, ROOT, STATE_ROOT, digest, file_hash, is_link, read_json, write_json
from arena.experiment import plan, validate_config
from arena.preparation import local_path
from .workspaces import Workspaces


TERMINAL = {"submitted", "budget_exhausted", "no_submission", "generation_failed",
            "provider_unavailable", "needs_reconciliation"}


def safe_path(root: Path, name: str) -> Path:
    path = local_path(root, name)
    if not path.resolve().is_relative_to(root.resolve()):
        raise ArenaError("Path outside the allowed directory")
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
            if call.get("name") == "configure_team" and not result.get("error"):
                args = {"path": "team.json", "content": result.get("content")}
            if (call.get("name") in {"write_file", "configure_team"} and not result.get("error")
                    and isinstance(args.get("content"), str) and isinstance(args.get("path"), str)):
                content = args["content"]
                expected = hashlib.sha256(content.encode("utf-8")).hexdigest()
                if result.get("sha256") != expected:
                    continue
                yield {"message": index, "generation": generation, "path": args["path"],
                       "content": content, "sha256": expected}


class Store(Workspaces):
    def __init__(self, runs: Path | None = None, state: Path | None = None):
        self.runs = (runs or ROOT / "runs").resolve()
        self.state = (state or STATE_ROOT / "ui").resolve()
        self.runs.mkdir(parents=True, exist_ok=True)
        self.state.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.secrets = {}
        self._cache = {}
        self._usage_cache = {}
        from collections import OrderedDict
        self._session_metadata_cache = OrderedDict()
        self._session_cache=OrderedDict()

    def json(self, path, default=None):
        if any(is_link(p) for p in [path, *path.parents]):
            raise ArenaError("Links cannot be browsed")
        if not path.is_file():
            return default
        stat = path.stat()
        stamp = (stat.st_mtime_ns, stat.st_size)
        with self.lock:
            cached = self._cache.get(path)
        if cached and cached[0] == stamp:
            return copy.deepcopy(cached[1])
        # Replay parsing must not hold the lock used by unrelated navigation requests.
        value = read_json(path)
        if stat.st_size < 200_000:
            with self.lock:
                if len(self._cache) > 256:
                    self._cache.clear()
                self._cache[path] = (stamp, value)
            return copy.deepcopy(value)
        return value

    def catalog(self):
        with self.lock:
            value = self.json(self.state / "participants.json")
            if value is None:
                value = [{"id": "mock-repair", "provider": "mock", "profile": "repair-and-submit"},
                         {"id": "mock-single", "provider": "mock", "profile": "single-shot"}]
            return value

    def participants(self):
        from arena.endpoints import optional_local_key
        return [{"spec": m, "key_optional": optional_local_key(m), "key_configured": bool(self.secrets.get(m.get("api_key_env")) or
                                                    os.environ.get(m.get("api_key_env", "")))}
                for m in self.catalog()]

    def model_size(self, model, catalog=None):
        """Frozen metadata wins; old runs can use an explicitly matching profile."""
        value=model.get('model_size_billion') or model.get('strategy',{}).get('origin',{}).get('model_size_billion')
        if value is not None:return value
        keys=('id','provider','model','endpoint')
        current=next((row for row in (self.catalog() if catalog is None else catalog) if all(row.get(key)==model.get(key) for key in keys)),{})
        return current.get('model_size_billion')

    def participant_groups(self):
        return self.json(self.state/'participant-groups.json',[])

    def save_participant_group(self, name, members, identifier=None):
        if not isinstance(name,str) or not name.strip() or len(name.strip())>100:
            raise ArenaError('Group name must contain 1 to 100 characters')
        if not isinstance(members,list) or len(members)>2000 or any(not isinstance(member,str) for member in members):
            raise ArenaError('Select at most 2,000 participant profiles')
        with self.lock:
            groups=self.participant_groups()
            if identifier is not None and not any(row['id']==identifier for row in groups):
                raise ArenaError('Participant group not found')
            if any(row['id']!=identifier and row['name'].casefold()==name.strip().casefold() for row in groups):
                raise ArenaError('A participant group with this name already exists')
            known={row['id'] for row in self.catalog()}
            if set(members)-known: raise ArenaError('Unknown participant: '+', '.join(sorted(set(members)-known)))
            row={'id':identifier or uuid4().hex[:12],'name':name.strip(),'members':list(dict.fromkeys(members))}
            write_json(self.state/'participant-groups.json',[g for g in groups if g['id']!=row['id']]+[row])
            return row

    def delete_participant_group(self, identifier):
        with self.lock:
            groups=self.participant_groups()
            if not any(row['id']==identifier for row in groups): raise ArenaError('Participant group not found')
            write_json(self.state/'participant-groups.json',[row for row in groups if row['id']!=identifier])
        return {'deleted':identifier}

    def set_participant_groups(self, participant, identifiers):
        if not isinstance(identifiers,list) or any(not isinstance(key,str) for key in identifiers):
            raise ArenaError('Invalid participant groups')
        with self.lock:
            if not any(row['id']==participant for row in self.catalog()): raise ArenaError('Unknown participant')
            groups=self.participant_groups()
            if set(identifiers)-{row['id'] for row in groups}: raise ArenaError('Participant group not found')
            for row in groups:
                row['members']=[member for member in row['members'] if member!=participant]
                if row['id'] in identifiers:row['members'].append(participant)
            write_json(self.state/'participant-groups.json',groups)
        return {'saved':participant}

    def providers(self):
        from arena.endpoints import optional_local_key
        return [{'spec':spec,'key_optional':optional_local_key(spec),
                 'key_configured':bool(self.secrets.get(spec['api_key_env']) or os.environ.get(spec['api_key_env']))}
                for spec in self.json(self.state/'providers.json',[])]

    def save_provider(self, spec, secret=None):
        import re
        from arena.api_providers import DEFAULT_ENDPOINTS
        from arena.endpoints import validate_endpoint
        if not isinstance(spec,dict) or set(spec)-{'id','provider','endpoint','api_key_env'}:
            raise ArenaError('Invalid provider fields')
        if not isinstance(spec.get('id'),str) or not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,39}',spec['id']):
            raise ArenaError('Provider ID must contain 1 to 40 letters, digits, underscores or hyphens')
        if spec.get('provider') not in {'openai','openai-compatible','anthropic','gemini'}:
            raise ArenaError('Invalid provider protocol')
        if not isinstance(spec.get('api_key_env'),str) or not re.fullmatch(r'ARENA_[A-Z0-9_]+',spec['api_key_env']):
            raise ArenaError('Use an ARENA_ environment variable name for this provider')
        validate_endpoint(spec.get('endpoint') or DEFAULT_ENDPOINTS.get(spec['provider'],''))
        if secret is not None and (not isinstance(secret,str) or len(secret)>8192):
            raise ArenaError('Invalid API key')
        with self.lock:
            values=[row['spec'] for row in self.providers() if row['spec']['id']!=spec['id']]
            write_json(self.state/'providers.json',values+[spec])
            if secret: self.secrets[spec['api_key_env']]=secret
        return {'saved':spec['id']}

    def delete_provider(self, identifier):
        with self.lock:
            write_json(self.state/'providers.json',[row['spec'] for row in self.providers() if row['spec']['id']!=identifier])
        return {'deleted':identifier}

    def create_provider_participants(self, identifier, models):
        with self.lock:
            spec=next((row['spec'] for row in self.providers() if row['spec']['id']==identifier),None)
            if not spec: raise ArenaError('Unknown saved provider')
            if not isinstance(models,list) or not 1<=len(models)<=100:
                raise ArenaError('Select 1 to 100 models')
            existing=self.catalog();ids={row['id'] for row in existing};created=[]
            for row in models:
                if not isinstance(row,dict) or set(row)-{'id','model','pricing','max_output_tokens','model_size_billion'}:
                    raise ArenaError('Invalid participant fields')
                model={key:value for key,value in spec.items() if key!='id'}
                model.update(row)
                if model.get('id') in ids: raise ArenaError('Participant ID already exists: '+model['id'])
                self.validate_model(model)
                ids.add(model['id']);created.append(model)
            write_json(self.state/'participants.json',existing+created)
        return {'created':[row['id'] for row in created]}

    def validate_model(self, model):
        config = read_json(ROOT / "configs/offline-complete.json")
        config["models"] = [model]
        if model.get("provider") != "mock":
            config["spending"] = {"allow_paid_calls": True, "max_total_usd": "1"}
            config["budget_per_session"].update(max_input_tokens=1_000_000, max_output_tokens=100_000, max_cost_usd="1")
        validate_config(config)

    def save_participant(self, model, secret=None):
        self.validate_model(model)
        from arena.reasoning import validate_effort
        validate_effort(model, model.get('parameters', {}).get('reasoning_effort'))
        if secret is not None and (not isinstance(secret, str) or len(secret) > 8192):
            raise ArenaError("Invalid API key")
        if secret and not model.get("api_key_env", "").startswith("ARENA_"):
            raise ArenaError("Use an ARENA_ variable name for a key entered here")
        with self.lock:
            models = self.catalog()
            models = [m for m in models if m["id"] != model["id"]] + [model]
            write_json(self.state / "participants.json", models)
            if secret:
                self.secrets[model["api_key_env"]] = secret
        return {"saved": model["id"]}

    def import_strategy(self, identifier, sid, name):
        from arena.core import submission, source_files
        root=self.run_path(identifier)
        state=self.session(identifier,sid)
        info=state.get('submission')
        if not info:
            raise ArenaError('This conversation has no submitted strategy')
        source=safe_path(root,'sessions/'+sid+'/submission')
        if submission(source,info['entrypoint']) != info:
            raise ArenaError('Submitted source no longer matches its frozen fingerprint')
        with self.lock:
            if any(m['id']==name for m in self.catalog()):
                raise ArenaError('A participant with this name already exists')
            metadata=self.json(root/'experiment.json')
            original=next((m for m in metadata['config']['models'] if m['id']==state['model']),{})
            spec={'id':name,'provider':'mock','profile':'saved-strategy','strategy':{
                'files':{path:content.decode('utf-8') for path,content in source_files(source).items()},
                'submission':info,'scenario_sha256':digest(metadata['config']['scenario']),
                'origin':{'run':identifier,'session':sid,'model':state['model'],
                          'round':state.get('generation',0)+1,'condition':state.get('condition','initial'),
                          'model_size_billion':self.model_size(original)}}}
            # Validation uses the source scenario, rather than the default scenario.
            config=copy.deepcopy(metadata['config']);config['models']=[spec]
            config['spending']={'allow_paid_calls':False,'max_total_usd':0}
            validate_config(config)
            write_json(self.state/'participants.json',self.catalog()+[spec])
        return {'saved':name}

    def delete_participant(self, identifier):
        with self.lock:
            groups=self.participant_groups()
            for row in groups:row['members']=[member for member in row['members'] if member!=identifier]
            write_json(self.state/'participant-groups.json',groups)
            write_json(self.state / "participants.json", [m for m in self.catalog() if m["id"] != identifier])
        return {"deleted": identifier}

    def resolve_models(self, config):
        result = copy.deepcopy(config)
        catalog = {model['id']: model for model in self.catalog()}
        from arena.reference_strategies import for_scenario
        result['models'] = [for_scenario(catalog.get(model['id'], model),result['scenario']) for model in result['models']]
        return result

    def drafts(self):
        rows = [self.json(p) for p in sorted((self.state / "competitions").glob("*.json"))]
        memberships=self.workspace_index()['drafts']
        return [{**row, 'workspace_id':memberships.get(row['id']), 'config': self.resolve_models(row['config'])} for row in rows]

    def save_draft(self, config, identifier=None, **options):
        config = self.resolve_models(config)
        validate_config(config)
        identifier = identifier or uuid4().hex[:12]
        path = safe_path(self.state / "competitions", identifier + ".json")
        value = {"id": identifier, "updated_at": time.time(), "config": config}
        with self.lock:
            if options.get('workspace_id') is not None: self.workspace(options['workspace_id'])
            write_json(path, value)
            if 'workspace_id' in options:
                self.assign_workspace(options['workspace_id'],drafts=[identifier])
        return {**value, 'workspace_id':self.workspace_index()['drafts'].get(identifier), "plan": plan(config)}

    def delete_draft(self, identifier):
        with self.lock:
            index=self.workspace_index()
            index['drafts'].pop(identifier,None)
            write_json(self.state/'workspaces.json',index)
            safe_path(self.state / "competitions", identifier + ".json").unlink(missing_ok=True)
        return {"deleted": identifier}

    def draft(self, identifier):
        result = self.json(safe_path(self.state / "competitions", identifier + ".json"))
        if result is None:
            raise ArenaError("Configuration not found")
        return {**result, "workspace_id":self.workspace_index()['drafts'].get(identifier), "config": self.resolve_models(result["config"])}

    def run_path(self, identifier):
        root = safe_path(self.runs, identifier)
        if not (root / "experiment.json").is_file():
            raise ArenaError("Competition not found")
        return root

    def run_paths(self):
        for base, dirs, files in os.walk(self.runs, followlinks=False):
            directory = Path(base)
            dirs[:] = [d for d in dirs if not is_link(directory / d) and d not in {".git", ".arena"}]
            if "experiment.json" in files:
                yield directory
                dirs[:] = []

    def states(self, root, fields=None):
        path = root / "journal.sqlite"
        if not path.is_file() or is_link(path):
            return {}
        # mode=ro avoids schema migrations, checkpoint writes and creating missing DBs.
        with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=2)) as connection:
            if not connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='sessions'").fetchone():
                return {}
            if fields:
                from arena.session_metadata import FIELDS
                if set(fields)<=set(FIELDS):
                    connection.execute('BEGIN')
                    tables={row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                    fingerprints=dict(connection.execute("SELECT id,sha256 FROM objects WHERE kind='Session'")) if 'objects' in tables else {}
                    metadata={sid:(sha,raw) for sid,sha,raw in connection.execute('SELECT id,checkpoint_sha256,metadata FROM session_metadata')} if 'session_metadata' in tables else {}
                    ids=[row[0] for row in connection.execute('SELECT id FROM sessions ORDER BY id')]
                    result={}
                    paths=", ".join("'$."+field+"'" for field in FIELDS)
                    for sid in ids:
                        fingerprint=fingerprints.get(sid)
                        cached=metadata.get(sid)
                        key=(str(root),sid,fingerprint)
                        if cached and fingerprint and cached[0]==fingerprint and 'replay_reads' in json.loads(cached[1]):
                            value=json.loads(cached[1])
                        else:
                            with self.lock:
                                value=self._session_metadata_cache.get(key) if fingerprint else None
                                if value is not None:self._session_metadata_cache.move_to_end(key)
                            if value is None:
                                raw,count,replays=connection.execute("SELECT json_extract(state,"+paths+"),json_array_length(state,'$.history'),(SELECT count(*) FROM json_each(state,'$.history') WHERE json_extract(value,'$.role')='tool' AND json_extract(value,'$.name') IN ('read_replay','read_past_fight')) FROM sessions WHERE id=?",(sid,)).fetchone()
                                value={**{field:item for field,item in zip(FIELDS,json.loads(raw)) if item is not None},'messages':count or 0,'replay_reads':replays}
                                if fingerprint:
                                    with self.lock:
                                        self._session_metadata_cache[key]=value
                                        while len(self._session_metadata_cache)>4096:self._session_metadata_cache.popitem(last=False)
                        result[sid]={**{field:copy.deepcopy(value[field]) for field in fields if field in value},'messages':value.get('messages',0)}
                    return result
                paths = ", ".join("'$." + field + "'" for field in fields)
                rows = connection.execute("SELECT id,json_extract(state," + paths + "),json_array_length(state,'$.history') FROM sessions ORDER BY id")
                return {sid: {**{key:value for key,value in zip(fields,json.loads(raw)) if value is not None}, "messages": count or 0}
                        for sid,raw,count in rows}
            return {sid: json.loads(raw) for sid, raw in connection.execute("SELECT id,state FROM sessions ORDER BY id")}

    def session(self, identifier, sid):
        path = self.run_path(identifier) / "journal.sqlite"
        if not path.is_file() or is_link(path):raise ArenaError("Session not found")
        with closing(sqlite3.connect(path.as_uri()+"?mode=ro",uri=True,timeout=2)) as connection:
            connection.execute('BEGIN')
            objects=connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='objects'").fetchone()
            fingerprint=connection.execute("SELECT sha256 FROM objects WHERE id=? AND kind='Session'",(sid,)).fetchone() if objects else None
            key=(str(path),sid,fingerprint[0]) if fingerprint else None
            with self.lock:
                cached=self._session_cache.get(key) if key else None
                if cached is not None:self._session_cache.move_to_end(key)
            if cached is None:
                row=connection.execute('SELECT state FROM sessions WHERE id=?',(sid,)).fetchone()
                if row is None:raise ArenaError('Session not found')
                cached=json.loads(row[0])
                if key and len(row[0])<=16_000_000:
                    with self.lock:
                        self._session_cache[key]=cached
                        while len(self._session_cache)>2:self._session_cache.popitem(last=False)
        # Callers can annotate their view without changing a cached checkpoint.
        return copy.deepcopy(cached)

    def listing(self):
        rows = []
        for path in self.run_paths():
            identifier = path.relative_to(self.runs).as_posix()
            try:
                metadata = self.json(path / "experiment.json")
                config = metadata.get("config", metadata.get("manifest", {}))
                if 'config' in metadata:
                    from arena.roster import effective
                    config = effective(path, config)
                from arena.roster import snapshot
                withdrawn=set((snapshot(path) or {}).get('withdrawn',[]))
                report = self.json(path / "report.json", {})
                rows.append({"id": identifier, "name": config.get("name", identifier),
                             "kind": "experiment" if "config" in metadata else "tournament",
                             "created_at": (path / "experiment.json").stat().st_mtime,
                             "archived": (path / "export.json").exists(),
                             "simulated": all(m.get("provider") == "mock" for m in config.get("models", []))
                                          if "models" in config else None,
                             "models": sum(model['id'] not in withdrawn for model in config['models']) if 'models' in config else len(config.get('strategies',[])),
                             "withdrawn_models":len(withdrawn),
                             "replicates": config.get("replicates"), "report": report,
                             "complete": bool(report) and not any(report.get(k) for k in
                                  ("incomplete", "failed", "pending", "assessment_failures", "unresolved_sessions"))
                                         and not (report.get("evolution") or {}).get("incomplete")})
            except (OSError, ValueError, sqlite3.Error) as error:
                rows.append({"id": identifier, "name": identifier, "error": str(error), "complete": False})
        memberships=self.workspace_index()['runs']
        return sorted([{**row,'workspace_id':memberships.get(row['id'])} for row in rows], key=lambda r: r.get("created_at", 0), reverse=True)

    def revision(self, root):
        event_id = 0
        database = root / 'journal.sqlite'
        if database.is_file():
            with closing(sqlite3.connect(database.as_uri() + '?mode=ro', uri=True, timeout=2)) as connection:
                if connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='events'").fetchone():
                    event_id = connection.execute('SELECT coalesce(max(id),0) FROM events').fetchone()[0]
        files = [root/'report.json', root/'analysis.json']
        for base in (root, root/'tournament', *sorted(root.glob('g*-tournament')), *sorted((root/'evaluations').glob('g*-panel')), *sorted((root/'evaluations').glob('g*-previous'))):
            files.extend((base/'records').glob('*.json'))
        files.extend((root/'sessions').glob('*/tools/**/result.json'))
        stamps = [(p.relative_to(root).as_posix(), p.stat().st_mtime_ns, p.stat().st_size) for p in files if p.is_file()]
        return digest({'event_id':event_id, 'files':sorted(stamps)})

    def usage_receipts(self, root):
        """Each response is counted once; usage_event repeats model_response."""
        from .accounting import summarize
        path = root / 'journal.sqlite'
        if not path.is_file():
            return {}
        with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=2)) as connection:
            rows = connection.execute("SELECT session,payload FROM events WHERE kind IN ('model_response','provider_probe_result') ORDER BY id").fetchall()
        grouped = {}
        from arena.usage import normalize, cost, effective_pricing
        from decimal import Decimal
        metadata = self.json(root / 'experiment.json', {})
        if 'config' in metadata:
            from arena.roster import effective
            metadata = {**metadata, 'config':effective(root,metadata['config'])}
        models = {m['id']: m for m in metadata.get('config', {}).get('models', [])}
        states = self.states(root, ('model', 'provider_parameter_overrides'))
        for sid, reference in rows:
            reference = json.loads(reference)
            artifact = safe_path(root, reference['artifact'])
            # Cache only the small usage receipt, not full model output, on live refresh.
            stamp = (artifact.stat().st_mtime_ns, artifact.stat().st_size)
            key = ('usage', artifact)
            with self.lock:
                cached = self._usage_cache.get(key)
            if cached and cached[0] == stamp:
                receipt = cached[1]
            else:
                raw = artifact.read_bytes()
                if hashlib.sha256(raw).hexdigest() != reference['sha256']:
                    raise ArenaError('The usage artifact hash no longer matches the journal')
                value = json.loads(raw)
                receipt = {field: value.get(field) for field in ('usage', 'cost_usd')}
                with self.lock:
                    self._usage_cache[key] = (stamp, receipt)
            receipt = copy.deepcopy(receipt)
            model = models.get(states.get(sid, {}).get('model'), {})
            usage = receipt.get('usage') or {}
            raw_usage = usage.get('raw') or {}
            details = raw_usage.get('input_tokens_details') or raw_usage.get('prompt_tokens_details') or {}
            if 'cache_write_tokens' in details:
                provider = 'openai-responses' if 'input_tokens' in raw_usage else 'openai'
                receipt['usage'] = normalize(provider, raw_usage)
                recalculated = cost(receipt['usage'], effective_pricing(model))
                if recalculated is not None and receipt.get('cost_usd') is not None:
                    receipt['cost_adjustment_usd'] = str(Decimal(recalculated) - Decimal(receipt['cost_usd']))
            grouped.setdefault(sid, []).append(receipt)
        return {sid: summarize(receipts) for sid, receipts in grouped.items()}

    def detail(self, identifier):
        root = self.run_path(identifier)
        metadata = self.json(root / "experiment.json")
        from arena.roster import effective, snapshot
        roster = snapshot(root)
        if 'config' in metadata:
            metadata = {**metadata, 'config':effective(root, metadata['config'])}
        withdrawn = set((roster or {}).get('withdrawn', []))
        sessions = []
        keys = ("model", "participant_revision", "replicate", "generation", "condition", "parent", "parent_checkpoint_sha256",
                "status", "validity", "automatic_retry_at", "automatic_retry_attempts", "calls", "completed_calls", "failure", "context_recoveries", "manual_frozen", "steps", "test_matches", "replay_reads", "wall_seconds", "cost_spent",
                "money_reserved", "token_usage_known", "input_tokens", "output_tokens", "submission", "in_flight", "reserved", "retry_count", "continuation_identity", "provider_parameter_overrides")
        from arena.retries import retry_reason
        from arena.budget_context import tool_budget_exhausted
        from arena.recovery import needs_reconciliation, zero_cost_requests
        free={m["id"] for m in metadata.get("config",{}).get("models",[]) if zero_cost_requests(m)}
        external = {m['id'] for m in metadata.get('config', {}).get('models', []) if m['provider'] != 'mock'}
        states = self.states(root, keys)
        receipts = self.usage_receipts(root)
        if any('completed_calls' not in state for state in states.values()):
            with closing(sqlite3.connect((root / 'journal.sqlite').as_uri() + '?mode=ro', uri=True, timeout=2)) as connection:
                from arena.call_counts import hydrate_calls
                for sid, state in states.items():
                    hydrate_calls(state, connection, sid)
        for sid, state in states.items():
            if state["model"] in free and state.get("status")=="needs_reconciliation" and not float(state.get("money_reserved","0")):
                state.update(status="provider_unavailable" if state.get("in_flight") else "running",in_flight=False)
            reason = 'Participant withdrawn; reactivate it to retry' if state['model'] in withdrawn else 'Exported archives are read-only' if (root / 'export.json').exists() else retry_reason(state, metadata.get('config', {}).get('budget_per_session'), states.get(state.get('parent')))
            assessment = self.json(safe_path(root, f"sessions/{sid}/assessment.json"))
            validation = (assessment or {}).get('status') or state.get('validity')
            from arena.context_recovery import context_overflow
            state['context_recovery_required'] = context_overflow(state)
            sessions.append({"withdrawn":state["model"] in withdrawn, "planned_frozen":state.get("condition") in (roster or {}).get("frozen_tracks",{}).get(state["model"],[]), "context_recovery_required":state['context_recovery_required'], "validation_status": validation or ('pending' if state.get('submission') or state['status'] == 'submitted' else 'not_submitted'), "id": sid, **{k: state[k] for k in keys if k in state},
                             "usage_receipts": receipts.get(sid), "messages": state["messages"], "retry_allowed": reason is None, "finalize_allowed": tool_budget_exhausted(state,metadata.get("config",{}).get("budget_per_session",{})), "retry_reason": reason,
                             "reconciliation_required": needs_reconciliation(state, state.get("model") in external)})
        from decimal import Decimal
        for session in sessions:
            session['recorded_cost_spent'] = session.get('cost_spent')
            adjustment = (session.get('usage_receipts') or {}).get('cost_adjustment_usd', '0')
            if session.get('cost_spent') is not None:
                session['cost_spent'] = str(Decimal(session['cost_spent']) + Decimal(adjustment))
        sessions.sort(key=lambda s:(s.get('model',''),s.get('replicate',0),s.get('generation',0),s.get('condition','')))
        return {"id": identifier, "revision": self.revision(root), "metadata": metadata, "roster":{key:value for key,value in roster.items() if key!='models'} if roster else None, "report": self.json(root / "report.json", {}),
                'model_metadata':{m['id']:{'model_size_billion':self.model_size(m)} for m in metadata.get('config',{}).get('models',[])},
                "analysis": self.json(root / "analysis.json"), "sessions": sessions,
                "g0": self.json(root / "tournament/report.json"),
                "g1": self.json(root / "g1-tournament/report.json"),
                "standings": self.json(root / "report.json", {}).get("standings"),
                "execution_control":self.json(root/"execution-control.json",{}), "archived": (root / "export.json").exists()}

    def provider_diagnostics(self, identifier, sid):
        """Public transport facts only: no credentials, prompts or source contents."""
        root = self.run_path(identifier)
        metadata = self.json(root/'experiment.json', {})
        if 'config' in metadata:
            from arena.roster import effective
            metadata = {**metadata, 'config':effective(root,metadata['config'])}
        selected = self.session(identifier, sid)
        current, state, visited = sid, selected, set()
        while state.get('parent') and not state.get('calls') and not state.get('submission') and current not in visited:
            visited.add(current)
            current = state['parent']
            state = self.session(identifier, current)
        model = next((m for m in metadata.get('config', {}).get('models', []) if m['id'] == state.get('model')), {})
        rows = self.events(identifier, current, 0, 100000)['events']
        intent = next((event for event in reversed(rows) if event['kind'] == 'model_intent'), None)
        failure_event = next((event for event in reversed(rows) if event['kind'] in {'provider_failure','malformed_provider_response','remote_state_unknown'}), None)
        intent_data = self.event(identifier, intent['id']) if intent else {}
        request = (intent_data or {}).get('request') or {}
        body = request.get('body') or {}
        from arena.api_providers import connection
        from arena.usage import effective_pricing
        try: configured_endpoint = connection(model, None)[0] if model else None
        except ArenaError: configured_endpoint = None
        params = model.get('parameters') or {}
        recorded_failure = self.event(identifier, failure_event['id']) if failure_event else {}
        recorded_failure = {k:v for k,v in (recorded_failure or {}).items() if k in {'error','error_type','uncertain','retryable','diagnostics'}}
        return {'session':sid, 'origin_session':current, 'provider':model.get('provider'), 'model':model.get('model'),
                'status':state['status'], 'model_calls':state.get('calls',0),
                'usage_receipts': self.usage_receipts(root).get(current),
                'pricing': effective_pricing(model),
                'diagnostic_calls':state.get('diagnostic_calls',0),
                'api_tests':[self.event(identifier,event['id']) for event in rows if event['kind']=='provider_probe_result'][-5:],
                'session_parameter_overrides':state.get('provider_parameter_overrides', {}),
                'endpoint':request.get('endpoint') or configured_endpoint,
                'configured_parameters':{k:v for k,v in params.items() if k in {'reasoning_effort','temperature','top_p','top_k','seed','thinking','thinking_config'}},
                'failure':state.get('failure'), 'failure_event':recorded_failure or None,
                'request_event_id':intent['id'] if intent else None,
                'request_shape':{'fields':sorted(body), 'model':body.get('model'), 'reasoning':body.get('reasoning'),
                    'reasoning_effort':body.get('reasoning_effort'), 'max_output_tokens':body.get('max_output_tokens'),
                    'max_completion_tokens':body.get('max_completion_tokens'), 'store':body.get('store'),
                    'instructions_present':'instructions' in body,
                    'input_items':len(body.get('input') or body.get('messages') or []),
                    'tools':[{'type':t.get('type'), 'name':t.get('name') or (t.get('function') or {}).get('name')} for t in body.get('tools') or []]},
                'note':'This branch did not make a model call; inspect the origin conversation.' if current != sid else
                       'No API request was recorded for this conversation.' if not intent else 'The recorded request endpoint is authoritative.'}

    def session_diagnostics(self, identifier, sid):
        """Separate generation, compilation and fight health, including still-running runs."""
        root = self.run_path(identifier)
        state = self.session(identifier, sid)
        assessment_path = safe_path(root, f"sessions/{sid}/assessment.json")
        assessment = self.json(assessment_path)
        if assessment is not None and state.get('assessment_sha256') and file_hash(assessment_path) != state['assessment_sha256']:
            raise ArenaError('Submission assessment was modified')
        validity = assessment.get('status') if assessment is not None else state.get('validity')
        assessment_problem = validity is not None and validity != 'valid'
        matches = [m for m in self.matches(identifier)['matches'] if sid in m['sides']]
        failed = [m for m in matches if m['result'].get('status') != 'completed']
        problems = []
        if state.get('failure'):
            problems.append({'phase': 'generation', 'status': state['status'], **state['failure']})
        if assessment_problem:
            problems.append({'phase': 'submission validation', 'status': validity,
                'message': (assessment or {}).get('error') or ('The submitted strategy does not compile.' if validity == 'invalid' else 'The engine could not complete submission validation.'),
                'path': assessment_path.relative_to(root).as_posix() if assessment is not None else None})
        for match in failed:
            problems.append({'phase': 'preparation fight' if match['kind'] == 'training' else 'evaluation fight' if match['kind'] == 'evaluation' else 'tournament fight',
                'status': match['result'].get('status'), 'message': match['result'].get('error') or 'The engine did not complete this fight.',
                'path': match['path'], 'stage': match['stage'], 'sides': match['sides'], 'seed': match['seed']})
        for match in matches:
            if match['result'].get('status') != 'completed':
                continue
            metrics = match['result'].get('team_metrics', {})
            errors = sum((metrics.get(str(side)) or {}).get('errors', 0) for side, participant in enumerate(match['sides']) if participant == sid)
            if errors:
                problems.append({'phase': 'script execution', 'status': 'script_errors',
                    'message': f'{errors} script errors were recorded for your side. This fight completed; inspect its replay logs for the exact messages.',
                    'path': match['path'], 'stage': match['stage'], 'sides': match['sides'], 'seed': match['seed']})
        origin = None
        if state.get('parent') and not state.get('calls') and not state.get('submission'):
            diagnostic = self.provider_diagnostics(identifier, sid)
            origin = diagnostic['origin_session']
            failure = diagnostic.get('failure') or diagnostic.get('failure_event') or {}
            problems.append({'phase':'previous-round preparation', 'status':diagnostic['status'],
                'message':failure.get('message') or failure.get('error') or diagnostic['note'], 'origin_session':origin})
        from arena.compiler_diagnostics import compilation_rows
        compilation = compilation_rows(assessment, (self.json(root / 'experiment.json') or {}).get('engine'))
        return {'failure_origin':origin, 'session':sid, 'compilation': compilation, 'generation_status': state['status'], 'has_submission': bool(state.get('submission')) or state['status'] == 'submitted',
                'validation_status': validity or ('pending' if state.get('submission') or state['status'] == 'submitted' else 'not_submitted'),
                'assessment': assessment, 'problems': problems,
                'matches': {'competition_completed': sum(m['kind'] == 'competition' and not m.get('mirror') and m['result'].get('status') == 'completed' for m in matches),
                            'reference_completed': sum(m['kind'] == 'evaluation' and m['result'].get('status') == 'completed' for m in matches),
                            'mirror_completed': sum(m['kind'] == 'competition' and m.get('mirror') and m['result'].get('status') == 'completed' for m in matches),
                            'completed': sum(m['result'].get('status') == 'completed' for m in matches if m['kind'] != 'training'),
                            'failed': sum(m['kind'] != 'training' for m in failed),
                            'preparation_completed': sum(m['result'].get('status') == 'completed' for m in matches if m['kind'] == 'training')},
                'schedule_note': 'Submitted strategies are frozen. Available fights run progressively; the next round waits for all participants. Preparation tests are separate and unscored.'}

    def message(self, identifier, sid, index):
        history = self.session(identifier, sid).get("history", [])
        if not 0 <= index < len(history):
            raise ArenaError("Message not found")
        message=history[index]
        if message.get('response_artifact'):
            reference=message['response_artifact']
            path=safe_path(self.run_path(identifier),reference['artifact'])
            if file_hash(path)!=reference['sha256']:
                raise ArenaError('Archived model response changed')
            message={**message,**self.json(path)}
        return {"message": message}

    def tool_exchange(self, identifier, sid, index):
        from .tool_exchange import inspect
        history = self.session(identifier, sid).get('history', [])
        if not 0 <= index < len(history): raise ArenaError('Message not found')
        result = inspect(history, index, self.starting_writes(identifier,sid) + list(history_writes(history[:index+1])))
        if result is None: raise ArenaError('No matching file tool request was recorded')
        return result

    def output_block(self, identifier, sid, index, block):
        from .provider_output import blocks
        message = self.message(identifier, sid, index)['message']
        parts = blocks(message)
        if not 0 <= block < len(parts):
            raise ArenaError("Output block not found")
        return parts[block]

    def conversation(self, identifier, sid, offset=0, limit=25, *, include_diagnostics=True, tail=False):
        state = self.session(identifier, sid)
        history = state.get("history", [])
        if tail:offset=max(0,len(history)-limit)
        failure = state.get("failure")
        times = list(state.get("message_times", [None] * len(history)))
        times.extend([None] * (len(history) - len(times)))
        events = self.events(identifier, sid, 0, 100000)["events"] if any(at is None for at in times) or (not failure and state.get("status") in TERMINAL - {"submitted", "budget_exhausted", "no_submission"}) else []
        start = max((i for i,m in enumerate(history) if m.get("role") == "user" and m.get("generation", 0) == state.get("generation", 0)), default=0)
        cursor = start + 1
        for event in events:
            if event["kind"] in {"session_created", "branch_created"} and history:
                times[start] = times[start] or event.get("at")
            role = {"model_response": "assistant", "tool_result": "tool"}.get(event["kind"])
            if role:
                match = next((i for i in range(cursor,len(history)) if history[i].get("role") == role), None)
                if match is not None:
                    times[match] = times[match] or event.get("at")
                    cursor = match + 1
        # Older runs keep failure detail only in journal events. Read artifacts
        # through the same hash-checked reader used by the journal UI.
        if not failure and state.get("status") in {"provider_unavailable", "needs_reconciliation", "generation_failed"}:
            event = next((e for e in reversed(events) if e["kind"] in {"provider_failure", "malformed_provider_response"}), None)
            if event:
                payload = self.event(identifier, event["id"]) or {}
                failure = {"message": payload.get("error") or "Malformed provider response: " + payload.get("error_type", "unknown"),
                           "at": event.get("at"), "phase": event["kind"], "event_id": event["id"],
                           "retryable": payload.get("retryable"), "uncertain": payload.get("uncertain")}
        timeline, last_request, turn = [], None, 0
        for item in history:
            if item.get("role") == "assistant":
                last_request = len(timeline)
                turn += 1
            timeline.append({"reply_to": last_request if item.get("role") == "tool" else None, "turn": turn})
        messages = []
        for absolute, item in enumerate(history[offset:offset + limit], offset):
            # Requests contain full prior histories. Do not transfer them N times
            # on every live refresh. Exact records remain available on demand.
            visible = {k:v for k,v in item.items() if k not in {"raw", "sent_parameters"}}
            if item.get('role')=='user' and isinstance(item.get('scenario'),dict) and isinstance(item.get('briefing'),dict):
                from arena.user_briefing import render
                from arena.model_content import visible as model_visible
                visible['model_text']=render(model_visible(item))
                visible['briefing_readable_view']=item.get('context_format')!='briefing-v1'
            if item.get('role') in {'assistant', 'tool'}:
                from .provider_output import preview
                visible.update(preview(item))
                visible.pop('native', None)
                if item.get('role') == 'assistant':
                    visible['tool_calls'] = [{k:v for k,v in call.items() if k != 'arguments'} for call in item.get('tool_calls', [])]
                    visible.pop('content', None)
                else:
                    visible['tool_error'] = bool((item.get('result') or {}).get('error') or (item.get('result') or {}).get('valid') is False) if isinstance(item.get('result'), dict) else False
                    visible.pop('result', None)
            if item.get('role') == 'tool':
                from .tool_exchange import summary
                visible['file_exchange'] = summary(history, absolute)
            if item.get('role') == 'assistant':
                visible['call_summaries'] = [{'name':c.get('name'), 'id':c.get('id'),
                    'arguments': {k:(v[:200] if isinstance(v,str) else v) for k,v in (c.get('arguments') or {}).items()
                                  if k != 'content' and isinstance(v,(str,int,float,bool))}}
                    for c in item.get('tool_calls', []) if isinstance(c.get('arguments'),dict)]
            parameters = item.get("sent_parameters") or item.get("request_summary") or {}
            visible["request_reasoning"] = {key:value for key,value in parameters.items()
                if key in {'reasoning_effort', 'thinking', 'output_config'}}
            if parameters.get('reasoning', {}).get('effort') is not None:
                visible['request_reasoning']['reasoning_effort'] = parameters['reasoning']['effort']
            if parameters.get('generationConfig', {}).get('thinkingConfig') is not None:
                visible['request_reasoning']['thinking_config'] = parameters['generationConfig']['thinkingConfig']
            visible["request_recorded"] = "sent_parameters" in item or "response_artifact" in item
            visible["request_seed"] = parameters.get("seed", parameters.get("generationConfig", {}).get("seed"))
            if item.get("role") == "user" and "scenario" in visible:
                from arena.briefing import participant_scenario
                visible["scenario"] = participant_scenario(visible["scenario"])
            messages.append(visible)
        failure_event = None
        if state.get('status') in {'provider_unavailable', 'needs_reconciliation', 'generation_failed'}:
            database = self.run_path(identifier) / 'journal.sqlite'
            with closing(sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)) as connection:
                row = connection.execute("SELECT id,kind FROM events WHERE session=? AND kind IN ('malformed_provider_response','provider_failure') ORDER BY id DESC LIMIT 1", (sid,)).fetchone()
                if row: failure_event = {'id': row[0], 'kind': row[1]}
        return {"total": len(history), "offset": offset, "messages": messages,
                "times": times[offset:offset + limit], "timeline": timeline[offset:offset + limit], "model": state.get("model"),
                "status": state["status"], "failure": failure, "instruction_index": start, "history_policy":state.get("history_policy"),
                "generation": state.get("generation", 0), "condition": state.get("condition", "initial"),
                "failure_event": failure_event, "diagnostics": self.session_diagnostics(identifier, sid) if include_diagnostics else None}

    def events(self, identifier, sid=None, offset=0, limit=100, model=None):
        root = self.run_path(identifier)
        path = root / "journal.sqlite"
        if not path.exists():
            return {"total": 0, "events": []}
        with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=2)) as connection:
            if not connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='events'").fetchone():
                return {"total": 0, "events": []}
            conditions, args = [], []
            if sid:
                conditions.append("session=?")
                args.append(sid)
            if model:
                conditions.append("session IN (SELECT id FROM sessions WHERE json_extract(state,'$.model')=?)")
                args.append(model)
            clause = " WHERE " + " AND ".join(conditions) if conditions else ""
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
            raise ArenaError("Event not found")
        reference = json.loads(row[0])
        path = safe_path(root, reference["artifact"])
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != reference["sha256"]:
            raise ArenaError("The event artifact hash no longer matches the journal")
        return self.json(path)

    def starting_writes(self, identifier, sid, state=None):
        state = state or self.session(identifier, sid)
        if state.get('saved_strategy_origin') is not None and state.get('submission'):
            result=[]
            for name,expected in sorted(state['submission']['files'].items()):
                path=safe_path(self.run_path(identifier),f'sessions/{sid}/submission/{name}')
                content=path.read_bytes()
                if hashlib.sha256(content).hexdigest()!=expected:
                    raise ArenaError('Saved strategy source changed')
                result.append({'message':-1,'generation':state.get('generation',0),'saved_strategy':True,
                               'path':name,'content':content.decode('utf-8'),'sha256':expected})
            return result
        if state.get('history_policy') != 'fresh-round' or not state.get('parent'):
            return []
        from arena.submitted_versions import OwnSubmissions
        versions = OwnSubmissions(self.run_path(identifier), state).versions()
        if not versions: return []
        previous = versions[-1]
        result = []
        for name, expected in sorted(previous['submission']['files'].items()):
            path = safe_path(self.run_path(identifier), f"sessions/{previous['session']}/submission/{name}")
            content = path.read_bytes()
            if hashlib.sha256(content).hexdigest() != expected:
                raise ArenaError('Inherited submitted source changed')
            result.append({'message':-1, 'generation':state['generation'], 'inherited_round':previous['round'],
                           'path':name, 'content':content.decode('utf-8'), 'sha256':expected})
        return result

    def versions(self, identifier, sid):
        history = self.session(identifier, sid).get("history", [])
        files, versions = {}, []
        for write in self.starting_writes(identifier,sid) + list(history_writes(history)):
            files[write["path"]] = write["sha256"]
            versions.append({k: v for k, v in write.items() if k != "content"} |
                            {"index": len(versions), "files": sorted(files), "tree_sha256": digest(files)})
        return {"versions": versions, "basis": "Inherited submitted files followed by successful source writes and team configurations; failed proposals are excluded."}

    def source(self, identifier, sid, version, filename, previous=None):
        files, before, after = {}, {}, None
        writes = self.starting_writes(identifier,sid) + list(history_writes(self.session(identifier, sid).get("history", [])))
        if not 0 <= version < len(writes):
            raise ArenaError("Version introuvable")
        previous = version - 1 if previous is None else previous
        if previous < -1 or previous > version:
            raise ArenaError("Choose an earlier version to compare")
        for index, write in enumerate(writes[:version + 1]):
            files[write["path"]] = write["content"]
            if index == previous:
                before = dict(files)
            if index == version:
                after = dict(files)
        if filename not in after:
            raise ArenaError("File not present in this version")
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

    def matches(self, identifier, *, compact=False):
        root = self.run_path(identifier)
        rows = []
        for base in (root, root/'tournament', *sorted(root.glob('g*-tournament')), *sorted((root/'evaluations').glob('g*-panel')), *sorted((root/'evaluations').glob('g*-previous'))):
            for path in sorted((base / "records").glob("*.json")):
                record = self.workspace_artifact(path,'record') if compact else self.json(path)
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
                             "sides": sides, "candidate": record.get("session"), "candidate_side": record.get("side"), "seed": match.get("seed", record.get("seed")),
                             "mirror": match.get("mirror", False), "result": record["result"], "timings":record.get("timings",{})})
        for path in sorted((root / "sessions").glob("*/tools/**/result.json")):
            if (path.parent / "scenario.json").is_file():
                info = {} if compact else self.json(path.parent / "provenance.json", {})
                scenario = {} if compact else self.json(path.parent / "scenario.json", {})
                cached = {} if compact else self.json(path.parent.parent / "cached.json", {})
                opponent = 'Own script: '+cached['opponent_entrypoint'] if cached.get('opponent_entrypoint') else 'passive'
                rows.append({"path": path.parent.relative_to(root).as_posix(), "stage": "training",
                             "sides": ([opponent, path.relative_to(root).parts[1]] if "side-1" in path.as_posix()
                                       else [path.relative_to(root).parts[1], opponent]),
                             "seed": scenario.get("random_seed"), "mirror": False,
                             "result": self.workspace_artifact(path,'result') if compact else self.json(path), "provenance": info})
        states=self.states(root,('model','generation','condition','replicate','parent'))
        metadata=self.json(root/'experiment.json',{})
        from arena.roster import effective
        models={model['id']:model for model in effective(root,metadata['config']).get('models',[])} if 'config' in metadata else {}
        for row in rows:
            row['kind'] = 'training' if row['stage'] == 'training' else 'evaluation' if row['stage'].startswith('evaluations/') else 'competition'
            if row['stage'].endswith('-previous'):row['kind']='progression'
            candidate=states.get(row.get('candidate'),{})
            opponent=next((states.get(sid,{}) for sid in row['sides'] if sid!=row.get('candidate')),{})
            row['previous_round_comparison']=row['kind']=='progression' or (row['kind']=='evaluation' and candidate.get('generation')==1 and opponent.get('generation')==0 and models.get(candidate.get('model'),{}).get('provider') not in {None,'mock'} and models.get(opponent.get('model'),{}).get('provider') not in {None,'mock'})
            row['counts_toward_standings'] = row['kind'] == 'competition' and not row.get('mirror')
        from .progression import summarize
        return {"matches": rows,"progression":[] if compact else summarize(states,models,rows)}

    def match(self, identifier, name):
        root = self.run_path(identifier)
        work = safe_path(root, name)
        result = self.json(work / "result.json")
        if result is None:
            raise ArenaError("Combat introuvable")
        return {"result": result, "scenario": self.json(work / "scenario.json"),
                "provenance": self.json(work / "provenance.json"),
                "outcome": self.json(work / "outcome.json")}

    def match_sources(self, identifier, name):
        root=self.run_path(identifier)
        work=safe_path(root,name)
        if not (work/'result.json').is_file():raise ArenaError('Match not found')
        provenance=self.json(work/'provenance.json',{})
        result=[]
        for side,info in enumerate(provenance.get('submissions',[])[:2]):
            directory=safe_path(root,(work/'strategies'/str(side+1)).relative_to(root).as_posix())
            result.append({'side':side,'entrypoint':info.get('entrypoint'),'files':sorted(info.get('files',{})),
                           'sha256':info.get('sha256'),'available':directory.is_dir()})
        return result

    def match_source(self, identifier, name, side, filename=None):
        if type(side) is not int or side not in (0,1):raise ArenaError('Choose side 0 or 1')
        sources=self.match_sources(identifier,name)
        info=next((row for row in sources if row['side']==side),None)
        if not info or not info['available']:raise ArenaError('This match has no archived source for this side')
        filename=filename or info['entrypoint']
        if filename not in info['files']:raise ArenaError('File is not part of the executed submission')
        root=self.run_path(identifier);work=safe_path(root,name)
        provenance=self.json(work/'provenance.json',{})['submissions'][side]
        path=safe_path(root,(work/'strategies'/str(side+1)/filename).relative_to(root).as_posix())
        with path.open('rb') as stream:content=stream.read(2_000_001)
        if len(content)>2_000_000:raise ArenaError('Source file exceeds preview limit')
        if hashlib.sha256(content).hexdigest()!=provenance['files'][filename]:raise ArenaError('Executed source fingerprint changed')
        return {'side':side,'path':filename,'content':content.decode('utf-8'),
                'sha256':provenance['files'][filename],'entrypoint':info['entrypoint'],'files':info['files']}

    def statistics(self, identifier):
        from .metrics import competition_stats
        root = self.run_path(identifier)
        all_matches = self.matches(identifier)["matches"]
        matches = [row for row in all_matches if row.get('kind') != 'training']
        training_count = len(all_matches) - len(matches)
        paths = [safe_path(root, row["path"] + "/outcome.json") for row in matches]
        stamp = (digest(matches), training_count), tuple((p.stat().st_mtime_ns, p.stat().st_size) if p.is_file() else None for p in paths)
        with self.lock:
            cache = getattr(self, "_statistics_cache", {})
            if identifier in cache and cache[identifier][0] == stamp:
                return copy.deepcopy(cache[identifier][1])
        result = competition_stats(matches, lambda name: self.json(safe_path(root, name + "/outcome.json")),
                                   lambda name: self.json(safe_path(root, name + "/scenario.json")))
        result['training_matches'] = training_count
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
                excluded.append({"run": identifier, "reason": "Exported copy excluded to avoid double counting."})
                continue
            analysis = detail["analysis"]
            if not analysis:
                excluded.append({"run": identifier, "reason": "No results against the fixed-strategy panel."})
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
                excluded.append({"run": identifier, "reason": "Fixed-opponent provenance is unavailable."})
                continue
            protocol = {"scenario": config["scenario"], "seeds": config.get("final_seeds"),
                        "engine": metadata.get("scientific_identity", metadata.get("engine")),
                        "opponents": opponents,
                        "preparation": {"parallel_requests":config.get("parallel_requests",1), "budgets": config["budget_per_session"], "catalogs": metadata.get("catalogs"),
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
                descriptor={**descriptor,'model_size_billion':self.model_size(descriptor)}
                model_key = digest({k: v for k, v in descriptor.items() if k not in {"api_key_env","model_size_billion"}})[:12]
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
                sizes={row['participant'].get('model_size_billion') for row in rows}
                participant={**rows[0]['participant'],'model_size_billion':next(iter(sizes)) if len(sizes)==1 else None}
                summaries.append({**totals, "cost_usd": total_cost, "key": key, "model": rows[0]["model"], "participant": participant, "generation": rows[0]["generation"],
                                  "condition": rows[0]["condition"],
                                  "score": sum(r["score"] for r in complete) / len(complete) if complete else None,
                                  "conversations": len(complete), "excluded": len(rows) - len(complete),
                                  "runs": len({r["run"] for r in complete})})
            group["models"] = summaries
        return {"groups": list(groups.values()), "excluded": excluded,
                "explanation": "Equal-weight average of complete conversations against the same fixed strategies. "
                               "Scenario, seeds, opponents, preparation, budgets, engine and mock/real mode must match. "
                               "Different protocols form separate groups."}
