"""Optional XVF3800 status ring. USB I/O never runs on an audio/API thread.

Protocol: Seeed xvf_host.py at 4b49bfd19977c63cf6e90dfe9e5827e74e20bf6d.
Only LED registers are written; hardware mute and flash are never changed.
"""
import json
import re
import struct
import threading
import time
from pathlib import Path
from meeting_recorder.core import atomic_write


class UsbRing:
    def __init__(self, device):
        self.device = device
        self.serial = device.serial_number or f'{device.bus}:{device.address}'

    def read(self, command, count, fmt='B'):
        size = struct.calcsize('<' + fmt * count)
        for _ in range(4):
            raw = bytes(self.device.ctrl_transfer(0xC0, 0, command | 0x80, 20, size + 1, timeout=250))
            if len(raw) == size + 1 and raw[0] == 0:
                return struct.unpack('<' + fmt * count, raw[1:])
            if raw and raw[0] == 64:
                time.sleep(.01)
                continue
            raise OSError('Ungültige ReSpeaker-Antwort.')
        raise OSError('ReSpeaker-Steuerung antwortet nicht.')

    def write(self, command, value, fmt='B'):
        data = struct.pack('<' + fmt, value)
        self.device.ctrl_transfer(0x40, 0, command, 20, data, timeout=250)

    def snapshot(self):
        return {'effect': self.read(12, 1)[0], 'color': self.read(16, 1, 'I')[0]}

    def restore(self, values):
        self.write(16, values['color'], 'I')
        self.write(12, values['effect'])

    def hardware_muted(self):
        return bool(self.read(0, 5)[1])  # X0D30 high = hardware mute

    def show(self, effect, color):
        self.write(16, color, 'I')
        self.write(12, effect)

    def close(self):
        import usb.util
        usb.util.dispose_resources(self.device)


def selected_usb(device, sound_root=Path('/sys/class/sound')):
    """Match the selected ALSA card to the USB device, never the first USB array."""
    match = re.search(r'(?:^|:)CARD=([^,]+)', device)
    if not match:
        return None
    for card in sound_root.glob('card[0-9]*'):
        if (card/'id').read_text().strip() != match[1] and card.name != 'card' + match[1]:
            continue
        for parent in (card/'device').resolve().parents:
            if not (parent/'idVendor').exists():
                continue
            if (parent/'idVendor').read_text().strip() != '2886' or (parent/'idProduct').read_text().strip() != '001a':
                return None
            return int((parent/'busnum').read_text()), int((parent/'devnum').read_text())
    return None


def connect(device):
    address = selected_usb(device)
    if address is None:
        return None
    import usb.core
    found = usb.core.find(idVendor=0x2886, idProduct=0x001A, bus=address[0], address=address[1])
    return UsbRing(found) if found is not None else None


class ReSpeakerLeds:
    def __init__(self, root, source, factory=connect, enabled=True, start=True):
        self.path = Path(root)/'respeaker-led-restore.json'
        self.source, self.factory = source, factory
        self.stopping = threading.Event()
        self.lock = threading.Lock()
        self.ring = None
        self.original = None
        self.applied = None
        self.selected = None
        self.changed = False
        self.retry = 0
        self.status = {'connected': False, 'state': 'unavailable', 'hardware_muted': False, 'message': ''}
        self.thread = None
        if enabled and start:
            self.thread = threading.Thread(target=self.run, name='respeaker-leds', daemon=True)
            self.thread.start()

    def public(self):
        with self.lock:
            return dict(self.status)

    def publish(self, **fields):
        with self.lock:
            self.status.update(fields)

    def release(self):
        if self.ring:
            try:
                if self.changed and self.ring.hardware_muted():
                    return  # Keep the restore journal; firmware owns hardware mute.
                if self.changed:
                    self.ring.restore(self.original)
                self.changed = False
                self.path.unlink(missing_ok=True)
            finally:
                self.ring.close()
                self.ring = None
                self.applied = None

    def tick(self, now=None):
        now = time.monotonic() if now is None else now
        if now < self.retry:
            return
        try:
            state = self.source()
            selected = state['device']
            if selected != self.selected:
                self.release()
                self.selected = selected
            if self.ring is None:
                self.ring = self.factory(selected)
                if self.ring is None:
                    self.publish(connected=False, state='unavailable', hardware_muted=False, message='')
                    self.retry = now + 2
                    return
                current = self.ring.snapshot()
                saved = json.loads(self.path.read_text()) if self.path.exists() else {}
                self.original = saved.get('values', current) if saved.get('serial') == self.ring.serial else current
                # Preserve the pre-app mode across a process crash. No flash writes.
                atomic_write(self.path, json.dumps({'serial': self.ring.serial, 'values': self.original}))
                self.changed = True
            muted = self.ring.hardware_muted()
            recording = state.get('recording', {})
            active = bool(recording.get('id')) or state.get('probe', False)
            if muted:
                mode = 'hardware-muted'
                self.applied = None  # Firmware owns its red hardware-mute indication.
            else:
                if not active:
                    mode, target = 'idle', (self.original['effect'], self.original['color'])
                elif recording.get('muted'):
                    mode, target = 'muted', (3 if int(now * 2) % 2 == 0 else 0, 0xCC2424)
                elif recording.get('paused'):
                    mode, target = 'paused', (3, 0xE0A000)
                else:
                    mode, target = 'recording', (3, 0x2266FF)
                if target != self.applied:
                    self.ring.show(*target)
                    self.applied = target
            self.publish(connected=True, state=mode, hardware_muted=muted, message='')
        except Exception:
            # Missing hardware, PyUSB, permissions or a disconnect must never stop audio.
            if self.ring:
                try:self.ring.close()
                except Exception:pass
            self.ring = None
            self.applied = None
            self.retry = now + 2
            self.publish(connected=False, state='error', hardware_muted=False,
                         message='ReSpeaker-LEDs nicht erreichbar. USB-Verbindung und Gerätezugriff prüfen.')

    def run(self):
        try:
            while not self.stopping.is_set():
                self.tick()
                self.stopping.wait(.15)
        finally:
            try:self.release()
            except Exception:pass  # Saved original values allow recovery next startup.

    def close(self):
        self.stopping.set()
        if self.thread:self.thread.join(timeout=5)
        else:self.release()
