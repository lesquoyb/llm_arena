"""A transparent ladder of fixed weapon scripts, not an Elo classification."""
CATALOG = [
    {'id':'passive','name':'Passive','description':'Does nothing. Checks whether a strategy can reach and damage an opponent.'},
    {'id':'turret','name':'Stationary shooter','description':'Never moves; fires at most once per turn when an enemy is in range.'},
    {'id':'single-shot','name':'Pursuer, one shot','description':'Moves toward the nearest enemy, then fires at most once per turn.'},
    {'id':'evasive','name':'Catchable evader','description':'Never attacks. Flees nearby enemies using at most two MP, and rests every fourth turn so a pursuer can catch it.'},
    {'id':'rush','name':'Aggressive shooter','description':'Moves toward the nearest enemy and spends available AP on attacks.'},
    {'id':'human-weapon','name':'Human weapon heuristic','description':'Apache-2.0 port of smarlhens: selects a legal weapon by expected burst damage. Weapons only.',
     'source':'https://github.com/smarlhens/leekwars-scripts/tree/0f58ff9641b0573f2757a93b5300b86ca3ab04cf','license':'Apache-2.0'},
]


def participant(name, identifier, scenario):
    import json
    from tempfile import TemporaryDirectory
    from pathlib import Path
    from .core import ROOT, ArenaError, digest, submission
    from .teams import validate_team
    from .stats import default_capital
    if name not in {row['id'] for row in CATALOG}:
        raise ArenaError('Unknown reference strategy')
    files={'main.leek':(ROOT/'examples/strategies'/name/'main.leek').read_text(encoding='utf-8')}
    if scenario.get('team_selection'):
        members=[]
        for index in range(scenario['team_size']):
            spec={**scenario['entity'],**(scenario.get('member_stats') or [{}]*scenario['team_size'])[index]}
            member={'entrypoint':'main.leek','weapons':spec.get('weapons',[]),'chips':spec.get('chips',[]),
                    'components':spec.get('components',[])}
            if scenario['team_selection'].get('require_capital'):
                member['capital']=spec.get('capital',default_capital(spec['level']))
            if scenario['team_selection'].get('independent_builds'):
                member['level']=spec['level']
            members.append(member)
        team=validate_team({'members':members},scenario,files,ROOT/'docs/leekscript-v1')
        files['team.json']=json.dumps(team,ensure_ascii=False,indent=2)+'\n'
    with TemporaryDirectory(prefix='arena-reference-') as directory:
        root=Path(directory)
        for path,text in files.items(): (root/path).write_text(text,encoding='utf-8',newline='')
        info=submission(root)
    return {'id':identifier,'provider':'mock','profile':'saved-strategy','strategy':{
        'files':files,'submission':info,'scenario_sha256':digest(scenario),
        'origin':{'reference':name,**next(row for row in CATALOG if row['id']==name)}}}
