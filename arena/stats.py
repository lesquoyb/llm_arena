"""Pinned official capital allocation; realistic builds exclude components."""
from .core import ArenaError, ROOT, integer, read_json

RULES = read_json(ROOT / 'docs/corpus/stat-rules.json')
STATS = tuple(RULES['costs'])


def total_capital(level):
    integer(level, 1, 301, 'realistic level')
    return 50 + (level - 1) * 5 + (level // 100) * 45 + (95 if level == 301 else 0)


def stat_bonus(stat, capital):
    steps, bonus = RULES['costs'][stat], 0
    while capital:
        step = next(s for s in reversed(steps) if bonus >= s['step'])
        if capital < step['capital']:
            break
        capital -= step['capital']
        bonus += step['sup']
    return bonus


def default_capital(level):
    remaining, result = total_capital(level), {}
    for key, desired in [('cores', 140), ('tp', 65), ('mp', 60), ('life', 50), ('strength', 50)]:
        result[key] = min(remaining, desired)
        remaining -= result[key]
    return result


def realistic_stats(level, capital):
    maximum = total_capital(level)
    if not isinstance(capital, dict) or set(capital) - set(STATS):
        raise ArenaError('Unknown capital characteristics')
    for key, value in capital.items():
        integer(value, 0, maximum, key + ' capital')
    used = sum(capital.values())
    if used > maximum:
        raise ArenaError(f'Capital allocation uses {used}; level {level} permits {maximum}')
    result = {key: RULES['base'].get(key, 0) + stat_bonus(key, capital.get(key, 0)) for key in STATS}
    result['life'] += (level - 1) * 3
    return result


def free_stats(values, baseline):
    if not isinstance(values, dict) or set(values) - set(STATS):
        raise ArenaError('Unknown member characteristics')
    result = {key: values.get(key, baseline.get(key, 0)) for key in STATS if key in values or key in baseline}
    for key, value in result.items():
        integer(value, 1 if key in ('life', 'cores', 'ram') else 0,
                50 if key == 'ram' else 100 if key == 'cores' else 100000, key)
    return result


def member_stats(scenario, index, member=None):
    mode = scenario.get('stats_mode', 'free')
    specs = scenario.get('member_stats')
    default = specs[index] if specs else {}
    member = member or {}
    if mode == 'realistic-v1':
        if 'stats' in member or set(default) - {'capital'}:
            raise ArenaError('Realistic mode accepts capital allocations, not raw stats')
        capital = member.get('capital', default.get('capital', default_capital(scenario['entity']['level'])))
        return realistic_stats(scenario['entity']['level'], capital)
    if 'capital' in member or set(default) - {'stats'}:
        raise ArenaError('Free mode accepts raw stats; switch to realistic mode for capital allocations')
    baseline = free_stats(default.get('stats', {}), scenario['entity'])
    return free_stats(member.get('stats', {}), baseline)


def validate_stats(scenario):
    mode = scenario.get('stats_mode', 'free')
    if mode not in ('free', 'realistic-v1'):
        raise ArenaError('Unknown stats mode')
    specs = scenario.get('member_stats')
    if specs is not None and (not isinstance(specs, list) or len(specs) != scenario['team_size'] or any(not isinstance(s, dict) for s in specs)):
        raise ArenaError('Specify one stat build for every default team member')
    for index in range(scenario['team_size']):
        values = member_stats(scenario, index)
        if mode == 'realistic-v1' and index == 0:
            if any(scenario['entity'].get(key, 0) != value for key, value in values.items()):
                raise ArenaError('Default entity stats must match the first realistic capital allocation')

    if mode == 'realistic-v1':
        for kind in ('weapons', 'chips'):
            catalog = read_json(ROOT / 'docs/leekscript-v1' / (kind + '.json'))
            for identifier in scenario['entity'].get(kind, []):
                item = catalog.get(str(identifier))
                if item is None:
                    raise ArenaError(f'Unknown {kind} ID: {identifier}')
                if item.get('level', 1) > scenario['entity']['level']:
                    raise ArenaError(f'{kind} ID {identifier} requires level {item["level"]}; leek level is {scenario["entity"]["level"]}')
