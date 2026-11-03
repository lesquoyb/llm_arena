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


def settings(pooled, environ=None, warm=False):
    """JVM profile, options and recycle interval. A warm worker keeps the engine
    loaded and reuses compiled strategies, so it lives for many more fights."""
    environ=os.environ if environ is None else environ
    profile=environ.get('ARENA_JVM_PROFILE','throughput' if pooled else 'startup')
    if profile not in PROFILES:raise ArenaError('ARENA_JVM_PROFILE must be '+', '.join(PROFILES))
    try:recycle=int(environ.get('ARENA_JVM_RECYCLE_MATCHES','1000' if warm else '32'))
    except (TypeError,ValueError):raise ArenaError('ARENA_JVM_RECYCLE_MATCHES must be a positive integer') from None
    integer(recycle,1,None,'ARENA_JVM_RECYCLE_MATCHES')
    extra=['-Darena.sharedEngine=true','-Darena.aiCache=true'] if warm else []
    return profile,['-Xmx512m','-Dfile.encoding=UTF-8',*PROFILES[profile],*extra],recycle
