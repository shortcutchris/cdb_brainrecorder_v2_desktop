"""Isolated optional system-Python worker. Emits hashes, never raw card IDs."""
import hashlib
import json
import re
import time


def select_reader(devices):
    """A dual-interface USB device can expose contact and contactless readers.

    Prefer a single explicitly labelled contactless interface. Never guess a
    slot number or the first entry of an ambiguous reader list.
    """
    if len(devices) == 1:
        return devices[0]
    contactless = [reader for reader in devices
                   if re.search(r'\bcontactless\b', str(reader), re.IGNORECASE)]
    return contactless[0] if len(contactless) == 1 else None


def sample(selection=None):
    from smartcard.System import readers
    from smartcard.Exceptions import NoCardException
    devices = readers()
    reader = select_reader(devices)
    if reader is None:
        return {'state':'error','message':'Kein NFC-Leser erkannt. USB-Verbindung prüfen.' if not devices else 'Mehrere mögliche NFC-Leser erkannt. Bitte nur einen anschließen.'}
    if selection is not None:
        if selection.get('name') and selection['name'] != str(reader):
            return {'state':'error','message':'Kontaktloser Leser nicht mehr verfügbar. Am Bildschirm stoppen.'}
        selection['name'] = str(reader)
    connection = reader.createConnection()
    try:
        connection.connect()
        data, sw1, sw2 = connection.transmit([0xff,0xca,0,0,0])
        if (sw1,sw2) != (0x90,0) or not 4 <= len(data) <= 16:
            return {'state':'error','message':'Dieser Tag oder Leser unterstützt die Kennungsabfrage nicht.'}
        return {'state':'present','tag':hashlib.sha256(bytes(data)).hexdigest()}
    except NoCardException:
        # Re-enumerate: a USB disconnection is not evidence of an empty field.
        current = readers()
        selected = select_reader(current)
        if selected is not None and str(selected) == str(reader):
            return {'state':'absent'}
        return {'state':'error','message':'Leserverbindung unterbrochen. Am Bildschirm stoppen.'}
    finally:
        try: connection.disconnect()
        except Exception: pass


def main():
    selection = {}
    while True:
        try: value = sample(selection)
        except ImportError: value = {'state':'error','message':'NFC-Unterstützung ist auf diesem Pi noch nicht installiert.'}
        except Exception: value = {'state':'error','message':'NFC-Leser nicht verfügbar. Laufenden Modus am Bildschirm beenden.'}
        print(json.dumps(value),flush=True)
        time.sleep(.35)


if __name__ == '__main__': main()
