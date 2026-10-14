#!/usr/bin/env python3
"""Root-owned, narrow Unix-socket NetworkManager adapter. Never logs credentials."""
import grp
import json
import os
from pathlib import Path
import re
import socketserver
import subprocess
import uuid


def fields(line):
    result, current, escaped = [], '', False
    for char in line:
        if escaped:
            current += char; escaped = False
        elif char == '\\':
            escaped = True
        elif char == ':':
            result.append(current); current = ''
        else:
            current += char
    result.append(current)
    return result


def credentials(body):
    ssid, password, security = body.get('ssid'), body.get('password'), body.get('security', 'wpa2')
    if not isinstance(ssid, str) or not 1 <= len(ssid.encode()) <= 32 or any(ord(c) < 32 for c in ssid):
        raise ValueError('WLAN-Name muss 1 bis 32 Bytes lang sein.')
    if security not in ('wpa2', 'wpa3'):
        raise ValueError('Nur WPA2/WPA3-Personal unterstützt. Firmennetze separat einrichten.')
    if not isinstance(password, str) or not password.isascii() or any(ord(c) < 32 or ord(c) > 126 for c in password):
        raise ValueError('Ungültiger WLAN-Schlüssel.')
    if not (8 <= len(password) <= 63 or security == 'wpa2' and re.fullmatch('[0-9a-fA-F]{64}', password)):
        raise ValueError('WLAN-Schlüssel: 8–63 Zeichen oder WPA2-Hexschlüssel.')
    return ssid, password, security


def profile(body, ident):
    ssid, password, security = credentials(body)
    # Decimal SSID bytes and GLib escapes prevent keyfile/section injection.
    psk = password.replace('\\', '\\\\').replace(' ', '\\s')
    return ('[connection]\nid=Brain WLAN\nuuid=' + ident + '\ntype=wifi\nautoconnect=false\n'
            '[wifi]\nmode=infrastructure\nhidden=' + ('true' if body.get('hidden') is True else 'false') + '\nssid=' + ';'.join(str(b) for b in ssid.encode()) + ';\n'
            '[wifi-security]\nkey-mgmt=' + ('sae' if security == 'wpa3' else 'wpa-psk') + '\npsk=' + psk + '\n'
            '[ipv4]\nmethod=auto\n[ipv6]\nmethod=auto\n')


class Network:
    def __init__(self, root='/var/lib/cdb-network', profiles='/etc/NetworkManager/system-connections', runner=None):
        self.root, self.profiles = Path(root), Path(profiles)
        self.runner = runner or self.execute
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)

    @staticmethod
    def execute(args):
        result = subprocess.run(['/usr/bin/nmcli', '--wait', '35', *args], capture_output=True, text=True,
                                timeout=40 if args[:2] == ['connection', 'up'] else 12, env={'PATH': '/usr/sbin:/usr/bin:/sbin:/bin', 'LC_ALL': 'C.UTF-8'})
        if result.returncode:
            raise ValueError('Netzwerkaktion fehlgeschlagen. Passwort, WLAN und Reichweite prüfen.')
        return result.stdout.strip()

    def interface(self):
        for line in self.runner(['-t', '-f', 'DEVICE,TYPE', 'device', 'status']).splitlines():
            values = fields(line)
            if len(values) == 2 and values[1] == 'wifi' and re.fullmatch(r'[a-zA-Z0-9_.-]{1,32}', values[0]):
                return values[0]
        raise ValueError('Kein WLAN-Adapter gefunden. Netzwerkkabel verwenden.')

    def status(self):
        devices = []
        for line in self.runner(['-t', '-f', 'DEVICE,TYPE,STATE,CONNECTION', 'device', 'status']).splitlines():
            values = fields(line)
            if len(values) == 4 and values[1] in ('wifi', 'ethernet'):
                devices.append(dict(zip(('device', 'type', 'state', 'name'), values)))
        connectivity = self.runner(['-t', '-f', 'CONNECTIVITY', 'general'])
        return {'devices': devices, 'connectivity': connectivity, 'networks': []}

    def scan(self):
        interface = self.interface()
        result = self.status()
        lines = self.runner(['-t', '-f', 'SSID,SIGNAL,SECURITY', 'device', 'wifi', 'list', 'ifname', interface, '--rescan', 'yes'])
        found = {}
        for line in lines.splitlines():
            values = fields(line)
            if len(values) != 3 or not values[0]:
                continue
            name, strength, security = values
            supported = '802.1X' not in security and ('WPA2' in security or 'WPA3' in security)
            item = {'ssid': name, 'signal': int(strength) if strength.isdigit() else 0,
                    'security': 'wpa3' if 'WPA3' in security and 'WPA2' not in security else 'wpa2', 'supported': supported}
            if name not in found or found[name]['signal'] < item['signal']:
                found[name] = item
        result['scanned'] = True
        result['networks'] = sorted(found.values(), key=lambda n: -n['signal'])[:100]
        return result

    def recover(self):
        journal = self.root / 'pending.json'
        if not journal.exists():
            return
        data = json.loads(journal.read_text())
        ident = str(uuid.UUID(data['new']))
        try:
            self.runner(['connection', 'delete', 'uuid', ident])
        except ValueError:
            pass
        (self.profiles / ('cdb-' + ident + '.nmconnection')).unlink(missing_ok=True)
        if data.get('previous'):
            self.runner(['connection', 'up', 'uuid', str(uuid.UUID(data['previous']))])
        journal.unlink()

    def connect(self, body):
        credentials(body)
        self.recover()
        interface = self.interface()
        previous = self.runner(['-g', 'GENERAL.CON-UUID', 'device', 'show', interface])
        previous = str(uuid.UUID(previous)) if previous and previous != '--' else ''
        ident = str(uuid.uuid4())
        journal = self.root / 'pending.json'
        with journal.open('w') as stream:
            os.chmod(journal, 0o600)
            json.dump({'new': ident, 'previous': previous}, stream); stream.flush(); os.fsync(stream.fileno())
        target = self.profiles / ('cdb-' + ident + '.nmconnection')
        try:
            with target.open('x') as stream:
                os.chmod(target, 0o600); stream.write(profile(body, ident)); stream.flush(); os.fsync(stream.fileno())
            self.runner(['connection', 'load', str(target)])
            self.runner(['connection', 'up', 'uuid', ident, 'ifname', interface])
            self.runner(['connection', 'modify', 'uuid', ident, 'connection.autoconnect', 'yes', 'connection.autoconnect-priority', '10'])
            journal.unlink()
            return self.status()
        except Exception:
            self.recover()
            raise ValueError('WLAN-Verbindung fehlgeschlagen. Vorherige Verbindung wiederhergestellt.') from None

    def dispatch(self, body):
        action = body.get('action')
        if action == 'status': return self.status()
        if action == 'scan': return self.scan()
        if action == 'connect': return self.connect(body)
        raise ValueError('Unbekannte Netzwerkaktion.')


class Handler(socketserver.StreamRequestHandler):
    def handle(self):
        self.connection.settimeout(5)
        try:
            raw = self.rfile.readline(4097)
            if len(raw) > 4096 or not raw.endswith(b'\n'):
                raise ValueError('Ungültige Anfrage.')
            body = json.loads(raw)
            if not isinstance(body, dict): raise ValueError('Ungültige Anfrage.')
            result = self.server.network.dispatch(body)
        except Exception:
            result = {'error': 'Netzwerkaktion fehlgeschlagen. WLAN-Schlüssel und Verbindung prüfen.'}
        try: self.wfile.write(json.dumps(result).encode() + b'\n')
        except (BrokenPipeError, ConnectionResetError): pass


def main():
    os.umask(0o077)
    path = Path('/run/cdb-network/control.sock'); path.parent.mkdir(exist_ok=True)
    os.chown(path.parent, 0, grp.getgrnam('cdb-network').gr_gid); os.chmod(path.parent, 0o750)
    network = Network(); network.recover()
    path.unlink(missing_ok=True)
    with socketserver.UnixStreamServer(str(path), Handler) as server:
        os.chown(path, 0, grp.getgrnam('cdb-network').gr_gid); os.chmod(path, 0o660)
        server.network = network
        server.serve_forever()

if __name__ == '__main__': main()
