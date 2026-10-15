import contextlib
import copy
import io
import os
import subprocess
import unittest
from pathlib import Path
from unittest import mock

from arena.core import ArenaError, ROOT, read_json, scratch_directory, write_json
from arena.experiment import Journal, experiment_lock, load_config, plan, run, run_session, status
from arena.preparation import Preparation, local_path


class ContractTests(unittest.TestCase):
    def test_legacy_journal_migration_preserves_session(self):
        import json
        import sqlite3
        with scratch_directory() as tmp:
            connection = sqlite3.connect(tmp / "journal.sqlite")
            connection.execute("CREATE TABLE sessions (id TEXT PRIMARY KEY, state TEXT NOT NULL)")
            connection.execute("CREATE TABLE events (id INTEGER PRIMARY KEY, session TEXT, kind TEXT, payload TEXT)")
            original = {"status": "running", "history": [], "calls": 1}
            connection.execute("INSERT INTO sessions VALUES (?,?)", ("legacy-r0", json.dumps(original)))
            connection.execute("PRAGMA user_version=1")
            connection.commit()
            connection.close()
            journal = Journal(tmp)
            try:
                self.assertEqual(journal.state("legacy-r0"), original)
                self.assertEqual(journal.db.execute("PRAGMA user_version").fetchone()[0], 2)
            finally:
                journal.db.close()

    def test_paused_workspace_rejects_external_source_changes(self):
        with scratch_directory() as tmp:
            config = load_config(ROOT / "configs/offline-demo.json")
            model = {"id": "budget", "provider": "mock", "profile": "budget"}
            journal = Journal(tmp)
            def stop(kind, sid):
                if kind == "response":
                    raise KeyboardInterrupt
            try:
                with self.assertRaises(KeyboardInterrupt):
                    run_session("budget-r0", model, config, tmp, journal, None, stop)
                (tmp / "sessions/budget-r0/workspace/main.leek").write_text("var external = 1")
                with self.assertRaisesRegex(ArenaError, "Working sources changed"):
                    run_session("budget-r0", model, config, tmp, journal, None)
            finally:
                journal.db.close()
    def test_mock_failure_profiles_and_budget_are_journaled(self):
        with scratch_directory() as tmp:
            config = load_config(ROOT / "configs/offline-demo.json")
            journal = Journal(tmp)
            try:
                for profile, expected in (("timeout", "needs_reconciliation"), ("rate-limit", "provider_unavailable"),
                                          ("budget", "budget_exhausted"), ("malformed", "no_submission")):
                    sid = profile + "-r0"
                    model = {"id": profile, "provider": "mock", "profile": profile}
                    run_session(sid, model, config, tmp, journal, None)
                    self.assertEqual(journal.state(sid)["status"], expected)
                journal.verify()
                row = journal.db.execute("SELECT artifact FROM objects WHERE kind='Session' LIMIT 1").fetchone()
                (tmp / row[0]).write_text("{}")
                with self.assertRaises(ArenaError):
                    journal.verify()
            finally:
                journal.db.close()

    def test_config_refuses_paid_calls_unknown_fields_and_training_seeds(self):
        original = read_json(ROOT / "configs/offline-demo.json")
        with scratch_directory() as tmp:
            for change in ({"spending": {"allow_paid_calls": True, "max_total_usd": 1}},
                           {"seeds": [17]}, {"extra": True}):
                path = tmp / "config.json"
                write_json(path, {**original, **change})
                with self.assertRaises(ArenaError):
                    load_config(path)
        self.assertEqual(plan(original)["ranked_matches_if_all_submit"], 12)

    def test_paths_links_and_pagination(self):
        with scratch_directory() as tmp:
            root = tmp / "workspace"
            root.mkdir()
            (root / "link").symlink_to(tmp, target_is_directory=True)
            for name in ("../other/main.leek", "/etc/passwd", "link/main.leek"):
                with self.assertRaises(ArenaError):
                    local_path(root, name)
            docs = tmp / "docs"
            docs.mkdir()
            (docs / "text.md").write_text("abcdefgh")
            tools = Preparation(tmp / "session", docs, None, {})
            page = tools.call("read_docs", {"path": "text.md", "limit": 3}, "1")
            self.assertEqual(page, {"content": "abc", "truncated": True, "next_offset": 3})
            with self.assertRaises(ArenaError):
                tools.call("write_file", {"path": "x.py", "content": "pass"}, "2")

    def test_experiment_lock_excludes_second_writer(self):
        with scratch_directory() as tmp:
            with experiment_lock(tmp):
                with self.assertRaises(ArenaError):
                    with experiment_lock(tmp):
                        pass

    def test_interrupted_snapshot_does_not_publish_partial_submission(self):
        with scratch_directory() as tmp:
            tools = Preparation(tmp / "session", tmp, None, {})
            tools.call("write_file", {"path": "main.leek", "content": "var a = 1"}, "1")
            def partial(source, target, expected):
                target.mkdir()
                (target / "partial.leek").write_text("partial")
                raise OSError("Simulated interruption during copy")
            with mock.patch("arena.preparation.copy_submission", side_effect=partial):
                with self.assertRaises(OSError):
                    tools.call("submit", {}, "2")
            self.assertFalse((tools.directory / "submission").exists())
            result = tools.call("submit", {}, "2")
            self.assertIn("submission", result)
            self.assertTrue((tools.directory / "submission/main.leek").exists())

    def test_reserved_tool_resumes_without_double_charging(self):
        with scratch_directory() as tmp:
            config = load_config(ROOT / "configs/offline-demo.json")
            config["budget_per_session"]["max_agent_steps"] = 1
            config["budget_per_session"]["max_calls"] = 1
            sid = "mock-single-r0"
            response = {"role": "assistant", "tool_calls": [
                {"name": "write_file", "arguments": {"path": "main.leek", "content": "var a = 1"}}]}
            state = {"model": "mock-single", "replicate": 0, "status": "running",
                     "history": [response], "calls": 1, "steps": 1,
                     "test_matches": 0, "wall_seconds": 0, "pending": response,
                     "cursor": 0, "reserved": "call-1-tool-0"}
            journal = Journal(tmp)
            try:
                journal.save(sid, state, "tool_reserved")
                run_session(sid, config["models"][1], config, tmp, journal, None)
                saved = journal.state(sid)
                self.assertEqual(saved["steps"], 1)
                self.assertEqual(saved["status"], "budget_exhausted")
                self.assertIn("submission", saved)
            finally:
                journal.db.close()


@unittest.skipUnless((ROOT / ".arena/engine.json").exists(), "Build the engine")
class OfflineIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.config = load_config(ROOT / "configs/offline-demo.json")
        self.config["replicates"] = 1
        self.config["scenario"]["max_turns"] = 4

    def test_end_to_end_repair_and_resume_without_recomputation(self):
        with scratch_directory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            out = tmp / "experiment"
            first = run(self.config, out)
            self.assertEqual(first["sessions"], 2)
            self.assertEqual(first["tournament"]["completed"], 4)
            self.assertEqual(first["tournament"]["failed"], 0)
            states = status(out)["sessions"]
            repaired = states["mock-repair-r0"]
            diagnostics = [m["result"]["status"] for m in repaired["history"]
                           if m["role"] == "tool" and m["name"] == "analyze"]
            self.assertEqual(diagnostics, ["invalid", "valid"])
            self.assertEqual(repaired["test_matches"], 2)
            matches = sorted(out.glob("tournament/matches/*/attempt-*"))
            calls = first["model_calls"]
            second = run(self.config, out, resume=True)
            self.assertEqual(second["model_calls"], calls)
            self.assertEqual(matches, sorted(out.glob("tournament/matches/*/attempt-*")))
            altered = copy.deepcopy(self.config)
            altered["budget_per_session"]["max_calls"] += 1
            with self.assertRaises(ArenaError):
                run(altered, out, resume=True)
            (out / "sessions/mock-single-r0/submission/main.leek").write_text("var changed = 1")
            with self.assertRaises(ArenaError):
                run(self.config, out, resume=True)

    def test_interruption_after_response_reuses_saved_response(self):
        with scratch_directory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            out = tmp / "experiment"
            def stop(kind, sid):
                if kind == "response":
                    raise KeyboardInterrupt
            with self.assertRaises(KeyboardInterrupt):
                run(self.config, out, interrupt=stop)
            self.assertEqual(status(out)["sessions"]["mock-repair-r0"]["calls"], 1)
            result = run(self.config, out, resume=True)
            self.assertEqual(result["model_calls"], 9)
            self.assertEqual(result["tournament"]["completed"], 4)

    def test_zero_test_budget_freezes_current_source_and_retains_failures(self):
        with scratch_directory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            out = tmp / "experiment"
            self.config["budget_per_session"]["max_test_matches"] = 0
            self.config["models"][1]["profile"] = "empty"
            result = run(self.config, out)
            self.assertEqual(result["budget_exhausted"], 1)
            self.assertEqual(result["no_submission"], 1)
            self.assertEqual(result["preparation_matches_reserved"], 0)
            self.assertIsNone(result["tournament"])
            self.assertIsNone(result["input_tokens"])

    def test_invalid_submission_is_visible_in_report(self):
        with scratch_directory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            self.config["models"][0]["profile"] = "invalid"
            self.config["models"][1]["profile"] = "empty"
            result = run(self.config, tmp / "experiment")
            self.assertEqual(result["invalid_submissions"], 1)
            self.assertEqual(result["no_submission"], 1)
            self.assertEqual(result["assessment_failures"], 0)

    def test_java_worker_does_not_inherit_provider_credentials(self):
        from arena.engine import Engine
        original = subprocess.Popen
        with scratch_directory() as tmp, mock.patch.dict(os.environ, {"PROVIDER_SECRET": "fixture"}):
            with mock.patch("arena.engine.subprocess.Popen", wraps=original) as spawn:
                result = Engine().analyze(ROOT / "examples/strategies/rush", "main.leek", tmp / "analyze")
                self.assertEqual(result["status"], "valid")
                worker = [call for call in spawn.call_args_list if call.kwargs.get("env") is not None]
                self.assertEqual(len(worker), 1)
                self.assertNotIn("PROVIDER_SECRET", worker[0].kwargs["env"])
                self.assertTrue(worker[0].kwargs["start_new_session"])
