"""Persistent projections of journal-referenced artifacts, keyed by content hash.

The journal stores each artifact's SHA-256. A small projection computed from
verified bytes therefore stays valid for those bytes forever, across server
restarts, and pages no longer reread thousands of model responses.
"""
from __future__ import annotations

from contextlib import closing
import hashlib
import json
import sqlite3
import threading

from arena.core import ArenaError


class ReceiptCache:
    def __init__(self, state):
        self.path = state / 'receipt-cache.sqlite'
        self.lock = threading.Lock()
        self.memory = {}
        with closing(self.connect()) as db:
            db.execute('CREATE TABLE IF NOT EXISTS receipts (sha256 TEXT, projection TEXT, value TEXT, PRIMARY KEY(sha256,projection))')
            db.commit()

    def connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.execute('PRAGMA journal_mode=WAL')
        db.execute('PRAGMA synchronous=NORMAL')
        return db

    def many(self, projection, references, project):
        """references: iterable of (sha256, path or zero-argument path factory)."""
        references = list(references)
        with self.lock:
            result = {sha: self.memory[(sha, projection)] for sha, _ in references if (sha, projection) in self.memory}
        wanted = {sha for sha, _ in references if sha not in result}
        if wanted:
            with closing(self.connect()) as db:
                found = {}
                hashes = list(wanted)
                for start in range(0, len(hashes), 500):
                    chunk = hashes[start:start + 500]
                    found.update(db.execute(f'SELECT sha256,value FROM receipts WHERE projection=? AND sha256 IN ({",".join("?" * len(chunk))})',
                                            (projection, *chunk)).fetchall())
                missing = [(sha, path) for sha, path in references if sha in wanted and sha not in found]
                inserts = []
                for sha, path in dict(missing).items():
                    path = path() if callable(path) else path
                    raw = path.read_bytes()
                    if hashlib.sha256(raw).hexdigest() != sha:
                        raise ArenaError('An artifact no longer matches its journal hash: ' + path.name)
                    value = json.dumps(project(json.loads(raw)), separators=(',', ':'))
                    found[sha] = value
                    inserts.append((sha, projection, value))
                if inserts:
                    db.executemany('INSERT OR REPLACE INTO receipts VALUES (?,?,?)', inserts)
                    db.commit()
            with self.lock:
                for sha, value in found.items():
                    result[sha] = self.memory[(sha, projection)] = json.loads(value)
                while len(self.memory) > 50_000:
                    self.memory.pop(next(iter(self.memory)))
        return result
