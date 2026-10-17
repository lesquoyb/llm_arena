"""UI contracts: immutable history, protocol grouping, local HTTP and worker resume."""
import copy
import hashlib
import json
from pathlib import Path
import threading
import time
import unittest
from urllib import request, error
from unittest import mock

from arena.core import ArenaError, ROOT, read_json, scratch_directory, write_json
from arena.experiment import Journal
from arena_web.data import Store
from arena_web.jobs import Jobs
from arena_web.replay import cell_position, describe
from arena_web.server import Application, Server


def api_model():
    return {"id": "real-test", "provider": "openai", "model": "fixture-model",
            "api_key_env": "ARENA_UI_TEST_KEY", "max_input_tokens_per_call": 1000,
            "max_output_tokens": 128,
            "pricing": {"date": "2026-10-15", "currency": "USD", "input_per_million": "1", "output_per_million": "2"}}


def write_history(content, success=True):
    return [{"role": "assistant", "tool_calls": [{"name": "write_file", "arguments": {"path": "main.leek", "content": content}}]},
            {"role": "tool", "name": "write_file", "provider_call_id": "call-1-tool-0",
             "result": {"sha256": hashlib.sha256(content.encode()).hexdigest()} if success else {"error": "rejected"}}]


def fixture(store, identifier="example", score=.5, life=600):
    root = store.runs / identifier
    config = read_json(ROOT / "configs/offline-complete.json")
    config["scenario"]["entity"]["life"] = life
    write_json(root / "experiment.json", {"config": config, "scientific_identity": {"engine": "fixture"}, "engine": {}})
    history = [{"role": "user", "content": "PROMPT INITIAL <script>not executable</script>"}]
    history += write_history("var a = 1") + write_history("invalid proposed write", False)
    history += [{"role": "user", "content": "Improve", "generation": 1}]
    history += write_history("var a = 2\n")
    journal = Journal(root)
    try:
        state = {"model": "mock-repair", "replicate": 0, "generation": 0, "condition": "initial",
                 "history": history, "status": "submitted", "calls": 3, "steps": 3,
                 "test_matches": 0, "wall_seconds": 1}
        journal.save("mock-repair-r0", state, "model_response", {"test": "event"})
    finally:
        journal.db.close()
    row = {"session": "mock-repair-r0", "model": "mock-repair", "replicate": 0, "generation": 0,
           "condition": "initial", "panel": "controls", "score": score, "failed": 0,
           "completed": 2, "operations": 100, "errors": 0, "cost_usd": "0",
           "input_tokens": None, "output_tokens": None}
    write_json(root / "analysis.json", {"rows": [row]})
    work = root / "evaluations/g1-panel/matches/reference"
    write_json(work / "provenance.json", {"submissions": [{"sha256": "candidate"}, {"sha256": "fixed"}]})
    write_json(root / "evaluations/g1-panel/results.json", {"ref": {"opponent": "fixed-rush", "side": 0,
               "artifact_dir": work.relative_to(root).as_posix()}})
    write_json(root / "report.json", {"simulated": True, "sessions": 1, "cost_usd": "0"})
    return root


class WebContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = scratch_directory()
        self.root = self.tmp.__enter__()
        self.addCleanup(self.tmp.__exit__, None, None, None)
        self.store = Store(self.root / "runs", self.root / "ui")

    def test_pinned_equipment_catalog_and_reference_documents(self):
        from arena_web.server import Application
        app = Application(self.store)
        catalog = app.get("/api/equipment", {})
        self.assertEqual(catalog["weapons"]["37"]["name"], "pistol")
        self.assertEqual(catalog["weapons"]["408"]["name"], "odachi")
        self.assertEqual(catalog["effects"]["1"], "Damage")
        self.assertGreater(len(catalog["chips"]), 100)
        document = app.get("/api/reference", {"document": ["api"]})
        self.assertIn("LeekScript", document["content"])
        with self.assertRaises(ArenaError):
            app.get("/api/reference", {"document": ["../engine.lock.json"]})

    def test_live_reader_tolerates_journal_before_schema_initialization(self):
        root = self.store.runs / "starting"
        root.mkdir()
        write_json(root / "experiment.json", {"config": {}})
        (root / "journal.sqlite").touch()
        self.assertEqual(self.store.states(root), {})
        self.assertEqual(self.store.events("starting"), {"total": 0, "events": []})

    def test_versions_require_successful_receipts_and_preserve_inherited_history(self):
        fixture(self.store)
        versions = self.store.versions("example", "mock-repair-r0")["versions"]
        self.assertEqual(len(versions), 2)
        self.assertEqual([v["generation"] for v in versions], [0, 1])
        result = self.store.source("example", "mock-repair-r0", 1, "main.leek")
        self.assertEqual(result["before"], "var a = 1")
        self.assertEqual(result["after"], "var a = 2\n")
        self.assertIn("-var a = 1", result["diff"])
        self.assertIn("+var a = 2", result["diff"])
        self.assertIn("\\ No newline at end of file", result["diff"])
        self.assertEqual(self.store.conversation("example", "mock-repair-r0", 0, 1)["messages"][0]["content"],
                         "PROMPT INITIAL <script>not executable</script>")

    def test_drafts_resolve_latest_profiles_but_runs_keep_frozen_settings(self):
        old = dict(api_model(), provider='openai-compatible', endpoint='http://localhost:11434/v1/chat/completions')
        self.store.save_participant(old)
        config = read_json(ROOT/'configs/offline-complete.json')
        config.update(models=[old], spending={'allow_paid_calls':True})
        draft = self.store.save_draft(config)
        file = self.store.state/'competitions'/(draft['id']+'.json')
        original = file.read_bytes()
        updated = {**old, 'endpoint':'http://localhost:11435/v1/chat/completions', 'model':'updated-local-model'}
        self.store.save_participant(updated)
        self.assertEqual(self.store.draft(draft['id'])['config']['models'], [updated])
        self.assertEqual(self.store.drafts()[0]['config']['models'], [updated])
        self.assertEqual(file.read_bytes(), original)
        app = Application(self.store)
        preview = app.post('/api/plan', {'config':config})
        self.assertEqual(preview['config']['models'], [updated])
        frozen = app.post('/api/plan', {'config':config, 'frozen':True})
        self.assertEqual(frozen['config']['models'], [old])
        with mock.patch('arena_web.jobs.subprocess.Popen') as process:
            with self.assertRaisesRegex(ArenaError,'settings changed'):
                app.jobs.launch(draft_id=draft['id'],confirm_paid=True,expected_config_sha256=frozen['config_sha256'])
            process.assert_not_called()
        root = self.store.runs/'frozen'
        write_json(root/'experiment.json', {'config':config})
        self.assertEqual(self.store.detail('frozen')['metadata']['config']['models'], [old])

    def test_live_revision_changes_without_conversation_or_root_report_changes(self):
        root = fixture(self.store)
        before = self.store.detail('example')
        write_json(root/'tournament/records/live.json', {'match':{'sides':['A','B']}, 'result':{}})
        after = self.store.detail('example')
        self.assertEqual(before['sessions'],after['sessions'])
        self.assertEqual(before['report'],after['report'])
        self.assertNotEqual(before['revision'],after['revision'])

    def test_training_tests_are_visible_but_excluded_from_competition_statistics(self):
        root = fixture(self.store)
        before = self.store.statistics('example')
        work = root/'sessions/mock-repair-r0/tools/call-1-tool-0-side-0/attempt-1'
        write_json(work/'scenario.json', {'random_seed':17,'entities':[[{'cores':1}],[{'cores':1}]]})
        write_json(work/'provenance.json', {})
        write_json(work/'result.json', {'status':'completed','winner_side':0,'turns':1})
        write_json(work/'outcome.json', {'fight':{'leeks':[],'actions':[]}})
        rows = self.store.matches('example')['matches']
        training = [r for r in rows if r['kind']=='training']
        self.assertEqual(len(training),1)
        self.assertFalse(training[0]['counts_toward_standings'])
        after = self.store.statistics('example')
        self.assertEqual(after['training_matches'],1)
        self.assertEqual(after['stages'],before['stages'])

    def test_journal_filters_models_before_counting_and_pagination(self):
        root = fixture(self.store)
        journal = Journal(root)
        base = journal.state("mock-repair-r0")
        try:
            for sid, model in (("other-r0", "other"), ("other-r1", "other"), ("repair-r1", "mock-repair")):
                journal.save(sid, {**base, "model": model}, "model_response", {"session": sid})
        finally:
            journal.db.close()
        before = (root / "journal.sqlite").read_bytes()
        first = self.store.events("example", model="mock-repair", limit=1)
        second = self.store.events("example", model="mock-repair", offset=1, limit=1)
        self.assertEqual(first["total"], 2)
        self.assertEqual(first["events"][0]["session"], "mock-repair-r0")
        self.assertEqual(second["events"][0]["session"], "repair-r1")
        self.assertEqual(self.store.events("example", "other-r0", model="mock-repair")["total"], 0)
        self.assertEqual(self.store.events("example", model="unknown' OR 1=1 --")["total"], 0)
        self.assertEqual(self.store.events("example")["total"], 4)
        self.assertEqual((root / "journal.sqlite").read_bytes(), before)

    def test_viewing_events_is_read_only_and_detects_modified_artifact(self):
        root = fixture(self.store)
        before = (root / "journal.sqlite").read_bytes()
        events = self.store.events("example")["events"]
        self.assertEqual(self.store.event("example", events[0]["id"]), {"test": "event"})
        self.assertEqual((root / "journal.sqlite").read_bytes(), before)
        write_json(root / events[0]["artifact"], {"test": "tampered"})
        with self.assertRaisesRegex(ArenaError, "artifact hash no longer matches"):
            self.store.event("example", events[0]["id"])

    def test_aggregate_separates_protocols_and_omits_duplicate_exports(self):
        fixture(self.store, "one", .4)
        fixture(self.store, "two", .8)
        fixture(self.store, "different-rules", .9, life=700)
        budget = fixture(self.store, "different-budget", .1)
        metadata = read_json(budget / "experiment.json")
        metadata["config"]["budget_per_session"]["max_calls"] += 1
        write_json(budget / "experiment.json", metadata)
        exported = fixture(self.store, "exported", 1)
        write_json(exported / "export.json", {})
        result = self.store.aggregate(["one", "two", "one", "different-rules", "different-budget", "exported"])
        self.assertEqual(len(result["groups"]), 3)
        same = next(g for g in result["groups"] if len(g["runs"]) == 2)
        self.assertAlmostEqual(same["models"][0]["score"], .6)
        self.assertEqual(same["models"][0]["conversations"], 2)
        self.assertIsNone(same["models"][0]["input_tokens"])
        self.assertEqual(len(result["excluded"]), 1)

    def test_secrets_stay_in_memory_and_paid_launch_requires_confirmation(self):
        model = api_model()
        self.store.save_participant(model, "secret-for-test-only")
        self.assertNotIn("secret-for-test-only", (self.store.state / "participants.json").read_text())
        self.assertNotIn("secret-for-test-only", json.dumps(self.store.participants()))
        self.assertTrue(self.store.participants()[0]["key_configured"] if self.store.participants()[0]["spec"]["id"] == model["id"]
                        else next(p for p in self.store.participants() if p["spec"]["id"] == model["id"])["key_configured"])
        config = read_json(ROOT / "configs/offline-complete.json")
        config["models"] = [model]
        config["spending"] = {"allow_paid_calls": True, "max_total_usd": "2"}
        config["budget_per_session"].update(max_input_tokens=10000, max_output_tokens=1000, max_cost_usd="1")
        draft = self.store.save_draft(config)
        jobs = Jobs(self.store)
        with mock.patch("arena_web.jobs.subprocess.Popen") as launch:
            for args in ({}, {"confirm_paid": True, "ceiling": "3"}):
                with self.assertRaisesRegex(ArenaError, "Confirm the spending limit"):
                    jobs.launch(draft_id=draft["id"], **args)
            launch.assert_not_called()

    def test_engine_data_filter_does_not_hide_generated_code_in_data_directory(self):
        root = fixture(self.store)
        code = root/"sessions/mock-repair-r0/submission/data/main.leek"
        code.parent.mkdir(parents=True)
        code.write_text("// generated",encoding="utf-8")
        resource = root/"matches/one/data/forbidden_words.txt"
        resource.parent.mkdir(parents=True)
        resource.write_text("upstream fixture",encoding="utf-8")
        write_json(resource.parent.parent/"outcome.json",{})
        rows = {r["path"]:r for r in self.store.files("example")["files"]}
        self.assertFalse(rows[code.relative_to(root).as_posix()]["engine_data"])
        self.assertTrue(rows[resource.relative_to(root).as_posix()]["engine_data"])

    def test_model_catalog_can_use_session_key_without_writing_or_echoing_it(self):
        app = Application(self.store)
        self.addCleanup(app.jobs.close)
        self.store.secrets["ARENA_GEMINI_KEY"] = "catalog-only-secret"
        with mock.patch("arena.api_providers.list_models", return_value={"models":[{"id":"models/test"}]}) as listing:
            result = app.post("/api/models", {"provider":"gemini", "api_key_env":"ARENA_GEMINI_KEY"})
        listing.assert_called_once_with("gemini","catalog-only-secret",None)
        self.assertNotIn("catalog-only-secret",str(result))
        self.assertFalse((self.store.state/"participants.json").exists())

    def test_statistics_cache_updates_when_an_outcome_changes(self):
        root = fixture(self.store)
        work = root/"matches/cached"
        result = {"status":"completed","winner_side":0}
        write_json(work/"result.json",result)
        write_json(root/"records/cached.json", {"match":{"sides":["A","B"],"seed":1},"directory":"matches/cached","result":result})
        data = {"fight":{"leeks":[{"id":0,"team":1,"name":"A"}],"actions":[[7,0],[13,37]]}}
        write_json(work/"outcome.json",data)
        first = self.store.statistics("example")
        self.assertEqual(first["stages"][0]["strategies"]["A"]["actions"],1)
        self.assertEqual(first["match_totals"]["matches/cached"][0]["actions"],1)
        data["fight"]["actions"].append([13,37])
        write_json(work/"outcome.json",data)
        second = self.store.statistics("example")
        self.assertEqual(second["stages"][0]["strategies"]["A"]["actions"],2)
        self.assertEqual(second["match_totals"]["matches/cached"][0]["actions"],2)

    def test_paths_cannot_escape_run_directory(self):
        fixture(self.store)
        for name in ("../outside", "C:/Windows", r"..\outside", "main.leek:secret"):
            with self.assertRaises(ArenaError):
                self.store.run_path(name)
        with self.assertRaises(ArenaError):
            self.store.save_draft(read_json(ROOT / "configs/offline-complete.json"), "../outside")

    def test_replay_matches_pinned_cell_layout_and_labels_actual_damage(self):
        cells = [cell_position(i) for i in range(613)]
        self.assertEqual(len({(c["x"], c["y"]) for c in cells}), 613)
        self.assertEqual(cells[0], {"id": 0, "x": 0, "y": 0})
        self.assertEqual(cells[612], {"id": 612, "x": 408, "y": 204})
        replay = describe({"leeks": [{"id": 0, "name": "A"}], "actions": [[0], [7, 0], [10, 0, 35, [18, 35]],
                           [101, 0, 20, 1], [6, 2], [9999]], "map": {"width": 18, "height": 18}})
        self.assertIn("loses 20 HP", replay["events"][3]["text"])
        self.assertEqual(replay["events"][4]["turn"], 2)
        self.assertEqual(replay["unknown_codes"], [9999])

    def test_http_rejects_cross_origin_mutations_and_serves_untrusted_files_as_text(self):
        root = fixture(self.store)
        (root / "untrusted.html").write_text("<script>alert(1)</script>", encoding="utf-8")
        app = Application(self.store)
        server = Server(("127.0.0.1", 0), app)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}"
        try:
            with request.urlopen(base + "/api/file?run=example&path=untrusted.html") as response:
                self.assertTrue(response.headers["Content-Type"].startswith("text/plain"))
                self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
            payload = json.dumps({"config": read_json(ROOT / "configs/offline-complete.json")}).encode()
            for extra, expected in (({}, 403), ({"X-Arena-Token": app.token, "Origin": "https://untrusted.example"}, 400)):
                req = request.Request(base + "/api/competition", data=payload,
                                      headers={"Content-Type": "application/json", **extra})
                with self.assertRaises(error.HTTPError) as raised:
                    request.urlopen(req)
                self.assertEqual(raised.exception.code, expected)
            with request.urlopen(request.Request(base + "/api/competition", data=payload,
                       headers={"Content-Type": "application/json", "X-Arena-Token": app.token})) as response:
                self.assertIn("id", json.load(response))
            req = request.Request(base + "/api/runs", headers={"Host": "untrusted.example"})
            with self.assertRaises(error.HTTPError):
                request.urlopen(req)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)
            app.jobs.close()


@unittest.skipUnless((ROOT / ".arena/engine.json").exists(), "Build the engine")
class WebWorkerIntegrationTests(unittest.TestCase):
    def test_ui_worker_runs_real_competition_and_resume_reuses_results(self):
        with scratch_directory() as tmp:
            store = Store(tmp / "runs with spaces", tmp / "ui state")
            config = read_json(ROOT / "configs/offline-complete.json")
            config.update(generations=1, include_mirrors=False)
            for model in config["models"]:
                model["id"] += "-worker"
                model["profile"] = "single-shot"
            config["scenario"]["max_turns"] = 1
            draft = store.save_draft(config)
            jobs = Jobs(store)
            def wait(expected="completed"):
                deadline = time.monotonic() + 120
                while jobs.listing()[0]["status"] in {"running", "stopping"}:
                    if time.monotonic() > deadline:
                        self.fail(jobs.log(jobs.listing()[0]["id"])["content"])
                    time.sleep(.1)
                self.assertEqual(jobs.listing()[0]["status"], expected, jobs.log(jobs.listing()[0]["id"])["content"])
            try:
                row = jobs.launch(draft_id=draft["id"])
                deadline = time.monotonic() + 30
                while True:
                    out = store.runs / row["run"]
                    states = store.states(out) if (out / "journal.sqlite").exists() else {}
                    if any(s.get("reserved") and s.get("pending", {}).get("tool_calls", [{}])[s.get("cursor", 0)].get("name") == "analyze"
                           for s in states.values() if s.get("pending")):
                        break
                    if time.monotonic() > deadline:
                        self.fail("Worker did not enter analysis before cancellation")
                    time.sleep(.02)
                jobs.stop(row["id"])
                wait("stopped")
                jobs.launch(run_id=row["run"])
                wait()
                root = store.run_path(row["run"])
                outcomes = {p.relative_to(root).as_posix(): (p.stat().st_mtime_ns, p.read_bytes()) for p in root.rglob("outcome.json")}
                self.assertEqual(len(store.matches(row["run"])["matches"]), 2)
                self.assertEqual(len(store.detail(row["run"])["sessions"]), 2)
                jobs.launch(run_id=row["run"])
                wait()
                for name, before in outcomes.items():
                    path = root / name
                    self.assertEqual((path.stat().st_mtime_ns, path.read_bytes()), before)
            finally:
                jobs.close()


class SubmissionDiagnosticsTests(unittest.TestCase):
    def test_submitted_conversation_exposes_compilation_failure_and_member_diagnostics(self):
        from arena.core import file_hash
        with scratch_directory() as tmp:
            store = Store(tmp/'runs',tmp/'state')
            root = fixture(store)
            path = root/'sessions/mock-repair-r0/assessment.json'
            assessment = {'status':'invalid','diagnostics':[{'file':'main.leek','line':8,'message':'Unknown function'}],
                          'member_analyses':{'support.leek':{'status':'invalid','error':'Unknown symbol'}}}
            write_json(path,assessment)
            journal = Journal(root)
            try:
                state=journal.state('mock-repair-r0')
                state.update(validity='invalid',assessment_sha256=file_hash(path))
                journal.save('mock-repair-r0',state,'submission_assessment',assessment)
            finally: journal.db.close()
            data=store.conversation('example','mock-repair-r0')
            self.assertEqual(data['status'],'submitted')
            self.assertIsNone(data['failure'])
            self.assertEqual(data['diagnostics']['validation_status'],'invalid')
            self.assertEqual(data['diagnostics']['problems'][0]['phase'],'submission validation')
            self.assertEqual(data['diagnostics']['assessment'],assessment)
            self.assertEqual(store.detail('example')['sessions'][0]['validation_status'],'invalid')
            write_json(path,{'status':'valid'})
            with self.assertRaisesRegex(ArenaError,'modified'):
                store.session_diagnostics('example','mock-repair-r0')

    def test_submitted_without_round_two_fights_is_pending_not_failed(self):
        with scratch_directory() as tmp:
            store=Store(tmp/'runs',tmp/'state')
            fixture(store)
            data=store.session_diagnostics('example','mock-repair-r0')
            self.assertEqual(data['generation_status'],'submitted')
            self.assertEqual(data['validation_status'],'pending')
            self.assertEqual(data['problems'],[])
            self.assertEqual(data['matches']['failed'],0)
            self.assertIn('after all Round 2 preparation',data['schedule_note'])

    def test_fight_engine_failure_surfaces_for_both_participants_not_unrelated_sessions(self):
        with scratch_directory() as tmp:
            store=Store(tmp/'runs',tmp/'state')
            root=fixture(store)
            write_json(root/'sessions/mock-repair-r0/assessment.json',{'status':'valid'})
            write_json(root/'tournament/records/failed.json',{
                'match':{'sides':['mock-repair-r0','other-r0'],'seed':101},'directory':'matches/broken',
                'result':{'status':'engine_error','error':'Engine exited 1; see stderr.log'}})
            write_json(root/'tournament/records/elsewhere.json',{
                'match':{'sides':['unrelated-r0','other-r0'],'seed':101},'directory':'matches/elsewhere',
                'result':{'status':'timeout','error':'Deadline exceeded'}})
            data=store.conversation('example','mock-repair-r0')['diagnostics']
            self.assertEqual(data['validation_status'],'valid')
            self.assertEqual(data['matches']['failed'],1)
            self.assertEqual(len(data['problems']),1)
            self.assertEqual(data['problems'][0]['message'],'Engine exited 1; see stderr.log')
            self.assertEqual(data['problems'][0]['path'],'tournament/matches/broken')
