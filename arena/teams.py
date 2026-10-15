"""Participant-selected teams under shared competition rules."""
from pathlib import PurePosixPath
from .core import ArenaError, integer

TEAM_FILE = "team.json"


def validate_rules(scenario):
    rules = scenario.get("team_selection")
    if rules is None:
        return
    if (not isinstance(rules, dict) or rules.get("mode") != "participant"
            or set(rules) - {"mode", "max_weapons", "max_chips", "allowed_weapons", "allowed_chips", "require_capital"}):
        raise ArenaError("Invalid participant team rules")
    if "require_capital" in rules and (type(rules["require_capital"]) is not bool or
                                        (rules["require_capital"] and scenario.get("stats_mode") != "realistic-v1")):
        raise ArenaError("Explicit capital requires realistic stats")
    for kind, default in (("weapons", 3), ("chips", 12)):
        integer(rules.get("max_" + kind, default), 0, 32, "max_" + kind)
        allowed = rules.get("allowed_" + kind)
        if allowed is not None:
            if not isinstance(allowed, list) or any(type(i) is not int for i in allowed) or len(allowed) != len(set(allowed)):
                raise ArenaError("Equipment allowlists must contain unique IDs")
            for item in allowed:
                integer(item, 1, 100000, kind)
            if kind == "chips":
                from .equipment import validate_player_chips
                validate_player_chips(allowed)


def validate_team(team, scenario=None, files=None, data=None):
    if not isinstance(team, dict) or set(team) != {"members"}:
        raise ArenaError("Team must contain members only")
    members = team["members"]
    maximum = scenario["team_size"] if scenario else 8
    if not isinstance(members, list) or not 1 <= len(members) <= maximum:
        raise ArenaError(f"Team must contain 1 to {maximum} members")
    rules = (scenario or {}).get("team_selection") or {}
    for index, member in enumerate(members):
        if not isinstance(member, dict) or not {"entrypoint", "weapons", "chips"} <= set(member) or set(member) - {"entrypoint", "weapons", "chips", "capital", "stats", "name"}:
            raise ArenaError("Each member needs entrypoint, weapons and chips")
        if rules.get("require_capital") and "capital" not in member:
            raise ArenaError("Choose an explicit capital allocation for every member")
        if "name" in member and (not isinstance(member["name"], str) or not 1 <= len(member["name"]) <= 80):
            raise ArenaError("Member name must contain 1 to 80 characters")
        from .stats import member_stats, STATS
        for key in ("capital", "stats"):
            if key in member and (not isinstance(member[key], dict) or set(member[key]) - set(STATS)
                                  or any(type(v) is not int or v < 0 or v > 100000 for v in member[key].values())):
                raise ArenaError("Invalid member characteristics")
        if scenario:
            values = member_stats(scenario, index, member)
            level = (scenario.get("member_stats") or [{}] * scenario["team_size"])[index].get("level", scenario["entity"]["level"])
        entry = member["entrypoint"]
        if (not isinstance(entry, str) or not entry.endswith(".leek") or "\\" in entry
                or ":" in entry or PurePosixPath(entry).is_absolute() or ".." in PurePosixPath(entry).parts
                or (files is not None and entry not in files)):
            raise ArenaError("Member entrypoint must name an existing .leek source")
        for kind, default in (("weapons", 3), ("chips", 12)):
            items = member[kind]
            if not isinstance(items, list) or len(items) > rules.get("max_" + kind, default if scenario else 32) or any(type(i) is not int for i in items):
                raise ArenaError(f"Invalid {kind} or slot limit exceeded")
            if len(items) != len(set(items)):
                raise ArenaError(f"Duplicate {kind} IDs")
            from .equipment import catalog as equipment_catalog
            catalog = equipment_catalog(data, kind) if data else None
            for item in items:
                integer(item, 1, 100000, kind)
                allowed = rules.get("allowed_" + kind)
                if allowed is not None and item not in allowed:
                    raise ArenaError(f"{kind} ID {item} is not allowed by this competition")
                if catalog is not None:
                    if str(item) not in catalog:
                        raise ArenaError(f"Unknown {kind} ID: {item}")
                    if scenario and scenario.get("stats_mode") != "free" and catalog[str(item)].get("level", 1) > level:
                        raise ArenaError(f"{kind} ID {item} requires a higher level")
        from .equipment import validate_player_chips
        validate_player_chips(member["chips"])
        if scenario and scenario.get('stats_mode') == 'realistic-v1':
            from .equipment import validate_loadout
            validate_loadout(level, values, member['weapons'], member['chips'])
    return team


def build_preview(scenario, index, capital):
    from .stats import realistic_stats, total_capital, RULES
    integer(index, 0, scenario['team_size'] - 1, 'member index')
    if scenario.get('stats_mode') != 'realistic-v1':
        raise ArenaError('Capital previews require realistic stats')
    spec = (scenario.get('member_stats') or [{}] * scenario['team_size'])[index]
    level = spec.get('level', scenario['entity']['level'])
    stats = realistic_stats(level, capital)
    next_costs = {}
    for key, value in stats.items():
        base = RULES['base'].get(key, 0) + ((level - 1) * 3 if key == 'life' else 0)
        step = next(s for s in reversed(RULES['costs'][key]) if value - base >= s['step'])
        used, bonus = 0, 0
        while bonus < value - base:
            previous = next(s for s in reversed(RULES['costs'][key]) if bonus >= s['step'])
            used += previous['capital']
            bonus += previous['sup']
        unused = capital.get(key, 0) - used
        next_costs[key] = {'stat_increase': step['sup'], 'capital_cost': step['capital'] - unused,
                           'unspent_in_allocation': unused}
    return {'level': level, 'stats': stats, 'capital': capital, 'spent': sum(capital.values()),
            'available': total_capital(level), 'remaining': total_capital(level) - sum(capital.values()),
            'weapon_slots': 2 if level < 100 else 3 if level < 200 else 4,
            'chip_slots': stats['ram'], 'next_increases': next_costs,
            'scope': 'Base stats plus capital; no components or alterations.'}


def team_preview(team, scenario, files, check_sources=False):
    from .stats import member_stats, default_capital
    members = []
    for index, member in enumerate(team['members']):
        spec = (scenario.get('member_stats') or [{}] * scenario['team_size'])[index]
        level = spec.get('level', scenario['entity']['level'])
        report = (build_preview(scenario, index, member.get('capital', spec.get('capital', default_capital(level))))
                  if scenario.get('stats_mode') == 'realistic-v1' else
                  {'level': level, 'stats': member_stats(scenario, index, member)})
        members.append({**report, 'entrypoint': member['entrypoint'], 'weapons': member['weapons'],
                        'chips': member['chips'], 'source_exists': member['entrypoint'] in files})
    return {'valid': True, 'members': members, 'maximum_members': scenario['team_size'],
            'source_files_checked': check_sources,
            'missing_entrypoints': [m['entrypoint'] for m in members if not m['source_exists']]}
