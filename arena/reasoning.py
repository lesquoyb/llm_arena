"""Explicit requested reasoning settings; never silently translate effort levels."""
from .core import ArenaError


def supported_efforts(model):
    if model.get('provider') in {'openai','openai-compatible'} and model.get('model','').lower() == 'gpt-6.1-sol':
        return ('low','medium','high','xhigh')
    return None


def validate_effort(model, effort):
    if effort is None: return
    if not isinstance(effort,str) or not effort.strip(): raise ArenaError('Reasoning effort must be a nonempty string')
    allowed = supported_efforts(model)
    if allowed and effort not in allowed:
        raise ArenaError(f"{model['model']} supports reasoning effort: {', '.join(allowed)}. '{effort}' is not supported; low is the smallest supported level.")


def apply_overrides(model, state):
    overrides = state.get('provider_parameter_overrides') or {}
    parameters = dict(model.get('parameters', {}))
    if 'reasoning_effort' in overrides:
        if overrides['reasoning_effort'] is None: parameters.pop('reasoning_effort',None)
        else: parameters['reasoning_effort'] = overrides['reasoning_effort']
    return {**model,'parameters':parameters}
