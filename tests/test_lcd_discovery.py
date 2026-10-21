import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
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

    def test_clean_and_repeat_service_configuration(self):
        root=Path('/opt/cdb recorder');runtime=Path('/home/cdb/.local/share/cdb-lcd/runtime')
        fresh=installer.unit(root,runtime)
        self.assertEqual(fresh,installer.unit(root,runtime))
        self.assertIn('WantedBy=default.target',fresh)
        self.assertIn('services.lcd_bridge',fresh);self.assertNotIn('--port',fresh)
        self.assertNotIn('cdb-recorder-studio.service',fresh)
        changed=installer.unit(root,runtime,8090,Path('/home/cdb/token'))
        self.assertIn('"8090"',changed);self.assertIn('"--token-file"',changed)
        self.assertNotIn('8088',changed)
        self.assertEqual(installer.quote('/home/a%/test'), '"/home/a%%/test"')
        with self.assertRaises(ValueError):installer.quote('x\nExecStart=bad')
        with self.assertRaises(ValueError):installer.unit(root,runtime,0)

if __name__=='__main__':unittest.main()
