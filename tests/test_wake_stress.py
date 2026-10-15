"""Isolated fault injection: no real audio, credentials, network or recordings."""
from concurrent.futures import ThreadPoolExecutor
import io
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch

from services.wake_word import WakeWord
from services.live_conversation import LiveConversation

AREA = '11111111-1111-1111-1111-111111111111'
BINDING = {'server': 'https://example.test', 'user_id': 'test', 'client_id': AREA}


class WakeFaultTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.now = 100.
        self.wake = WakeWord(self.root.name, lambda: self.now)
        self.wake.runtime = True
        self.wake.configure(True, BINDING)
        self.wake.cooldown = 0
        self.trigger = Mock()

    def tearDown(self):
        self.wake.process = None
        self.root.cleanup()

    def tick(self, reason=''):
        self.wake.tick(account=BINDING, reason=reason, config={'device': 'synthetic'}, trigger=self.trigger)

    def test_stalled_child_is_released_after_start_timeout(self):
        child = Mock()
        child.poll.return_value = None
        child.stdout = io.BytesIO()
        with patch('services.wake_word.subprocess.Popen', return_value=child), patch('services.wake_word.select.select', return_value=([], [], [])), patch('services.wake_word.os.killpg'):
            self.tick()
            self.now += 40
            self.tick()
            self.assertIsNone(self.wake.process)
            self.assertEqual(self.wake.mode, 'error')
            self.trigger.assert_not_called()

    def test_partial_child_output_never_blocks_recording_control_lock(self):
        read_fd, write_fd = os.pipe()
        reader = os.fdopen(read_fd, 'rb', buffering=0)
        child = Mock()
        child.stdout = reader
        child.poll.return_value = None
        self.wake.process = child
        done = threading.Event()
        worker = threading.Thread(target=lambda: (self.tick(), done.set()))
        try:
            os.write(write_fd, b'rea')
            worker.start()
            responsive = done.wait(.2)
        finally:
            os.close(write_fd)
            worker.join(1)
            reader.close()
        self.assertTrue(responsive, 'partial child line blocked the ambient/control loop')
        self.trigger.assert_not_called()

    def test_100_double_mentions_transfer_capture_only_once_per_cycle(self):
        with patch('services.wake_word.select.select', return_value=([True], [], [])), patch('services.wake_word.os.killpg'):
            for cycle in range(100):
                self.now += 5
                child = Mock()
                child.poll.return_value = None
                child.stdout = io.BytesIO(b'detected\ndetected\n')
                self.wake.process = child
                self.tick()
                self.assertIsNone(self.wake.process)
                self.tick(reason='Live-Gespräch läuft.')
                self.assertEqual(self.trigger.call_count, cycle + 1)
                child.wait.assert_called_once()
        self.assertEqual(self.wake.count, 100)

    def test_progress_recovers_stalled_listening_and_respects_recording(self):
        child = Mock()
        child.poll.return_value = None
        child.stdout = io.BytesIO(b'ready\n')
        with patch('services.wake_word.subprocess.Popen', return_value=child) as spawn, patch('services.wake_word.select.select', return_value=([True], [], [])) as select, patch('services.wake_word.os.killpg'):
            self.tick()
            self.assertEqual(self.wake.mode, 'listening')
            for _ in range(100):
                self.now += 2
                child.stdout = io.BytesIO(b'alive\n')
                self.tick()
                self.assertEqual(self.wake.mode, 'listening')
            self.now += 16
            select.return_value = ([], [], [])
            self.tick()
            self.assertIsNone(self.wake.process)
            self.assertEqual(self.wake.mode, 'error')
            self.now += 11
            self.tick(reason='Aufnahme pausiert.')
            self.assertEqual(spawn.call_count, 1)
            child.stdout = io.BytesIO(b'ready\n')
            select.return_value = ([True], [], [])
            self.tick()
            self.assertEqual(spawn.call_count, 2)
            self.assertEqual(self.wake.mode, 'listening')
            self.trigger.assert_not_called()

    def test_child_imports_own_release_not_service_working_directory(self):
        child = Mock()
        child.poll.return_value = None
        child.stdout = io.BytesIO(b'ready\n')
        with tempfile.TemporaryDirectory() as unrelated:
            previous = os.getcwd()
            try:
                os.chdir(unrelated)
                with patch('services.wake_word.subprocess.Popen', return_value=child) as spawn, patch('services.wake_word.select.select', return_value=([True], [], [])):
                    self.tick()
                expected = str(Path(__import__('services.wake_word', fromlist=['__file__']).__file__).resolve().parents[1])
                self.assertEqual(spawn.call_args.kwargs['cwd'], expected)
                self.assertNotEqual(spawn.call_args.kwargs['cwd'], unrelated)
            finally:
                os.chdir(previous)


class LiveStressTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.entered, self.release = threading.Event(), threading.Event()
        self.brain = Mock()
        self.brain.generation = 0
        self.brain.call.side_effect = self.call
        self.live = LiveConversation(self.brain, self.root.name)

    def tearDown(self):
        self.release.set()
        self.live.close()
        self.live.watch.join(2)
        self.root.cleanup()

    def call(self, path, *args, **kwargs):
        if path.endswith('/heartbeat'):
            self.entered.set()
            self.release.wait(5)
            raise TimeoutError('synthetic heartbeat failure')
        return {}

    def reserve(self):
        return self.live.reserve([AREA], owner_kind='device', cached_binding=BINDING)

    def heartbeat_pending(self):
        self.reserve()
        with self.live.lock:
            self.live.handle = 'old-session'
            self.live.state = 'listening'
            self.live.last_heartbeat = time.monotonic() - 20
        self.assertTrue(self.entered.wait(2))

    def test_slow_heartbeat_does_not_block_voice_end(self):
        self.heartbeat_pending()
        with self.live.lock:
            self.live._transcript({'role': 'user', 'delta': 'Gespräch beenden'})
        self.assertTrue(self.live.finished.wait(3), 'heartbeat prevented local end-command handling')
        self.assertEqual(self.live.end_reason, 'voice_command')

    def test_late_heartbeat_failure_cannot_end_new_conversation(self):
        self.heartbeat_pending()
        self.live.end()
        self.assertTrue(self.live.finished.wait(1))
        self.reserve()
        generation = self.live.generation
        self.release.set()
        time.sleep(.2)
        self.assertEqual(self.live.generation, generation)
        self.assertTrue(self.live.busy())

    def test_100_concurrent_reservation_rounds_have_exactly_one_owner(self):
        self.live.stop.set()
        self.live.watch.join(2)
        with ThreadPoolExecutor(max_workers=8) as pool:
            for _ in range(100):
                barrier = threading.Barrier(8)
                def attempt():
                    barrier.wait()
                    try:
                        self.reserve()
                        return True
                    except ValueError:
                        return False
                self.assertEqual(sum(f.result() for f in [pool.submit(attempt) for _ in range(8)]), 1)
                self.live.end()
                self.assertTrue(self.live.finished.wait(1))
                self.assertIsNone(self.live.native)
                self.assertFalse(self.live.busy())
