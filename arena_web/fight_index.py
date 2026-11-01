"""Incremental SQLite projection of fight records for overview reads.

Fight artifacts stay authoritative and untouched. The index keeps one compact
row per record file and only re-reads a records directory when its own
modification time changes (records are always published by rename, which
updates the directory). Overviews then aggregate with SQL instead of loading
hundreds of thousands of JSON files into the browser.
"""
from __future__ import annotations

from contextlib import closing
import json
import os
from pathlib import Path, PureWindowsPath
import re
import sqlite3
import threading
import time

from arena.core import ArenaError

SCHEMA = 3
FULL_RESCAN_SECONDS = 300
LARGE_RUN = 20_000


def stages(root: Path):
    """Record directories in display order: (stage label, base directory)."""
    bases = [root, root / 'tournament', *sorted(root.glob('g*-tournament')),
             *sorted((root / 'evaluations').glob('g*-panel')), *sorted((root / 'evaluations').glob('g*-previous'))]
    return [(base.relative_to(root).as_posix(), base) for base in bases if (base / 'records').is_dir() or (base / 'fights.sqlite').is_file()]


def kind_of(stage: str) -> str:
    if stage == 'training':
        return 'training'
    if stage.endswith('-previous'):
        return 'progression'
    return 'evaluation' if stage.startswith('evaluations/') else 'competition'


def round_of(stage: str):
    match = re.search(r'g(\d+)-(?:tournament|panel|previous)$', stage)
    if match:
        return int(match.group(1))
    return 0 if stage in {'tournament', '.'} else None


def _safe_relative(name: str) -> str:
    parts = PureWindowsPath(name)
    if parts.anchor or '..' in parts.parts or ':' in name:
        raise ArenaError('Invalid fight artifact path')
    return name


def project(stage: str, base: Path, root: Path, record: dict) -> dict:
    """Compact, query-friendly view of one fight record."""
    result = record.get('result') or {}
    match = record.get('match') or {}
    sides = match.get('sides')
    if not sides:
        sides = [record.get('session'), record.get('opponent')]
        if record.get('side') == 1:
            sides.reverse()
    if 'directory' in record:
        work = (base / record['directory']).relative_to(root).as_posix()
    else:
        work = record.get('artifact_dir', '')
    _safe_relative(work)
    metrics = result.get('team_metrics') or {}
    side_metrics = [metrics.get(str(side)) or {} for side in (0, 1)]
    winner = result.get('winner_side')
    return {
        'work': work, 'a': sides[0], 'b': sides[1] if len(sides) > 1 else None,
        'candidate': record.get('session'), 'candidate_side': record.get('side'),
        'seed': match.get('seed', record.get('seed')), 'mirror': int(bool(match.get('mirror', False))),
        'status': result.get('status'), 'winner': winner if winner in (-1, 0, 1) else None,
        'turns': result.get('turns'), 'elapsed': result.get('elapsed_seconds'),
        'ops_a': side_metrics[0].get('operations'), 'ops_b': side_metrics[1].get('operations'),
        'errors_a': side_metrics[0].get('errors', 0), 'errors_b': side_metrics[1].get('errors', 0),
        'limits_a': side_metrics[0].get('operation_limit_hits', 0), 'limits_b': side_metrics[1].get('operation_limit_hits', 0),
        'cache_hit': int(bool((result.get('reference_cache') or {}).get('hit'))),
        'timings': json.dumps(record['timings'], separators=(',', ':')) if record.get('timings') else None,
    }


ROW_COLUMNS = ('rowid', 'kind', 'stage', 'mirror', 'a', 'b', 'candidate', 'candidate_side', 'seed', 'status', 'winner', 'turns',
               'elapsed', 'errors_a', 'errors_b', 'limits_a', 'limits_b', 'cache_hit', 'modified')
COLUMNS = ('work', 'a', 'b', 'candidate', 'candidate_side', 'seed', 'mirror', 'status', 'winner', 'turns', 'elapsed',
           'ops_a', 'ops_b', 'errors_a', 'errors_b', 'limits_a', 'limits_b', 'cache_hit', 'timings')


class FightIndex:
    def __init__(self, state: Path):
        self.path = state / 'fight-index.sqlite'
        self.locks = {}
        self.guard = threading.Lock()
        self.versions = {}
        self.checked = {}
        self.progress = {}
        self.group_cache = {}
        self.row_cache = {}
        with closing(self.connect()) as db:
            version = db.execute('PRAGMA user_version').fetchone()[0]
            if version != SCHEMA:
                for table in ('fights', 'directories', 'training_dirs'):
                    db.execute(f'DROP TABLE IF EXISTS {table}')
            db.execute('CREATE TABLE IF NOT EXISTS directories (run TEXT, stage TEXT, stamp TEXT, PRIMARY KEY(run,stage))')
            db.execute('CREATE TABLE IF NOT EXISTS training_dirs (run TEXT, path TEXT, stamp TEXT, PRIMARY KEY(run,path))')
            db.execute('CREATE TABLE IF NOT EXISTS fights (run TEXT, stage TEXT, kind TEXT, round INTEGER, name TEXT, stamp TEXT, '
                       + ', '.join(f'{column} {"INTEGER" if column in {"candidate_side","mirror","winner","turns","ops_a","ops_b","errors_a","errors_b","limits_a","limits_b","cache_hit"} else "REAL" if column=="elapsed" else "TEXT"}' for column in COLUMNS)
                       + ', modified REAL, PRIMARY KEY(run,stage,name))')
            db.execute('CREATE INDEX IF NOT EXISTS fights_run_kind ON fights(run,kind,stage)')
            db.execute('CREATE INDEX IF NOT EXISTS fights_run_stage ON fights(run,stage)')
            db.execute(f'PRAGMA user_version={SCHEMA}')
            db.commit()

    def connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.execute('PRAGMA journal_mode=WAL')
        db.execute('PRAGMA synchronous=NORMAL')
        return db

    def lock(self, run):
        with self.guard:
            return self.locks.setdefault(run, threading.Lock())

    def version(self, root: Path):
        """Per-process change token, after synchronising the run."""
        self.sync(root)
        progress = self.progress.get(str(root))
        return [self.versions.get(str(root), 0), progress and progress.get('stages_done')]

    def indexing(self, root: Path):
        """Progress of a running scan, or None when the index is current."""
        return self.progress.get(str(root))

    def warm(self, roots):
        """Build missing indexes in the background, most recent runs first."""
        def work():
            for root in roots:
                try:self.sync(root, wait=True)
                except (OSError, sqlite3.Error, ArenaError):pass
        threading.Thread(target=work, name='arena-fight-index', daemon=True).start()

    def sync(self, root: Path, *, force=False, wait=False):
        run = str(root)
        lock = self.lock(run)
        if not wait and run not in self.versions and not lock.locked() and self._large_unindexed(root):
            # A first scan of a large competition can take minutes on a cold
            # disk. Build it in the background; pages read the rows committed
            # so far and report the progress.
            self.progress.setdefault(run, {'stage': None, 'stages_done': 0, 'stages': len(stages(root))})
            threading.Thread(target=self.sync, args=(root,), kwargs={'wait': True}, name='arena-fight-index', daemon=True).start()
            return
        if not lock.acquire(blocking=wait or run not in self.progress):
            return
        try:
            self._sync(root, run, force)
        finally:
            lock.release()

    def _large_unindexed(self, root):
        with closing(self.connect()) as db:
            if db.execute('SELECT 1 FROM directories WHERE run=? LIMIT 1', (str(root),)).fetchone():
                return False
        total = 0
        for _, base in stages(root):
            with os.scandir(base / 'records') as entries:
                for _ in entries:
                    total += 1
                    if total > LARGE_RUN:
                        return True
        return False

    def _sync(self, root, run, force):
        full = force or time.monotonic() - self.checked.get(('full', run), -1e9) > FULL_RESCAN_SECONDS
        changed = False
        with closing(self.connect()) as db:
            saved = dict(db.execute('SELECT stage,stamp FROM directories WHERE run=?', (run,)))
            present = set()
            found = stages(root)
            for number, (stage, base) in enumerate(found):
                present.add(stage)
                records = base / 'records'
                from arena.fight_store import FightStore
                store = FightStore.at(base)
                stat = records.stat() if records.is_dir() else None
                seq = store.last_seq() if store else 0
                stamp = f'{stat.st_mtime_ns if stat else 0}:{stat.st_size if stat else 0}:{seq}'
                if not full and saved.get(stage) == stamp:
                    continue
                if saved.get(stage) is None:
                    self.progress[run] = {'stage': stage, 'stages_done': number, 'stages': len(found)}
                if stat is not None:
                    changed |= self._scan(db, run, stage, base, root, records)
                if store is not None:
                    changed |= self._scan_store(db, run, stage, base, root, store)
                db.execute('INSERT OR REPLACE INTO directories VALUES (?,?,?)', (run, stage, stamp))
                db.commit()
            for stage in set(saved) - present:
                db.execute('DELETE FROM fights WHERE run=? AND stage=?', (run, stage))
                db.execute('DELETE FROM directories WHERE run=? AND stage=?', (run, stage))
                changed = True
            # Record folders cost one stat each. Preparation tests need a tree
            # walk: when it is slow, live pages reuse it for a few seconds.
            if full or time.monotonic() >= self.checked.get(('training', run), -1e9):
                started = time.monotonic()
                changed |= self._scan_training(db, run, root, full)
                elapsed = time.monotonic() - started
                self.checked[('training', run)] = time.monotonic() + (15 if elapsed > .2 else 0)
            db.commit()
        self.progress.pop(run, None)
        if changed or run not in self.versions:
            self.versions[run] = self.versions.get(run, 0) + 1
        self.checked[run] = time.monotonic()
        if full:
            self.checked[('full', run)] = time.monotonic()

    def _scan(self, db, run, stage, base, root, records):
        # Rows indexed from a fight store carry a 'sha:' stamp; they are not files.
        known = dict(db.execute("SELECT name,stamp FROM fights WHERE run=? AND stage=? AND stamp NOT LIKE 'sha:%'", (run, stage)))
        seen = set();updates = []
        with os.scandir(records) as entries:
            for entry in entries:
                if not entry.name.endswith('.json') or not entry.is_file(follow_symlinks=False):
                    continue
                stat = entry.stat(follow_symlinks=False)
                stamp = f'{stat.st_mtime_ns}:{stat.st_size}'
                seen.add(entry.name)
                if known.get(entry.name) == stamp:
                    continue
                try:
                    with open(entry.path, 'rb') as stream:
                        record = json.loads(stream.read())
                except (OSError, ValueError):
                    continue  # A record replaced mid-read is picked up by the next scan.
                row = project(stage, base, root, record)
                updates.append((run, stage, kind_of(stage), round_of(stage), entry.name, stamp,
                                *(row[column] for column in COLUMNS), stat.st_mtime))
        removed = [(run, stage, name) for name in set(known) - seen]
        if updates:
            db.executemany(f'INSERT OR REPLACE INTO fights VALUES ({",".join("?" * (6 + len(COLUMNS) + 1))})', updates)
        if removed:
            db.executemany('DELETE FROM fights WHERE run=? AND stage=? AND name=?', removed)
        return bool(updates or removed)

    def _scan_store(self, db, run, stage, base, root, store):
        """Records published to the stage's fight store since the last scan."""
        db.execute('CREATE TABLE IF NOT EXISTS store_seq (run TEXT, stage TEXT, seq INTEGER, PRIMARY KEY(run,stage))')
        row = db.execute('SELECT seq FROM store_seq WHERE run=? AND stage=?', (run, stage)).fetchone()
        after = row[0] if row else 0
        updates = [];last = after
        for seq, path, sha, modified in store.changes(after, 'records'):
            last = max(last, seq)
            try:
                record = json.loads(store.blob(sha))
            except (ValueError, ArenaError):
                continue
            projected = project(stage, base, root, record)
            updates.append((run, stage, kind_of(stage), round_of(stage), Path(path).name, 'sha:' + sha,
                            *(projected[column] for column in COLUMNS), modified))
        if updates:
            db.executemany(f'INSERT OR REPLACE INTO fights VALUES ({",".join("?" * (6 + len(COLUMNS) + 1))})', updates)
        db.execute('INSERT OR REPLACE INTO store_seq VALUES (?,?,?)', (run, stage, last))
        return bool(updates)

    def _scan_training(self, db, run, root, full):
        """Preparation tests: sessions/<sid>/tools/<call>/**/result.json next to scenario.json."""
        sessions = root / 'sessions'
        if not sessions.is_dir():
            return False
        saved = dict(db.execute('SELECT path,stamp FROM training_dirs WHERE run=?', (run,)))
        changed = False;stamps = {}
        def stamp_of(path):
            try:
                stat = os.stat(path)
            except FileNotFoundError:
                return None
            return f'{stat.st_mtime_ns}:{stat.st_size}'
        def walk(directory: Path, depth: int):
            nonlocal changed
            key = directory.relative_to(root).as_posix()
            stamp = stamp_of(directory)
            stamps[key] = stamp
            unchanged = not full and saved.get(key) == stamp
            try:
                entries = list(os.scandir(directory))
            except FileNotFoundError:
                return
            names = {entry.name for entry in entries}
            if 'result.json' in names and 'scenario.json' in names and not unchanged:
                changed |= self._training_row(db, run, root, directory)
            if depth >= 4:
                return
            for entry in entries:
                if entry.is_dir(follow_symlinks=False) and entry.name not in {'strategies', 'data', 'ai'}:
                    child = Path(entry.path)
                    # Unchanged leaf directories have no new results; still visit
                    # call directories whose own subdirectories may have changed.
                    walk(child, depth + 1)
        with os.scandir(sessions) as entries:
            for session in entries:
                tools = Path(session.path) / 'tools'
                if session.is_dir(follow_symlinks=False) and tools.is_dir():
                    walk(tools, 0)
        if stamps != saved:
            db.execute('DELETE FROM training_dirs WHERE run=?', (run,))
            db.executemany('INSERT INTO training_dirs VALUES (?,?,?)', [(run, key, value) for key, value in stamps.items() if value])
        return changed

    def _training_row(self, db, run, root, directory: Path):
        result_path = directory / 'result.json'
        try:
            result = json.loads(result_path.read_bytes())
            scenario = json.loads((directory / 'scenario.json').read_bytes())
        except (OSError, ValueError):
            return False
        try:
            cached = json.loads((directory.parent / 'cached.json').read_bytes())
        except (OSError, ValueError):
            cached = {}
        relative = directory.relative_to(root)
        sid = relative.parts[1]
        opponent = 'Own script: ' + cached['opponent_entrypoint'] if cached.get('opponent_entrypoint') else 'passive'
        sides = [opponent, sid] if 'side-1' in relative.as_posix() else [sid, opponent]
        name = relative.as_posix()
        metrics = result.get('team_metrics') or {}
        side_metrics = [metrics.get(str(side)) or {} for side in (0, 1)]
        winner = result.get('winner_side')
        row = {'work': name, 'a': sides[0], 'b': sides[1], 'candidate': None, 'candidate_side': None,
               'seed': scenario.get('random_seed'), 'mirror': 0, 'status': result.get('status'),
               'winner': winner if winner in (-1, 0, 1) else None, 'turns': result.get('turns'),
               'elapsed': result.get('elapsed_seconds'),
               'ops_a': side_metrics[0].get('operations'), 'ops_b': side_metrics[1].get('operations'),
               'errors_a': side_metrics[0].get('errors', 0), 'errors_b': side_metrics[1].get('errors', 0),
               'limits_a': side_metrics[0].get('operation_limit_hits', 0), 'limits_b': side_metrics[1].get('operation_limit_hits', 0),
               'cache_hit': 0, 'timings': None}
        stat = result_path.stat()
        db.execute(f'INSERT OR REPLACE INTO fights VALUES ({",".join("?" * (6 + len(COLUMNS) + 1))})',
                   (run, 'training', 'training', None, name, f'{stat.st_mtime_ns}:{stat.st_size}',
                    *(row[column] for column in COLUMNS), stat.st_mtime))
        return True

    def stage_rows(self, root: Path):
        """Compact rows of every record stage (ROW_COLUMNS), cached per unchanged stage.

        Overviews filter these in memory instead of re-reading SQLite for each
        request; only the stage being written by a live run is reloaded."""
        import sys
        self.sync(root)
        run = str(root)
        with closing(self.connect()) as db:
            stamps = dict(db.execute('SELECT stage,stamp FROM directories WHERE run=?', (run,)))
            cache = self.row_cache.setdefault(run, {})
            for stage in set(cache) - set(stamps):
                cache.pop(stage)
            rows = []
            for stage, stamp in sorted(stamps.items()):
                saved = cache.get(stage)
                if saved is None or saved[0] != stamp:
                    fetched = db.execute(f'SELECT {",".join(ROW_COLUMNS)} FROM fights WHERE run=? AND stage=? ORDER BY name', (run, stage)).fetchall()
                    intern = lambda value: sys.intern(value) if isinstance(value, str) else value
                    saved = cache[stage] = (stamp, [tuple(intern(value) for value in row) for row in fetched])
                rows.extend(saved[1])
            return rows

    def details(self, root: Path, rowids):
        """Artifact paths and timings for a page of rows."""
        rowids = list(rowids)
        result = {}
        with closing(self.connect()) as db:
            for start in range(0, len(rowids), 500):
                chunk = rowids[start:start + 500]
                result.update((rowid, (work, timings)) for rowid, work, timings in
                              db.execute(f'SELECT rowid,work,timings FROM fights WHERE rowid IN ({",".join("?" * len(chunk))})', chunk))
        return result

    def stage_groups(self, root: Path):
        """Grouped outcome counts, recomputed only for stages whose records changed."""
        self.sync(root)
        run = str(root)
        with closing(self.connect()) as db:
            stamps = dict(db.execute('SELECT stage,stamp FROM directories WHERE run=?', (run,)))
            cache = self.group_cache.setdefault(run, {})
            for stage in set(cache) - set(stamps):
                cache.pop(stage)
            rows = []
            for stage, stamp in sorted(stamps.items()):
                saved = cache.get(stage)
                if saved is None or saved[0] != stamp:
                    grouped = db.execute('SELECT kind,stage,mirror,a,b,candidate,candidate_side,status,winner,count(*),'
                                         'coalesce(sum(cache_hit),0),max(modified) FROM fights WHERE run=? AND stage=? '
                                         'GROUP BY mirror,a,b,candidate,candidate_side,status,winner', (run, stage)).fetchall()
                    saved = cache[stage] = (stamp, grouped)
                rows.extend(saved[1])
            return rows

    def query(self, root: Path, sql: str, parameters=()):
        self.sync(root)
        with closing(self.connect()) as db:
            return db.execute(sql, (str(root), *parameters)).fetchall()
