"""Explore prompt hypotheses freely while exploiting the best measured candidate."""
import random


def defaults():
    return {'exploration':0.2, 'seed':0, 'stop_on_plateau':True,
            'minimum_episodes':10, 'plateau_patience':8, 'minimum_improvement':0.001}


def select(trials, incumbent, settings, episode):
    rng=random.Random(settings['seed']+episode)
    explore=rng.random()<settings['exploration']
    alternatives=[i for i,row in enumerate(trials) if i!=incumbent and row['report'].get('final_valid')]
    parent=rng.choice(alternatives) if explore and alternatives else incumbent
    return {'mode':'exploration' if explore else 'exploitation', 'parent':parent,
            'instruction':('Explore a different hypothesis from recent attempts. You may revise any learning material; choose the diagnosis and modification yourself.'
                           if explore else 'Build on the best measured candidate. Choose the diagnosis and most useful modification yourself.')}


def converged(trials, settings):
    rows=[row for row in trials if row.get('search')]
    if not settings['stop_on_plateau'] or len(rows)<settings['minimum_episodes']: return False
    recent=rows[-settings['plateau_patience']:]
    return len(recent)>=settings['plateau_patience'] and all(row['search']['improvement']<=settings['minimum_improvement'] for row in recent)
