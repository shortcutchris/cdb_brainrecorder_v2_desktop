import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from services import update_session as handoff
from services.app_activity import AppActivity
from services.device_management import DeviceManagement
from services.room_mode import RoomMode


class UpdateSessionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.management = DeviceManagement(self.root)
        self.command = '11111111-1111-1111-1111-111111111111'
        self.now = 100.0
        self.clock = lambda: self.now
        self.boot = patch.object(handoff, 'boot_id', return_value='boot-one').start()
        self.addCleanup(patch.stopall)
        self.account = {'server': 'https://example.test', 'user_id': 'alice', 'client_id': 'tenant-one'}
        self.cdb = Mock()
        self.cdb.stored_session.return_value = {
            'server': self.account['server'], 'identity': self.account,
            'token': 'synthetic-secret-never-in-handoff'}
        self.cdb.logout.side_effect = lambda: setattr(self.cdb.stored_session, 'side_effect', ValueError('signed out'))
        self.epoch = 'a' * 32
        self.ticket = self.root/'management/update-session.json'

    def issue(self, remaining=180):
        self.management.marker.write_text(json.dumps({'command': self.command, 'expires': time.time()+600}))
        return handoff.issue(self.root, self.command, self.account, self.epoch, remaining, clock=self.clock)

    def test_update_retains_account_epoch_and_original_idle_deadline_once(self):
        self.assertTrue(self.issue())
        self.assertEqual(self.ticket.stat().st_mode & 0o777, 0o600)
        self.assertNotIn('synthetic-secret', self.ticket.read_text())
        self.now += 12
        room = RoomMode(self.root, self.cdb, self.clock)
        self.assertEqual(room.account(), self.account)
        self.assertEqual(room.epoch, self.epoch)
        self.assertEqual(room.idle_remaining(), 168)
        self.assertIsNone(room.intent)
        self.assertEqual(room.operator_until, 0)
        self.assertFalse(room.login_owned)
        self.assertEqual(room.observed_account, self.account)
        self.cdb.logout.assert_not_called()
        self.assertFalse(self.ticket.exists())
        RoomMode(self.root, self.cdb, self.clock)
        self.cdb.logout.assert_called_once()

    def test_reboot_stale_unbound_and_corrupt_handoffs_fail_closed(self):
        cases = ('boot', 'expired', 'idle_expired', 'account', 'tenant', 'server',
                 'command', 'marker_absent', 'marker_expired', 'corrupt', 'future', 'nan')
        for case in cases:
            with self.subTest(case=case):
                self.boot.return_value = 'boot-one'; self.now = 100
                self.cdb.stored_session.side_effect = None; self.cdb.logout.reset_mock()
                self.issue(20 if case == 'idle_expired' else 180)
                data = json.loads(self.ticket.read_text())
                if case == 'boot': self.boot.return_value = 'boot-two'
                if case == 'expired': self.now += 121
                if case == 'idle_expired': self.now += 21
                if case in ('account', 'tenant', 'server'):
                    data['account'][{'account':'user_id', 'tenant':'client_id', 'server':'server'}[case]] = 'other'
                if case == 'command': data['command'] = 'different'
                if case == 'marker_absent': self.management.marker.unlink()
                if case == 'marker_expired': self.management.marker.write_text(json.dumps({'command':self.command,'expires':0}))
                if case == 'future': data['issued'] += 1
                if case == 'nan': data['expires'] = float('nan')
                self.ticket.write_text('invalid' if case == 'corrupt' else json.dumps(data))
                RoomMode(self.root, self.cdb, self.clock)
                self.cdb.logout.assert_called_once()
                self.assertFalse(self.ticket.exists())

    def test_clean_install_and_ordinary_restart_do_not_restore_login(self):
        RoomMode(self.root, self.cdb, self.clock)
        self.cdb.logout.assert_called_once()
        self.assertFalse(self.ticket.exists())

    def test_maintenance_does_not_extend_original_idle_deadline(self):
        self.issue(); room = RoomMode(self.root, self.cdb, self.clock)
        self.now += 30
        room.observe_activity(AppActivity(maintenance=True))
        self.assertFalse(room.idle_suspended)
        self.assertEqual(room.idle_remaining(), 150)
        self.now += 151
        room.observe_activity(AppActivity(maintenance=True))
        self.assertEqual(room.idle_remaining(), 0)

    def test_logout_and_aborted_update_invalidate_handoff(self):
        self.issue(); room = RoomMode(self.root, self.cdb, self.clock)
        self.issue(); room.reset(); self.assertFalse(self.ticket.exists())
        self.issue(); self.management.release(self.command)
        self.assertFalse(self.ticket.exists())

    def test_new_policy_can_shorten_but_not_extend_remaining_idle_time(self):
        self.issue(900)
        self.assertEqual(handoff.consume(self.root, self.account, 2, clock=self.clock)['remaining'], 120)

    def app(self):
        app = Mock()
        app.activity.return_value = AppActivity()
        app.schedules.items.return_value = []
        app.playback_leases = {}
        app.cdb.db.return_value.__enter__ = Mock(return_value=Mock())
        app.cdb.db.return_value.__exit__ = Mock(return_value=False)
        app.cdb.db.return_value.__enter__.return_value.execute.return_value.fetchone.return_value = None
        app.cdb.login = {'state': 'completed'}
        app.room.intent = None; app.room.epoch = self.epoch
        app.room.account.return_value = self.account
        app.room.idle_remaining.return_value = 180
        return app

    def test_guarded_prepare_issues_ticket_and_default_power_path_does_not(self):
        app = self.app()
        self.management.prepare(app, self.command, 'test', preserve_login=True)
        self.assertTrue(self.ticket.exists())
        self.management.release(self.command)
        self.management.prepare(app, self.command, 'test')
        self.assertFalse(self.ticket.exists())

    def test_active_login_and_start_intent_block_update(self):
        app = self.app()
        for state, intent in [('pending', None), ('completed', {'mode':'meeting'})]:
            app.cdb.login = {'state':state}; app.room.intent = intent
            with self.assertRaises(ValueError):
                self.management.prepare(app, self.command, 'test', preserve_login=True)
            self.assertFalse(self.management.busy())
            self.assertFalse(self.ticket.exists())

    def test_failed_ticket_write_releases_maintenance(self):
        with patch.object(handoff, 'issue', side_effect=OSError('disk full')):
            with self.assertRaises(ValueError):
                self.management.prepare(self.app(), self.command, 'test', preserve_login=True)
        self.assertFalse(self.management.busy())


if __name__ == '__main__': unittest.main()
