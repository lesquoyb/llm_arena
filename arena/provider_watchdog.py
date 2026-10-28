"""Interrupt a real provider socket when output stops, even if SSE heartbeats continue."""
import socket
import threading
import time


class InactivityGuard:
    def __init__(self,response,timeout,*,started_at=None):
        self.timeout=timeout
        self.last_progress=time.monotonic() if started_at is None else started_at
        self.expired=False
        self.stop=threading.Event()
        node=response;self.socket=None
        for _ in range(5):
            if node is None:break
            self.socket=getattr(node,'_sock',None)
            if self.socket is not None:break
            node=getattr(node,'fp',None) or getattr(node,'raw',None)
        self.thread=threading.Thread(target=self.watch,name='arena-provider-watchdog',daemon=True)

    def touch(self):
        self.last_progress=time.monotonic()

    def watch(self):
        while not self.stop.wait(min(.25,self.timeout/4)):
            if time.monotonic()-self.last_progress<self.timeout:continue
            self.expired=True
            if self.socket is not None:
                try:self.socket.shutdown(socket.SHUT_RDWR)
                except OSError:pass
            return

    def check(self):
        if self.expired or time.monotonic()-self.last_progress>=self.timeout:
            from .api_providers import ProviderFailure
            raise ProviderFailure(f'No provider output for {self.timeout:g} seconds. Conversation paused; retry when the provider is available. This does not establish a quota error.',
                uncertain=True,retryable=True,diagnostics={'network_error':'provider_inactivity_timeout',
                    'inactivity_timeout_seconds':self.timeout,'request_delivery':'unknown'})

    def __enter__(self):
        self.check()
        self.thread.start()
        return self

    def __exit__(self,*args):
        self.stop.set()
        self.thread.join()
        self.check()
