"""Local device timers; durable transitions, monotonic countdowns and explicit DST.

The scheduler's single tick is driven by Studio independently of any browser.
A due item remains visible until acknowledged. Audio delivery is separate from
firing and never interrupts a recorder/live session.
"""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import sqlite3
import threading
import time
import uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo


def boottime():
    return time.clock_gettime(time.CLOCK_BOOTTIME) if hasattr(time, 'CLOCK_BOOTTIME') else time.monotonic()


def local_due(value, zone='Europe/Berlin', fold=None):
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is not None: raise ValueError()
        tz = ZoneInfo(zone)
        candidates = {dt.replace(tzinfo=tz, fold=f).timestamp() for f in (0, 1)
                      if datetime.fromtimestamp(dt.replace(tzinfo=tz, fold=f).timestamp(), tz).replace(tzinfo=None) == dt}
        if not candidates: raise ValueError('Diese Uhrzeit gibt es wegen der Zeitumstellung nicht.')
        if len(candidates) > 1 and fold not in (0, 1):
            raise ValueError('Diese Uhrzeit kommt zweimal vor. Bitte eine eindeutige Uhrzeit wählen.')
        return dt.replace(tzinfo=tz, fold=fold or 0).timestamp()
    except (TypeError, KeyError): raise ValueError('Datum und Uhrzeit prüfen.') from None


class Schedules:
    def __init__(self, root, wall=time.time, elapsed=boottime, boot=None):
        self.wall, self.elapsed = wall, elapsed
        try: self.boot = boot or Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        except OSError: self.boot = boot or 'process-'+str(os.getpid())
        self.path = Path(root)/'timers.sqlite3'
        self.lock = threading.RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.db() as db:
            db.execute('CREATE TABLE IF NOT EXISTS schedules (id TEXT PRIMARY KEY, request TEXT UNIQUE, payload TEXT, kind TEXT, label TEXT, due REAL, boot TEXT, deadline REAL, state TEXT, revision INTEGER, sound TEXT, created REAL)')
        os.chmod(self.path, 0o600)

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.path, timeout=3)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA synchronous=FULL')
        try:
            with db: yield db
        finally: db.close()

    @staticmethod
    def duration(value):
        if type(value) is not int or not 1 <= value <= 604800:
            raise ValueError('Dauer zwischen einer Sekunde und sieben Tagen wählen.')
        return value

    def create(self, body):
        kind, label, request = body.get('kind'), body.get('label', ''), body.get('request_id')
        if kind not in ('timer','reminder'): raise ValueError('Timer oder Erinnerung wählen.')
        if not isinstance(label, str) or not 1 <= len(label.strip()) <= 80: raise ValueError('Titel mit 1–80 Zeichen eingeben.')
        if not isinstance(request, str) or not 8 <= len(request) <= 100: raise ValueError('Anfragekennung fehlt.')
        payload = json.dumps(body, sort_keys=True)
        with self.lock, self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            old = db.execute('SELECT * FROM schedules WHERE request=?', (request,)).fetchone()
            if old:
                if old['payload'] != payload: raise ValueError('Anfragekennung wurde bereits anders verwendet.')
                return dict(old)
            if db.execute("SELECT count(*) FROM schedules WHERE state IN ('scheduled','due','missed')").fetchone()[0] >= 100:
                raise ValueError('Maximal 100 offene Timer und Erinnerungen.')
            now = self.wall()
            if kind == 'timer':
                duration = self.duration(body.get('seconds'))
                due, deadline = now+duration, self.elapsed()+duration
            else:
                due, deadline = local_due(body.get('local_time'), body.get('zone','Europe/Berlin')), 0
                if not now < due <= now+366*86400: raise ValueError('Erinnerung innerhalb des nächsten Jahres wählen.')
            ident = str(uuid.uuid4())
            db.execute('INSERT INTO schedules VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
                (ident,request,payload,kind,label.strip(),due,self.boot,deadline,'scheduled',1,'pending',now))
            return {'id': ident}

    def change(self, body):
        with self.lock, self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM schedules WHERE id=?',(body.get('id'),)).fetchone()
            if not row: raise ValueError('Eintrag fehlt.')
            if type(body.get('revision')) is not int or row['revision'] != body['revision']:
                raise ValueError('Eintrag wurde geändert. Bitte aktualisieren.')
            action = body.get('action')
            if action not in ('cancel','ack','snooze'): raise ValueError('Unbekannte Timeraktion.')
            if action in ('ack','snooze') and row['state'] not in ('due','missed'): raise ValueError('Dieser Eintrag ist noch nicht fällig.')
            if action == 'cancel' and row['state'] not in ('scheduled','due','missed'): raise ValueError('Eintrag ist bereits erledigt.')
            state = {'cancel':'cancelled','ack':'done','snooze':'scheduled'}[action]
            if action == 'snooze':
                db.execute("UPDATE schedules SET kind='timer',due=?,boot=?,deadline=?,state=?,sound='pending',revision=revision+1 WHERE id=?",
                    (self.wall()+300,self.boot,self.elapsed()+300,state,row['id']))
            else: db.execute('UPDATE schedules SET state=?,revision=revision+1 WHERE id=?',(state,row['id']))
            return {'ok':True}

    def remaining(self, row):
        if row['kind']=='timer' and row['boot']==self.boot: return row['deadline']-self.elapsed()
        return row['due']-self.wall()

    def tick(self, clock_ready=True):
        with self.lock, self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            for row in db.execute("SELECT * FROM schedules WHERE state='scheduled'").fetchall():
                if not clock_ready and (row['kind']=='reminder' or row['boot']!=self.boot): continue
                remaining = self.remaining(row)
                if remaining <= 0:
                    state = 'due' if remaining >= -300 else 'missed'
                    db.execute('UPDATE schedules SET state=?,revision=revision+1 WHERE id=?',(state,row['id']))
            # Retain a bounded recent history, never remove outstanding alarms.
            db.execute("DELETE FROM schedules WHERE state IN ('done','cancelled') AND created < ?",(self.wall()-30*86400,))

    def items(self):
        with self.lock, self.db() as db:
            rows = db.execute("SELECT * FROM schedules ORDER BY CASE state WHEN 'due' THEN 0 WHEN 'scheduled' THEN 1 WHEN 'missed' THEN 2 ELSE 3 END,due LIMIT 150").fetchall()
        return [{k:r[k] for k in ('id','kind','label','due','state','revision','sound')} |
                {'remaining':max(0,round(self.remaining(r)))} for r in rows]

    def sound_result(self, ident, result):
        with self.lock, self.db() as db:
            db.execute("UPDATE schedules SET sound=? WHERE id=? AND state='due'",(result,ident))
