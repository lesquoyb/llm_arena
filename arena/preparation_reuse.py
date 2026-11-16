"""Freeze completed preparations for a new set of fights."""
from pathlib import Path
import shutil

from .core import ArenaError, copy_submission, file_hash, is_link, read_json, write_json


def model_ids(config):
    return set((config.get('reuse_preparations') or {}).get('models', ()))


def validate(config):
    reuse = config['reuse_preparations']
    if (not isinstance(reuse, dict) or set(reuse) != {'source', 'models'}
            or not isinstance(reuse['source'], str) or not reuse['source']
            or not isinstance(reuse['models'], list) or not reuse['models']
            or any(not isinstance(id_, str) for id_ in reuse['models'])
            or len(model_ids(config)) != len(reuse['models'])
            or model_ids(config) - {model['id'] for model in config['models'] if model['provider'] != 'mock'}):
        raise ArenaError('Choose a source competition and distinct API participants to reuse')
    if config.get('evolutionary') or config.get('generations', 1) is None:
        raise ArenaError('Reusing preparations requires a standard competition with a fixed number of rounds')


def slots(config, generation):
    for model in sorted(model_ids(config) - set(config.get('_withdrawn_models', ()))):
        for repetition in range(config['replicates']):
            root = f'{model}-r{repetition}'
            if generation == 0:
                yield root, model, repetition, 'initial'
            else:
                for track in config.get('improvement_conditions', ['control', 'feedback']):
                    yield f'{root}-g{generation}-{track}', model, repetition, track


def _archive(source, target, reference):
    artifact = Path(reference['artifact'])
    if len(artifact.parts) != 2 or artifact.parts[0] != 'artifacts' or artifact.suffix != '.json':
        raise ArenaError('Invalid reused conversation archive path')
    path, destination = source / artifact, target / artifact
    if is_link(path) or is_link(path.parent) or file_hash(path) != reference['sha256']:
        raise ArenaError('A reused conversation archive changed')
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists():
        shutil.copyfile(path, destination)
    if file_hash(destination) != reference['sha256']:
        raise ArenaError('A reused conversation archive changed during copying')


def stage(config, source, target, states, receipts, loads):
    from .usage import amount

    def settled(state):
        return (state.get('status') in {'submitted', 'budget_exhausted'} and state.get('submission')
                and not state.get('in_flight') and amount(state.get('money_reserved', '0')) == 0)

    source_id = config['reuse_preparations']['source']
    entries = {}
    for generation in range(config.get('generations', 1)):
        for sid, model, repetition, track in slots(config, generation):
            brief = states.get(sid, {})
            if not settled(brief):
                raise ArenaError(f'{source_id} has no settled submission for {sid}. Rerun that participant instead.')
            state = loads(sid)
            if (not settled(state) or state['submission'] != brief['submission']
                    or [state.get(key) for key in ('model','replicate','generation','condition')] != [model,repetition,generation,track]):
                raise ArenaError(f'The source checkpoint does not match {sid}')
            state['completed_calls'] = brief.get('completed_calls', state.get('calls', 0))
            state['reused_from'] = {'run':source_id, 'session':sid}
            state['reused_usage'] = receipts.get(sid)
            state.pop('assessment_sha256', None)
            state.pop('validity', None)
            for message in state.get('history', []):
                if message.get('response_artifact'):
                    _archive(source, target, message['response_artifact'])
            directory = target / 'sessions' / sid
            copy_submission(source / 'sessions' / sid / 'submission', directory / 'submission', state['submission'])
            entries[sid] = write_json(directory / 'checkpoint.json', state, return_sha256=True)
    write_json(target / 'manifest.json', {'reuse':config['reuse_preparations'], 'sessions':entries})


def restore_generation(config, out, journal, generation):
    if not model_ids(config):
        return
    snapshot = out / 'reused-preparations'
    entries = read_json(snapshot / 'manifest.json')['sessions']
    existing = journal.metadata()
    for sid, *_ in slots(config, generation):
        if sid in existing:
            if not existing[sid].get('reused_from'):
                raise ArenaError(f'Expected a reused checkpoint for {sid}')
            continue
        source = snapshot / 'sessions' / sid
        checkpoint = source / 'checkpoint.json'
        if sid not in entries or file_hash(checkpoint) != entries[sid]:
            raise ArenaError(f'Reused checkpoint changed: {sid}')
        state = read_json(checkpoint)
        for message in state.get('history', []):
            if message.get('response_artifact'):
                _archive(snapshot, out, message['response_artifact'])
        copy_submission(source / 'submission', out / 'sessions' / sid / 'submission', state['submission'])
        journal.save(sid, state, 'preparation_reused', state['reused_from'])
