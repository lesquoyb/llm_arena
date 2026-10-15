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
