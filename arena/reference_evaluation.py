"""Optional, unranked fights against versioned reference scripts."""
import re
from contextlib import closing
from itertools import combinations, product

from .core import ArenaError, digest, read_json, write_json


SETTINGS = 'reference-evaluation.json'
EVALUATION_STAGE = re.compile(r'^evaluations/g(\d+)-references-panel$')


def settings(root):
    path = root / SETTINGS
    return read_json(path) if path.is_file() else {}


def reference_model(model):
    strategy=model.get('strategy')
    origin=strategy.get('origin') if isinstance(strategy,dict) else None
    return (model.get('provider') == 'mock' and model.get('profile') == 'saved-strategy'
            and isinstance(origin,dict) and bool(origin.get('reference')))


def initialize_automatic(root, config):
    if config.get('evaluation_references') and not (root / SETTINGS).exists():
        write_json(root / SETTINGS, {'models':config['evaluation_references'], 'automatic':True,
                                    'rounds':[], 'excluded':[]})


def evaluate_round(engine, config, root, journal, generation, policy, scratch):
    from .core import verify_source_files
    from .evolution import references
    from .greedy import entrants
    from .reference_strategies import for_scenario
    from .scenario_rules import scenario_for

    inactive = set(config.get('_withdrawn_models', ())) | set(policy.get('excluded', ()))
    states = journal.metadata()
    ready = [entry for entry in entrants(journal, root, generation)
             if entry['model'] not in inactive and states[entry['id']].get('validity') != 'invalid']
    if not ready:
        return None
    scenario = scenario_for(config, generation)
    official = {(entry['model'],entry['submission']['sha256']) for entry in ready}
    panel = []
    for model in policy.get('models', []):
        strategy = for_scenario(model, scenario)['strategy']
        if (model['id'],strategy['submission']['sha256']) in official:
            continue
        sid = opponent_id(model)
        source = scratch / sid
        for name, content in strategy['files'].items():
            file = source / name
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(content.encode('utf-8'))
        verify_source_files(source, strategy['submission'])
        panel.append({'id':sid,'path':source,'submission':strategy['submission'],
                      'generation':generation,'fixed_reference':True})
    panel.sort(key=lambda entry:entry['id'])
    pairs = [*product(ready, panel), *combinations(panel, 2)]
    if not pairs:
        return None
    seeds = config['final_seeds'] if generation else config['seeds']
    if policy.setdefault('round_seeds', {}).get(str(generation)) != seeds or generation not in policy.get('rounds', []):
        policy['round_seeds'][str(generation)] = seeds
        policy['rounds'] = sorted(set(policy.get('rounds', ())) | {generation})
        write_json(root / SETTINGS, policy)
    return references(engine, {**config,'final_seeds':seeds}, root, journal, ready,
                      f'g{generation}-references-panel', panel, pairs=pairs)


def evaluate_automatic(engine, config, root, journal, generation, *, final=False):
    from .core import scratch_directory
    from .run_memory import shared
    policy = settings(root)
    if not policy.get('automatic') or not policy.get('models'):
        return
    states = journal.metadata()
    signature = digest([policy['models'], policy.get('excluded', []), config.get('_withdrawn_models', []),
                        [(sid, row['submission']['sha256'], row.get('validity')) for sid,row in sorted(states.items())
                         if row.get('generation', 0) == generation and row.get('submission')]])
    attempted = shared(root, 'automatic_reference_evaluations')
    if attempted.get(generation) == (signature, True) or attempted.get(generation) == (signature, final):
        return
    with scratch_directory() as scratch:
        results = evaluate_round(engine, config, root, journal, generation, policy, scratch)
    attempted[generation] = (signature, final or results is None or
                             all(row['result']['status']=='completed' for row in results.values()))


def opponent_id(model):
    info = model['strategy']['submission']
    version = digest((info['sha256'], info['entrypoint']))[:12]
    return f"{model['id']}@{version}"


def ranking_exclusions(root):
    return set(settings(root).get('excluded', []))


def evaluation_id(sid):
    return bool(re.search(r'@[a-f0-9]{12}$', sid or ''))


def evaluation_seeds(policy):
    return {f'evaluations/g{generation}-references-panel': seeds
            for generation, seeds in policy.get('round_seeds', {}).items()}


def hidden_from_results(stage, kind, sides, states, policy, seed=None):
    if kind != 'training':
        excluded = policy.get('excluded', ())
        if any(states.get(sid, {}).get('model', sid) in excluded for sid in sides):
            return True
    evaluation = EVALUATION_STAGE.fullmatch(stage)
    if evaluation:
        enabled = {opponent_id(model) for model in policy.get('models', [])}
        virtual = [sid for sid in sides if evaluation_id(sid)]
        if not virtual or any(sid not in enabled for sid in virtual):
            return True
        allowed = policy.get('round_seeds', {}).get(evaluation[1])
        if seed is not None and allowed is not None and str(seed) not in {str(value) for value in allowed}:
            return True
    return False


def refresh_standings(root):
    """Update generated score reports after changing exclusions."""
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
    from .core import scratch_directory
    from .engine import Engine
    from .experiment import Journal, experiment_lock
    from .execution_control import poll
    from .recovery import engine_compatible
    from .roster import effective, snapshot

    with experiment_lock(root):
        if (root / 'export.json').exists():
            raise ArenaError('Exported archives are read-only')
        metadata = read_json(root / 'experiment.json')
        policy = settings(root)
        engine = Engine()
        if not engine_compatible(metadata['engine'], engine.identity):
            raise ArenaError('Restore the original engine before evaluating references')
        engine.allow_updated_runner = True
        config = effective(root, metadata['config'])
        roster = snapshot(root) or {}
        config['_scenario_changes'] = roster.get('scenario_changes', [])
        config['_withdrawn_models'] = roster.get('withdrawn', [])
        config['_parallel_fights'] = poll(root, roster.get('parallel_fights', config.get('parallel_fights', 1)))
        journal = Journal(root)
        failed = 0
        with closing(journal.db), scratch_directory() as scratch:
            for generation in policy.get('rounds', []):
                results = evaluate_round(engine, config, root, journal, generation, policy, scratch / str(generation))
                failed += sum(row['result']['status'] != 'completed' for row in (results or {}).values())
        return failed
