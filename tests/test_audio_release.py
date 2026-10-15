"""Cleanup failure injection; no hardware, network, user profile or audio."""
import io
from concurrent.futures import ThreadPoolExecutor
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import AsyncMock, Mock, patch

from services.live_audio import NativeLiveAudio
from services.live_conversation import LiveConversation
from services.wake_word import WakeWord

AREA = '11111111-1111-1111-1111-111111111111'
BINDING = {'server': 'https://example.test', 'user_id': 'synthetic', 'client_id': AREA}


class WakeReleaseTests(unittest.TestCase):
    def test_owned_child_is_reaped_on_retry_after_signal_failure(self):
        with tempfile.TemporaryDirectory() as root:
            wake = WakeWord(root)
            child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(20)'],
                                     stdout=subprocess.PIPE, start_new_session=True)
            wake.process = child
            try:
                with patch('services.wake_word.os.killpg', side_effect=PermissionError('synthetic')):
                    with self.assertRaises(ValueError): wake.suspend()
                self.assertIsNone(child.poll())
                self.assertIs(wake.process, child)
                wake.suspend()
                self.assertIsNotNone(child.poll())
                self.assertIsNone(wake.process)
            finally:
                if child.poll() is None: child.kill(); child.wait(timeout=2)
                child.stdout.close()

    def test_failed_kill_keeps_owner_and_never_triggers_or_respawns(self):
        with tempfile.TemporaryDirectory() as root:
            now = [100.]
            wake = WakeWord(root, lambda: now[0])
            wake.runtime = True
            wake.configure(True, BINDING)
            child = Mock(); child.poll.return_value = None
            child.stdout = io.BytesIO(b'detected\n')
            wake.process = child
            trigger = Mock()
            with patch('services.wake_word.os.killpg', side_effect=PermissionError('private detail')), patch('services.wake_word.subprocess.Popen') as spawn:
                with self.assertRaisesRegex(ValueError, 'freigegeben'):
                    wake.suspend()
                self.assertIs(wake.process, child)
                self.assertFalse(child.stdout.closed)
                for _ in range(3):
                    now[0] += 11
                    wake.tick(account=BINDING, reason='', config={'device': 'synthetic'}, trigger=trigger)
                spawn.assert_not_called(); trigger.assert_not_called()
                self.assertEqual(wake.public()['state'], 'error')
                self.assertNotIn('private detail', str(wake.public()))
            with patch('services.wake_word.os.killpg'):
                now[0] += 11
                wake.tick(account=BINDING, reason='Aufnahme pausiert.', config={'device': 'synthetic'}, trigger=trigger)
            self.assertIsNone(wake.process)
            self.assertFalse(wake.stop_pending)
            self.assertTrue(child.stdout.closed)
            trigger.assert_not_called()

    def test_timeout_after_sigkill_retains_process_until_confirmed_exit(self):
        with tempfile.TemporaryDirectory() as root:
            wake = WakeWord(root)
            child = Mock(); child.stdout = io.BytesIO()
            child.wait.side_effect = subprocess.TimeoutExpired('synthetic', 2)
            wake.process = child
            with patch('services.wake_word.os.killpg') as kill:
                with self.assertRaises(ValueError): wake.suspend()
                self.assertEqual(kill.call_count, 2)
                self.assertIs(wake.process, child)
                child.wait.side_effect = None
                wake.suspend()
            self.assertIsNone(wake.process)


class LiveReleaseTests(unittest.TestCase):
    def test_failed_native_close_keeps_reservation_then_recovers(self):
        with tempfile.TemporaryDirectory() as root:
            brain = Mock(); brain.generation = 0
            now = [100.]
            live = LiveConversation(brain, root, clock=lambda: now[0])
            audio = Mock(); audio.close.side_effect = TimeoutError('private detail')
            try:
                live.reserve([AREA], owner_kind='device', cached_binding=BINDING)
                generation = live.generation
                live.native = audio
                with live.lock: live._finish('ended')
                self.assertTrue(live.busy())
                self.assertEqual(live.state, 'closing')
                self.assertIs(live.native, audio)
                self.assertFalse(live.finished.is_set())
                self.assertEqual(live.generation, generation)
                with self.assertRaises(ValueError):
                    live.reserve([AREA], owner_kind='device', cached_binding=BINDING)
                self.assertNotIn('private detail', live.public()['error'])
                audio.close.side_effect = None
                now[0] += 6
                self.assertTrue(live.finished.wait(2), 'cleanup watcher did not retry')
                self.assertFalse(live.busy())
                self.assertIsNone(live.native)
                live.reserve([AREA], owner_kind='device', cached_binding=BINDING)
                self.assertTrue(live.busy())
            finally:
                audio.close.side_effect = None
                live.close(); live.watch.join(2)

    def test_cloud_close_ack_cannot_release_failed_local_audio(self):
        with tempfile.TemporaryDirectory() as root:
            brain = Mock(); brain.generation = 0
            live = LiveConversation(brain, root)
            audio = Mock(); audio.close.side_effect = OSError('synthetic')
            try:
                live.reserve([AREA], owner_kind='device', cached_binding=BINDING)
                live.native = audio
                live._frame(live.generation, 'closed', {})
                self.assertTrue(live.busy())
                self.assertIs(live.native, audio)
                self.assertFalse(live.finished.is_set())
            finally:
                audio.close.side_effect = None
                with live.lock: live._finish('ended')
                live.close(); live.watch.join(2)


class NativeReleaseTests(unittest.TestCase):
    def test_100_concurrent_close_retries_leave_no_audio_threads(self):
        # Real event loops and simultaneous callers, but no microphone, playback
        # process or cloud connection. Exercise the newly retryable close path.
        with ThreadPoolExecutor(max_workers=2) as pool:
            for cycle in range(100):
                with self.subTest(cycle=cycle):
                    audio = NativeLiveAudio({}, capture_command=['unused'], playback_command=['unused'])
                    original = audio._shutdown
                    attempts = []
                    async def transient_failure():
                        attempts.append(True)
                        if len(attempts) == 1: raise OSError('synthetic transient failure')
                        await original()
                    barrier = threading.Barrier(2)
                    def close():
                        barrier.wait(timeout=3)
                        try:
                            audio.close()
                            return 'closed'
                        except RuntimeError:
                            return 'retry-required'
                    try:
                        with patch.object(audio, '_shutdown', new=transient_failure):
                            pending = [pool.submit(close) for _ in range(2)]
                            outcomes = [future.result(timeout=5) for future in pending]
                        self.assertCountEqual(outcomes, ['closed', 'retry-required'])
                        self.assertEqual(len(attempts), 2)
                        self.assertTrue(audio.cleanup_complete)
                        self.assertFalse(audio.thread.is_alive())
                        self.assertTrue(audio.loop.is_closed())
                        self.assertEqual(audio.stats()['processes_alive'], 0)
                    finally:
                        audio.close()

    def test_failed_shutdown_is_retryable_even_after_closed_flag(self):
        audio = NativeLiveAudio({}, capture_command=['unused'], playback_command=['unused'])
        try:
            with patch.object(audio, '_shutdown', new=AsyncMock(side_effect=OSError('synthetic'))):
                with self.assertRaises(RuntimeError): audio.close()
            self.assertTrue(audio.closed.is_set())
            self.assertTrue(audio.thread.is_alive())
            self.assertFalse(audio.cleanup_complete)
            audio.close()
            self.assertTrue(audio.cleanup_complete)
            self.assertFalse(audio.thread.is_alive())
            audio.close()  # Successful cleanup remains idempotent.
        finally:
            audio.close()

    def test_unreaped_process_never_counts_as_closed(self):
        audio = NativeLiveAudio({}, capture_command=['unused'], playback_command=['unused'])
        child = Mock(); child.returncode = None
        child.wait = AsyncMock(return_value=None)
        audio.processes.append(child)
        try:
            with patch.object(audio, '_shutdown', new=AsyncMock()), patch('services.live_audio.os.killpg'):
                with self.assertRaisesRegex(RuntimeError, 'not exited'): audio.close()
            self.assertFalse(audio.cleanup_complete)
            self.assertTrue(audio.thread.is_alive())
        finally:
            child.returncode = 0
            audio.processes.clear()
            audio.close()


if __name__ == '__main__':
    unittest.main()
