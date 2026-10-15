"""Ephemeral, explicitly synthetic archive for browser tests; no engine/API needed."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
from arena.core import scratch_directory, write_json
from arena_web.data import Store
from arena_web.server import Application, Server
from test_web import fixture


def main():
    with scratch_directory() as tmp:
        store = Store(tmp / "runs", tmp / "ui")
        for identifier, score in (("one", .4), ("two", .8)):
            root = fixture(store, identifier, score)
            analysis = json.loads((root / "analysis.json").read_text(encoding="utf-8"))
            analysis["rows"].append({**analysis["rows"][0], "panel": "all"})
            write_json(root / "analysis.json", analysis)
            source = root / "sessions/mock-repair-r0/submission/main.leek"
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_text("var a = 2\n", encoding="utf-8")
            work = root / "matches/browser-fixture/attempt-1"
            result = {"status": "completed", "winner_side": 0, "turns": 1, "elapsed_seconds": .1,
                      "team_metrics": {"0": {"operations": 100, "errors": 0}, "1": {"operations": 10, "errors": 0}}}
            fight = {"version": 1, "map": {"width": 18, "height": 18, "obstacles": {"7": 1}},
                     "leeks": [{"id": 0, "name": "Équipe bleue", "team": 1, "life": 30, "cellPos": 0, "summon": False},
                               {"id": 1, "name": "Équipe orange", "team": 2, "life": 20, "cellPos": 2, "summon": False}],
                     "actions": [[0], [7, 0], [10, 0, 18, [18]], [16, 2, 1], [101, 1, 20, 0], [5, 1, 0]]}
            write_json(work / "result.json", result)
            write_json(work / "outcome.json", {"fight": fight, "winner": 0, "success": True})
            write_json(root / "records/browser-fixture.json", {"match": {"sides": ["mock-repair-r0", "passive"],
                       "seed": 301, "mirror": False}, "directory": work.relative_to(root).as_posix(), "result": result})
            (root / "report.md").write_text("# Rapport navigateur\n\n**Résultat** : terminé.\n\n<img src=x onerror=window.__arenaUnexpectedScript=1>\n\n| Stat | Valeur |\n| --- | --- |\n| Score | 50 % |\n", encoding="utf-8")
            write_json(root / "example.json", {"result": {"score": .5}, "literal":"<script>window.__arenaUnexpectedScript=1</script>"})
        legacy = store.runs / "legacy"
        write_json(legacy / "experiment.json", {"manifest":{"name":"Tournoi sans génération", "strategies":[]}})
        write_json(legacy / "report.json", {"completed":0})
        code = legacy / "sources/passive/main.leek"
        code.parent.mkdir(parents=True)
        code.write_text("// stratégie fournie directement\n",encoding="utf-8")
        app = Application(store)
        server = Server(("127.0.0.1", 0), app)
        print(json.dumps({"url": f"http://127.0.0.1:{server.server_port}"}), flush=True)
        try:
            server.serve_forever(poll_interval=.1)
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
            app.jobs.close()


if __name__ == "__main__":
    main()
