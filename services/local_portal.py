"""Offline manual and explicitly paired TLS-only LAN controls.

No proxy to the kiosk API. Sessions and receipts are memory-only: process restart
revokes all controllers, so commands can never be replayed across a restart.
Every account check, snapshot and action uses the Studio control lock.
"""
from collections import deque
from datetime import datetime, timedelta, timezone
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
import base64
from functools import lru_cache
import hashlib
import hmac
import ipaddress
import json
import mimetypes
import secrets
import socket
import ssl
import subprocess
import threading
import time
import uuid

from meeting_recorder.core import atomic_write

STATIC = Path(__file__).resolve().parent.parent / 'studio' / 'help'
COOKIE = '__Host-cdbportal'


def addresses():
    try:
        result = subprocess.run(['hostname', '-I'], capture_output=True, text=True, timeout=2)
        values = result.stdout.split() if result.returncode == 0 else []
    except (OSError, subprocess.SubprocessError):
        values = []
    return sorted({str(ip) for value in values for ip in [ipaddress.ip_address(value)]
                   if ip.version == 4 and ip.is_private and not ip.is_loopback})


def certificate(folder, hostname, ips):
    # cryptography is already part of the supported aiortc runtime.
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    cert_path, key_path = folder / 'certificate.pem', folder / 'private.pem'
    if cert_path.is_symlink() or key_path.is_symlink():
        raise ValueError('Zertifikatspfad ungültig.')
    names = [x509.DNSName(hostname), x509.DNSName(hostname + '.local'), x509.DNSName('localhost')]
    names += [x509.IPAddress(ipaddress.ip_address(ip)) for ip in ['127.0.0.1', *ips]]
    if not cert_path.exists() or not key_path.exists():
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, hostname + '.local')])
        now = datetime.now(timezone.utc)
        cert = (x509.CertificateBuilder().subject_name(subject).issuer_name(subject)
                .public_key(key.public_key()).serial_number(x509.random_serial_number())
                .not_valid_before(now - timedelta(days=1)).not_valid_after(now + timedelta(days=3650))
                .add_extension(x509.SubjectAlternativeName(names), critical=False)
                .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
                .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
                .sign(key, hashes.SHA256()))
        atomic_write(key_path, key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                                serialization.NoEncryption()).decode())
        key_path.chmod(0o600)
        atomic_write(cert_path, cert.public_bytes(serialization.Encoding.PEM).decode())
        cert_path.chmod(0o600)
    cert = x509.load_pem_x509_certificate(cert_path.read_bytes())
    fingerprint = ':'.join(f'{b:02X}' for b in cert.fingerprint(hashes.SHA256()))
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(cert_path, key_path)
    return context, fingerprint


@lru_cache(maxsize=1)
def wiring_pdf():
    item = json.loads((STATIC / 'downloads.json').read_text())['wiring']
    data = base64.b64decode(item['data'], validate=True)
    if hashlib.sha256(data).hexdigest() != item['sha256']:
        raise ValueError('Anleitungsdatei beschädigt.')
    return data


@lru_cache(maxsize=4)
def qr_svg(url):
    from services.vendor.qrcodegen import QrCode
    qr = QrCode.encode_text(url, QrCode.Ecc.MEDIUM)
    size = qr.get_size() + 8
    path = ''.join(f'M{x+4},{y+4}h1v1h-1z' for y in range(qr.get_size())
                   for x in range(qr.get_size()) if qr.get_module(x, y))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}">'
            f'<path fill="white" d="M0,0h{size}v{size}H0z"/>'
            f'<path fill="black" d="{path}"/></svg>').encode()


class LocalPortal:
    def __init__(self, app, version, address='0.0.0.0', help_port=8091, control_port=8443, clock=time.monotonic):
        self.app, self.version, self.address, self.clock = app, version, address, clock
        self.help_port, self.control_port = help_port, control_port
        self.hostname = socket.gethostname().split('.')[0]
        self.ips = []
        self.folder = app.store.root / 'local-portal'
        self.config_path = self.folder / 'settings.json'
        self.http = self.https = None
        self.sessions = {}
        self.requests, self.attempts = deque(), deque()
        self.fingerprint = ''
        self.error = ''
        self.revision = 0
        self.state_key = None
        self.enabled = False

    def start(self):
        self.ips = addresses()
        try:
            self.http = self._serve(self.help_port, False)
            self.help_port = self.http.server_port
            if json.loads(self.config_path.read_text()).get('control_enabled') is True:
                self.enable()
        except FileNotFoundError:
            pass
        except (OSError, ValueError, ImportError):
            self.error = 'Portal konnte nicht vollständig starten. Netzwerkzugang am Pi prüfen.'

    def _serve(self, port, secure):
        server = PortalServer((self.address, port), self, secure)
        threading.Thread(target=server.serve_forever, daemon=True, name='cdb-help').start()
        return server

    def enable(self):
        if not self.https:
            context, self.fingerprint = certificate(self.folder, self.hostname, self.ips)
            server = PortalServer((self.address, self.control_port), self, True, context)
            self.https = server
            self.control_port = server.server_port
            threading.Thread(target=server.serve_forever, daemon=True, name='cdb-local-control').start()
        self.enabled = True
        self.error = ''
        atomic_write(self.config_path, json.dumps({'control_enabled': True}))
        self.config_path.chmod(0o600)
        return self.public()

    def disable(self):
        # Listener may remain until process exit; all control endpoints fail closed.
        self.enabled = False
        self.sessions.clear()
        self.folder.mkdir(exist_ok=True, parents=True, mode=0o700)
        atomic_write(self.config_path, json.dumps({'control_enabled': False}))
        return self.public()

    def close(self):
        with self.app.control_lock:
            self.enabled = False
            self.sessions.clear()
        for server in (self.http, self.https):
            if server:
                server.shutdown()
                server.server_close()

    def binding(self):
        account = self.app.room.account()
        return {'account': account, 'generation': self.app.cdb.generation,
                'epoch': self.app.room.epoch} if account else None

    def prune(self):
        now, binding = self.clock(), self.binding()
        for token, row in list(self.sessions.items()):
            if now >= row['expires'] or now - row['seen'] > 600 or row['binding'] != binding:
                self.sessions.pop(token, None)

    def public(self):
        with self.app.control_lock:
            self.prune()
            return {'available': bool(self.http), 'enabled': self.enabled, 'error': self.error,
                    'url': f'http://{self.hostname}.local:{self.help_port}/',
                    'ip_urls': [f'http://{ip}:{self.help_port}/' for ip in self.ips],
                    'control_url': f'https://{self.hostname}.local:{self.control_port}/#remote',
                    'fingerprint': self.fingerprint,
                    'controllers': [row['name'] for row in self.sessions.values() if row['approved']]}

    def limited(self, queue, limit):
        now = self.clock()
        while queue and now - queue[0] >= 60:
            queue.popleft()
        if len(queue) >= limit:
            raise ValueError('Zu viele Versuche. Bitte eine Minute warten.')
        queue.append(now)

    def begin(self, name):
        with self.app.control_lock:
            self.prune()
            if not self.enabled:
                raise ValueError('Fernbedienung zuerst am Pi freigeben.')
            self.app.room.require_account()
            self.limited(self.requests, 12)
            if len(self.sessions) >= 8:
                raise ValueError('Zu viele offene Verbindungen. Am Pi entkoppeln oder kurz warten.')
            if not isinstance(name, str) or not 1 <= len(name.strip()) <= 48:
                raise ValueError('Bitte einen kurzen Namen für deinen Browser eingeben.')
            code = str(secrets.randbelow(900000) + 100000)
            while any(row['code'] == code for row in self.sessions.values()):
                code = str(secrets.randbelow(900000) + 100000)
            token = secrets.token_urlsafe(32)
            self.sessions[token] = {'name': ' '.join(name.split()), 'code': code, 'approved': False,
                                    'binding': self.binding(), 'expires': self.clock()+120, 'seen': self.clock(),
                                    'csrf': secrets.token_urlsafe(32), 'commands': {}, 'tickets': {}}
            return token

    def approve(self, code):
        with self.app.control_lock:
            self.prune()
            self.app.room.require_account()
            self.app.require('configure')
            self.limited(self.attempts, 5)
            if not isinstance(code, str) or len(code) != 6 or not code.isdigit():
                raise ValueError('Sechsstelligen Code aus dem Browser eingeben.')
            row = next((r for r in self.sessions.values() if not r['approved'] and hmac.compare_digest(r['code'], code)), None)
            if not row:
                raise ValueError('Code ungültig oder abgelaufen.')
            row.update(approved=True, code='', expires=self.clock()+7200)
            return self.public()

    def session(self, token, approved=False):
        self.prune()
        row = self.sessions.get(token)
        if not self.enabled or not row or (approved and not row['approved']):
            raise PermissionError('Verbindung nicht freigegeben oder abgelaufen. Bitte erneut koppeln.')
        row['seen'] = self.clock()  # Never calls room.touch().
        return row

    def snapshot(self):
        app = self.app
        rec = app.engine.recorder.status()
        live = app.live.public()
        activity = app.activity()
        caps = app.capabilities()
        ready = not app.closing and not app.management.busy() and not app.first_start.busy
        allowed = []
        if ready:
            if rec.get('id'):
                allowed = ['record.stop', 'record.resume' if rec.get('paused') else 'record.pause',
                           'record.unmute' if rec.get('muted') else 'record.mute']
            elif live['busy']:
                if app.live.binding == app.room.account() and getattr(app.live, 'account_generation', None) == app.cdb.generation:
                    if live['state'] != 'closing': allowed = ['talk.stop']
                    if live['state'] in ('listening', 'thinking', 'speaking', 'reconnecting'):
                        allowed += ['talk.unmute' if live['muted'] else 'talk.mute']
            else:
                if caps['record']['allowed']: allowed.append('record.start')
                if caps['live']['allowed'] and not app.wake_reason(): allowed.append('talk.start')
        # No titles, transcript, credentials, files, level data or account names.
        state = {'recording': bool(rec.get('id')), 'paused': bool(rec.get('paused')), 'muted': bool(rec.get('muted')),
                 'talk': live['state'], 'talk_muted': live['muted'], 'allowed': allowed,
                 'mode': activity.mode, 'reason': activity.reason or caps['record']['reason']}
        key = (json.dumps(state, sort_keys=True), rec.get('id'), app.live.generation, app.live.control_revision)
        if key != self.state_key:
            self.state_key = key
            self.revision += 1
        return state | {'revision': self.revision, 'seconds': rec.get('seconds', 0), 'version': self.version}

    def status(self, token):
        app = self.app
        with app.control_lock, app.controller.lock, app.engine.recorder.lock, app.live.lock:
            row = self.session(token)
            result = {'paired': row['approved'], 'name': row['name'], 'code': row['code'],
                      'expires_in': max(0, int(row['expires']-self.clock())), 'csrf': row['csrf']}
            if row['approved']:
                snapshot = self.snapshot()
                # Short-lived server-clock ticket avoids relying on phone clock.
                ticket = secrets.token_urlsafe(24)
                row['tickets'] = {k: v for k, v in row['tickets'].items() if v[0] > self.clock()}
                if len(row['tickets']) >= 16: row['tickets'].pop(next(iter(row['tickets'])))
                row['tickets'][ticket] = (self.clock()+15, snapshot['revision'])
                result.update(snapshot=snapshot, ticket=ticket)
            return result

    def command(self, token, csrf, body):
        app = self.app
        with app.control_lock, app.controller.lock, app.engine.recorder.lock, app.live.lock:
            row = self.session(token, approved=True)
            if not hmac.compare_digest(csrf, row['csrf']): raise PermissionError('Sitzung ungültig.')
            if not isinstance(body, dict) or set(body) != {'id', 'action', 'ticket'}:
                raise ValueError('Ungültiger Auftrag.')
            try:
                if str(uuid.UUID(body['id'])) != body['id']: raise ValueError()
            except (ValueError, TypeError, AttributeError): raise ValueError('Ungültige Auftragskennung.') from None
            if not isinstance(body['ticket'], str) or not isinstance(body['action'], str): raise ValueError('Ungültiger Auftrag.')
            previous = row['commands'].get(body['id'])
            if previous:
                if previous[0] != body: raise ValueError('Auftragskennung bereits verwendet.')
                return previous[1]
            if len(row['commands']) >= 2000: raise ValueError('Bitte neu koppeln.')
            ticket = row['tickets'].pop(body['ticket'], None)
            snapshot = self.snapshot()
            if not ticket or ticket[0] <= self.clock() or ticket[1] != snapshot['revision']:
                raise ValueError('Status hat sich geändert. Bitte erneut prüfen und bedienen.')
            action = body['action']
            if action not in snapshot['allowed']: raise ValueError('Aktion derzeit nicht möglich.')
            # Remember BEFORE the side effect; never retry an uncertain result.
            result = {'ok': False, 'message': 'Ergebnis unklar. Status am Pi prüfen.'}
            row['commands'][body['id']] = (dict(body), result)
            try:
                app.room.require_account()
                def start_guard():
                    self.session(token, approved=True)
                    if self.clock() >= ticket[0]: raise ValueError('Auftrag abgelaufen. Bitte erneut starten.')
                if action == 'record.start': app.action('/api/record/start', {}, start_guard=start_guard)
                elif action == 'record.stop': app.action('/api/record/stop', {})
                elif action.startswith('record.'):
                    key = 'paused' if action in ('record.pause', 'record.resume') else 'muted'
                    app.action('/api/record/control', {key: action in ('record.pause', 'record.mute')})
                elif action == 'talk.start':
                    app.require('live')
                    app.wake.test_until = 0
                    app.wake.suspend('Gespräch startet.')
                    start_guard()
                    app._start_device_live_locked(app.room.account())
                    app.room.touch()
                elif action == 'talk.stop': app.action('/api/live/end', {'lease': app.live.lease})
                else: app.action('/api/live/mute', {'lease': app.live.lease, 'muted': action == 'talk.mute'})
                result.update(ok=True, message='Am Pi ausgeführt.')
            except ValueError as error:
                result['message'] = str(error)
            finally:
                self.revision += 1
            return result


class PortalServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True
    def __init__(self, address, portal, secure, context=None):
        self.portal, self.secure, self.context = portal, secure, context
        self.slots = threading.BoundedSemaphore(20)
        super().__init__(address, PortalHandler)

    def process_request(self, request, client_address):
        if not self.slots.acquire(blocking=False): request.close(); return
        try: super().process_request(request, client_address)
        except Exception: self.slots.release(); raise

    def process_request_thread(self, request, client_address):
        try:
            request.settimeout(5)
            if self.context: request = self.context.wrap_socket(request, server_side=True)
            super().process_request_thread(request, client_address)
        except (OSError, ssl.SSLError): request.close()
        finally: self.slots.release()

    def handle_error(self, *_): pass  # Never log a request, pairing code or cookie.


class PortalHandler(BaseHTTPRequestHandler):
    def log_message(self, *_): pass

    def respond(self, value, status=200, mime='application/json; charset=utf-8', cookie=None):
        data = value if isinstance(value, bytes) else json.dumps(value, ensure_ascii=False).encode()
        self.send_response(status)
        for key, val in {'Content-Type': mime, 'Content-Length': str(len(data)), 'Cache-Control': 'no-store',
                         'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer',
                         'Permissions-Policy': 'microphone=(), camera=()',
                         'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"}.items():
            self.send_header(key, val)
        if cookie: self.send_header('Set-Cookie', f'{COOKIE}={cookie}; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age=7200')
        self.end_headers()
        self.wfile.write(data)

    def valid_host(self):
        host = urlsplit('http://' + self.headers.get('Host', '')).hostname
        portal = self.server.portal
        if not ipaddress.ip_address(self.client_address[0]).is_private: return False
        if host in (portal.hostname.lower(), portal.hostname.lower()+'.local', 'localhost'): return True
        return host == self.connection.getsockname()[0]

    def token(self):
        try:
            cookie = SimpleCookie(self.headers.get('Cookie', ''))
            return cookie[COOKIE].value if COOKIE in cookie else ''
        except Exception: return ''

    def do_GET(self):
        try:
            if not self.valid_host(): raise PermissionError('Geräteadresse ungültig.')
            path = urlsplit(self.path).path
            portal = self.server.portal
            if path == '/verkabelung-r2.pdf':
                self.respond(wiring_pdf(), mime='application/pdf')
            elif path == '/api/info':
                # Generic metadata only. No names, status or fingerprints over HTTP.
                host = urlsplit('http://' + self.headers['Host']).hostname
                self.respond({'version': portal.version, 'secure': self.server.secure,
                              'control_url': f'https://{host}:{portal.control_port}/#remote', 'enabled': portal.enabled})
            elif path == '/api/session' and self.server.secure:
                self.respond(portal.status(self.token()))
            elif path.startswith('/api/'):
                self.respond({'error': 'Nicht verfügbar.'}, 404)
            elif path == '/downloads.json':
                self.respond({'error': 'Seite nicht gefunden.'}, 404)
            else:
                relative = 'index.html' if path == '/' else path.lstrip('/')
                file = (STATIC / relative).resolve()
                if not file.is_relative_to(STATIC.resolve()) or not file.is_file() or file.suffix not in ('.html', '.css', '.js', '.json', '.svg', '.png', '.pdf'):
                    self.respond({'error': 'Seite nicht gefunden.'}, 404); return
                self.respond(file.read_bytes(), mime=mimetypes.guess_type(file)[0] or 'application/octet-stream')
        except PermissionError as error: self.respond({'error': str(error)}, 403)
        except (ValueError, OSError): self.respond({'error': 'Anfrage nicht verfügbar.'}, 400)

    def do_POST(self):
        try:
            if not self.server.secure or not self.valid_host(): raise PermissionError('Fernbedienung benötigt den verschlüsselten Zugang.')
            if self.headers.get('Origin') != 'https://' + self.headers.get('Host', '') or self.headers.get('X-Portal-Request') != '1':
                raise PermissionError('Fremder Ursprung nicht erlaubt.')
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 2048 or self.headers.get('Content-Type') != 'application/json': raise ValueError('Ungültige Anfrage.')
            body = json.loads(self.rfile.read(size))
            if not isinstance(body, dict): raise ValueError('Ungültige Anfrage.')
            portal, path = self.server.portal, urlsplit(self.path).path
            if path == '/api/pair':
                if set(body) != {'name'}: raise ValueError('Ungültige Anfrage.')
                token = portal.begin(body['name'])
                self.respond(portal.status(token), cookie=token)
            elif path == '/api/command':
                # Same persistent owner thread as local recording start; request
                # thread exit must not terminate the microphone child process.
                result = portal.app.recording_owner.submit(portal.command, self.token(), self.headers.get('X-Portal-CSRF', ''), body).result()
                self.respond(result)
            elif path == '/api/leave':
                with portal.app.control_lock:
                    row = portal.session(self.token())
                    if not hmac.compare_digest(self.headers.get('X-Portal-CSRF', ''), row['csrf']): raise PermissionError('Sitzung ungültig.')
                    portal.sessions.pop(self.token(), None)
                self.respond({'ok': True})
            else: self.respond({'error': 'Aktion nicht verfügbar.'}, 404)
        except PermissionError as error: self.respond({'error': str(error)}, 403)
        except (ValueError, KeyError) as error: self.respond({'error': str(error)}, 400)
        except Exception: self.respond({'error': 'Ergebnis unklar. Status am Pi prüfen.'}, 500)
