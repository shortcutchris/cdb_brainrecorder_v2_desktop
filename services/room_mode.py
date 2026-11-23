"""Default account-bound device policy. Ownership is durable; start consent is not.

No legacy personal content is migrated or assigned by this policy. Callers
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
            self.config = {'idle_minutes': 15}
        except (OSError, ValueError):
            # A damaged policy must not expose the personal device library.
            self.config = {'idle_minutes': 15, 'setup_locked': True}
        # v2 is the product standard. An old opt-out cannot bypass account checks.
        # Keep an explicitly configured timeout; unused personal devices get 15 min.
        if self.config.get('enabled') is False:
            self.config['idle_minutes'] = 15
        minutes = self.config.get('idle_minutes', 15)
        if type(minutes) is not int or not 2 <= minutes <= 60:
            self.config['idle_minutes'] = 15
        self.config.update(enabled=True, policy_version=2)
        if not self.config.get('setup_locked'):
            atomic_write(self.path, json.dumps(self.config)); self.path.chmod(0o600)
        self.idle_suspended = False
        self.idle_reason = ''
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
        return True

    def account(self):
        try:
            session = self.cdb.stored_session(self.cdb.config())
        except ValueError:
            return None
        return {'server': session['server'], **{k: session['identity'][k] for k in ('user_id', 'client_id')}}

    def require_account(self):
        if not self.account(): raise ValueError('Bitte zuerst mit Brain anmelden. Aufnahmen ohne Anmeldung sind ausgeschaltet.')

    def operator(self):
        return (not self.config.get('pin') and not self.config.get('setup_locked')) or self.clock() < self.operator_until

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
        if 'enabled' in body and body['enabled'] is not True:
            raise ValueError('Anmeldung und Kontotrennung sind immer aktiv.')
        minutes = body.get('idle_minutes', self.config.get('idle_minutes', 15))
        if type(minutes) is not int or not 2 <= minutes <= 60:
            raise ValueError('Abmeldefrist von 2 bis 60 Minuten wählen.')
        ambient = body.get('ambient_activity', self.config.get('ambient_activity', False))
        if type(ambient) is not bool: raise ValueError('Geräuscherkennung ein- oder ausschalten.')
        config = self.config | {'enabled': True, 'idle_minutes': minutes, 'ambient_activity': ambient}
        pin = body.get('pin', '')
        if pin:
            if not isinstance(pin, str) or not pin.isdigit() or not 6 <= len(pin) <= 12:
                raise ValueError('Betreiber-PIN mit 6 bis 12 Ziffern eingeben.')
            salt = secrets.token_bytes(16)
            config['pin'] = {'salt': salt.hex(), 'hash': hashlib.scrypt(pin.encode(), salt=salt, n=16384, r=8, p=1).hex()}
        if not config.get('pin'): raise ValueError('Einmalig eine Betreiber-PIN für die Geräteeinstellungen festlegen.')
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
        self.idle_suspended = False
        self.idle_reason = ''
        self.touch()

    def begin(self, mode, tag=None):
        if mode not in ('talk', 'meeting'): raise ValueError('Talk oder Meeting wählen.')
        self.cancel(); self.touch()
        self.intent = {'id': secrets.token_urlsafe(20), 'mode': mode, 'tag': tag,
                       'account': self.account(), 'deadline': self.clock() + 300,
                       'tag_present': False}
        return self.public()

    def check_intent(self, ident, nfc):
        self.reconcile(nfc)
        if not self.intent or not hmac.compare_digest(str(ident), self.intent['id']):
            raise ValueError('Startwunsch abgelaufen. Bitte Talk oder Meeting erneut wählen.')
        self.require_account()
        if self.intent['account'] != self.account(): raise ValueError('Konto hat sich geändert. Bitte erneut wählen.')
        if self.intent['tag'] and not self.intent['tag_present']:
            raise ValueError('Zum Start bitte denselben Aufsteller wieder auflegen und die Erkennung abwarten.')
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
        changed_tag = False
        if intent['tag']:
            sample = nfc.reader.snapshot()
            intent['tag_present'] = nfc.enabled and sample.get('state') == 'present' and sample.get('tag') == intent['tag']
            # The login handoff survives a lifted tag or interrupted reader.
            # A different tag/disabled NFC still invalidates the old request;
            # check_intent rechecks fresh presence before any audio can start.
            changed_tag = not nfc.enabled or (sample.get('state') == 'present' and sample.get('tag') != intent['tag'])
        if (self.clock() >= intent['deadline'] or changed_tag or
                (intent['account'] is not None and intent['account'] != account)):
            self.cancel()
        elif account and intent['account'] is None:
            intent['account'] = account
            self.touch()

    def observe_activity(self, activity, playback=False):
        """Activity, not silence or lack of screen touches, keeps a session open.

        On the first idle observation grant the entire grace period again, even
        if the device was busy for hours or the monitor was briefly delayed.
        Background processing alone does not keep an unattended account open.
        """
        suspended = bool(activity.occupied or activity.paused or playback)
        if suspended or self.idle_suspended:
            self.touch()
        self.idle_suspended = suspended
        self.idle_reason = ('Aufnahme pausiert' if activity.paused else
                            'Aufnahme läuft' if activity.recording else
                            'Gespräch läuft' if activity.live_busy else
                            'Wiedergabe läuft' if playback else
                            'Gerät wird verwendet' if suspended else '')

    def idle_remaining(self):
        return max(0, int(self.config.get('idle_minutes', 15) * 60 - (self.clock() - self.last_touch)))

    def public(self):
        intent = None
        if self.intent:
            intent = {k: self.intent[k] for k in ('id', 'mode')}
            intent['source'] = 'nfc' if self.intent['tag'] else 'touch'
            intent['tag_present'] = bool(self.intent['tag_present'])
        return {'enabled': self.enabled, 'signed_in': bool(self.account()), 'intent': intent,
                'epoch': self.epoch, 'idle_minutes': self.config.get('idle_minutes', 15),
                'idle_remaining': self.idle_remaining(), 'idle_suspended': self.idle_suspended,
                'idle_reason': self.idle_reason, 'warning_seconds': 60, 'operator': self.operator(),
                'ambient_activity': self.config.get('ambient_activity') is True,
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
