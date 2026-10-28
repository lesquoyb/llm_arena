from __future__ import annotations

import itertools
from pathlib import Path

from .core import ArenaError, copy_submission, digest, file_hash, file_lock, make_scenario, read_json, submission, write_json
from .engine import Engine


def schedule(manifest: dict) -> list[dict]:
    ids = [s["id"] for s in manifest["strategies"]]
    pairs = list(itertools.combinations(ids, 2))
    if manifest.get("include_mirrors", False):
        pairs.extend((s, s) for s in ids)
    matches = []
    for a, b in pairs:
        for seed in manifest["seeds"]:
            # A mirror has no distinct reverse fixture.
            for sides in ([(a, b), (b, a)] if a != b else [(a, a)]):
                match = {"sides": list(sides), "seed": seed, "mirror": a == b}
                match["id"] = digest(match)[:20]
                matches.append(match)
    return matches


def verify_record(root: Path, record: dict):
    if record["result"]["status"] != "completed":
        return
    work = root / record["directory"]
    if file_hash(work / "outcome.json") != record["result"]["outcome_sha256"]:
        raise ArenaError(f"Stored outcome was modified: {work}")
    if read_json(work / "result.json") != record["result"]:
        raise ArenaError(f"Stored result was modified: {work}")
    experiment = read_json(root / "experiment.json")
    provenance = read_json(work / "provenance.json")
    strategies = {s["id"]: s for s in experiment["manifest"]["strategies"]}
    expected = [strategies[s]["submission"] for s in record["match"]["sides"]]
    scenario = make_scenario(experiment["manifest"]["scenario"],
                             [s["entrypoint"] for s in expected], record["match"]["seed"], [s.get("team") for s in expected])
    engines = [experiment['engine']]
    for archive in sorted((root / 'history').glob('*.json')):
        prior = read_json(archive)
        if prior.get('sha256') != digest({k:v for k,v in prior.items() if k != 'sha256'}):
            raise ArenaError('Tournament history was modified')
        engines.append(prior['engine'])
    if (provenance["engine"] not in engines or provenance["submissions"] != expected or
            provenance["scenario_sha256"] != digest(scenario) or read_json(work / "scenario.json") != scenario):
        raise ArenaError("Stored match provenance or scenario was modified")
    for side, info in enumerate(expected, 1):
        if submission(work / "strategies" / str(side), info["entrypoint"]) != info:
            raise ArenaError("Stored match source was modified")


def run_tournament(engine: Engine, manifest: dict, out: Path, resume: bool = False, *, allow_extend=False) -> dict:
    with file_lock(out.parent / ("." + out.name + ".lock")):
        return _run_tournament(engine, manifest, out, resume, allow_extend=allow_extend)


def _run_tournament(engine: Engine, manifest: dict, out: Path, resume: bool = False, *, allow_extend=False) -> dict:
    matches = schedule(manifest)
    # Absolute source locations are metadata, not part of the experiment identity.
    frozen = {**manifest, "strategies": [{k: v for k, v in s.items() if k != "path"} for s in manifest["strategies"]]}
    provenance = {"schema_version": 1, "manifest": frozen, "engine": engine.identity,
                  "timeout_seconds": engine.timeout, "schedule": matches}
    identity = digest(provenance)
    if out.exists():
        if not resume or not (out / "experiment.json").exists():
            raise ArenaError("Output already exists; use --resume for the same experiment or a new output path")
        old = read_json(out / "experiment.json")
        if old != {**provenance, "sha256": identity}:
            old_rows = {s['id']:s for s in old['manifest']['strategies']}
            new_rows = {s['id']:s for s in frozen['strategies']}
            old_base = {**old, 'manifest':{k:v for k,v in old['manifest'].items() if k != 'strategies'}}
            new_base = {**provenance, 'manifest':{k:v for k,v in frozen.items() if k != 'strategies'}}
            for value in (old_base,new_base):
                value.pop('sha256',None);value.pop('schedule',None)
            from .recovery import engine_compatible
            updated = bool(getattr(engine, 'allow_updated_runner', False) and engine_compatible(old['engine'], engine.identity))
            if updated:
                old_base['engine'] = new_base['engine']
            extending = allow_extend and old_rows.keys() < new_rows.keys()
            if ((not extending and not (updated and old_rows == new_rows)) or old_base != new_base
                    or any(new_rows[key] != row for key,row in old_rows.items())
                    or old.get('sha256') != digest({k:v for k,v in old.items() if k != 'sha256'})
                    or any(match not in matches for match in old['schedule'])):
                raise ArenaError("Cannot resume: configuration, sources, engine or timeout changed")
            # Retain the original schedule/provenance before admitting newly
            # recovered entrants. Existing sources and completed matches stay put.
            archive = out / 'history' / (old['sha256'] + '.json')
            if archive.exists() and read_json(archive) != old:
                raise ArenaError('Tournament history was modified')
            write_json(archive,old)
            write_json(out / 'experiment.json',{**provenance,'sha256':identity})
    else:
        if resume:
            raise ArenaError("Cannot resume an experiment that does not exist")
        out.mkdir(parents=True)
        write_json(out / "experiment.json", {**provenance, "sha256": identity})
    strategies = {s["id"]: s for s in manifest["strategies"]}
    for name, s in strategies.items():
        target = out / "submissions" / name
        if target.exists():
            if submission(target, s["submission"]["entrypoint"]) != s["submission"]:
                raise ArenaError(f"Archived submission changed: {name}")
        else:
            copy_submission(Path(s["path"]), target, s["submission"])
    from .roster import snapshot
    roster = snapshot(out.parent)
    withdrawn = set((roster or {}).get('withdrawn', []))
    excluded = {s['id'] for s in manifest['strategies'] if s.get('model', s['id']) in withdrawn}
    for index, match in enumerate(matches, 1):
        record_path = out / "records" / f"{match['id']}.json"
        if record_path.exists():
            record = read_json(record_path)
            if record["match"] != match:
                raise ArenaError("Stored match metadata mismatch")
            if record["result"]["status"] == "completed":
                verify_record(out, record)
                print(f"[{index}/{len(matches)}] cached {match['sides']}, seed {match['seed']}", flush=True)
                continue
        if any(side in excluded for side in match['sides']):
            continue
        base = out / "matches" / match["id"]
        attempt = 1
        while (base / f"attempt-{attempt}").exists():
            attempt += 1
        work = base / f"attempt-{attempt}"
        sides = match["sides"]
        print(f"[{index}/{len(matches)}] {sides[0]} vs {sides[1]}, seed {match['seed']}", flush=True)
        from .activity import operation
        with operation(out.parent,'tournament_fight',participants=sides,
                       generation=max(strategies[s].get('generation',0) for s in sides),seed=match['seed']):
            result = engine.fight([out / "submissions" / s for s in sides],
                                  [strategies[s]["submission"] for s in sides], manifest["scenario"], match["seed"], work)
        write_json(record_path, {"match": match, "directory": work.relative_to(out).as_posix(), "result": result})
        report(out)
    return report(out)


def report(out: Path) -> dict:
    experiment = read_json(out / "experiment.json")
    ids = [s["id"] for s in experiment["manifest"]["strategies"]]
    rows = {s: {"id": s, "played": 0, "wins": 0, "draws": 0, "losses": 0,
                "failures": 0, "operations": 0, "errors": 0, "operation_limit_hits": 0} for s in ids}
    matrix = {a: {b: {"points": 0, "played": 0} for b in ids if a != b} for a in ids}
    mirrors = []
    from .roster import snapshot
    roster = snapshot(out.parent)
    withdrawn = set((roster or {}).get('withdrawn', []))
    excluded = {s['id'] for s in experiment['manifest']['strategies'] if s.get('model', s['id']) in withdrawn}
    missing = failed = completed = cancelled = 0
    for match in experiment["schedule"]:
        path = out / "records" / f"{match['id']}.json"
        if any(side in excluded for side in match['sides']) and (not path.exists() or read_json(path)['result']['status'] != 'completed'):
            cancelled += 1
            continue
        if not path.exists():
            missing += 1
            continue
        record = read_json(path)
        if record["match"] != match:
            raise ArenaError(f"Stored match metadata mismatch: {path}")
        verify_record(out, record)
        r = record["result"]
        sides = match["sides"]
        if r["status"] != "completed":
            failed += 1
            if not match["mirror"]:
                for s in sides:
                    rows[s]["failures"] += 1
            continue
        completed += 1
        if match["mirror"]:
            mirrors.append({"strategy": sides[0], "seed": match["seed"], "winner_side": r["winner_side"], "turns": r["turns"]})
            continue
        for side, s in enumerate(sides):
            row = rows[s]
            row["played"] += 1
            kind = "draws" if r["winner_side"] == -1 else "wins" if r["winner_side"] == side else "losses"
            row[kind] += 1
            for key in ("operations", "errors", "operation_limit_hits"):
                row[key] += r["team_metrics"][str(side)][key]
            cell = matrix[s][sides[1 - side]]
            cell["played"] += 1
            cell["points"] += {"wins": 1, "draws": 0.5, "losses": 0}[kind]
    for row in rows.values():
        row["score"] = (row["wins"] + row["draws"] * 0.5) / row["played"] if row["played"] else None
    standings = sorted(rows.values(), key=lambda r: (-(r["score"] if r["score"] is not None else -1), r["id"]))
    result = {"completed": completed, "failed": failed, "pending": missing, "cancelled":cancelled,
              "withdrawn_strategies":sorted(excluded),
              "standings": standings, "matrix": matrix, "mirrors": mirrors}
    write_json(out / "report.json", result)
    lines = [f"# {experiment['manifest'].get('name', 'Tournament')}", "",
             f"Completed: {completed} · Failed: {failed} · Pending: {missing}", "",
             "Mirrors are excluded. Process failures are unscored; runtime AI errors retain the game result.", "",
             "| Strategy | Played | W | D | L | Score | Operations | Errors | Ops limit hits | Failures |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in standings:
        score = f"{r['score']:.1%}" if r["score"] is not None else "N/A"
        lines.append(f"| {r['id']} | {r['played']} | {r['wins']} | {r['draws']} | {r['losses']} | {score} | {r['operations']} | {r['errors']} | {r['operation_limit_hits']} | {r['failures']} |")
    lines += ["", "## Head-to-head score", "", "| Strategy | " + " | ".join(ids) + " |", "|---|" + "---:|" * len(ids)]
    for a in ids:
        cells = []
        for b in ids:
            cell = matrix[a].get(b)
            cells.append(f"{cell['points'] / cell['played']:.1%} ({cell['played']})" if cell and cell["played"] else "N/A")
        lines.append("| " + a + " | " + " | ".join(cells) + " |")
    lines += ["", f"Mirror diagnostics: {len(mirrors)} (details in report.json).", "",
              "These are strategy-level descriptive scores; model-level inference requires independent generation replicates."]
    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return result
