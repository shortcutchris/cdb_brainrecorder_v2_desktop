"""Studio HTTP adapter for the existing native data and shared DesktopEngine.

Loopback only. No second recorder, worker, model pipeline or session database.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import hmac
import json
import logging
import mimetypes
import os
from pathlib import Path
import secrets
import shutil
import signal
import subprocess
import threading
import time
from http.server import ThreadingHTTPServer
from urllib.parse import urlsplit

from data.repo import SessionRepository
from services.local_controller import LocalController
from settings import SettingsManager
from services.cdb_integration import CdbService, CdbBackend
from meeting_recorder.audio import BYTES_PER_SECOND, devices
from meeting_recorder.core import atomic_write
from meeting_recorder.server import Handler, Server, App as SharedWebApp
from meeting_recorder.child_process import owned_command

VERSION = '1.0.0-rc5'
STATIC = Path(__file__).parent/'studio'
FIELDS = ('title', 'notes', 'transcript_text', 'summary_text')
BUSY = ('recording', 'importing', 'queued', 'transcribing', 'summarizing')


class Conflict(ValueError): pass


class StudioApp:
    def __init__(self, root, database, backend=None, command_factory=None, preview=False, settings_file=None):
        self.cdb = CdbService(root)
        from services.room_mode import RoomMode
        self.room = RoomMode(root, self.cdb)
        self.job_context = None
        self.cdb_backend = CdbBackend(self.cdb) if backend is None else None
        self.repo = SessionRepository(str(database))
        # PipeWire may retain the ALSA device after wake listening stops. Use
        # the same explicitly mapped source for recording and microphone tests.
        if command_factory is None:
            command_factory = self.capture_command
        self.controller = LocalController(self.repo, root, backend=backend or self.cdb_backend, command_factory=command_factory)
        self.engine = self.controller.engine
        self.store, self.models, self.probe = self.engine.store, self.engine.models, self.engine.probe
        if self.cdb_backend:self.cdb_backend.store = self.store
        create = self.store.create
        def create_bound(title):
            snapshot = self.job_context['route'] if self.job_context else self.cdb.snapshot()
            owner = self.job_context['owner'] if self.job_context else (self.room.account() if self.room.enabled else None)
            if self.room.enabled and owner is None:
                self.room.require_account()
            ident = create(title)
            atomic_write(self.store.folder(ident)/'cdb-request.json',json.dumps(snapshot))
            if owner is not None: self.room.bind(self.store.folder(ident), owner)
            return ident
        self.store.create = create_bound
        self.cdb.thread(self.cdb.run)
        self.token = ''
        self.csrf = secrets.token_urlsafe(32)
        self.preview = preview
        self.settings_file = Path(settings_file).resolve() if settings_file else None
        if self.settings_file:self.settings_file.parent.mkdir(parents=True,exist_ok=True)
        self.settings_lock = threading.RLock()
        self.control_lock = threading.RLock()
        self.recording_owner = ThreadPoolExecutor(max_workers=1, thread_name_prefix='studio-recording')
        self.probe_started_ns = 0
        from services.device_management import DeviceManagement
        self.management = DeviceManagement(self.store.root)
        from services.first_start import FirstStart
        self.first_start = FirstStart(self.store.root)
        self.closing = False
        from services.audio_output import AudioOutput
        self.speakers = AudioOutput(self.store.root)
        from services.usb_audio_recovery import UsbAudioRecovery
        self.usb_recovery = UsbAudioRecovery()
        from services.device_sounds import DeviceSounds
        self.device_sounds = DeviceSounds(self.store.root)
        self.device_sounds_hardware = not preview and backend is None
        from services.announcements import Announcements
        self.announcements = Announcements(self.store.root)
        self.announcement_playing = False
        self.countdown = None
        from services.bluetooth_audio import BluetoothAudio
        self.bluetooth = BluetoothAudio(enabled=not preview and backend is None)
        from services.model_checks import ModelChecks
        self.model_checks = ModelChecks(self)
        self.model_test = None
        test_id = self.store.root/'model-test'/'job.txt'
        if test_id.is_file():
            try:
                candidate=test_id.read_text().strip();self.store.get(candidate)
                self.model_test=candidate
            except (OSError,KeyError,ValueError):pass

        from services.live_conversation import LiveConversation
        self.live = LiveConversation(self.cdb, self.store.root, audio_config=self.live_audio_config)
        from services.remote_control import RemoteControl
        self.remote_control = RemoteControl(self)
        from services.remote_display import DisplayHub
        self.display = DisplayHub(self.live, self.display_account)
        self.display_preferences = self.store.root/'display-enabled.json'
        from services.respeaker_leds import ReSpeakerLeds
        self.respeaker = ReSpeakerLeds(self.store.root, self.respeaker_state, enabled=not preview and backend is None)
        from services.wake_word import WakeWord
        from services.schedules import Schedules
        from services.nfc_tokens import NfcTokens
        self.nfc = NfcTokens(self.store.root)
        self.wake = WakeWord(self.store.root)
        self.schedules = Schedules(self.store.root)
        self.schedules.room_policy = lambda: (self.room.enabled, self.room.account())
        from services.voice_device import VoiceDevice, device_status, NAMES as VOICE_DEVICE_NAMES
        from services.voice_actions import VoiceActions
        self.voice_actions = VoiceActions(self)
        self.voice_device = VoiceDevice(self.store.root, self.speakers, lambda: device_status(self), actions=self.voice_actions)
        from services.workshops import Workshops, NAMES as WORKSHOP_NAMES
        self.workshops = Workshops(self.store.root, self.cdb, self.wake_account)
        self.live.device_executor = lambda scope, request: (
            self.workshops.execute(scope, request) if request.get('name') in WORKSHOP_NAMES else
            self.voice_device.execute(scope, request) if request.get('name') in VOICE_DEVICE_NAMES
            else self.schedules.execute_tool(scope, request, self.clock_ready))
        self.playback_leases = {}
        self.ambient_stop = threading.Event()
        self.alarm_id = None
        self.clock_ready = False
        self.ambient_error = ''
        self.output_busy_until = 0
        from services.remote_control_transport import create_channel
        self.remote_channel = create_channel(self, start=not preview and backend is None)
        from services.local_portal import LocalPortal
        self.portal = LocalPortal(self, VERSION)
        self.ambient_thread = threading.Thread(target=self.ambient_loop, daemon=True)
        self.ambient_thread.start()

    def wake_account(self):
        # Token expiry is not a logout. Keep local opt-in bound to the saved
        # identity; the background start still calls Cdb.session(), refreshing and
        # validating the account BEFORE cloud audio is connected.
        session = self.cdb.read('session.json', {})
        identity = session.get('identity')
        config = self.cdb.config()
        if not identity or session.get('server') != config['server'] or session.get('client_id') != config['client_id']:
            return None
        return {'server': session['server'], 'user_id': identity['user_id'], 'client_id': identity['client_id']}

    def wake_reason(self):
        import time
        activity = self.activity()
        if activity.occupied: return activity.reason
        if any(deadline > time.monotonic() for deadline in self.playback_leases.values()):
            return 'Audiowiedergabe läuft.'
        if self.alarm_id: return 'Timer-Signal läuft.'
        if self.output_busy_until > time.monotonic(): return 'Audioausgabe am Pi läuft.'
        return ''

    def wake_start(self):
        # Called under the same control/controller/recorder locks as Record and Live.
        reason = self.wake_reason()
        if reason: raise ValueError(reason)
        if not self.wake.enabled or self.wake.account != self.wake_account():
            raise ValueError('Brain-Anmeldung oder Freigabe hat sich geändert.')
        return self._start_device_live_locked(self.wake.account)

    def _start_device_live_locked(self, binding):
        """Caller owns the control/controller/recorder locks and input consent."""
        self.require('live')
        path = self.live.root/('areas-'+self.live._selection_key(binding)+'.json')
        try: remembered = json.loads(path.read_text())
        except (OSError, ValueError): raise ValueError('Im Live-Gespräch zuerst Wissensbereiche auswählen.') from None
        if remembered.get('binding') != binding or not remembered.get('area_ids'):
            raise ValueError('Im Live-Gespräch zuerst Wissensbereiche auswählen.')
        self.live_audio_config()
        self.cdb.invalidate_pending_login()
        if binding != self.wake_account():
            raise ValueError('Brain-Konto hat sich geändert.')
        lease = self.live.reserve(remembered['area_ids'], owner_kind='device', cached_binding=binding)['lease']
        try: self.live.start_native(lease)
        except Exception:
            self.live.end(lease)
            raise
        return lease

    def nfc_start(self, mode):
        if mode not in ('talk', 'meeting'): raise ValueError('Talk oder Meeting wählen.')
        reason = self.wake_reason()
        if reason: raise ValueError(reason)
        intent = self.room.intent
        if self.room.enabled and (not self.room.account() or intent or not self.nfc.direct_start[mode]):
            # Replacing the same tag after a reader dropout must not cancel
            # its pending device login or silently extend its deadline.
            if not intent or intent['mode'] != mode or intent['tag'] != self.nfc.tag:
                self.room.begin(mode, self.nfc.tag)
            raise ValueError('Am Bildschirm anmelden und den Start bestätigen.')
        try:
            if mode == 'meeting':
                identity = self.action('/api/record/start', {})['id']
            else:
                account = self.wake_account()
                if not account: raise ValueError('Für Talk zuerst beim Brain anmelden.')
                self.wake.suspend('NFC-Gespräch startet.')
                identity = self._start_device_live_locked(account)
        except ValueError as error:
            if self.room.enabled:
                self.room.begin(mode, self.nfc.tag)
                self.room.intent['message'] = str(error)
            raise
        self.room.touch()
        return identity

    def nfc_still_owned(self, mode, identity):
        if mode == 'meeting': return self.engine.recorder.status().get('id') == identity
        with self.live.lock:
            return self.live.lease == identity and self.live.public()['busy']

    def nfc_stop(self, mode, identity):
        if not self.nfc_still_owned(mode, identity): return
        if mode == 'meeting': self.action('/api/record/stop', {})
        else: self.live.end(identity)

    def remote_live_command(self, envelope, verified_grant):
        return self.remote_control.command(envelope, verified_grant)

    def speech_context_allowed(self):
        import time
        activity = self.activity()
        return (not activity.occupied and not activity.pending and not self.closing
                and self.wake.test_until <= time.monotonic()
                and not any(deadline > time.monotonic() for deadline in self.playback_leases.values()))

    def speech_allowed(self):
        import time
        return self.speech_context_allowed() and self.output_busy_until <= time.monotonic()

    def tick_announcements(self):
        import time
        if self.announcement_playing and self.speakers.test_status()['state'] != 'running':
            self.announcement_playing = False
            self.output_busy_until = max(self.output_busy_until, time.monotonic() + 2)
        # No transcript, tokens, error text or audio are passed to speech.
        with self.live.lock:
            event = self.live.announcement_failure
            safe = (self.speech_context_allowed() and self.live.state == 'error' and event is not None
                    and event['sequence'] == self.live.generation
                    and event['account_generation'] == self.cdb.generation)
            clip = self.announcements.failure_clip(event, safe, quiet=self.output_busy_until <= time.monotonic())
        if clip:
            self.wake.suspend('Lokale Ansage läuft.')
            self.speakers.start_announcement(clip)
            self.announcement_playing = True

    def tick_device_sounds(self):
        if not self.device_sounds.take_startup():
            return
        # No delayed welcome after recording, login, maintenance or another
        # activity. Failure to play a decorative cue leaves the app usable.
        if not self.device_sounds_hardware or not self.speech_allowed():
            return
        try:
            self.wake.suspend('Startklang läuft.')
            self.speakers.start_chime('startup')
            self.announcement_playing = True
        except ValueError:
            pass

    def stop_countdown(self):
        import time
        if self.countdown is not None:
            self.speakers.stop_test()  # Retain ownership on failed cleanup.
            self.countdown = None
            self.announcement_playing = False
            self.output_busy_until = max(self.output_busy_until, time.monotonic() + 2)

    def tick_countdown(self):
        """Under device locks, use only the timer deadline, never labels/content."""
        import time
        candidate = self.schedules.claim_countdown(self.clock_ready)
        if self.countdown is not None:
            valid = any(item['id'] == self.countdown['id'] and
                        item['revision'] == self.countdown['revision'] and item['state'] == 'scheduled'
                        for item in self.schedules.items())
            if (not valid or time.monotonic() >= self.countdown['end_at'] or
                    self.speakers.test_status()['state'] != 'running'):
                self.stop_countdown()
            return
        clip = self.announcements.countdown_clip()
        if candidate and clip and self.speech_allowed():
            self.wake.suspend('Timer zählt herunter.')
            try: self.speakers.start_countdown(clip, candidate['end_at'])
            except ValueError: return  # Skip; the normal alarm remains due on time.
            self.countdown = candidate
            self.announcement_playing = True

    def tick_alarm(self):
        """Called under the device control locks; Live does not defer an alarm."""
        if self.alarm_id and not any(i['id']==self.alarm_id and i['state']=='due' for i in self.schedules.items()):
            self.speakers.stop_test(); self.alarm_id = None
        if self.alarm_id and self.speakers.test_status()['state'] != 'running':
            outcome = 'played' if self.speakers.test_status()['state']=='completed' else 'failed'
            self.schedules.sound_result(self.alarm_id, outcome)
            self.alarm_id = None
        if self.activity().alarm_allowed:
            for item in self.schedules.items():
                if item['state']=='due' and item['sound']=='pending':
                    if item.get('tone') == 'silent':
                        self.schedules.sound_result(item['id'], 'silent'); continue
                    clip = self.announcements.timer_clip(item['kind']) if self.speech_allowed() else None
                    self.wake.suspend('Timer-Signal läuft.')
                    # Claim before playback: at most one attempt after a crash.
                    self.schedules.sound_result(item['id'],'attempted')
                    try:
                        if clip is None: self.speakers.start_alarm(item.get('tone','bell'))
                        else: self.speakers.start_alarm(item.get('tone','bell'), announcement=clip)
                        self.alarm_id = item['id']
                    except ValueError as error:
                        logging.warning('timer_audio_start_failed: %s', error)
                        self.schedules.sound_result(item['id'],'failed')
                    break

    def ambient_loop(self):
        import time
        next_clock = 0
        next_output = 0
        while not self.ambient_stop.wait(.5):
            try:
                if time.monotonic() >= next_clock:
                    try:
                        result = subprocess.run(['timedatectl','show','-p','NTPSynchronized','--value'], capture_output=True,text=True,timeout=2)
                        self.clock_ready = result.returncode == 0 and result.stdout.strip() == 'yes'
                    except (OSError, subprocess.SubprocessError): self.clock_ready = False
                    next_clock = time.monotonic()+60
                if (self.wake.enabled or self.wake.test_until or self.room.config.get('ambient_activity') or any(self.announcements.enabled.values())) and time.monotonic() >= next_output:
                    try:
                        output = subprocess.run(['pactl','-f','json','list','sink-inputs'],capture_output=True,text=True,timeout=2)
                        if output.returncode != 0: raise ValueError()
                        if any(not row.get('corked',False) for row in json.loads(output.stdout)):
                            self.output_busy_until = time.monotonic()+2
                    except (OSError, ValueError, subprocess.SubprocessError):
                        self.output_busy_until = time.monotonic()+2
                    next_output = time.monotonic()+1
                self.schedules.tick(self.clock_ready)
                with self.control_lock, self.controller.lock, self.engine.recorder.lock:
                    if self.closing: return
                    self.playback_leases = {key:value for key,value in self.playback_leases.items() if value>time.monotonic()}
                    self.tick_countdown()
                    self.tick_alarm()
                    self.tick_announcements()
                    self.tick_device_sounds()
                    self.nfc.tick(self.nfc_start, self.nfc_stop, self.nfc_still_owned)
                    reason = self.wake_reason()
                    self.wake.tick(account=self.wake_account(),reason=reason,
                                   config=self.store.config(),trigger=self.wake_start,
                                   monitor=self.room.config.get('ambient_activity') is True, on_activity=self.room.touch)
                    self.tick_room()
                    self.ambient_error = ''
            except Exception as error:
                with self.control_lock:
                    try:
                        self.wake.suspend(str(error) if isinstance(error,ValueError) else 'Lokale Bereitschaft unterbrochen. Geräte prüfen.')
                    except ValueError:
                        # The detector remains owned and will retry its cleanup.
                        # A second stop failure must not kill the ambient loop.
                        pass
                    self.wake.cooldown = time.monotonic()+10
                    self.ambient_error = 'Bereitschaft prüfen.'


    def display_account(self):
        import time
        session = self.cdb.read('session.json', {})
        identity = session.get('identity')
        if not identity or session.get('expires', 0) <= time.time(): return None
        if session.get('server') != self.cdb.config()['server']: return None
        return {'binding': {'server': session['server'], 'user_id': identity['user_id'],
                            'client_id': identity['client_id']}, 'generation': self.cdb.generation}

    def live_audio_config(self):
        device=self.store.config()['device']
        microphone=next((d for d in self.audio_devices().get('devices',[]) if d['id']==device),None)
        if not microphone:raise ValueError('Das eingerichtete Pi-Mikrofon fehlt. Unter Einstellungen → Audio prüfen.')
        speaker=self.speakers.public()
        if not speaker['available']:raise ValueError(speaker['message'])
        if speaker['muted'] or speaker['volume']==0:raise ValueError('Pi-Lautsprecher ist stumm. Unter Einstellungen → Audio einschalten.')
        output=next(d for d in speaker['devices'] if d['id']==speaker['selected'])
        return {'device':device,'speaker':speaker['selected'],'microphone_label':microphone['label'],'speaker_label':output['label'],
                'connecting_announcement':self.announcements.connecting_clip()}

    def respeaker_state(self):
        recording=self.engine.recorder.status()
        live=self.live.public()
        if not recording['id'] and live.get('transport')=='pi' and live['busy']:
            recording={'id':'live','muted':live['muted'],'paused':False}
        return {'device':self.store.config()['device'],'recording':recording,'probe':self.probe.status()['state']=='running'}

    def activity(self, state=None, include_bluetooth=True):
        from services.app_activity import AppActivity
        state = state or self.engine.state()
        live = self.live.public() if hasattr(self, 'live') else {'state':'idle','busy':False}
        return AppActivity(maintenance=self.management.busy() or self.first_start.busy or self.usb_recovery.running, recording=bool(state['recording']['id']), paused=state['recording'].get('paused',False),
            live=live['state'], live_reserved=live['busy'], microphone_test=state['microphone_test']['state']=='running',
            speaker_test=self.speakers.test_status()['state']=='running', alarm=bool(self.alarm_id),
            bluetooth=include_bluetooth and self.bluetooth.busy(),
            download=state['installation']['state']=='running',
            model_test=self.model_checks.public()['state']=='running' or bool(self.model_test and self.store.get(self.model_test)['state'] in BUSY),
            pending=any(j['state'] in BUSY for j in state['jobs']))

    def capabilities(self, state=None):
        state = state or self.engine.state()
        cdb_config=self.cdb.config()
        signed_in=bool(self.cdb.read('session.json',{}).get('identity'))
        needs_login=(self.room.enabled or 'cdb' in (cdb_config['transcription'],cdb_config['summary'])) and not signed_in
        return self.activity(state).capabilities(
            low_disk=self.store.free_mb()<state['config'].get('min_free_mb',1024), needs_login=needs_login,
            setup_complete=state['config']['setup_complete'], brain_signed_in=signed_in)

    def require(self, capability):
        rule = self.capabilities()[capability]
        if not rule['allowed']: raise ValueError(rule['reason'])

    def capture_command(self, config):
        from services.live_audio import native_capture_command
        return native_capture_command(config, timed_probe=self.engine.recorder.probe)

    def microphone_progress(self, result):
        if result['state'] == 'running':
            raw = self.probe.folder / 'audio.pcm'
            try:
                stat = raw.stat()
            except FileNotFoundError:
                stat = None
            recorded = stat.st_size if stat and stat.st_mtime_ns >= self.probe_started_ns else 0
            if stat is None:
                # Finalizing replaces the raw data with the completed WAV.
                try:
                    if (self.probe.folder / 'audio.wav').stat().st_mtime_ns >= self.probe_started_ns:
                        recorded = 5 * BYTES_PER_SECOND
                except FileNotFoundError:
                    pass
            return result | {'seconds_left': max(0, 5 - recorded // BYTES_PER_SECOND)}
        if result['state'] == 'completed':
            try:
                sample = (self.probe.folder / 'audio.wav').stat()
                if sample.st_size > 44:
                    return result | {'sample_id': str(sample.st_mtime_ns)}
            except FileNotFoundError:
                pass
            return result | {'state': 'failed', 'message': 'Testaufnahme fehlt. Bitte erneut testen.'}
        return result

    def audio_devices(self): return devices()
    def setup_state(self):
        self.finish_model_validation()
        result=SharedWebApp.setup_state(self)
        providers=self.cdb.config();checks=result['checks']
        result['probe'] = self.microphone_progress(result['probe'])
        checks[0]['ok'] = checks[0]['ok'] and result['probe']['state'] == 'completed'
        result['checks']=[check for i,check in enumerate(checks) if i==0 or i in (1,2) and providers['transcription']=='local' or i in (3,4) and providers['summary']=='local']
        if 'cdb' in (providers['transcription'],providers['summary']):result['checks'].append({'label':'CDB-Firmenanmeldung','ok':bool(self.cdb.read('session.json',{}).get('identity'))})
        result['ready']=all(check['ok'] for check in result['checks'])
        try:self.model_test_preflight();reason=""
        except ValueError as e:reason=str(e)
        except OSError:reason="Modelltest wartet: Kühlung, Temperatur oder Arbeitsspeicher prüfen."
        result["catalog"]["test_block_reason"]=reason
        return result

    def finish_model_validation(self):
        path=self.store.root/'model-test'/'pair.json'
        if not self.model_test or not path.exists():return
        pending=json.loads(path.read_text())
        if pending.get('id')!=self.model_test or pending.get('processed'):return
        job=self.store.get(self.model_test)
        if job['state'] not in ('completed','failed'):return
        result=self.engine.result(self.model_test)
        if job['state']=='completed' and result.get('transcript','').strip() and result.get('summary','').strip():
            catalog=self.models.catalog()
            entries=pending['entries']
            unchanged=all(any(m['id']==old['id'] and m['fingerprint']==old['fingerprint'] for m in catalog['asr' if backend=='whisper' else 'llm']) for backend,old in entries.items())
            if unchanged:self.models.validate_pair(entries)
        atomic_write(path,json.dumps(pending|{'processed':True}))

    @staticmethod
    def model_test_preflight():
        model=Path('/proc/device-tree/model')
        if not model.exists() or b'Raspberry Pi' not in model.read_bytes():return
        temperature=int(Path('/sys/class/thermal/thermal_zone0/temp').read_text())/1000
        fans=list(Path('/sys/class/hwmon').glob('hwmon*/fan1_input'))
        if any(int(p.read_text())==0 and (int((p.parent/'pwm1').read_text())>0 if (p.parent/'pwm1').exists() else temperature>=50) for p in fans):
            raise ValueError('Modelltest wartet: Kühlung angefordert, Lüfter meldet 0 U/min. Anschluss und Lüfter prüfen.')
        if temperature>=65:raise ValueError('Modelltest wartet: Gerät zuerst unter 65 °C abkühlen lassen.')
        available=next(int(x.split()[1]) for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:'))
        if available<4*1024**2:raise ValueError('Modelltest wartet: mindestens 4 GiB verfügbarer Arbeitsspeicher erforderlich.')


    @staticmethod
    def audio_file_bytes(*paths):
        for path in paths:
            try:
                return path.stat().st_size
            except OSError:
                continue
        return None

    def state(self):
        with self.control_lock, self.controller.lock:
            self.controller.sync()
            state = self.engine.state()
            state['microphone_test'] = self.microphone_progress(state['microphone_test'])
            for job in state['jobs']:
                folder = self.store.folder(job['id'])
                job['waiting_for_brain'] = job['state'] == 'failed' and (folder/'brain-wait.json').exists()
                job['audio_file_bytes'] = self.audio_file_bytes(folder/'audio.wav', folder/'audio.pcm', folder/'audio.import.wav')
                if job['state'] == 'transcribing' and self.cdb_backend:
                    job['whisper_progress'] = self.cdb_backend.local.progress_for(job['id'])
                job['processing_detail'] = state['progress'] if job['state'] in ('transcribing', 'summarizing') else ''
            rows = self.repo.get_all()
            state['sessions'] = [{k:r.get(k) for k in ('id','title','recorded_at','duration_sec',
                'samplerate','channels','transcription_status','local_job_id','local_error')}
                | {'has_audio': bool(r.get('path') and Path(r['path']).is_file()),
                   'audio_file_bytes': self.audio_file_bytes(Path(r['path'])) if r.get('path') else None} for r in rows]
        raw = b''
        ident = state['recording']['id']
        if ident:
            path = self.store.folder(ident)/'audio.pcm'
            try:
                with path.open('rb') as f:
                    f.seek(max(0,path.stat().st_size-32000));raw=f.read(32000)
            except OSError: pass
        # Actual bounded PCM measurements, never decorative fake microphone levels.
        if state['recording'].get('paused') or state['recording'].get('muted'):raw=b''
        if raw:
            import numpy as np
            samples = np.frombuffer(raw[:len(raw)//2*2],dtype='<i2').astype('float32')/32768
            state['waveform'] = [float(abs(chunk).max()) if len(chunk) else 0 for chunk in np.array_split(samples,64)]
        else: state['waveform'] = [0]*64
        state['level'] = self.probe.level(raw) if raw else 0
        state['capabilities'] = self.capabilities(state)
        state['activity'] = self.activity(state).public()
        state['remote_control'] = self.remote_channel.public()
        state['portal'] = self.portal.public()
        state['management'] = self.management.public()
        state['first_start'] = self.first_start.public(state['management'])
        state['cdb'] = self.cdb.public()
        state['model_check'] = self.model_checks.public()
        state['model_results'] = self.model_checks.results()
        state['speaker_test'] = self.speakers.test_status()
        state['announcements'] = self.announcements.public()
        state['device_sounds'] = self.device_sounds.public()
        state['respeaker'] = self.respeaker.public()
        state['live'] = self.live.public()
        state['display'] = self.display.status()
        from services.device_health import lcd_usb_status
        state['lcd_status'] = lcd_usb_status()
        self.voice_actions.observe(state)
        state['voice_ui'] = self.voice_actions.public()
        state['workshops'] = self.workshops.list(self.wake_account())
        state['device_clock'] = {'ready': self.clock_ready, 'text': time.strftime('%H:%M') if self.clock_ready else '--:--'}
        state['wake'] = self.wake.public()
        state['nfc'] = self.nfc.public()
        state['timers'] = {'items': self.schedules.items(), 'ringing_id': self.alarm_id, 'clock_ready': self.clock_ready, 'voice_available': bool(self.live.public().get('device_tools'))}
        visible_timers = self.schedules.visible_ids()
        state['timers']['items'] = [item for item in state['timers']['items'] if item['id'] in visible_timers]
        if self.alarm_id not in visible_timers: state['timers']['ringing_id'] = None
        state['bluetooth'] = self.bluetooth.public()
        state.update(csrf=self.csrf, version=VERSION, preview=self.preview,
            namespace=hashlib.sha256(str(self.store.root).encode()).hexdigest()[:16])
        if self.model_test:
            job = self.store.get(self.model_test)
            state['model_test'] = job | self.engine.result(self.model_test)
            self.finish_model_validation()
        state['room'] = self.room.public()
        state['room']['ambient_state'] = self.wake.mode if state['room']['ambient_activity'] and state['room']['signed_in'] else 'off'
        state['sessions'] = [row for row in state['sessions'] if self.visible_session(row)]
        state['jobs'] = [job for job in state['jobs'] if self.room.can_read(self.store.folder(job['id']))]
        # Global worker strings can name a different account's meeting.
        if self.room.enabled:
            state['namespace'] += ':' + self.room.epoch
            state['progress'] = ''
            for job in state['jobs']: job['processing_detail'] = ''
            state['cdb']['progress'] = ''
            if not self.room.operator():
                state['model_results'] = []; state.pop('model_test', None)
            if not self.room.account():
                state['live'] = {'state':'idle','busy':False,'muted':True,'history':[],'areas':[]}
                state['timers']['items'] = []
        return state

    def visible_session(self, row):
        ident = row.get('local_job_id')
        return self.room.can_read(self.store.folder(ident) if ident else None)

    def tick_room(self):
        self.room.reconcile(self.nfc)
        if self.room.intent and self.room.intent['tag'] and self.nfc.status != 'error':
            self.nfc.message = ('Aufsteller erkannt · Anmeldung und Start am Bildschirm bestätigen.'
                                if self.room.intent['tag_present'] else
                                'Anmeldung bleibt offen · Zum Start denselben Aufsteller wieder auflegen.')
        if self.room.enabled and self.room.account():
            playback = any(deadline > time.monotonic() for deadline in self.playback_leases.values())
            self.room.observe_activity(self.activity(), playback)
            if not self.room.idle_suspended and self.room.idle_remaining() == 0:
                self.room_logout()

    def room_logout(self):
        """Only after capture/live has stopped successfully; never delete meetings."""
        if self.engine.recorder.active or self.live.busy():
            raise ValueError('Aufnahme oder Gespräch zuerst erfolgreich beenden.')
        self.wake.configure(False, None)
        self.display.revoke()
        self.cdb.logout()
        self.live.clear()
        self.live.restored_binding = None
        self.remote_channel._sync_account()
        self.room.reset()
        self.nfc.reset_edge()
        self.playback_leases.clear()
        self.csrf = secrets.token_urlsafe(32)

    def room_action(self, path, body):
        action = path.removeprefix('/api/room/')
        if action == 'unlock':
            self.room.unlock(body.get('pin'))
        elif action == 'configure':
            self.require('configure')
            if self.activity().pending: raise ValueError('Laufende Verarbeitung zuerst abschließen.')
            self.wake.suspend('Geräteschutz wird angepasst.')
            self.room.configure(body)
            self.room.operator_until = 0
            self.room.touch()
        elif action == 'touch':
            self.room.touch()
        elif action == 'cancel':
            self.room.cancel()
        elif action == 'begin':
            self.require('configure')
            self.room.begin(body.get('mode'))
        elif action == 'finish':
            # Logout never doubles as Stop, even for stale confirmed dialogs.
            # action() holds the same lock as recording/Live start throughout.
            self.require('configure')
            self.room_logout()
        elif action == 'start':
            intent = self.room.check_intent(body.get('id'), self.nfc)
            if intent['mode'] == 'meeting':
                ident = self.action('/api/record/start', {})['id']
            else:
                self.wake.suspend('Gespräch startet.')
                ident = self._start_device_live_locked(self.room.account())
            if intent['tag']: self.nfc.owner = (intent['mode'], ident)
            self.room.cancel(); self.room.touch()
            return {'id': ident, 'mode': intent['mode']}
        else: raise KeyError('Unbekannte Raumaktion.')
        return self.room.public()

    def room_guard(self, path):
        if not self.room.enabled: return
        # Only these operations are available to room users. Other device changes
        # require a short-lived operator unlock; it grants no content access.
        user_paths = ('/api/room/', '/api/record/', '/api/live/', '/api/sessions/', '/api/voice-ui/')
        user_exact = {'/api/cdb/login', '/api/cdb/login/cancel', '/api/cdb/logout',
                      '/api/cdb/area', '/api/cdb/send', '/api/playback', '/api/timers'}
        if not path.startswith(user_paths) and path not in user_exact:
            self.room.require_operator()
        if path.startswith(('/api/record/', '/api/live/', '/api/sessions/', '/api/voice-ui/')) or path in ('/api/cdb/area','/api/cdb/send','/api/timers'):
            self.room.require_account()

    def session(self, sid):
        with self.controller.lock:
            self.controller.sync()
            row = self.repo.get_by_id(sid)
        if not row: raise KeyError('Meeting fehlt.')
        if not self.visible_session(row): raise KeyError('Meeting fehlt oder gehört zu einem anderen Konto.')
        return row

    def save(self, sid, changes, base):
        self.session(sid)
        if not isinstance(changes,dict) or not changes or set(changes)-set(FIELDS):
            raise ValueError('Ungültige Textfelder.')
        if not isinstance(base,dict) or set(changes)-set(base): raise ValueError('Textbasis fehlt.')
        if any(not isinstance(v,str) or len(v)>1_000_000 for v in changes.values()):
            raise ValueError('Text ist ungültig oder zu groß.')
        with self.controller.lock:
            self.controller.sync()
            with self.repo.connection() as db:
                db.execute('BEGIN IMMEDIATE')
                db.row_factory = __import__('sqlite3').Row
                row = db.execute('SELECT * FROM sessions WHERE id=?',(sid,)).fetchone()
                if not row: raise KeyError('Meeting fehlt.')
                if row['transcription_status'] in BUSY and set(changes)-{'title','notes'}:
                    raise Conflict('KI-Texte erst nach Abschluss bearbeiten. Entwurf bleibt erhalten.')
                if any((row[k] or '') != base[k] for k in changes):
                    raise Conflict('Text wurde zwischenzeitlich geändert. Entwurf bleibt erhalten; zuerst exportieren und vergleichen.')
                db.execute('UPDATE sessions SET '+','.join(k+'=?' for k in changes)+' WHERE id=?',
                           [*changes.values(),sid])
        return self.session(sid)

    def settings_manager(self):
        if self.room.enabled:
            from PySide6.QtCore import QSettings
            key = hashlib.sha256(json.dumps(self.room.account(), sort_keys=True).encode()).hexdigest()
            directory = self.store.root/'room-prompts'; directory.mkdir(mode=0o700, exist_ok=True)
            return SettingsManager(QSettings(str(directory/(key+'.ini')), QSettings.IniFormat))
        if self.settings_file:
            from PySide6.QtCore import QSettings
            return SettingsManager(QSettings(str(self.settings_file),QSettings.IniFormat))
        return SettingsManager()

    def prompts(self):
        with self.settings_lock:
            settings=self.settings_manager();settings.settings.sync()
            return settings.get_all_prompts()

    def mutate_prompt(self, body):
        with self.settings_lock:
            settings=self.settings_manager();settings.settings.sync()
            action=body.get('action');ident=body.get('id')
            if action in ('update','delete'):
                current=settings.get_prompt_by_id(ident)
                if not current or current.get('is_default'):raise ValueError('Standardprompt bleibt unverändert. Eigenen Prompt anlegen.')
            if action != 'delete':
                if not isinstance(body.get('name'),str) or not 1<=len(body['name'].strip())<=120:raise ValueError('Promptname fehlt.')
                if not isinstance(body.get('text'),str) or not 1<=len(body['text'])<=16000:raise ValueError('Prompttext fehlt oder ist zu lang.')
            if action=='add':settings.add_prompt(body['name'].strip(),body['text'])
            elif action=='update':settings.update_prompt(ident,body['name'].strip(),body['text'])
            elif action=='delete':settings.delete_prompt(ident)
            else:raise ValueError('Unbekannte Promptaktion.')
            settings.settings.sync()
            if settings.settings.status()!=settings.settings.Status.NoError:raise OSError('Prompts konnten nicht gespeichert werden.')
            return settings.get_all_prompts()

    def start_model_test(self, entries=None):
        if self.model_test and self.store.get(self.model_test)['state'] not in ('completed','failed'):
            raise ValueError('Modelltest läuft bereits.')
        if not shutil.which('espeak-ng'):raise ValueError('Programm für künstliche Testsprache fehlt. Bitte Installation prüfen.')
        folder=self.store.root/'model-test';folder.mkdir(exist_ok=True)
        text='Dies ist ein technischer Modelltest. Anna erstellt bis Donnerstag eine Aufgabenliste. Fortsetzung am Freitag um zehn Uhr. Die Kosten sind ungeklärt.'
        subprocess.run(owned_command(['espeak-ng','-v','de','-s','145','-w',str(folder/'spoken.wav'),text]),
                       check=True,timeout=30,capture_output=True)
        with self.controller.lock:
            previous_context = self.job_context
            self.job_context = {'owner': {'technical': 'model-test'},
                                'route': {'transcription':'local','summary':'local','binding':None}}
            try:
                ident=self.engine.enqueue(folder/'spoken.wav','Technischer Modelltest · künstliche Sprache',test_config=None if entries is None else {'whisper_model':entries['whisper']['path'],'summary_model':entries['ollama']['id'],'model_test':True})
            finally:
                self.job_context = previous_context
            if entries:atomic_write(folder/'pair.json',json.dumps({'id':ident,'entries':entries}))
            with self.store.db() as db:
                db.execute('CREATE TABLE IF NOT EXISTS hidden_jobs (id TEXT PRIMARY KEY)')
                db.execute('INSERT OR IGNORE INTO hidden_jobs VALUES(?)',(ident,))
            self.model_test=ident
            atomic_write(folder/'job.txt',ident)
            atomic_write(folder/'expected.txt',text)
        return {'id':ident}

    def workshop_action(self, body):
        binding = self.wake_account()
        if not binding: raise ValueError('Bitte zuerst am Brain anmelden.')
        action = body.get('action')
        if action != 'read': self.room.touch()
        if action == 'create':
            self.require('live')
            if set(body) != {'action', 'format', 'title', 'goal', 'minutes'}: raise ValueError('Ungültiger Auftrag.')
            return self.workshops.create(binding, body['format'], body['title'], body['goal'], body['minutes'])
        ident = body.get('id')
        if action == 'read' and set(body) == {'action', 'id'}: return self.workshops.get(binding, ident)
        if self.live.busy() and ident != getattr(self.live, 'workshop_id', None):
            raise ValueError('Nur das aktuelle Gesprächsergebnis kann während Talk bearbeitet werden.')
        if action == 'edit' and set(body) == {'action', 'id', 'revision', 'section', 'text'}:
            return self.workshops.edit(binding, ident, body['revision'], section=body['section'], text=body['text'])
        if action == 'save' and set(body) == {'action', 'id', 'revision'}:
            return self.workshops.save(binding, ident, body['revision'])
        if action == 'brain-save' and set(body) == {'action', 'id', 'revision', 'sections', 'area_id'}:
            if self.live.busy() or self.engine.recorder.active:
                raise ValueError('Gespräch oder Aufnahme zuerst beenden. Ergebnisse bleiben erhalten.')
            return self.workshops.save_brain(binding, ident, body['revision'], body['sections'], body['area_id'])
        if action == 'pause' and set(body) == {'action', 'id', 'revision'}:
            if self.live.busy(): raise ValueError('Gespräch zuerst beenden, dann pausieren.')
            return self.workshops.edit(binding, ident, body['revision'], paused=True)
        raise ValueError('Unbekannte Ergebnisaktion.')

    def action(self, path, body, *, start_guard=None):
        with self.control_lock:
            try:
                return self._action(path, body, start_guard=start_guard)
            finally:
                if path in ('/api/record/start', '/api/record/stop', '/api/record/control',
                            '/api/live/reserve', '/api/live/end', '/api/live/mute'):
                    if getattr(self, 'portal', None): self.portal.revision += 1

    def _action(self, path, body, *, start_guard=None):
        # Lock order matches state(): controller before recorder.
        with self.control_lock, self.controller.lock, self.engine.recorder.lock:
            if self.closing:raise ValueError('Dienst wird beendet. Änderungen bitte kurz aufbewahren.')
            if path.startswith('/api/portal/'):
                if path == '/api/portal/revoke':
                    self.portal.sessions.clear()
                    return self.portal.public()
                if path == '/api/portal/approve':
                    return self.portal.approve(body.get('code'))
                self.room.require_operator()
                self.require('configure')
                if path == '/api/portal/enable' and not body:
                    return self.portal.enable()
                if path == '/api/portal/disable' and not body:
                    return self.portal.disable()
                raise ValueError('Unbekannte Portalaktion.')
            if path == '/api/device/ready':
                if body: raise ValueError('Keine Parameter erwartet.')
                # UI readiness is public to local users, including before PIN
                # unlock. It does not count as activity or prolong their session.
                if self.device_sounds_hardware:
                    self.device_sounds.ready(self.management.boot_id())
                return {'ok': True}
            if self.management.busy():raise ValueError('Gerät wird gewartet. Bitte kurz warten.')
            if self.first_start.busy:raise ValueError('Netzwerk wird eingerichtet. Bitte kurz warten.')
            self.room_guard(path)
            if path.startswith('/api/room/'):
                return self.room_action(path, body)
            if path == '/api/workshops':
                return self.workshop_action(body)
            if path == '/api/voice-ui/action':
                if body.get('action') != 'shown': self.room.touch()
                return self.voice_actions.touch(body)
            if self.room.enabled:
                self.room.touch()
                if path == '/api/cdb/logout':
                    self.require('configure'); self.room_logout(); return self.cdb.public()
                if path == '/api/cdb/login/cancel':
                    self.require('configure'); self.room.cancel()
                if path == '/api/cdb/login':
                    self.require('configure')
                    if self.room.account(): self.room_logout()
                    self.room.login_owned = bool(self.room.intent) and self.cdb.login.get('state') != 'pending'
            # Check before any wake, playback or account side effects.
            if path in ('/api/cdb/login', '/api/cdb/logout', '/api/cdb/login/cancel', '/api/cdb/config'):
                self.require('configure')
            if path == '/api/cdb/login/cancel':
                return self.cdb.cancel_login()
            if path == '/api/nfc':
                self.require('configure')
                return self.nfc.configure(body)
            if path == '/api/onboarding/network':
                self.require('install')
                if any(i['state'] in ('scheduled','due') for i in self.schedules.items()):raise ValueError('Aktiven Timer zuerst abschließen.')
                with self.cdb.db() as db:
                    if db.execute("SELECT 1 FROM publications WHERE state IN ('queued','accepted','sending') LIMIT 1").fetchone():raise ValueError('Übertragung zuerst abschließen.')
                self.wake.suspend('Netzwerk wird eingerichtet.')
                return self.first_start.run_network(body)
            if path == '/api/onboarding/step':
                self.require('configure')
                return self.first_start.advance(body.get('step'),self.management.public(),body.get('offline',False))
            if path == '/api/device/restart':
                if body.get('confirm') is not True:raise ValueError('Neustart bitte bestätigen.')
                return self.management.restart_device(self,VERSION)
            if path == '/api/speakers/recover':
                if set(body) != {'confirm'} or body.get('confirm') is not True:
                    raise ValueError('USB-Wiederherstellung bitte bestätigen.')
                return self.usb_recovery.start(self, VERSION)
            if path == '/api/device/shutdown':
                if body.get('confirm') is not True:raise ValueError('Herunterfahren bitte bestätigen.')
                return self.management.shutdown_device(self,VERSION)
            if path.startswith('/api/remote-control/'):
                if path != '/api/remote-control/revoke': self.require('configure')
                return self.remote_channel.enqueue(path.removeprefix('/api/remote-control/'), body)
            if path == '/api/management/enroll':
                self.require('configure')
                return self.management.enroll(body.get('code'))
            if path == '/api/playback':
                key = body.get('client')
                if not isinstance(key,str) or not 8<=len(key)<=80 or type(body.get('playing')) is not bool:
                    raise ValueError('Ungültiger Wiedergabestatus.')
                if body['playing']:
                    if len(self.playback_leases)>=20 and key not in self.playback_leases: raise ValueError('Zu viele Wiedergaben.')
                    self.playback_leases[key]=time.monotonic()+6
                    self.wake.suspend('Audiowiedergabe läuft.')
                else: self.playback_leases.pop(key,None)
                return {'ok':True}
            if path == '/api/announcements/reload':
                self.require('configure')
                if body: raise ValueError('Keine Parameter erwartet.')
                self.announcements.reload()
                return self.announcements.public()
            if path == '/api/device/sounds':
                self.require('configure')
                return self.device_sounds.configure(body)
            if path == '/api/device/sounds/test':
                self.require('configure')
                from services.device_sounds import KINDS
                if set(body) != {'kind'} or body.get('kind') not in KINDS:
                    raise ValueError('Unbekannter Geräteklang.')
                self.wake.suspend('Geräteklang wird vorgespielt.')
                result = self.speakers.start_chime(body['kind'])
                self.announcement_playing = True
                return result
            if path == '/api/announcements':
                self.require('configure')
                return self.announcements.configure(body)
            if path == '/api/timers/tone':
                self.require('configure')
                self.wake.suspend('Alarmton wird vorgespielt.')
                return self.speakers.start_test(body.get('tone','bell'))
            if path == '/api/timers':
                action = body.get('action')
                if action == 'create':
                    if body.get('kind')=='reminder' and not self.clock_ready: raise ValueError('Gerätezeit zuerst synchronisieren lassen.')
                    return self.schedules.create(body)
                result = self.schedules.change(body)
                if self.countdown is not None and self.countdown['id'] == body.get('id'):
                    self.stop_countdown()
                if self.alarm_id == body.get('id'):
                    self.speakers.stop_test(); self.alarm_id=None
                return result
            if path == '/api/wake':
                if body.get('action') == 'off': return self.wake.configure(False,None)
                if body.get('action') == 'test-stop':
                    self.wake.test_until=0;self.wake.suspend('Test beendet.');return self.wake.public()
                self.require('configure')
                if body.get('action') == 'phrase': return self.wake.select_phrase(body.get('phrase'))
                if body.get('action') == 'test': return self.wake.test()
                if body.get('action') == 'on':
                    setup=self.live.setup()
                    if not setup['enabled']: raise ValueError('Voice One ist für dieses Brain-Konto nicht freigeschaltet.')
                    if not setup.get('remembered_area_ids'): raise ValueError('Im Live-Gespräch zuerst Wissensbereiche auswählen.')
                    self.live_audio_config()
                    return self.wake.configure(True,self.wake_account())
                raise ValueError('Unbekannte Aktivierungswort-Aktion.')
            if path in ('/api/record/start','/api/live/reserve','/api/microphone/test','/api/cdb/logout'):
                with self.live.lock:
                    self.announcements.failure_clip(self.live.announcement_failure, False)
                if self.countdown is not None:
                    self.stop_countdown()
                if self.announcement_playing:
                    self.speakers.stop_test()
                    self.announcement_playing = False
            if path in ('/api/record/start','/api/live/reserve','/api/microphone/test') and self.alarm_id:
                self.speakers.stop_test();self.schedules.sound_result(self.alarm_id,'interrupted');self.alarm_id=None
            if path == '/api/cdb/logout': self.wake.configure(False,None)
            if path not in ('/api/live/pulse','/api/live/status'):
                self.wake.test_until=0
                self.wake.suspend()
            if path == '/api/display/revoke':
                return self.display.revoke()
            if path == '/api/display/control':
                self.require('configure')
                action = body.get('action')
                if action == 'enable':
                    result = self.display.enable()
                    atomic_write(self.display_preferences, json.dumps({'enabled': True}))
                    return result
                if action == 'disable':
                    self.display.close()
                    atomic_write(self.display_preferences, json.dumps({'enabled': False}))
                    return self.display.status()
                if action == 'pair':
                    self.cdb.session()  # Validate/refresh only on the authorized local control path.
                    self.live._restore(self.live._binding())
                    return self.display.pair(body.get('code'))
                raise ValueError('Unbekannte Bildschirmaktion.')
            if path=='/api/bluetooth':
                activity=self.activity(include_bluetooth=False)
                if activity.occupied:raise ValueError(activity.reason)
                return self.bluetooth.action(body)
            if self.bluetooth.busy():raise ValueError('Bluetooth wird eingerichtet. Bitte abschließen oder abbrechen.')
            live_controls={'/api/live/start-native','/api/live/status','/api/live/pulse','/api/live/end','/api/live/mute','/api/live/preferences'}
            if self.live.busy() and path not in live_controls:
                raise ValueError(self.activity().reason)
            if path.startswith('/api/live/'):
                if path=='/api/live/reserve':
                    self.require('live')
                    self.cdb.invalidate_pending_login()
                    workshop_id = body.get('workshop_id')
                    if workshop_id:
                        draft = self.workshops.get(self.wake_account(), workshop_id)
                        if draft['paused']: self.workshops.edit(self.wake_account(), workshop_id, draft['revision'], paused=False)
                    return self.live.reserve(body.get('area_ids'), workshop_id=workshop_id)
                if path=='/api/live/areas':
                    self.require('configure');return self.live.remember_areas(body.get('area_ids'),body.get('account_key'))
                if path=='/api/live/clear':
                    self.require('configure');return self.live.clear()
                if self.engine.recorder.active:
                    raise ValueError('Aufnahme läuft. Bitte zuerst stoppen.')
                lease=body.get('lease')
                if path in ('/api/live/mute','/api/live/preferences') and self.live.owner_kind=='device':
                    lease=self.live.lease
                if path=='/api/live/start-native':return self.live.start_native(lease)
                if path=='/api/live/start':raise ValueError('Live-Audio läuft jetzt direkt am Pi. Bitte die Oberfläche neu laden.')
                if path=='/api/live/status':return self.live.status(lease)
                if path=='/api/live/pulse':return self.live.pulse(lease)
                if path=='/api/live/preferences':return self.live.preferences(body.get('search_sound'),lease)
                if path=='/api/live/mute':return self.live.mute(lease,body.get('muted'))
                if path=='/api/live/end':return self.live.end(lease)
                raise KeyError('Unbekannte Gesprächsaktion.')
            if self.engine.recorder.active and path not in ('/api/record/stop','/api/record/control'):
                parts=path.strip('/').split('/')
                note_save=(len(parts)==4 and parts[:2]==['api','sessions'] and parts[3]=='save'
                           and isinstance(body.get('changes'),dict) and set(body['changes'])=={'notes'})
                active_id=self.engine.state()['recording']['id']
                if not note_save or self.session(int(parts[2])).get('local_job_id')!=active_id:
                    raise ValueError('Aufnahme läuft. Nur aktuelle Notizen, Stummschaltung, Pause und Stoppen sind verfügbar.')
            if path=='/api/speakers/stop':return self.speakers.stop_test()
            if path=='/api/speakers':
                self.require('configure');return self.speakers.configure(body)
            if path=='/api/speakers/test':
                self.require('configure');return self.speakers.start_test()
            if path=='/api/record/start':
                self.require('record')
                if not self.store.config()['setup_complete']:raise ValueError('Bitte unter Einstellungen die Recorder-Einrichtung prüfen und abschließen.')
                if self.engine.recorder.active:raise ValueError('Aufnahme läuft bereits.')
                if start_guard is not None: start_guard()
                self.cdb.invalidate_pending_login()
                return {'id':self.engine.start('')}
            if path=='/api/record/control':
                if not body or set(body)-{'paused','muted'} or any(type(v) is not bool for v in body.values()):raise ValueError('Ungültige Aufnahmesteuerung.')
                return self.engine.recorder.control(**body)
            if path=='/api/record/stop':
                ident = self.engine.stop()
                self.controller.sync()
                # Use the route saved for this recording, even if preferences change.
                try:
                    route = json.loads((self.store.folder(ident) / 'cdb-request.json').read_text())
                except (OSError, ValueError):
                    route = {}
                provider = route.get('transcription') if isinstance(route, dict) else None
                return {'id': ident, 'transcription': provider if provider in ('local', 'cdb') else None}
            if path.startswith('/api/cdb/'):
                if path=='/api/cdb/config':
                    return self.cdb.configure(body)
                if path=='/api/cdb/login':
                    return self.cdb.start_login()
                if path=='/api/cdb/logout':
                    self.cdb.logout();return self.cdb.public()
                if path=='/api/cdb/area':return self.cdb.select_area(body.get('area'))
                if path=='/api/cdb/send':return self.cdb.enqueue(self.session(int(body.get('session',0))),body.get('area'))
                raise KeyError('Unbekannte CDB-Aktion.')
            if path=='/api/settings':
                self.require('configure')
                if set(body)-{'device','whisper_binary','whisper_model','summary_model','threads'}:raise ValueError('Unbekannte Einstellung.')
                if 'summary_model' in body or 'whisper_model' in body:
                    catalog=self.models.catalog()
                    for backend,key,entries,valuekey in [('whisper','whisper_model',catalog['asr'],'path'),('ollama','summary_model',catalog['llm'],'id')]:
                        if key in body and body[key]!=self.store.config()[key]:
                            m=next((m for m in entries if m[valuekey]==body[key]),None)
                            if not m or not m.get('tested'):raise ValueError('Neues Modell zuerst installieren und erfolgreich auf diesem Gerät testen; danach ausdrücklich aktivieren.')
                return self.engine.configure(body|{'setup_complete':False})
            if path=='/api/models/check':
                self.require('model_test');return self.model_checks.start(body)
            if path=='/api/models/use':
                self.require('configure');return self.model_checks.use(body)
            if path=='/api/models/install':
                self.require('install')
                return self.models.install(body.get('backend'),body.get('model'))
            if path=='/api/models/activate':
                self.require('configure');self.finish_model_validation()
                catalog=self.models.catalog();backend=body.get('backend')
                if backend not in ('whisper','ollama'):raise ValueError('Unbekannter Modelltyp.')
                entries=catalog['asr' if backend=='whisper' else 'llm']
                m=next((m for m in entries if m['id']==body.get('model')),None)
                if not m or not m.get('tested'):raise ValueError('Aktivierung erst nach bestandenem Gerätetest möglich.')
                key,value=('whisper_model',m['path']) if backend=='whisper' else ('summary_model',m['id'])
                return self.engine.configure({key:value})
            if path=='/api/models/test':
                self.require('model_test');self.model_test_preflight()
                catalog=self.models.catalog();config=self.store.config()
                asr=next((m for m in catalog['asr'] if (m['id']==body.get('asr') if body.get('asr') else m['path']==config['whisper_model'])),None)
                llm=next((m for m in catalog['llm'] if m['id']==body.get('llm',config['summary_model'])),None)
                if not (catalog['whisper_runtime'] and catalog['ollama'] and asr and asr['installed'] and llm and llm['installed']):
                    raise ValueError('Ausgewählte Modelle und Programme zuerst installieren.')
                if llm.get('candidate') and not llm.get('runtime_compatible'):raise ValueError('Laufzeit und Thinking-Vorlage dieses Kandidaten nicht bestätigt.')
                return self.start_model_test({'whisper':asr,'ollama':llm})
            if path=='/api/microphone/test':
                self.require('probe')
                self.probe_started_ns = time.time_ns()
                return self.microphone_progress(self.probe.start())
            if path=='/api/setup/complete':
                self.require('finish_setup')
                if not self.setup_state()['ready']:raise ValueError('Einrichtung noch nicht bereit. Offene Punkte prüfen.')
                return self.engine.configure({'setup_complete':True})
            if path=='/api/prompts':return self.mutate_prompt(body)
            parts=path.strip('/').split('/')
            if len(parts)==4 and parts[:2]==['api','sessions']:
                sid=int(parts[2]);session=self.session(sid)
                if parts[3]=='save':return self.save(sid,body.get('changes'),body.get('base'))
                if parts[3]=='local-process':
                    self.require('process')
                    if body.get('confirm') is not True: raise ValueError('Lokale Verarbeitung bitte bestätigen.')
                    catalog = self.models.catalog(); config = self.store.config()
                    asr = next((m for m in catalog['asr'] if m['path'] == config['whisper_model']), {})
                    llm = next((m for m in catalog['llm'] if m['id'] == config['summary_model']), {})
                    if not (catalog['whisper_runtime'] and catalog['ollama'] and asr.get('tested') and asr.get('installed') and llm.get('tested') and llm.get('installed')):
                        raise ValueError('Lokale Sprachmodelle zuerst installieren, testen und auswählen.')
                    folder = self.store.folder(session['local_job_id']) if session.get('local_job_id') else None
                    self.job_context = {'owner':self.room.owner(folder) if folder else None,
                                        'route':{'transcription':'local','summary':'local','binding':None}}
                    try: return {'id':self.controller.process(sid)}
                    finally: self.job_context = None
                if parts[3]=='process':
                    self.require('process')
                    prompt=next((p for p in self.prompts() if p['id']==body.get('prompt')),None)
                    if not prompt:raise ValueError('Prompt fehlt.')
                    old = session.get('local_job_id')
                    folder = self.store.folder(old) if old else None
                    self.job_context = {'owner': self.room.owner(folder) if folder else None,
                                        'route': json.loads((folder/'cdb-request.json').read_text()) if folder and (folder/'cdb-request.json').exists() else self.cdb.snapshot()}
                    try: return {'id':self.controller.process(sid,prompt['prompt_text'],reuse_transcript=not body.get('transcribe_again',False))}
                    finally: self.job_context = None
                if parts[3]=='retry':
                    self.require('process')
                    if session.get('local_job_id'):self.engine.retry(session['local_job_id']);return {'ok':True}
                    return {'id':self.controller.process(sid)}
                if parts[3]=='delete':
                    if session['transcription_status'] in BUSY:raise ValueError('Aufnahme oder Verarbeitung zuerst abschließen.')
                    return self.controller.delete(sid)
            raise KeyError('Unbekannte Aktion.')

    def close(self):
        # Stop accepting LAN requests outside the lock used by request workers.
        with self.control_lock:
            self.closing=True
        self.portal.close()
        with self.control_lock:
            if hasattr(self, 'remote_channel'): self.remote_channel.close()
            self.ambient_stop.set()
            self.nfc.close()
            self.wake.test_until=0
            self.wake.suspend()
            self.display.close()
            self.speakers.stop_test()
            if self.engine.recorder.active:self.engine.stop()
            self.controller.sync()
            self.model_checks.stopping.set()
            self.bluetooth.close()
            self.live.close()
            self.cdb.close()
            if self.model_checks.thread:self.model_checks.thread.join(timeout=5)
            self.respeaker.close()
            self.engine.close()
        self.recording_owner.shutdown(wait=True)
        self.ambient_thread.join(timeout=3)


class StudioHandler(Handler):
    def get(self):
        # Serve a consistent account snapshot, including streamed files. A
        # concurrent logout cannot approve a file under the next room account.
        path = urlsplit(self.path).path
        if path in ('/api/state', '/api/search', '/api/lcd/timers') or path.startswith(('/api/sessions/', '/api/meetings/')):
            with self.server.app.control_lock:
                return self.get_locked()
        return self.get_locked()

    def get_locked(self):
        if not self.authorized():return
        path=urlsplit(self.path).path
        app = self.server.app
        if path.startswith('/api/meetings/'):
            ident = path.strip('/').split('/')[2]
            if not app.room.can_read(app.store.folder(ident)):
                raise KeyError('Meeting fehlt oder gehört zu einem anderen Konto.')
        if app.room.enabled:
            if path in ('/api/live/activity', '/api/live/setup', '/api/cdb/areas'):
                app.room.require_account()
            if path in ('/api/microphone/audio', '/api/bluetooth', '/api/diagnostics'):
                app.room.require_operator()
        if path=='/api/management/health':
            app=self.server.app
            if not app.management.authorized(self.headers.get('Authorization','')):
                self.respond({'error':'Nicht berechtigt.'},403);return
            self.respond({'version':VERSION,'ready':not app.closing,'activity':('processing' if app.activity().pending and not app.activity().occupied else app.activity().mode),'wake_state':app.wake.public().get('state','unknown')});return
        if path=='/api/onboarding':
            app=self.server.app
            activity = app.activity()
            self.respond(app.first_start.public(app.management.public()) | {
                'csrf': app.csrf, 'allowed': not activity.occupied and not activity.pending,
                'reason': activity.reason or ('Offene Verarbeitung zuerst abschließen.' if activity.pending else ''),
                'installation': app.models.status(),
                'brain': {'signed_in': bool(app.cdb.read('session.json', {}).get('identity')),
                          'server': app.cdb.config()['server'], 'login': dict(app.cdb.login)},
            });return
        if path=='/api/live/activity':
            self.respond(self.server.app.live.feedback());return
        if path=='/api/live/setup':
            self.respond(self.server.app.live.setup());return
        if path=='/favicon.ico':
            self.send_response(204);self.headers_base('image/x-icon',0);self.end_headers();return
        if path=='/api/wake/status':self.respond(self.server.app.wake.public());return
        if path=='/api/lcd/timers':
            if self.client_address[0] not in ('127.0.0.1','::1'):
                self.respond({'error':'Nur lokal verfügbar.'},403);return
            from services.lcd_display import snapshot
            app=self.server.app
            # Use the current account's timers, with generic labels on the shared
            # peripheral. The control lock keeps account changes atomic with projection.
            result = app.voice_actions.project_lcd(snapshot(app.schedules, app.clock_ready, private_labels=app.room.enabled, focus_id=app.voice_actions.lcd_focus()))
            self.respond(result);return
        if path=='/help/verkabelung-r2.pdf':
            from services.local_portal import wiring_pdf
            data = wiring_pdf()
            self.send_response(200);self.headers_base('application/pdf',len(data));self.end_headers();self.wfile.write(data);return
        if path=='/api/portal/info':
            self.respond({'version': VERSION, 'secure': False, 'enabled': app.portal.enabled, 'control_url': app.portal.public()['control_url']});return
        if path=='/api/portal/qr':
            from services.local_portal import qr_svg
            data = qr_svg(app.portal.public()['url'])
            self.send_response(200);self.headers_base('image/svg+xml',len(data));self.end_headers();self.wfile.write(data);return
        if path=='/api/state':self.respond(self.server.app.state());return
        if path=='/api/bluetooth':
            self.server.app.bluetooth.start();self.respond(self.server.app.bluetooth.public());return
        if path=='/api/speakers/diagnostic-status':
            app = self.server.app
            with app.control_lock, app.controller.lock, app.engine.recorder.lock, app.speakers.lock:
                app.room.require_operator()
                activity = app.activity()
                self.respond({'csrf': app.csrf, 'preview': app.preview,
                    'signed_in': bool(app.room.account()), 'account_epoch': app.room.epoch,
                    'activity': activity.public(), 'pending_processing': activity.pending,
                    'playback_active': any(t > time.monotonic() for t in app.playback_leases.values()),
                    'output_busy': app.speakers.test_status()['state'] == 'running',
                    'output_cooldown_active': app.output_busy_until > time.monotonic(),
                    'pending_login': app.cdb.login.get('state') == 'pending',
                    'pending_intent': bool(app.room.intent),
                    'open_timer_count': sum(i['state'] in ('scheduled','due','missed') for i in app.schedules.items()),
                    'ringing_id': app.alarm_id, 'countdown_active': app.countdown is not None,
                    'speakers': app.speakers.public()})
            return
        if path=='/api/speakers':
            app = self.server.app
            self.respond(app.speakers.public() | {'recovery': app.usb_recovery.public()});return
        if path=='/api/cdb/areas':
            try:self.respond(self.server.app.cdb.areas())
            except ValueError as e:self.respond({'error':str(e)},400)
            return
        if path=='/api/prompts':self.respond(self.server.app.prompts());return
        if path=='/api/search':
            from urllib.parse import parse_qs
            query=parse_qs(urlsplit(self.path).query).get('q',[''])[0][:1000]
            publications=app.cdb.public()['publications']
            rows=[]
            for row in app.repo.get_all(query):
                if not app.visible_session(row):continue
                transfers=[p['state'] for p in publications if p.get('session_id')==row['id']]
                status='completed' if 'completed' in transfers else 'pending' if any(s in ('queued','accepted','sending') for s in transfers) else 'failed' if transfers else 'unknown'
                rows.append({k:row.get(k) for k in ('id','title','recorded_at','duration_sec','transcription_status')} | {'transfer_status':status})
            self.respond(rows);return
        if path.startswith('/api/sessions/'):
            parts=path.strip('/').split('/')
            if len(parts) not in (3,4):raise KeyError('Unbekannte Datei.')
            row=self.server.app.session(int(parts[2]))
            if len(parts)==3:self.respond(row);return
            if parts[3]=='peaks':
                import wave, array
                peaks=[]
                try:
                    with wave.open(row['path'],'rb') as f:
                        if f.getsampwidth()!=2:raise ValueError('Unsupported audio width')
                        total=f.getnframes()
                        for i in range(64):
                            f.setpos(min(max(0,total-128),total*i//64))
                            data=array.array('h',f.readframes(128))
                            peaks.append(max((abs(n)/32768 for n in data),default=0))
                except (OSError,ValueError,wave.Error):peaks=[0]*64
                self.respond(peaks);return
            if parts[3]=='audio':self.serve_file(Path(row['path']),'audio/wav',ranges=True);return
            if parts[3]=='export':
                text='# '+row['title']+'\n\n'+'\n\n'.join('## '+title+'\n\n'+(row.get(key) or '')
                    for title,key in [('Notizen','notes'),('Transkript','transcript_text'),('Zusammenfassung','summary_text')])
                self.send_response(200);self.headers_base('text/markdown; charset=utf-8',len(text.encode()))
                self.send_header('Content-Disposition',f'attachment; filename="meeting-{row["id"]}.md"')
                self.end_headers();self.wfile.write(text.encode());return
            raise KeyError('Unbekannte Datei.')
        if path=='/api/microphone/audio':self.serve_file(self.server.app.probe.folder/'audio.wav','audio/wav',ranges=True);return
        if path.startswith('/api/'):
            super().get();return
        relative='index.html' if path=='/' else path.lstrip('/')
        if relative == 'index.html':
            # One release version: a forgotten static HTML bump must never cause
            # an automatic reload loop after an otherwise healthy app update.
            body=(STATIC/'index.html').read_text().replace('__STUDIO_VERSION__',VERSION).encode()
            self.send_response(200);self.headers_base('text/html; charset=utf-8',len(body))
            self.end_headers();self.wfile.write(body);return
        file=(STATIC/relative).resolve()
        if not file.is_relative_to(STATIC.resolve()) or not file.is_file():raise KeyError('Datei fehlt.')
        self.serve_file(file,mimetypes.guess_type(file.name)[0] or 'application/octet-stream')

    def headers_base(self,mime,length):
        super().headers_base(mime,length)
        self.send_header('Permissions-Policy','microphone=(), camera=()')

    def serve_file(self,path,mime,ranges=False):
        if not path.is_file():raise KeyError('Audiodatei fehlt.' if ranges else 'Datei fehlt.')
        size=path.stat().st_size;start=0;end=size-1;status=200
        value=self.headers.get('Range') if ranges else None
        if value:
            import re
            match=re.fullmatch(r'bytes=(\d*)-(\d*)',value)
            if not match or not any(match.groups()):raise ValueError('Ungültiger Audiobereich.')
            first,last=match.groups()
            if first:start=int(first);end=min(int(last),end) if last else end
            else:start=max(0,size-int(last))
            if start>=size or start>end:
                self.send_response(416);self.send_header('Content-Range',f'bytes */{size}');self.end_headers();return
            status=206
        length=max(0,end-start+1)
        self.send_response(status);self.headers_base(mime,length)
        if ranges:self.send_header('Accept-Ranges','bytes')
        if status==206:self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
        self.end_headers()
        with path.open('rb') as source:
            source.seek(start)
            while length:
                block=source.read(min(length,65536))
                if not block:break
                self.wfile.write(block);length-=len(block)

    def do_POST(self):
        if urlsplit(self.path).path in ('/api/management/prepare','/api/management/release'):
            app=self.server.app
            if not self.authorized() or not app.management.authorized(self.headers.get('Authorization','')):
                self.respond({'error':'Nicht berechtigt.'},403);return
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<1024:raise ValueError('Ungültige Anfrage.')
                body=json.loads(self.rfile.read(size))
                with app.control_lock, app.controller.lock, app.engine.recorder.lock:
                    result=app.management.prepare(app,body.get('command'),VERSION,preserve_login=True) if self.path.endswith('/prepare') else app.management.release(body.get('command'))
                self.respond(result)
            except (ValueError,TypeError):self.respond({'error':'Gerät beschäftigt oder Anfrage ungültig.'},409)
            return
        try:
            if not self.authorized():return
            origin=self.headers.get('Origin')
            if origin and origin!='http://'+self.headers.get('Host',''):
                self.respond({'error':'Fremder Ursprung nicht erlaubt.'},403);return
            if not hmac.compare_digest(self.headers.get('X-CSRF-Token',''),self.server.app.csrf):
                self.respond({'error':'Sitzung ungültig. Seite neu laden; Entwürfe bleiben lokal erhalten.'},403);return
            length=int(self.headers.get('Content-Length','0'))
            if not 0<=length<=4_000_000:self.respond({'error':'Anfrage zu groß.'},413);return
            body=json.loads(self.rfile.read(length) or b'{}')
            if not isinstance(body,dict):raise ValueError('JSON-Objekt erwartet.')
            path = urlsplit(self.path).path
            app = self.server.app
            if path in ('/api/record/start', '/api/room/start'):
                # Linux delivers PDEATHSIG when the spawning thread exits. An
                # HTTP handler can finish while the microphone is still needed.
                result = app.recording_owner.submit(app.action, path, body).result()
            else:
                result = app.action(path, body)
            self.respond(result)
        except (BrokenPipeError,ConnectionResetError):pass
        except Conflict as e:self.respond({'error':str(e)},409)
        except (ValueError,KeyError) as e:self.respond({'error':str(e)},400)
        except Exception:
            logging.exception('Aktion fehlgeschlagen')
            self.respond({'error':'Aktion fehlgeschlagen. Dienstprotokoll prüfen; Entwurf bleibt erhalten.'},500)


class StudioServer(Server):
    def __init__(self,address,app):
        if address[0]!='127.0.0.1':raise ValueError('Studio ist ausschließlich lokal erreichbar. Für Fernzugriff SSH-Tunnel verwenden.')
        self.app=app
        ThreadingHTTPServer.__init__(self,address,StudioHandler)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--port',type=int,default=8088)
    parser.add_argument('--root',default=str(Path.home()/'.local/share/cdb-recorder-local'))
    parser.add_argument('--database',default='data/sessions.db')
    args=parser.parse_args()
    os.umask(0o077)
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
    app=StudioApp(args.root,args.database)
    server=StudioServer(('127.0.0.1',args.port),app);server.timeout=.5
    app.portal.start()
    try:
        if json.loads(app.display_preferences.read_text()).get('enabled'): app.display.enable()
    except (OSError, ValueError): logging.warning('Externer Bildschirm bleibt ausgeschaltet.')
    stopping=threading.Event()
    signal.signal(signal.SIGTERM,lambda *_:stopping.set())
    signal.signal(signal.SIGINT,lambda *_:stopping.set())
    try:
        while not stopping.is_set():server.handle_request()
    finally:
        server.server_close();app.close()

if __name__=='__main__':main()
