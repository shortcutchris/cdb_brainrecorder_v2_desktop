import io
import math
import tempfile
import subprocess
import sys
import unittest
from array import array
from unittest.mock import Mock, patch
from services.room_activity import RoomActivity
from services.wake_word import WakeWord


def pcm(level):
    return array('h', (int(math.sin(i * .21) * level * 32767) for i in range(800))).tobytes()


class LevelTests(unittest.TestCase):
    def test_silence_steady_fan_and_single_click_do_not_extend_session(self):
        for level in (0, .002, .04):
            detector = RoomActivity()
            self.assertFalse(any(detector.feed(pcm(level)) for _ in range(200)))
        detector = RoomActivity()
        for _ in range(100): detector.feed(pcm(.002))
        self.assertFalse(detector.feed(pcm(.2)))
        self.assertFalse(detector.feed(pcm(.002)))

    def test_real_worker_emits_only_events_from_synthetic_pcm_without_wake_model(self):
        capture="import sys,math;from array import array;quiet=array('h',[0]*800).tobytes();sound=array('h',[int(math.sin(i*.21)*8000) for i in range(800)]).tobytes();sys.stdout.buffer.write(quiet*100+sound*10)"
        runner="from services.wake_word import detect;detect(capture_command="+repr([sys.executable,'-c',capture])+",phrase='--room-activity')"
        result=subprocess.run([sys.executable,'-c',runner],capture_output=True,text=True,timeout=10,check=True)
        self.assertEqual(result.stdout.splitlines(),['ready','room-activity'])

    def test_changing_room_sound_emits_bounded_level_events(self):
        detector = RoomActivity()
        for _ in range(100): detector.feed(pcm(.002))
        events = [detector.feed(pcm(.08)) for _ in range(10)]
        self.assertEqual(sum(events), 1)
        for _ in range(100): detector.feed(pcm(.002))
        self.assertTrue(any(detector.feed(pcm(.08)) for _ in range(10)))
        self.assertLessEqual(len(detector.levels), 100)
        self.assertTrue(all(isinstance(v, float) for v in detector.levels))


class MonitorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.now = 100
        self.wake = WakeWord(self.tmp.name, lambda: self.now)
        self.wake.runtime = False
        self.account = {'user_id':'synthetic', 'client_id':'test', 'server':'https://example.test'}
        self.touch = Mock(); self.trigger = Mock()

    def tick(self, monitor=True, account=True, reason=''):
        self.wake.tick(account=self.account if account else None, reason=reason,
                       config={'device':'synthetic'}, trigger=self.trigger,
                       monitor=monitor, on_activity=self.touch)

    def child(self, output=b'ready\nroom-activity\ndetected\n'):
        process = Mock(); process.poll.return_value = None
        process.stdout = io.BytesIO(output)
        return process

    def test_monitor_needs_opt_in_and_account_and_no_other_audio_owner(self):
        with patch('services.wake_word.subprocess.Popen') as spawn:
            self.tick(monitor=False)
            self.tick(account=False)
            for reason in ('Aufnahme läuft.', 'Aufnahme pausiert.', 'Gespräch läuft.', 'Wiedergabe läuft.'):
                self.tick(reason=reason)
            spawn.assert_not_called()

    def test_monitor_works_without_wake_model_and_never_starts_talk(self):
        child = self.child()
        with patch('services.wake_word.subprocess.Popen', return_value=child) as spawn, \
             patch('services.wake_word.select.select', return_value=([child.stdout],[],[])):
            self.tick()
        self.assertIn('--room-activity', spawn.call_args.args[0])
        self.assertEqual(self.wake.mode, 'monitoring')
        self.touch.assert_called_once(); self.trigger.assert_not_called()
        self.assertFalse(self.wake.enabled)
        self.assertEqual(self.wake.count, 0)

    def test_existing_wake_stream_shares_activity_signal_without_second_capture(self):
        self.wake.runtime = True; self.wake.enabled = True; self.wake.account = self.account
        child = self.child(b'ready\nroom-activity\n'); self.wake.process = child
        with patch('services.wake_word.subprocess.Popen') as spawn, \
             patch('services.wake_word.select.select', return_value=([child.stdout],[],[])):
            self.tick()
        spawn.assert_not_called(); self.touch.assert_called_once()
        self.assertEqual(self.wake.mode, 'listening')

    def test_stop_failure_retains_microphone_owner_and_blocks_handoff(self):
        child = self.child(); self.wake.process = child; self.wake.activity_only = True
        with patch('services.wake_word.os.killpg', side_effect=PermissionError('synthetic')):
            with self.assertRaises(ValueError): self.wake.suspend('Aufnahme startet.')
        self.assertIs(self.wake.process, child)
        self.assertTrue(self.wake.stop_pending)
        with patch('services.wake_word.os.killpg'):
            self.wake.suspend()
        self.assertIsNone(self.wake.process)

    def test_missing_audio_progress_does_not_refresh_idle_and_stops_on_logout(self):
        child = self.child(b'')
        self.wake.process = child; self.wake.activity_only = True
        self.wake.mode = 'monitoring'; self.wake.read_process = child
        self.wake.progress_at = self.now - 16
        with patch('services.wake_word.select.select', return_value=([],[],[])), \
             patch('services.wake_word.os.killpg'):
            self.tick()
        self.assertEqual(self.wake.mode, 'error'); self.touch.assert_not_called()
        self.assertIsNone(self.wake.process)
        child = self.child(); self.wake.process = child; self.wake.activity_only = True
        with patch('services.wake_word.os.killpg'):
            self.tick(account=False)
        self.assertIsNone(self.wake.process)


if __name__ == '__main__': unittest.main()
