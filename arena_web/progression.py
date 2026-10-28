"""Candidate-only historical comparisons; no opponent losses are pooled into scores."""


def summarize(states, models, matches):
    """Compare a version with its own root/parent and the preceding LLM pool."""
    groups={}
    def learnable(state):return models.get(state.get('model'),{}).get('provider') not in {None,'mock'}
    def key(state):return state['model'],state.get('generation',0),state.get('condition','initial')
    def blank():return {'wins':0,'draws':0,'losses':0,'failures':0,'opponents':set(),'seen':set()}
    for state in states.values():
        if learnable(state) and state.get('generation',0)>0:
            groups.setdefault(key(state),{name:blank() for name in ('own_initial','own_previous','previous_pool')})
    for match in matches:
        if match.get('mirror') or match.get('kind') not in {'evaluation','progression'}:continue
        sid=match.get('candidate');candidate=states.get(sid,{})
        if not learnable(candidate) or candidate.get('generation',0)<=0:continue
        side=match.get('candidate_side')
        if side not in (0,1):side=match.get('sides',[]).index(sid) if sid in match.get('sides',[]) else None
        if side not in (0,1) or len(match.get('sides',[]))!=2:continue
        oid=match['sides'][1-side];opponent=states.get(oid,{})
        if not learnable(opponent):continue
        generation=candidate['generation'];same=candidate['model']==opponent.get('model')
        same_replicate=candidate.get('replicate',0)==opponent.get('replicate',0)
        prior=opponent.get('generation',0)==generation-1
        parent=(oid==candidate['parent']) if candidate.get('parent') else (same and same_replicate and (generation==1 or candidate.get('condition')==opponent.get('condition')))
        selected={'own_initial':same and same_replicate and opponent.get('generation',0)==0,
                  'own_previous':prior and same and same_replicate and parent,
                  'previous_pool':prior}
        for name,include in selected.items():
            if not include:continue
            row=groups[key(candidate)][name]
            identity=(match.get('path'),sid,match.get('seed'),side,oid)
            if identity in row['seen']:continue
            row['seen'].add(identity);row['opponents'].add(oid)
            result=match.get('result',{});winner=result.get('winner_side')
            if result.get('status')!='completed' or winner not in (-1,0,1):row['failures']+=1
            else:row['draws' if winner==-1 else 'wins' if winner==side else 'losses']+=1
    result=[]
    for (model,generation,condition),comparisons in sorted(groups.items()):
        values={}
        for name,row in comparisons.items():
            completed=row['wins']+row['draws']+row['losses']
            values[name]={**{field:row[field] for field in ('wins','draws','losses','failures')},
                          'completed':completed,'opponent_versions':len(row['opponents']),
                          'score':(row['wins']+.5*row['draws'])/completed if completed else None}
        result.append({'model':model,'generation':generation,'condition':condition,**values})
    return result
