from pathlib import Path
import tempfile
import unittest
from services.device_health import lcd_usb_status


class DeviceHealthTests(unittest.TestCase):
    def test_usb_identity_is_required_and_multiple_displays_are_ambiguous(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(lcd_usb_status(root)['state'], 'missing')
            for name in ('1-1', '1-2'):
                device = root / name
                device.mkdir()
                for key, value in {'idVendor': '303a', 'idProduct': '4001',
                                   'manufacturer': 'CDB', 'product': 'CDB Timer Display'}.items():
                    (device / key).write_text(value + '\n')
                expected = 'detected' if name == '1-1' else 'ambiguous'
                self.assertEqual(lcd_usb_status(root)['state'], expected)
            (root / '1-2' / 'product').write_text('Unrelated serial device')
            self.assertEqual(lcd_usb_status(root)['state'], 'detected')
            (root / '1-1' / 'idVendor').unlink()
            self.assertEqual(lcd_usb_status(root)['state'], 'missing')
            self.assertEqual(lcd_usb_status(root / 'unavailable')['state'], 'unavailable')

