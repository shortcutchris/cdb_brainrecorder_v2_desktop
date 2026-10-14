"""Opt-in factory onboarding; existing installations are never reclassified."""
import json
from pathlib import Path
import socket
import threading
import uuid
from fleet.common import read, save


class NetworkClient:
    def __init__(self, path='/run/cdb-network/control.sock'):
        self.path = path

    def __call__(self, body):
        with socket.socket(socket.AF_UNIX) as sock:
            sock.settimeout(240)
            sock.connect(self.path)
            sock.sendall(json.dumps(body).encode() + b'\n')
            raw = b''
            while not raw.endswith(b'\n'):
                part = sock.recv(65536)
                if not part or len(raw) + len(part) > 262144:
                    raise ValueError('Netzwerkdienst antwortet nicht.')
                raw += part
        result = json.loads(raw)
        if 'error' in result:
            raise ValueError(result['error'])
        return result


class FirstStart:
    def __init__(self, root, network=None):
        self.path = Path(root) / 'first-start.json'
        self.network = network or NetworkClient()
        self.lock = threading.Lock()
        self.busy = False
        self.result = {'state': 'idle', 'message': ''}
        self.thread = None

    def public(self, management):
        saved = read(self.path, {})
        return {'required': saved.get('required') is True and not saved.get('completed'),
                'step': saved.get('step', 'welcome'), 'offline': saved.get('offline') is True, 'busy': self.busy,
                'operation': dict(self.result), 'management': management}

    def run_network(self, body):
        action = body.get('action')
        if action not in ('scan', 'status', 'connect'):
            raise ValueError('Unbekannte Netzwerkaktion.')
        with self.lock:
            if self.busy:
                raise ValueError('Netzwerk wird bereits eingerichtet.')
            self.busy = True
            self.result = {'state': 'running', 'message': 'Verbindung wird geprüft …' if action == 'connect' else 'Netzwerke werden geprüft …'}
        operation_id = str(uuid.uuid4())
        def work():
            try:
                result = self.network(body)
                self.result = {'id': operation_id, 'action': action, 'state': 'done', 'message': 'Netzwerk aktualisiert.', 'network': result}
            except FileNotFoundError:
                self.result = {'state': 'error', 'message': 'WLAN-Dienst auf diesem Gerät noch nicht installiert. Vorhandene Netzwerkverbindung bleibt erhalten.'}
            except (OSError, ValueError, TimeoutError):
                self.result = {'state': 'error', 'message': 'Netzwerk nicht verbunden. Passwort und Reichweite prüfen. Vorherige Verbindung wird wiederhergestellt; erneut prüfen.'}
            finally:
                self.busy = False
        self.thread = threading.Thread(target=work, daemon=True)
        self.thread.start()
        return {'ok': True}

    def advance(self, step, management, offline=False):
        if step not in ('welcome', 'network', 'pair', 'audio', 'done'):
            raise ValueError('Ungültiger Einrichtungsschritt.')
        if self.busy:
            raise ValueError('Netzwerkprüfung zuerst abschließen.')
        if step == 'done' and management.get('state') != 'connected' and offline is not True:
            raise ValueError('Gerät zuerst koppeln oder bewusst offline fortfahren.')
        saved = read(self.path, {})
        save(self.path, saved | {'step': step, 'completed': step == 'done', 'offline': offline is True})
        return {'ok': True}
