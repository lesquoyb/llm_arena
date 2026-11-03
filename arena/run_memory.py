"""Per-process memory of verified fight work, shared by every journal of a run.

The conversation coordinator and the independent fight coordinator each open
their own Journal (SQLite connections stay with their thread). Verification
memos must not be per journal: otherwise each thread re-verifies every record
the other one already checked, which made round ends re-audit earlier rounds.
"""
from pathlib import Path
import threading

_runs = {}
_lock = threading.Lock()


def shared(out, name, factory=dict):
    key = str(Path(out).resolve())
    with _lock:
        values = _runs.setdefault(key, {})
        if name not in values:
            values[name] = factory()
        return values[name]


def reset(out, name, value):
    key = str(Path(out).resolve())
    with _lock:
        _runs.setdefault(key, {})[name] = value
    return value


def forget(out):
    with _lock:
        _runs.pop(str(Path(out).resolve()), None)
