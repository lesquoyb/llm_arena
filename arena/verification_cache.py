"""Derived SHA-256 cache guarded by file identity and filesystem change stamps."""
import os
import json
import hashlib
from pathlib import Path
import sqlite3
import stat
import threading
from functools import lru_cache
import time
from contextlib import closing
from .core import ArenaError, file_hash,digest
from .sqlite_metrics import connect


@lru_cache(maxsize=1)
def _windows_api():
    import ctypes
    from ctypes import wintypes
    class BasicInfo(ctypes.Structure):
        _fields_=[(name,ctypes.c_longlong) for name in ('created','accessed','written','changed')]+[('attributes',wintypes.DWORD)]
    kernel=ctypes.windll.kernel32
    create=kernel.CreateFileW
    create.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE]
    create.restype=wintypes.HANDLE
    query=kernel.GetFileInformationByHandleEx
    query.argtypes=[wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD]
    close=kernel.CloseHandle;close.argtypes=[wintypes.HANDLE]
    return ctypes,BasicInfo,create,query,close


def _windows_change_time(path):
    ctypes,BasicInfo,create,query,close=_windows_api()
    handle=create(str(path),0x80,7,None,3,0x02200000,None)
    if handle==ctypes.c_void_p(-1).value:raise OSError('File change stamp unavailable')
    try:
        value=BasicInfo()
        if not query(handle,0,ctypes.byref(value),ctypes.sizeof(value)):raise OSError('File change stamp unavailable')
        return value.changed
    finally:close(handle)


def fingerprint(path, directory=False):
    value=path.stat(follow_symlinks=False)
    if not (stat.S_ISREG(value.st_mode) or (directory and stat.S_ISDIR(value.st_mode))):raise ArenaError('Verified artifact must be a regular file: '+str(path))
    try:changed=_windows_change_time(path) if os.name=='nt' else value.st_ctime_ns
    except (OSError,AttributeError):return None
    if not value.st_ino or not changed:return None
    return (value.st_dev,value.st_ino,value.st_size,value.st_mtime_ns,changed)


class VerificationCache:
    def __init__(self, root):
        self.root=Path(root).absolute();self.path=self.root/'.verification-cache.sqlite'
        self.entries={};self.dirty={};self.records={};self.sessions={};self.dirty_sessions={};self._record_reads={};self.dirty_records={};self.receipts={};self.dirty_receipts={};self.receipt_hits=0;self.record_hits=0;self.session_hits=0;self.lock=threading.Lock();self.hits=0;self.misses=0;self.bytes_read=0;self.errors=0;self.last_flush=0
        self.force=os.environ.get('ARENA_FULL_AUDIT')=='1';self._discard=False
        self.engines={};self.dirty_engines={}
        if self.path.is_file() and not self.path.is_symlink():
            try:
                with closing(connect(self.path.as_uri()+'?mode=ro',uri=True,timeout=2)) as db:
                    tables={row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                    if 'verification_entries' not in tables:return
                    for kind,name,raw,seal in db.execute('SELECT kind,path,payload,sha256 FROM verification_entries'):
                        if hashlib.sha256((kind+'\0'+name+'\0'+raw).encode()).hexdigest()!=seal:raise ValueError('Derived cache checksum mismatch')
                        value=json.loads(raw)
                        if kind=='hash':self.entries[name]=(tuple(value[0]),value[1])
                        elif kind=='record':self.records[name]=(tuple(value[0]),value[1])
                        elif kind=='session':self.sessions[name]=tuple(value)
                        elif kind=='receipt':self.receipts[name]=(value[0],[(path,tuple(stamp)) for path,stamp in value[1]],*value[2:])
                        elif kind=='engine':
                            if digest(value)!=name:raise ValueError('Derived engine binding mismatch')
                            self.engines[name]=value
                        else:raise ValueError('Unknown derived cache entry')
            except (sqlite3.Error,OSError,ValueError,TypeError,IndexError,AttributeError):
                self.entries.clear();self.records.clear();self.receipts.clear();self.sessions.clear()
                self.engines.clear()
                self.errors+=1;self._discard=True

    def hash(self, path):
        path=Path(path).absolute()
        try:name=path.relative_to(self.root).as_posix()
        except ValueError:raise ArenaError('Verification path is outside its archive') from None
        if '..' in Path(name).parts:raise ArenaError('Verification path is outside its archive')
        stamp=fingerprint(path)
        with self.lock:
            cached=self.entries.get(name)
            if not self.force and stamp is not None and cached and cached[0]==stamp:
                self.hits+=1;return cached[1]
        sha=file_hash(path)
        after=fingerprint(path)
        if stamp is not None and stamp!=after:raise ArenaError('Artifact changed during verification: '+str(path))
        with self.lock:
            self.misses+=1;self.bytes_read+=path.stat().st_size
            if stamp is not None:self.entries[name]=(stamp,sha);self.dirty[name]=(stamp,sha)
        return sha

    def checked_session(self, sid, proof):
        with self.lock:
            valid=not self.force and self.sessions.get(sid)==proof
            if valid:self.session_hits+=1
            return valid

    def remember_session(self, sid, proof):
        with self.lock:self.sessions[sid]=proof;self.dirty_sessions[sid]=proof

    def read_record(self, path):
        import copy
        from .core import read_json
        name=path.relative_to(self.root).as_posix()
        if not self.force:
            with self.lock:cached=self.records.get(name)
            if cached and fingerprint(path)==cached[0]:
                with self.lock:self.record_hits+=1;self._record_reads[name]=cached[0]
                return copy.deepcopy(cached[1])
        with self.lock:self._record_reads.pop(name,None)
        return read_json(path)

    def remember_record(self, path, value):
        import copy,json,hashlib
        name=path.relative_to(self.root).as_posix()
        with self.lock:cached=self.records.get(name);read_stamp=self._record_reads.pop(name,None)
        if cached and read_stamp==cached[0] and cached[1]==value:return
        expected=hashlib.sha256((json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode()).hexdigest()
        if self.hash(path)!=expected:
            from .core import read_json
            if read_json(path)!=value:raise ArenaError('Record changed during verification')
        stamp=fingerprint(path)
        with self.lock:
            verified=self.entries.get(name)
            if stamp is None or not verified or verified[0]!=stamp:return
            self.records[name]=(stamp,copy.deepcopy(value));self.dirty_records[name]=self.records[name]

    def checked_receipt(self, path, binding, *, engine_accepts=None):
        name=path.relative_to(self.root).as_posix()
        with self.lock:cached=self.receipts.get(name)
        if self.force or not cached or cached[0]!=binding:return False
        if engine_accepts is not None:
            key=cached[2] if len(cached)>2 else None
            with self.lock:engine=self.engines.get(key)
            if engine is None or not engine_accepts(key,engine):return False
        for relative,expected in cached[1]:
            try:actual=fingerprint(self.root/relative,directory=True)
            except FileNotFoundError:return False
            if actual is None or actual!=expected:return False
        with self.lock:self.receipt_hits+=1
        return True

    def remember_receipt(self, path, binding, files, directories, *, engine=None):
        signature=[]
        for file in files:
            name=file.relative_to(self.root).as_posix()
            with self.lock:verified=self.entries.get(name)
            if not verified or fingerprint(file)!=verified[0]:return
            signature.append((name,verified[0]))
        for directory,stamp in directories.items():
            if stamp is None or fingerprint(directory,directory=True)!=stamp:return
            signature.append((directory.relative_to(self.root).as_posix(),stamp))
        name=path.relative_to(self.root).as_posix()
        with self.lock:
            if engine is not None:
                key=digest(engine);self.engines[key]=engine;self.dirty_engines[key]=engine
                self.receipts[name]=(binding,signature,key)
            else:self.receipts[name]=(binding,signature)
            self.dirty_receipts[name]=self.receipts[name]

    def flush(self):
        # SQLite stays on the coordinator; worker checks only update in-memory data.
        groups={'hash':self.dirty,'record':self.dirty_records,'receipt':self.dirty_receipts,'session':self.dirty_sessions,'engine':self.dirty_engines}
        with self.lock:snapshots={kind:dict(values) for kind,values in groups.items()}
        if not any(snapshots.values()):return
        rows=[]
        for kind,values in snapshots.items():
            for name,value in values.items():
                raw=json.dumps(value)
                rows.append((kind,name,raw,hashlib.sha256((kind+'\0'+name+'\0'+raw).encode()).hexdigest()))
        try:
            if self.path.is_symlink():raise OSError('Linked verification cache rejected')
            with closing(connect(self.path,timeout=2)) as db:
                db.execute('CREATE TABLE IF NOT EXISTS verification_entries(kind TEXT,path TEXT,payload TEXT,sha256 TEXT,PRIMARY KEY(kind,path))')
                with db:
                    if self._discard:db.execute('DELETE FROM verification_entries')
                    db.executemany('INSERT OR REPLACE INTO verification_entries VALUES (?,?,?,?)',rows)
            self._discard=False
            with self.lock:
                for kind,values in snapshots.items():
                    for name,value in values.items():
                        if groups[kind].get(name)==value:groups[kind].pop(name,None)
        except (sqlite3.Error,OSError,OverflowError):self.errors+=1  # Cache failure never skips the authoritative checks.
        self.last_flush=time.monotonic()

    def release(self, prefix=None, records=True):
        """Keep durable proofs on disk, not entire past rounds in process memory."""
        relative=prefix.relative_to(self.root).as_posix()+'/' if prefix is not None else None
        with self.lock:
            groups=[self.entries,self.dirty,self.receipts,self.dirty_receipts]
            if records:groups.extend([self.records,self.dirty_records,self._record_reads])
            for values in groups:
                if relative is None:values.clear()
                else:
                    for name in [name for name in values if name.startswith(relative)]:values.pop(name,None)

    def stats(self):
        with self.lock:return {'unchanged_hashes':self.hits,'computed_hashes':self.misses,'bytes_read':self.bytes_read,'cache_errors':self.errors,'unchanged_fights':self.receipt_hits,'cached_records':self.record_hits,'unchanged_session_checkpoints':self.session_hits,'full_audit':self.force}
