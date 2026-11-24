"""Explicit recovery of the optional USB-audio board, never an automatic reset.

The installed root-owned helper validates the hardware independently. Studio
only reserves the existing maintenance boundary and observes the result.
"""
import json
from pathlib import Path
import subprocess
import threading
import time
import uuid
from fleet.common import read, save

HELPER = '/usr/local/sbin/cdb-usb-audio-recover'
SOUNDBAR_PREFIX = 'alsa_output.usb-0020_188A_'


class UsbAudioRecovery:
    def __init__(self, helper=HELPER, runner=subprocess.run):
        self.helper, self.runner = helper, runner
        self.lock = threading.RLock()
        self.state = 'idle'
        self.message = ''
        self.running = False
        self.checked_at = 0
        self.hardware = {}

    def check(self, force=False):
        with self.lock:
            if self.running or (self.checked_at and not force and time.monotonic() - self.checked_at < 5):
                return dict(self.hardware)
            self.checked_at = time.monotonic()
            path = Path(self.helper)
            try:
                st = path.stat()
                if not path.is_file() or path.is_symlink() or st.st_uid != 0 or st.st_mode & 0o022:
                    raise ValueError('Die USB-Wiederherstellung ist auf diesem Pi noch nicht eingerichtet.')
                result = self.runner(['/usr/bin/sudo', '-n', self.helper, 'check'],
                                     capture_output=True, text=True, timeout=5)
                data = json.loads(result.stdout)
                if (not isinstance(data, dict) or result.returncode not in (0, 2)
                        or any(type(data.get(k)) is not bool for k in ('supported', 'available', 'device_present'))
                        or not isinstance(data.get('reason'), str)
                        or (data['available'] and (not data['supported'] or result.returncode != 0))):
                    raise ValueError('USB-Erweiterung konnte nicht geprüft werden.')
                self.hardware = {k: data.get(k) for k in ('supported','available','reason','device_present')}
            except (OSError, ValueError, subprocess.SubprocessError):
                self.hardware = {'supported': False, 'available': False,
                                 'reason': 'USB-Wiederherstellung auf diesem Pi noch nicht eingerichtet oder nicht erreichbar.'}
            return dict(self.hardware)

    def public(self):
        hardware = self.check()
        with self.lock:
            return hardware | {'state': self.state, 'running': self.running,
                               'message': self.message or hardware.get('reason', '')}

    def start(self, app, version):
        # Called with the same control/controller/recorder locks as all starts.
        boot = app.management.boot_id()
        if app.preview or not boot:
            raise ValueError('USB-Wiederherstellung nur am eingerichteten Pi verfügbar.')
        if self.running:
            raise ValueError('USB-Wiederherstellung läuft bereits.')
        if app.room.intent or app.cdb.login.get('state') == 'pending':
            raise ValueError('Anmeldung oder Startvorbereitung zuerst abschließen.')
        hardware = self.check(force=True)
        if not hardware.get('available'):
            raise ValueError(hardware.get('reason') or 'USB-Erweiterung ist nicht zur Wiederherstellung freigegeben.')
        command = str(uuid.uuid4())
        try:
            app.management.prepare(app, command, version)
            # The existing prepare() owns all activity checks. Bind this short
            # hardware lease to the current boot so a power cycle clears it.
            lease = read(app.management.marker, {})
            if lease.get('command') != command:
                raise ValueError('USB-Wiederherstellung konnte nicht reserviert werden.')
            save(app.management.marker, {'command': command, 'boot': boot,
                                        'expires': time.time() + 90, 'kind': 'usb-audio-recovery'})
        except Exception:
            # prepare() can fail after writing its marker, e.g. wake cleanup.
            app.management.release(command)
            raise
        with self.lock:
            self.running, self.state = True, 'running'
            self.message = 'USB-Erweiterung wird neu verbunden. Bitte kurz warten.'
        try:
            threading.Thread(target=self._recover, args=(app, command), daemon=True).start()
        except Exception:
            with self.lock:
                self.running, self.state = False, 'failed'
                self.message = 'USB-Wiederherstellung konnte nicht gestartet werden.'
            app.management.release(command)
            raise
        return self.public()

    def _recover(self, app, command):
        result, process = None, None
        message = 'USB-Audio konnte nicht wiederhergestellt werden. Gerätestatus prüfen.'
        try:
            lease = read(app.management.marker, {})
            if (lease.get('command') != command or lease.get('boot') != app.management.boot_id()
                    or lease.get('expires', 0) <= time.time()):
                raise ValueError('USB-Wiederherstellung ist nicht mehr freigegeben. Bitte erneut prüfen.')
            process = subprocess.Popen(['/usr/bin/sudo', '-n', self.helper, 'recover'],
                                       stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
            try:
                output, _ = process.communicate(timeout=45)
            except subprocess.TimeoutExpired:
                # TERM lets sudo forward cancellation to its privileged child.
                # Keep the app reserved until that command has actually exited.
                with self.lock:
                    self.message = 'USB-Wiederherstellung wird noch beendet. Bitte warten.'
                self._confirm_exit(process)
                raise ValueError('Zeitlimit der USB-Wiederherstellung erreicht. Gerätestatus prüfen.')
            data = json.loads(output)
            if not isinstance(data, dict):
                raise ValueError(message)
            if process.returncode != 0 or data.get('recovered') is not True or data.get('device_present') is not True:
                raise ValueError(data.get('reason') or message)
            # USB detection alone does not prove that the audio service is ready.
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                speakers = app.speakers.public()
                soundbars = [d for d in speakers.get('devices', [])
                             if isinstance(d, dict) and isinstance(d.get('id'), str)
                             and d['id'].startswith(SOUNDBAR_PREFIX)]
                if soundbars:
                    result = True
                    message = ('Soundbar wieder verbunden. Bitte den Testton prüfen.'
                               if speakers.get('selected') in {d['id'] for d in soundbars}
                               else 'Soundbar wieder verbunden. Bitte 188A als Lautsprecher auswählen und den Testton prüfen.')
                    break
                time.sleep(.5)
            if not result:
                message = 'USB-Soundbar erkannt, aber noch kein Audioausgang verfügbar. Geräte aktualisieren.'
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            if isinstance(error, ValueError) and str(error):
                message = str(error)[:400]
        finally:
            if process is not None and process.poll() is None:
                with self.lock:
                    self.message = 'USB-Wiederherstellung wird noch beendet. Bitte warten.'
                # On a communication error, never release a live root command.
                self._confirm_exit(process)
            with app.control_lock, app.controller.lock, app.engine.recorder.lock:
                with self.lock:
                    self.state = 'completed' if result else 'failed'
                    self.message = message
                    self.running = False
                    self.checked_at = 0
                app.management.release(command)

    @staticmethod
    def _confirm_exit(process):
        # The helper handles TERM with a final bind attempt. Retain the app's
        # maintenance reservation if the kernel has not released the process.
        while process.poll() is None:
            try:
                process.terminate()
            except OSError:
                pass
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                continue
            except OSError:
                time.sleep(.25)
