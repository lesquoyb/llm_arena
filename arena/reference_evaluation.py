"""Optional, unranked fights against versioned reference scripts."""
from contextlib import closing

from .core import ArenaError, digest, read_json


SETTINGS = 'reference-evaluation.json'


def settings(root):
    path = root / SETTINGS
    return read_json(path) if path.is_file() else {}


def reference_model(model):
    return (model.get('provider') == 'mock' and model.get('profile') == 'saved-strategy'
            and bool((model['strategy'].get('origin') or {}).get('reference')))


def opponent_id(model):
    info = model['strategy']['submission']
    version = digest((info['sha256'], info['entrypoint']))[:12]
    return f"{model['id']}@{version}"


def ranking_exclusions(root):
    return set(settings(root).get('excluded', []))


def hidden_from_results(stage, kind, sides, states, policy):
    if kind != 'training':
        excluded = policy.get('excluded', ())
        if any(states.get(sid, {}).get('model', sid) in excluded for sid in sides):
            return True
    if stage.startswith('evaluations/') and stage.endswith('-references-panel'):
        enabled = {opponent_id(model) for model in policy.get('models', [])}
        return all(sid not in enabled for sid in sides)
    return False


def refresh_standings(root):
    """Update generated score reports after changing exclusions."""
    from .core import write_json
    from .fight_store import stage_records
    from .tournament import report

    updated = {}
    for stage in (root/'tournament', *sorted(root.glob('g*-tournament'))):
        if not (stage/'report.json').is_file():
            continue
        records = {key: record for key, (_, record) in stage_records(stage)[1].items()}
        updated[stage.name] = report(stage, verified_records=records)
    if updated and (root/'report.json').is_file():
        summary = read_json(root/'report.json')
        if 'tournament' in updated:
            summary['tournament'] = updated['tournament']
        latest = f"g{summary.get('generation', 0)}-tournament"
        contemporary = (summary.get('evolution') or {}).get('contemporaries')
        if latest in updated and contemporary is not None:
            for key in ('standings', 'matrix'):
                contemporary[key] = updated[latest][key]
        write_json(root/'report.json', summary)


def run(root):
    from .engine import Engine
    from .evolution import references
    from .experiment import Journal, experiment_lock
    from .execution_control import poll
    from .recovery import engine_compatible
    from .reference_strategies import for_scenario
    from .roster import effective, snapshot
    from .scenario_rules import scenario_for
    from .core import scratch_directory, verify_source_files

    with experiment_lock(root):
        metadata = read_json(root / 'experiment.json')
        policy = settings(root)
        engine = Engine()
        if not engine_compatible(metadata['engine'], engine.identity):
            raise ArenaError('Restore the original engine before evaluating references')
        engine.allow_updated_runner = True
        config = effective(root, metadata['config'])
        roster = snapshot(root) or {}
        config['_scenario_changes'] = roster.get('scenario_changes', [])
        config['_parallel_fights'] = poll(root, roster.get('parallel_fights', config.get('parallel_fights', 1)))
        participants = {model['id']: model for model in config['models']}
        journal = Journal(root)
        failed = 0
        with closing(journal.db), scratch_directory() as scratch:
            states = journal.states()
            for generation in policy.get('rounds', []):
                entrants = []
                for sid, state in states.items():
                    if (state.get('generation', 0) != generation or not state.get('submission')
                            or state.get('validity') == 'invalid'
                            or participants[state['model']]['provider'] == 'mock'):
                        continue
                    source = root / 'sessions' / sid / 'submission'
                    verify_source_files(source, state['submission'])
                    entrants.append({'id': sid, 'model': state['model'], 'path': source,
                                     'generation': generation, 'submission': state['submission']})
                panel = []
                for model in policy.get('models', []):
                    sid = opponent_id(model)
                    strategy = for_scenario(model, scenario_for(config, generation))['strategy']
                    source = scratch / str(generation) / sid
                    for name, content in strategy['files'].items():
                        file = source / name
                        file.parent.mkdir(parents=True, exist_ok=True)
                        file.write_bytes(content.encode('utf-8'))
                    verify_source_files(source, strategy['submission'])
                    panel.append({'id': sid, 'path': source, 'submission': strategy['submission']})
                if entrants and panel:
                    results = references(engine, config, root, journal, entrants,
                                         f'g{generation}-references-panel', panel)
                    failed += sum(row['result']['status'] != 'completed' for row in results.values())
        return failed
