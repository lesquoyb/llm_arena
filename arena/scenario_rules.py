"""Audited game-rule changes that apply from a later round of a running competition.

The scenario frozen in experiment.json stays the authority for every round
before a change, so completed fights remain verifiable byte for byte. A change
is recorded in the participants_updated journal event (see roster.update) as
{'from_generation': g, 'stall_turns': n or None} and applies to every fight,
preparation test and participant briefing of generation g and later.
"""
import copy

from .core import ArenaError, integer

RULES = ('stall_turns',)


def scenario_for(config, generation):
    """The scenario in force for a round (generation index, 0 for Round 1)."""
    scenario = copy.deepcopy(config['scenario'])
    for change in sorted(config.get('_scenario_changes', []), key=lambda row: row['from_generation']):
        if generation < change['from_generation']:
            continue
        for rule in RULES:
            if rule not in change:
                continue
            if change[rule] is None:
                scenario.pop(rule, None)
            else:
                scenario[rule] = change[rule]
    return scenario


def round_config(config, generation):
    """A config copy whose scenario is the one in force for that round."""
    return {**config, 'scenario': scenario_for(config, generation)}


def generation_of(label):
    """Round index of an evaluation label such as g3-panel or g4-previous."""
    import re
    match = re.match(r'g(\d+)-', str(label))
    return int(match.group(1)) if match else 0


def validated_change(value, from_generation):
    if not isinstance(value, dict) or set(value) - set(RULES) or not value:
        raise ArenaError('Unknown game-rule change')
    stall = value.get('stall_turns')
    if stall is not None:
        integer(stall, 10, 1000, 'stall_turns')
    return {'from_generation': from_generation, **{rule: value[rule] for rule in RULES if rule in value}}
