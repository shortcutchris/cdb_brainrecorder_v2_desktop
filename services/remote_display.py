"""Read-only LAN display. Pairing is approved only through the loopback Studio API.

No recorder routes, Microsoft credentials or audio are exposed by this server.
Pairings are memory-only and expire on restart, logout, timeout or explicit revoke.
"""
from collections import deque
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hashlib
import ipaddress
import json
from pathlib import Path
import re
import secrets
import socket
import threading
import time
from urllib.parse import urlsplit, parse_qs

STATIC = Path(__file__).resolve().parent.parent / 'studio' / 'receiver'


class DisplayHub:
    def __init__(self, live, account, address=('0.0.0.0', 8090), clock=time.monotonic):
        self.live, self.account, self.address, self.clock = live, account, address, clock
        self.lock = threading.RLock()
        self.server = None
        self.thread = None
        self.clients = {}
        self.attempts = deque()
        self.starts = deque()
        self.enabled = False

    def enable(self):
        with self.lock:
            if self.server: return self.status()
            server = DisplayServer(self.address, self)
            self.server = server
            self.enabled = True
            self.thread = threading.Thread(target=server.serve_forever, daemon=True)
            self.thread.start()
            return self.status()

    def close(self):
        with self.lock:
            server, self.server = self.server, None
            self.enabled = False
            self.clients.clear()
        if server:
            server.shutdown()
            server.server_close()

    def _prune(self):
        now, account = self.clock(), self.account()
        for key, row in list(self.clients.items()):
            if now >= row['expires'] or row.get('account') is not None and (row['account'] != account or now-row['seen'] > 600):
                del self.clients[key]

    def status(self):
        with self.lock:
            self._prune()
            paired = next((r for r in self.clients.values() if r.get('account') is not None), None)
            port = self.server.server_port if self.server else self.address[1]
            return {'enabled': self.enabled, 'paired': paired is not None,
                    'connected': bool(paired and self.clock()-paired['seen'] < 15),
                    'name': paired['name'] if paired else '', 'port': port,
                    'url': 'http://' + socket.gethostname().split('.')[0] + '.local:' + str(port),
                    'pending': sum(r.get('account') is None for r in self.clients.values())}

    def begin(self, name, previous=None):
        with self.lock:
            self._prune()
            if not self.enabled: raise ValueError('Bildschirmfreigabe ist ausgeschaltet.')
            if previous in self.clients:
                row = self.clients[previous]
                return previous, self._welcome(row)
            now = self.clock()
            while self.starts and now-self.starts[0] >= 60: self.starts.popleft()
            if len(self.starts) >= 20 or len(self.clients) >= 8:
                raise ValueError('Zu viele Kopplungen. Bitte kurz warten.')
            self.starts.append(now)
            if not isinstance(name, str): raise ValueError('Bildschirmname fehlt.')
            name = ' '.join(name.split())[:40] or 'Browser'
            used = {r['code'] for r in self.clients.values()}
            code = str(secrets.randbelow(900000)+100000)
            while code in used: code = str(secrets.randbelow(900000)+100000)
            token = secrets.token_urlsafe(32)
            self.clients[token] = {'name': name, 'code': code, 'expires': now+120, 'seen': now, 'account': None}
            return token, self._welcome(self.clients[token])

    def _welcome(self, row):
        return {'paired': row.get('account') is not None,
                'code': row['code'] if row.get('account') is None else '',
                'expires_in': max(0, int(row['expires']-self.clock()))}

    def pair(self, code):
        with self.lock:
            self._prune()
            account = self.account()
            if account is None: raise ValueError('Bitte zuerst beim Brain-Konto anmelden.')
            if not self.enabled: raise ValueError('Bildschirmfreigabe zuerst einschalten.')
            now = self.clock()
            while self.attempts and now-self.attempts[0] >= 60: self.attempts.popleft()
            if len(self.attempts) >= 5: raise ValueError('Zu viele Versuche. Eine Minute warten.')
            self.attempts.append(now)
            if not isinstance(code, str) or not re.fullmatch(r'\d{6}', code): raise ValueError('Sechsstelligen Code eingeben.')
            found = next(((key, row) for key, row in self.clients.items() if row['account'] is None and secrets.compare_digest(row['code'], code)), None)
            if not found: raise ValueError('Code ungültig oder abgelaufen. Am Bildschirm neu anfordern.')
            key, row = found
            row.update(account=account, expires=now+86400, seen=now, code='')
            self.clients = {key: row}  # Only one explicitly selected receiver.
            return self.status()

    def revoke(self):
        with self.lock: self.clients.clear()
        return self.status()

    def leave(self, token):
        with self.lock: self.clients.pop(token, None)

    def pulse(self, token, offset=0, revision=''):
        with self.lock:
            self._prune()
            row = self.clients.get(token)
            if not row: raise PermissionError('Kopplung abgelaufen. Bitte erneut verbinden.')
            row['seen'] = self.clock()
            if row['account'] is None: return self._welcome(row)
            # Snapshot takes the Live lock; account is checked again after the read.
            snapshot = self.live.display_snapshot(row['account']['binding'])
            if self.account() != row['account']:
                self.clients.pop(token, None)
                raise PermissionError('Brain-Konto hat sich geändert.')
            history = snapshot.pop('history')
            digest = hashlib.sha256(json.dumps(snapshot | {'history': history}, ensure_ascii=False).encode()).hexdigest()
            result = {'paired': True, **snapshot, 'revision': digest, 'total': len(history)}
            if revision == digest: return result | {'unchanged': True}
            if not isinstance(offset, int) or offset < 0: raise ValueError('Ungültige Verlaufsseite.')
            offset = min(offset, len(history))
            return result | {'offset': offset, 'history': history[offset:offset+100], 'more': offset+100 < len(history)}


class DisplayServer(ThreadingHTTPServer):
    daemon_threads = True
    def __init__(self, address, hub):
        self.hub = hub
        super().__init__(address, DisplayHandler)


class DisplayHandler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    def log_message(self, *_): pass  # Do not log cookies, codes or chat content.
    def setup(self):
        super().setup()
        self.connection.settimeout(10)

    def respond(self, value, status=200, cookie=None, mime='application/json; charset=utf-8'):
        data = value if isinstance(value, bytes) else json.dumps(value, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Permissions-Policy', 'microphone=(), camera=()')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        if cookie: self.send_header('Set-Cookie', 'display='+cookie+'; HttpOnly; SameSite=Strict; Path=/; Max-Age=86400')
        self.end_headers()
        self.wfile.write(data)

    def token(self):
        try:
            cookie = SimpleCookie(self.headers.get('Cookie', ''))
            return cookie['display'].value if 'display' in cookie else ''
        except Exception: return ''

    def allowed(self):
        try:
            host = urlsplit('http://'+self.headers.get('Host', '')).hostname or ''
            names = {'localhost', socket.gethostname().lower(), socket.gethostname().lower().split('.')[0]+'.local'}
            if host not in names:
                address = ipaddress.ip_address(host)
                # Host must identify this socket, not an arbitrary LAN address.
                if not (address.is_loopback or host == self.connection.getsockname()[0]): return False
            if not ipaddress.ip_address(self.client_address[0]).is_private: return False
            origin = self.headers.get('Origin')
            return not origin or origin == 'http://'+self.headers.get('Host', '')
        except ValueError: return False

    def do_GET(self):
        try:
            if not self.allowed(): return self.respond({'error': 'Ursprung nicht erlaubt.'}, 403)
            path = urlsplit(self.path).path
            if path == '/api/display':
                query = parse_qs(urlsplit(self.path).query)
                return self.respond(self.server.hub.pulse(self.token(), int(query.get('offset', ['0'])[0]), query.get('revision', [''])[0]))
            files = {'/': ('index.html', 'text/html; charset=utf-8'), '/receiver.js': ('receiver.js', 'text/javascript; charset=utf-8'), '/receiver.css': ('receiver.css', 'text/css; charset=utf-8')}
            if path not in files: return self.respond({'error': 'Nicht verfügbar.'}, 404)
            name, mime = files[path]
            return self.respond((STATIC/name).read_bytes(), mime=mime)
        except PermissionError as e: self.respond({'error': str(e)}, 401)
        except (ValueError, KeyError): self.respond({'error': 'Ungültige Anfrage.'}, 400)
        except (BrokenPipeError, ConnectionResetError): pass

    def do_POST(self):
        try:
            if not self.allowed() or self.headers.get('X-Display-Request') != '1':
                self.close_connection = True
                return self.respond({'error': 'Ursprung nicht erlaubt.'}, 403)
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 <= length <= 1024:
                self.close_connection = True
                return self.respond({'error': 'Anfrage zu groß.'}, 413)
            body = json.loads(self.rfile.read(length) or b'{}')
            if not isinstance(body, dict): raise ValueError()
            if self.path == '/api/begin':
                token, response = self.server.hub.begin(body.get('name', 'Browser'), self.token())
                return self.respond(response, cookie=token)
            if self.path == '/api/leave':
                self.server.hub.leave(self.token())
                return self.respond({'left': True})
            return self.respond({'error': 'Nicht verfügbar.'}, 404)
        except (ValueError, KeyError) as e: self.respond({'error': str(e) or 'Ungültige Anfrage.'}, 400)
        except (BrokenPipeError, ConnectionResetError): pass
