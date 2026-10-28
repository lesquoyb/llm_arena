"""Paired G1 branches and shared reference evaluation; opponents stay private."""
from __future__ import annotations
import copy
from pathlib import Path
from .core import ROOT, ArenaError, copy_submission, digest, make_scenario, read_json, submission, write_json
from .preparation import Preparation


def feedback_for(sid, tournament):
    from .feedback import PastFights
    return PastFights(tournament.parent, sid).summary()


def references(engine, config, out, journal, entrants, label, panel, *, incremental=False):
    """Both positions, identical reference opponents and final seeds for each branch."""
    root = out / "evaluations" / label
    root.mkdir(parents=True, exist_ok=True)
    results = read_json(root / 'results.json') if incremental and (root / 'results.json').exists() else {}
    for entrant in entrants:
        for opponent in panel:
            for seed in config["final_seeds"]:
                for side in (0, 1):
                    sources = [entrant, opponent] if side == 0 else [opponent, entrant]
                    key = digest({"entrant": entrant["id"], "opponent": opponent["id"], "seed": seed, "side": side})[:24]
                    cached = root / "records" / (key + ".json")
                    if cached.exists():
                        record = read_json(cached)
                        work = out / record["artifact_dir"]
                        from .core import file_hash
                        if record["result"]["status"] == "completed":
                            if file_hash(work / "outcome.json") != record["result"]["outcome_sha256"]:
                                raise ArenaError("Reference outcome changed")
                            if read_json(work / "result.json") != record["result"]:
                                raise ArenaError("Reference result changed")
                            scenario = make_scenario(config["scenario"], [s["submission"]["entrypoint"] for s in sources], seed, [s["submission"].get("team") for s in sources])
                            provenance = read_json(work / "provenance.json")
                            from .recovery import engine_compatible
                            accepted_engine = provenance['engine'] == engine.identity or (
                                getattr(engine, 'allow_updated_runner', False) and engine_compatible(provenance['engine'], engine.identity))
                            if (read_json(work / "scenario.json") != scenario or not accepted_engine
                                    or provenance["submissions"] != [s["submission"] for s in sources]):
                                raise ArenaError("Reference provenance changed")
                            for index, source in enumerate(sources, 1):
                                if submission(work / "strategies" / str(index), source["submission"]["entrypoint"]) != source["submission"]:
                                    raise ArenaError("Reference source changed")
                        else:
                            cached = None
                    if not cached or not cached.exists():
                        work = Preparation._attempt(root / "matches" / key)
                        from .activity import operation
                        with operation(out,'reference_fight',participants=[s['id'] for s in sources],
                                       generation=entrant.get('generation',0),seed=seed):
                            result = engine.fight([Path(s["path"]) for s in sources], [s["submission"] for s in sources],
                                                  config["scenario"], seed, work)
                        record = {"session": entrant["id"], "opponent": opponent["id"], "seed": seed,
                                  "side": side, "result": result, "artifact_dir": work.relative_to(out).as_posix()}
                        write_json(root / "records" / (key + ".json"), record)
                        journal.save(entrant["id"], journal.state(entrant["id"]), "reference_match", record)
                    results[key] = record
    write_json(root / "results.json", results)
    return results


def run_generation(config, out, journal, engine, initial, interrupt=None, retry_session=None, allow_extend=False, generation=1, roots=None):
    from .experiment import run_session, PROMPT, initial_state
    from .analysis import analyze_evolution
    from .roster import active
    models = {m["id"]: m for m in config["models"]}
    initial_states = {s["id"]: journal.state(s["id"]) for s in initial}
    branches = []
    roots = roots if roots is not None else initial
    panel = [dict(s, path=s["path"]) for s in roots]
    for name in ("rush", "single-shot", "passive"):
        source = ROOT / "examples/strategies" / name
        target = out / "controls" / name
        info = submission(source)
        if not target.exists():
            copy_submission(source, target, info)
        elif submission(target) != info:
            raise ArenaError("Frozen control changed")
        panel.append({"id": "fixed-" + name, "path": target, "submission": info})
    from .greedy import evaluate as evaluate_ready, entrants as ready_entrants
    evaluated = set()
    baseline = references(engine, config, out, journal, roots, "g0-panel", panel)
    def evaluate_available():
        evaluate_ready(engine, config, out, journal, generation)
        for entrant in ready_entrants(journal, out, generation):
            if not active(config,entrant): continue
            if entrant['id'] not in evaluated:
                references(engine, config, out, journal, [entrant], f'g{generation}-panel', panel, incremental=True)
                evaluated.add(entrant['id'])
    evaluate_available()
    tasks=[];candidates=[]
    for parent in initial:
        parent_state = initial_states[parent["id"]]
        if parent_state["status"] == "needs_reconciliation":
            continue
        for condition in config["improvement_conditions"]:
            if generation > 1 and condition != parent_state.get('condition'): continue
            root = parent_state.get('lineage_root', parent['id'])
            sid = root + f"-g{generation}-" + condition
            permitted = not retry_session or sid == retry_session or parent['id'] == retry_session or root == retry_session
            ancestor = parent['id']
            while retry_session and not permitted and ancestor:
                permitted = ancestor == retry_session
                ancestor = (journal.state(ancestor) or {}).get('parent')
            existing = journal.state(sid)
            if existing is None or existing.get('retry_parent_refresh'):
                if not permitted:
                    continue
                state = copy.deepcopy(parent_state)
                state.update(generation=generation, condition=condition, parent=parent["id"], lineage_root=root, participant_revision=config.get('_roster_revision',0),
                             parent_checkpoint_sha256=digest(parent_state), status="running",
                             calls=0, completed_calls=0, steps=0, test_matches=0, wall_seconds=0, pending=None, cursor=0,
                             in_flight=False, money_reserved="0", reservation_unbounded=False, cost_spent="0", input_tokens=0, output_tokens=0, diagnostic_calls=0, diagnostic_cost_usd="0")
                state['history'] = initial_state(sid, models[parent_state['model']], config)['history']
                state['message_times'] = []
                state['history_policy'] = 'fresh-round'
                state.pop('request_history_start', None)
                state.pop('context_recoveries', None)
                state["token_usage_known"] = False
                state["missing_usage_calls"] = 0
                state.pop("submission", None)
                state.pop("reserved", None)
                state.pop("assessment_sha256", None)
                state.pop("validity", None)
                state.pop("failure", None)
                state.pop("retry_parent_refresh", None)
                state.pop("retry_count", None)
                state.pop('manual_frozen', None)
                state.pop("submission_reminders", None)
                prompt_path = ROOT / "prompts" / ("feedback.md" if condition == "feedback" else "control.md")
                message = state['history'][0]
                from .round_context import phase, source_context, progress_line
                from .submitted_versions import OwnSubmissions
                versions = OwnSubmissions(out, state).versions()
                message['previous_submission'] = source_context(versions[-1])
                message.update(generation=generation,condition=condition,
                    content=phase(generation+1, config.get('generations', 2)) + f" {generation} competition rounds have elapsed.\n"
                        + prompt_path.read_text(encoding='utf-8') + '\nPreparation rules:\n' + PROMPT)
                if condition == "feedback":
                    counts = feedback_for(parent["id"], out / "tournament")
                    state["previous_round_feedback"] = counts
                    message["content"] += ("\nUse list_past_fights to choose a fight, then read_past_fight to inspect its overview, actions, "
                                           f"your per-turn metrics or your debug/error logs. The default is Round {generation}; pass round to list_past_fights for an earlier round of this track.\n")
                    message['content'] += 'Performance across your own earlier rounds in this track:\n' + '\n'.join(
                        progress_line(v['round'], feedback_for(v['session'], out / 'tournament')) for v in versions)
                    write_json(out / "feedback" / (sid + ".json"), counts)
                copy_submission(Path(parent["path"]), out / "sessions" / sid / "workspace", parent["submission"])
                from .experiment import workspace_files
                state['workspace_files'] = workspace_files(out / 'sessions' / sid / 'workspace')
                journal.save(sid, state, "branch_created", {"parent": parent["id"],
                                                          "checkpoint_sha256": state["parent_checkpoint_sha256"],
                                                          "condition": condition})
            if condition in config.get('_frozen_tracks',{}).get(parent_state['model'], []):
                state = journal.state(sid)
                if not state.get('submission'):
                    target = out/'sessions'/sid/'submission'
                    if target.exists():
                        if submission(target,parent['submission']['entrypoint']) != parent['submission']:
                            raise ArenaError('An existing frozen source differs from the requested manual freeze')
                    else:
                        copy_submission(Path(parent['path']),target,parent['submission'])
                    for call in (state.get('pending') or {}).get('tool_calls',[])[state.get('cursor',0):]:
                        state['history'].append({'role':'tool','name':call['name'],'provider_call_id':call.get('id'),
                                                 'result':{'error':'Not executed: this track was manually frozen at its previous submitted strategy'}})
                    state.update(status='submitted',submission=parent['submission'],pending=None,cursor=0,reserved=None,
                                 manual_frozen={'from_session':parent['id'],'submission_sha256':parent['submission']['sha256'],
                                                'roster_revision':config.get('_roster_revision',0)})
                    state.pop('failure',None)
                    journal.save(sid,state,'track_frozen',state['manual_frozen'])
            if permitted:tasks.append((sid,models[parent_state['model']]))
            candidates.append(sid)
    from .parallel import prepare
    prepare(tasks,config,out,journal,engine,interrupt,evaluate_available)
    for sid in candidates:
        state = journal.state(sid)
        if "submission" in state:
            directory = out / "sessions" / sid
            cached = directory / "assessment.json"
            from .core import file_hash
            if cached.exists():
                if state.get("assessment_sha256") and file_hash(cached) != state["assessment_sha256"]:
                    raise ArenaError("G1 assessment changed")
                assessment = read_json(cached)
            else:
                from .activity import operation
                with operation(out,'validation',participants=[sid],generation=generation):
                    assessment = engine.analyze(directory / "submission", state["submission"]["entrypoint"],
                                                Preparation._attempt(directory / "assessment"))
                write_json(cached, assessment)
            state["validity"] = assessment["status"]
            state["assessment_sha256"] = file_hash(cached)
            journal.save(sid, state, "submission_assessment", assessment)
            branches.append({"id": sid, "path": out / "sessions" / sid / "submission",
                             "submission": state["submission"], "model": state["model"],
                             "replicate": state["replicate"], "parent": state["parent"], "generation": generation, "condition": state["condition"]})
    for parent_sid, parent_state in list(journal.states().items()):
        if not active(config,parent_state) or parent_state.get("generation", 0) != generation-1 or "submission" in parent_state:
            continue
        for condition in config["improvement_conditions"]:
            if generation > 1 and condition != parent_state.get('condition'): continue
            root = parent_state.get('lineage_root', parent_sid)
            sid = root + f"-g{generation}-" + condition
            if journal.state(sid) is None:
                skipped = copy.deepcopy(parent_state)
                skipped.update(parent=parent_sid, generation=generation, lineage_root=root, condition=condition, status="no_submission",
                               calls=0, completed_calls=0, steps=0, test_matches=0, cost_spent="0", money_reserved="0",
                               input_tokens=0, output_tokens=0, token_usage_known=False, missing_usage_calls=0, diagnostic_calls=0, diagnostic_cost_usd="0")
                journal.save(sid, skipped, "branch_unavailable", {"reason": "No G0 submission"})
    contemporaries = evaluate_ready(engine, config, out, journal, generation)
    evolved = references(engine, config, out, journal, branches, f"g{generation}-panel", panel)
    result = analyze_evolution(config, out, journal.states(), roots, branches, baseline, evolved, contemporaries)
    result["contemporaries"] = contemporaries
    write_json(out / "evolution.json", result)
    return result


def run_evolution(config, out, journal, engine, initial, interrupt=None, retry_session=None, allow_extend=False):
    """Two persistent improvement tracks, with a tournament barrier between rounds."""
    import itertools
    from .analysis import analyze_evolution
    from .roster import active
    previous, branches, evolved, tournaments = initial, [], {}, []
    indices = range(1, config.get('generations', 1)) if config.get('generations', 1) is not None else itertools.count(1)
    for generation in indices:
        generation_retry = retry_session if retry_session and generation <= (journal.state(retry_session) or {}).get('generation',0) else None
        result = run_generation(config, out, journal, engine, previous, interrupt, generation_retry, allow_extend, generation, initial)
        states = journal.states()
        current = [{'id':sid,'path':out/'sessions'/sid/'submission','submission':s['submission'],
                    'model':s['model'],'replicate':s['replicate'],'parent':s['parent'],
                    'condition':s['condition'],'generation':generation}
                   for sid,s in states.items() if active(config,s) and s.get('generation')==generation and 'submission' in s]
        branches.extend(current)
        evolved.update(read_json(out/'evaluations'/f'g{generation}-panel/results.json'))
        if result['contemporaries']: tournaments.append(result['contemporaries'])
        combined = dict(result['contemporaries'] or {})
        for key in ('completed','failed','pending'):
            combined[key] = sum(t.get(key,0) for t in tournaments)
        result = analyze_evolution(config,out,states,initial,branches,
            read_json(out/'evaluations/g0-panel/results.json'), evolved, combined)
        result.update(contemporaries=combined, completed_rounds=generation+1)
        write_json(out/'evolution.json',result)
        if (out/'report.json').exists():
            from .experiment import token_totals
            summary = read_json(out/'report.json')
            summary.update(evolution=result, generation=generation, sessions=len(states),
                with_submission=sum('submission' in s for s in states.values()),
                no_submission=sum('submission' not in s for s in states.values()),
                model_calls=sum(s['calls'] for s in states.values()),
                tool_calls=sum(s['steps'] for s in states.values()),
                **{key:result[key] for key in ('cost_usd','known_cost_subtotal_usd','reserved_usd','incomplete')},
                **token_totals(config,states))
            write_json(out/'report.json',summary)
        # Preserve a resumable boundary if any model needs recovery. Do not silently
        # exclude it from all future rounds or spin forever with an empty panel.
        if (not current or len(current) != 2*len(initial)
                or any(active(config,s) and s.get('generation',0)<=generation and 'submission' not in s for s in states.values())
                or any(r['failed'] for r in result['rows'])):
            break
        previous = current
    return result
