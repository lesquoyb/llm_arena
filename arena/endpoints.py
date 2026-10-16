"""Provider transport policy: HTTPS, or HTTP to this machine's loopback."""
import ipaddress
from urllib.parse import urlsplit
from .core import ArenaError


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
