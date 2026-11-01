"""Disk usage report and compaction of fight folders into per-stage SQLite stores.

``python -m arena storage report <run>`` shows where space goes.
``python -m arena storage compact <run>`` moves fight records and artifacts
into ``fights.sqlite`` (compressed, deduplicated), checks every stored file
against the original bytes, then deletes the folders. Engine data copies left
in old fight folders are scratch inputs, not results: they are removed.
The run must be stopped: compaction takes the experiment lock.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil

from .core import ArenaError
from .fight_store import FightStore


def stage_directories(run: Path):
    stages = [run / 'tournament', *sorted(run.glob('g*-tournament')), *sorted((run / 'evaluations').glob('g*-*'))]
    if (run / 'records').is_dir() and (run / 'experiment.json').is_file():
        stages.insert(0, run)  # CLI tournament: the run itself is the stage.
    return [stage for stage in stages if (stage / 'records').is_dir() or (stage / 'matches').is_dir()]


def usage(path: Path):
    files = size = 0
    for base, dirs, names in os.walk(path):
        for name in names:
            try:
                size += os.stat(os.path.join(base, name)).st_size
                files += 1
            except OSError:
                pass
    return files, size


def report(run: Path):
    rows = []
    for stage in stage_directories(run):
        for part in ('records', 'matches'):
            files, size = usage(stage / part)
            rows.append((stage.relative_to(run).as_posix() + '/' + part, files, size))
        store = stage / 'fights.sqlite'
        if store.is_file():
            rows.append((store.relative_to(run).as_posix(), 1, store.stat().st_size))
    for name in ('artifacts', '.verification-cache.sqlite', 'journal.sqlite'):
        path = run / name
        if path.is_dir():
            files, size = usage(path)
        elif path.is_file():
            files, size = 1, path.stat().st_size
        else:
            continue
        rows.append((name, files, size))
    return rows


def _batched(stage: Path, folder: str, skip_data: bool, size=2000):
    batch = []
    root = stage / folder
    for base, dirs, names in os.walk(root):
        if skip_data:
            # Engine inputs copied next to old fights are not artifacts.
            dirs[:] = [d for d in dirs if not (d == 'data' and (Path(base) / 'scenario.json').is_file())]
        for name in names:
            path = Path(base) / name
            batch.append((path.relative_to(stage).as_posix(), path))
            if len(batch) >= size:
                yield batch
                batch = []
    if batch:
        yield batch


def compact_stage(stage: Path, *, delete=True, progress=None):
    store = FightStore.at(stage, create=True)
    stored = 0
    for folder in ('records', 'matches'):
        if not (stage / folder).is_dir():
            continue
        for batch in _batched(stage, folder, skip_data=folder == 'matches'):
            items = [(name, path.read_bytes()) for name, path in batch]
            store.put_many(items)
            for name, content in items:
                if store.sha256(name) != hashlib.sha256(content).hexdigest():
                    raise ArenaError('Compaction check failed for ' + name)
            stored += len(items)
            if progress:
                progress(stage, stored)
    if delete:
        for folder in ('records', 'matches'):
            shutil.rmtree(stage / folder, ignore_errors=True)
    from .fight_store import release
    release(stage)
    return stored


def prune_verification_cache(run: Path):
    """Drop derived fingerprints of the deleted fight files; keep journal proofs."""
    import sqlite3
    from contextlib import closing
    stages = stage_directories(run) + [stage for stage in [run / 'tournament', *run.glob('g*-tournament'), *(run / 'evaluations').glob('g*-*')] if (stage / 'fights.sqlite').is_file()]
    for stage in set(stages):
        if stage != run:
            (stage / '.verification-cache.sqlite').unlink(missing_ok=True)
    cache = run / '.verification-cache.sqlite'
    if not cache.is_file():
        return
    prefixes = sorted({stage.relative_to(run).as_posix() + '/' for stage in stages if stage != run})
    with closing(sqlite3.connect(cache)) as db:
        with db:
            for prefix in prefixes:
                db.execute('DELETE FROM verification_entries WHERE path >= ? AND path < ?', (prefix, prefix + '￿'))
        db.execute('VACUUM')


def compact(run: Path, *, delete=True, progress=None):
    from .experiment import experiment_lock
    run = run.resolve()
    if not (run / 'experiment.json').is_file():
        raise ArenaError('Not a competition folder: ' + str(run))
    before = sum(size for _, _, size in report(run))
    with experiment_lock(run):
        total = sum(compact_stage(stage, delete=delete, progress=progress) for stage in stage_directories(run))
        if delete:
            prune_verification_cache(run)
    after = sum(size for _, _, size in report(run))
    return {'files_stored': total, 'bytes_before': before, 'bytes_after': after}


def status(run: Path):
    """Cheap storage summary for the interface: no walk over fight folders."""
    stages = []
    for stage in stage_directories(run) + [s for s in [run / 'tournament', *run.glob('g*-tournament'), *(run / 'evaluations').glob('g*-*')] if (s / 'fights.sqlite').is_file()]:
        if any(row['stage'] == stage.relative_to(run).as_posix() for row in stages):
            continue
        store = stage / 'fights.sqlite'
        stages.append({'stage': stage.relative_to(run).as_posix(), 'legacy_folders': (stage / 'matches').is_dir() or (stage / 'records').is_dir(),
                       'store_bytes': store.stat().st_size if store.is_file() else 0})
    return {'stages': stages, 'needs_compaction': any(row['legacy_folders'] for row in stages)}
