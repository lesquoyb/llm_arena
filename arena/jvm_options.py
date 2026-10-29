"""Measured JVM presets; execution tuning is separate from game rules."""
import os
from .core import ArenaError, integer

PROFILES={
    'startup':['-XX:TieredStopAtLevel=1'],
    'full':[],
    # Fresh game classloaders favor inexpensive C1; one collector thread avoids
    # multiplying GC pools across independent, single-fight JVM slots.
    'throughput':['-Xms32m','-XX:+UseSerialGC','-XX:TieredStopAtLevel=1'],
    'optimizing':['-Xms32m','-XX:+UseSerialGC','-XX:CICompilerCount=2'],
}


def settings(pooled, environ=None):
    environ=os.environ if environ is None else environ
    profile=environ.get('ARENA_JVM_PROFILE','throughput' if pooled else 'startup')
    if profile not in PROFILES:raise ArenaError('ARENA_JVM_PROFILE must be '+', '.join(PROFILES))
    try:recycle=int(environ.get('ARENA_JVM_RECYCLE_MATCHES','32'))
    except (TypeError,ValueError):raise ArenaError('ARENA_JVM_RECYCLE_MATCHES must be a nonnegative integer') from None
    integer(recycle,0,None,'ARENA_JVM_RECYCLE_MATCHES')
    return profile,['-Xmx512m','-Dfile.encoding=UTF-8',*PROFILES[profile]],recycle
