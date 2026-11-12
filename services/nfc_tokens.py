"""Optional physical mode controls; no separate audio engine or session store."""
import json
import re
import subprocess
import threading
import time
from pathlib import Path
from meeting_recorder.core import atomic_write


class ReaderProcess:
    """Keep native PC/SC calls out of the recorder's control thread."""
    def __init__(self):
        self.process = None
        self.latest = {'state': 'off'}
        self.received = 0
        self.started = 0
        self.lock = threading.Lock()

    def start(self):
        if self.process is not None and self.process.poll() is None:
            if time.monotonic() - max(self.received, self.started) < 4:
                return
        self.close()
        helper = Path(__file__).with_name('nfc_reader.py')
        self.process = subprocess.Popen(['/usr/bin/python3', '-I', '-u', str(helper)],
                                        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                        text=True, start_new_session=True)
        process = self.process
        self.started = time.monotonic()
        def read():
            try:
                for line in process.stdout:
                    value = json.loads(line)
                    if value.get('state') not in ('present', 'absent', 'error'): continue
                    with self.lock:
                        if process is self.process:
                            self.latest, self.received = value, time.monotonic()
            except (OSError, ValueError): pass
            finally:
                process.stdout.close()
        threading.Thread(target=read, daemon=True, name='nfc-reader').start()

    def snapshot(self):
        with self.lock:
            if time.monotonic() - self.received > 2:
                return {'state': 'error', 'message': 'Keine aktuelle Leserantwort. Laufenden Modus am Bildschirm beenden.'}
            return dict(self.latest)

    def close(self):
        process, self.process = self.process, None
        if process is not None:
            if process.poll() is None:
                process.terminate()
                try: process.wait(timeout=.5)
                except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=.5)
        with self.lock:
            self.latest, self.received = {'state': 'off'}, 0


class NfcTokens:
    def __init__(self, root, reader=None, clock=time.monotonic):
        self.path = Path(root)/'nfc-tokens.json'
        try: saved = json.loads(self.path.read_text())
        except (OSError, ValueError): saved = {}
        if not isinstance(saved, dict): saved = {}
        tags = saved.get('tags', {})
        if not isinstance(tags, dict): tags = {}
        self.tags = {k:v for k,v in tags.items()
                     if k in ('talk', 'meeting') and isinstance(v,str) and re.fullmatch('[0-9a-f]{64}',v)}
        self.enabled = saved.get('enabled') is True and len(self.tags) == 2 and len(set(self.tags.values())) == 2
        self.reader = reader or ReaderProcess()
        self.clock = clock
        self.inspect_until = 0
        self.armed = False
        self.empty_since = None
        self.present_since = None
        self.tag = None
        self.owner = None
        self.message = 'NFC ausgeschaltet.'
        self.status = 'off'

    def reset_edge(self):
        self.armed = False
        self.empty_since = self.present_since = self.tag = None

    def save(self):
        atomic_write(self.path, json.dumps({'enabled':self.enabled, 'tags':self.tags}))
        self.path.chmod(0o600)

    def configure(self, body):
        previous = dict(self.tags), self.enabled
        try: return self._configure(body)
        except Exception:
            self.tags, self.enabled = previous
            self.reset_edge()
            raise

    def _configure(self, body):
        action = body.get('action')
        if action == 'inspect':
            self.inspect_until = self.clock()+120
            self.reader.start()
        elif action == 'enroll':
            if self.enabled or self.owner: raise ValueError('NFC zuerst ausschalten und laufenden Modus beenden.')
            mode = body.get('mode')
            value = self.reader.snapshot()
            tag = value.get('tag', '')
            if mode not in ('talk','meeting') or value.get('state') != 'present' or not re.fullmatch('[0-9a-f]{64}',tag):
                raise ValueError('Leser prüfen und genau den gewünschten Aufsteller auflegen.')
            if any(k != mode and v == tag for k,v in self.tags.items()):
                raise ValueError('Talk und Meeting benötigen unterschiedliche Tags.')
            self.tags[mode] = tag
            self.save()
            self.message = mode.title()+' zugeordnet. Aufsteller wieder abnehmen.'
            self.reset_edge()
        elif action in ('on','off'):
            if action == 'on' and len(set(self.tags.values())) != 2:
                raise ValueError('Zuerst zwei unterschiedliche Tags zuordnen.')
            self.enabled = action == 'on'
            self.reset_edge()
            self.save()
            self.message = 'Aufsteller zunächst abnehmen.' if self.enabled else 'NFC ausgeschaltet. Laufenden Modus am Bildschirm beenden.'
        else: raise ValueError('Unbekannte NFC-Aktion.')
        return self.public()

    def public(self):
        return {'enabled':self.enabled, 'state':self.status, 'message':self.message,
                'assigned':{k:k in self.tags for k in ('talk','meeting')},
                'active_mode':self.owner[0] if self.owner else None,
                'can_enroll':not self.enabled and self.reader.snapshot().get('state') == 'present'}

    def tick(self, start, stop, still_owned):
        now = self.clock()
        if self.owner and not still_owned(*self.owner):
            self.owner = None
            self.reset_edge()  # Manual stop never restarts a held token.
        if not self.enabled and now >= self.inspect_until:
            self.reader.close()
            self.status = 'off'
            return
        try:
            self.reader.start()
            sample = self.reader.snapshot()
        except OSError:
            sample = {'state':'error', 'message':'NFC-Leser konnte nicht gestartet werden.'}
        self.status = sample['state']
        if self.status == 'error':
            self.reset_edge()
            self.message = sample.get('message','Leser prüfen. Laufenden Modus am Bildschirm beenden.')
            return  # Never treat transport failure as token removal.
        if not self.enabled:
            self.message = 'Tag erkannt. Talk oder Meeting zuordnen.' if self.status == 'present' else 'Leser bereit. Aufsteller auflegen.'
            return
        if self.status == 'absent':
            self.present_since = self.tag = None
            if self.empty_since is None: self.empty_since = now
            if now-self.empty_since < 1.5: return
            if self.owner:
                try: stop(*self.owner)
                except Exception:
                    self.message = 'Beenden fehlgeschlagen. Bitte am Bildschirm stoppen.'
                    return
                self.owner = None
            self.armed = True
            self.message = 'Bereit für Talk oder Meeting.'
            return
        self.empty_since = None
        tag = sample.get('tag')
        if tag != self.tag:
            self.tag, self.present_since = tag, now
        if self.owner:
            self.message = self.owner[0].title()+' aktiv. Zum Beenden Aufsteller abnehmen.'
            return
        if not self.armed:
            self.message = 'Zum Start zunächst alle Aufsteller abnehmen.'
            return
        if self.present_since is None or now-self.present_since < .5: return
        self.armed = False
        mode = next((k for k,v in self.tags.items() if v == tag),None)
        if mode is None:
            self.message = 'Unbekannter Aufsteller. In den Einstellungen zuordnen.'
            return
        try:
            identity = start(mode)
            self.owner = (mode, identity)
            self.message = mode.title()+' gestartet.'
        except ValueError as error: self.message = str(error)
        except Exception: self.message = 'Start fehlgeschlagen. Bitte Einrichtung am Bildschirm prüfen.'

    def close(self):
        self.reader.close()
