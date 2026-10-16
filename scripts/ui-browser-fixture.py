"""Ephemeral, explicitly synthetic archive for browser tests; no engine/API needed."""
from pathlib import Path
import json
import sys
import time

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
from arena.core import scratch_directory, write_json, read_json
from arena.experiment import Journal
from arena_web.data import Store
from arena_web.server import Application, Server
from test_web import fixture, write_history


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
            source.write_text("var a = 2\n", encoding="utf-8", newline="\n")
            work = root / "matches/browser-fixture/attempt-1"
            result = {"status": "completed", "winner_side": 0, "turns": 1, "elapsed_seconds": .1,
                      "team_metrics": {"0": {"operations": 100, "errors": 0}, "1": {"operations": 10, "errors": 0}}}
            fight = {"version": 1, "map": {"width": 18, "height": 18, "obstacles": {"7": 1}},
                     "leeks": [{"id": 0, "name": "Équipe bleue", "team": 1, "life": 30, "cellPos": 0, "summon": False},
                               {"id": 1, "name": "Équipe orange", "team": 2, "life": 20, "cellPos": 2, "summon": False},
                               {"id": 2, "name": "Fixture bulb", "team": 1, "life": 10, "cellPos": 35, "summon": True}],
                     "actions": [[0], [7, 0], [10, 0, 18, [18]], [16, 2, 1], [101, 1, 20, 0], [9, 0, 2, 35, 1], [7, 2], [10, 2, 36, [36]], [5, 1, 0]]}
            write_json(work / "scenario.json", {"entities":[[{"cores":10}],[{"cores":10}]]})
            write_json(work / "result.json", result)
            write_json(work / "outcome.json", {"fight": fight, "winner": 0, "success": True})
            write_json(root / "records/browser-fixture.json", {"match": {"sides": ["mock-repair-r0", "passive"],
                       "seed": 301, "mirror": False}, "directory": work.relative_to(root).as_posix(), "result": result})
            (root / "report.md").write_text("# Rapport navigateur\n\n**Résultat** : terminé.\n\n<img src=x onerror=window.__arenaUnexpectedScript=1>\n\n| Stat | Valeur |\n| --- | --- |\n| Score | 50 % |\n", encoding="utf-8")
            write_json(root / "example.json", {"result": {"score": .5}, "literal":"<script>window.__arenaUnexpectedScript=1</script>"})
        threads = fixture(store, "threads")
        journal = Journal(threads)
        try:
            base = journal.state("mock-repair-r0")
            journal.save("mock-repair-r1", {**base, "replicate":1,
                "history":[{"role":"user","content":"Second repair conversation"}]},
                "session_created", {"test":"repair repetition"})
            journal.save("mock-single-r0", {**base, "model":"mock-single", "status":"provider_unavailable",
                "failure":{"message":"Provider HTTP 429","phase":"provider request","retryable":True},
                "history":[{"role":"user","content":"Single model conversation"}]},
                "session_created", {"test":"single model"})
        finally:
            journal.db.close()
        legacy = store.runs / "legacy"
        write_json(legacy / "experiment.json", {"manifest":{"name":"Tournoi sans génération", "strategies":[]}})
        write_json(legacy / "report.json", {"completed":0})
        code = legacy / "sources/passive/main.leek"
        code.parent.mkdir(parents=True)
        code.write_text("// stratégie fournie directement\n",encoding="utf-8")
        matrix = store.runs / "matrix"
        write_json(matrix / "experiment.json", {"manifest":{"name":"Matrix filter fixture","strategies":[]}})
        write_json(matrix / "report.json", {"completed":7})
        cases = [("win-left",["A","B"],0,"."), ("win-right",["B","A"],1,"."),
                 ("draw",["A","B"],-1,"."), ("loss",["B","A"],0,"."),
                 ("failure",["A","B"],None,"."), ("other-opponent",["A","C"],0,"."),
                 ("mirror",["A","A"],0,"."), ("other-stage",["A","B"],0,"tournament")]
        for label,sides,winner,stage in cases:
            base = matrix if stage == "." else matrix/stage
            work = base/"matches"/label/"attempt-1"
            result = {"status":"timeout", "error":"Fixture timeout"} if winner is None else {
                "status":"completed","winner_side":winner,"turns":1,"elapsed_seconds":.1}
            write_json(work/"result.json",result)
            write_json(work/"scenario.json", {"entities":[[{"cores":10}],[{"cores":10}]]})
            if winner is not None:
                write_json(work/"outcome.json", {"fight":fight,"winner":winner,"success":True})
            write_json(base/"records"/(label+".json"), {"match":{"sides":sides,"seed":301,"mirror":label=="mirror"},
                       "directory":work.relative_to(base).as_posix(),"result":result})
        class FixtureApplication(Application):
            def post(self, route, data):
                if route != '/api/fixture-live':
                    return super().post(route,data)
                root = store.runs/'live'
                action = data['action']
                if action == 'start':
                    config = read_json(ROOT/'configs/offline-complete.json')
                    config.update(generations=1,replicates=1,models=config['models'][:1])
                    write_json(root/'experiment.json',{'config':config,'engine':{},'scientific_identity':{'fixture':'live'}})
                    write_json(root/'report.json',{})
                    journal = Journal(root)
                    journal.save('mock-repair-r0',{'model':'mock-repair','replicate':0,'generation':0,'condition':'initial',
                        'history':[{'role':'user','content':'Live fixture prompt'}],'status':'submitted','calls':1,'steps':0,
                        'test_matches':0,'wall_seconds':1},'session_created')
                    journal.db.close()
                    logs = store.state/'jobs';logs.mkdir(exist_ok=True)
                    (logs/'fixture-live.log').write_text('Synthetic running job',encoding='utf-8')
                    self.jobs.rows.append({'id':'fixture-live-job','run':'live','name':'Live fixture','status':'running',
                        'started_at':time.time(),'log':'fixture-live.log'})
                elif action in {'training','competition'}:
                    def save(work):
                        result = {'status':'completed','winner_side':0,'turns':1,'elapsed_seconds':.1}
                        write_json(work/'scenario.json',{'random_seed':17,'entities':[[{'cores':10}],[{'cores':10}]]})
                        write_json(work/'provenance.json',{})
                        write_json(work/'result.json',result)
                        write_json(work/'outcome.json',{'fight':fight,'winner':0,'success':True})
                        return result
                    if action == 'training':
                        for side in (0,1):
                            save(root/f'sessions/mock-repair-r0/tools/call-1-tool-0-side-{side}/attempt-1')
                    else:
                        number = len(list((root/'records').glob('*.json'))) + 1
                        work = root/f'matches/live-{number}/attempt-1'
                        result = save(work)
                        write_json(root/f'records/live-{number}.json',{'match':{'sides':['mock-repair-r0','mock-single-r0'],'seed':101,'mirror':False},
                            'directory':work.relative_to(root).as_posix(),'result':result})
                elif action in {'event','file','source'}:
                    journal = Journal(root)
                    state = journal.state('mock-repair-r0')
                    if action == 'file':
                        (root/'live-note.txt').write_text('New file while running',encoding='utf-8')
                    if action == 'source':
                        state['history'] += write_history('var live = 1')
                    journal.save('mock-repair-r0',state,'fixture_live_update',{'action':action})
                    journal.db.close()
                elif action == 'finish':
                    self.jobs.rows[-1]['status']='completed'
                return {'updated':action}
        app = FixtureApplication(store)
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
