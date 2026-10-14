"""Stagger TCP candidates so a broken IPv6 route cannot stall Brain requests.

TLS/SNI/certificate checks remain the standard HTTPSConnection implementation.
Only connection establishment is raced; HTTP requests are never replayed.
"""
import errno
import http.client
import selectors
import socket
import threading
import time
import urllib.request
from collections import OrderedDict

_CACHE = OrderedDict()
_LOCK = threading.Lock()


def resolve(address):
    key = tuple(address)
    with _LOCK:
        cached = _CACHE.get(key)
        if cached and cached[0] > time.monotonic(): return list(cached[1])
    rows = socket.getaddrinfo(*address, 0, socket.SOCK_STREAM)
    # Alternate families, preserving resolver preference within each family.
    ordered = []
    groups = {}
    for row in rows:
        if row not in groups.setdefault(row[0], []): groups[row[0]].append(row)
    while any(groups.values()):
        for values in groups.values():
            if values: ordered.append(values.pop(0))
    with _LOCK:
        _CACHE[key] = (time.monotonic() + 30, ordered)
        _CACHE.move_to_end(key)
        while len(_CACHE) > 64: _CACHE.popitem(last=False)
    return list(ordered)


def connect(address, timeout=socket._GLOBAL_DEFAULT_TIMEOUT, source_address=None):
    """Try another address after 250 ms; bound total TCP setup to ten seconds."""
    rows = resolve(address)
    limit = 10 if timeout is socket._GLOBAL_DEFAULT_TIMEOUT or timeout is None else min(10, timeout)
    deadline = time.monotonic() + limit
    pending = set()
    winner = None
    failure = OSError('No reachable address')
    selector = selectors.DefaultSelector()
    next_attempt = 0
    try:
        while rows or pending:
            now = time.monotonic()
            if now >= deadline: raise TimeoutError('Connection establishment timed out')
            if rows and (now >= next_attempt or not pending):
                family, kind, protocol, _, endpoint = rows.pop(0)
                try: sock = socket.socket(family, kind, protocol)
                except OSError as error:
                    failure = error
                    continue
                pending.add(sock)
                try:
                    sock.setblocking(False)
                    if source_address: sock.bind(source_address)
                    code = sock.connect_ex(endpoint)
                    if code == 0:
                        winner = sock
                        break
                    if code not in (errno.EINPROGRESS, errno.EWOULDBLOCK, errno.EALREADY):
                        raise OSError(code, 'Connection failed')
                    selector.register(sock, selectors.EVENT_WRITE)
                    next_attempt = now + .25
                except OSError as error:
                    failure = error; pending.remove(sock); sock.close()
                    continue
            delay = max(0, min(deadline, next_attempt if rows else deadline) - time.monotonic())
            for key, _ in selector.select(delay):
                sock = key.fileobj
                code = sock.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
                selector.unregister(sock)
                if code == 0:
                    winner = sock
                    break
                failure = OSError(code, 'Connection failed')
                pending.remove(sock); sock.close()
            if winner: break
        if winner is None: raise failure
        winner.settimeout(socket.getdefaulttimeout() if timeout is socket._GLOBAL_DEFAULT_TIMEOUT else timeout)
        return winner
    except OSError:
        with _LOCK: _CACHE.pop(tuple(address), None)
        raise
    finally:
        selector.close()
        for sock in pending:
            if sock is not winner: sock.close()


class HTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._create_connection = connect


class HTTPSHandler(urllib.request.HTTPSHandler):
    def https_open(self, request):
        return self.do_open(HTTPSConnection, request, context=self._context)
