import copy
import contextlib
import io
import unittest
from pathlib import Path

from arena.core import ArenaError, DEFAULT_SCENARIO, ROOT, copy_submission, load_manifest, make_scenario, read_json, scratch_directory, submission, validate_scenario, write_json
from arena.engine import Engine
from arena.tournament import report, run_tournament, schedule


class ProtocolTests(unittest.TestCase):
    def test_balanced_pairs_and_separate_mirrors(self):
        manifest = {"strategies": [{"id": "a"}, {"id": "b"}, {"id": "c"}], "seeds": [11, 22], "include_mirrors": True}
        matches = schedule(manifest)
        self.assertEqual(len(matches), 18)
        self.assertEqual(len({m["id"] for m in matches}), 18)
        ranked = [m for m in matches if not m["mirror"]]
        for match in ranked:
            self.assertEqual(sum(m["sides"] == match["sides"][::-1] and m["seed"] == match["seed"] for m in ranked), 1)

    def test_reject_silent_scenario_fields(self):
        for key in ("max_operations_per_entity", "typo"):
            with self.assertRaises(ArenaError):
                validate_scenario({**DEFAULT_SCENARIO, key: 10})
        with self.assertRaises(ArenaError):
            make_scenario(DEFAULT_SCENARIO, ["main.leek"] * 2, True)

    def test_snapshot_hashes_dependencies_and_rejects_changed_source(self):
        with scratch_directory() as tmp:
            source = Path(tmp) / "source"
            source.mkdir()
            (source / "main.leek").write_text('include("helper.leek")')
            (source / "helper.leek").write_text("var a = 1")
            info = submission(source)
            (source / "helper.leek").write_text("var a = 2")
            self.assertNotEqual(info["sha256"], submission(source)["sha256"])
            with self.assertRaises(ArenaError):
                copy_submission(source, Path(tmp) / "copy", info)
            with self.assertRaises(ArenaError):
                submission(source, "../main.leek")

    def test_teams_have_equal_stats(self):
        value = make_scenario(DEFAULT_SCENARIO, ["a.leek", "b.leek"], 123)
        for side in value["entities"]:
            for entity in side:
                for k, v in DEFAULT_SCENARIO["entity"].items():
                    self.assertEqual(entity[k], v)
        self.assertEqual(value["random_seed"], 123)


@unittest.skipUnless((ROOT / ".arena/engine.json").exists(), "Run python -m arena setup for integration tests")
class EngineIntegrationTests(unittest.TestCase):
    def test_documented_corpus_example_runs_in_pinned_engine(self):
        import re
        text = (ROOT / "docs/corpus/api-guide.md").read_text()
        code = re.search(r"```javascript\n(.*?)```", text, re.S).group(1)
        with scratch_directory() as tmp:
            source = tmp / "documented"
            source.mkdir()
            (source / "main.leek").write_text(code)
            self.assertEqual(self.engine.analyze(source, "main.leek", tmp / "analysis")["status"], "valid")
            result = self.fight(source, self.passive, "documented-example")
            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["team_metrics"]["0"]["errors"], 0)

    @classmethod
    def setUpClass(cls):
        cls.engine = Engine()

    def setUp(self):
        self.tmp = scratch_directory()
        self.root = self.tmp.__enter__()
        self.addCleanup(self.tmp.__exit__, None, None, None)
        self.passive = ROOT / "examples/strategies/passive"
        self.rush = ROOT / "examples/strategies/rush"

    def fight(self, left, right, name, config=None):
        return self.engine.fight([left, right], [submission(left), submission(right)],
                                 config or DEFAULT_SCENARIO, 101, self.root / name)

    def test_result_mapping_and_reproducibility(self):
        first = self.fight(self.rush, self.passive, "first")
        second = self.fight(self.rush, self.passive, "second")
        reverse = self.fight(self.passive, self.rush, "reverse")
        self.assertEqual(first["status"], "completed")
        self.assertEqual(first["winner_side"], 0)
        self.assertEqual(reverse["winner_side"], 1)
        self.assertEqual(first["replay_sha256"], second["replay_sha256"])
        self.assertGreater(first["team_metrics"]["0"]["operations"], 0)
        self.assertEqual(first["team_metrics"]["0"]["errors"], 0)
        outcome = read_json(self.root / "first/outcome.json")
        self.assertEqual(outcome["operations_limit_per_turn"], 20_000_000)
        self.assertEqual(sum(r["operations"] for r in outcome["turn_metrics"] if r["side"] == 0),
                         first["team_metrics"]["0"]["operations"])
        for metric in ("damage_dealt", "damage_taken", "healing_given", "healing_received"):
            self.assertTrue(all(type(r[metric]) is int for r in outcome["turn_metrics"]))
        self.assertEqual(sum(r["damage_dealt"] for r in outcome["turn_metrics"]),
                         sum(r["damage_taken"] for r in outcome["turn_metrics"]))
        self.assertGreater(sum(r["damage_dealt"] for r in outcome["turn_metrics"] if r["side"] == 0), 0)

    def test_draw_and_explicit_map_applied(self):
        config = copy.deepcopy(DEFAULT_SCENARIO)
        config["max_turns"] = 2
        config["map"] = {"obstacles": {"300": True}, "team1": [100, 101], "team2": [500, 501]}
        result = self.fight(self.passive, self.passive, "draw", config)
        self.assertEqual(result["winner_side"], -1)
        outcome = read_json(self.root / "draw/outcome.json")
        self.assertIn("300", outcome["fight"]["map"]["obstacles"])
        # Replay entities follow initiative order, not team-list order.
        self.assertEqual({e["cellPos"] for e in outcome["fight"]["leeks"] if e["team"] == 1}, {100, 101})
        self.assertEqual({e["cellPos"] for e in outcome["fight"]["leeks"] if e["team"] == 2}, {500, 501})

    def test_analysis_and_includes_are_scoped(self):
        source = self.root / "source"
        (source / "lib").mkdir(parents=True)
        (source / "main.leek").write_text('include("lib/helper.leek")')
        (source / "lib/helper.leek").write_text("var enemy = getNearestEnemy()")
        valid = self.engine.analyze(source, "main.leek", self.root / "valid")
        self.assertEqual(valid["status"], "valid")
        (source / "main.leek").write_text('include("../../2/main.leek")')
        invalid = self.engine.analyze(source, "main.leek", self.root / "escape")
        self.assertEqual(invalid["status"], "invalid")
        (source / "main.leek").write_text("var = ???")
        invalid = self.engine.analyze(source, "main.leek", self.root / "invalid")
        self.assertEqual(invalid["status"], "invalid")

    def test_invalid_ai_is_counted_as_player_error(self):
        source = self.root / "broken"
        source.mkdir()
        (source / "main.leek").write_text("var = ???")
        result = self.fight(source, self.rush, "invalid-fight")
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["winner_side"], 1)
        self.assertGreater(result["team_metrics"]["0"]["errors"], 0)

    def test_paths_with_spaces_and_multifile_includes(self):
        source = self.root / "strategy with spaces"
        (source / "lib").mkdir(parents=True)
        (source / "main.leek").write_text('include("lib/helper.leek")')
        (source / "lib/helper.leek").write_text("var enemy = getNearestEnemy()")
        result = self.engine.analyze(source, "main.leek", self.root / "output with spaces")
        self.assertEqual(result["status"], "valid")

    def test_operation_limit_is_enforced(self):
        source = self.root / "loop"
        source.mkdir()
        (source / "main.leek").write_text("while (true) {}")
        config = copy.deepcopy(DEFAULT_SCENARIO)
        config["max_turns"] = 1
        config["entity"]["cores"] = 1
        result = self.fight(source, self.passive, "limited", config)
        self.assertEqual(result["status"], "completed")
        self.assertGreater(result["team_metrics"]["0"]["operation_limit_hits"], 0)

    def test_timeout_is_unscored_infrastructure_failure(self):
        engine = Engine(timeout=0.001)
        result = engine.fight([self.passive] * 2, [submission(self.passive)] * 2, DEFAULT_SCENARIO, 101, self.root / "timeout")
        self.assertEqual(result["status"], "timeout")
        self.assertNotIn("winner_side", result)

    def test_resume_and_corruption_checks(self):
        manifest = load_manifest(ROOT / "examples/tournament.json")
        manifest["strategies"] = [manifest["strategies"][0], manifest["strategies"][2]]
        manifest["seeds"] = [101]
        out = self.root / "tournament"
        with contextlib.redirect_stdout(io.StringIO()):
            first = run_tournament(self.engine, manifest, out)
            paths = sorted((out / "matches").glob("*/attempt-*"))
            second = run_tournament(self.engine, manifest, out, resume=True)
        self.assertEqual(first, second)
        self.assertEqual(paths, sorted((out / "matches").glob("*/attempt-*")))
        self.assertEqual(first["completed"], 4)
        self.assertEqual(first["standings"][0]["played"], 2)
        self.assertEqual(len(first["mirrors"]), 2)
        altered = copy.deepcopy(manifest)
        altered["seeds"] = [202]
        with self.assertRaises(ArenaError):
            run_tournament(self.engine, altered, out, resume=True)
        outcome = paths[0] / "outcome.json"
        outcome.write_text("{}")
        with self.assertRaises(ArenaError):
            report(out)


if __name__ == "__main__":
    unittest.main()
