import contextlib
import json
from pathlib import Path
import stat
import subprocess
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from fleet.common import read, save
from services.app_activity import AppActivity
from services.device_management import DeviceManagement
from services.usb_audio_recovery import UsbAudioRecovery, HELPER, SOUNDBAR_PREFIX


SAFE = {'supported': True, 'available': True, 'device_present': False, 'reason': 'Bereit.'}
RECOVERED = {'recovered': True, 'device_present': True, 'reason': 'USB erkannt.'}
SINK = SOUNDBAR_PREFIX + '20210924-00.analog-stereo'


class UsbAudioRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.recovery = UsbAudioRecovery()
        self.management = DeviceManagement(self.root)
        self.management.boot_id = Mock(return_value='boot-a')
        self.activity = AppActivity()
        self.db = Mock()
        self.db.execute.return_value.fetchone.return_value = None
        @contextlib.contextmanager
        def database():
            yield self.db
        self.app = SimpleNamespace(
            preview=False, management=self.management,
            room=SimpleNamespace(intent=None),
            cdb=SimpleNamespace(login={'state': 'idle'}, db=database),
            activity=lambda: self.activity, playback_leases={},
            schedules=SimpleNamespace(items=Mock(return_value=[])), wake=Mock(),
            control_lock=threading.RLock(), controller=SimpleNamespace(lock=threading.RLock()),
            engine=SimpleNamespace(recorder=SimpleNamespace(lock=threading.RLock())),
            speakers=SimpleNamespace(public=Mock(return_value={'devices': [], 'selected': ''})),
        )

    def tearDown(self):
        self.tmp.cleanup()

    def start_reserved(self):
        with patch.object(self.recovery, 'check', return_value=SAFE), patch('services.usb_audio_recovery.threading.Thread') as thread:
            result = self.recovery.start(self.app, 'test')
        self.assertTrue(result['running'])
        thread.return_value.start.assert_called_once()
        return read(self.management.marker)['command']

    @staticmethod
    def process(data=RECOVERED, code=0):
        process = Mock(returncode=code)
        process.poll.side_effect = lambda: process.returncode
        process.communicate.return_value = (json.dumps(data), None)
        return process

    def worker(self, command, process):
        ticks = [0]
        def sleep(seconds):
            ticks[0] += seconds
        with patch('services.usb_audio_recovery.subprocess.Popen', return_value=process) as popen, patch('services.usb_audio_recovery.time.monotonic', side_effect=lambda: ticks[0]), patch('services.usb_audio_recovery.time.sleep', side_effect=sleep):
            self.recovery._recover(self.app, command)
        return popen

    def test_all_existing_activity_guards_block_start_before_hardware_mutation(self):
        states = [AppActivity(recording=True), AppActivity(recording=True, paused=True),
                  AppActivity(live='active'), AppActivity(live_reserved=True),
                  AppActivity(live='connecting'), AppActivity(microphone_test=True),
                  AppActivity(speaker_test=True), AppActivity(alarm=True),
                  AppActivity(bluetooth=True), AppActivity(pending=True),
                  AppActivity(download=True), AppActivity(model_test=True),
                  AppActivity(maintenance=True)]
        for state in states:
            self.activity = state
            with self.subTest(activity=state), patch.object(self.recovery, 'check', return_value=SAFE), patch('services.usb_audio_recovery.threading.Thread') as thread:
                with self.assertRaises(ValueError):
                    self.recovery.start(self.app, 'test')
                thread.assert_not_called()
                self.assertFalse(self.recovery.running)
                self.assertFalse(self.management.marker.exists())

    def test_scheduled_due_timer_playback_and_upload_block_start(self):
        for reason in ('scheduled', 'due', 'playback', 'upload'):
            with self.subTest(reason=reason):
                self.app.schedules.items.return_value = [{'state': reason}] if reason in ('scheduled', 'due') else []
                self.app.playback_leases = {'test': time.monotonic() + 20} if reason == 'playback' else {}
                self.db.execute.return_value.fetchone.return_value = (1,) if reason == 'upload' else None
                with patch.object(self.recovery, 'check', return_value=SAFE), patch('services.usb_audio_recovery.threading.Thread') as thread:
                    with self.assertRaises(ValueError):
                        self.recovery.start(self.app, 'test')
                    thread.assert_not_called()

    def test_pending_login_intent_preview_and_missing_boot_block_before_helper_check(self):
        for reason in ('login', 'intent', 'preview', 'boot'):
            self.app.cdb.login['state'] = 'pending' if reason == 'login' else 'idle'
            self.app.room.intent = {'id': 'intent'} if reason == 'intent' else None
            self.app.preview = reason == 'preview'
            self.management.boot_id.return_value = '' if reason == 'boot' else 'boot-a'
            with self.subTest(reason=reason), patch.object(self.recovery, 'check') as check:
                with self.assertRaises(ValueError):
                    self.recovery.start(self.app, 'test')
                check.assert_not_called()

    def test_unavailable_hardware_never_acquires_maintenance(self):
        with patch.object(self.recovery, 'check', return_value=SAFE | {'available': False, 'reason': 'Fremdgerät'}), patch.object(self.management, 'prepare') as prepare:
            with self.assertRaisesRegex(ValueError, 'Fremdgerät'):
                self.recovery.start(self.app, 'test')
            prepare.assert_not_called()

    def test_maintenance_lease_is_short_boot_bound_and_held_during_worker(self):
        command = self.start_reserved()
        lease = read(self.management.marker)
        self.assertEqual(lease['boot'], 'boot-a')
        self.assertEqual(lease['kind'], 'usb-audio-recovery')
        self.assertGreater(lease['expires'], time.time() + 80)
        self.assertLessEqual(lease['expires'], time.time() + 90)
        self.assertTrue(self.management.busy())
        self.app.wake.suspend.assert_called_once()
        with patch.object(self.recovery, 'check') as check:
            with self.assertRaisesRegex(ValueError, 'bereits'):
                self.recovery.start(self.app, 'test')
            check.assert_not_called()
        self.app.speakers.public.return_value = {'devices': [{'id': SINK}], 'selected': SINK}
        process = self.process()
        def communicate(**kwargs):
            self.assertTrue(self.recovery.running)
            self.assertTrue(self.management.busy())
            return json.dumps(RECOVERED), None
        process.communicate.side_effect = communicate
        self.worker(command, process)
        self.assertEqual(self.recovery.state, 'completed')
        self.assertFalse(self.recovery.running)
        self.assertFalse(self.management.busy())

    def test_new_boot_or_expired_lease_never_launches_helper(self):
        for reason in ('new-boot', 'expired'):
            with self.subTest(reason=reason):
                self.recovery.running = False
                self.management.boot_id.return_value = 'boot-a'
                command = self.start_reserved()
                if reason == 'new-boot':
                    self.management.boot_id.return_value = 'boot-b'
                    self.assertFalse(self.management.busy())
                else:
                    save(self.management.marker, read(self.management.marker) | {'expires': 0})
                with patch('services.usb_audio_recovery.subprocess.Popen') as popen:
                    self.recovery._recover(self.app, command)
                    popen.assert_not_called()
                self.assertEqual(self.recovery.state, 'failed')

    def test_replaced_lease_is_not_released_by_old_worker(self):
        command = self.start_reserved()
        newer = read(self.management.marker) | {'command': 'another-command'}
        save(self.management.marker, newer)
        with patch('services.usb_audio_recovery.subprocess.Popen') as popen:
            self.recovery._recover(self.app, command)
            popen.assert_not_called()
        self.assertEqual(read(self.management.marker), newer)

    def test_prepare_failure_after_marker_creation_releases_own_lease(self):
        self.app.wake.suspend.side_effect = ValueError('Mikrofon noch belegt')
        with patch.object(self.recovery, 'check', return_value=SAFE), patch('services.usb_audio_recovery.threading.Thread') as thread:
            with self.assertRaisesRegex(ValueError, 'Mikrofon'):
                self.recovery.start(self.app, 'test')
            thread.assert_not_called()
        self.assertFalse(self.management.marker.exists())

    def test_thread_start_failure_reports_failed_and_releases_reservation(self):
        with patch.object(self.recovery, 'check', return_value=SAFE), patch('services.usb_audio_recovery.threading.Thread') as thread:
            thread.return_value.start.side_effect = RuntimeError('thread unavailable')
            with self.assertRaises(RuntimeError):
                self.recovery.start(self.app, 'test')
        self.assertFalse(self.recovery.running)
        self.assertEqual(self.recovery.state, 'failed')
        self.assertFalse(self.management.marker.exists())

    def test_usb_found_without_pipewire_and_respeaker_only_are_failures(self):
        for devices in ([], [{'id': 'alsa_output.usb-Seeed_Studio_reSpeaker_XVF3800.analog-stereo'}], [{'id': 'alsa_output.usb-unknown_188A_fake'}]):
            with self.subTest(devices=devices):
                self.recovery.running = False
                command = self.start_reserved()
                self.app.speakers.public.return_value = {'devices': devices, 'selected': ''}
                self.worker(command, self.process())
                self.assertEqual(self.recovery.state, 'failed')
                self.assertIn('noch kein Audioausgang', self.recovery.message)
                self.assertFalse(self.management.busy())

    def test_success_only_after_188a_sink_appears_without_changing_selection(self):
        command = self.start_reserved()
        self.app.speakers.public.side_effect = [
            {'devices': [{'id': 'respeaker'}], 'selected': 'respeaker'},
            {'devices': [{'id': 'respeaker'}, {'id': SINK}], 'selected': 'respeaker'},
        ]
        self.app.speakers.configure = Mock()
        popen = self.worker(command, self.process())
        self.assertEqual(self.recovery.state, 'completed')
        self.assertIn('188A als Lautsprecher auswählen', self.recovery.message)
        self.app.speakers.configure.assert_not_called()
        self.assertEqual(popen.call_args.args[0], ['/usr/bin/sudo', '-n', HELPER, 'recover'])

    def test_helper_errors_and_invalid_json_never_report_success(self):
        cases = [(self.process({'recovered': False, 'reason': 'Kabel prüfen'}, 2), 'Kabel prüfen'),
                 (self.process([]), 'nicht wiederhergestellt'),
                 (self.process({'recovered': 'true', 'device_present': True}), 'nicht wiederhergestellt'),
                 (self.process({'recovered': True, 'device_present': 'true'}), 'nicht wiederhergestellt')]
        invalid = self.process()
        invalid.communicate.return_value = ('not json', None)
        cases.append((invalid, ''))
        for process, text in cases:
            with self.subTest(text=text):
                self.recovery.running = False
                command = self.start_reserved()
                self.worker(command, process)
                self.assertEqual(self.recovery.state, 'failed')
                self.assertIn(text, self.recovery.message)
                self.assertFalse(self.management.busy())

    def test_popen_failure_releases_lease(self):
        command = self.start_reserved()
        with patch('services.usb_audio_recovery.subprocess.Popen', side_effect=OSError('missing')):
            self.recovery._recover(self.app, command)
        self.assertEqual(self.recovery.state, 'failed')
        self.assertFalse(self.management.busy())

    def test_timeout_keeps_maintenance_until_child_exit_and_is_not_success(self):
        command = self.start_reserved()
        process = self.process(code=None)
        process.communicate.side_effect = subprocess.TimeoutExpired('sudo', 45)
        calls = []
        def wait(**kwargs):
            self.assertTrue(self.recovery.running)
            self.assertTrue(self.management.busy())
            calls.append(True)
            if len(calls) == 1:
                raise subprocess.TimeoutExpired('sudo', 5)
            process.returncode = 0
            return 0
        process.wait.side_effect = wait
        self.worker(command, process)
        self.assertEqual(len(calls), 2)
        self.assertEqual(self.recovery.state, 'failed')
        self.assertIn('Zeitlimit', self.recovery.message)
        self.assertFalse(self.management.busy())

    def test_communication_error_still_waits_for_live_child_before_unlock(self):
        command = self.start_reserved()
        process = self.process(code=None)
        process.communicate.side_effect = OSError('pipe closed')
        def wait(**kwargs):
            self.assertTrue(self.recovery.running)
            self.assertTrue(self.management.busy())
            process.returncode = -15
            return -15
        process.wait.side_effect = wait
        self.worker(command, process)
        process.terminate.assert_called()
        process.wait.assert_called_once()
        self.assertEqual(self.recovery.state, 'failed')
        self.assertFalse(self.management.busy())

    def test_helper_check_requires_strict_schema_and_root_owned_file(self):
        helper = self.root / 'helper'
        helper.write_text('test')
        for data in (SAFE, SAFE | {'available': 'true'}, SAFE | {'device_present': 'false'}, [], {'available': True}):
            with self.subTest(data=data):
                runner = Mock(return_value=Mock(returncode=0, stdout=json.dumps(data)))
                recovery = UsbAudioRecovery(str(helper), runner=runner)
                info = SimpleNamespace(st_mode=stat.S_IFREG | 0o755, st_uid=0)
                with patch.object(Path, 'stat', return_value=info):
                    result = recovery.check(force=True)
                self.assertEqual(result.get('available'), data == SAFE)
        runner = Mock()
        recovery = UsbAudioRecovery(str(helper), runner=runner)
        with patch.object(Path, 'stat', return_value=SimpleNamespace(st_mode=stat.S_IFREG | 0o777, st_uid=0)):
            self.assertFalse(recovery.check(force=True)['available'])
        runner.assert_not_called()


if __name__ == '__main__':
    unittest.main()
