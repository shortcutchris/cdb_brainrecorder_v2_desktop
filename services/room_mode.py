"""Opt-in shared device policy. Ownership is durable; room consent is not.

No personal content is migrated or assigned by enabling this mode. Callers
serialize transitions with StudioApp.control_lock. Files are additive sidecars.
"""
import hashlib
import hmac
import json
import secrets
import time
from pathlib import Path
from meeting_recorder.core import atomic_write


class RoomMode:
    def __init__(self, root, cdb, clock=time.monotonic):
        self.path = Path(root) / 'room-mode.json'
        self.cdb, self.clock = cdb, clock
        try:
            self.config = json.loads(self.path.read_text())
            if not isinstance(self.config, dict): raise ValueError()
        except FileNotFoundError:
            self.config = {'enabled': False, 'idle_minutes': 5}
        except (OSError, ValueError):
            # A damaged policy must not expose the personal device library.
            self.config = {'enabled': True, 'idle_minutes': 5}
        self.intent = None
        self.login_owned = False
        self.last_touch = clock()
        self.operator_until = 0
        self.failed_pin = 0
        self.pin_after = 0
        self.epoch = secrets.token_hex(16)
        self.observed_account = None
        if self.enabled:
            cdb.logout()  # A reboot never silently signs the next room user in.

    @property
    def enabled(self):
        return self.config.get('enabled') is True

    def account(self):
        try:
            session = self.cdb.stored_session(self.cdb.config())
        except ValueError:
            return None
        return {'server': session['server'], **{k: session['identity'][k] for k in ('user_id', 'client_id')}}

    def require_account(self):
        if not self.account(): raise ValueError('Bitte zuerst mit Brain anmelden. Gastaufnahmen sind im Raummodus ausgeschaltet.')

    def operator(self):
        return not self.enabled or self.clock() < self.operator_until

    def require_operator(self):
        if not self.operator(): raise ValueError('Geräteeinstellungen sind gesperrt. Zuerst Betreiber-PIN eingeben.')

    def unlock(self, pin):
        if self.clock() < self.pin_after: raise ValueError('PIN bitte in einer Minute erneut versuchen.')
        stored = self.config.get('pin', {})
        valid = False
        if isinstance(pin, str) and 6 <= len(pin) <= 12 and pin.isdigit() and stored:
            digest = hashlib.scrypt(pin.encode(), salt=bytes.fromhex(stored['salt']), n=16384, r=8, p=1).hex()
            valid = hmac.compare_digest(digest, stored['hash'])
        if not valid:
            self.failed_pin += 1
            if self.failed_pin >= 5: self.pin_after = self.clock() + 60; self.failed_pin = 0
            raise ValueError('Betreiber-PIN stimmt nicht.')
        self.failed_pin = 0
        self.operator_until = self.clock() + 300

    def configure(self, body):
        self.require_operator()
        enabled, minutes = body.get('enabled'), body.get('idle_minutes', 5)
        if type(enabled) is not bool or type(minutes) is not int or not 2 <= minutes <= 60:
            raise ValueError('Modus und Abmeldefrist von 2 bis 60 Minuten wählen.')
        config = self.config | {'enabled': enabled, 'idle_minutes': minutes}
        pin = body.get('pin', '')
        if pin:
            if not isinstance(pin, str) or not pin.isdigit() or not 6 <= len(pin) <= 12:
                raise ValueError('Betreiber-PIN mit 6 bis 12 Ziffern eingeben.')
            salt = secrets.token_bytes(16)
            config['pin'] = {'salt': salt.hex(), 'hash': hashlib.scrypt(pin.encode(), salt=salt, n=16384, r=8, p=1).hex()}
        if enabled and not config.get('pin'): raise ValueError('Beim ersten Einschalten eine Betreiber-PIN festlegen.')
        atomic_write(self.path, json.dumps(config)); self.path.chmod(0o600)
        self.config = config

    def touch(self):
        self.last_touch = self.clock()

    def cancel(self):
        if self.login_owned: self.cdb.invalidate_pending_login()
        self.login_owned = False
        self.intent = None

    def reset(self):
        self.cancel()
        self.operator_until = 0
        self.epoch = secrets.token_hex(16)
        self.observed_account = self.account()
        self.touch()

    def begin(self, mode, tag=None):
        if mode not in ('talk', 'meeting'): raise ValueError('Talk oder Meeting wählen.')
        self.cancel(); self.touch()
        self.intent = {'id': secrets.token_urlsafe(20), 'mode': mode, 'tag': tag,
                       'account': self.account(), 'deadline': self.clock() + 300}
        return self.public()

    def check_intent(self, ident, nfc):
        self.reconcile(nfc)
        if not self.intent or not hmac.compare_digest(str(ident), self.intent['id']):
            raise ValueError('Startwunsch abgelaufen. Bitte Talk oder Meeting erneut wählen.')
        self.require_account()
        if self.intent['account'] != self.account(): raise ValueError('Konto hat sich geändert. Bitte erneut wählen.')
        return dict(self.intent)

    def reconcile(self, nfc):
        account = self.account()
        if account != self.observed_account:
            if self.observed_account is not None:
                self.reset()
            self.observed_account = account
            self.touch()
        intent = self.intent
        if not intent: return
        valid_tag = True
        if intent['tag']:
            sample = nfc.reader.snapshot()
            valid_tag = nfc.enabled and sample.get('state') == 'present' and sample.get('tag') == intent['tag']
        if (self.clock() >= intent['deadline'] or not valid_tag or
                (intent['account'] is not None and intent['account'] != account)):
            self.cancel()
        elif account and intent['account'] is None:
            intent['account'] = account
            self.touch()

    def idle_remaining(self):
        return max(0, int(self.config.get('idle_minutes', 5) * 60 - (self.clock() - self.last_touch)))

    def public(self):
        intent = None
        if self.intent:
            intent = {k: self.intent[k] for k in ('id', 'mode')}
            intent['source'] = 'nfc' if self.intent['tag'] else 'touch'
        return {'enabled': self.enabled, 'signed_in': bool(self.account()), 'intent': intent,
                'epoch': self.epoch, 'idle_minutes': self.config.get('idle_minutes', 5),
                'idle_remaining': self.idle_remaining(), 'operator': self.operator(),
                'has_pin': bool(self.config.get('pin'))}

    def owner(self, folder):
        path = folder / 'room-owner.json'
        try:
            data = json.loads(path.read_text())
            return data['binding'] if isinstance(data['binding'], dict) else {'invalid': True}
        except FileNotFoundError:
            return None
        except (OSError, ValueError, KeyError, TypeError):
            return {'invalid': True}

    def can_read(self, folder=None):
        owner = self.owner(folder) if folder else None
        if owner is not None: return owner == self.account()
        return not self.enabled

    @staticmethod
    def bind(folder, binding):
        atomic_write(folder / 'room-owner.json', json.dumps({'binding': binding}))
        (folder / 'room-owner.json').chmod(0o600)
