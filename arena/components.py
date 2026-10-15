"""Pinned base components: item-template IDs, slot costs and additive bonuses."""
from .core import ArenaError, ROOT, integer, read_json

LEVEL_FILE = ROOT / 'docs/corpus/component-levels.json'
LEVELS = read_json(LEVEL_FILE).get('levels', {}) if LEVEL_FILE.exists() else {}
NEGATIVE_STATS = {'strength', 'agility', 'wisdom', 'resistance', 'science', 'magic', 'frequency'}


def catalog():
    data = read_json(ROOT / 'docs/leekscript-v1/components.json')
    return {str(row['template']): {**row, 'runtime_id': row['template'],
                'level': LEVELS.get(str(row['template'])),
                'slots': 3 if row['template'] in (406,407) else 1}
            for row in data.values()}


def identifier(component):
    return component.get('template') if isinstance(component, dict) else component


def describe(components, level, realistic=True):
    if not isinstance(components, list) or len(components) > 8:
        raise ArenaError('Equip at most eight component pieces')
    data, bonuses, seen, slots = catalog(), {}, set(), 0
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
            if isinstance(piece, dict):
                raise ArenaError('Realistic builds accept base component IDs only; alterations are not validated')
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
        for key, value in row['stats']:
            bonuses[key] = bonuses.get(key, 0) + value
        for key, value in delta.items():
            bonuses[key] = bonuses.get(key, 0) + value
    return {'bonuses': bonuses, 'slots_used': slots, 'slots_available': 8 - slots,
            'level_checks_complete': all(data[str(identifier(c))]['level'] is not None for c in components)}


def add_bonuses(stats, bonuses):
    result = {key: value + bonuses.get(key, 0) for key, value in stats.items()}
    for key, value in result.items():
        low = -100000 if key in NEGATIVE_STATS else 1 if key in ('life','cores','ram') else 0
        integer(value, low, 50 if key == 'ram' else 100 if key == 'cores' else 100000, key + ' after components')
    return result
