"""Opt-in local detector. All ownership changes happen under Studio.control_lock.

The detector is a replaceable child process: a slow/native inference call can
never delay a Record click, and termination closes its capture process as well.
No audio or pre-roll is saved or uploaded by this service.
"""
import importlib.util
import json
import os
from pathlib import Path
import select
import signal
import subprocess
import sys
import time
from meeting_recorder.child_process import owned_command
from meeting_recorder.core import atomic_write
from services.wake_phrase import WORD, model_ready


class WakeWord:
    def __init__(self, root, clock=time.monotonic):
        self.path = Path(root)/'wake-word.json'
        self.clock = clock
        self.enabled = False
        self.account = None
        self.process = None
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
        return {'enabled': self.enabled, 'available': self.runtime, 'word': WORD,
                'state': self.mode, 'message': self.message, 'detections': self.count,
                'recognized_for': max(0, round(self.recognized_until-self.clock(), 2)),
                'testing': self.test_until > self.clock()}

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
            self.process = subprocess.Popen(owned_command([sys.executable, '-u', '-m', 'services.wake_word', config['device']]),
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, start_new_session=True, bufsize=0)
            self.mode, self.message = 'loading', 'Lokale Erkennung startet …'
        if self.process.poll() is not None:
            self.suspend('Erkennung unterbrochen. Mikrofon und Laufzeit prüfen.')
            self.cooldown = self.clock()+10
            self.mode = 'error'
            return
        if not select.select([self.process.stdout], [], [], 0)[0]: return
        line = self.process.stdout.readline().decode().strip()
        if line == 'ready':
            self.mode = 'testing' if testing else 'listening'
            self.message = 'Sage „Hey Brain“ · Test ohne Cloud-Start.' if testing else 'Bereit für „Hey Brain“ · Erkennung bleibt lokal.'
        if line == 'detected':
            self.count += 1
            self.recognized_until = self.clock()+8
            self.suspend('Aktivierungswort erkannt.' if testing else 'Erkannt · Gespräch wird gestartet …')
            self.cooldown = self.clock()+3
            if not testing: trigger()


def detect(capture_command=None):
    from services.wake_phrase import PhraseDetector
    from services.live_audio import native_capture_command
    model = PhraseDetector()
    command = capture_command or native_capture_command({'device': sys.argv[1]})
    capture = subprocess.Popen(owned_command(command), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    def stop(*_):
        capture.terminate()
        raise SystemExit()
    signal.signal(signal.SIGTERM, stop)
    try:
        ready = False
        while True:
            audio = capture.stdout.read(1600)
            if len(audio) != 1600: break
            if not ready:
                print('ready', flush=True); ready = True
            if model.feed(audio): print('detected', flush=True)
    finally:
        if capture.poll() is None: capture.terminate()
        try: capture.wait(timeout=1)
        except subprocess.TimeoutExpired: capture.kill(); capture.wait()
        capture.stdout.close()

if __name__ == '__main__': detect()
