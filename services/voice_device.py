"""Bounded local voice tools; never run shell text or inspect conversation text.

Hardware writes cannot share a transaction with SQLite. Commit an uncertain
receipt BEFORE the one attempt, then replace it after hardware readback. A
crash/duplicate may be unconfirmed, but can never increase volume twice.
"""
import hashlib
import json
import math
import shutil
import sqlite3
import threading
import time
from pathlib import Path

from services.voice_actions import ACTION_NAMES, valid_action

NAMES = ('set_device_volume', 'adjust_device_volume', 'set_device_mute', 'get_device_status') + ACTION_NAMES
UNCERTAIN = {'ok': False, 'code': 'device_result_unconfirmed',
             'instruction': 'Ergebnis unbestätigt. Nicht automatisch wiederholen; zuerst Gerätestatus abfragen.'}


class VoiceDevice:
    def __init__(self, root, speakers, status, *, wall=time.time, actions=None):
        self.path = Path(root) / 'voice-device.sqlite3'
        self.speakers, self.status, self.wall = speakers, status, wall
        self.actions = actions
        self.lock = threading.RLock()
        with self.db() as db:
            db.execute('CREATE TABLE IF NOT EXISTS receipts (key TEXT PRIMARY KEY, payload TEXT NOT NULL, result TEXT NOT NULL, created REAL NOT NULL)')
        self.path.chmod(0o600)

    def db(self):
        return sqlite3.connect(self.path, timeout=10)

    def execute(self, scope, request):
        ident, name, args = request.get('id'), request.get('name'), request.get('arguments')
        if not isinstance(ident, str) or not 16 <= len(ident) <= 100 or not isinstance(args, dict):
            raise ValueError('Ungültiger Geräteauftrag.')
        payload = json.dumps(request, sort_keys=True, allow_nan=False)
        key = hashlib.sha256(json.dumps([scope, ident], sort_keys=True).encode()).hexdigest()
        with self.lock:
            with self.db() as db:
                db.execute('BEGIN IMMEDIATE')
                old = db.execute('SELECT payload, result FROM receipts WHERE key=?', (key,)).fetchone()
                if old:
                    if old[0] != payload: raise ValueError('Geräteauftrag wurde nachträglich verändert.')
                    return json.loads(old[1])
                expires = request.get('expires_at')
                if type(expires) not in (int, float) or not math.isfinite(expires) or self.wall() >= expires:
                    return {'ok': False, 'code': 'expired', 'message': 'Geräteauftrag abgelaufen.'}
                # Validate before writing any receipt or changing hardware.
                fields = {'set_device_volume': ('percent', 0, 100), 'adjust_device_volume': ('delta', -100, 100)}
                if name in fields:
                    field, low, high = fields[name]
                    valid = set(args) == {field} and type(args[field]) is int and low <= args[field] <= high
                    if name == 'adjust_device_volume' and args.get('delta') == 0: valid = False
                elif name == 'set_device_mute':
                    valid = set(args) == {'muted'} and type(args['muted']) is bool
                elif name in ACTION_NAMES:
                    valid = valid_action(name, args)
                else:
                    valid = name == 'get_device_status' and not args
                if not valid: return {'ok': False, 'code': 'invalid_arguments'}
                db.execute('INSERT INTO receipts VALUES (?,?,?,?)', (key, payload, json.dumps(UNCERTAIN), self.wall()))
            try:
                if name == 'get_device_status':
                    result = {'ok': True, **self.status()}
                elif name in ACTION_NAMES:
                    if self.actions is None: raise ValueError('Geräteansichten sind nicht verfügbar.')
                    result = self.actions.request(scope, request)
                else:
                    with self.speakers.lock:
                        state = self.speakers.public()
                        if not state['available'] or not state['is_default']:
                            raise ValueError('Gewählter Pi-Lautsprecher ist nicht als Audioausgang verfügbar. Einstellungen prüfen.')
                        if name == 'set_device_mute':
                            body = args
                        else:
                            target = args['percent'] if name == 'set_device_volume' else max(0, min(100, state['volume'] + args['delta']))
                            body = {'volume': target}
                            # Explicit positive volume restores audible responses.
                            if target > 0: body['muted'] = False
                        actual = self.speakers.configure(body)
                        if not actual['is_default']:
                            raise ValueError('Pi-Audioausgang während der Änderung gewechselt. Gerätestatus prüfen.')
                        result = {'ok': True, 'volume_percent': actual['volume'], 'muted': actual['muted'],
                                  'audible': not actual['muted'] and actual['volume'] > 0,
                                  'message': 'Am Pi-Ausgang eingestellt und zurückgelesen.'}
            except ValueError as error:
                result = {'ok': False, 'code': 'device_unavailable', 'message': str(error),
                          'instruction': 'Keinen Erfolg behaupten. Gerätestatus abfragen; nicht automatisch wiederholen.'}
            except Exception:
                result = dict(UNCERTAIN)
            with self.db() as db:
                db.execute('UPDATE receipts SET result=? WHERE key=?', (json.dumps(result), key))
                db.execute('DELETE FROM receipts WHERE created < ?', (self.wall() - 7 * 86400,))
            return result


def device_status(app):
    """Explicit allowlist: no identities, tokens, addresses, tags or meeting text.

Read-only inventory, no test recording, playback, USB reset or serial-port open.
One unavailable module must not hide all other observations.
"""
    from services.device_health import lcd_usb_status

    def audio():
        s = app.speakers.public()
        return {'detected': s['available'], 'selected_as_default': s['is_default'],
                'volume_percent': s['volume'] if s['available'] else None, 'muted': s['muted'],
                'audible_expected': s['available'] and s['is_default'] and not s['muted'] and s['volume'] > 0,
                'acoustic_test': 'not_performed'}

    def microphone():
        selected = app.store.config()['device']
        return {'detected': any(d['id'] == selected for d in app.audio_devices().get('devices', [])),
                'signal_test': 'not_performed'}

    def nfc():
        s = app.nfc.public()
        return {k: s[k] for k in ('enabled', 'state', 'assigned')}

    def led():
        s = app.respeaker.public()
        return {k: s[k] for k in ('connected', 'state', 'hardware_muted')}

    def storage():
        s = shutil.disk_usage(app.store.root)
        return {'free_bytes': s.free, 'total_bytes': s.total, 'low_space': s.free < 1024**3}

    def processing():
        s = app.cdb.config()
        return {k: s[k] for k in ('transcription', 'summary')}

    readers = {'account': lambda: {'signed_in': bool(app.room.account())},
               'speakers': audio, 'microphone': microphone, 'nfc': nfc, 'respeaker_leds': led,
               'timer_display': lambda: {'state': lcd_usb_status()['state'], 'visual_test': 'not_performed'},
               'storage': storage, 'processing': processing,
               'voice': lambda: {'state': app.live.public()['state']},
               'clock': lambda: {'synchronized': bool(app.clock_ready)}}
    result = {}
    for name, reader in readers.items():
        try: result[name] = reader()
        except Exception: result[name] = {'state': 'unknown'}
    return {'observed_at': time.time(), 'components': result,
            'instruction': 'Momentaufnahme. Nur gemeldete Fakten nennen. Erkannt bedeutet nicht funktional getestet; fehlend, ausgeschaltet und unbekannt unterscheiden. Keine pauschale Aussage, dass alle Module funktionieren.'}
