"""Internal mobile control boundary. No listener, credentials or network I/O.

The transport authenticates the caller; a local, nonblocking grant lookup returns
its CURRENT grant, or None after revocation. No lookup means deny all. Mutations
are serialized with Studio and journaled durably before their first side effect.
Stdlib only; services/ and web_server.py are already update/image allowlisted.
The private journal is created on the target device, never shipped in an image.
"""
from dataclasses import dataclass
from contextlib import contextmanager
import hashlib
import json
import math
import os
import sqlite3
import time
import uuid


@dataclass(frozen=True)
class VerifiedGrant:
    grant_id: str
    controller_id: str
    server: str
    user_id: str
    client_id: str
    account_generation: int
    expires_at: float

    @property
    def binding(self):
        return {'server': self.server, 'user_id': self.user_id, 'client_id': self.client_id}


class RemoteControlError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def is_uuid(value):
    if not isinstance(value, str): return False
    try: return str(uuid.UUID(value)) == value
    except ValueError: return False


class RemoteControl:
    MAX_TTL = 15
    MAX_RECEIPTS = 10000
    RETAIN_SECONDS = 24 * 60 * 60
    FIELDS = {'command_id', 'action', 'process_epoch', 'expected_generation', 'expected_revision', 'expires_at'}

    def __init__(self, app, grant_lookup=None, clock=time.time):
        self.app, self.grant_lookup, self.clock = app, grant_lookup, clock
        self.process_epoch = str(uuid.uuid4())
        self.revision = 0
        self.fingerprint = None
        folder = app.live.root.parent / 'remote-control'
        self.journal = folder / 'receipts.sqlite3'
        self.journal_ready = False
        try:
            self._initialize_journal(folder)
            self.journal_ready = True
        except (OSError, sqlite3.Error):
            # Optional remote control must not prevent local Studio from starting.
            pass

    def _initialize_journal(self, folder):
        folder.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(folder, 0o700)
        with self._db() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS receipts (
                command_id TEXT PRIMARY KEY, grant_id TEXT NOT NULL, controller_id TEXT NOT NULL,
                binding TEXT NOT NULL, fingerprint TEXT NOT NULL, command TEXT NOT NULL, created REAL NOT NULL,
                phase TEXT NOT NULL, result TEXT)''')
            # Never infer success or replay an effect after a process crash.
            db.execute("UPDATE receipts SET phase='unknown', result=NULL WHERE phase='executing'")
        os.chmod(self.journal, 0o600)

    @contextmanager
    def _db(self):
        connection = sqlite3.connect(self.journal, timeout=2)
        connection.row_factory = sqlite3.Row
        connection.execute('PRAGMA synchronous=FULL')
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def _authorize(self, grant):
        if not self.journal_ready:
            raise RemoteControlError('device_control_unavailable', 'Fernbedienungsspeicher nicht verfügbar.')
        if (not isinstance(grant, VerifiedGrant) or self.grant_lookup is None or
                self.grant_lookup(grant.grant_id, grant.controller_id) != grant or
                not self.clock() < grant.expires_at or
                grant.account_generation != self.app.cdb.generation or
                grant.binding != self.app.wake_account()):
            raise RemoteControlError('grant_revoked', 'Fernbedienung nicht freigegeben. Bitte erneut verbinden.')

    def _selected_areas(self, binding):
        live = self.app.live
        path = live.root / ('areas-' + live._selection_key(binding) + '.json')
        try: value = json.loads(path.read_text())
        except (OSError, ValueError): return []
        if not isinstance(value, dict) or value.get('binding') != binding: return []
        areas = value.get('area_ids')
        if (not isinstance(areas, list) or not 1 <= len(areas) <= 8 or
                any(not is_uuid(area) for area in areas) or len(set(areas)) != len(areas)):
            return []
        return areas

    def _snapshot(self, grant):
        app, live = self.app, self.app.live
        selected = self._selected_areas(grant.binding)
        activity = app.activity()
        reason = app.wake_reason()
        active = live.busy()
        same_account = (live.binding == grant.binding and
                        getattr(live, 'account_generation', None) == grant.account_generation)
        ids = list(live.area_ids) if active and same_account and hasattr(live, 'area_ids') else selected
        names = {}
        try:
            catalog = live.root / ('area-names-' + live._selection_key(grant.binding) + '.json')
            if catalog.stat().st_size <= 262144:
                cached = json.loads(catalog.read_text())
                if cached.get('binding') == grant.binding and isinstance(cached.get('areas'), list):
                    names = {a['id']: a['name'] for a in cached['areas']
                             if isinstance(a, dict) and is_uuid(a.get('id')) and isinstance(a.get('name'), str)}
        except (OSError, ValueError, AttributeError): pass
        names.update({area['id']: area.get('label') or area.get('name', area['id'])
                      for area in live.areas if same_account and isinstance(area, dict) and 'id' in area})
        areas = [{'id': area, 'name': names.get(area, area)} for area in ids]
        state = ('active' if live.state in ('listening', 'thinking', 'speaking', 'reconnecting') else
                 live.state if live.state in ('connecting', 'closing', 'error') else 'idle')
        allowed = []
        if not app.closing and not app.management.busy() and not app.first_start.busy:
            if not active and not reason and selected and app.clock_ready: allowed = ['start']
            elif active and same_account and live.state != 'closing':
                allowed = ['end']
                if state == 'active': allowed.append('set_muted')
        fingerprint = (live.generation, live.control_revision, state, live.muted,
                       tuple(selected), tuple((area['id'], area['name']) for area in areas),
                       activity.mode, reason, tuple(allowed))
        if fingerprint != self.fingerprint:
            self.fingerprint = fingerprint
            self.revision += 1
        return {'process_epoch': self.process_epoch, 'generation': live.generation,
                'revision': self.revision, 'state': state, 'busy': bool(reason),
                'muted': live.muted, 'areas': areas, 'allowed_actions': allowed}

    def status(self, grant):
        app = self.app
        with app.control_lock, app.controller.lock, app.engine.recorder.lock, app.live.lock:
            self._authorize(grant)
            self._finish_pending_ends(grant)
            return self._snapshot(grant)

    def _validate(self, envelope):
        if not isinstance(envelope, dict):
            raise RemoteControlError('invalid_command', 'Ungültiger Fernbedienungsbefehl.')
        command = dict(envelope)
        action = command.get('action')
        fields = self.FIELDS | ({'muted'} if action == 'set_muted' else set())
        expiry = command.get('expires_at')
        if (set(command) != fields or action not in ('start', 'end', 'set_muted') or
                not is_uuid(command.get('command_id')) or not is_uuid(command.get('process_epoch')) or
                type(command.get('expected_generation')) is not int or command['expected_generation'] < 0 or
                type(command.get('expected_revision')) is not int or command['expected_revision'] < 0 or
                type(expiry) not in (int, float) or not math.isfinite(expiry) or
                (action == 'set_muted' and type(command.get('muted')) is not bool)):
            raise RemoteControlError('invalid_command', 'Ungültiger Fernbedienungsbefehl.')
        return command

    def _result(self, command, grant, status, code=None):
        try:
            self._authorize(grant)
            snapshot = self._snapshot(grant)
        except RemoteControlError:
            snapshot = None
        return {'command_id': command['command_id'], 'status': status, 'code': code,
                'snapshot': snapshot}

    def _save(self, db, command_id, phase, result):
        db.execute('UPDATE receipts SET phase=?, result=? WHERE command_id=?',
                   (phase, json.dumps(result, sort_keys=True), command_id))

    def _read_result(self, row, grant):
        if (row['grant_id'] != grant.grant_id or row['controller_id'] != grant.controller_id or
                row['binding'] != json.dumps(grant.binding, sort_keys=True)):
            raise RemoteControlError('not_found', 'Auftrag nicht gefunden.')
        if row['result']: return json.loads(row['result'])
        return self._result(json.loads(row['command']), grant, 'unknown', 'execution_unknown')

    def _finish_pending_ends(self, grant):
        with self._db() as db:
            rows = db.execute("SELECT * FROM receipts WHERE phase='executing' AND grant_id=? AND controller_id=? AND binding=?",
                              (grant.grant_id, grant.controller_id, json.dumps(grant.binding, sort_keys=True))).fetchall()
            for row in rows:
                command = json.loads(row['command'])
                pending = json.loads(row['result']) if row['result'] else {}
                if (pending.get('code') == 'cleanup_pending' and command['action'] == 'end' and
                        command['process_epoch'] == self.process_epoch and
                        self.app.live.generation > command['expected_generation']):
                    self._save(db, command['command_id'], 'complete', self._result(command, grant, 'applied'))

    def receipt(self, command_id, grant):
        app = self.app
        with app.control_lock, app.controller.lock, app.engine.recorder.lock, app.live.lock:
            self._authorize(grant)
            self._finish_pending_ends(grant)
            with self._db() as db:
                row = db.execute('SELECT * FROM receipts WHERE command_id=?', (command_id,)).fetchone()
            if row is None: raise RemoteControlError('not_found', 'Auftrag nicht gefunden.')
            return self._read_result(row, grant)

    def command(self, envelope, grant):
        command = self._validate(envelope)
        app = self.app
        with app.control_lock, app.controller.lock, app.engine.recorder.lock, app.live.lock:
            self._authorize(grant)
            self._finish_pending_ends(grant)
            now = self.clock()
            encoded = json.dumps(command, sort_keys=True, separators=(',', ':'))
            fingerprint = hashlib.sha256(encoded.encode()).hexdigest()
            with self._db() as db:
                row = db.execute('SELECT * FROM receipts WHERE command_id=?', (command['command_id'],)).fetchone()
                if row:
                    self._read_result(row, grant)  # Enforce scope before revealing a conflict.
                    if row['fingerprint'] != fingerprint:
                        raise RemoteControlError('command_conflict', 'Befehlskennung bereits verwendet.')
                    return self._read_result(row, grant)
                if not now < command['expires_at'] <= now + self.MAX_TTL:
                    raise RemoteControlError('command_expired', 'Befehl abgelaufen. Status aktualisieren.')
                snapshot = self._snapshot(grant)
                if (command['process_epoch'] != self.process_epoch or
                        command['expected_generation'] != app.live.generation or
                        command['expected_revision'] != snapshot['revision']):
                    raise RemoteControlError('stale_state', 'Gespräch hat sich geändert. Status aktualisieren.')
                db.execute("DELETE FROM receipts WHERE created<? AND phase!='executing'",
                           (now - self.RETAIN_SECONDS,))
                if db.execute('SELECT COUNT(*) FROM receipts').fetchone()[0] >= self.MAX_RECEIPTS:
                    raise RemoteControlError('rate_limited', 'Zu viele Befehle. Bitte später erneut versuchen.')
                db.execute('INSERT INTO receipts VALUES (?,?,?,?,?,?,?,?,NULL)',
                           (command['command_id'], grant.grant_id, grant.controller_id,
                            json.dumps(grant.binding, sort_keys=True), fingerprint, encoded, now, 'executing'))
            # SQLite commit above is deliberately BEFORE any audio side effect.
            try:
                self._dispatch(command, grant)
                pending = command['action'] == 'end' and app.live.state == 'closing'
                result = self._result(command, grant, 'unknown' if pending else 'applied',
                                      'cleanup_pending' if pending else None)
            except RemoteControlError as error:
                pending = False
                result = self._result(command, grant, 'expired' if error.code == 'command_expired' else 'rejected', error.code)
            except Exception:
                pending = False
                result = self._result(command, grant, 'rejected', 'operation_failed')
            with self._db() as db:
                self._save(db, command['command_id'], 'executing' if pending else 'complete', result)
            return result

    def _dispatch(self, command, grant):
        app, live = self.app, self.app.live
        if app.closing or app.management.busy() or app.first_start.busy:
            raise RemoteControlError('device_busy', 'Gerät ist beschäftigt. Bitte kurz warten.')
        if (command['action'] == 'start' or command.get('muted') is False) and not app.clock_ready:
            raise RemoteControlError('clock_untrusted', 'Gerätezeit ist noch nicht bestätigt.')
        if command['action'] == 'start':
            reason = app.wake_reason()
            if reason: raise RemoteControlError('device_busy', reason)
            app.require('live')
            app.wake.test_until = 0
            app.wake.suspend()
            # Suspend may wait for child cleanup; expired/revoked starts stay closed.
            self._authorize(grant)
            if self.clock() >= command['expires_at']:
                raise RemoteControlError('command_expired', 'Befehl abgelaufen.')
            app._start_device_live_locked(grant.binding)
            return
        if (live.binding != grant.binding or
                getattr(live, 'account_generation', None) != grant.account_generation):
            raise RemoteControlError('stale_state', 'Gespräch gehört nicht zur aktuellen Freigabe.')
        if command['action'] == 'end':
            live.end(generation=command['expected_generation'])
            return
        if live.state not in ('listening', 'thinking', 'speaking', 'reconnecting'):
            raise RemoteControlError('not_ready', 'Mikrofon erst im verbundenen Gespräch steuern.')
        live.mute(live.lease, command['muted'])
