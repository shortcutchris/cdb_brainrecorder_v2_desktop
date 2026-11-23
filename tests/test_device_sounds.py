import array
import io
import json
from pathlib import Path
import subprocess
import tempfile
import threading
import time
import unittest
import wave
from unittest.mock import Mock, patch

from fleet.common import save
from services.device_sounds import DeviceSounds, cue, play_shutdown
from services.device_power import execute_shutdown


class DeviceSoundTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.sounds = DeviceSounds(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def test_clean_install_and_upgrade_do_not_opt_in_or_change_other_preferences(self):
        speaker = self.root / 'speaker.json'; speaker.write_text('{"device":"usb"}')
        self.assertEqual(self.sounds.public(), {'startup': False, 'shutdown': False})
        self.assertFalse(self.sounds.path.exists())
        self.sounds.configure({'startup': True})
        self.assertEqual(DeviceSounds(self.root).public(), {'startup': True, 'shutdown': False})
        self.sounds.configure({'shutdown': True})
        self.assertEqual(speaker.read_text(), '{"device":"usb"}')
        for value in ({'startup': 1}, {'startup': 'true'}, {'other': True}, {}):
            with self.assertRaises(ValueError): self.sounds.configure(value)

    def test_bad_preferences_are_silent_and_recoverable(self):
        for value in ('{bad', '[]', '{"startup":"true"}'):
            self.sounds.path.write_text(value)
            self.assertFalse(any(self.sounds.public().values()))
            self.assertFalse(play_shutdown(self.root, Mock(side_effect=AssertionError('no audio'))))
        self.sounds.configure({'shutdown': True})
        self.assertTrue(self.sounds.public()['shutdown'])

    def test_startup_is_once_per_boot_across_tabs_and_app_restarts(self):
        self.sounds.configure({'startup': True})
        copies = [DeviceSounds(self.root) for _ in range(4)]
        threads = [threading.Thread(target=s.ready, args=('boot-a',)) for s in copies]
        for t in threads: t.start()
        for t in threads: t.join()
        self.assertEqual(sum(s.take_startup() for s in copies), 1)
        self.sounds.ready('boot-a'); self.assertFalse(self.sounds.take_startup())
        self.sounds.ready('boot-b'); self.assertTrue(self.sounds.take_startup())
        self.assertFalse(self.sounds.take_startup())

    def test_enabling_later_or_no_boot_id_never_replays_startup(self):
        self.sounds.ready('boot-a')
        self.sounds.configure({'startup': True})
        self.sounds.ready('boot-a'); self.assertFalse(self.sounds.take_startup())
        self.sounds.ready(''); self.assertFalse(self.sounds.take_startup())
        self.sounds.ready('boot-b'); self.sounds.configure({'startup': False})
        self.assertFalse(self.sounds.take_startup())

    def test_generated_pcm_is_short_soft_and_fades_to_silence(self):
        for kind, seconds in [('startup', 1.2), ('shutdown', .7)]:
            with wave.open(io.BytesIO(cue(kind))) as wav:
                self.assertEqual((wav.getnchannels(), wav.getsampwidth(), wav.getframerate()), (1, 2, 24000))
                self.assertAlmostEqual(wav.getnframes() / 24000, seconds)
                samples = array.array('h', wav.readframes(wav.getnframes()))
                self.assertGreater(max(samples), 1000)
                self.assertLess(max(abs(v) for v in samples), 8000)
                self.assertEqual(samples[0], 0); self.assertLess(abs(samples[-1]), 3)
        self.assertNotEqual(cue('startup'), cue('shutdown'))
        with self.assertRaises(ValueError): cue('unknown')

    def output_runner(self, *, selected='usb', muted=False, volume=30000):
        self.sounds.configure({'shutdown': True})
        save(self.root / 'speaker.json', {'device': 'usb'})
        sinks = [{'name': selected, 'mute': muted, 'volume': {'left': {'value': volume}}}]
        return Mock(side_effect=[Mock(stdout=json.dumps(sinks)), Mock(returncode=0)])

    def test_shutdown_uses_selected_output_without_volume_mutation(self):
        run = self.output_runner()
        self.assertTrue(play_shutdown(self.root, run))
        self.assertEqual(run.call_count, 2)
        self.assertIn('--device=usb', run.call_args.args[0])
        self.assertEqual(run.call_args.kwargs['timeout'], 1.3)
        self.assertEqual(len(run.call_args.kwargs['input']), 33600)

    def test_shutdown_is_silent_for_unavailable_muted_or_zero_volume(self):
        for options in [{'selected': 'hdmi'}, {'muted': True}, {'volume': 0}]:
            run = self.output_runner(**options)
            self.assertFalse(play_shutdown(self.root, run)); self.assertEqual(run.call_count, 1)
        self.sounds.configure({'shutdown': False})
        run = Mock(); self.assertFalse(play_shutdown(self.root, run)); run.assert_not_called()

    def test_missing_or_hung_audio_never_prevents_poweroff(self):
        self.sounds.configure({'shutdown': True})
        for error in (OSError('missing'), subprocess.TimeoutExpired('paplay', 1.3)):
            with patch('services.device_power.play_shutdown', side_effect=lambda _: play_shutdown(self.root, Mock(side_effect=error))):
                folder = self.root / 'management'
                save(folder / 'maintenance.json', {'command': 'test', 'boot': 'boot', 'expires': time.time() + 60})
                power = Mock(return_value=Mock(returncode=0))
                self.assertTrue(execute_shutdown(folder, 'test', 'logind', power, boot='boot'))
                power.assert_called_once()

    def test_revoked_lease_during_farewell_prevents_poweroff(self):
        folder = self.root / 'management'; marker = folder / 'maintenance.json'
        save(marker, {'command': 'test', 'boot': 'boot', 'expires': time.time() + 60})
        with patch('services.device_power.play_shutdown', side_effect=lambda _: marker.unlink()):
            power = Mock()
            self.assertFalse(execute_shutdown(folder, 'test', 'logind', power, boot='boot'))
            power.assert_not_called()

    def test_startup_never_interrupts_activity_and_is_not_delayed(self):
        from web_server import StudioApp
        for hardware, safe in [(False, True), (True, False), (True, True)]:
            self.sounds.startup_pending = True; self.sounds.configure({'startup': True})
            app = Mock(device_sounds=self.sounds, device_sounds_hardware=hardware)
            app.speech_allowed.return_value = safe
            StudioApp.tick_device_sounds(app)
            self.assertEqual(app.speakers.start_chime.call_count, int(hardware and safe))
            app.speech_allowed.return_value = True
            StudioApp.tick_device_sounds(app)
            self.assertEqual(app.speakers.start_chime.call_count, int(hardware and safe))

    def test_failed_startup_cue_does_not_fail_readiness(self):
        from web_server import StudioApp
        self.sounds.configure({'startup': True}); self.sounds.startup_pending = True
        app = Mock(device_sounds=self.sounds, device_sounds_hardware=True)
        app.speech_allowed.return_value = True
        app.speakers.start_chime.side_effect = ValueError('missing speaker')
        StudioApp.tick_device_sounds(app)
        self.assertFalse(self.sounds.take_startup())
