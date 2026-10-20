"""Optional experimental semantic gate for analyst proposals, separate from diagnostics."""
import difflib
import math
from .core import digest,read_json,write_json
from .calibration_judge import agent
from .calibration_documents import effective

QUESTIONS={
    'provided_solution':{'type':'noul','instructions':'The text supplies executable LeekScript code implementing a complete combat turn: choosing enemies, moving, attacking, healing or defending. Isolated syntax examples and instructions to write, compile, test or submit code are not combat implementations.'},
    'prescribed_strategy':{'type':'choice','instructions':'What behavior is being prescribed? Judge actual instructions, not mentions of the game.',
        'criteria':{'coding_workflow':'How the programmer reads docs, writes files, compiles, tests and submits code. The programmer still chooses game tactics.',
                    'battle_tactics':'What the game character does in battle: select targets, move, attack, heal or defend in a prescribed way.'}}}



def defaults():
    return {'enabled':False,'mode':'automatic','model':'convaiinnovations/laya','device':'cpu','accept_max_risk':0.2,'reject_min_risk':0.8}


def review(before,after,directory,settings):
    sources=[]
    old={'system prompt':before['prompt'],**effective(before)}
    new={'system prompt':after['prompt'],**effective(after)}
    for name,text in new.items():
        if text==old[name]: continue
        changes=list(difflib.ndiff(old[name].splitlines(),text.splitlines()))
        added='\n'.join(line[2:] for line in changes if line.startswith('+ '))
        if added.strip(): sources.append({'source':name,'added_instructions':added})
    identity=digest({'sources':sources,'settings':settings,'questions':QUESTIONS})
    path=directory/'guards'/f'{identity}.json'
    if path.exists():
        result=read_json(path);write_json(directory/'guard.json',result);return result
    result={'receipt_version':2,'identity':identity,'questions':QUESTIONS,'sources':sources,'settings':settings,
            'risk_interpretation':{'provided_solution':'Probability that added text supplies a complete combat implementation.','prescribed_strategy':'Probability of battle_tactics in the explicit coding_workflow versus battle_tactics classification. Coding workflow is permitted.'},
            'note':'Experimental semantic check of cumulative additions against the study baseline, not a guarantee. Trajectory diagnostics are not used here.'}
    try:
        model=agent(settings['model'],settings['device']) if sources else None
        observations=[]
        result['observations']=observations
        result['revision']=getattr(model,'revision',None)
        for source in sources:
            response=model.predict_long(source,QUESTIONS,batch_size=4)
            observation={'source':source['source'],'response':response}
            observations.append(observation)
            answers=response.get('answers',{})
            domain=answers.get('prescribed_strategy',{}).get('probabilities',{})
            if (not isinstance(domain,dict) or set(domain)!={'coding_workflow','battle_tactics'}
                    or any(type(p) not in (int,float) or not math.isfinite(p) or not 0<=p<=1 for p in domain.values())
                    or abs(sum(domain.values())-1)>0.01):
                raise ValueError('Invalid coding-workflow versus battle-tactics distribution')
            risks={'provided_solution':answers.get('provided_solution',{}).get('noul'),
                   'prescribed_strategy':answers.get('prescribed_strategy',{}).get('probabilities',{}).get('battle_tactics')}
            if any(type(p) not in (float,int) or not math.isfinite(p) or not 0<=p<=1 for p in risks.values()): raise ValueError('Invalid proposal risk response')
            observation.update(risks=risks,answers=response['answers'],usage=response.get('usage'))
        risks=[p for row in observations for p in row['risks'].values()]
        status='rejected' if any(p>=settings['reject_min_risk'] for p in risks) else 'approved' if all(p<=settings['accept_max_risk'] for p in risks) else 'needs_review'
        result.update(status=status,observations=observations,revision=getattr(model,'revision',None))
        write_json(path,result)
    except Exception as error:
        result.update(status='unavailable',error=str(error))
    write_json(directory/'guard.json',result)
    return result
