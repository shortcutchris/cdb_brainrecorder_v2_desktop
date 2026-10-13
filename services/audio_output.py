"""Pi speaker control through the user's existing PipeWire/PulseAudio session.

Only enumerated sinks can be addressed. Test audio is generated locally and sent
by paplay on the Pi, never by the remote browser.
"""
import array
import json
import math
from pathlib import Path
import shutil
import subprocess
import threading
import wave

from meeting_recorder.core import atomic_write


class AudioOutput:
    def __init__(self, root, *, allow_virtual=False):
        self.root = Path(root)
        self.preference = self.root / 'speaker.json'
        self.allow_virtual = allow_virtual  # isolated integration tests only
        self.lock = threading.RLock()
        self.process = None
        self.thread = None
        self.cancelled = False
        self.test = {'state': 'idle', 'message': 'Noch kein Testton abgespielt.'}

    def command(self, *args):
        try:
            return subprocess.run(['pactl', *args], check=True, capture_output=True,
                                  text=True, timeout=4).stdout.strip()
        except (OSError, subprocess.SubprocessError) as e:
            raise ValueError('Audioausgabe am Pi nicht erreichbar. Geräte aktualisieren.') from e

    def saved_device(self):
        try:
            return json.loads(self.preference.read_text()).get('device', '')
        except (OSError, ValueError, AttributeError):
            return ''

    def test_status(self):
        with self.lock:
            return dict(self.test)

    def public(self):
        base = {'supported': False, 'devices': [], 'selected': self.saved_device(),
                'available': False, 'volume': 0, 'muted': False, 'is_default': False,
                'test': self.test_status()}
        if not shutil.which('pactl') or not shutil.which('paplay'):
            return base | {'message': 'Audioausgabe benötigt pactl und paplay auf dem Pi.'}
        try:
            sinks = json.loads(self.command('-f', 'json', 'list', 'sinks'))
            default = self.command('get-default-sink')
            devices = []
            for sink in sinks:
                props = sink.get('properties', {})
                virtual = sink['name'] == 'auto_null' or str(props.get('node.virtual', '')).lower() == 'true' or props.get('factory.name') == 'support.null-audio-sink'
                if virtual and not self.allow_virtual:
                    continue
                channels = sink.get('volume', {}).values()
                volume = round(max((float(v['value_percent'].rstrip('%')) for v in channels), default=0))
                devices.append({'id': sink['name'], 'label': sink.get('description') or sink['name'],
                                'volume': max(0, min(100, volume)), 'muted': bool(sink.get('mute'))})
            selected = base['selected'] or default
            current = next((d for d in devices if d['id'] == selected), None)
            message = ('Lautsprecher verbunden.' if current and selected == default else
                       'Ausgang verbunden, aber nicht als Pi-Standard aktiv. In der Auswahl erneut wählen.' if current else
                       'Gewählter Lautsprecher nicht verbunden. Anschließen oder einen anderen Ausgang wählen.' if devices else
                       'Kein Lautsprecher erkannt. USB-Audio, HDMI-Audio oder einen eingerichteten Audioverstärker anschließen.')
            return base | {'supported': True, 'devices': devices, 'selected': selected,
                           'available': bool(current), 'volume': current['volume'] if current else 0,
                           'muted': current['muted'] if current else False,
                           'is_default': bool(current and selected == default), 'message': message}
        except (ValueError, KeyError, TypeError) as e:
            return base | {'message': str(e) if isinstance(e, ValueError) and str(e).startswith('Audioausgabe') else 'Audioausgänge konnten nicht gelesen werden.'}

    def configure(self, body):
        if not body or set(body) - {'device', 'volume', 'muted'}:
            raise ValueError('Unbekannte Lautsprechereinstellung.')
        if 'volume' in body and (type(body['volume']) is not int or not 0 <= body['volume'] <= 100):
            raise ValueError('Lautstärke muss zwischen 0 und 100 liegen.')
        if 'muted' in body and type(body['muted']) is not bool:
            raise ValueError('Ungültiger Stummschaltwert.')
        with self.lock:
            if self.test['state'] == 'running':
                raise ValueError('Testton zuerst beenden.')
            state = self.public()
            device = body.get('device', state['selected'])
            if not any(d['id'] == device for d in state['devices']):
                raise ValueError('Lautsprecher nicht verbunden. Geräte aktualisieren.')
            if 'device' in body:
                self.command('set-default-sink', device)
                # WirePlumber persists the system route; retain its stable name to
                # detect unplugged outputs instead of silently testing a fallback.
                atomic_write(self.preference, json.dumps({'device': device}))
            if 'volume' in body:
                self.command('set-sink-volume', device, str(body['volume']) + '%')
            if 'muted' in body:
                self.command('set-sink-mute', device, '1' if body['muted'] else '0')
            result = self.public()
            if 'volume' in body and abs(result['volume'] - body['volume']) > 1:
                raise ValueError('Der Ausgang hat die Lautstärke nicht übernommen. Geräte aktualisieren und erneut versuchen.')
            if 'muted' in body and result['muted'] != body['muted']:
                raise ValueError('Der Ausgang hat die Stummschaltung nicht übernommen.')
            if 'device' in body and not result['is_default']:
                raise ValueError('Standardausgang wurde nicht übernommen. Geräte aktualisieren.')
            return result

    @staticmethod
    def write_tone(path):
        rate = 24000
        frames = array.array('h')
        for i in range(rate * 2):
            t = i / rate
            left = .1 <= t < .8
            right = 1.1 <= t < 1.8
            local = t - (.1 if left else 1.1)
            envelope = max(0, min(1, local / .02, (.7 - local) / .02))
            value = round(6000 * envelope * math.sin(2 * math.pi * (440 if left else 660) * t)) if left or right else 0
            frames.extend((value if left else 0, value if right else 0))
        import sys
        if sys.byteorder != 'little':
            frames.byteswap()
        with wave.open(str(path), 'wb') as output:
            output.setparams((2, 2, rate, 0, 'NONE', 'not compressed'))
            output.writeframes(frames.tobytes())

    def start_test(self, tone=None):
        if tone is not None:
            from services.alarm_tones import TONES
            if tone not in TONES or tone=='silent': raise ValueError('Kein abspielbarer Alarmton.')
        with self.lock:
            if self.test['state'] == 'running':
                raise ValueError('Testton läuft bereits.')
            state = self.public()
            if not state['available']:
                raise ValueError(state['message'])
            if state['muted'] or state['volume'] == 0:
                raise ValueError('Stummschaltung aufheben und Lautstärke erhöhen.')
            self.cancelled = False
            self.test = {'state': 'running', 'message': 'Alarmton am Pi.' if tone else 'Testton am Pi: erst links, dann rechts.', 'device': state['selected']}
            self.thread = threading.Thread(target=self._play, args=(state['selected'],tone), daemon=True)
            self.thread.start()
            return self.test_status()

    def _play(self, device, tone=None):
        try:
            path = self.root / 'speaker-test.wav'
            if tone is None: self.write_tone(path)
            else:
                from services.alarm_tones import write_alarm
                write_alarm(path,tone)
            with self.lock:
                if self.cancelled:
                    return
                self.process = subprocess.Popen(['paplay', '--device=' + device, str(path)],
                                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                process = self.process
            code = process.wait(timeout=8)
            with self.lock:
                if not self.cancelled:
                    self.test = {'state': 'completed' if code == 0 else 'failed', 'device': device,
                                 'message': ('Alarmton beendet.' if tone else 'Testton beendet. Waren beide Töne hörbar?') if code == 0 else 'Testton fehlgeschlagen. Ausgang und Verbindung prüfen.'}
        except (OSError, subprocess.SubprocessError):
            with self.lock:
                if self.process and self.process.poll() is None:
                    self.process.kill()
                    self.process.wait()
                if not self.cancelled:
                    self.test = {'state': 'failed', 'device': device, 'message': 'Testton fehlgeschlagen. Audioausgabe prüfen.'}
        finally:
            with self.lock:
                self.process = None

    def stop_test(self):
        with self.lock:
            self.cancelled = True
            if self.process and self.process.poll() is None:
                self.process.terminate()
            if self.test['state'] == 'running':
                self.test = {'state': 'cancelled', 'message': 'Testton beendet.'}
            thread = self.thread
        if thread:
            thread.join(timeout=9)
        return self.test_status()
