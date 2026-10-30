"""Load local environment assignments without shell evaluation or interpolation."""
import os
from pathlib import Path
import re

from .core import ArenaError, ROOT


def load_dotenv(path: Path | None = None, environ=None):
    """Existing process variables win. Parse completely before applying changes."""
    path = path if path is not None else ROOT / '.env'
    environ = os.environ if environ is None else environ
    try:
        text = path.read_text(encoding='utf-8-sig')
    except FileNotFoundError:
        return
    except (OSError, UnicodeError):
        raise ArenaError('Cannot read .env as UTF-8') from None
    values = {}
    for number, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        match = re.fullmatch(r'(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)', line)
        if not match:
            raise ArenaError(f'Invalid .env assignment on line {number}; use NAME=value')
        name, value = match.groups()
        if value.startswith(('"', "'")):
            quote = value[0]
            # Quotes are literal; secrets containing backslashes or dollars stay intact.
            closing = value.find(quote, 1)
            if closing < 0 or (value[closing+1:].strip() and not value[closing+1:].strip().startswith('#')):
                raise ArenaError(f'Invalid .env quoted value on line {number}')
            value = value[1:closing]
        else:
            value = '' if value.startswith('#') else re.split(r'\s+#', value, maxsplit=1)[0].rstrip()
        if '\x00' in value:
            raise ArenaError(f'Invalid .env value on line {number}')
        values[name] = value
    for name, value in values.items():
        environ.setdefault(name, value)
