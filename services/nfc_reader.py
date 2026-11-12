"""Isolated optional system-Python worker. Emits hashes, never raw card IDs."""
import hashlib
import json
import time


def sample():
    from smartcard.System import readers
    from smartcard.Exceptions import NoCardException
    devices = readers()
    if len(devices) != 1:
        return {'state':'error','message':'Bitte genau einen NFC-Leser anschließen.'}
    reader = devices[0]
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
        if len(current) == 1 and str(current[0]) == str(reader):
            return {'state':'absent'}
        return {'state':'error','message':'Leserverbindung unterbrochen. Am Bildschirm stoppen.'}
    finally:
        try: connection.disconnect()
        except Exception: pass


def main():
    while True:
        try: value = sample()
        except ImportError: value = {'state':'error','message':'NFC-Unterstützung ist auf diesem Pi noch nicht installiert.'}
        except Exception: value = {'state':'error','message':'NFC-Leser nicht verfügbar. Laufenden Modus am Bildschirm beenden.'}
        print(json.dumps(value),flush=True)
        time.sleep(.35)


if __name__ == '__main__': main()
