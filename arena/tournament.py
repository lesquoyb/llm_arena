from __future__ import annotations

import itertools
import time
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


def verification_context(root, experiment=None):
    experiment=experiment or read_json(root/'experiment.json')
    engines=[experiment['engine']]
    for archive in sorted((root/'history').glob('*.json')):
        prior=read_json(archive)
        if prior.get('sha256')!=digest({k:v for k,v in prior.items() if k!='sha256'}):
            raise ArenaError('Tournament history was modified')
        engines.append(prior['engine'])
    return {'experiment':experiment,'engines':engines,
            'strategies':{s['id']:s for s in experiment['manifest']['strategies']}}


def verify_record(root: Path, record: dict, *, context=None):
    if record['result']['status']!='completed':return
    context=context or verification_context(root)
    work=root/record['directory']
    if file_hash(work/'outcome.json')!=record['result']['outcome_sha256']:
        raise ArenaError(f'Stored outcome was modified: {work}')
    if read_json(work/'result.json')!=record['result']:
        raise ArenaError(f'Stored result was modified: {work}')
    provenance=read_json(work/'provenance.json')
    expected=[context['strategies'][s]['submission'] for s in record['match']['sides']]
    scenario=make_scenario(context['experiment']['manifest']['scenario'],
        [s['entrypoint'] for s in expected],record['match']['seed'],[s.get('team') for s in expected])
    if (provenance['engine'] not in context['engines'] or provenance['submissions']!=expected or
            provenance['scenario_sha256']!=digest(scenario) or read_json(work/'scenario.json')!=scenario):
        raise ArenaError('Stored match provenance or scenario was modified')
    for side,info in enumerate(expected,1):
        if submission(work/'strategies'/str(side),info['entrypoint'])!=info:
            raise ArenaError('Stored match source was modified')


def scoring_record(record):
    result=record['result']
    slim={key:result[key] for key in ('status','winner_side','turns') if key in result}
    if result.get('team_metrics') is not None:
        slim['team_metrics']={side:{key:metrics[key] for key in ('operations','errors','operation_limit_hits')}
                              for side,metrics in result['team_metrics'].items()}
    return {'match':record['match'],'result':slim}


def run_tournament(engine: Engine, manifest: dict, out: Path, resume: bool = False, *, allow_extend=False, priority_ids=None, reference_ids=None, parallel_fights=1) -> dict:
    with file_lock(out.parent / ("." + out.name + ".lock")):
        return _run_tournament(engine, manifest, out, resume, allow_extend=allow_extend, priority_ids=priority_ids, reference_ids=reference_ids, parallel_fights=parallel_fights)


def _run_tournament(engine: Engine, manifest: dict, out: Path, resume: bool = False, *, allow_extend=False, priority_ids=None, reference_ids=None, parallel_fights=1) -> dict:
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
    priority_ids=set(priority_ids or [])
    reference_ids=set(reference_ids or [])
    execution=sorted(matches,key=lambda match:-sum(side in priority_ids for side in match['sides']))
    from .activity import operation, poll_provider_failures, provider_work_ready
    verification=verification_context(out)
    known={};completed=set()
    def deferred():
        value=read_json(out/'report.json') if (out/'report.json').exists() else {'completed':0,'failed':0,'pending':len(matches)}
        return {**value,'deferred':True}
    audit_started=time.time();last_audit=0
    with operation(out.parent,'checking_fights',generation=max((s.get('generation',0) for s in strategies.values()),default=0)):
        for index,match in enumerate(execution,1):
            poll_provider_failures()
            if provider_work_ready():return deferred()
            path=out/'records'/f"{match['id']}.json"
            if path.exists():
                record=read_json(path)
                if record['match']!=match:raise ArenaError('Stored match metadata mismatch')
                verify_record(out,record,context=verification)
                known[match['id']]=scoring_record(record)
                if record['result']['status']=='completed':
                    completed.add(match['id'])
                    if all(side in reference_ids for side in match['sides']):
                        from .reference_cache import seed as seed_reference
                        seed_reference(engine,[strategies[side]['submission'] for side in match['sides']],manifest['scenario'],match['seed'],out/record['directory'])
            if time.monotonic()-last_audit>=.5:
                write_json(out.parent/'activity.json',{'kind':'checking_fights','started_at':audit_started,
                    'generation':max((s.get('generation',0) for s in strategies.values()),default=0),
                    'checked_records':index,'total_records':len(matches)})
                last_audit=time.monotonic()
    def jobs():
        for index,match in enumerate(execution,1):
            poll_provider_failures()
            if match['id'] in completed or any(side in excluded for side in match['sides']):continue
            base=out/'matches'/match['id'];attempt=1
            while (base/f'attempt-{attempt}').exists():attempt+=1
            print(f"[{index}/{len(matches)}] {match['sides'][0]} vs {match['sides'][1]}, seed {match['seed']}",flush=True)
            yield {'match':match,'work':base/f'attempt-{attempt}','record_path':out/'records'/f"{match['id']}.json",
                   'participants':match['sides'],'seed':match['seed']}
    def record_for(job,result):
        return {'match':job['match'],'directory':job['work'].relative_to(out).as_posix(),'result':result}
    def execute(job):
        from .reference_cache import fight as cached_reference_fight
        sides=job['participants']
        fight=cached_reference_fight if all(side in reference_ids for side in sides) else lambda engine,*args:engine.fight(*args)
        result=fight(engine,[out/'submissions'/side for side in sides],
                     [strategies[side]['submission'] for side in sides],manifest['scenario'],job['seed'],job['work'])
        job['phase']='verifying_result'
        verify_record(out,record_for(job,result),context=verification)
        return result
    last_report=0
    def publish(markdown=False):
        return report(out,verified_records=known,experiment=verification['experiment'],markdown=markdown)
    def save(job,result):
        nonlocal last_report
        record=record_for(job,result)
        write_json(job['record_path'],record)
        known[job['match']['id']]=scoring_record(record)
        if time.monotonic()-last_report>=.5:
            publish();last_report=time.monotonic()
    publish()
    from .fight_pool import run as run_fights
    run_fights(jobs(),execute,save,limit=parallel_fights,out=out.parent,kind='tournament_fight',
               generation=max((s.get('generation',0) for s in strategies.values()),default=0))
    return publish(markdown=True)


def report(out: Path, *, verified_records=None, experiment=None, markdown=True) -> dict:
    experiment = experiment or read_json(out / "experiment.json")
    verification=verification_context(out,experiment) if verified_records is None else None
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
        if verified_records is None:
            path=out/'records'/f"{match['id']}.json"
            record=read_json(path) if path.exists() else None
        else:record=verified_records.get(match['id'])
        if any(side in excluded for side in match['sides']) and (record is None or record['result']['status']!='completed'):
            cancelled+=1;continue
        if record is None:missing+=1;continue
        if record['match']!=match:raise ArenaError('Stored match metadata mismatch')
        if verified_records is None:verify_record(out,record,context=verification)
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
    if not markdown:return result
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
