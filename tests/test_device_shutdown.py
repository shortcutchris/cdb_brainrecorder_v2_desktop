import tempfile,time,unittest,subprocess
from pathlib import Path
from unittest.mock import Mock,patch
from services.device_management import DeviceManagement
from services.device_power import execute_shutdown,power_status,shutdown_method,LOGIN_MANAGER
from fleet.common import read,save

class ShutdownTests(unittest.TestCase):
    def test_existing_desktop_uses_noninteractive_logind_without_sudo(self):
        run=Mock(return_value=Mock(returncode=0,stdout='s "yes"\n'))
        self.assertEqual(shutdown_method(run),'logind');run.assert_called_once()
        self.assertEqual(run.call_args.args[0],LOGIN_MANAGER+['CanPowerOff'])

    def test_factory_permission_fallback_and_denied_desktop(self):
        run=Mock(side_effect=[Mock(returncode=0,stdout='s "challenge"'),Mock(returncode=0)])
        self.assertEqual(shutdown_method(run),'sudo')
        self.assertEqual(run.call_args.args[0],['sudo','-n','-l','/usr/bin/systemctl','poweroff'])
        for answer in ['s "no"','s "challenge"']:
            with self.assertRaises(ValueError):shutdown_method(Mock(side_effect=[Mock(returncode=0,stdout=answer),Mock(returncode=1)]))
        for error in [OSError('missing'),subprocess.TimeoutExpired('check',5)]:
            with self.assertRaisesRegex(ValueError,'noch nicht freigegeben'):shutdown_method(Mock(side_effect=error))

    def test_shutdown_is_guarded_delayed_and_has_no_force_flag(self):
        with tempfile.TemporaryDirectory() as folder:
            m=DeviceManagement(folder);run=Mock(return_value=Mock(returncode=0))
            with patch.object(m,'boot_id',return_value='boot-a'),patch.object(m,'prepare') as guard,patch('services.device_power.shutdown_method',return_value='logind'):
                result=m.shutdown_device(Mock(preview=False),'test',run)
                guard.assert_called_once();self.assertTrue(result['scheduled']);self.assertTrue(m.busy())
                args=run.call_args.args[0];self.assertIn('--on-active=2',args);self.assertIn('services.device_power',args)
                self.assertNotIn('--force',args);self.assertNotIn('poweroff',args)
                self.assertEqual(power_status(m.root,'boot-a')['state'],'scheduled')
                self.assertEqual(power_status(m.root,'boot-b'),{})

    def test_preview_and_busy_never_schedule_shutdown(self):
        with tempfile.TemporaryDirectory() as folder:
            m=DeviceManagement(folder);run=Mock()
            with self.assertRaises(ValueError):m.shutdown_device(Mock(preview=True),'test',run)
            run.assert_not_called()
            with patch.object(m,'boot_id',return_value='boot'),patch.object(m,'prepare',side_effect=ValueError('busy')),patch('services.device_power.shutdown_method',return_value='logind'):
                with self.assertRaises(ValueError):m.shutdown_device(Mock(preview=False),'test',run)
            run.assert_not_called()

    def test_failed_scheduler_releases_lock_and_reports_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            m=DeviceManagement(folder)
            with patch.object(m,'boot_id',return_value='boot'),patch.object(m,'prepare'),patch('services.device_power.shutdown_method',return_value='logind'):
                with self.assertRaises(ValueError):m.shutdown_device(Mock(preview=False),'test',Mock(return_value=Mock(returncode=1)))
                self.assertFalse(m.busy());self.assertEqual(m.public()['power']['state'],'failed')

    def test_worker_requires_current_matching_lease(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);run=Mock(return_value=Mock(returncode=0))
            for changes in [{'command':'other'},{'boot':'old'},{'expires':0}]:
                save(root/'maintenance.json',{'command':'task','boot':'boot','expires':time.time()+60}|changes)
                self.assertFalse(execute_shutdown(root,'task','logind',run,boot='boot'))
            run.assert_not_called()

    def test_worker_success_is_requested_never_claimed_off(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);run=Mock(return_value=Mock(returncode=0))
            save(root/'maintenance.json',{'command':'task','boot':'boot','expires':time.time()+60})
            self.assertTrue(execute_shutdown(root,'task','logind',run,boot='boot'))
            self.assertEqual(run.call_args.args[0],LOGIN_MANAGER+['PowerOff','b','false'])
            self.assertEqual(power_status(root,'boot')['state'],'requested')
            self.assertTrue((root/'maintenance.json').exists())
            state=read(root/'power.json');state['expires']=0;save(root/'power.json',state)
            self.assertEqual(power_status(root,'boot')['state'],'failed')

    def test_worker_errors_unlock_device_and_do_not_leak_system_output(self):
        for error in [None,OSError('private'),subprocess.TimeoutExpired('cmd',15)]:
            with self.subTest(error=error),tempfile.TemporaryDirectory() as folder:
                root=Path(folder);run=Mock(return_value=Mock(returncode=1,stderr='private'),side_effect=error)
                save(root/'maintenance.json',{'command':'task','boot':'boot','expires':time.time()+60})
                self.assertFalse(execute_shutdown(root,'task','sudo',run,boot='boot'))
                self.assertFalse((root/'maintenance.json').exists())
                self.assertEqual(power_status(root,'boot')['state'],'failed')
                self.assertNotIn('private',(root/'power.json').read_text())
