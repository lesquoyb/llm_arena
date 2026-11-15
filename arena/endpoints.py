"""Provider transport policy: HTTPS, or HTTP to this machine's loopback."""
import ipaddress
import re
from urllib.parse import urlsplit
from .core import ArenaError

OPENAI_CHAT = 'https://api.openai.com/v1/chat/completions'
OPENAI_RESPONSES = 'https://api.openai.com/v1/responses'


def openai_endpoint(value=None):
    """Keep explicit official routes in older profiles; never send to a gateway."""
    if not value:
        return OPENAI_CHAT
    if not isinstance(value, str) or value.rstrip('/') not in {OPENAI_CHAT, OPENAI_RESPONSES}:
        raise ArenaError('OpenAI uses the official API address. Select OpenAI-compatible for a custom endpoint.')
    return value.rstrip('/')


def clean_api_key(provider, key, binding=None):
    if not key:
        return key
    key = key.strip()
    if provider == 'openai' and (re.search(r'\*{3,}|…|\.{3,}', key)
            or key.lower() in {'unavailable', '[unavailable]', 'redacted', '[redacted]'}):
        where = f' for {binding}' if binding else ''
        raise ArenaError(f'The OpenAI API key{where} is masked or unavailable. Enter the full key, not the value shown in an error or log.')
    if provider == 'openai' and (key.lower() in {'api', 'api key', 'api_key', 'your_openai_key',
            'your_api_key', 'openai_api_key', 'arena_openai_key'} or key.lower().startswith('bearer ')):
        where = f' for {binding}' if binding else ''
        raise ArenaError(f'Enter the actual OpenAI API key{where}, without the Bearer prefix; the environment variable name is a separate field.')
    return key


def is_loopback(url):
    try:
        hostname = urlsplit(url).hostname
        if hostname and hostname.lower().rstrip('.') == 'localhost':
            return True
        return bool(hostname and ipaddress.ip_address(hostname).is_loopback)
    except (ValueError, TypeError, AttributeError):
        return False


def validate_endpoint(url, *, allow_query=False):
    try:
        parsed = urlsplit(url)
        parsed.port  # Reject malformed ports before urllib makes a request.
        valid = (isinstance(url, str) and not any(c.isspace() for c in url)
                 and parsed.hostname and not parsed.username and not parsed.password
                 and not parsed.fragment and (allow_query or not parsed.query)
                 and (parsed.scheme == 'https' or (parsed.scheme == 'http' and is_loopback(url))))
    except (ValueError, TypeError, AttributeError):
        valid = False
    if not valid:
        raise ArenaError('Use HTTPS, or HTTP on localhost/127.0.0.1/[::1], without embedded credentials or fragments')
    return parsed


def optional_local_key(model):
    return model.get('provider') == 'openai-compatible' and is_loopback(model.get('endpoint', ''))
