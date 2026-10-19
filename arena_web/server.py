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
        return {"token": self.token, "participants": self.store.participants(),
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
        if route == "/api/run":
            return store.detail(run)
        if route == "/api/provider-diagnostics":
            return store.provider_diagnostics(run, sid)
        if route == "/api/session-diagnostics":
            return store.session_diagnostics(run, sid)
        if route == "/api/conversation":
            return store.conversation(run, sid, number("offset", 0), min(number("limit", 25), 100))
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
        if route == "/api/competition":
            return self.store.save_draft(data["config"], data.get("id"))
        if route == "/api/competition/delete":
            return self.store.delete_draft(data["id"])
        if route == "/api/plan":
            config = data['config'] if data.get('frozen') else self.store.resolve_models(data['config'])
            return {**plan(validate_config(config)), 'config':config, 'config_sha256':digest(config)}
        if route == "/api/launch":
            return self.jobs.launch(draft_id=data.get("draft_id"), run_id=data.get("run"),
                                    confirm_paid=data.get("confirm_paid", False), ceiling=data.get("ceiling"), retry_session=data.get("retry_session"), expected_config_sha256=data.get("expected_config_sha256"), allow_updated_runner=data.get("allow_updated_runner") is True, retry_reasoning_effort=data.get("retry_reasoning_effort"))
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
            return {**result, "run": target.relative_to(self.store.runs).as_posix()}
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
        self.headers_for(status, "application/json; charset=utf-8", len(body))
        self.wfile.write(body)

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
                root = app.store.run_path(query['run'][0])
                table = query.get('table', ['results'])[0]
                if table not in {'results', 'fights', 'sessions'}:
                    raise ArenaError('Unknown results table')
                with TemporaryDirectory(prefix='arena-results-') as directory:
                    target = Path(directory) / 'export'
                    export([root], target)
                    body = (target / (table + '.csv')).read_bytes()
                self.headers_for(200, 'text/csv; charset=utf-8', len(body), table + '.csv')
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
                names = {"/": "index.html", "/app.js": "app.js", "/style.css": "style.css", "/workspace.css": "workspace.css", "/favicon.png": "favicon.png"}
                if parsed.path not in names:
                    self.json_response(404, {"error": "Page not found"})
                    return
                path = STATIC / names[parsed.path]
                body = path.read_bytes()
                mime = {".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".png": "image/png"}[path.suffix]
                self.headers_for(200, mime if path.suffix == ".png" else mime + "; charset=utf-8", len(body))
                self.wfile.write(body)
        except (ArenaError, ValueError, KeyError, TypeError, OSError, sqlite3.Error) as error:
            self.json_response(400, {"error": str(error)})
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_POST(self):
        try:
            self.check_origin()
            if not secrets.compare_digest(self.headers.get("X-Arena-Token", ""), self.server.app.token):
                self.json_response(403, {"error": "Reload the page before continuing"})
                return
            if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                raise ArenaError("Content-Type application/json requis")
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 2_000_000:
                raise ArenaError("Request is empty or too large")
            data = json.loads(self.rfile.read(length))
            self.json_response(200, self.server.app.post(urlsplit(self.path).path, data))
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
