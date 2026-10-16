"""Synthetic broker + actual channel/Studio domain: never opens audio or network."""
import copy
import json
import os
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
import uuid
from unittest.mock import Mock, patch

from services.remote_control_transport import RemoteControlChannel, ChannelError, create_channel, HTTPSControl
import test_remote_live_control as fixtures
AREA = fixtures.AREA

USER = '33333333-3333-3333-3333-333333333333'
GRANT = '44444444-4444-4444-4444-444444444444'
CONTROLLER = '55555555-5555-5555-5555-555555555555'


class Broker:
    def __init__(self, app, now):
        self.app, self.now = app, now
        self.calls = []
        self.device = None
        self.active = False
        self.pending = False
        self.revision = 0
        self.commands = []
        self.receipts = []
        self.hook = None
        self.failure = None
        self.enabled = True
    def request(self, origin, path, token, body=None):
        self.calls.append((origin, path, body))
        if self.failure: raise self.failure
        binding = {'environment': origin, 'user_id': USER, 'client_id': AREA}
        if path == '/capabilities': return {'device_control_v1': self.enabled, 'protocol_version': 1}
        if path == '/devices/register':
            assert len(body['credential_hash']) == 64 and 'credential' not in body
            self.device = body['device_id']; return {'device_id': self.device, 'binding': binding}
        if path == '/device/pairings': return {'code': 'ABCD2345', 'expires_at': self.now[0] + 300}
        if path.endswith('/confirm'):
            self.active = body['approved']; self.pending = False; self.revision += 1
            return {}
        if path == '/device/poll':
            result = {'protocol_version': 1, 'binding': binding, 'grants_revision': self.revision,
                      'grants': [{'grant_id': GRANT, 'controller_id': CONTROLLER, 'expires_at': 10000}] if self.active else [],
                      'pending_pairings': [{'pairing_id': GRANT, 'controller_id': CONTROLLER, 'device_id': self.device,
                         'binding': binding, 'state': 'pending_confirmation', 'expires_at': self.now[0] + 200}] if self.pending else [],
                      'commands': copy.deepcopy(self.commands)}
            if self.hook: self.hook()
            return result
        if path.endswith('/receipt'):
            self.receipts.append(body); return {}
        if path == '/device/revoke': self.active = False; self.revision += 1; return {}
        if path == '/device/status': return {}
        raise AssertionError(path)


class ChannelTests(fixtures.RemoteTests):
    """Reuse the real lifecycle fixture; inherited domain cases run unchanged."""
    def setUp(self):
        super().setUp()
        self.app.cdb.binding = {'server': 'https://staging.cdbos.de', 'user_id': USER, 'client_id': AREA}
        self.app.store.root = Path(self.tmp.name)
        self.app.cdb.session = lambda binding=None: {'token': 'SYNTHETIC-ONLY'}
        self.select_areas_for_account()
        self.broker = Broker(self.app, self.now)
        self.channel = RemoteControlChannel(self.app, self.broker, lambda: self.now[0], start=False)
        self.addCleanup(self.channel.close)
    def select_areas_for_account(self):
        p = self.app.live.root / ('areas-' + self.app.live._selection_key(self.app.wake_account()) + '.json')
        p.write_text(json.dumps({'binding': self.app.wake_account(), 'area_ids': [AREA]}))
    def pair(self):
        self.channel.enqueue('pair', {}); self.channel.step()
        self.assertEqual(self.channel.public()['code'], 'ABCD2345')
        self.broker.pending = True; self.channel.step()
        self.channel.enqueue('confirm', {'pairing_id': GRANT, 'approved': True}); self.channel.step()
        self.assertTrue(self.channel.public()['paired'])
    def remote_command(self, action='start'):
        grant = self.channel.lookup(GRANT, CONTROLLER)
        snapshot = self.app.remote_control.status(grant)
        return {'command_id': str(uuid.uuid4()), 'grant_id': GRANT, 'controller_id': CONTROLLER,
                'action': action, 'process_epoch': snapshot['process_epoch'],
                'expected_generation': snapshot['generation'], 'expected_revision': snapshot['revision'],
                'expires_at': self.now[0] + 10, 'device_id': self.broker.device,
                'binding': self.channel.wire_binding(self.app.wake_account()),
                'grant': {'grant_id': GRANT, 'controller_id': CONTROLLER, 'expires_at': 10000}}

    def test_channel_real_lifecycle_start_mute_end_and_recording_guard(self):
        self.pair()
        self.broker.commands = [self.remote_command()]
        self.channel.step()
        self.wait(lambda: self.app.live.state == 'listening')
        self.assertEqual(self.app.live.owner_kind, 'device')
        mute = self.remote_command('set_muted'); mute['muted'] = True
        self.broker.commands = [mute]; self.channel.step()
        self.assertTrue(self.app.live.muted)
        self.broker.commands = [self.remote_command('end')]; self.channel.step()
        self.events_done.set()  # release injected synthetic event stream for cleanup
        self.wait(lambda: not self.app.live.busy())
        self.broker.commands = []; self.channel.step()
        self.assertEqual(self.broker.receipts[-1]['status'], 'applied')
        self.engine_state['recording'].update(id='synthetic-recording', paused=True)
        self.broker.commands = [self.remote_command()]; self.channel.step()
        self.assertEqual(self.broker.receipts[-1]['status'], 'rejected')
        self.assertEqual(self.broker.receipts[-1]['code'], 'device_busy')
        self.assertFalse(self.app.live.busy())

    def test_channel_idle_catalog_is_account_bound(self):
        self.pair()
        path = self.app.live.root / ('area-names-' + self.app.live._selection_key(self.app.wake_account()) + '.json')
        path.write_text(json.dumps({'binding': self.app.wake_account(), 'areas': [{'id': AREA, 'name': 'Synthetic knowledge'}]}))
        grant = self.channel.lookup(GRANT, CONTROLLER)
        self.assertEqual(self.app.remote_control.status(grant)['areas'][0]['name'], 'Synthetic knowledge')
        path.write_text(json.dumps({'binding': {}, 'areas': [{'id': AREA, 'name': 'Wrong account'}]}))
        self.assertEqual(self.app.remote_control.status(grant)['areas'][0]['name'], AREA)

    def test_channel_fresh_profile_is_opt_in(self):
        self.channel.step()
        self.assertEqual(self.broker.calls, [])
        self.assertFalse(self.channel.path.exists())
        self.assertIsNone(self.channel.lookup(GRANT, CONTROLLER))

    def test_channel_full_pairing_then_duplicate_start_uses_real_domain(self):
        self.pair(); command = self.remote_command()
        with patch.object(self.app, '_start_device_live_locked') as start:
            self.broker.commands = [command]; self.channel.step(); self.channel.step()
            self.assertEqual(start.call_count, 1)
        self.assertEqual(self.broker.receipts[-1]['status'], 'applied')
        self.assertEqual(self.broker.receipts[-1]['snapshot']['device_id'], self.broker.device)

    def test_channel_revoke_during_poll_never_dispatches(self):
        self.pair(); self.broker.commands = [self.remote_command()]
        self.broker.hook = lambda: self.channel.enqueue('revoke', {})
        with patch.object(self.app, '_start_device_live_locked') as start:
            self.channel.step()
            start.assert_not_called()
        self.assertIsNone(self.channel.lookup(GRANT, CONTROLLER))

    def test_channel_account_change_during_network_discards_all(self):
        self.pair(); self.broker.commands = [self.remote_command()]
        self.broker.hook = lambda: setattr(self.app.cdb, 'generation', 1)
        with patch.object(self.app, '_start_device_live_locked') as start:
            self.channel.step(); start.assert_not_called()
        self.assertFalse(self.channel.public()['paired'])
        self.assertFalse(self.channel.path.exists())

    def test_channel_forged_binding_or_grant_denied_before_dispatch(self):
        self.pair()
        for field, value in [('binding', {}), ('grant', {}), ('device_id', str(uuid.uuid4()))]:
            self.broker.commands = [dict(self.remote_command(), **{field: value})]
            with patch.object(self.app, '_start_device_live_locked') as start:
                self.channel.step(); start.assert_not_called()
            self.broker.commands = []; self.channel.step()

    def test_channel_failed_poll_invalidates_cached_grant(self):
        self.pair(); self.broker.failure = ChannelError('unavailable'); self.channel.step()
        self.assertIsNone(self.channel.lookup(GRANT, CONTROLLER))
        self.broker.failure = None; self.channel.step()
        self.assertIsNotNone(self.channel.lookup(GRANT, CONTROLLER))

    def test_channel_receipt_loss_never_repeats_effect(self):
        self.pair(); self.broker.commands = [self.remote_command()]
        request = self.broker.request
        lose = [True]
        def response(*args):
            if args[1].endswith('/receipt') and lose[0]:
                lose[0] = False; raise ChannelError('unavailable')
            return request(*args)
        self.broker.request = response
        with patch.object(self.app, '_start_device_live_locked') as start:
            self.channel.step(); self.channel.step()
            self.assertEqual(start.call_count, 1)
        self.assertEqual(self.broker.receipts[-1]['status'], 'applied')

    def test_channel_restart_preserves_credential_but_not_grants(self):
        self.pair(); credential = self.channel.connection['credential']
        self.assertEqual(os.stat(self.channel.path).st_mode & 0o777, 0o600)
        self.channel.close()
        other = RemoteControlChannel(self.app, self.broker, lambda: self.now[0], start=False)
        self.addCleanup(other.close)
        self.assertEqual(other.connection['credential'], credential)
        self.assertIsNone(other.lookup(GRANT, CONTROLLER))
        self.assertNotIn(credential, json.dumps(other.public()))
        other.step(); self.assertIsNotNone(other.lookup(GRANT, CONTROLLER))

    def test_channel_revoke_persists_across_failed_delivery_and_restart(self):
        self.pair(); self.channel.enqueue('revoke', {})
        self.broker.failure = ChannelError('unavailable'); self.channel.step()
        self.assertIsNone(self.channel.lookup(GRANT, CONTROLLER))
        self.channel.close(); self.broker.failure = None
        other = RemoteControlChannel(self.app, self.broker, lambda: self.now[0], start=False)
        self.addCleanup(other.close); other.step()
        self.assertFalse(other.path.exists()); self.assertFalse(self.broker.active)

    def test_channel_default_off_capability_never_registers(self):
        self.broker.enabled = False
        self.channel.enqueue('pair', {}); self.channel.step()
        self.assertEqual([call[1] for call in self.broker.calls], ['/capabilities'])
        self.assertEqual(self.channel.public()['state'], 'unsupported')

    def test_channel_unavailable_storage_does_not_break_local_app(self):
        with patch('services.remote_control_transport.RemoteControlChannel', side_effect=OSError('private')):
            disabled = create_channel(self.app)
        self.assertEqual(disabled.public()['error'], 'storage_unavailable')
        self.assertNotIn('private', json.dumps(disabled.public()))

    def test_channel_expired_or_reordered_snapshot_cannot_authorize(self):
        self.pair(); self.channel.grants_revision = 10
        self.broker.commands = [self.remote_command()]
        with patch.object(self.app, '_start_device_live_locked') as start:
            self.channel.step(); start.assert_not_called()
        self.assertIsNone(self.channel.lookup(GRANT, CONTROLLER))

    def test_channel_http_rejects_other_origins_without_network(self):
        with self.assertRaises(ChannelError): HTTPSControl().request('http://staging.cdbos.de', '/capabilities', 'fake')
        with self.assertRaises(ChannelError): HTTPSControl().request('https://evil.test', '/capabilities', 'fake')

# Inherit only setup/helpers: the domain suite has its own fixed identity fixture.
for _name in list(vars(fixtures.RemoteTests)):
    if _name.startswith('test_'):
        setattr(ChannelTests, _name, None)

if __name__ == '__main__': unittest.main()
