"""Translate pinned game catalogs to the IDs accepted by the generator API."""
from .core import read_json


def catalog(data, kind, include_special=False):
    raw = read_json(data / (kind + '.json'))
    return {str(row['item'] if kind == 'weapons' else key):
            {**row, 'catalog_key': key, 'runtime_id': int(row['item'] if kind == 'weapons' else key),
             'restricted_reason': SPECIAL_CHIPS.get(int(key)) if kind == 'chips' else None}
            for key, row in raw.items()
            if include_special or kind != "chips" or int(key) not in SPECIAL_CHIPS}


# Equipment reserved for bosses or a summon's native abilities, not player loadouts.
# Preserve upstream data for native summon behavior and historical replay decoding.
SPECIAL_CHIPS = dict.fromkeys(range(411, 420), 'Boss-only chip')
SPECIAL_CHIPS.update({425: 'Internal special chip', **dict.fromkeys(range(444, 448), 'Summon-only chip')})


def validate_player_chips(chips):
    from .core import ArenaError
    for chip in chips:
        if chip in SPECIAL_CHIPS:
            raise ArenaError(f'Chip {chip} is not player equipment: {SPECIAL_CHIPS[chip]}')


def validate_loadout(level, stats, weapons, chips):
    from .core import ArenaError
    weapon_slots = 2 if level < 100 else 3 if level < 200 else 4
    if len(weapons) > weapon_slots:
        raise ArenaError(f'Level {level} permits {weapon_slots} weapons; selected {len(weapons)}')
    if len(chips) > stats['ram']:
        raise ArenaError(f"RAM {stats['ram']} permits {stats['ram']} chips; selected {len(chips)}")
    validate_player_chips(chips)
