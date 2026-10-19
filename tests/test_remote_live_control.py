"""Real Studio locks/guards and Live lifecycle, with fake audio and CDB only."""
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
import uuid
from unittest.mock import Mock, patch

from services.live_conversation import LiveConversation, BASE
from services.live_audio import PcmGate
from services.remote_control import RemoteControl, RemoteControlError, VerifiedGrant
from web_server import StudioApp

AREA = '11111111-1111-1111-1111-111111111111'
OTHER_AREA = '22222222-2222-2222-2222-222222222222'
BINDING = {'server': 'https://example.test', 'user_id': 'synthetic', 'client_id': AREA}


class Brain:
    def __init__(self):
        self.generation = 0
        self.binding = dict(BINDING)
        self.calls = []
    def read(self, name, fallback):
        return {'server': self.binding['server'], 'client_id': self.binding['client_id'],
                'identity': {'user_id': self.binding['user_id'], 'client_id': self.binding['client_id']}}
    def config(self):
        return {'server': self.binding['server'], 'client_id': self.binding['client_id'],
                'transcription': 'local', 'summary': 'local'}
    def session(self):
        return {'server': self.binding['server'], 'identity': dict(self.binding), 'token': 'NEVER-EXPOSE'}
    def call(self, path, body=None, binding=None):
        self.calls.append((path, body))
        if path.endswith('/capabilities'): return {'enabled': True, 'max_areas': 8}
        if path == BASE + '/sessions': return {'session_handle': 'synthetic', 'sdp_answer': 'v=0\r\nanswer'}
        return {}
    def areas(self, binding=None):
        return [{'id': AREA, 'name': 'Synthetic', 'label': 'Synthetic'}]


class Audio:
    def __init__(self, config, on_failure):
        self.gate = PcmGate()
        self.closed = False
        self.ready = threading.Event()
    def open(self): return 'v=0\r\noffer'
    def answer(self, answer): self.ready.set()
    def mute(self, value): self.gate.mute(value)
    def close(self): self.closed = True


class RemoteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.now = [100.]
        app = self.app = StudioApp.__new__(StudioApp)
        app.control_lock = threading.RLock()
        app.controller = SimpleNamespace(lock=threading.RLock())
        app.engine = SimpleNamespace(recorder=SimpleNamespace(lock=threading.RLock(), active=False))
        self.engine_state = {'recording': {'id': None, 'paused': False},
                             'microphone_test': {'state': 'idle'}, 'installation': {'state': 'idle'},
                             'jobs': [], 'config': {'setup_complete': True}}
        app.engine.state = lambda: self.engine_state
        app.management = SimpleNamespace(busy=lambda: False)
        app.first_start = SimpleNamespace(busy=False)
        app.speakers = SimpleNamespace(test_status=lambda: {'state': 'idle'})
        app.bluetooth = SimpleNamespace(busy=lambda: False)
        app.model_checks = SimpleNamespace(public=lambda: {'state': 'idle'})
        app.model_test = None
        app.store = SimpleNamespace(free_mb=lambda: 10000)
        app.cdb = Brain()
        app.closing = False
        app.clock_ready = True
        app.alarm_id = None
        app.playback_leases = {}
        app.output_busy_until = 0
        app.wake = SimpleNamespace(enabled=False, account=None, test_until=0, suspend=Mock())
        app.live_audio_config = lambda: {'device': 'fake-input', 'speaker': 'fake-output'}
        self.events_done = threading.Event()
        app.live = LiveConversation(app.cdb, self.tmp.name, audio_config=app.live_audio_config,
                                    audio_factory=Audio, events=lambda *args: self.events_done.wait(5))
        app.live.clock = lambda: self.now[0]
        self.addCleanup(app.live.close)
        self.addCleanup(self.events_done.set)
        self.grant = VerifiedGrant('grant-1', 'controller-1', **BINDING, account_generation=0, expires_at=100000)
        self.grants = {(self.grant.grant_id, self.grant.controller_id): self.grant}
        app.remote_control = RemoteControl(app, lambda *key: self.grants.get(key), clock=lambda: self.now[0])
        self.select_areas([AREA])
        self.sequence = 0

    def select_areas(self, ids):
        live = self.app.live
        path = live.root / ('areas-' + live._selection_key(BINDING) + '.json')
        path.write_text(json.dumps({'binding': BINDING, 'area_ids': ids}))

    def envelope(self, action='start', **extra):
        status = self.app.remote_control.status(self.grant)
        self.sequence += 1
        return {'command_id': str(uuid.uuid4()), 'action': action,
                'process_epoch': status['process_epoch'], 'expected_generation': status['generation'],
                'expected_revision': status['revision'], 'expires_at': self.now[0] + 10, **extra}

    def send(self, command=None):
        return self.app.remote_live_command(command or self.envelope(), self.grant)

    def wait(self, predicate):
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            if predicate(): return
            time.sleep(.005)
        self.assertTrue(predicate())

    def start(self):
        result = self.send()
        self.wait(lambda: self.app.live.state == 'listening')
        return result

    def assert_error(self, code, command, grant=None):
        try:
            result = self.app.remote_live_command(command, grant or self.grant)
        except RemoteControlError as error:
            self.assertEqual(error.code, code)
        else:
            self.assertEqual(result['status'], 'expired' if code == 'command_expired' else 'rejected')
            self.assertEqual(result['code'], code)

    def test_real_studio_entry_start_with_wake_off_and_unchanged_device_deadlines(self):
        self.start()
        self.app.wake.suspend.assert_called_once()
        self.assertEqual(self.app.live.owner_kind, 'device')
        self.assertEqual(self.app.live.area_ids, [AREA])
        self.assertEqual(self.app.live.deadline, 220)
        self.assertEqual(self.app.live.maximum, 1300)
        for _ in range(3): self.app.remote_control.status(self.grant)
        self.assertEqual(self.app.live.deadline, 220)
        self.assertFalse(self.app.wake.enabled)

    def test_wake_guard_order_and_shared_helper_unchanged(self):
        self.app.wake.suspend.reset_mock()
        with self.assertRaisesRegex(ValueError, 'Freigabe'): self.app.wake_start()
        self.assertFalse(self.app.live.busy())
        self.app.wake.enabled = True
        self.app.wake.account = dict(BINDING)
        with self.app.control_lock, self.app.controller.lock, self.app.engine.recorder.lock:
            self.app.wake_start()
        self.wait(lambda: self.app.live.state == 'listening')
        self.app.wake.suspend.assert_not_called()
        self.assertEqual(self.app.live.owner_kind, 'device')

    def test_failed_wake_release_never_reserves_or_opens_audio(self):
        self.app.wake.suspend.side_effect = ValueError('private-path-and-token')
        command = self.envelope()
        self.assert_error('operation_failed', command)
        self.assertEqual(self.app.live.generation, 0)
        self.assertIsNone(self.app.live.native)
        self.assertEqual(self.app.cdb.calls, [])
        result = self.send(command)
        self.assertNotIn('private-path', str(result))
        self.app.wake.suspend.assert_called_once()

    def test_real_activity_guards_reject_record_pause_tests_bluetooth_and_maintenance(self):
        cases = [
            ('record', lambda: self.engine_state['recording'].update(id='recording')),
            ('paused', lambda: self.engine_state['recording'].update(id='recording', paused=True)),
            ('mic', lambda: self.engine_state['microphone_test'].update(state='running')),
            ('download', lambda: self.engine_state['installation'].update(state='running')),
            ('speaker', lambda: setattr(self.app.speakers, 'test_status', lambda: {'state': 'running'})),
            ('bluetooth', lambda: setattr(self.app.bluetooth, 'busy', lambda: True)),
            ('maintenance', lambda: setattr(self.app.management, 'busy', lambda: True)),
            ('onboarding', lambda: setattr(self.app.first_start, 'busy', True)),
            ('alarm', lambda: setattr(self.app, 'alarm_id', 'alarm')),
            ('playback', lambda: self.app.playback_leases.update(player=time.monotonic()+60)),
        ]
        for label, block in cases:
            with self.subTest(label=label):
                block()
                self.assert_error('device_busy', self.envelope())
                self.engine_state['recording'].update(id=None, paused=False)
                self.engine_state['microphone_test']['state'] = 'idle'
                self.engine_state['installation']['state'] = 'idle'
                self.app.speakers.test_status = lambda: {'state': 'idle'}
                self.app.bluetooth.busy = lambda: False
                self.app.management.busy = lambda: False
                self.app.first_start.busy = False
                self.app.alarm_id = None
                self.app.playback_leases.clear()
        self.app.wake.suspend.assert_not_called()
        self.assertEqual(self.app.live.generation, 0)

    def test_repeated_and_concurrent_start_only_reserves_once(self):
        command = self.envelope()
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda _: self.send(command), range(8)))
        self.assertTrue(all(result == results[0] for result in results))
        self.assertEqual(self.app.live.generation, 1)
        self.app.wake.suspend.assert_called_once()
        self.assert_error('command_conflict', {**command, 'action': 'end'})

    def test_two_different_start_commands_and_wake_race_get_one_owner(self):
        a, b = self.envelope(), self.envelope()
        self.app.wake.enabled = True
        self.app.wake.account = dict(BINDING)
        def wake():
            try:
                with self.app.control_lock, self.app.controller.lock, self.app.engine.recorder.lock:
                    self.app.wake_start()
                return True
            except ValueError: return False
        def remote(command):
            try: return self.send(command)['status'] == 'applied'
            except ValueError: return False
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = [pool.submit(remote, a), pool.submit(remote, b), pool.submit(wake)]
            results = [future.result() for future in futures]
        self.assertEqual(sum(results), 1)
        self.assertEqual(self.app.live.generation, 1)

    def test_strict_schema_epoch_expiry_and_default_deny(self):
        command = self.envelope()
        for change in ({'action': 'shell'}, {'expected_generation': True}, {'expires_at': float('nan')},
                       {'extra': 'ignored?'}, {'muted': False}, {'area_ids': [AREA]}, {'language': 'de'}):
            self.assert_error('invalid_command', {**command, **change})
        self.assert_error('command_expired', {**command, 'expires_at': 100})
        self.assert_error('command_expired', {**command, 'expires_at': 116})
        self.assert_error('stale_state', {**command, 'process_epoch': str(uuid.uuid4())})
        self.assert_error('stale_state', {**command, 'expected_generation': 23})
        self.app.remote_control.grant_lookup = None
        self.assert_error('grant_revoked', command)

    def test_revoke_account_change_and_forged_verified_grant_deny_before_effects(self):
        command = self.envelope()
        self.assert_error('grant_revoked', command, replace(self.grant, controller_id='other'))
        self.grants.clear()
        self.assert_error('grant_revoked', command)
        self.grants[(self.grant.grant_id, self.grant.controller_id)] = self.grant
        self.app.cdb.generation += 1
        self.assert_error('grant_revoked', command)
        self.app.cdb.generation = 0
        self.app.cdb.binding['user_id'] = 'other-user'
        self.assert_error('grant_revoked', command)
        self.app.wake.suspend.assert_not_called()

    def test_status_poll_stable_selected_area_change_invalidates_start(self):
        one = self.app.remote_control.status(self.grant)
        self.assertEqual(one, self.app.remote_control.status(self.grant))
        command = self.envelope()
        self.select_areas([OTHER_AREA])
        self.assert_error('stale_state', command)
        self.assertEqual(self.app.remote_control.status(self.grant)['areas'], [{'id': OTHER_AREA, 'name': OTHER_AREA}])
        self.assertEqual(self.app.live.generation, 0)

    def test_touch_mute_aba_invalidates_remote_cas_and_pcm_never_replays(self):
        self.start()
        command = self.envelope('set_muted', muted=True)
        native = self.app.live.native
        native.gate.put(b'old speech')
        self.app.action('/api/live/mute', {'muted': True})
        self.app.action('/api/live/mute', {'muted': False})
        self.assert_error('stale_state', command)
        self.assertEqual(native.gate.take(), bytes(640))
        self.send(self.envelope('set_muted', muted=True))
        self.assertTrue(self.app.live.muted)
        for value in (1, 'true', None):
            self.assert_error('invalid_command', self.envelope('set_muted', muted=value))

    def test_end_during_connecting_and_late_end_cannot_touch_next_generation(self):
        opened = threading.Event()
        release = threading.Event()
        class BlockedAudio(Audio):
            def open(self):
                opened.set(); release.wait(2)
                if self.closed: raise ValueError('closed')
                return super().open()
            def close(self):
                super().close(); release.set()
        self.app.live.audio_factory = BlockedAudio
        self.addCleanup(release.set)
        self.send()
        self.assertTrue(opened.wait(1))
        self.assert_error('not_ready', self.envelope('set_muted', muted=True))
        end = self.envelope('end')
        self.send(end)
        self.wait(lambda: not self.app.live.busy())
        self.assertFalse(any(path == BASE + '/sessions' for path, _ in self.app.cdb.calls))
        self.app.live.audio_factory = Audio
        self.start()
        self.send(end)  # Original receipt only, never act on the later session.
        self.assertEqual(self.app.live.state, 'listening')
        self.assert_error('stale_state', {**end, 'command_id': str(uuid.uuid4())})

    def test_bounded_receipts_and_expired_commands_never_replay(self):
        self.app.remote_control.MAX_RECEIPTS = 1
        command = self.envelope()
        self.send(command)
        self.wait(lambda: self.app.live.state == 'listening')
        self.assert_error('rate_limited', self.envelope('end'))
        self.now[0] += 21
        self.assertEqual(self.send(command)['status'], 'applied')
        self.assert_error('rate_limited', self.envelope('end'))
        with self.app.remote_control._db() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM receipts').fetchone()[0], 1)

    def test_results_exclude_credentials_and_do_not_grant_browser_lease(self):
        self.start()
        result = self.app.remote_control.status(self.grant)
        self.assertNotIn('lease', result)
        self.assertNotIn('NEVER-EXPOSE', json.dumps(result))
        self.assertNotIn(self.app.live.lease, json.dumps(result))
        self.assertNotIn('binding', result)
        self.assertNotIn('history', result)

    def test_missing_or_wrong_account_area_selection_never_opens_audio(self):
        self.select_areas([])
        self.assert_error('operation_failed', self.envelope())
        self.assertIsNone(self.app.live.native)
        self.assertEqual(self.app.cdb.calls, [])

    def test_audio_constructor_failure_releases_reservation(self):
        self.app.live.audio_factory = Mock(side_effect=RuntimeError('private credential'))
        self.assert_error('operation_failed', self.envelope())
        self.wait(lambda: not self.app.live.busy())
        self.assertIsNone(self.app.live.native)

    def test_crash_before_or_after_start_effect_is_unknown_and_never_replayed(self):
        class Crash(BaseException): pass
        for after_effect in (False, True):
            with self.subTest(after_effect=after_effect):
                command = self.envelope()
                remote = self.app.remote_control
                original = remote._dispatch
                def crash(command, grant):
                    # A new SQLite connection can see the committed pre-effect row.
                    with remote._db() as db:
                        row = db.execute('SELECT phase FROM receipts WHERE command_id=?',
                                         (command['command_id'],)).fetchone()
                    self.assertEqual(row['phase'], 'executing')
                    if after_effect: original(command, grant)
                    raise Crash()
                with patch.object(remote, '_dispatch', side_effect=crash):
                    with self.assertRaises(Crash): self.send(command)
                generation = self.app.live.generation
                self.app.remote_control = RemoteControl(self.app, lambda *key: self.grants.get(key),
                                                        clock=lambda: self.now[0])
                receipt = self.app.remote_control.receipt(command['command_id'], self.grant)
                self.assertEqual(receipt['status'], 'unknown')
                self.assertNotEqual(remote.process_epoch, self.app.remote_control.process_epoch)
                self.assertEqual(self.send(command)['status'], 'unknown')
                self.assertEqual(self.app.live.generation, generation)
                if self.app.live.busy():
                    self.app.live.end()
                    self.wait(lambda: not self.app.live.busy())

    def test_applied_receipt_survives_lost_ack_restart_and_24h_retention(self):
        command = self.envelope()
        original = self.send(command)
        self.app.remote_control = RemoteControl(self.app, lambda *key: self.grants.get(key),
                                                clock=lambda: self.now[0])
        self.assertEqual(self.app.remote_control.receipt(command['command_id'], self.grant), original)
        self.assertEqual(self.send(command), original)
        self.assertEqual(self.app.live.generation, 1)
        self.now[0] += 23 * 60 * 60
        self.assertEqual(self.app.remote_control.receipt(command['command_id'], self.grant), original)
        self.grants.clear()
        self.assert_error('grant_revoked', command)

    def test_end_receipt_only_applied_after_real_cleanup_generation_advances(self):
        self.start()
        audio = self.app.live.native
        audio.close = Mock(side_effect=TimeoutError('private cleanup detail'))
        command = self.envelope('end')
        result = self.send(command)
        self.assertEqual(result['status'], 'unknown')
        self.assertEqual(result['code'], 'cleanup_pending')
        self.wait(lambda: self.app.live.pending_finish is not None)
        self.assertEqual(self.app.remote_control.receipt(command['command_id'], self.grant)['status'], 'unknown')
        self.assertTrue(self.app.live.busy())
        audio.close.side_effect = None
        with self.app.live.lock: self.app.live._finish('ended')
        receipt = self.app.remote_control.receipt(command['command_id'], self.grant)
        self.assertEqual(receipt['status'], 'applied')
        self.assertEqual(receipt['snapshot']['state'], 'error')  # Preserve the cleanup failure diagnostic.
        self.assertFalse(self.app.live.busy())

    def test_clock_untrusted_blocks_start_unmute_but_allows_mute_end(self):
        self.app.clock_ready = False
        self.assert_error('clock_untrusted', self.envelope())
        self.app.clock_ready = True
        self.start()
        self.app.clock_ready = False
        self.send(self.envelope('set_muted', muted=True))
        self.assert_error('clock_untrusted', self.envelope('set_muted', muted=False))
        result = self.send(self.envelope('end'))
        self.assertNotEqual(result['status'], 'rejected')

    def test_expiry_and_revocation_during_wake_release_prevent_start(self):
        self.app.wake.suspend.side_effect = lambda: self.now.__setitem__(0, self.now[0]+11)
        self.assert_error('command_expired', self.envelope())
        self.app.wake.suspend.side_effect = lambda: self.grants.clear()
        self.assert_error('grant_revoked', self.envelope())
        self.assertEqual(self.app.live.generation, 0)
        self.assertIsNone(self.app.live.native)

    def test_touch_record_and_remote_share_actual_studio_reservation_lock(self):
        self.app.store.config = lambda: {'setup_complete': True}
        def record_start(title):
            self.engine_state['recording']['id'] = 'synthetic-recording'
            self.app.engine.recorder.active = True
            return 'synthetic-recording'
        self.app.engine.start = record_start
        command = self.envelope()
        barrier = threading.Barrier(2)
        def record():
            barrier.wait()
            try: self.app.action('/api/record/start', {}); return True
            except ValueError: return False
        def remote():
            barrier.wait()
            try: return self.send(command)['status'] == 'applied'
            except RemoteControlError: return False
        with ThreadPoolExecutor(max_workers=2) as pool:
            a, b = pool.submit(record), pool.submit(remote)
            self.assertEqual(int(a.result()) + int(b.result()), 1)
        self.assertFalse(self.app.engine.recorder.active and self.app.live.busy())

    def test_new_account_status_never_discloses_old_live_areas(self):
        self.start()
        self.app.cdb.binding['user_id'] = 'other-account'
        self.app.cdb.generation += 1
        grant = replace(self.grant, user_id='other-account', account_generation=1,
                        grant_id='new-grant')
        self.grants[(grant.grant_id, grant.controller_id)] = grant
        snapshot = self.app.remote_control.status(grant)
        self.assertEqual(snapshot['areas'], [])
        self.assertEqual(snapshot['allowed_actions'], [])

    def test_new_and_existing_profiles_have_private_default_denied_journal(self):
        remote = self.app.remote_control
        self.assertEqual(remote.journal.stat().st_mode & 0o777, 0o600)
        self.assertEqual(remote.journal.parent.stat().st_mode & 0o777, 0o700)
        self.assertEqual(remote.journal.name, 'receipts.sqlite3')
        disabled = RemoteControl(self.app, clock=lambda: self.now[0])
        with self.assertRaises(RemoteControlError): disabled.status(self.grant)
        # Existing profiles retain their saved selection after first initialization.
        self.assertEqual(remote.status(self.grant)['areas'][0]['id'], AREA)

    def test_failed_journal_initialization_disables_remote_without_breaking_studio(self):
        with patch.object(RemoteControl, '_initialize_journal', side_effect=PermissionError('private path')):
            disabled = RemoteControl(self.app)
        self.assertFalse(disabled.journal_ready)
        with self.assertRaises(RemoteControlError) as caught: disabled.status(self.grant)
        self.assertEqual(caught.exception.code, 'device_control_unavailable')
        self.assertNotIn('private path', str(caught.exception))
        self.assertFalse(self.app.live.busy())

    def test_terminal_journal_entries_only_pruned_after_24_hours(self):
        self.app.closing = True
        original = self.envelope()
        self.assert_error('device_busy', original)
        self.now[0] += 24 * 60 * 60 - 1
        self.assert_error('device_busy', self.envelope())
        self.assertEqual(self.app.remote_control.receipt(original['command_id'], self.grant)['status'], 'rejected')
        self.now[0] += 2
        self.assert_error('device_busy', self.envelope())
        with self.assertRaises(RemoteControlError) as caught:
            self.app.remote_control.receipt(original['command_id'], self.grant)
        self.assertEqual(caught.exception.code, 'not_found')
        self.assert_error('command_expired', original)


if __name__ == '__main__': unittest.main()
