import contextlib
import copy
import io
import unittest
from unittest import mock
from arena.core import ROOT, ArenaError, digest, file_hash, read_json, scratch_directory, write_json
from arena.engine import Engine
from arena.experiment import run, plan, status
from arena.exporting import export_experiment


@unittest.skipUnless((ROOT / ".arena/engine.json").exists(), "Build engine")
class EvolutionIntegrationTests(unittest.TestCase):
    def test_complete_pipeline_paired_checkpoints_final_panel_export_and_resume(self):
        config = read_json(ROOT / "configs/offline-complete.json")
        config["scenario"]["max_turns"] = 1
        config["models"][0]["profile"] = "single-shot"
        config["models"][1]["profile"] = "single-shot"
        with scratch_directory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            out = tmp / "experiment"
            original_fight = Engine.fight
            injected = False
            def fail_one_reference(engine, sources, infos, scenario, seed, directory):
                nonlocal injected
                if "evaluations" in directory.parts and not injected:
                    injected = True
                    directory.mkdir(parents=True)
                    result = {"status": "timeout", "elapsed_seconds": 0,
                              "error": "Injected infrastructure timeout"}
                    write_json(directory / "result.json", result)
                    return result
                return original_fight(engine, sources, infos, scenario, seed, directory)
            with mock.patch.object(Engine, "fight", fail_one_reference):
                interrupted = run(config, out)
            self.assertTrue(interrupted["evolution"]["incomplete"])
            successful = {p.relative_to(out).as_posix(): file_hash(p)
                          for p in out.glob("evaluations/*/matches/**/outcome.json")}
            result = run(config, out, resume=True)
            for name, expected in successful.items():
                self.assertEqual(file_hash(out / name), expected)
            self.assertEqual(result["sessions"], 6)
            self.assertEqual(result["evolution"]["contemporaries"]["completed"], 16)
            self.assertFalse(result["evolution"]["incomplete"])
            self.assertEqual(len(result["evolution"]["paired"]), 2)
            states = status(out)["sessions"]
            for parent in ("mock-repair-r0", "mock-single-r0"):
                control, feedback = states[parent + "-g1-control"], states[parent + "-g1-feedback"]
                self.assertEqual(control["parent_checkpoint_sha256"], feedback["parent_checkpoint_sha256"])
                self.assertEqual(control["history"][:len(states[parent]["history"])], states[parent]["history"])
                marker = len(states[parent]["history"])
                self.assertNotIn("feedback", control["history"][marker])
                serialized = str(feedback["history"][marker]["feedback"])
                self.assertNotIn("main.leek", serialized)
                self.assertNotIn(str(out), serialized)
                self.assertNotIn("seed", serialized)
            reference = read_json(out / "evaluations/g1-panel/results.json")
            sets = {}
            for record in reference.values():
                sets.setdefault(record["session"], set()).add((record["opponent"], record["seed"], record["side"]))
            self.assertEqual(sets["mock-single-r0-g1-control"], sets["mock-single-r0-g1-feedback"])
            before = {p.relative_to(out).as_posix(): file_hash(p) for p in out.glob("evaluations/*/matches/**/*") if p.is_file()}
            resumed = run(config, out, resume=True)
            self.assertEqual(resumed["evolution"]["rows"], result["evolution"]["rows"])
            after = {p.relative_to(out).as_posix(): file_hash(p) for p in out.glob("evaluations/*/matches/**/*") if p.is_file()}
            self.assertEqual(before, after)
            exported = tmp / "export"
            export_experiment(out, exported)
            index = read_json(exported / "export.json")
            self.assertEqual(index["config"], config)
            for name, expected in index["files"].items():
                self.assertEqual(file_hash(exported / name), expected)

    def test_planner_counts_every_stage(self):
        config = read_json(ROOT / "configs/offline-complete.json")
        result = plan(config)
        self.assertEqual(result["sessions"], 6)
        self.assertEqual(result["common_reference_matches"], 60)
        self.assertEqual(result["g1_contemporary_matches"], 16)
