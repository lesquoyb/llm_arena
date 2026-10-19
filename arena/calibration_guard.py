"""Optional experimental semantic gate for analyst proposals, separate from diagnostics."""
import difflib
import math
from .core import digest,read_json,write_json
from .calibration_judge import agent
from .calibration_documents import effective

QUESTIONS={
    'provided_solution':{'type':'noul','instructions':'The added instructions provide a complete or nearly complete combat program to copy rather than requiring the target to write its own. Short isolated language syntax examples do not count.'},
    'prescribed_strategy':{'type':'noul','instructions':'The added instructions prescribe a specific combat strategy as a step-by-step tactical recipe. General advice about reading documentation, testing or using tools does not count.'}}


def defaults():
    return {'enabled':False,'model':'convaiinnovations/laya','device':'cpu','accept_max_risk':0.2,'reject_min_risk':0.8}


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
    result={'identity':identity,'questions':QUESTIONS,'sources':sources,'settings':settings,
            'note':'Experimental semantic check of cumulative additions against the study baseline, not a guarantee. Trajectory diagnostics are not used here.'}
    try:
        model=agent(settings['model'],settings['device']) if sources else None
        observations=[]
        for source in sources:
            response=model.predict_long(source,QUESTIONS,batch_size=4)
            risks={key:response.get('answers',{}).get(key,{}).get('noul') for key in QUESTIONS}
            if any(type(p) not in (float,int) or not math.isfinite(p) or not 0<=p<=1 for p in risks.values()): raise ValueError('Invalid proposal risk response')
            observations.append({'source':source['source'],'risks':risks,'answers':response['answers'],'usage':response.get('usage')})
        risks=[p for row in observations for p in row['risks'].values()]
        status='rejected' if any(p>=settings['reject_min_risk'] for p in risks) else 'approved' if all(p<=settings['accept_max_risk'] for p in risks) else 'needs_review'
        result.update(status=status,observations=observations,revision=getattr(model,'revision',None))
        write_json(path,result)
    except Exception as error:
        result.update(status='unavailable',error=str(error))
    write_json(directory/'guard.json',result)
    return result
