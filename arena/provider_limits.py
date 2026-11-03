"""Live transport concurrency controls, shared by models on one API endpoint."""
from urllib.parse import urlsplit, urlunsplit
from .core import integer, read_json
from .endpoints import is_loopback


def endpoint(model):
    from .api_providers import DEFAULT_ENDPOINTS
    value=(model.get('endpoint') or DEFAULT_ENDPOINTS.get(model.get('provider'),'')).rstrip('/')
    for suffix in ('/chat/completions','/responses','/messages'):
        if value.endswith(suffix):value=value[:-len(suffix)];break
    parsed=urlsplit(value)
    # Credentials and query strings are never part of scheduling or UI labels.
    local=is_loopback(value)
    host='localhost' if local else (parsed.hostname or '')
    if ':' in host:host='['+host+']'
    port=parsed.port
    if port and port!=(443 if parsed.scheme=='https' else 80):host+=':'+str(port)
    return urlunsplit((parsed.scheme.lower(),host.lower(),'' if local else parsed.path,'',''))


def configured(out):
    path=out/'provider-control.json'
    return read_json(path).get('endpoint_limits',{}) if path.exists() else {}


def limit(model, limits):
    key=endpoint(model)
    return limits.get(key,1 if is_loopback(key) else None)


def validate(limits):
    if not isinstance(limits,dict):raise ValueError('Expected endpoint limits')
    for key,value in limits.items():
        if not isinstance(key,str) or len(key)>2048:raise ValueError('Invalid endpoint')
        if value is not None:integer(value,1,None,'max_parallel_requests')
    return limits
