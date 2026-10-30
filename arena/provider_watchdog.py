"""Interrupt a real provider socket when output stops, even if SSE heartbeats continue."""
import socket
import threading
import time
from contextvars import ContextVar


request_control=ContextVar('arena_request_control',default=None)


def cancellable_handlers(control):
    """Register sockets before waiting for response headers, preserving urllib TLS/proxy handling."""
    from http.client import HTTPConnection, HTTPSConnection
    from urllib.request import HTTPHandler, HTTPSHandler
    def connection(base):
        class Connection(base):
            def connect(self):
                control.check()
                super().connect()
                control.attach(self.sock)
                control.check()
        return Connection
    class HTTP(HTTPHandler):
        def http_open(self, req):return self.do_open(connection(HTTPConnection),req)
    class HTTPS(HTTPSHandler):
        def https_open(self, req):return self.do_open(connection(HTTPSConnection),req,context=self._context)
    return [HTTP(),HTTPS()]


class RequestControl:
    """Cancel one transport without cancelling the other conversations."""
    def __init__(self):
        self.cancelled=threading.Event()
        self.lock=threading.Lock()
        self.socket=None

    def attach(self, sock):
        with self.lock:
            self.socket=sock
            if self.cancelled.is_set():self._shutdown()

    def _shutdown(self):
        if self.socket is not None:
            try:self.socket.shutdown(socket.SHUT_RDWR)
            except OSError:pass

    def cancel(self):
        with self.lock:
            self.cancelled.set()
            self._shutdown()

    def check(self):
        if self.cancelled.is_set():
            from .api_providers import ProviderFailure
            raise ProviderFailure('Conversation paused by the user. The interrupted request may have reached the provider.',
                uncertain=True,retryable=True,diagnostics={'network_error':'conversation_paused','request_delivery':'unknown'})


class InactivityGuard:
    def __init__(self,response,timeout,*,started_at=None):
        self.timeout=timeout
        self.last_progress=time.monotonic() if started_at is None else started_at
        self.expired=False
        self.control=request_control.get()
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
        if self.control:self.control.check()
        if self.expired or time.monotonic()-self.last_progress>=self.timeout:
            from .api_providers import ProviderFailure
            raise ProviderFailure(f'No provider output for {self.timeout:g} seconds. Conversation paused; retry when the provider is available. This does not establish a quota error.',
                uncertain=True,retryable=True,diagnostics={'network_error':'provider_inactivity_timeout',
                    'inactivity_timeout_seconds':self.timeout,'request_delivery':'unknown'})

    def __enter__(self):
        if self.control:self.control.attach(self.socket)
        self.check()
        self.thread.start()
        return self

    def __exit__(self,*args):
        self.stop.set()
        self.thread.join()
        try:self.check()
        finally:
            if self.control:self.control.attach(None)
