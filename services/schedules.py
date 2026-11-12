"""Local device timers; durable transitions, monotonic countdowns and explicit DST.

The scheduler's single tick is driven by Studio independently of any browser.
A due item remains visible until acknowledged. Audio delivery is separate from
firing and never interrupts a recorder/live session.
"""
from contextlib import contextmanager
import hashlib
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
            if 'tone' not in {r[1] for r in db.execute('PRAGMA table_info(schedules)')}:
                db.execute("ALTER TABLE schedules ADD COLUMN tone TEXT NOT NULL DEFAULT 'bell'")
            db.execute('CREATE TABLE IF NOT EXISTS tool_results (request TEXT PRIMARY KEY, payload TEXT NOT NULL, result TEXT NOT NULL, created REAL NOT NULL)')
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
        with self.lock, self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            return self._create(db, body)

    def _create(self, db, body):
        kind, label, request = body.get('kind'), body.get('label', ''), body.get('request_id')
        if kind not in ('timer','reminder'): raise ValueError('Timer oder Erinnerung wählen.')
        if not isinstance(label, str) or not 1 <= len(label.strip()) <= 80: raise ValueError('Titel mit 1–80 Zeichen eingeben.')
        if not isinstance(request, str) or not 8 <= len(request) <= 100: raise ValueError('Anfragekennung fehlt.')
        from services.alarm_tones import TONES
        if body.get('tone', 'bell') not in TONES: raise ValueError('Unbekannter Alarmton.')
        payload = json.dumps(body, sort_keys=True)
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
        db.execute('INSERT INTO schedules VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
            (ident,request,payload,kind,label.strip(),due,self.boot,deadline,'scheduled',1,'pending',now,body.get('tone','bell')))
        return {'id': ident}

    def change(self, body):
        with self.lock, self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            return self._change(db, body)

    def _change(self, db, body):
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
        return [{k:r[k] for k in ('id','kind','label','due','state','revision','sound','tone')} |
                {'remaining':max(0,round(self.remaining(r)))} for r in rows]

    def claim_countdown(self, clock_ready=True):
        """Consume the pre-roll window durably, even if speech is disabled/busy.

        Separate bounded receipts leave the timer schema and alarm receipts
        unchanged. Overlapping timers are consumed too, never queued for later.
        A damaged/unwritable receipt file disables countdowns, not normal alarms.
        """
        from meeting_recorder.core import atomic_write
        receipt = self.path.parent / 'timer-countdowns.json'
        with self.lock, self.db() as db:
            try:
                from services.announcements import bounded_file
                seen = json.loads(bounded_file(receipt, 32768)) if receipt.exists() else {}
                if (not isinstance(seen, dict) or len(seen) > 150 or
                        any(not isinstance(k, str) or type(v) is not int or v < 1 for k, v in seen.items())):
                    return None
                rows = db.execute("SELECT * FROM schedules WHERE state='scheduled' AND kind='timer'").fetchall()
                updated = {r['id']:seen[r['id']] for r in rows if r['id'] in seen}
                candidates = []
                for row in rows:
                    if row['boot'] != self.boot and not clock_ready: continue
                    remaining = self.remaining(row)
                    if remaining > 7 or seen.get(row['id']) == row['revision']: continue
                    updated[row['id']] = row['revision']
                    if 5 <= remaining <= 7 and row['tone'] != 'silent':
                        candidates.append({'id': row['id'], 'revision': row['revision'],
                                           'end_at': time.monotonic() + remaining})
                if updated != seen: atomic_write(receipt, json.dumps(updated))
                return min(candidates, key=lambda item: item['end_at']) if candidates else None
            except (OSError, ValueError): return None

    def sound_result(self, ident, result):
        with self.lock, self.db() as db:
            db.execute("UPDATE schedules SET sound=? WHERE id=? AND state='due'",(result,ident))

    def execute_tool(self, scope, request, clock_ready=True):
        """Mutation and replayable receipt commit together; no transcript interpretation."""
        ident, name, args = request.get('id'), request.get('name'), request.get('arguments')
        if not isinstance(ident,str) or not 16 <= len(ident) <= 100 or not isinstance(args,dict):
            raise ValueError('Ungültiger Geräteauftrag.')
        key = hashlib.sha256(json.dumps([scope,ident],sort_keys=True).encode()).hexdigest()
        payload = json.dumps(request,sort_keys=True)
        with self.lock, self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            old=db.execute('SELECT * FROM tool_results WHERE request=?',(key,)).fetchone()
            if old:
                if old['payload'] != payload: raise ValueError('Geräteauftrag wurde nachträglich verändert.')
                return json.loads(old['result'])
            try:
                if type(request.get('expires_at')) not in (int,float) or self.wall() >= request['expires_at']:
                    raise ValueError('Geräteauftrag abgelaufen. Nicht automatisch erneut anlegen.')
                if name in ('create_timer','create_reminder'):
                    fields={'label','seconds','tone'} if name=='create_timer' else {'label','local_time','zone','tone'}
                    if set(args)!=fields: raise ValueError('Ungültige Parameter.')
                    if name=='create_reminder' and not clock_ready: raise ValueError('Gerätezeit ist nicht synchronisiert.')
                    body={**args,'kind':'timer' if name=='create_timer' else 'reminder','request_id':key}
                    created=self._create(db,body)
                    result={'ok':True,'id':created['id'],'label':args['label'],'tone':args['tone'],'message':'Auf dem Pi gespeichert.'}
                elif name=='list_schedules' and not args:
                    rows=db.execute("SELECT id,kind,label,due,state,revision,tone FROM schedules WHERE state IN ('scheduled','due','missed') ORDER BY due LIMIT 100").fetchall()
                    result={'ok':True,'items':[dict(r) for r in rows]}
                elif name in ('cancel_schedule','acknowledge_alarm','snooze_alarm') and set(args)=={'id','revision'}:
                    self._change(db,{**args,'action':{'cancel_schedule':'cancel','acknowledge_alarm':'ack','snooze_alarm':'snooze'}[name]})
                    result={'ok':True,'id':args['id']}
                else: raise ValueError('Gerätewerkzeug nicht verfügbar.')
            except (ValueError,TypeError,KeyError) as error:
                result={'ok':False,'message':str(error),'instruction':'Keinen Erfolg behaupten. Bei unklarer Zeit nachfragen; bei unbestätigtem Ergebnis zuerst die Timerliste prüfen.'}
            db.execute('INSERT INTO tool_results VALUES (?,?,?,?)',(key,payload,json.dumps(result),self.wall()))
            db.execute('DELETE FROM tool_results WHERE created < ?',(self.wall()-7*86400,))
            return result
