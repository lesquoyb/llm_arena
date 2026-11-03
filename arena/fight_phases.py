"""Per-worker progress without shared mutable Engine state."""
from contextvars import ContextVar

callback=ContextVar('arena_fight_phase',default=None)


def phase(name):
    update=callback.get()
    if update is not None:update(name)
