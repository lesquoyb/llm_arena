"""Translate pinned game catalogs to the IDs accepted by the generator API."""
from .core import read_json


def catalog(data, kind):
    raw = read_json(data / (kind + '.json'))
    return {str(row['item'] if kind == 'weapons' else key):
            {**row, 'catalog_key': key, 'runtime_id': int(row['item'] if kind == 'weapons' else key),
             'restricted_reason': SPECIAL_CHIPS.get(int(key)) if kind == 'chips' else None}
            for key, row in raw.items()}


# The engine catalog includes special entities' equipment. It is not a market list.
# Keep this exceptional instant-kill item out of player-style benchmarks unless
# free mode is explicitly selected; its player obtainability is not established.
SPECIAL_CHIPS = {418: 'Special engine item: player availability is not verified'}


def validate_loadout(level, stats, weapons, chips):
    from .core import ArenaError
    weapon_slots = 2 if level < 100 else 3 if level < 200 else 4
    if len(weapons) > weapon_slots:
        raise ArenaError(f'Level {level} permits {weapon_slots} weapons; selected {len(weapons)}')
    if len(chips) > stats['ram']:
        raise ArenaError(f"RAM {stats['ram']} permits {stats['ram']} chips; selected {len(chips)}")
    for chip in chips:
        if chip in SPECIAL_CHIPS:
            raise ArenaError(f'Chip {chip}: {SPECIAL_CHIPS[chip]}; use free mode for special engine items')
