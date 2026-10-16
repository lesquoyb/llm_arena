"""Pinned official capital allocation and per-member component bonuses."""
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
        integer(value, -100000 if key in ('strength','agility','wisdom','resistance','science','magic','frequency') else 1 if key in ('life', 'cores', 'ram') else 0,
                50 if key == 'ram' else 100 if key == 'cores' else 100000, key)
    return result


def capital_for_stats(level, values, components):
    """Invert final stats exactly, rejecting unattainable values instead of rounding."""
    from .components import describe, add_bonuses
    bonuses = describe(components, level)['bonuses']
    baseline = realistic_stats(level, {})
    values = free_stats(values, baseline)
    capital = {}
    for key in STATS:
        target = values[key] - bonuses.get(key, 0) - baseline[key]
        cost, bonus = 0, 0
        while bonus < target and cost <= total_capital(level):
            step = next(s for s in reversed(RULES['costs'][key]) if bonus >= s['step'])
            cost += step['capital']
            bonus += step['sup']
        if bonus != target:
            raise ArenaError(f'{key}: final value {values[key]} cannot be obtained at level {level} '
                             f'with component bonus {bonuses.get(key, 0)}')
        capital[key] = cost
    if add_bonuses(realistic_stats(level, capital), bonuses) != values:
        raise ArenaError('Recalculated stats differ from the supplied final stats')
    return capital


def to_realistic(scenario):
    """Validate and convert a complete roster without changing any final stat."""
    from copy import deepcopy
    from .core import validate_scenario
    validate_scenario(scenario)
    result = deepcopy(scenario)
    if scenario.get('stats_mode') == 'realistic-v1':
        return result
    specs = result.get('member_stats') or [{} for _ in range(result['team_size'])]
    for index, spec in enumerate(specs):
        try:
            values = member_stats(scenario, index)
            level = spec.get('level', scenario['entity']['level'])
            spec['capital'] = capital_for_stats(level, values, spec.get('components', []))
            spec.pop('stats', None)
        except ArenaError as error:
            raise ArenaError(f'{spec.get("name", f"Leek {index + 1}")}: {error}') from error
    result['member_stats'] = specs
    result['stats_mode'] = 'realistic-v1'
    result['entity'].update(member_stats(result, 0))
    validate_scenario(result)
    return result


def member_stats(scenario, index, member=None):
    mode = scenario.get('stats_mode', 'free')
    specs = scenario.get('member_stats')
    default = specs[index] if specs else {}
    member = member or {}
    # Native fixed opponents pass entrypoint/equipment overrides, but no capital.
    # Only an explicitly allocated participant build opts out of inheritance.
    independent = 'capital' in member and (scenario.get('team_selection') or {}).get('independent_builds')
    level = member.get('level', default.get('level', scenario['entity']['level']))
    integer(level, 1, 301 if mode == 'realistic-v1' else 100000, 'member level')
    if mode == 'realistic-v1':
        if 'stats' in member or set(default) - {'capital', 'weapons', 'chips', 'name', 'level', 'components'}:
            raise ArenaError('Realistic mode accepts capital allocations, not raw stats')
        capital = member.get('capital', default.get('capital', default_capital(level)))
        from .components import describe, add_bonuses
        components = member.get('components', [] if independent else default.get('components', []))
        return add_bonuses(realistic_stats(level, capital), describe(components, level)['bonuses'])
    if 'capital' in member or set(default) - {'stats', 'weapons', 'chips', 'name', 'level', 'components'}:
        raise ArenaError('Free mode accepts raw stats; switch to realistic mode for capital allocations')
    from .components import describe
    describe(member.get('components', default.get('components', [])), level, realistic=False)
    baseline = free_stats(default.get('stats', {}), scenario['entity'])
    return free_stats(member.get('stats', {}), baseline)


def validate_stats(scenario):
    mode = scenario.get('stats_mode', 'free')
    if mode not in ('free', 'realistic-v1'):
        raise ArenaError('Unknown stats mode')
    specs = scenario.get('member_stats')
    if specs is not None and (not isinstance(specs, list) or len(specs) != scenario['team_size'] or any(not isinstance(s, dict) for s in specs)):
        raise ArenaError('Specify one stat build for every default team member')
    from .equipment import catalog, validate_loadout, validate_player_chips
    catalogs = {kind: catalog(ROOT / 'docs/leekscript-v1', kind) for kind in ('weapons', 'chips')}
    for index in range(scenario['team_size']):
        values = member_stats(scenario, index)
        spec = specs[index] if specs else {}
        level = spec.get('level', scenario['entity']['level'])
        if 'name' in spec and (not isinstance(spec['name'], str) or not 1 <= len(spec['name']) <= 80):
            raise ArenaError('Member name must contain 1 to 80 characters')
        gear = {kind: spec.get(kind, scenario['entity'].get(kind, [])) for kind in ('weapons', 'chips')}
        for kind, items in gear.items():
            if not isinstance(items, list) or len(items) > (50 if kind == 'chips' else 32) or any(type(i) is not int for i in items) or len(items) != len(set(items)):
                raise ArenaError(f'Invalid member {index + 1} {kind}')
            if kind == 'chips':
                validate_player_chips(items)
            for identifier in items:
                item = catalogs[kind].get(str(identifier))
                if item is None:
                    raise ArenaError(f'Unknown {kind} ID: {identifier}')
                if mode == 'realistic-v1' and item.get('level', 1) > level:
                    raise ArenaError(f'{kind} ID {identifier} requires level {item["level"]}; leek level is {level}')
        if mode == 'realistic-v1':
            validate_loadout(level, values, gear['weapons'], gear['chips'])
            if index == 0 and any(scenario['entity'].get(key, 0) != value for key, value in values.items()):
                raise ArenaError('Default entity stats must match the first realistic capital allocation')
