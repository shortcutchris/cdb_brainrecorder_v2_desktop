"""Opt-in local detector. All ownership changes happen under Studio.control_lock.

The detector is a replaceable child process: a slow/native inference call can
never delay a Record click, and termination closes its capture process as well.
No audio or pre-roll is saved or uploaded by this service.
"""
import importlib.util
import json
import logging
import os
from pathlib import Path
import select
import signal
import secrets
import subprocess
import sys
import time
from meeting_recorder.child_process import owned_command
from meeting_recorder.core import atomic_write
from services.wake_phrase import WORD, model_ready
from services.wake_diagnostics import AudioDiagnostics, validate


class WakeWord:
    def __init__(self, root, clock=time.monotonic):
        self.path = Path(root)/'wake-word.json'
        self.instance = secrets.token_hex(8)
        self.clock = clock
        self.enabled = False
        self.account = None
        self.process = None
        self.read_process = None
        self.read_buffer = b''
        self.progress_at = self.clock()
        self.diagnostics = None
        self.diagnostic_at = None
        self.diagnostic_history = []
        self.detector_starts = 0
        self.test_until = 0
        self.cooldown = 0
        self.count = 0
        self.recognized_until = 0
        self.message = 'Aktivierungswort ausgeschaltet.'
        self.mode = 'off'
        self.runtime = importlib.util.find_spec('vosk') is not None and model_ready()
        try:
            saved = json.loads(self.path.read_text())
            self.enabled = saved.get('enabled') is True
            self.account = saved.get('account')
        except (ValueError, OSError): pass

    def public(self):
        return {'instance': self.instance, 'enabled': self.enabled, 'available': self.runtime, 'word': WORD,
                'state': self.mode, 'message': self.message, 'detections': self.count,
                'recognized_for': max(0, round(self.recognized_until-self.clock(), 2)),
                'testing': self.test_until > self.clock(),
                'diagnostics': {'detector_starts': self.detector_starts,
                                'capture_running': self.process is not None,
                                'sample_age_seconds': round(max(0, self.clock()-self.diagnostic_at), 2) if self.diagnostic_at is not None else None,
                                'latest': self.diagnostics, 'recent_decisions': list(self.diagnostic_history)}}

    def save(self):
        atomic_write(self.path, json.dumps({'enabled': self.enabled, 'account': self.account}))
        os.chmod(self.path, 0o600)

    def configure(self, enabled, account):
        if type(enabled) is not bool: raise ValueError('Ein oder Aus wählen.')
        if enabled and not self.runtime: raise ValueError('Hey-Brain-Erkennung fehlt. Bitte die lokale Laufzeit und das Modell installieren.')
        if enabled and not account: raise ValueError('Zuerst beim Brain anmelden.')
        self.suspend()
        self.test_until = 0
        self.recognized_until = 0
        self.enabled, self.account = enabled, account if enabled else None
        self.save()
        self.mode = 'waiting' if enabled else 'off'
        self.message = 'Bereitschaft wird geprüft.' if enabled else 'Aktivierungswort ausgeschaltet.'
        return self.public()

    def test(self):
        if not self.runtime: raise ValueError('Hey-Brain-Erkennung fehlt. Bitte die lokale Laufzeit und das Modell installieren.')
        self.suspend()
        self.count = 0
        self.test_until = self.clock()+30
        return self.public()

    def suspend(self, reason='Kurz unterbrochen.'):
        process, self.process = self.process, None
        self.read_process = None
        self.read_buffer = b''
        if process:
            try:
                os.killpg(process.pid, signal.SIGTERM)
                process.wait(timeout=1)
            except ProcessLookupError: pass
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL); process.wait(timeout=2)
            finally:
                if process.stdout: process.stdout.close()
        self.cooldown = self.clock()+1
        self.mode = 'waiting' if self.enabled or self.test_until else 'off'
        self.message = reason

    def tick(self, *, account, reason, config, trigger):
        testing = self.test_until > self.clock()
        if self.test_until and not testing:
            self.test_until = 0
            self.suspend('Test beendet · '+str(self.count)+' Erkennungen.')
        if self.enabled and account != self.account:
            # Explicit re-enable on account/environment change, never inherit consent.
            self.configure(False, None)
            self.message = 'Brain-Konto geändert oder abgemeldet. Bitte erneut einschalten.'
        if not self.enabled and not testing:
            if self.process: self.suspend()
            self.mode = 'off'
            return
        if not self.runtime:
            self.mode, self.message = 'error', 'Hey-Brain-Erkennung fehlt. Bitte Laufzeit und Modell installieren.'
            return
        if reason:
            if self.process: self.suspend(reason)
            self.mode, self.message = 'waiting', reason
            return
        if self.clock() < self.cooldown: return
        if not self.process:
            # The service may retain its pre-update working directory. Parent and
            # detector must import the same immutable release, also on fresh images.
            self.process = subprocess.Popen(owned_command([sys.executable, '-u', '-m', 'services.wake_word', config['device']]),
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, start_new_session=True, bufsize=0,
                cwd=str(Path(__file__).resolve().parents[1]))
            self.detector_starts += 1
            self.diagnostics = None
            self.diagnostic_at = None
            self.mode, self.message = 'loading', 'Lokale Erkennung startet …'
        if self.process.poll() is not None:
            self.suspend('Erkennung unterbrochen. Mikrofon und Laufzeit prüfen.')
            self.cooldown = self.clock()+10
            self.mode = 'error'
            return
        if self.read_process is not self.process:
            self.read_process = self.process
            self.read_buffer = b''
            self.progress_at = self.clock()
        if select.select([self.process.stdout], [], [], 0)[0]:
            # stdout is unbuffered: read only available bytes, never wait for a
            # newline while holding the app's recording/control locks.
            chunk = self.process.stdout.read(4096)
            self.read_buffer += chunk
            if not chunk or len(self.read_buffer) > 8192:
                self.suspend('Erkennung unterbrochen. Wird erneut gestartet.')
                self.cooldown = self.clock()+10
                self.mode = 'error'
                return
            while b'\n' in self.read_buffer:
                line, self.read_buffer = self.read_buffer.split(b'\n', 1)
                if line.startswith(b'diagnostic '):
                    try: values = validate(json.loads(line[11:]))
                    except (ValueError, UnicodeError): values = None
                    if values:
                        previous = (self.diagnostics or {}).get('speech_segments', 0)
                        self.diagnostics, self.diagnostic_at = values, self.clock()
                        if values['speech_segments'] > previous:
                            self.diagnostic_history.append({'detector': self.detector_starts,
                                'at_monotonic': round(self.clock(), 2), **values})
                            self.diagnostic_history = self.diagnostic_history[-16:]
                if line in (b'ready', b'detected') or (line == b'alive' and self.mode in ('listening', 'testing')):
                    self.progress_at = self.clock()
                if line == b'ready':
                    self.mode = 'testing' if testing else 'listening'
                    self.message = 'Sage „Hey Brain“ · Test ohne Cloud-Start.' if testing else 'Bereit für „Hey Brain“ · Erkennung bleibt lokal.'
                if line == b'detected':
                    self.count += 1
                    logging.info('Wake detected count=%d testing=%s',self.count,testing)
                    self.recognized_until = self.clock()+8
                    self.suspend('Aktivierungswort erkannt.' if testing else 'Erkannt · Gespräch wird gestartet …')
                    self.cooldown = self.clock()+3
                    if not testing: trigger()
                    return  # Discard duplicate detections from the released child.
        timeout = 30 if self.mode == 'loading' else 15
        if self.clock() - self.progress_at > timeout:
            self.suspend('Erkennung reagiert nicht. Wird erneut gestartet.')
            self.cooldown = self.clock()+10
            self.mode = 'error'


def detect(capture_command=None):
    from services.wake_phrase import PhraseDetector
    from services.live_audio import native_capture_command
    model = PhraseDetector()
    diagnostics = AudioDiagnostics()
    command = capture_command or native_capture_command({'device': sys.argv[1]})
    capture = subprocess.Popen(owned_command(command), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    def stop(*_):
        capture.terminate()
        raise SystemExit()
    signal.signal(signal.SIGTERM, stop)
    try:
        ready = False
        last_progress = time.monotonic()
        while True:
            audio = capture.stdout.read(1600)
            if len(audio) != 1600: break
            if not ready:
                print('ready', flush=True); ready = True
            detected = model.feed(audio)
            diagnostics.feed(audio, model.last_decision)
            if model.last_decision or time.monotonic() - last_progress >= 2:
                print('diagnostic ' + json.dumps(diagnostics.snapshot(), separators=(',', ':')), flush=True)
            if detected: print('detected', flush=True)
            if time.monotonic() - last_progress >= 2:
                print('alive', flush=True)
                last_progress = time.monotonic()
    finally:
        if capture.poll() is None: capture.terminate()
        try: capture.wait(timeout=1)
        except subprocess.TimeoutExpired: capture.kill(); capture.wait()
        capture.stdout.close()

if __name__ == '__main__': detect()
