"""Deterministic defaults for new UI competitions; imported builds stay explicit."""
from .stats import realistic_stats


def simple_scenario():
    # Level 300: 1680 capital. Balanced offensive build, all capital spent.
    capital = {'cores': 140, 'tp': 150, 'mp': 120, 'life': 570, 'strength': 700}
    stats = realistic_stats(300, capital)
    # Pistol, magnum, rifle and rhino: direct damage, simple targeting.
    weapons = [37, 45, 151, 153]
    return {'preset': 'simple', 'team_size': 1, 'max_turns': 1000,
            'stats_mode': 'realistic-v1',
            'entity': {'level': 300, **stats, 'weapons': weapons, 'chips': []},
            'member_stats': [{'name': 'Gunner', 'capital': capital, 'weapons': weapons, 'chips': []}]}


def participant_scenario():
    import copy
    scenario = simple_scenario()
    scenario.update(preset='llm-team', team_size=4)
    scenario['member_stats'] = [copy.deepcopy(scenario['member_stats'][0]) for _ in range(4)]
    for i, member in enumerate(scenario['member_stats'], 1):
        member['name'] = f'Reference {i}'
    scenario['team_selection'] = {'mode': 'participant', 'max_weapons': 4, 'max_chips': 50,
                                  'require_capital': True, 'independent_builds': True}
    return scenario


def dream_team_scenario(path=None):
    from .core import ROOT, ArenaError, read_json, validate_scenario
    path = path or ROOT / 'data/presets/dream-team.json'
    data = read_json(path)
    if data.get('status') != 'ready':
        raise ArenaError('The fixed Dream team preset needs a real public snapshot. Import one or explicitly refresh it; selecting this preset never fetches the ranking.')
    scenario = data['scenario']
    # Older cached imports retained totals but omitted the component instances.
    # Recover them from the existing snapshot, without fetching or altering totals.
    from .components import public_components
    from .stats import STATS
    leeks = scenario.get('source', {}).get('snapshot', {}).get('leeks', [])
    for member, leek in zip(scenario.get('member_stats', []), leeks):
        if ('components' not in member and 'components' in leek
                and member.get('stats') == {key: leek.get('total_' + key) for key in STATS}
                and member.get('level') == leek.get('level')):
            member['components'] = public_components(leek)
    validate_scenario(scenario)
    if scenario.get('preset') != 'dream-team' or scenario['team_size'] != 4 or scenario.get('team_selection'):
        raise ArenaError('Invalid fixed Dream team preset')
    return scenario


def save_dream_team(snapshot, path):
    from .core import write_json
    from .public_teams import scenario_from_snapshot
    scenario = scenario_from_snapshot(snapshot)
    write_json(path, {'schema_version': 1, 'status': 'ready', 'scenario': scenario})
    return scenario
