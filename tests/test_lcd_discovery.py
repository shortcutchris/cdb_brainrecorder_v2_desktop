import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
import tempfile
from unittest.mock import Mock, patch
from services.lcd_bridge import discover, run

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('lcd_install', ROOT/'scripts/lcd-display/install.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


def port(device='/dev/ttyACM0', **changes):
    return SimpleNamespace(**({'device':device,'vid':0x303a,'pid':0x4001,
        'manufacturer':'CDB','product':'CDB Timer Display','serial_number':'012345ABCDEF'} | changes))


class DiscoveryTests(unittest.TestCase):
    def test_exact_identity_and_ambiguity(self):
        self.assertIsNone(discover([]))
        for field, value in [('vid',0x2886),('pid',0x1001),('manufacturer','Espressif'),
                             ('product','USB microphone'),('serial_number',None),('serial_number','unknown')]:
            self.assertIsNone(discover([port(**{field:value})]))
        self.assertEqual(discover([port(),port('/dev/ttyACM1',product='Other ESP board')]),'/dev/ttyACM0')
        self.assertIsNone(discover([port(),port('/dev/ttyACM1')]))
        self.assertEqual(discover([port('/dev/ttyACM7')]),'/dev/ttyACM7')

    def test_auto_loop_never_opens_unrelated_ports(self):
        # A synthetic serial module keeps this test independent of pyserial/runtime.
        serial = Mock();serial.SerialException=OSError
        lists = Mock();lists.comports.return_value=[port(product='ReSpeaker')]
        with patch.dict('sys.modules',{'serial':serial,'serial.tools':SimpleNamespace(list_ports=lists)}), \
             patch('services.lcd_bridge.time.sleep', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):run(None,'Pi',8088,'')
        serial.Serial.assert_not_called()

    def test_disconnect_rediscovers_changed_port(self):
        serial=Mock();serial.SerialException=OSError
        first=Mock();first.__enter__=Mock(side_effect=OSError('unplugged'));first.__exit__=Mock()
        second=Mock();second.__enter__=Mock(side_effect=KeyboardInterrupt);second.__exit__=Mock()
        serial.Serial.side_effect=[first,second]
        lists=Mock();lists.comports.side_effect=[[port()],[port('/dev/ttyACM7')]]
        with patch.dict('sys.modules',{'serial':serial,'serial.tools':SimpleNamespace(list_ports=lists)}), \
             patch('services.lcd_bridge.time.sleep'):
            with self.assertRaises(KeyboardInterrupt):run(None,'Pi',8088,'')
        self.assertEqual(first.port,'/dev/ttyACM0');self.assertEqual(second.port,'/dev/ttyACM7')
        self.assertFalse(first.dtr);self.assertFalse(first.rts);self.assertTrue(first.exclusive)

    def test_install_then_upgrade_only_changes_companion(self):
        with tempfile.TemporaryDirectory() as temp:
            home=Path(temp)
            recorder=home/'recorder-settings.json';recorder.write_text('keep existing settings')
            with patch.object(installer.Path, 'home', return_value=home), \
                 patch.object(installer.sys, 'platform', 'linux'), \
                 patch.object(installer.os, 'getuid', return_value=1000), \
                 patch.object(installer.os, 'getgroups', return_value=[20]), \
                 patch.object(installer.grp, 'getgrnam', return_value=SimpleNamespace(gr_gid=20)), \
                 patch.object(installer.os, 'umask'), \
                 patch.object(installer.subprocess, 'run') as execute:
                with patch.object(installer.sys, 'argv', ['install.py', '--no-start']):installer.main()
                destination=home/'.config/systemd/user/cdb-lcd-display.service'
                self.assertTrue(destination.is_file())
                first=destination.read_text()
                self.assertFalse(any('restart' in call.args[0] for call in execute.call_args_list))
                execute.reset_mock()
                with patch.object(installer.sys, 'argv', ['install.py']):installer.main()
                self.assertEqual(first,destination.read_text())
                self.assertEqual(recorder.read_text(),'keep existing settings')
                calls=[call.args[0] for call in execute.call_args_list]
                self.assertIn(['systemctl','--user','restart','cdb-lcd-display.service'],calls)
                self.assertTrue(any(call[:3]==['systemd-analyze','--user','verify'] for call in calls))
                self.assertFalse(any('cdb-recorder-studio.service' in call for call in calls))
                release=home/'release';(release/'services').mkdir(parents=True)
                (release/'services/lcd_bridge.py').touch();(release/'web_server.py').touch()
                current=home/'current';current.symlink_to(release,target_is_directory=True)
                with patch.object(installer.sys,'argv',['install.py','--app-root',str(current),'--no-start']):installer.main()
                self.assertIn(str(current),destination.read_text())
                self.assertNotIn(str(release),destination.read_text())

    def test_clean_and_repeat_service_configuration(self):
        root=Path('/opt/cdb recorder');runtime=Path('/home/cdb/.local/share/cdb-lcd/runtime')
        fresh=installer.unit(root,runtime)
        self.assertEqual(fresh,installer.unit(root,runtime))
        self.assertIn('WantedBy=default.target',fresh)
        self.assertIn('WorkingDirectory=/opt/cdb recorder\n',fresh)
        self.assertNotIn('WorkingDirectory="',fresh)
        self.assertIn('services.lcd_bridge',fresh);self.assertNotIn('--port',fresh)
        self.assertNotIn('cdb-recorder-studio.service',fresh)
        changed=installer.unit(root,runtime,8090,Path('/home/cdb/token'))
        self.assertIn('"8090"',changed);self.assertIn('"--token-file"',changed)
        self.assertNotIn('8088',changed)
        self.assertEqual(installer.quote('/home/a%/test'), '"/home/a%%/test"')
        with self.assertRaises(ValueError):installer.quote('x\nExecStart=bad')
        with self.assertRaises(ValueError):installer.unit(root,runtime,0)

if __name__=='__main__':unittest.main()
