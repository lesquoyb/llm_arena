"""Gameplay information exposed to participants, separate from run provenance."""
import copy
from .core import ROOT
from .stats import member_stats
from .equipment import catalog as equipment_catalog
from .components import catalog as component_catalog, identifier


def participant_scenario(scenario):
    # Explicit allowlist: imported farmer profiles, fight history and source hashes
    # belong to provenance and must never enter the participant's context.
    return copy.deepcopy({key: scenario[key] for key in
        ('preset', 'team_size', 'max_turns', 'stats_mode', 'entity', 'member_stats', 'team_selection', 'map')
        if key in scenario})


def briefing(scenario):
    data = ROOT / 'docs/leekscript-v1'
    catalogs = {kind: equipment_catalog(data, kind) for kind in ('weapons', 'chips')}
    catalogs['components'] = component_catalog()
    roster = []
    for index in range(scenario['team_size']):
        spec = (scenario.get('member_stats') or [{}] * scenario['team_size'])[index]
        equipment = {}
        for kind in catalogs:
            pieces = spec.get(kind, scenario['entity'].get(kind, []))
            equipment[kind] = [{'id': identifier(piece), 'name': catalogs[kind][str(identifier(piece))]['name']}
                               for piece in pieces]
        roster.append({'member': index + 1, 'name': spec.get('name', f'Leek {index + 1}'),
                       'level': spec.get('level', scenario['entity']['level']),
                       'final_stats': member_stats(scenario, index), **equipment})
    selected = bool(scenario.get('team_selection'))
    independent = (scenario.get('team_selection') or {}).get('independent_builds')
    return {
        'game': 'LeekWars: a turn-based tactical fight on a grid. Each living leek executes its LeekScript once per turn. AP (tp) pays for weapons/chips; MP (mp) pays for movement. Line of sight, range and cooldowns constrain actions. Summons run their own callback scripts.',
        'objective': 'Defeat the opposing team while keeping your team alive. Eliminate all enemies to win. Reaching the turn limit without a winner is a draw. Tournament score is win=1, draw=0.5, loss=0; mirror matches do not count.',
        'team_mode': ('Choose 1 to team_size members, each with an entrypoint, equipment and stat build. Write sources, validate_team, then configure_team before test/submit. Other participants can choose different teams; fixed reference opponents use the roster below.' if selected else
                      'The roster below is fixed for both sides. Write one main.leek script, executed independently by every member of your team. Equipment and stats cannot be changed by configure_team in this mode.'),
        'build_rules': 'Choose an explicit level (1 to 301), capital allocation, weapons, chips and optional components for every member. Reference builds are not imposed; omitted components mean none. preview_build accepts level, capital and components; validate_team checks the entire proposal.' if independent else 'Members use the reference levels and inherit their builds unless the team-selection rules permit overrides. Check scenario.team_selection before configuring a team.',
        'roster_role': 'Default roster and fixed reference opponents' if selected else 'Your team and the opposing team; scripts differ',
        'roster': roster,
        'stats': 'life=HP; strength=physical damage; science/magic=effect scaling; agility/resistance/wisdom=other combat characteristics; frequency=turn order; tp=AP per turn; mp=MP per turn; cores=millions of operations per script turn; ram=script memory and realistic chip capacity. Exact effect formulas are in the API guide and equipment catalogs.',
        'ids': {'weapons': 'Runtime weapon IDs are the item field in leekscript-v1/weapons.json, e.g. pistol=37; object keys and replay template IDs differ.',
                'chips': 'Runtime chip IDs are the object key/id in leekscript-v1/chips.json, e.g. shock=1. Replay actions use template IDs.',
                'components': 'Use component template IDs in corpus/component-rules.json. Its current stats, levels, slots and alteration capacities override the older generator catalog. Altered instances use {template, stats}, with additive alteration deltas. Read corpus/components.md.',
                'entities': 'Use getLeek(), getAliveEnemies(), getAliveAllies() and related game APIs for runtime entity IDs. Roster positions are not runtime IDs. A missing target is -1, not null.'},
        'tools': 'You have the native engine through analyze (compile diagnostics), test (two fights, both sides, fixed training seed against passive), and read_replay (actions, metrics, errors and debug logs). read_docs provides the pinned API and all selectable equipment. You can only read/write your own workspace and the shared docs; no shell or opponent code is exposed.',
        'submission': 'Write main.leek and optional .leek support files, then submit. In participant-team mode each configured member can use its own .leek entrypoint. Tool errors are recoverable: read them and fix your proposal. An explicit tool submission finishes preparation.',
    }
