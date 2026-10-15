"""Real account/live services with synthetic transport; no network or audio hardware."""
import tempfile
import threading
import time
import unittest

from services.cdb_integration import CdbFailure, CdbService, DEFAULT
from services.live_conversation import BASE, LiveConversation


TENANT = '11111111-1111-1111-1111-111111111111'
AREA = '22222222-2222-2222-2222-222222222222'


class RefreshTransport:
    def __init__(self):
        self.entered = threading.Event()
        self.release = threading.Event()
        self.fail = False
        self.refreshes = 0
        self.sessions = 0

    def request(self, url, body=None, token=None, form=False):
        if url.endswith('/token'):
            self.refreshes += 1
            self.entered.set()
            if not self.release.wait(3):
                raise AssertionError('Test did not release synthetic authentication')
            if self.fail:
                raise CdbFailure('synthetic provider-private failure')
            return {'access_token': 'synthetic-new', 'refresh_token': 'synthetic-refresh',
                    'expires_in': 3600, 'token_type': 'Bearer'}
        if url.endswith('/auth/me'):
            return {'user_id': 'synthetic-user', 'client_id': TENANT, 'is_active': True}
        if url.endswith('/capabilities'):
            assert token == 'synthetic-new'
            return {'enabled': True, 'max_areas': 8}
        if '/knowledge-areas?' in url:
            return {'knowledge_areas': [{'id': AREA, 'name': 'staging_playground',
                                        'client_id': TENANT, 'is_active': True}]}
        if url.endswith(BASE + '/sessions'):
            assert token == 'synthetic-new'
            self.sessions += 1
            return {'session_handle': 'synthetic-handle', 'sdp_answer': 'v=0\r\nanswer'}
        if url.endswith('/close'):
            return {}
        raise AssertionError('Unexpected synthetic transport route')


class AudioProbe:
    def __init__(self, config, failed):
        self.closed = False
        self.answers = 0

    def open(self):
        return 'v=0\r\nsynthetic-offer'

    def answer(self, sdp):
        assert not self.closed, 'Audio was revived after cancellation'
        self.answers += 1

    def close(self):
        self.closed = True


class LiveRefreshTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.transport = RefreshTransport()
        self.cdb = CdbService(self.root.name, self.transport)
        self.cdb.save_token({'access_token': 'synthetic-old', 'refresh_token': 'synthetic-refresh',
                            'expires_in': 3600, 'token_type': 'Bearer'}, DEFAULT)
        saved = self.cdb.read('session.json', {})
        saved['expires'] = 0
        self.cdb.write('session.json', saved)
        self.binding = {'server': saved['server'], 'user_id': 'synthetic-user', 'client_id': TENANT}
        self.events_release = threading.Event()
        self.audio = []

        def factory(config, failed):
            probe = AudioProbe(config, failed)
            self.audio.append(probe)
            return probe

        self.live = LiveConversation(
            self.cdb, self.root.name,
            events=lambda *args: self.events_release.wait(3),
            audio_config=lambda: {'device': 'synthetic', 'speaker': 'synthetic'},
            audio_factory=factory)

    def tearDown(self):
        self.transport.release.set()
        self.events_release.set()
        self.live.close()
        self.live.watch.join(2)
        self.cdb.close()
        self.root.cleanup()

    def start(self):
        lease = self.live.reserve([AREA], owner_kind='device', cached_binding=self.binding)['lease']
        self.live.start_native(lease)

    def wait_listening(self):
        deadline = time.monotonic() + 2
        while self.live.public()['state'] == 'connecting' and time.monotonic() < deadline:
            time.sleep(.01)
        self.assertEqual(self.live.public()['state'], 'listening')

    def test_cancel_during_refresh_keeps_owner_until_worker_finishes_then_can_restart(self):
        self.start()
        self.assertTrue(self.transport.entered.wait(1))
        self.assertEqual(self.live.public()['state'], 'connecting')
        self.assertEqual(self.cdb.public()['identity']['user_id'], 'synthetic-user')
        self.live.end()
        self.assertTrue(self.audio[0].closed)
        self.assertEqual(self.live.public()['state'], 'closing')
        with self.assertRaisesRegex(ValueError, 'bereits'):
            self.live.reserve([AREA], owner_kind='device', cached_binding=self.binding)
        self.transport.release.set()
        self.assertTrue(self.live.finished.wait(2))
        self.assertFalse(self.live.busy())
        self.assertEqual(self.transport.sessions, 0)
        self.assertEqual(self.audio[0].answers, 0)
        self.start()
        self.wait_listening()
        self.assertEqual(self.transport.refreshes, 1)
        self.assertEqual(self.transport.sessions, 1)
        self.assertEqual(self.audio[1].answers, 1)
        self.live.end()
        self.assertTrue(self.live.finished.wait(2))
        self.assertTrue(all(probe.closed for probe in self.audio))
        self.assertIsNone(self.live.native)

    def test_failed_refresh_releases_audio_and_retry_revalidates_saved_account(self):
        self.transport.fail = True
        self.transport.release.set()
        self.start()
        self.assertTrue(self.live.finished.wait(2))
        self.assertEqual(self.live.public()['state'], 'error')
        self.assertFalse(self.live.busy())
        self.assertNotIn('provider-private', str(self.live.public()))
        self.assertEqual(self.transport.sessions, 0)
        self.assertTrue(self.audio[0].closed)
        self.assertEqual(self.cdb.read('session.json', {})['token'], 'synthetic-old')
        self.transport.fail = False
        self.start()
        self.wait_listening()
        self.assertEqual(self.transport.refreshes, 2)
        self.assertEqual(self.transport.sessions, 1)
        self.assertEqual(self.cdb.read('session.json', {})['token'], 'synthetic-new')
        self.live.end()
        self.assertTrue(self.live.finished.wait(2))
        self.assertIsNone(self.live.native)
        self.assertTrue(all(probe.closed for probe in self.audio))
