"""Explicit requested reasoning settings; never silently translate effort levels."""
import re
from .core import ArenaError


def reported_efforts(state):
    failure = state.get('failure') or {}
    diagnostics = failure.get('diagnostics') or {}
    detail = f"{failure.get('message', '')} {diagnostics.get('provider_detail', '')}"
    if 'reasoning_effort' not in detail:
        return ()
    return tuple(dict.fromkeys(re.findall(r'ReasoningEffort\.([a-z_]+)', detail)))


def validate_retry_effort(model, state, requested):
    effort = None if requested == 'provider-default' else requested
    validate_effort(model, effort)
    allowed = reported_efforts(state)
    if effort is not None and allowed and effort not in allowed:
        raise ArenaError(f"Provider accepts these reasoning levels: {', '.join(allowed)}")


def supported_efforts(model):
    if model.get('provider') == 'anthropic':
        name = model.get('model', '').lower()
        if re.match(r'^claude-(?:opus|sonnet)-4-6(?:-|$)', name):
            return ('low', 'medium', 'high', 'max')
        if re.match(r'^claude-opus-4-5(?:-|$)', name):
            return ('low', 'medium', 'high')
        if re.match(r'^claude-(?:3(?:[.-]|$)|(?:haiku|sonnet)-4-5(?:-|$)|(?:opus|sonnet)-4(?:-[01])?(?:-\d{8}|$))', name):
            return ()
        return ('low', 'medium', 'high', 'xhigh', 'max')
    if model.get('provider') in {'openai','openai-compatible'} and model.get('model','').lower() == 'gpt-6.1-sol':
        return ('low','medium','high','xhigh')
    return None


def validate_effort(model, effort):
    if effort is None: return
    if not isinstance(effort,str) or not effort.strip(): raise ArenaError('Reasoning effort must be a nonempty string')
    allowed = supported_efforts(model)
    if allowed == ():
        raise ArenaError(f"{model['model']} does not support reasoning effort. Use its provider-specific thinking settings.")
    if allowed and effort not in allowed:
        raise ArenaError(f"{model['model']} supports reasoning effort: {', '.join(allowed)}. '{effort}' is not supported; low is the smallest supported level.")


def apply_overrides(model, state):
    overrides = state.get('provider_parameter_overrides') or {}
    parameters = dict(model.get('parameters', {}))
    if 'reasoning_effort' in overrides:
        effort = overrides['reasoning_effort']
        if model.get('provider') == 'anthropic':
            output = dict(parameters.get('output_config', {}))
            if effort is None:
                output.pop('effort', None)
            else:
                output['effort'] = effort
            if output:
                parameters['output_config'] = output
            else:
                parameters.pop('output_config', None)
        elif effort is None:
            parameters.pop('reasoning_effort', None)
        else:
            parameters['reasoning_effort'] = effort
    return {**model,'parameters':parameters}
