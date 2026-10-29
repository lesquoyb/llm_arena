"""Rebuildable SQLite projections of immutable fight records for overview reads."""
from contextlib import closing
import json
import sqlite3
import threading

from arena.core import ArenaError, is_link


class MatchIndex:
    def __init__(self, state):
        self.path=state/'match-index.sqlite'
        self.lock=threading.Lock()

    def read(self, root, paths, project):
        # This lock only serializes projection builders. Activity and journal
        # readers never acquire it; the authoritative artifacts are untouched.
        with self.lock, closing(sqlite3.connect(self.path,timeout=10)) as db:
            db.execute('PRAGMA journal_mode=WAL')
            db.execute('CREATE TABLE IF NOT EXISTS records (run TEXT, path TEXT, stamp TEXT, payload TEXT, PRIMARY KEY(run,path))')
            run=str(root)
            saved={name:(stamp,payload) for name,stamp,payload in db.execute('SELECT path,stamp,payload FROM records WHERE run=?',(run,))}
            updates=[];result={}
            for path in paths:
                if is_link(path):raise ArenaError('Links cannot be browsed')
                stat=path.stat()
                stamp=f'{stat.st_mtime_ns}:{stat.st_ctime_ns}:{stat.st_size}'
                name=path.relative_to(root).as_posix();cached=saved.get(name)
                if cached and cached[0]==stamp:
                    value=json.loads(cached[1])
                else:
                    value=project(path,'record')
                    payload=json.dumps(value,separators=(',',':'))
                    updates.append((run,name,stamp,payload))
                result[path]=value
            if updates:
                db.executemany('INSERT OR REPLACE INTO records VALUES (?,?,?,?)',updates)
                db.commit()
            return result
