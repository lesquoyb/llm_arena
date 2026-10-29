"""Audited participant changes without replacing an experiment or its sources."""
import copy
import json
import sqlite3
from contextlib import closing
from .core import ArenaError, file_hash, read_json


def snapshot(out):
    path = out / 'journal.sqlite'
    if not path.exists(): return None
    with closing(sqlite3.connect(path.as_uri()+'?mode=ro', uri=True)) as db:
        if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='events'").fetchone():return None
        row = db.execute("SELECT payload FROM events WHERE kind='participants_updated' ORDER BY id DESC LIMIT 1").fetchone()
    if not row: return None
    reference = json.loads(row[0])
    path = (out / reference['artifact']).resolve()
    if not path.is_relative_to(out.resolve()):raise ArenaError('Invalid participant change artifact path')
    if file_hash(path) != reference['sha256']: raise ArenaError('Participant change journal was modified')
    return read_json(path)


def effective(out, config):
    result = copy.deepcopy(config)
    roster = snapshot(out)
    if roster: result['models'] = roster['models']
    return result


def active(config, state):
    identifier = state.get('id') if 'provider' in state else state.get('model', state.get('id'))
    return identifier not in config.get('_withdrawn_models', [])


def validate_effective(config, withdrawn):
    from .experiment import validate_config
    models=config['models']
    # The active pool retains its normal bound; archived participants do not
    # consume slots when a replacement is added.
    def check(selected):
        spending=config['spending']
        if selected and all(model['provider']=='mock' for model in selected):
            spending={'allow_paid_calls':False,'max_total_usd':0}
        validate_config({**config,'models':selected,'spending':spending})
    check([model for model in models if model['id'] not in withdrawn])
    for start in range(0,len(models),20):
        check(models[start:start+20])
    return config


def update(out, journal, original, catalog, selected, frozen_tracks=None, compare_previous_round=None, parallel_fights=None, request_order=None, parallel_requests=None):
    if not isinstance(selected, list) or not selected or any(not isinstance(value,str) for value in selected) or len(set(selected)) != len(selected):
        raise ArenaError('Select at least one participant, without duplicates')
    previous = snapshot(out)
    models = copy.deepcopy(previous['models'] if previous else original['models'])
    known = {model['id']:model for model in models}
    old_active = set(known)-set(previous['withdrawn'] if previous else [])
    profiles = {model['id']:model for model in catalog}
    for identifier in selected:
        if identifier not in known:
            if identifier not in profiles: raise ArenaError('Unknown participant: '+identifier)
            from .reference_strategies import for_scenario
            model = for_scenario(profiles[identifier],original['scenario']); models.append(model); known[identifier]=model
    withdrawn = sorted(set(known)-set(selected))
    validate_effective({**original,'models':models},withdrawn)
    states = journal.states()
    if not states: raise ArenaError('The competition has no checkpoint yet')
    frozen_tracks = (previous or {}).get('frozen_tracks', {}) if frozen_tracks is None else frozen_tracks
    if not isinstance(frozen_tracks,dict) or set(frozen_tracks)-set(known):
        raise ArenaError('Unknown participant in frozen tracks')
    for model, tracks in frozen_tracks.items():
        if not isinstance(tracks,list) or any(not isinstance(track,str) or track not in {'control','feedback'} for track in tracks) or len(set(tracks))!=len(tracks):
            raise ArenaError('Freeze tracks must be control or feedback')
        if tracks and not any(state['model']==model and state.get('submission') for state in states.values()):
            raise ArenaError('A participant needs a submitted strategy before it can be frozen: '+model)
        if tracks and any(state['model']==model and state.get('condition') in tracks and
                          (state.get('in_flight') or state.get('status')=='needs_reconciliation') for state in states.values()):
            raise ArenaError('Resolve the interrupted request before freezing this track: '+model)
    if compare_previous_round is None:compare_previous_round=(previous or {}).get('compare_previous_round',original.get('compare_previous_round',False))
    if type(compare_previous_round) is not bool:raise ArenaError('Previous-round comparison must be boolean')
    if parallel_fights is None:parallel_fights=(previous or {}).get('parallel_fights',original.get('parallel_fights',1))
    from .core import integer
    integer(parallel_fights,1,None,'parallel_fights')
    if request_order is None:request_order=(previous or {}).get('request_order',original.get('request_order','models'))
    if request_order not in ('models','repetitions'):raise ArenaError('Request order must be models or repetitions')
    if parallel_requests is None:parallel_requests=(previous or {}).get('parallel_requests',original.get('parallel_requests',1))
    integer(parallel_requests,1,20,'parallel_requests')
    change = {'parallel_requests':parallel_requests,'request_order':request_order,'parallel_fights':parallel_fights,'compare_previous_round':compare_previous_round, 'frozen_tracks':frozen_tracks, 'revision':(previous or {}).get('revision',0)+1, 'models':models,
              'active':selected, 'withdrawn':withdrawn,
              'added':sorted(set(selected)-old_active), 'removed':sorted(old_active-set(selected)),
              'at_round':max(state.get('generation',0) for state in states.values())+1,
              'policy':'Keep completed fights and sources; cancel unplayed fights involving withdrawn participants. New entrants prepare missing rounds; existing submissions remain frozen.'}
    # One immutable event is the authority. Withdrawal is derived from it, so a
    # crash cannot leave a partially updated set of participant checkpoints.
    sid = next(iter(states))
    journal.save(sid, states[sid], 'participants_updated', change)
    return change
