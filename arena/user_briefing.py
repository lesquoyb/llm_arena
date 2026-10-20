"""Readable participant context; internal configuration stays in the archive."""
import json
import re


def render(message):
    scenario=message.get('scenario') or {};brief=message.get('briefing') or {}
    rules=scenario.get('team_selection') or {};selected=bool(rules)
    sections=[message.get('content','').strip(),'## Scenario',brief.get('game','LeekWars: turn-based tactical combat on a grid.'),
              f"Defeat the opposing team. Eliminating all enemies wins; no winner after {scenario.get('max_turns','the configured limit')} turns is a draw. Win=1, draw=0.5, loss=0."]
    if not selected and not any(member.get('chips') for member in brief.get('roster',[])):
        sections=[part.replace(' Summons run their own callback scripts.','') for part in sections]
    if selected:
        sections+=['## Your team: you must build it',f"Choose 1 to {scenario['team_size']} members. Choose their source entrypoints, weapons, chips and stat builds; members may differ. The reference roster below is not your team."]
        if rules.get('independent_builds'):
            from .teams import maximum_level
            legacy=re.search(r'level \(1 to (\d+)\)',brief.get('build_rules',''))
            level_limit=brief.get('max_member_level') or (int(legacy[1]) if legacy else maximum_level(scenario))
            sections.append(f"Choose an explicit level from 1 to {level_limit} and an explicit capital allocation for every member. Reference levels and stats are not imposed. Optional components may modify the build.")
        elif rules.get('require_capital'): sections.append('Allocate capital explicitly for every member; reference levels apply.')
        else: sections.append(brief.get('build_rules','Reference levels and default builds apply unless overridden within the scenario rules.'))
        if scenario.get('stats_mode')=='realistic-v1':
            sections.append('Allocate capital rather than raw final stats. Read corpus/stat-rules.json for costs and corpus/component-rules.json for component constraints; preview_build calculates final values.')
        sections.append(f"Stats mode: {scenario.get('stats_mode','free')}. Upper equipment limits: {rules.get('max_weapons',3)} weapons and {rules.get('max_chips',12)} chips per member. Level, weapon-slot and RAM/chip-capacity rules may impose lower limits; validate the complete build.")
        for kind in ('weapons','chips'):
            if rules.get('allowed_'+kind) is not None: sections.append('Allowed '+kind+' IDs: '+', '.join(map(str,rules['allowed_'+kind]))+'.')
        sections+=['Write the source files first. Use preview_build for final stats/capital and validate_team for draft checks when enabled. Call configure_team to save the actual roster, then analyze and submit. Sources alone do not configure a team. On later rounds the saved sources and configured team are inherited and can be revised.','## Fixed reference roster (opponents only)']
    else:
        sections+=['## Your fixed roster',f"Your team has {scenario['team_size']} members. Its levels, stats and equipment are fixed; do not call configure_team. The entrypoint runs once per living member per turn."]
    groups={}
    for member in brief.get('roster',[]):
        spec={key:value for key,value in member.items() if key not in {'member','name'}}
        key=json.dumps(spec,sort_keys=True);groups.setdefault(key,{'spec':spec,'members':[]})['members'].append(str(member['member']))
    for group in groups.values():
        spec=group['spec'];line='Members '+', '.join(group['members'])+': level '+str(spec.get('level'))+'. '
        line+='Stats: '+', '.join(f'{key}={value}' for key,value in spec.get('final_stats',{}).items())+'. '
        for kind in ('weapons','chips','components'):
            items=spec.get(kind,[])
            if items: line+=kind.title()+': '+', '.join(f"{item['name']} (ID {item['id']})" for item in items)+'. '
        sections.append(line)
    if brief.get('stats'): sections.append(brief['stats'])
    sections.append('## API and equipment references')
    sections.append('Use getEntity() for your active runtime entity ID. Runtime entity IDs, cell IDs, equipment IDs and roster positions are different concepts. Game calls are global LeekScript functions.')
    relevant=[kind for kind in ('weapons','chips','components') if selected or any(member.get(kind) for member in brief.get('roster',[]))]
    for kind in relevant:
        if brief.get('ids',{}).get(kind): sections.append(brief['ids'][kind])
    sections.append('Read shared documentation with read_docs, not read_file. Use corpus/language/cheatsheet.md for syntax and corpus/api-guide.md for API semantics. lookup_api supports queries for grouped signatures and mode=index for function names. Only tools in the supplied declarations are enabled.')
    if scenario.get('map'):
        sections.append('## Map constraints')
        for key,value in scenario['map'].items(): sections.append(key+': '+', '.join(map(str,value)))
    limits=(message.get('preparation_budget') or {}).get('limits',{})
    labels={'calls':'model calls','steps':'tool steps','test_matches':'preparation fights','wall_seconds':'seconds','input_tokens':'input tokens','output_tokens':'output tokens','cost_usd':'USD'}
    budget=message.get('budgets') or {}
    if limits or budget:
        sections.append('## Preparation limits (this round)')
        if limits:
            for key,row in limits.items(): sections.append(f"- {labels.get(key,key)}: {row['limit']} maximum; {row.get('remaining','unknown')} remaining.")
        else:
            for key,value in budget.items(): sections.append(f'- {key}: {value}')
        sections.append('Calls and tool steps are separate. One test uses two preparation fights. At exhaustion, Arena freezes the latest saved files even without submit. Invalid code or an incomplete team still fails evaluation. Save early and leave time to configure the team and analyze. Input usage includes repeated/cached context; output usage includes reasoning when reported.')
    if message.get('shared_spending_limit_usd') is not None:
        sections.append('Shared API spending ceiling across conversations: USD '+str(message['shared_spending_limit_usd'])+'. Its exhaustion also freezes preparation.')
    consumed={'role','content','scenario','briefing','equipment_ids','team_instructions','budgets','preparation_budget','budget_instructions','shared_spending_limit_usd','shared_limit_instructions','context_format','generation'}
    extra={key:value for key,value in message.items() if key not in consumed}
    if extra:
        sections.append('## This preparation period')
        def describe(key,value,depth=0):
            if isinstance(value,dict):
                sections.append('  '*depth+key.replace('_',' ')+':')
                for child,item in value.items(): describe(child,item,depth+1)
            elif isinstance(value,list):
                sections.append('  '*depth+key.replace('_',' ')+':')
                for index,item in enumerate(value,1): describe(str(index),item,depth+1)
            else: sections.append('  '*depth+key.replace('_',' ')+': '+str(value))
        for key,value in extra.items(): describe(key,value)
    return '\n\n'.join(part for part in sections if part)
