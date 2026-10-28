"""Loopback-only HTTP application. No framework, CDN, Node or external service."""
from __future__ import annotations

from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import shutil
import sqlite3
import threading
from urllib.parse import parse_qs, urlsplit, quote
import webbrowser

from arena.core import ArenaError, ROOT, digest, file_lock, read_json
from arena.experiment import plan, validate_config
from .data import Store, safe_path
from .jobs import Jobs

STATIC = Path(__file__).parent / "static"


class Application:
    def __init__(self, store=None):
        self.store = store or Store()
        self.jobs = Jobs(self.store)
        self.token = secrets.token_urlsafe(32)

    def bootstrap(self):
        from arena.engine import Engine
        from arena.providers import PROFILES
        try:
            engine = {"ready": True, "identity": Engine().identity}
        except (ArenaError, OSError) as error:
            engine = {"ready": False, "error": str(error)}
        from arena.presets import simple_scenario, participant_scenario
        demo = self.store.json(ROOT / "configs/offline-complete.json")
        config = {**demo, "name": "New competition", "scenario": simple_scenario()}
        return {"token": self.token, "participants": self.store.participants(), "providers": self.store.providers(),
                "workspaces":self.store.workspace_index()['workspaces'],
                "participant_groups":self.store.participant_groups(),
                "drafts": self.store.drafts(), "runs": self.store.listing(), "jobs": self.jobs.listing(),
                "profiles": list(PROFILES), "engine": engine,
                "default_config": config, "demo_config": demo, "participant_scenario": participant_scenario()}

    def get(self, route, query):
        value = lambda key, default=None: query.get(key, [default])[0]
        number = lambda key, default: max(0, min(int(value(key, default)), 100_000))
        store, run, sid = self.store, value("run"), value("session")
        if route == "/api/bootstrap":
            return self.bootstrap()
        if route == "/api/reference":
            documents = {"authoring": "authoring.md", "rules": "corpus/rules.md",
                         "api-guide": "corpus/api-guide.md", "api": "leekscript-v1/api.md",
                         "ui": "ui.md", "providers": "providers.md", "stats": "realistic-stats.md"}
            name = value("document")
            if name not in documents:
                raise ArenaError("Unknown reference document")
            return {"title": documents[name], "content": (ROOT / "docs" / documents[name]).read_text(encoding="utf-8")}
        if route == "/api/equipment":
            data = ROOT / "docs/leekscript-v1"
            constants = store.json(data / "api.json")["constants"]
            effects = {}
            for name, value in constants.items():
                if name.startswith("EFFECT_") and not name.startswith(("EFFECT_TARGET_", "EFFECT_MODIFIER_")):
                    effects.setdefault(str(int(float(value))), name.removeprefix("EFFECT_").replace("_", " ").title())
            from arena.stats import RULES
            from arena.components import catalog as component_catalog
            from arena.equipment import catalog
            component_rules = read_json(ROOT/'docs/corpus/component-rules.json')
            return {"components": component_catalog(), "stat_rules": RULES, "weapons": catalog(data, "weapons"), "chips": catalog(data, "chips"),
                    "component_snapshot": {key: component_rules[key] for key in ('source_url', 'master_version', 'fetched_at')},
                    "effects": effects, "snapshot": store.json(data / "snapshot.json")["engine"]["lock"]["commit"]}
        if route == "/api/reference-strategies":
            from arena.reference_strategies import CATALOG
            return {"strategies":CATALOG}
        if route == "/api/runs":
            return {"runs": store.listing(), "jobs": self.jobs.listing()}
        if route == '/api/workspace':
            return store.workspace_summary(value('workspace',''))
        if route == '/api/match/source':
            return store.match_source(run,value('path'),int(value('side','0')),value('file'))
        if route == '/api/match/sources':
            return {'sources':store.match_sources(run,value('path'))}
        if route == '/api/activity':
            from .activity import status
            job=next((job for job in self.jobs.listing() if job['run']==run),None)
            return status(store,run,job)
        if route == '/api/faults':
            from .faults import report
            return report(store,run)
        if route == "/api/run":
            return store.detail(run)
        if route == "/api/provider-diagnostics":
            return store.provider_diagnostics(run, sid)
        if route == "/api/session-diagnostics":
            return store.session_diagnostics(run, sid)
        if route == "/api/conversation":
            return store.conversation(run, sid, number("offset", 0), min(number("limit", 25), 100),include_diagnostics=value("lightweight")!="1",tail=value("tail")=="1")
        if route == "/api/tool-exchange":
            return store.tool_exchange(run, sid, number("index", 0))
        if route == "/api/message-output":
            return store.output_block(run, sid, number("index", 0), number("block", 0))
        if route == "/api/message":
            return store.message(run, sid, number("index", 0))
        if route == "/api/events":
            return store.events(run, sid, number("offset", 0), min(number("limit", 100), 500), value("model"))
        if route == "/api/event":
            return store.event(run, number("id", 0))
        if route == "/api/versions":
            return store.versions(run, sid)
        if route == "/api/source":
            return store.source(run, sid, number("version", 0), value("file"),
                                int(value("previous")) if value("previous") is not None else None)
        if route == "/api/files":
            return store.files(run)
        if route == "/api/statistics":
            return store.statistics(run)
        if route == "/api/matches":
            return store.matches(run)
        if route == "/api/match":
            from .replay import describe
            result = store.match(run, value("path"))
            if result["outcome"] and result["outcome"].get("fight"):
                from arena.equipment import catalog
                data = ROOT / "docs/leekscript-v1"
                result["replay"] = describe(result["outcome"]["fight"], {kind: catalog(data, kind, include_special=True) for kind in ("weapons", "chips")})
                from .metrics import combat_stats
                result["statistics"] = combat_stats(result["outcome"], result["scenario"])
            return result
        if route == "/api/job":
            return self.jobs.log(value("id"))
        raise ArenaError("Route not found")

    def post(self, route, data):
        if not isinstance(data, dict):
            raise ArenaError("Expected a JSON object")
        if route == "/api/provider":
            return self.store.save_provider(data['spec'],data.get('secret'))
        if route == "/api/provider/delete":
            return self.store.delete_provider(data['id'])
        if route == "/api/provider/participants":
            return self.store.create_provider_participants(data['id'],data['models'])
        if route == "/api/models":
            from arena.api_providers import list_models
            import os
            secret = data.get("secret")
            if secret is not None and (not isinstance(secret, str) or len(secret) > 8192):
                raise ArenaError("Invalid API key")
            key_name = data.get("api_key_env") or ""
            if not isinstance(key_name, str):
                raise ArenaError("Invalid environment variable name")
            key = secret or self.store.secrets.get(key_name) or os.environ.get(key_name)
            return list_models(data.get("provider"), key, data.get("endpoint"))
        if route == "/api/dream-team":
            from arena.presets import dream_team_scenario, save_dream_team
            from arena.public_teams import fetch_snapshot
            if set(data) - {"refresh", "snapshot"} or ("refresh" in data and type(data["refresh"]) is not bool):
                raise ArenaError("Invalid Dream team refresh request")
            cache = self.store.state / "dream-team-preset.json"
            if data.get("refresh") or "snapshot" in data:
                snapshot = data["snapshot"] if "snapshot" in data else fetch_snapshot()
                with self.store.lock:
                    scenario = save_dream_team(snapshot, cache)
                return {"scenario": scenario}
            return {"scenario": dream_team_scenario(cache if cache.exists() else None)}
        if route == "/api/stats/realistic":
            from arena.stats import to_realistic
            return {"scenario": to_realistic(data['scenario'])}
        if route == '/api/participant/reference':
            from arena.reference_strategies import participant
            from arena.presets import simple_scenario
            scenario=self.store.detail(data['run'])['metadata']['config']['scenario'] if data.get('run') else simple_scenario()
            spec=participant(data['reference'],data['id'],scenario)
            with self.store.lock:
                if any(m['id']==data['id'] for m in self.store.catalog()):
                    raise ArenaError('A participant with this name already exists')
                config=read_json(ROOT/'configs/offline-complete.json')
                config.update(models=[spec],scenario=scenario,spending={'allow_paid_calls':False,'max_total_usd':0})
                validate_config(config)
                from arena.core import write_json
                write_json(self.store.state/'participants.json',self.store.catalog()+[spec])
            return {'saved':data['id']}
        if route == "/api/participant/import":
            return self.store.import_strategy(data["run"],data["session"],data["id"])
        if route == "/api/participant":
            return self.store.save_participant(data["spec"], data.get("secret"))
        if route == "/api/participant/delete":
            return self.store.delete_participant(data["id"])
        if route == '/api/participant-group':
            return self.store.save_participant_group(data['name'],data.get('members',[]),data.get('id'))
        if route == '/api/participant-group/delete':
            return self.store.delete_participant_group(data['id'])
        if route == '/api/participant/groups':
            return self.store.set_participant_groups(data['participant'],data.get('groups',[]))
        if route == "/api/competition":
            options={'workspace_id':data['workspace_id']} if 'workspace_id' in data else {}
            return self.store.save_draft(data["config"], data.get("id"),**options)
        if route == '/api/workspace':
            return self.store.save_workspace(data['name'],data.get('id'),data.get('description',''))
        if route == '/api/workspace/delete':
            return self.store.delete_workspace(data['id'])
        if route == '/api/workspace/members':
            return self.store.assign_workspace(data.get('workspace_id'),data.get('runs'),data.get('drafts'),replace=data.get('replace') is True)
        if route == "/api/competition/delete":
            return self.store.delete_draft(data["id"])
        if route == "/api/plan":
            if data.get('frozen') and data.get('run'):
                from arena.roster import effective, snapshot, validate_effective
                root=self.store.run_path(data['run'])
                config=effective(root,read_json(root/'experiment.json')['config'])
                roster=snapshot(root) or {}
                withdrawn=set(roster.get('withdrawn',[]))
                validate_effective(config,withdrawn)
                selected={**config,'compare_previous_round':roster.get('compare_previous_round',config.get('compare_previous_round',False)),'models':[model for model in config['models'] if model['id'] not in withdrawn]}
                planned={**selected,'_parallel_fights':roster.get('parallel_fights',config.get('parallel_fights',1)),
                         '_request_order':roster.get('request_order',config.get('request_order','models')),
                         '_parallel_requests':roster.get('parallel_requests',config.get('parallel_requests',1)),
                         '_fixed_reference_repetitions':read_json(root/'experiment.json').get('fixed_reference_repetitions',config['replicates'])}
                return {**plan(planned),'active_models':[model['id'] for model in selected['models']], 'config':config,'config_sha256':digest(config)}
            config = data['config'] if data.get('frozen') else self.store.resolve_models(data['config'])
            return {**plan(validate_config(config)), 'config':config, 'config_sha256':digest(config)}
        if route == '/api/run/participants':
            return self.jobs.participants(data['run'], data.get('participants'), data.get('frozen_tracks'), data.get('compare_previous_round'), data.get('parallel_fights'), data.get('request_order'), data.get('parallel_requests'))
        if route == "/api/launch":
            return self.jobs.launch(draft_id=data.get("draft_id"), run_id=data.get("run"),
                                    confirm_paid=data.get("confirm_paid", False), ceiling=data.get("ceiling"), retry_session=data.get("retry_session"), expected_config_sha256=data.get("expected_config_sha256"), allow_updated_runner=data.get("allow_updated_runner") is True, retry_reasoning_effort=data.get("retry_reasoning_effort"))
        if route == '/api/model-test':
            from .model_probe import probe_model
            model=next((row for row in self.store.catalog() if row['id']==data['id']),None)
            if not model: raise ArenaError('Unknown participant')
            return probe_model(self.store,model,data.get('mode','text'),data.get('secret'))
        if route == "/api/provider-probe":
            from .provider_probe import probe
            return probe(self.jobs, data["run"], data["session"], data["mode"], data.get("confirm_paid"))
        if route == "/api/reconcile":
            return self.jobs.reconcile(data["run"], data["session"], data["cost_usd"], data["note"])
        if route == "/api/stop":
            return self.jobs.stop(data["id"])
        if route == "/api/aggregate":
            identifiers = data.get("runs", [])
            if not isinstance(identifiers, list) or len(identifiers) > 200:
                raise ArenaError("Select at most 200 competitions")
            return self.store.aggregate(identifiers)
        if route == "/api/export":
            from arena.exporting import export_experiment
            import uuid
            source = self.store.run_path(data["run"])
            target = self.store.runs / (source.name + "-export-" + uuid.uuid4().hex[:8])
            result = export_experiment(source, target)
            identifier=target.relative_to(self.store.runs).as_posix()
            with self.store.lock:
                workspace=self.store.workspace_index()['runs'].get(data['run'])
                if workspace:self.store.assign_workspace(workspace,runs=[identifier])
            return {**result, "run": identifier}
        raise ArenaError("Route not found")


class Handler(BaseHTTPRequestHandler):
    server_version = "LLMArena/1"

    def log_message(self, *args):
        pass

    def headers_for(self, status, mime, size=None, download=None):
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        if size is not None:
            self.send_header("Content-Length", str(size))
        if download:
            self.send_header("Content-Disposition", "attachment; filename=artifact; filename*=UTF-8''" + quote(str(download), safe=""))
        self.end_headers()

    def json_response(self, status, value):
        body = json.dumps(value, ensure_ascii=False).encode("utf-8")
        try:
            self.headers_for(status, "application/json; charset=utf-8", len(body))
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            self.close_connection=True

    def check_origin(self):
        expected = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
        host = self.headers.get("Host", "")
        if host not in expected:
            raise ArenaError("Host not allowed")
        origin = self.headers.get("Origin")
        if origin and origin not in {"http://" + host}:
            raise ArenaError("Origin not allowed")
        if self.headers.get("Sec-Fetch-Site") == "cross-site":
            raise ArenaError("Origin not allowed")

    def do_GET(self):
        try:
            self.check_origin()
            parsed = urlsplit(self.path)
            query = parse_qs(parsed.query)
            app = self.server.app
            if parsed.path == "/api/results.csv":
                from tempfile import TemporaryDirectory
                from arena.benchmark_export import export
                roots=([app.store.run_path(row['id']) for row in app.store.workspace_runs(query['workspace'][0])
                        if not row.get('archived') and not row.get('error')]
                       if 'workspace' in query else [app.store.run_path(query['run'][0])])
                table = query.get('table', ['results'])[0]
                if table=='summary' and 'workspace' in query:
                    import csv
                    import io
                    summary=app.store.workspace_summary(query['workspace'][0])
                    stream=io.StringIO(newline='')
                    columns=['workspace_id','comparison_group','kind','stage','scenario_sha256','runs','participant','round','condition','score','wins','draws','losses','failed','strategies','model_size_billion','score_per_billion','mean_cost_usd','mean_wall_seconds','mean_tool_calls','total_tool_calls']
                    writer=csv.DictWriter(stream,fieldnames=columns);writer.writeheader()
                    for group in summary['groups']:
                        for row in group['models']:
                            writer.writerow({'workspace_id':query['workspace'][0],'comparison_group':group['id'],
                                'kind':group['kind'],'stage':group['stage'],'scenario_sha256':digest(group['scenario']),
                                'runs':json.dumps(group['runs']), 'participant':row['name'],'strategies':row['conversations'],
                                **{key:row[key] for key in ('round','condition','score','wins','draws','losses','failed','model_size_billion','score_per_billion','mean_cost_usd','mean_wall_seconds','mean_tool_calls','total_tool_calls')}})
                    body=stream.getvalue().encode('utf-8-sig')
                elif table in {'results', 'fights', 'sessions', 'errors'}:
                    with TemporaryDirectory(prefix='arena-results-') as directory:
                        target = Path(directory) / 'export'
                        export(roots, target,catalog=app.store.catalog())
                        body = (target / (table + '.csv')).read_bytes()
                else:
                    raise ArenaError('Unknown results table')
                filename=(query['workspace'][0]+'-' if 'workspace' in query else '')+table+'.csv'
                self.headers_for(200, 'text/csv; charset=utf-8', len(body), filename)
                self.wfile.write(body)
            elif parsed.path == "/api/file":
                root = app.store.run_path(query["run"][0])
                path = safe_path(root, query["path"][0])
                if not path.is_file() or path.name.startswith("journal.sqlite") or path.name == ".lock":
                    raise ArenaError("File cannot be viewed")
                size = path.stat().st_size
                download = query.get("download") == ["1"]
                if size > 8_000_000 and not download:
                    raise ArenaError("File exceeds 8 MB; use Download")
                self.headers_for(200, "application/octet-stream" if download else "text/plain; charset=utf-8", size, path.name if download else None)
                with path.open("rb") as stream:
                    shutil.copyfileobj(stream, self.wfile)
            elif parsed.path.startswith("/api/"):
                self.json_response(200, app.get(parsed.path, query))
            else:
                names = {"/": "index.html", "/app.js": "app.js", "/live-dom.js":"live-dom.js", "/style.css": "style.css", "/workspace.css": "workspace.css", "/favicon.png": "favicon.png"}
                if parsed.path not in names:
                    self.json_response(404, {"error": "Page not found"})
                    return
                path = STATIC / names[parsed.path]
                body = path.read_bytes()
                mime = {".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".png": "image/png"}[path.suffix]
                self.headers_for(200, mime if path.suffix == ".png" else mime + "; charset=utf-8", len(body))
                self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            self.close_connection=True
        except (ArenaError, ValueError, KeyError, TypeError, OSError, sqlite3.Error) as error:
            self.json_response(400, {"error": str(error)})

    def do_POST(self):
        try:
            self.check_origin()
            if not secrets.compare_digest(self.headers.get("X-Arena-Token", ""), self.server.app.token):
                self.json_response(403, {"error": "The application session changed. Refresh its session token and retry.", "code":"stale_arena_token"})
                return
            if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                raise ArenaError("Content-Type application/json requis")
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 2_000_000:
                raise ArenaError("Request is empty or too large")
            data = json.loads(self.rfile.read(length))
            self.json_response(200, self.server.app.post(urlsplit(self.path).path, data))
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            self.close_connection=True
        except (ArenaError, ValueError, KeyError, TypeError, OSError, sqlite3.Error) as error:
            self.json_response(400, {"error": str(error)})


class Server(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, app):
        self.app = app
        super().__init__(address, Handler)


def serve(port=8765, runs=None, open_browser=False):
    app = Application(Store(runs=runs))
    with file_lock(app.store.state / "server.lock"):
        server = Server(("127.0.0.1", port), app)
        url = f"http://127.0.0.1:{server.server_port}"
        print(f"LLM Arena: {url}\nCtrl+C to stop the server.", flush=True)
        if open_browser:
            threading.Timer(0.5, lambda: webbrowser.open(url)).start()
        try:
            server.serve_forever(poll_interval=0.2)
        except KeyboardInterrupt:
            pass
        finally:
            app.jobs.close()
            server.server_close()
