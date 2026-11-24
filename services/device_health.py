"""Read-only USB inventory. Never opens the display's serial port."""
from pathlib import Path


def lcd_usb_status(root=Path('/sys/bus/usb/devices')):
    if not root.is_dir():
        return {'state': 'unavailable', 'message': 'USB-Erkennung auf diesem System nicht verfügbar'}
    matches = 0
    try:
        for device in root.iterdir():
            try:
                values = [(device / key).read_text().strip() for key in
                          ('idVendor', 'idProduct', 'manufacturer', 'product')]
            except OSError:
                continue
            if values == ['303a', '4001', 'CDB', 'CDB Timer Display']:
                matches += 1
    except OSError:
        return {'state': 'unavailable', 'message': 'USB-Erkennung derzeit nicht verfügbar'}
    if matches == 1:
        return {'state': 'detected', 'message': 'USB-Display erkannt · Timeranzeige am Display prüfen'}
    if matches > 1:
        return {'state': 'ambiguous', 'message': 'Mehrere USB-Timerdisplays erkannt · nur eines anschließen'}
    return {'state': 'missing', 'message': 'Kein eingerichtetes USB-Timerdisplay erkannt'}
