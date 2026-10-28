"""Evaluate the immutable submissions already available in the current round."""
from .tournament import run_tournament


def entrants(journal, out, generation):
    return [{'id':sid, 'model':state['model'], 'replicate':state['replicate'],
             'path':str(out/'sessions'/sid/'submission'), 'submission':state['submission'],
             **({'parent':state['parent'], 'generation':generation} if generation else {})}
            for sid,state in journal.metadata().items()
            if state.get('generation',0) == generation and 'submission' in state]


def evaluate(engine, config, out, journal, generation=0):
    ready = entrants(journal, out, generation)
    if len(ready) < 2 and not (ready and config['include_mirrors']):
        return None
    root = out/('tournament' if generation == 0 else f'g{generation}-tournament')
    manifest = {'name':config['name'] if generation == 0 else config['name']+f'-round-{generation+1}',
                'seeds':config['seeds'] if generation == 0 else config['final_seeds'],
                'scenario':config['scenario'], 'include_mirrors':config['include_mirrors'], 'strategies':ready}
    # Append-only entrants: archived submissions, seeds and completed fixtures
    # are verified by run_tournament before any new fixtures are admitted.
    reference_models={model['id'] for model in config['models'] if model.get('provider')=='mock'}
    priority={source['id'] for source in ready if source['model'] in reference_models}
    from .core import digest
    signature=digest({'manifest':manifest,'withdrawn':config.get('_withdrawn_models',[])})
    cached=getattr(journal,'_ready_evaluations',{}).get(generation)
    if cached and cached[0]==signature:return cached[1]
    from .activity import operation
    with operation(out,'checking_fights',generation=generation,participants=[s['id'] for s in ready]):
        result=run_tournament(engine,manifest,root,root.exists(),allow_extend=True,priority_ids=priority,reference_ids=priority,parallel_fights=config.get("_parallel_fights",config.get("parallel_fights",1)))
    if not result.get('failed') and not result.get('pending'):
        if not hasattr(journal,'_ready_evaluations'):journal._ready_evaluations={}
        journal._ready_evaluations[generation]=(signature,result)
    return result
