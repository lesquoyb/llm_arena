"""Measure SQLite work without logging SQL, parameters, prompts or credentials."""
from contextlib import contextmanager
from contextvars import ContextVar
import sqlite3
import time

_current=ContextVar('arena_sqlite_metrics',default=None)


@contextmanager
def collect():
    values={'sqlite_calls':0,'sqlite_wall_seconds':0,'sqlite_cpu_seconds':0,'sqlite_errors':0}
    token=_current.set(values)
    try:yield values
    finally:_current.reset(token)


def measured(function,*args,**kwargs):
    values=_current.get()
    if values is None:return function(*args,**kwargs)
    wall=time.monotonic();cpu=time.thread_time()
    try:return function(*args,**kwargs)
    except sqlite3.Error:
        values['sqlite_errors']+=1
        raise
    finally:
        values['sqlite_calls']+=1
        values['sqlite_wall_seconds']+=time.monotonic()-wall
        values['sqlite_cpu_seconds']+=time.thread_time()-cpu


class Cursor(sqlite3.Cursor):
    def fetchone(self):return measured(super().fetchone)
    def fetchall(self):return measured(super().fetchall)


class Connection(sqlite3.Connection):
    def execute(self,*args,**kwargs):
        cursor=self.cursor(factory=Cursor)
        try:return measured(cursor.execute,*args,**kwargs)
        except BaseException:cursor.close();raise

    def executemany(self,*args,**kwargs):return measured(super().executemany,*args,**kwargs)
    def commit(self):return measured(super().commit)
    def __exit__(self,*args):return measured(super().__exit__,*args)


def connect(*args,**kwargs):
    return sqlite3.connect(*args,factory=Connection,**kwargs)
