"""Static size of a submitted LeekScript AI: the entrypoint and the files it includes.

Other files in the submission (for example a sparring opponent written for
preparation tests) are not part of the fighting AI and are not counted.
"""
from __future__ import annotations
import re
from pathlib import Path

_INCLUDE = re.compile(r'\binclude\s*\(\s*["\']([^"\']+)["\']\s*\)')
_FUNCTION = re.compile(r'^\s*function\s+\w+\s*\(', re.M)
_CLASS = re.compile(r'^\s*class\s+\w+', re.M)
_cache: dict[str, dict | None] = {}


def _strip_comments(source: str) -> str:
    """Remove // and /* */ comments while keeping string literals intact."""
    out, i, n = [], 0, len(source)
    while i < n:
        char = source[i]
        if char in '"\'':
            end = i + 1
            while end < n and source[end] != char:
                end += 2 if source[end] == '\\' else 1
            out.append(source[i:end + 1]); i = end + 1
        elif source.startswith('//', i):
            end = source.find('\n', i)
            i = n if end < 0 else end
        elif source.startswith('/*', i):
            end = source.find('*/', i + 2)
            out.append('\n' * source.count('\n', i, n if end < 0 else end))
            i = n if end < 0 else end + 2
        else:
            out.append(char); i += 1
    return ''.join(out)


def measure(directory: Path, entrypoint: str) -> dict | None:
    """Lines of code (non-blank, non-comment), functions, classes and files reachable from the entrypoint."""
    root = directory.resolve()
    pending, seen, totals = [entrypoint], set(), {'files': 0, 'lines': 0, 'functions': 0, 'classes': 0, 'characters': 0}
    while pending:
        name = pending.pop()
        path = (root / name).resolve()
        if path in seen or not path.is_relative_to(root) or not path.is_file():
            continue
        seen.add(path)
        try:
            source = path.read_text(encoding='utf-8', errors='replace')
        except OSError:
            continue
        code = _strip_comments(source)
        totals['files'] += 1
        totals['lines'] += sum(1 for line in code.splitlines() if line.strip())
        totals['functions'] += len(_FUNCTION.findall(code))
        totals['classes'] += len(_CLASS.findall(code))
        totals['characters'] += len(source)
        pending.extend(_INCLUDE.findall(code))
    return totals if totals['files'] else None


def submission_metrics(session_directory: Path, submission: dict | None) -> dict | None:
    """Cached by submission hash: submitted files are immutable."""
    if not submission or not submission.get('entrypoint'):
        return None
    key = submission.get('sha256') or ''
    if key and key in _cache:
        return _cache[key]
    value = measure(session_directory / 'submission', submission['entrypoint'])
    if key and value is not None:
        _cache[key] = value
    return value
