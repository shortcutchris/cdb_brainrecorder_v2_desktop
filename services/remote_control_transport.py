"""Outgoing, opt-in CDB control channel. No LAN listener or mobile audio.

The serial worker owns network requests; neither Studio locks nor the domain
adapter perform network I/O. A fresh complete grant snapshot authenticates each
batch. Account changes invalidate credentials and every late response.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import queue
import re
import secrets
import threading
import time
import urllib.error
import urllib.request
import uuid

from services.http_connection import HTTPSHandler
from services.remote_control import RemoteControlError, VerifiedGrant, is_uuid

BASE = '/api/v1/tqs/device-control'
ORIGINS = frozenset(('https://staging.cdbos.de', 'https://cdbos.de'))
CODE = re.compile(r'^[ABCDEFGHJKLMNPQRSTUVWXYZ23456789]{8}$')


class ChannelError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__('Fernbedienung: ' + code)


class HTTPSControl:
    """Fixed origins, certificate validation, no redirects/proxies, bounded JSON."""
    def request(self, origin, path, token, body=None):
        if origin not in ORIGINS or not path.startswith('/') or '?' in path or '#' in path:
            raise ChannelError('invalid_server')
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *args): return None
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect(), HTTPSHandler())
        headers = {'Authorization': 'Bearer ' + token, 'Accept': 'application/json',
                   'User-Agent': 'CDB-Pi-Control/1'}
        data = None if body is None else json.dumps(body).encode()
        if data is not None: headers['Content-Type'] = 'application/json'
        try:
            with opener.open(urllib.request.Request(origin + BASE + path, data=data, headers=headers), timeout=6) as response:
                if response.status == 204: return {}
                raw = response.read(262145)
                if len(raw) > 262144: raise ChannelError('invalid_response')
                result = json.loads(raw)
                if not isinstance(result, dict): raise ChannelError('invalid_response')
                return result
        except urllib.error.HTTPError as error:
            # Never relay arbitrary server text or credentials into UI/logs.
            raise ChannelError({401: 'sign_in_required', 403: 'access_denied',
                                404: 'not_supported', 409: 'conflict', 410: 'expired',
                                429: 'rate_limited'}.get(error.code, 'unavailable')) from None
        except (OSError, ValueError) as error:
            if isinstance(error, ChannelError): raise
            raise ChannelError('unavailable') from None


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


class RemoteControlChannel:
    def __init__(self, app, transport=None, clock=time.time, start=True):
        self.app, self.http, self.clock = app, transport or HTTPSControl(), clock
        self.root = Path(app.store.root) / 'remote-control'
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.root, 0o700)
        self.path = self.root / 'connection.json'
        self.lock = threading.RLock()
        self.stop = threading.Event()
        self.signal = threading.Event()
        self.jobs = queue.Queue(maxsize=4)
        self.connection = None
        self.account_generation = app.cdb.generation
        self.grants, self.pending, self.receipts = {}, [], {}
        self.grants_revision = -1
        self.code, self.code_expiry = '', 0
        self.state, self.error, self.last_contact = 'unpaired', '', 0
        self.capable = False
        self.busy = False
        self.worker = None
        self._load()
        app.remote_control.grant_lookup = self.lookup
        if start:
            self.worker = threading.Thread(target=self._run, name='cdb-mobile-control', daemon=True)
            self.worker.start()

    def _identity(self):
        try: binding = self.app.wake_account()
        except (OSError, ValueError, TypeError): return None
        if (not isinstance(binding, dict) or binding.get('server') not in ORIGINS or
                not all(is_uuid(binding.get(k)) for k in ('user_id', 'client_id'))): return None
        return binding

    @staticmethod
    def wire_binding(binding):
        return {'environment': binding['server'], 'user_id': binding['user_id'], 'client_id': binding['client_id']}

    def _load(self):
        try:
            value = json.loads(self.path.read_text())
            if (set(value) != {'device_id', 'credential', 'binding', 'registered', 'revoking'} or
                    not is_uuid(value['device_id']) or not isinstance(value['credential'], str) or
                    not re.fullmatch(r'[A-Za-z0-9_-]{43}', value['credential']) or
                    type(value['registered']) is not bool or type(value['revoking']) is not bool or
                    value['binding'] != self._identity()): raise ValueError()
            self.connection = value
            self.state = 'revoking' if value['revoking'] else 'connecting'
        except (OSError, ValueError, KeyError, TypeError):
            # Corrupt/old-account credentials are never reused on a fresh profile.
            self.path.unlink(missing_ok=True)

    def _save(self):
        data = json.dumps(self.connection)
        temporary = self.path.with_suffix('.tmp')
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(descriptor, 'w') as stream:
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, self.path)
        os.chmod(self.path, 0o600)

    def _context(self):
        return self.app.cdb.generation, self._identity()

    def _current(self, context):
        return not self.stop.is_set() and context == self._context()

    def _sync_account(self):
        context = self._context()
        with self.lock:
            if (context[0] != self.account_generation or
                    (self.connection and self.connection['binding'] != context[1])):
                self.account_generation = context[0]
                self.connection = None
                self.grants, self.pending, self.receipts = {}, [], {}
                self.grants_revision = -1
                self.code, self.code_expiry = '', 0
                self.capable = False
                self.state, self.error = 'unpaired', ''
                self.path.unlink(missing_ok=True)
        return context

    def lookup(self, grant_id, controller_id):
        # Called inside Studio's locks. No I/O beyond local identity, no network.
        with self.lock:
            grant = self.grants.get((grant_id, controller_id))
            if (not grant or not self.connection or self.connection['revoking'] or self.stop.is_set() or self.state == 'revoking' or
                    grant.account_generation != self.app.cdb.generation or
                    grant.binding != self._identity() or self.clock() >= grant.expires_at or
                    not 0 <= self.clock() - self.last_contact <= 15): return None
            return grant

    def public(self):
        self._sync_account()
        with self.lock:
            paired = bool(self.grants)
            code = self.code if self.clock() < self.code_expiry else ''
            pending = [dict(item) for item in self.pending if self.clock() < item['expires_at']]
            return {'state': self.state, 'error': self.error, 'supported': self.capable,
                    'busy': self.busy, 'paired': paired, 'code': code,
                    'code_expires_at': self.code_expiry if code else 0,
                    'pending': pending, 'device_id': self.connection['device_id'] if self.connection else '',
                    'environment': self.connection['binding']['server'] if self.connection else '',
                    'online': bool(self.last_contact and self.clock() - self.last_contact < 15),
                    'account_ready': self._identity() is not None}

    def enqueue(self, action, body):
        if action not in ('check', 'pair', 'confirm', 'revoke'): raise ValueError('Unbekannte Aktion.')
        fields = {'pairing_id', 'approved'} if action == 'confirm' else set()
        if (not isinstance(body, dict) or set(body) != fields or
                (action == 'confirm' and (not is_uuid(body['pairing_id']) or type(body['approved']) is not bool))):
            raise ValueError('Ungültige Kopplungsangaben.')
        context = self._sync_account()
        if not context[1]: raise ValueError('Bitte zuerst beim Brain anmelden.')
        with self.lock:
            if self.busy: raise ValueError('Bitte den laufenden Schritt abwarten.')
            if action == 'confirm' and not any(p['pairing_id'] == body['pairing_id'] and
                                               self.clock() < p['expires_at'] for p in self.pending):
                raise ValueError('Kopplungsanfrage abgelaufen. Bitte erneut beginnen.')
            if action == 'revoke':
                if not self.connection: return self.public()
                # Local revocation precedes network. Failed delivery retries safely.
                self.connection['revoking'] = True
                self._save()
                self.grants, self.pending, self.receipts = {}, [], {}
                self.code = ''
                self.state = 'revoking'
            self.busy = True
            try: self.jobs.put_nowait((action, dict(body), context))
            except queue.Full:
                self.busy = False
                raise ValueError('Bitte kurz warten.') from None
            self.signal.set()
        return {'accepted': True}

    def _call(self, context, path, body=None, personal=False):
        if not self._current(context): raise ChannelError('account_changed')
        if personal:
            session = self.app.cdb.session(binding=context[1])
            token = session['token']
        else:
            with self.lock:
                if not self.connection or self.connection['binding'] != context[1]: raise ChannelError('account_changed')
                token = self.connection['credential']
        if not self._current(context): raise ChannelError('account_changed')
        result = self.http.request(context[1]['server'], path, token, body)
        if not self._current(context): raise ChannelError('account_changed')
        return result

    def _check(self, context):
        capability = self._call(context, '/capabilities', personal=True)
        with self.lock:
            self.capable = capability.get('device_control_v1') is True and capability.get('protocol_version') == 1
            self.state = 'ready' if self.capable and not self.connection else self.state
            if not self.capable:
                self.state = 'unsupported'
                raise ChannelError('not_supported')

    def _register(self, context):
        with self.lock:
            if not self.connection:
                self.connection = {'device_id': str(uuid.uuid4()), 'credential': secrets.token_urlsafe(32),
                                   'binding': context[1], 'registered': False, 'revoking': False}
                self._save()  # persist before an ambiguous network result; retry same ID/hash
            connection = dict(self.connection)
        if not connection['registered']:
            result = self._call(context, '/devices/register', {
                'device_id': connection['device_id'], 'device_name': 'Brain Recorder',
                'credential_hash': hashlib.sha256(connection['credential'].encode()).hexdigest()}, personal=True)
            if result.get('device_id') != connection['device_id'] or result.get('binding') != self.wire_binding(context[1]):
                raise ChannelError('invalid_response')
            with self.lock:
                if not self._current(context): raise ChannelError('account_changed')
                self.connection['registered'] = True
                self._save()

    def _job(self, action, body, context):
        if not self._current(context): return
        if action == 'check': self._check(context)
        elif action == 'pair':
            self._check(context)
            self._register(context)
            result = self._call(context, '/device/pairings', {})
            if (not isinstance(result.get('code'), str) or not CODE.fullmatch(result['code']) or
                    not finite(result.get('expires_at')) or not self.clock() < result['expires_at'] <= self.clock() + 305):
                raise ChannelError('invalid_response')
            with self.lock:
                self.code, self.code_expiry = result['code'], result['expires_at']
                self.state = 'pairing'
        elif action == 'confirm':
            self._call(context, '/device/pairings/' + body['pairing_id'] + '/confirm', {'approved': body['approved']})
            # Only a fresh poll installs grants; UI never invents confirmation.
        elif action == 'revoke': self._revoke(context)

    def _revoke(self, context):
        self._call(context, '/device/revoke', {})
        with self.lock:
            if not self._current(context): return
            self.connection = None
            self.grants, self.pending, self.receipts = {}, [], {}
            self.grants_revision = -1
            self.code, self.code_expiry, self.last_contact = '', 0, 0
            self.state = 'unpaired'
            self.path.unlink(missing_ok=True)

    def _poll(self, context):
        with self.lock:
            connection = dict(self.connection) if self.connection else None
        if not connection: return
        if connection['revoking']:
            self._revoke(context); return
        if not connection['registered']: return
        result = self._call(context, '/device/poll', {'process_epoch': self.app.remote_control.process_epoch, 'timeout_seconds': 2})
        grants, pending, commands = self._validate_poll(result, context, connection['device_id'])
        with self.lock:
            if not self._current(context): raise ChannelError('account_changed')
            if self.connection != connection or self.connection['revoking']:
                raise ChannelError('account_changed')
            revision = result['grants_revision']
            if revision < self.grants_revision: raise ChannelError('stale_response')
            if revision == self.grants_revision and grants != self.grants: raise ChannelError('stale_response')
            self.grants_revision, self.grants, self.pending = revision, grants, pending
            self.last_contact = self.clock()
            self.state = 'paired' if grants else 'confirm' if pending else 'pairing' if self.clock() < self.code_expiry else 'ready'
            if grants or pending: self.code = ''
            self.capable, self.error = True, ''
        # Never hold transport lock while entering Studio locks.
        for command in commands:
            grant = self.lookup(command['grant_id'], command['controller_id'])
            if not grant: continue
            payload = {key: value for key, value in command.items()
                       if key not in ('device_id', 'binding', 'grant', 'grant_id', 'controller_id')}
            try:
                outcome = self.app.remote_control.command(payload, grant)
            except RemoteControlError as error:
                outcome = {'command_id': command['command_id'], 'status': 'expired' if error.code == 'command_expired' else 'rejected',
                           'code': error.code, 'snapshot': self.app.remote_control.status(grant)}
            self.receipts[command['command_id']] = (grant, outcome)
        for command_id, (grant, outcome) in list(self.receipts.items()):
            if not self.lookup(grant.grant_id, grant.controller_id):
                self.receipts.pop(command_id, None); continue
            if outcome.get('code') == 'cleanup_pending':
                outcome = self.app.remote_control.receipt(command_id, grant)
                if outcome.get('code') == 'cleanup_pending': continue
            receipt = {key: outcome.get(key) for key in ('status', 'code', 'snapshot')}
            if receipt['snapshot'] is not None: receipt['snapshot'] = dict(receipt['snapshot'], device_id=connection['device_id'])
            self._call(context, '/device/commands/' + command_id + '/receipt', receipt)
            self.receipts.pop(command_id, None)
        for grant in grants.values():
            snapshot = dict(self.app.remote_control.status(grant), device_id=connection['device_id'])
            self._call(context, '/device/status', snapshot)
            break  # v1 allows one active controller only

    def _validate_poll(self, value, context, device_id):
        if (value.get('protocol_version') != 1 or value.get('binding') != self.wire_binding(context[1]) or
                type(value.get('grants_revision')) is not int or value['grants_revision'] < 0 or
                any(not isinstance(value.get(k), list) for k in ('grants', 'pending_pairings', 'commands')) or
                len(value['grants']) > 1 or len(value['pending_pairings']) > 1 or len(value['commands']) > 32):
            raise ChannelError('invalid_response')
        grants = {}
        for item in value['grants']:
            if (not isinstance(item, dict) or not is_uuid(item.get('grant_id')) or not is_uuid(item.get('controller_id')) or
                    not finite(item.get('expires_at')) or not self.clock() < item['expires_at'] <= self.clock() + 30 * 86400 + 10):
                raise ChannelError('invalid_response')
            grant = VerifiedGrant(item['grant_id'], item['controller_id'], **context[1],
                                  account_generation=context[0], expires_at=item['expires_at'])
            grants[(grant.grant_id, grant.controller_id)] = grant
        pending = []
        for item in value['pending_pairings']:
            if (not isinstance(item, dict) or not is_uuid(item.get('pairing_id')) or not is_uuid(item.get('controller_id')) or
                    item.get('device_id') != device_id or item.get('binding') != self.wire_binding(context[1]) or
                    item.get('state') != 'pending_confirmation' or not finite(item.get('expires_at'))):
                raise ChannelError('invalid_response')
            if self.clock() < item['expires_at']:
                pending.append({'pairing_id': item['pairing_id'], 'controller_id': item['controller_id'], 'expires_at': item['expires_at']})
        commands = []
        for command in value['commands']:
            if (not isinstance(command, dict) or command.get('device_id') != device_id or
                    command.get('binding') != self.wire_binding(context[1]) or not is_uuid(command.get('command_id'))):
                raise ChannelError('invalid_response')
            grant = grants.get((command.get('grant_id'), command.get('controller_id')))
            if not grant or command.get('grant') != {'grant_id': grant.grant_id, 'controller_id': grant.controller_id, 'expires_at': grant.expires_at}:
                raise ChannelError('invalid_response')
            commands.append(command)
        return grants, pending, commands

    def step(self):
        """One bounded worker iteration; injectable transport enables offline tests."""
        try:
            context = self._sync_account()
            try: action, body, queued_context = self.jobs.get_nowait()
            except queue.Empty: pass
            else:
                try: self._job(action, body, queued_context)
                finally:
                    with self.lock: self.busy = False
                    self.jobs.task_done()
            if context[1]: self._poll(context)
        except Exception as error:
            with self.lock:
                self.error = error.code if isinstance(error, (ChannelError, RemoteControlError)) else 'unavailable'
                if self.state not in ('revoking', 'unsupported'): self.state = 'offline' if self.connection else 'error'
                # No stale grant is usable after a failed authenticated poll.
                self.grants = {}
                self.grants_revision = -1

    def _run(self):
        while not self.stop.is_set():
            self.step()
            self.signal.wait(2 if not self.error else 5)
            self.signal.clear()

    def close(self):
        self.stop.set(); self.signal.set()
        with self.lock: self.grants = {}
        # No join here: Studio.close may hold its own locks. Worker responses are
        # generation/stop checked and therefore cannot mutate after shutdown.


class UnavailableChannel:
    """Optional control setup must not prevent local recording or boot."""
    def public(self):
        return {'state': 'error', 'error': 'storage_unavailable', 'supported': False,
                'busy': False, 'paired': False, 'pending': [], 'account_ready': False}
    def enqueue(self, action, body):
        raise ValueError('Fernbedienung nicht verfügbar. Gerätespeicher prüfen.')
    def close(self): pass


def create_channel(app, **kwargs):
    try: return RemoteControlChannel(app, **kwargs)
    except (OSError, ValueError): return UnavailableChannel()
