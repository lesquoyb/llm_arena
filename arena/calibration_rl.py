"""Persisted contextual bandit for prompt edits (one-step reinforcement learning).

The analyst implements actions; rewards update the controller, not LLM weights.
All random choices are deterministic from the saved study seed and episode index.
"""
import math
import random

ACTIONS = {
    'language': 'Improve language/API guidance using actual compilation and syntax failures.',
    'strategy': 'Improve scenario understanding and tactical planning; preserve correct language guidance.',
    'tools': 'Improve tool discovery, pagination, test/compile workflow and interpretation of tool results.',
    'compression': 'Remove redundant or misleading prompt/document content while preserving useful information.',
    'explore': 'Try a substantially different evidence-based teaching approach; explain the hypothesis.',
}


def defaults():
    return {'learning_rate': 0.25, 'exploration': 0.2, 'seed': 0, 'stop_on_plateau': True,
            'minimum_episodes': 10, 'plateau_patience': 8, 'minimum_improvement': 0.001}


def context(report):
    if not report.get('final_valid'): return 'invalid'
    score = report['validation_score']
    return 'low' if score < 0.4 else 'medium' if score < 0.8 else 'high'


def select(policy, report, settings, episode):
    state = context(report)
    rows = policy.get('values', {}).get(state, {})
    rng = random.Random(settings['seed'] + episode)
    untried = [action for action in ACTIONS if not rows.get(action, {}).get('visits')]
    if untried:
        action = rng.choice(untried)
        exploring = True
    elif rng.random() < settings['exploration']:
        action = rng.choice(list(ACTIONS))
        exploring = True
    else:
        best = max(rows[action]['q'] for action in ACTIONS)
        action = rng.choice([action for action in ACTIONS if rows[action]['q'] == best])
        exploring = False
    return {'context': state, 'action': action, 'instruction': ACTIONS[action], 'exploring': exploring}


def update(policy, action, reward, settings):
    if not math.isfinite(reward): raise ValueError('Non-finite RL reward')
    row = policy.setdefault('values', {}).setdefault(action['context'], {}).setdefault(action['action'], {'q': 0.0, 'visits': 0})
    before = row['q']
    row['q'] += settings['learning_rate'] * (reward - row['q'])
    row['visits'] += 1
    return {'reward': reward, 'q_before': before, 'q_after': row['q'], 'visits': row['visits']}


def converged(trials, settings):
    episodes = [row for row in trials if row.get('rl')]
    if not settings['stop_on_plateau'] or len(episodes) < settings['minimum_episodes']: return False
    recent = episodes[-settings['plateau_patience']:]
    if len(recent) < settings['plateau_patience']: return False
    # Exploration must have tried every edit operator, including in the current context.
    state = episodes[-1]['rl']['context']
    tried = {row['rl']['action'] for row in episodes if row['rl']['context'] == state}
    return set(ACTIONS) <= tried and all(row['rl']['reward'] <= settings['minimum_improvement'] for row in recent)
