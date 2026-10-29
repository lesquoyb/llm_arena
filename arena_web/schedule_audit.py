"""Read-only reconciliation of frozen submissions, scheduled fixtures and results."""
from collections import Counter
from arena.core import ArenaError, digest
from arena.roster import effective
from arena.reference_strategies import repetitions
from arena.tournament import schedule


def audit(store, identifier, generation=None):
    root=store.run_path(identifier);metadata=store.json(root/'experiment.json',{})
    config=effective(root,metadata.get('config',{}))
    states=store.states(root,('model','generation','condition','status','submission','steps','in_flight','reserved'))
    withdrawn=set(config.get('_withdrawn_models',[]))
    from arena.roster import snapshot
    withdrawn.update((snapshot(root) or {}).get('withdrawn',[]))
    if generation is None:generation=max((state.get('generation',0) for state in states.values()),default=0)
    if type(generation) is not int or generation<0:raise ArenaError('Invalid round')
    current={sid:state for sid,state in states.items() if state.get('generation',0)==generation and state['model'] not in withdrawn}
    ready={sid:state for sid,state in current.items() if state.get('submission')}
    seeds=config.get('final_seeds' if generation else 'seeds',[])
    expected=schedule({'strategies':[{'id':sid} for sid in ready],'seeds':seeds,'include_mirrors':config.get('include_mirrors',False)})
    expected_ids={match['id'] for match in expected}
    tournament=root/('tournament' if generation==0 else f'g{generation}-tournament')
    frozen=store.json(tournament/'experiment.json',{})
    planned_ids={match['id'] for match in frozen.get('schedule',[])}
    recorded={};invalid=[]
    for path in sorted((tournament/'records').glob('*.json')):
        try:
            value=store.workspace_artifact(path,'record');match=value['match']
            key=match.get('id') or digest({'sides':match['sides'],'seed':match['seed'],'mirror':match.get('mirror',False)})[:20]
            recorded[key]=value
        except (ArenaError,OSError,ValueError,KeyError,TypeError) as error:
            invalid.append({'record':path.name,'error':str(error)})
    config['_fixed_reference_repetitions']=metadata.get('fixed_reference_repetitions',config.get('replicates',1))
    tracks=len(config.get('improvement_conditions',['control','feedback'])) if generation else 1
    models={model['id']:{'model':model['id'],'expected_submissions':repetitions(config,model)*tracks,
        'submitted':sum(state['model']==model['id'] for state in ready.values()),
        'available_ranked_appearances':0,'completed_ranked_appearances':0,'failed_ranked_appearances':0}
        for model in config.get('models',[]) if model['id'] not in withdrawn}
    for match in expected:
        a,b=(ready[sid]['model'] for sid in match['sides'])
        if a==b:continue
        result=recorded.get(match['id'],{}).get('result')
        for model in (a,b):
            row=models[model];row['available_ranked_appearances']+=1
            if result:row['completed_ranked_appearances' if result.get('status')=='completed' else 'failed_ranked_appearances']+=1
    from arena.budget_context import tool_budget_exhausted
    statuses=Counter(recorded[key]['result'].get('status','unknown') for key in expected_ids&recorded.keys())
    missing=expected_ids-recorded.keys()
    reported=store.json(tournament/'report.json',{})
    return {'run':identifier,'round':generation+1,'combat_seeds':len(seeds),
        'submitted':len(ready),'expected_submissions':sum(row['expected_submissions'] for row in models.values()),
        'available_fixtures':len(expected),'planned_fixtures':len(planned_ids),
        'missing_from_plan':len(expected_ids-planned_ids),'missing_result_records':len(missing),
        'actual_result_statuses':dict(statuses),'invalid_records':invalid[:20],
        'reported_counts':{key:reported.get(key) for key in ('completed','failed','pending','cancelled')},
        'models':list(models.values()),'unfinished_sessions':[{'session':sid,'model':state['model'],'status':state['status'],
            'tool_calls':state.get('steps',0),'finalization_due':tool_budget_exhausted(state,config.get('budget_per_session',{}))}
            for sid,state in current.items() if not state.get('submission')],
        'note':'Ranked appearances count both sides and exclude self-play and same-model fights. Missing records are counted independently of the cached report.'}
