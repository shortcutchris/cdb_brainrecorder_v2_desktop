import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import wave
from unittest.mock import Mock, patch

from services.announcements import Announcements, PHRASES, load_pack, validate_wav, MAX_WAV_BYTES
from services.audio_output import AudioOutput
from services.app_activity import AppActivity


def wav(rate=24000, channels=1, seconds=.25):
    out = io.BytesIO()
    with wave.open(out, 'wb') as audio:
        audio.setparams((channels, 2, rate, 0, 'NONE', 'none'))
        audio.writeframes(b'\x00\x01' * int(rate * seconds) * channels)
    return out.getvalue()


def pack(root):
    folder = Path(root) / 'announcements-pack'; folder.mkdir()
    data = {key: wav(seconds=5 if key == 'countdown' else .25) for key in PHRASES}
    manifest = {'version': 1, 'clips': {key: {'text': text, 'sha256': hashlib.sha256(data[key]).hexdigest()} for key, text in PHRASES.items()}}
    for key in PHRASES: (folder / (key + '.wav')).write_bytes(data[key])
    (folder / 'manifest.json').write_text(json.dumps(manifest))
    return folder


class PackTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name)
    def tearDown(self): self.temp.cleanup()

    def test_clean_install_and_upgrade_preserve_other_settings_default_off(self):
        old = self.root / 'config.json'; old.write_text('{"device":"existing"}')
        manager = Announcements(self.root)
        self.assertEqual(manager.enabled, {'offline': False, 'timers': False, 'connecting': False, 'countdown': False})
        self.assertFalse(manager.public()['ready'])
        with self.assertRaises(ValueError): manager.configure({'offline': True})
        pack(self.root); manager.configure({'timers': True})
        restored = Announcements(self.root)
        self.assertTrue(restored.enabled['timers']); self.assertFalse(restored.enabled['offline'])
        self.assertEqual(old.read_text(), '{"device":"existing"}')
        self.assertIsNone(restored.timer_clip('../../outside'))

    def test_invalid_preferences_fail_closed_and_disable_without_pack(self):
        (self.root / 'announcements.json').write_text('{"offline":"true","timers":1}')
        manager = Announcements(self.root)
        self.assertFalse(any(manager.enabled.values()))
        for body in ({'offline': 'true'}, {'text': 'arbitrary'}, {}, {'timers': 1}):
            with self.subTest(body=body), self.assertRaises(ValueError): manager.configure(body)
        manager.configure({'offline': False, 'timers': False, 'connecting': False, 'countdown': False})

    def test_pack_tamper_missing_wrong_phrase_and_symlink_rejected(self):
        folder = pack(self.root)
        valid = (folder / 'timer.wav').read_bytes()
        (folder / 'timer.wav').write_bytes(valid + b'changed')
        with self.assertRaises(ValueError): load_pack(folder)
        (folder / 'timer.wav').unlink()
        with self.assertRaises(ValueError): load_pack(folder)
        other = self.root / 'elsewhere.wav'; other.write_bytes(valid)
        (folder / 'timer.wav').symlink_to(other)
        with self.assertRaises(ValueError): load_pack(folder)
        (folder / 'timer.wav').unlink(); (folder / 'timer.wav').write_bytes(valid)
        manifest = json.loads((folder / 'manifest.json').read_text())
        manifest['clips']['timer']['text'] = 'arbitrary'
        (folder / 'manifest.json').write_text(json.dumps(manifest))
        with self.assertRaises(ValueError): load_pack(folder)

    def test_invalid_wav_format_length_truncation(self):
        for data in (b'bad', wav(16000), wav(channels=2), wav()[:-50], b'x' * (MAX_WAV_BYTES + 1)):
            with self.subTest(size=len(data)), self.assertRaises(ValueError): validate_wav(data)

    def test_installed_bytes_are_immutable_until_explicit_reload(self):
        folder = pack(self.root); manager = Announcements(self.root); manager.configure({'timers': True})
        original = manager.timer_clip('timer')
        (folder / 'timer.wav').write_bytes(b'corrupt')
        self.assertEqual(manager.timer_clip('timer'), original)
        manager.reload(); self.assertIsNone(manager.timer_clip('timer'))

    def test_offline_fresh_dedup_cooldown_and_no_delayed_replay(self):
        pack(self.root); now = [100.0]; manager = Announcements(self.root, lambda: now[0]); manager.configure({'offline': True})
        def event(sequence, age=0): return {'sequence': sequence, 'at': now[0] - age}
        self.assertIsNotNone(manager.failure_clip(event(1), True))
        self.assertIsNone(manager.failure_clip(event(1), True))
        self.assertIsNone(manager.failure_clip(event(2), True))
        now[0] += 61
        self.assertIsNone(manager.failure_clip(event(3), False))
        self.assertIsNone(manager.failure_clip(event(3), True))
        self.assertIsNone(manager.failure_clip(event(4, 16), True))
        self.assertIsNotNone(manager.failure_clip(event(5), True))

    def test_output_tail_wait_is_bounded_and_new_activity_discards_notice(self):
        pack(self.root); now = [100.0]; manager = Announcements(self.root, lambda: now[0]); manager.configure({'offline': True})
        event = {'sequence': 1, 'at': 100.0}
        self.assertIsNone(manager.failure_clip(event, True, quiet=False))
        now[0] = 103.0
        self.assertIsNotNone(manager.failure_clip(event, True, quiet=True))
        now[0] = 200.0; event = {'sequence': 2, 'at': 200.0}
        self.assertIsNone(manager.failure_clip(event, True, quiet=False))
        self.assertIsNone(manager.failure_clip(event, False, quiet=False))
        self.assertIsNone(manager.failure_clip(event, True, quiet=True))
        now[0] = 300.0; event = {'sequence': 3, 'at': 300.0}
        self.assertIsNone(manager.failure_clip(event, True, quiet=False))
        now[0] += 16
        self.assertIsNone(manager.failure_clip(event, True, quiet=True))

    def test_install_new_validated_pack_without_settings_or_model_and_reject_overwrite(self):
        from scripts.prepare_announcements import install
        source = pack(self.root)
        target = self.root / 'app'; target.mkdir()
        preference = target / 'announcements.json'; preference.write_text('{"timers":false}')
        installed = install(source, target)
        self.assertEqual(set(p.name for p in installed.iterdir()), {'manifest.json', 'offline.wav', 'timer.wav', 'reminder.wav', 'connecting.wav', 'countdown.wav'})
        self.assertEqual(preference.read_text(), '{"timers":false}')
        self.assertEqual(load_pack(installed), load_pack(source))
        with self.assertRaises(ValueError): install(source, target)

    def test_install_manifest_uses_utf8_with_non_utf8_system_default(self):
        from scripts.prepare_announcements import install
        source = pack(self.root)
        target = self.root / 'non-utf8-app'; target.mkdir()
        original = Path.write_text
        def locale_write(path, data, encoding=None, **kwargs):
            return original(path, data, encoding=encoding or 'latin-1', **kwargs)
        with patch.object(Path, 'write_text', locale_write):
            installed = install(source, target)
        manifest = json.loads((installed / 'manifest.json').read_bytes())
        self.assertEqual(manifest['clips']['offline']['text'], PHRASES['offline'])
        self.assertEqual(load_pack(installed), load_pack(source))

    def test_legacy_pack_keeps_existing_opt_ins_and_requires_optional_connecting_clip(self):
        folder = pack(self.root)
        manifest = json.loads((folder / 'manifest.json').read_text())
        del manifest['clips']['connecting']
        (folder / 'manifest.json').write_text(json.dumps(manifest))
        (folder / 'connecting.wav').unlink()
        (self.root / 'announcements.json').write_text('{"offline":true,"timers":true}')
        manager = Announcements(self.root)
        self.assertTrue(manager.public()['ready'])
        self.assertFalse(manager.public()['connecting_ready'])
        self.assertIsNotNone(manager.timer_clip('timer'))
        self.assertIsNone(manager.connecting_clip())
        with self.assertRaises(ValueError): manager.configure({'connecting': True})
        self.assertEqual(manager.enabled, {'offline': True, 'timers': True, 'connecting': False, 'countdown': False})

    def test_connecting_clip_opt_in_and_duration_limit(self):
        folder = pack(self.root); manager = Announcements(self.root)
        self.assertIsNone(manager.connecting_clip())
        manager.configure({'connecting': True})
        self.assertEqual(manager.connecting_clip(), wav())
        data = io.BytesIO()
        with wave.open(data, 'wb') as audio:
            audio.setparams((1, 2, 24000, 0, 'NONE', 'none'))
            audio.writeframes(b'\x00\x01' * (24000 * 4))
        (folder / 'connecting.wav').write_bytes(data.getvalue())
        manifest = json.loads((folder / 'manifest.json').read_text())
        manifest['clips']['connecting']['sha256'] = hashlib.sha256(data.getvalue()).hexdigest()
        (folder / 'manifest.json').write_text(json.dumps(manifest))
        with self.assertRaises(ValueError): load_pack(folder)

    def test_runtime_assets_allowlisted_private_pack_excluded(self):
        from fleet.releases import allowed
        for name in ('services/announcements.py', 'studio/speakers.js'): self.assertTrue(allowed(name))
        for name in ('announcements-pack/timer.wav', 'announcements.json', 'models/model.q8.gguf'): self.assertFalse(allowed(name))


class PlaybackTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name)
        self.output = AudioOutput(self.root)
        self.output.public = lambda: {'available': True, 'muted': False, 'volume': 30, 'selected': 'fake'}
    def tearDown(self):
        self.output.stop_test(); self.temp.cleanup()

    def test_timer_speech_once_then_original_tone(self):
        from services.alarm_tones import write_alarm
        path = self.root / 'tone.wav'; write_alarm(path, 'bell', 3)
        with wave.open(str(path)) as audio: original = audio.readframes(audio.getnframes())
        AudioOutput.prepend_speech(path, wav())
        with wave.open(str(path)) as audio:
            self.assertEqual(audio.getnchannels(), 2)
            self.assertEqual(audio.getnframes(), 24000 * 3 + 6000)
            speech = audio.readframes(6000)
            self.assertEqual(speech[:4], b'\x00\x01\x00\x01')
            self.assertEqual(audio.readframes(72000), original)

    def test_actual_child_is_reaped_before_stop_returns_no_audio_device(self):
        real_popen = subprocess.Popen; ready = threading.Event(); children = []
        def launch(*args, **kwargs):
            # Exercise actual process ownership using a sleeping child, never paplay.
            child = real_popen([sys.executable, '-c', 'import time; time.sleep(60)'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            children.append(child); ready.set(); return child
        with patch('services.audio_output.subprocess.Popen', side_effect=launch):
            self.output.start_announcement(wav()); self.assertTrue(ready.wait(2))
            self.assertEqual(self.output.stop_test()['state'], 'cancelled')
        self.assertIsNotNone(children[0].poll()); self.assertFalse(self.output.thread.is_alive()); self.assertIsNone(self.output.process)

    def test_failed_cleanup_retains_busy_owner_until_retry(self):
        child = Mock(); child.poll.return_value = None
        child.wait.side_effect = subprocess.TimeoutExpired('fake', 1)
        self.output.process = child; self.output.test = {'state': 'running', 'kind': 'announcement'}
        with self.assertRaises(ValueError): self.output.stop_test()
        self.assertIs(self.output.process, child); self.assertEqual(self.output.test_status()['state'], 'running')
        with self.assertRaises(ValueError): self.output.start_announcement(wav())
        child.poll.return_value = 0
        self.assertEqual(self.output.stop_test()['state'], 'cancelled')

    def test_timeout_worker_keeps_unreaped_process(self):
        child = Mock(); child.poll.return_value = None
        child.wait.side_effect = subprocess.TimeoutExpired('fake', 1)
        with patch('services.audio_output.subprocess.Popen', return_value=child):
            self.output.start_announcement(wav()); self.output.thread.join(2)
        self.assertIs(self.output.process, child); self.assertEqual(self.output.test_status()['state'], 'running')
        child.poll.return_value = 0
        self.output.stop_test()


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        from web_server import StudioApp
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name)
        self.app = StudioApp(self.root / 'queue', self.root / 'db.sqlite', backend=Mock(), preview=True, settings_file=self.root / 'settings.ini')
        self.app.ambient_stop.set(); self.app.ambient_thread.join(3)
        pack(self.app.store.root); self.app.announcements.configure({'offline': True, 'timers': True})
        self.app.speakers.public = lambda: {'available': True, 'muted': False, 'volume': 30, 'selected': 'fake'}
    def tearDown(self): self.app.close(); self.temp.cleanup()
    def fail_live(self):
        with self.app.live.lock:
            self.app.live._finish('error', 'synthetic failure; never speak this arbitrary string')
    def timer(self, tone='bell', kind='timer'):
        return {'id': 'one', 'state': 'due', 'sound': 'pending', 'tone': tone, 'kind': kind}

    def test_offline_terminal_failure_suspends_before_output_and_resumes_after_tail(self):
        self.fail_live(); order = []
        with patch.object(self.app, 'activity', return_value=AppActivity()), patch.object(self.app.wake, 'suspend', side_effect=lambda *a: order.append('wake-stopped')), patch.object(self.app.speakers, 'start_announcement', side_effect=lambda *a: order.append('play')):
            self.app.tick_announcements(); self.app.tick_announcements()
        self.assertEqual(order, ['wake-stopped', 'play'])
        self.assertFalse(self.app.announcement_playing)  # mocked playback already idle
        self.assertGreater(self.app.output_busy_until, time.monotonic())
        self.app.output_busy_until = 0
        with patch.object(self.app, 'activity', return_value=AppActivity()): self.assertEqual(self.app.wake_reason(), '')

    def test_all_protected_activities_skip_failure_and_do_not_replay(self):
        activities = [AppActivity(recording=True), AppActivity(recording=True, paused=True), AppActivity(live='active'), AppActivity(live_reserved=True), AppActivity(maintenance=True), AppActivity(microphone_test=True), AppActivity(speaker_test=True), AppActivity(download=True), AppActivity(pending=True), AppActivity(bluetooth=True), AppActivity(model_test=True)]
        for activity in activities:
            self.fail_live()
            with self.subTest(activity=activity), patch.object(self.app, 'activity', return_value=activity), patch.object(self.app.speakers, 'start_announcement') as play, patch.object(self.app.wake, 'suspend') as suspend:
                self.app.tick_announcements(); play.assert_not_called(); suspend.assert_not_called()
            with patch.object(self.app, 'activity', return_value=AppActivity()), patch.object(self.app.speakers, 'start_announcement') as play:
                self.app.tick_announcements(); play.assert_not_called()

    def test_browser_external_audio_logout_and_new_conversation_suppress_stale(self):
        for reason in ('browser', 'external', 'logout', 'new-live'):
            self.fail_live()
            self.app.playback_leases = {'synthetic': time.monotonic() + 10} if reason == 'browser' else {}
            self.app.output_busy_until = time.monotonic() + 10 if reason == 'external' else 0
            if reason == 'logout': self.app.cdb.generation += 1
            if reason == 'new-live': self.app.live.generation += 1
            with self.subTest(reason=reason), patch.object(self.app, 'activity', return_value=AppActivity()), patch.object(self.app.speakers, 'start_announcement') as play:
                self.app.tick_announcements(); play.assert_not_called()

    def test_failed_wake_shutdown_never_starts_speech(self):
        self.fail_live()
        with patch.object(self.app, 'activity', return_value=AppActivity()), patch.object(self.app.wake, 'suspend', side_effect=ValueError('cleanup pending')), patch.object(self.app.speakers, 'start_announcement') as play:
            with self.assertRaises(ValueError): self.app.tick_announcements()
            play.assert_not_called()

    def test_timer_generic_speech_fallback_live_and_silent(self):
        for kind in ('timer', 'reminder'):
            self.app.alarm_id = None
            with patch.object(self.app.schedules, 'items', return_value=[self.timer(kind=kind)]), patch.object(self.app.schedules, 'sound_result'), patch.object(self.app, 'activity', return_value=AppActivity()), patch.object(self.app.wake, 'suspend'), patch.object(self.app.speakers, 'start_alarm') as play:
                self.app.tick_alarm(); play.assert_called_once_with('bell', announcement=self.app.announcements.clips[kind])
        for activity in (AppActivity(live='active'), AppActivity(pending=True)):
            self.app.alarm_id = None
            with patch.object(self.app.schedules, 'items', return_value=[self.timer()]), patch.object(self.app.schedules, 'sound_result'), patch.object(self.app, 'activity', return_value=activity), patch.object(self.app.wake, 'suspend'), patch.object(self.app.speakers, 'start_alarm') as play:
                self.app.tick_alarm(); play.assert_called_once_with('bell')
        self.app.alarm_id = None
        with patch.object(self.app.schedules, 'items', return_value=[self.timer('silent')]), patch.object(self.app.schedules, 'sound_result') as result, patch.object(self.app, 'activity', return_value=AppActivity()), patch.object(self.app.wake, 'suspend') as suspend, patch.object(self.app.speakers, 'start_alarm') as play:
            self.app.tick_alarm(); play.assert_not_called(); suspend.assert_not_called(); result.assert_called_once_with('one', 'silent')

    def test_recording_pause_defer_whole_alarm(self):
        for paused in (True, False):
            with patch.object(self.app.schedules, 'items', return_value=[self.timer()]), patch.object(self.app, 'activity', return_value=AppActivity(recording=True, paused=paused)), patch.object(self.app.speakers, 'start_alarm') as play:
                self.app.tick_alarm(); play.assert_not_called()

    def test_capture_requests_stop_announcement_before_capture_and_fail_closed(self):
        for path in ('/api/record/start', '/api/live/reserve', '/api/microphone/test'):
            self.app.announcement_playing = True
            with patch.object(self.app.speakers, 'stop_test', side_effect=ValueError('cleanup pending')), patch.object(self.app.engine, 'start') as capture, patch.object(self.app.live, 'reserve') as live, patch.object(self.app.probe, 'start') as probe:
                with self.assertRaisesRegex(ValueError, 'cleanup pending'): self.app.action(path, {})
                capture.assert_not_called(); live.assert_not_called(); probe.assert_not_called()
                self.assertTrue(self.app.announcement_playing)
        self.app.announcement_playing = False

    def test_successful_record_request_stops_output_before_start(self):
        self.app.announcement_playing = True
        order = []
        with patch.object(self.app.speakers, 'stop_test', side_effect=lambda: order.append('stopped')), patch.object(self.app.wake, 'suspend', side_effect=lambda *a: order.append('wake-stopped')), patch.object(self.app, 'require'), patch.object(self.app.store, 'config', return_value={'setup_complete': True}), patch.object(self.app.engine, 'start', side_effect=lambda *a: order.append('record') or 'new'):
            self.assertEqual(self.app.action('/api/record/start', {}), {'id': 'new'})
        self.assertEqual(order, ['stopped', 'wake-stopped', 'record'])
        self.assertFalse(self.app.announcement_playing)

    def test_explicit_wake_test_and_missing_pack_keep_speech_silent(self):
        self.app.wake.test_until = time.monotonic() + 30
        self.fail_live()
        with patch.object(self.app, 'activity', return_value=AppActivity()), patch.object(self.app.speakers, 'start_announcement') as play:
            self.app.tick_announcements(); play.assert_not_called()
        self.app.wake.test_until = 0
        self.app.announcements.clips = {}
        with patch.object(self.app.schedules, 'items', return_value=[self.timer()]), patch.object(self.app.schedules, 'sound_result'), patch.object(self.app, 'activity', return_value=AppActivity()), patch.object(self.app.wake, 'suspend'), patch.object(self.app.speakers, 'start_alarm') as play:
            self.app.tick_alarm(); play.assert_called_once_with('bell')

    def test_settings_blocked_during_recording_and_http_csrf(self):
        from web_server import StudioServer
        import urllib.request
        import urllib.error
        with patch.object(self.app, 'activity', return_value=AppActivity(recording=True, paused=True)):
            with self.assertRaises(ValueError): self.app.action('/api/announcements', {'offline': False})
        server = StudioServer(('127.0.0.1', 0), self.app)
        thread = threading.Thread(target=server.serve_forever); thread.start()
        try:
            url = 'http://127.0.0.1:%d/api/announcements' % server.server_port
            for token, expected in (('wrong', 403), (self.app.csrf, 200)):
                request = urllib.request.Request(url, data=b'{"offline":false}', headers={'Content-Type': 'application/json', 'X-CSRF-Token': token})
                try:
                    with urllib.request.urlopen(request) as response: status = response.status
                except urllib.error.HTTPError as error: status = error.code; error.close()
                self.assertEqual(status, expected)
        finally: server.shutdown(); server.server_close(); thread.join()
