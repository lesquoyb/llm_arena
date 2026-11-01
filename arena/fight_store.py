"""Fight artifacts in one SQLite file per stage instead of a folder per fight.

A stage directory (``tournament``, ``g2-tournament``, ``evaluations/g1-panel``)
used to hold ``records/<id>.json`` plus ``matches/<id>/attempt-N/`` with eight to
sixteen small files per fight. On NTFS each file costs at least one cluster,
and every open pays antivirus scanning: hundreds of thousands of fights meant
tens of gigabytes and minutes of I/O for every overview or resume.

The store keeps the same relative paths, so records and their artifact
references are unchanged, but:

* contents live in ``blobs`` keyed by SHA-256 of the exact bytes, compressed
  with zlib and deduplicated (sources, scenarios and empty logs repeat a lot);
* ``files`` maps each relative path to its content hash;
* reading a blob checks that its bytes still hash to that key, so integrity
  checks no longer need a separate derived cache.

Files that already exist on disk stay readable (legacy runs, or runs not yet
compacted with ``python -m arena storage compact``).
"""
from __future__ import annotations

from contextlib import closing
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import sqlite3
import threading
import time
import zlib

from .core import ArenaError

NAME = 'fights.sqlite'
SCHEMA = 1
_stores = {}
_stores_lock = threading.Lock()


def _relative(name) -> str:
    value = PurePosixPath(str(name).replace('\\', '/'))
    if value.is_absolute() or '..' in value.parts or not value.parts or ':' in str(value):
        raise ArenaError('Invalid stored artifact path: ' + str(name))
    return value.as_posix()


class FightStore:
    """Artifact store rooted at one stage directory. Thread-safe."""

    @classmethod
    def at(cls, directory, *, create=False):
        """The store of a stage directory, or None if it has none and create is False."""
        directory = Path(directory).resolve()
        key = str(directory)
        with _stores_lock:
            store = _stores.get(key)
            if store is None:
                if not create and not (directory / NAME).is_file():
                    return None
                store = cls(directory)
                _stores[key] = store
            return store

    def __init__(self, directory: Path):
        self.root = Path(directory)
        self.path = self.root / NAME
        # One connection per store, shared by engine threads under a lock:
        # SQLite work per fight is tiny, and a single handle can be closed
        # deterministically (Windows cannot delete a folder with open files).
        self.lock = threading.RLock()
        self._db = None
        self.verified = set()
        self.root.mkdir(parents=True, exist_ok=True)
        with closing(self._open()) as db:
            version = db.execute('PRAGMA user_version').fetchone()[0]
            if version not in (0, SCHEMA):
                raise ArenaError('Unsupported fight store version')
            db.execute('CREATE TABLE IF NOT EXISTS blobs (sha256 TEXT PRIMARY KEY, size INTEGER NOT NULL, data BLOB NOT NULL)')
            # seq orders changes for incremental readers (overview index).
            db.execute('CREATE TABLE IF NOT EXISTS files (path TEXT PRIMARY KEY, sha256 TEXT NOT NULL, modified REAL NOT NULL, seq INTEGER NOT NULL)')
            db.execute('CREATE INDEX IF NOT EXISTS files_seq ON files(seq)')
            if version != SCHEMA:
                db.execute(f'PRAGMA user_version={SCHEMA}')
            db.commit()

    def _open(self):
        db = sqlite3.connect(self.path, timeout=60, check_same_thread=False)
        db.execute('PRAGMA journal_mode=WAL')
        db.execute('PRAGMA synchronous=NORMAL')
        return db

    @property
    def db(self):
        if self._db is None:
            self._db = self._open()
        return self._db

    def close(self):
        with self.lock:
            if self._db is not None:
                self._db.close()
                self._db = None

    # Writing -------------------------------------------------------------
    def put_many(self, items):
        """items: iterable of (relative path, bytes). One transaction."""
        rows = [(_relative(name), bytes(content)) for name, content in items]
        if not rows:
            return
        now = time.time()
        with self.lock:
            db = self.db
            with db:
                seq = db.execute('SELECT coalesce(max(seq),0) FROM files').fetchone()[0]
                for name, content in rows:
                    sha = hashlib.sha256(content).hexdigest()
                    db.execute('INSERT OR IGNORE INTO blobs VALUES (?,?,?)', (sha, len(content), zlib.compress(content, 6)))
                    seq += 1
                    db.execute('INSERT OR REPLACE INTO files VALUES (?,?,?,?)', (name, sha, now, seq))

    def put(self, name, content: bytes):
        self.put_many([(name, content)])

    def put_json(self, name, value):
        """Same bytes as core.write_json, so hashes match legacy files."""
        self.put(name, (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))

    def ingest(self, name, directory: Path, *, remove=True):
        """Store every file below a scratch directory under ``name``/..."""
        prefix = _relative(name)
        items = []
        for base, dirs, files in os.walk(directory):
            for file in files:
                path = Path(base) / file
                items.append((prefix + '/' + path.relative_to(directory).as_posix(), path.read_bytes()))
        self.put_many(items)
        if remove:
            shutil.rmtree(directory, ignore_errors=True)
        return len(items)

    def delete_prefix(self, name):
        prefix = _relative(name) + '/'
        with self.lock:
            with self.db:
                self.db.execute('DELETE FROM files WHERE path >= ? AND path < ?', (prefix, prefix + '￿'))

    # Reading -------------------------------------------------------------
    def sha256(self, name):
        with self.lock:
            row = self.db.execute('SELECT sha256 FROM files WHERE path=?', (_relative(name),)).fetchone()
        return row[0] if row else None

    def exists(self, name):
        return self.sha256(name) is not None

    def get(self, name):
        sha = self.sha256(name)
        return None if sha is None else self.blob(sha)

    def blob(self, sha):
        with self.lock:
            row = self.db.execute('SELECT data FROM blobs WHERE sha256=?', (sha,)).fetchone()
        if row is None:
            raise ArenaError('Stored artifact content is missing: ' + sha)
        content = zlib.decompress(row[0])
        if sha not in self.verified:
            if hashlib.sha256(content).hexdigest() != sha:
                raise ArenaError('Stored artifact content was modified: ' + sha)
            self.verified.add(sha)
        return content

    def get_json(self, name):
        content = self.get(name)
        return None if content is None else json.loads(content)

    def list(self, prefix):
        """Relative paths directly or indirectly below prefix."""
        prefix = _relative(prefix) + '/'
        with self.lock:
            return [row[0] for row in self.db.execute('SELECT path FROM files WHERE path >= ? AND path < ? ORDER BY path', (prefix, prefix + '￿'))]

    def last_seq(self):
        with self.lock:
            return self.db.execute('SELECT coalesce(max(seq),0) FROM files').fetchone()[0]

    def changes(self, after=0, prefix=None):
        """(seq, path, sha256, modified) of entries changed after seq."""
        with self.lock:
            if prefix:
                prefix = _relative(prefix) + '/'
                return self.db.execute('SELECT seq,path,sha256,modified FROM files WHERE seq>? AND path >= ? AND path < ? ORDER BY seq',
                                       (after, prefix, prefix + '￿')).fetchall()
            return self.db.execute('SELECT seq,path,sha256,modified FROM files WHERE seq>? ORDER BY seq', (after,)).fetchall()

    def materialize(self, prefix, target: Path):
        """Write a stored folder (for example executed sources) to disk."""
        names = self.list(prefix)
        base = _relative(prefix) + '/'
        for name in names:
            path = target / name[len(base):]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(self.get(name))
        return len(names)


_stage_dirs = {}


def stage_of(path: Path):
    """(store, relative name) for a path inside a stage that has a store, else (None, None).

    Stores sit at most a few levels above an artifact (stage/matches/id/attempt/...).
    """
    path = Path(path).resolve()
    for depth, parent in enumerate(path.parents):
        if depth > 6:
            break
        key = str(parent)
        present = _stage_dirs.get(key)
        if present is None:
            present = (parent / NAME).is_file()
            if present:
                _stage_dirs[key] = True  # A store, once created, stays.
        if present:
            return FightStore.at(parent), path.relative_to(parent).as_posix()
    return None, None


def read_bytes(path: Path):
    """Artifact bytes from a fight store or, for legacy layouts, the file itself."""
    store, name = stage_of(path)
    if store is not None:
        content = store.get(name)
        if content is not None:
            return content
    return Path(path).read_bytes()


def read_json(path: Path):
    return json.loads(read_bytes(path))


def exists(path: Path):
    store, name = stage_of(path)
    if store is not None and store.exists(name):
        return True
    return Path(path).exists()


class scratch:
    """Temporary folder for one engine run; removed after its files are stored."""
    def __enter__(self):
        from uuid import uuid4
        from .core import STATE_ROOT
        self.path = STATE_ROOT / 'tmp' / 'fights' / uuid4().hex
        self.path.parent.mkdir(parents=True, exist_ok=True)
        return self.path

    def __exit__(self, *args):
        shutil.rmtree(self.path, ignore_errors=True)


def attempt_path(store, root: Path, base: Path):
    """Next free retry folder name, considering stored and legacy attempts."""
    index = 1
    candidate = base
    while candidate.exists() or (store is not None and store.list(candidate.relative_to(root).as_posix())):
        candidate = base.with_name(base.name + f'-retry-{index}')
        index += 1
    return candidate


SOURCE_SUFFIX = '.leek'


def stored_sources(store, prefix):
    """{relative name: sha256} of a stored submission folder, plus its byte size."""
    from .core import AUTOMATIC_ERROR_FILE
    base = _relative(prefix) + '/'
    with store.lock:
        rows = store.db.execute('SELECT f.path,f.sha256,b.size FROM files f JOIN blobs b ON b.sha256=f.sha256 WHERE f.path >= ? AND f.path < ?',
                            (base, base + '￿')).fetchall()
    hashes = {};size = 0
    for path, sha, length in rows:
        name = path[len(base):]
        if name.endswith(SOURCE_SUFFIX) or name in ('team.json', AUTOMATIC_ERROR_FILE):
            hashes[name] = sha
            if name != AUTOMATIC_ERROR_FILE:
                size += length
    return hashes, size


def verify_stored_fight(store, work, result, expected, scenario, scenario_hash, engine_accepted):
    """Same checks as the file-based verification, against stored bytes."""
    if store.sha256(work + '/outcome.json') != result.get('outcome_sha256'):
        raise ArenaError(f'Stored outcome was modified: {work}')
    if store.get_json(work + '/result.json') != result:
        raise ArenaError(f'Stored result was modified: {work}')
    provenance = store.get_json(work + '/provenance.json')
    if (not engine_accepted(provenance.get('engine')) or provenance.get('submissions') != expected
            or provenance.get('scenario_sha256') != scenario_hash or store.get_json(work + '/scenario.json') != scenario):
        raise ArenaError('Stored match provenance or scenario was modified')
    for side, info in enumerate(expected, 1):
        hashes, size = stored_sources(store, f'{work}/strategies/{side}')
        if hashes != info['files'] or size > 2_000_000:
            raise ArenaError(f'Frozen source was modified: {work}/strategies/{side}')



def stage_records(stage: Path):
    """(store, {key: (location, record)}): stored records override legacy files."""
    from .core import read_json as read_file
    store = FightStore.at(stage)
    result = {}
    for path in sorted((stage / 'records').glob('*.json')):
        result[path.stem] = (path, read_file(path))
    if store is not None:
        for name in store.list('records'):
            result[PurePosixPath(name).stem] = (name, store.get_json(name))
    return store, result


def stage_fingerprint(root):
    """Cheap identity of a stage's records: legacy record files (name, size,
    mtime) plus the store's last sequence number. Any new, retried or edited
    fight changes it, so a seal over it is invalidated."""
    from .core import digest
    root = Path(root)
    entries = []
    if (root / 'records').is_dir():
        with os.scandir(root / 'records') as items:
            for item in items:
                stat = item.stat(); entries.append((item.name, stat.st_size, stat.st_mtime_ns))
    store = FightStore.at(root) if (root / NAME).is_file() else None
    return digest({'files': sorted(entries), 'store': store.last_seq() if store else 0})


def release(directory):
    """Close and forget every store at or below a directory (before deleting it)."""
    directory = Path(directory).resolve()
    with _stores_lock:
        keys = [key for key in _stores if Path(key) == directory or Path(key).is_relative_to(directory)]
        stores = [_stores.pop(key) for key in keys]
    for key in keys:
        _stage_dirs.pop(key, None)
    for store in stores:
        store.close()
