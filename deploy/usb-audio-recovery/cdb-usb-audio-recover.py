#!/usr/bin/python3 -I
"""Narrow root helper for the recorder's dedicated VIA USB audio controller.

No app imports, caller-supplied paths, PCI removal, bus resets or global driver
operations. The app owns activity exclusion; this helper independently checks
the complete current hardware subtree before its one unbind/bind operation.
"""
import fcntl
import json
import os
from pathlib import Path
import re
import signal
import stat
import sys
import time

INSTALL_PATH = Path('/usr/local/sbin/cdb-usb-audio-recover')
LOCK_PATH = Path('/run/lock/cdb-usb-audio-recover.lock')
PCI_ID = ('0x1106', '0x3483', '0x0c0330')
AUDIO_ID = ('0020', '0b21')
HUB_ID = ('2109', '3431')
BDF = re.compile(r'[0-9a-f]{4}:[0-9a-f]{2}:[0-9a-f]{2}\.[0-7]')


class Refused(Exception):
    pass


def inside(path, parent):
    return path == parent or parent in path.parents


def read(path):
    try:
        return path.read_text(encoding='ascii').strip().lower()
    except (OSError, UnicodeError) as error:
        raise Refused('Die USB-Topologie konnte nicht vollständig geprüft werden.') from error


class Recovery:
    """Dependency injection is Python-only; the privileged CLI has no overrides."""
    def __init__(self, sysfs=Path('/sys'), *, write=None, sleep=time.sleep,
                 monotonic=time.monotonic, settle_seconds=10):
        self.sysfs = Path(sysfs).resolve()
        self.write = write or self._write
        self.sleep = sleep
        self.monotonic = monotonic
        self.settle_seconds = settle_seconds

    @staticmethod
    def _write(path, value):
        with path.open('w', encoding='ascii') as stream:
            stream.write(value)

    def result(self, *, supported=False, available=False, reason='',
               controller=None, device_present=False, action='check', recovered=False):
        return dict(supported=supported, available=available, reason=reason,
                    controller=controller, device_present=device_present,
                    action=action, recovered=recovered)

    def resolve(self, path):
        try:
            result = path.resolve(strict=True)
        except (OSError, RuntimeError) as error:
            raise Refused('Die USB-Topologie konnte nicht vollständig geprüft werden.') from error
        if not inside(result, self.sysfs):
            raise Refused('Unerwarteter Gerätepfad. Wiederherstellung gesperrt.')
        return result

    def pci_identity(self, path):
        return tuple(read(path / name) for name in ('vendor', 'device', 'class'))

    def candidates(self):
        base = self.sysfs / 'bus/pci/devices'
        if not base.is_dir():
            return []
        matches = []
        for entry in base.iterdir():
            if not BDF.fullmatch(entry.name):
                continue
            path = self.resolve(entry)
            if self.pci_identity(path) == PCI_ID:
                matches.append((entry.name, path))
        return matches

    def verify_subtree(self, controller):
        """Allow known hubs/audio only, also reject unmounted storage and NICs."""
        for entry in (self.sysfs / 'bus/pci/devices').iterdir():
            if BDF.fullmatch(entry.name):
                path = self.resolve(entry)
                if path != controller and inside(path, controller):
                    raise Refused('Weitere PCI-Geräte am Ziel. Wiederherstellung gesperrt.')
        for category in ('block', 'net'):
            base = self.sysfs / 'class' / category
            if not base.is_dir():
                raise Refused('Speicher- und Netzwerkgeräte konnten nicht geprüft werden.')
            for entry in base.iterdir():
                paths = [entry]
                if (entry / 'device').exists() or (entry / 'device').is_symlink():
                    paths.append(entry / 'device')
                if any(inside(self.resolve(path), controller) for path in paths):
                    raise Refused('Speicher- oder Netzwerkgerät am Ziel. Wiederherstellung gesperrt.')
        base = self.sysfs / 'bus/usb/devices'
        if not base.is_dir():
            raise Refused('USB-Geräte konnten nicht vollständig geprüft werden.')
        audio = False
        for entry in base.iterdir():
            path = self.resolve(entry)
            if not inside(path, controller):
                continue
            if ':' in entry.name:
                # Interfaces must belong to an explicitly allowed physical device.
                parent = path.parent
                identity = (read(parent / 'idVendor'), read(parent / 'idProduct'))
                kind = read(path / 'bInterfaceClass')
                root_hub = parent.parent == controller and re.fullmatch(r'usb\d+', parent.name)
                allowed = {'09'} if (root_hub and identity in {('1d6b', '0002'), ('1d6b', '0003')}) or identity == HUB_ID else {'01', '03'} if identity == AUDIO_ID else set()
                if kind not in allowed:
                    raise Refused('Fremde USB-Schnittstelle am Ziel. Wiederherstellung gesperrt.')
                continue
            identity = (read(path / 'idVendor'), read(path / 'idProduct'))
            kind = read(path / 'bDeviceClass')
            root_hub = path.parent == controller and re.fullmatch(r'usb\d+', entry.name)
            if root_hub and identity in {('1d6b', '0002'), ('1d6b', '0003')} and kind == '09':
                continue
            if identity == HUB_ID and kind == '09':
                continue
            if identity == AUDIO_ID and kind in {'00', '01'}:
                audio = True
                continue
            raise Refused('Fremdes USB-Gerät am Ziel. Wiederherstellung gesperrt.')
        return audio

    def check(self):
        try:
            candidates = self.candidates()
            if len(candidates) != 1:
                return self.result(reason='Kein eindeutiger unterstützter VIA-USB-Controller gefunden.')
            bdf, path = candidates[0]
            if self.resolve(path / 'driver') != self.resolve(self.sysfs / 'bus/pci/drivers/xhci_hcd'):
                raise Refused('Der Zielcontroller verwendet nicht den erwarteten USB-Treiber.')
            audio = self.verify_subtree(path)
            return self.result(supported=True, available=True, controller=bdf,
                               device_present=audio, reason='Soundbar erkannt.' if audio else 'USB-Audio kann sicher neu erkannt werden.')
        except (Refused, OSError) as error:
            return self.result(supported=bool(locals().get('candidates')),
                               controller=locals().get('bdf'), reason=str(error))

    def recover(self):
        state = self.check() | {'action': 'recover'}
        if not state['available']:
            return state
        bdf = state['controller']
        # Repeat every safety check immediately before the hardware operation.
        second = self.check()
        if not second['available'] or second['controller'] != bdf:
            return second | {'action': 'recover', 'available': False,
                             'reason': 'Gerätebelegung hat sich geändert. Bitte erneut prüfen.'}
        path = self.resolve(self.sysfs / 'bus/pci/devices' / bdf)
        driver = self.resolve(self.sysfs / 'bus/pci/drivers/xhci_hcd')
        unbind_attempted = False
        try:
            # Mark before writing: a timeout after the kernel write must still
            # enter the matching bind attempt in finally.
            unbind_attempted = True
            self.write(driver / 'unbind', bdf)
            self.sleep(.25)
        except (OSError, Refused) as error:
            state.update(available=False, reason='USB-Controller konnte nicht getrennt werden.')
        finally:
            if unbind_attempted:
                try:
                    # Do not interrupt the one cleanup bind with repeated TERM/
                    # INT. ALRM remains unblocked as the operation's time limit.
                    old_mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGTERM, signal.SIGINT})
                    try:
                        # Bind only the identical function; never rescan a bus.
                        if self.pci_identity(path) != PCI_ID:
                            raise Refused('Die Controllerkennung hat sich geändert.')
                        self.write(driver / 'bind', bdf)
                    finally:
                        signal.pthread_sigmask(signal.SIG_SETMASK, old_mask)
                except (OSError, Refused):
                    state.update(available=False, reason='USB-Controller konnte nicht wieder verbunden werden. Bitte Gerät neu starten.')
        if not state['available']:
            return state
        deadline = self.monotonic() + self.settle_seconds
        while True:
            current = self.check()
            if current['available'] and current['controller'] == bdf and current['device_present']:
                return current | {'action': 'recover', 'recovered': True,
                                  'reason': 'USB-Soundbar wieder erkannt. Audioausgang wird anschließend geprüft.'}
            if self.monotonic() >= deadline:
                return state | {'available': False, 'device_present': False,
                                'reason': 'USB neu verbunden, Soundbar aber noch nicht erkannt. Kabel und Stromversorgung prüfen.'}
            self.sleep(.25)


def verify_installation():
    if os.geteuid() != 0 or Path(__file__) != INSTALL_PATH:
        raise Refused('Die freigegebene USB-Audio-Einrichtung fehlt.')
    for path in (INSTALL_PATH, *INSTALL_PATH.parents):
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
            raise Refused('USB-Audio-Helfer ist nicht sicher installiert.')
    if not stat.S_ISREG(INSTALL_PATH.stat().st_mode):
        raise Refused('USB-Audio-Helfer ist nicht sicher installiert.')


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    recovery = Recovery()
    if len(args) != 1 or args[0] not in ('check', 'recover'):
        print(json.dumps(recovery.result(reason='Nur check oder recover ohne weitere Parameter erlaubt.')))
        return 2
    action = args[0]
    fd = None
    old_handlers = {}
    try:
        verify_installation()
        def timeout(signum, frame):
            raise Refused('Zeitlimit der USB-Wiederherstellung erreicht. Gerätebelegung prüfen.')
        for signum in (signal.SIGALRM, signal.SIGTERM, signal.SIGINT):
            old_handlers[signum] = signal.signal(signum, timeout)
        signal.alarm(35)
        fd = os.open(LOCK_PATH, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o077:
            raise Refused('USB-Audio-Sperre ist nicht sicher eingerichtet.')
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise Refused('USB-Audio wird bereits wiederhergestellt.') from error
        if action == 'recover':
            previous = os.read(fd, 128).decode('ascii').strip()
            if previous and 0 <= time.monotonic() - float(previous) < 30:
                raise Refused('Bitte 30 Sekunden vor einem weiteren Versuch warten.')
            preflight = recovery.check()
            if not preflight['available']:
                print(json.dumps(preflight | {'action': action}, ensure_ascii=False))
                return 2
            os.lseek(fd, 0, os.SEEK_SET)
            os.ftruncate(fd, 0)
            os.write(fd, str(time.monotonic()).encode('ascii'))
            result = recovery.recover()
        else:
            result = recovery.check()
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result['available'] else 2
    except (Refused, OSError, ValueError) as error:
        print(json.dumps(recovery.result(action=action, reason=str(error)), ensure_ascii=False))
        return 2
    finally:
        if old_handlers:
            signal.alarm(0)
            for signum, handler in old_handlers.items():
                signal.signal(signum, handler)
        if fd is not None:
            os.close(fd)


if __name__ == '__main__':
    raise SystemExit(main())
