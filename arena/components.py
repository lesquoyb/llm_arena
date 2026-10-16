"""Frozen public component stats and alteration capacity rules."""
from .core import ArenaError, ROOT, integer, read_json

RULES_FILE = ROOT / 'docs/corpus/component-rules.json'
NEGATIVE_STATS = {'strength', 'agility', 'wisdom', 'resistance', 'science', 'magic', 'frequency'}


def catalog():
    data = read_json(RULES_FILE)['components']
    return {str(row['template']): {**row, 'runtime_id': row['template']}
            for row in data.values()}


def alteration_info(delta, component):
    """Check the published end-state charge limit; no forging history is inferred."""
    rules = read_json(RULES_FILE)
    weights = rules['alterations']['weights']
    # Integer quarters avoid rounding away a small over-capacity violation.
    charge_quarters = sum(value * weights[key] * (4 if value >= 0 else 1)
                          for key, value in delta.items())
    capacity = component['capacity']
    if delta and (capacity <= 0 or charge_quarters > 4 * capacity):
        raise ArenaError(f'Component {component["template"]} alteration charge '
                         f'{charge_quarters / 4:g} exceeds capacity {capacity}')
    return {'charge': charge_quarters / 4, 'capacity': capacity}


def identifier(component):
    return component.get('template') if isinstance(component, dict) else component


def public_components(leek):
    """Keep published alteration deltas, excluding account-specific instance IDs."""
    pieces = leek.get('components', [])
    if (not isinstance(pieces, list)
            or any(isinstance(p, dict) and 'template' not in p for p in pieces)):
        raise ArenaError('Public components must be a list')
    return [({'template': p['template'], **({'stats': p['stats']} if p.get('stats') else {})}
             if isinstance(p, dict) else p) for p in pieces if p is not None]


def describe(components, level, realistic=True):
    if not isinstance(components, list) or len(components) > 8:
        raise ArenaError('Equip at most eight component pieces')
    data, bonuses, seen, slots, alterations = catalog(), {}, set(), 0, []
    for piece in components:
        item_id = identifier(piece)
        integer(item_id, 1, 100000, 'component item-template ID')
        if item_id in seen:
            raise ArenaError('A leek cannot equip the same component template twice')
        seen.add(item_id)
        row = data.get(str(item_id))
        if row is None:
            raise ArenaError(f'Unknown component template: {item_id}')
        slots += row['slots']
        if slots > 8:
            raise ArenaError('Component capacity exceeded: eight slots; recovery components consume three each')
        if realistic:
            if row['level'] is None:
                raise ArenaError('Component equipment levels are missing; import the public component-level catalog first')
            if row['level'] > level:
                raise ArenaError(f'Component {item_id} requires level {row["level"]}; leek level is {level}')
        delta = {}
        if isinstance(piece, dict):
            if set(piece) - {'template','stats'}:
                raise ArenaError('Component instances contain template and optional alteration stats only')
            delta = piece.get('stats', {})
            from .stats import STATS
            if not isinstance(delta, dict) or set(delta) - set(STATS):
                raise ArenaError('Unknown component alteration stats')
            for key, value in delta.items():
                integer(value, -100000, 100000, key + ' alteration')
        if realistic:
            alterations.append({'template': item_id, **alteration_info(delta, row)})
        for key, value in row['stats']:
            bonuses[key] = bonuses.get(key, 0) + value
        for key, value in delta.items():
            bonuses[key] = bonuses.get(key, 0) + value
    return {'bonuses': bonuses, 'slots_used': slots, 'slots_available': 8 - slots,
            'alterations': alterations,
            'level_checks_complete': all(data[str(identifier(c))]['level'] is not None for c in components)}


def add_bonuses(stats, bonuses):
    result = {key: value + bonuses.get(key, 0) for key, value in stats.items()}
    for key, value in result.items():
        low = -100000 if key in NEGATIVE_STATS else 1 if key in ('life','cores','ram') else 0
        integer(value, low, 50 if key == 'ram' else 100 if key == 'cores' else 100000, key + ' after components')
    return result
