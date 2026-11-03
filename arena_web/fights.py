"""Fight overviews computed from the incremental fight index.

The browser receives aggregates (grouped counts, one filtered page of fights,
length histograms) rather than every fight of a competition.
"""
from __future__ import annotations

import re

from .performance import measure

IDENTITY = re.compile(r'^(.*)-r(\d+)(?:-g(\d+)-(control|feedback))?$')
KINDS = ('competition', 'evaluation', 'progression', 'training')


def seed_value(seed):
    if isinstance(seed, str) and seed.lstrip('-').isdigit():
        return int(seed)
    return seed
MATCH_LIMIT = 800


def identities(detail_sessions, manifest_strategies=()):
    """Same derivation as the browser's overviewIdentity()."""
    sessions = {row['id']: row for row in detail_sessions}
    origins = {row['id']: row.get('origin') or {} for row in manifest_strategies}
    cache = {}
    def identity(sid):
        if sid in cache:
            return cache[sid]
        session = sessions.get(sid) or {}
        origin = origins.get(sid) or {}
        parts = IDENTITY.match(str(sid or ''))
        generation = session.get('generation')
        if generation is None and origin.get('round') is not None:
            generation = origin['round'] - 1
        if generation is None and parts and parts.group(3):
            generation = int(parts.group(3))
        replicate = session.get('replicate', origin.get('replicate'))
        if replicate is None and parts:
            replicate = int(parts.group(2))
        value = {'id': sid,
                 'model': session.get('model') or origin.get('variant') or (parts.group(1) if parts else sid),
                 'condition': session.get('condition') or origin.get('condition') or (parts.group(4) if parts and parts.group(4) else 'initial'),
                 'generation': int(generation or 0), 'replicate': int(replicate or 0)}
        cache[sid] = value
        return value
    return identity


def _attempt_cutoffs(states):
    return {sid: state.get('attempt_started_at', 0) for sid, state in states.items()}


def previous_round(kind, candidate, opponent, models):
    if kind == 'progression':
        return True
    return (kind == 'evaluation' and candidate.get('generation') == 1 and opponent.get('generation') == 0
            and models.get(candidate.get('model'), {}).get('provider') not in {None, 'mock'}
            and models.get(opponent.get('model'), {}).get('provider') not in {None, 'mock'})


@measure('fight_groups')
def groups(store, root, states, models):
    """Interchangeable fights merged into counted groups, oriented canonically."""
    cutoffs = _attempt_cutoffs(states)
    rows = store.fight_index.stage_groups(root)
    training = store.fight_index.query(root, 'SELECT a,b,status,winner,modified FROM fights WHERE run=? AND kind=?', ('training',))
    ids = {};stage_ids = {};merged = {}
    def ref(table, value):
        if value not in table:
            table[value] = len(table)
        return table[value]
    for kind, stage, mirror, a, b, candidate, candidate_side, status, winner, count, cached, _ in rows:
        completed = status == 'completed'
        # Without a designated candidate, orientation carries no meaning: fold
        # A-vs-B and B-vs-A together so a pair costs one row per outcome.
        if candidate is None and not mirror and str(b) < str(a):
            a, b = b, a
            if completed and winner in (0, 1):
                winner = 1 - winner
        key = (KINDS.index(kind), ref(stage_ids, stage), mirror, ref(ids, a), ref(ids, b),
               ref(ids, candidate) if candidate is not None else -1, -1 if candidate_side is None else candidate_side)
        counts = merged.setdefault(key, [0, 0, 0, 0, 0])
        index = 3 if not completed else 2 if winner == -1 else winner
        counts[index] += count
        counts[4] += cached
    sessions_training = sum(1 for a, b, status, winner, modified in training
                            if modified >= cutoffs.get(a if a in states else b, 0))
    identity = identities([{'id': sid, **state} for sid, state in states.items()])
    names = list(ids)
    previous = []
    for key in merged:
        kind, _, _, a, b, candidate, side = key
        if KINDS[kind] not in {'evaluation', 'progression'}:
            previous.append(0)
            continue
        cand_id = names[candidate] if candidate >= 0 else names[a]
        opponent = names[b] if names[a] == cand_id else names[a]
        previous.append(int(previous_round(KINDS[kind], identity(cand_id), identity(opponent), models)))
    return {'columns': ['kind', 'stage', 'mirror', 'a', 'b', 'candidate', 'candidate_side',
                        'wins_a', 'wins_b', 'draws', 'failures', 'cached', 'previous_round_comparison'],
            'kinds': list(KINDS), 'stages': list(stage_ids), 'ids': names,
            'rows': [[*key, *counts, flag] for (key, counts), flag in zip(merged.items(), previous)],
            'training_matches': sessions_training}


def _identity_accept(item, scope):
    return ((not scope.get('model') or item['model'] == scope['model'])
            and (not scope.get('round') or item['generation'] + 1 == int(scope['round']))
            and (not scope.get('track') or item['condition'] == scope['track'])
            and (not scope.get('replicate') or item['replicate'] + 1 == int(scope['replicate'])))


def _category(kind):
    """Python form of the Matches tab categories (before progression refinement)."""
    if kind == 'all':
        return lambda fkind, mirror: True
    if kind == 'selfplay':
        return lambda fkind, mirror: bool(mirror)
    if kind in (None, '', 'competition'):
        return lambda fkind, mirror: fkind == 'competition' and not mirror
    if kind == 'progression':
        return lambda fkind, mirror: fkind in ('progression', 'evaluation')
    return lambda fkind, mirror: fkind == kind


def _rows(store, root, training=False):
    """Compact ROW_COLUMNS tuples for record stages, plus preparation tests on request."""
    from .fight_index import ROW_COLUMNS
    rows = store.fight_index.stage_rows(root)
    if training:
        rows = rows + store.fight_index.query(root, f"SELECT {','.join(ROW_COLUMNS)} FROM fights WHERE run=? AND kind='training'")
    return rows


@measure('fight_list')
def listing(store, root, states, models, detail_sessions, manifest, filters, scope):
    """One page of fights matching the Matches tab filters, with facet counts."""
    import json
    identity = identities(detail_sessions, manifest)
    kind = filters.get('kind') or 'competition'
    accept = _category(kind)
    cutoffs = _attempt_cutoffs(states)
    scoped = any(scope.values())
    search = (filters.get('search') or '').lower()
    selected = [];category_total = 0
    session_ids = {row['id'] for row in detail_sessions}
    stage_filter = filters.get('stage')
    for (rowid, fkind, stage, mirror, a, b, candidate, candidate_side, seed, status, winner, turns, elapsed,
         errors_a, errors_b, limits_a, limits_b, cache_hit, modified) in _rows(store, root, training=kind in ('training', 'all')):
        if not accept(fkind, mirror) or (stage_filter and stage != stage_filter):
            continue
        if fkind == 'training' and modified < cutoffs.get(a if a in states else b, 0):
            continue
        sides = [a, b]
        if kind == 'progression' and fkind == 'evaluation':
            cand = identity(candidate) if candidate else identity(a)
            other = identity(b if (candidate or a) == a else a)
            if not previous_round(fkind, cand, other, models):
                continue
        category_total += 1
        if filters.get('scored') and mirror:
            continue
        if filters.get('exclude_same_model') and identity(a)['model'] == identity(b)['model']:
            continue
        scoped_side = None
        if scoped or filters.get('entrant_model') or filters.get('opponent_model') or filters.get('round') or filters.get('track'):
            entries = []
            focus = candidate_side if candidate_side is not None else (sides.index(candidate) if candidate in sides else -1)
            for side, sid in enumerate(sides):
                if fkind in {'evaluation', 'progression'} and focus >= 0 and side != focus:
                    continue
                item = identity(sid)
                if not _identity_accept(item, scope):continue
                if filters.get('entrant_model') and item['model'] != filters['entrant_model']:continue
                if filters.get('round') and filters['round'] != 'all' and item['generation'] + 1 != int(filters['round']):continue
                if filters.get('track') and item['condition'] != filters['track']:continue
                if fkind == 'training' and sid not in session_ids:continue
                if filters.get('opponent_model') and identity(sides[1 - side])['model'] != filters['opponent_model']:continue
                entries.append(side)
            if not entries:
                continue
            scoped_side = entries[0]
        entrant, opponent = filters.get('entrant'), filters.get('opponent')
        if entrant and entrant not in sides:
            continue
        if opponent and (opponent not in sides or (entrant and not any(sid == entrant and sides[1 - side] == opponent for side, sid in enumerate(sides)))):
            continue
        if search and search not in f'{a} {b} {seed}'.lower():
            continue
        completed = status == 'completed'
        side = scoped_side if scoped_side is not None else (
            (candidate_side if candidate == entrant and candidate_side is not None else sides.index(entrant)) if entrant else 0)
        outcome = filters.get('outcome')
        if outcome == 'failure' and completed:continue
        if outcome == 'completed' and not completed:continue
        if outcome == 'draw' and not (completed and winner == -1):continue
        if outcome == 'win' and not (completed and winner == side):continue
        if outcome == 'loss' and not (completed and winner not in (-1, side)):continue
        selected.append((rowid, fkind, stage, mirror, sides, candidate, candidate_side, seed, status, winner, turns, cache_hit, elapsed))
    page = selected[:MATCH_LIMIT]
    details = store.fight_index.details(root, [row[0] for row in page])
    rows = []
    for rowid, fkind, stage, mirror, sides, candidate, candidate_side, seed, status, winner, turns, cache_hit, elapsed in page:
        work, timings = details.get(rowid, (None, None))
        result = {'status': status, 'winner_side': winner, 'turns': turns, 'elapsed_seconds': elapsed}
        if cache_hit:
            result['reference_cache'] = {'hit': True}
        rows.append({'path': work, 'stage': stage, 'kind': fkind, 'sides': sides, 'candidate': candidate,
                     'candidate_side': candidate_side, 'seed': seed_value(seed), 'mirror': bool(mirror), 'result': result,
                     'timings': json.loads(timings) if timings else {}})
    everyone = {sid for row in store.fight_index.stage_rows(root) for sid in (row[4], row[5]) if sid}
    participants = sorted({identity(sid)['model'] for sid in everyone})
    rounds = sorted({identity(sid)['generation'] + 1 for sid in everyone} | {int(s.get('generation') or 0) + 1 for s in detail_sessions})
    training_total = store.fight_index.query(root, "SELECT count(*) FROM fights WHERE run=? AND kind='training'")[0][0]
    return {'matches': rows, 'total': len(selected), 'category_total': category_total, 'limit': MATCH_LIMIT,
            'participants': participants, 'rounds': rounds, 'training_matches': training_total}


def _bins(limit):
    limit = max(1, int(limit or 1000))
    width = max(1, -(-limit // 50))
    return width, -(-limit // width) + 1


@measure('fight_lengths')
def lengths(store, root, detail_sessions, manifest, max_turns):
    """Turn-count histograms per stage, model and outcome class.

    Classes: decisive, early draw (stopped before the turn limit) and capped
    draw (reached the limit). Each fight counts once in the "*" model series and
    once for each distinct model on its sides.
    """
    identity = identities(detail_sessions, manifest)
    width, count = _bins(max_turns)
    limit = int(max_turns or 0)
    series = {}
    for (rowid, kind, stage, mirror, a, b, candidate, candidate_side, seed, status, winner, turns, elapsed,
         *_ignored) in _rows(store, root):
        if status != 'completed' or mirror or turns is None:
            continue
        outcome = 'decisive' if winner in (0, 1) else 'capped' if limit and turns >= limit else 'draw'
        models = {identity(candidate)['model']} if kind in {'evaluation', 'progression'} and candidate else {identity(a)['model'], identity(b)['model']}
        for model in ('*', *models):
            entry = series.get((stage, model, outcome))
            if entry is None:
                entry = series[(stage, model, outcome)] = {'counts': [0] * count, 'fights': 0, 'turns': 0, 'seconds': 0.0}
            entry['counts'][min(count - 1, turns // width)] += 1
            entry['fights'] += 1;entry['turns'] += turns;entry['seconds'] += elapsed or 0
    return {'bin_width': width, 'bins': count, 'max_turns': limit or None,
            'series': [{'stage': stage, 'model': model, 'outcome': outcome, **value}
                       for (stage, model, outcome), value in sorted(series.items())]}


@measure('fight_metrics')
def side_metrics(store, root, cutoffs=None):
    """Per strategy and fight kind: runtime errors and operation-limit hits."""
    cutoffs = cutoffs or {}
    totals = {}
    for (rowid, kind, stage, mirror, a, b, candidate, candidate_side, seed, status, winner, turns, elapsed,
         errors_a, errors_b, limits_a, limits_b, cache_hit, modified) in _rows(store, root, training=True):
        if kind == 'training' and modified < cutoffs.get(a if a in cutoffs else b, 0):
            continue
        for sid, errors, limits in ((a, errors_a, limits_a), (b, errors_b, limits_b)):
            if (kind in {'evaluation', 'progression'} and candidate != sid) or not (errors or limits):
                continue
            row = totals.setdefault((sid, kind), [0, 0])
            row[0] += errors or 0;row[1] += limits or 0
    return totals


@measure('fight_fixtures')
def fixtures(store, root, states, models, source, stage=None):
    """Per-entry outcomes for repetition statistics, as a flat integer array.

    Rows are [session, opponent, seed, side, outcome] with outcome 0=loss,
    1=draw, 2=win, 3=failure. Same-model opponents are excluded except for the
    previous-round comparison, matching the overview's selection.
    """
    accept = _category(source)
    identity = identities([{'id': sid, **state} for sid, state in states.items()])
    ids = {};flat = []
    def ref(value):
        if value not in ids:
            ids[value] = len(ids)
        return ids[value]
    for (rowid, kind, fstage, mirror, a, b, candidate, candidate_side, seed, status, winner, *_ignored) in _rows(store, root):
        if mirror or not accept(kind, mirror) or (stage and fstage != stage):
            continue
        seed = seed_value(seed)
        if not isinstance(seed, int):
            continue
        sides = [a, b]
        if source == 'progression' and kind == 'evaluation':
            cand = identity(candidate or a)
            if not previous_round(kind, cand, identity(b if (candidate or a) == a else a), models):
                continue
        focus = candidate_side if candidate_side is not None else (sides.index(candidate) if candidate in sides else -1)
        for side, sid in enumerate(sides):
            if sid not in states or (kind in {'evaluation', 'progression'} and focus >= 0 and side != focus):
                continue
            opponent = sides[1 - side]
            if source != 'progression' and identity(opponent)['model'] == identity(sid)['model']:
                continue
            outcome = 3 if status != 'completed' or winner not in (-1, 0, 1) else 1 if winner == -1 else 2 if winner == side else 0
            flat.extend((ref(sid), ref(opponent), seed, side, outcome))
    return {'ids': list(ids), 'rows': flat}


def expand(summary):
    """Pseudo-fights carrying a count, one per stored outcome of a group."""
    kinds, stages, ids = summary['kinds'], summary['stages'], summary['ids']
    for kind, stage, mirror, a, b, candidate, side, wins_a, wins_b, draws, failures, cached, previous in summary['rows']:
        base = {'kind': kinds[kind], 'stage': stages[stage], 'mirror': bool(mirror), 'sides': [ids[a], ids[b]],
                'candidate': ids[candidate] if candidate >= 0 else None, 'candidate_side': side if side >= 0 else None,
                'previous_round_comparison': bool(previous)}
        for count, result in ((wins_a, {'status': 'completed', 'winner_side': 0}), (wins_b, {'status': 'completed', 'winner_side': 1}),
                              (draws, {'status': 'completed', 'winner_side': -1}), (failures, {'status': 'failed'})):
            if count:
                yield {**base, 'result': result, 'count': count}
