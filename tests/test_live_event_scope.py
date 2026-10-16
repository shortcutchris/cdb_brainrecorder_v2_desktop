"""Old cloud streams must not inherit a newer conversation's active state."""
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch

from services.live_conversation import LiveConversation

AREA = '11111111-1111-1111-1111-111111111111'
BINDING = {'server': 'https://example.test', 'user_id': 'synthetic', 'client_id': AREA}


class Response:
    def __init__(self, rows):
        self.rows = rows
        self.closed = False
        self.consumed = 0

    def __enter__(self): return self
    def __exit__(self, *args): self.closed = True

    def __iter__(self):
        for row in self.rows():
            self.consumed += 1
            yield row


class LiveEventScopeTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.brain = Mock()
        self.brain.generation = 0
        self.brain.session.return_value = {'server': BINDING['server'], 'token': 'synthetic'}
        self.live = LiveConversation(self.brain, self.root.name)
        self.activate()
        self.generation = self.live.generation

    def activate(self):
        self.live.reserve([AREA], owner_kind='device', cached_binding=BINDING)
        # Reuse the handle deliberately: generation, not a server string alone,
        # must distinguish the old conversation from the new one.
        self.live.handle = 'synthetic-handle'
        self.live.state = 'listening'

    def replace(self):
        with self.live.lock:
            self.live._finish('ended')
            self.activate()

    def tearDown(self):
        self.live.close()
        self.live.watch.join(2)
        self.root.cleanup()

    def test_old_keepalive_stream_closes_when_next_conversation_starts(self):
        def rows():
            yield b': heartbeat\n'
            self.replace()
            yield b': heartbeat from old session\n'
            yield b'event: transcript\n'
            yield b'data: {"role":"user","delta":"old"}\n'
            yield b'\n'
        response = Response(rows)
        opener = Mock()
        opener.open.return_value = response
        callback = Mock()
        with patch('services.live_conversation.urllib.request.build_opener', return_value=opener):
            self.live._read_events('synthetic-handle', BINDING, callback, generation=self.generation)
        self.assertTrue(response.closed)
        self.assertEqual(response.consumed, 2, 'obsolete reader consumed the next session lifetime')
        callback.assert_not_called()
        self.assertEqual(self.live.state, 'listening')
        self.assertNotEqual(self.live.generation, self.generation)

    def test_already_obsolete_reader_does_not_refresh_token_or_open_network(self):
        self.replace()
        with patch('services.live_conversation.urllib.request.build_opener') as build:
            self.live._read_events('synthetic-handle', BINDING, Mock(), generation=self.generation)
        self.brain.session.assert_not_called()
        build.assert_not_called()

    def test_token_refresh_finishing_after_replacement_does_not_open_stream(self):
        def session(binding):
            self.replace()
            return {'server': BINDING['server'], 'token': 'synthetic-refreshed'}
        self.brain.session.side_effect = session
        with patch('services.live_conversation.urllib.request.build_opener') as build:
            self.live._read_events('synthetic-handle', BINDING, Mock(), generation=self.generation)
        build.assert_not_called()
        self.assertEqual(self.live.state, 'listening')

    def test_open_finishing_after_replacement_closes_without_reading(self):
        response = Response(lambda: iter([b': heartbeat\n']))
        def opened(*args, **kwargs):
            self.replace()
            return response
        opener = Mock()
        opener.open.side_effect = opened
        with patch('services.live_conversation.urllib.request.build_opener', return_value=opener):
            self.live._read_events('synthetic-handle', BINDING, Mock(), generation=self.generation)
        self.assertTrue(response.closed)
        self.assertEqual(response.consumed, 0)

    def test_account_change_closes_old_keepalive_stream(self):
        def rows():
            yield b': heartbeat\n'
            self.brain.generation += 1
            yield b': heartbeat\n'
            yield b': obsolete\n'
        response = Response(rows)
        opener = Mock()
        opener.open.return_value = response
        with patch('services.live_conversation.urllib.request.build_opener', return_value=opener):
            self.live._read_events('synthetic-handle', BINDING, Mock(), generation=self.generation)
        self.assertTrue(response.closed)
        self.assertEqual(response.consumed, 2)

    def test_current_stream_keeps_delivering_transcript_and_closes_on_eof(self):
        response = Response(lambda: iter([
            b': heartbeat\n', b'\n', b'event: transcript\n',
            b'data: {"role":"user","delta":"current"}\n', b'\n']))
        opener = Mock()
        opener.open.return_value = response
        callback = Mock()
        with patch('services.live_conversation.urllib.request.build_opener', return_value=opener):
            self.live._read_events('synthetic-handle', BINDING, callback, generation=self.generation)
        callback.assert_called_once_with('transcript', {'role': 'user', 'delta': 'current'})
        self.assertTrue(response.closed)

    def test_closing_current_conversation_preserves_final_transcript(self):
        def rows():
            yield b': heartbeat\n'
            self.live.state = 'closing'
            yield b'event: transcript\n'
            yield b'data: {"role":"user","delta":"final words"}\n'
            yield b'\n'
            yield b'event: closed\n'
            yield b'data: {}\n'
            yield b'\n'
            yield b': after close\n'
            yield b': obsolete\n'
        response = Response(rows)
        opener = Mock()
        opener.open.return_value = response
        with patch('services.live_conversation.urllib.request.build_opener', return_value=opener):
            self.live._read_events('synthetic-handle', BINDING,
                                  lambda name, data: self.live._frame(self.generation, name, data),
                                  generation=self.generation)
        self.assertTrue(response.closed)
        self.assertEqual(response.consumed, 8)
        self.assertEqual(self.live.state, 'ended')
        self.assertEqual(self.live.history, [{'role': 'user', 'text': 'final words'}])

    def test_default_event_loop_passes_its_generation_to_reader(self):
        self.live.stop.set()
        self.live.watch.join(2)
        def read(handle, binding, callback, *, generation):
            self.assertEqual(generation, self.generation)
            self.replace()
        with patch.object(self.live, '_read_events', side_effect=read) as reader:
            self.live._events(self.generation, 'synthetic-handle', BINDING)
        reader.assert_called_once()
        self.assertEqual(self.live.state, 'listening')

    def test_100_successive_conversations_leave_no_obsolete_reader_threads(self):
        opener = Mock()
        with patch('services.live_conversation.urllib.request.build_opener', return_value=opener):
            for _ in range(100):
                entered, release = threading.Event(), threading.Event()
                failures = []
                callback = Mock()
                generation = self.live.generation
                def rows():
                    yield b': heartbeat\n'
                    entered.set()
                    if not release.wait(2): raise AssertionError('Test did not release old stream')
                    yield b': late heartbeat\n'
                    yield b': must not be read\n'
                response = Response(rows)
                opener.open.return_value = response
                def read():
                    try:
                        self.live._read_events('synthetic-handle', BINDING, callback, generation=generation)
                    except Exception as error:
                        failures.append(error)
                worker = threading.Thread(target=read)
                worker.start()
                try:
                    self.assertTrue(entered.wait(1))
                    self.replace()
                finally:
                    release.set()
                    worker.join(2)
                self.assertFalse(worker.is_alive(), 'obsolete reader survived conversation replacement')
                self.assertEqual(failures, [])
                self.assertTrue(response.closed)
                self.assertEqual(response.consumed, 2)
                callback.assert_not_called()
                self.assertEqual(self.live.state, 'listening')
