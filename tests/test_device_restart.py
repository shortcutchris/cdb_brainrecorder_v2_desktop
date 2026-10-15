import tempfile
import time
import unittest
from unittest.mock import Mock,patch
from services.device_management import DeviceManagement
from fleet.common import save

class RestartTests(unittest.TestCase):
    def test_confirmation_guards_hardware_and_preserves_boot_lifetime(self):
        with tempfile.TemporaryDirectory() as folder:
            m=DeviceManagement(folder);app=Mock(preview=False);runner=Mock(return_value=Mock(returncode=0))
            with patch.object(m,'boot_id',return_value='boot-a'),patch.object(m,'prepare') as guard:
                self.assertTrue(m.restart_device(app,'test',runner)['scheduled']);guard.assert_called_once()
                self.assertTrue(m.busy());self.assertEqual(runner.call_args.args[0][-3:],['-n','/usr/bin/systemctl','reboot'])
            with patch.object(m,'boot_id',return_value='boot-b'):self.assertFalse(m.busy())
    def test_preview_busy_or_missing_permission_never_schedules_reboot(self):
        with tempfile.TemporaryDirectory() as folder:
            m=DeviceManagement(folder);runner=Mock(return_value=Mock(returncode=0))
            with self.assertRaises(ValueError):m.restart_device(Mock(preview=True),'test',runner)
            runner.assert_not_called()
            with patch.object(m,'boot_id',return_value='boot'),patch.object(m,'prepare',side_effect=ValueError('busy')):
                with self.assertRaises(ValueError):m.restart_device(Mock(preview=False),'test',runner)
                self.assertEqual(runner.call_count,1)
    def test_failed_scheduler_releases_maintenance(self):
        with tempfile.TemporaryDirectory() as folder:
            m=DeviceManagement(folder);runner=Mock(side_effect=[Mock(returncode=0),Mock(returncode=1)])
            with patch.object(m,'boot_id',return_value='boot'),patch.object(m,'prepare'):
                with self.assertRaises(ValueError):m.restart_device(Mock(preview=False),'test',runner)
                self.assertFalse(m.busy())
