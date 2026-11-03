"""Versioned, trial-local authoring documents; engine catalogs remain immutable."""
from .core import ROOT, ArenaError


def originals():
    files=[ROOT/'docs/authoring.md', *sorted((ROOT/'docs/corpus').rglob('*.md'))]
    return {path.relative_to(ROOT/'docs').as_posix():path.read_text(encoding='utf-8') for path in files}


def validate(documents):
    if not isinstance(documents,dict):
        raise ArenaError('reference_documents must map document paths to complete text')
    allowed=originals()
    for path,text in documents.items():
        if path not in allowed or not isinstance(text,str) or not text.strip():
            raise ArenaError('Only existing authoring/tutorial Markdown documents can be edited: '+str(path))
    if sum(len(text) for text in documents.values()) > 500000:
        raise ArenaError('Reference documents exceed 500000 characters')
    return documents


def effective(config):
    return {**originals(),**validate(config.get('reference_documents',{}))}
