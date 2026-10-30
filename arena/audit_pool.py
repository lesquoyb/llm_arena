"""Bounded parallel read-only checks; all progress and journal writes stay local."""
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait


def scan(items, check, accept, *, interrupted=None, workers=None):
    workers=workers or 8
    items=iter(items);pending=set();exhausted=False;deferred=False;dispatched=0
    with ThreadPoolExecutor(max_workers=workers,thread_name_prefix='arena-audit') as pool:
        while pending or not exhausted:
            # Always make one bounded batch of progress. A ready provider must
            # not cause the same unverified backlog to be deferred forever.
            if dispatched and interrupted and interrupted():deferred=True;exhausted=True
            while not exhausted and len(pending)<workers:
                try:item=next(items)
                except StopIteration:exhausted=True;break
                pending.add(pool.submit(check,item))
                dispatched+=1
            if not pending:break
            done,pending=wait(pending,timeout=.1,return_when=FIRST_COMPLETED)
            from .runner_diagnostics import pulse
            pulse('checking_fights',pending_checks=len(pending))
            for future in done:accept(future.result())
    return deferred
