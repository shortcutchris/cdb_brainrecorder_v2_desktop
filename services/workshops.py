"""Account-owned workshop drafts and explicit Composer snapshot publication.

No raw audio; no model-selected URLs/board IDs. Composer's existing voice bridge
executes MCP tools with the caller's Entra login. Every remote write is journalled
before it is attempted; uncertain writes are never repeated automatically.
"""
import contextlib
import hashlib
import json
import math
import sqlite3
import threading
import time
import uuid
from pathlib import Path

NAMES = ('get_workshop', 'update_workshop_result', 'set_workshop_phase', 'save_workshop_to_composer')
SECTIONS = {'goal': 'Ziel', 'questions': 'Fragen', 'findings': 'Erkenntnisse',
            'ideas': 'Ideen', 'decisions': 'Bestätigte Entscheidungen', 'next_steps': 'Nächste Schritte'}
PHASES = ('opening', 'exploring', 'grouping', 'prioritizing', 'closing')
PHASE_LABELS = ('Ankommen', 'Sammeln', 'Ordnen', 'Priorisieren', 'Abschließen')
FORMATS = ('interview', 'brainstorming')


def owner(binding):
    if not isinstance(binding, dict) or not all(binding.get(k) for k in ('server', 'user_id', 'client_id')):
        raise ValueError('Bitte zuerst am Brain anmelden.')
    return hashlib.sha256(json.dumps(binding, sort_keys=True).encode()).hexdigest()


class Workshops:
    def __init__(self, root, cdb, account, *, spawn=None):
        self.path = Path(root) / 'workshops.sqlite3'
        self.cdb, self.account = cdb, account
        self.lock = threading.RLock()
        self.spawn = spawn or (lambda fn: threading.Thread(target=fn, daemon=True).start())
        with self.db() as db:
            db.execute('CREATE TABLE IF NOT EXISTS drafts (id TEXT PRIMARY KEY, owner TEXT NOT NULL, data TEXT NOT NULL, updated REAL NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS receipts (id TEXT PRIMARY KEY, payload TEXT NOT NULL, result TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS writes (id TEXT PRIMARY KEY, state TEXT NOT NULL, data TEXT NOT NULL)')
            for ident, raw in db.execute('SELECT id,data FROM drafts').fetchall():
                row = json.loads(raw)
                if row['composer']['state'] == 'saving':
                    row['composer']['state'] = 'uncertain'
                    row['composer']['message'] = 'Übertragung wurde unterbrochen. Bitte das Composer-Board prüfen; nicht erneut senden.'
                    self._put(db, row)
        self.path.chmod(0o600)

    @contextlib.contextmanager
    def db(self):
        db = sqlite3.connect(self.path, timeout=10)
        try:
            with db:
                yield db
        finally:
            db.close()

    def _put(self, db, row):
        db.execute('UPDATE drafts SET data=?,updated=? WHERE id=?', (json.dumps(row), time.time(), row['id']))

    def _get(self, db, binding, ident):
        if not isinstance(ident, str) or len(ident) != 36:
            raise ValueError('Ungültiges Gesprächsergebnis.')
        if binding != self.account():
            raise ValueError('Das angemeldete Konto hat sich geändert.')
        raw = db.execute('SELECT data FROM drafts WHERE id=? AND owner=?', (ident, owner(binding))).fetchone()
        if not raw:
            raise ValueError('Ergebnis fehlt oder gehört zu einem anderen Konto.')
        return json.loads(raw[0])

    def list(self, binding):
        if not binding: return []
        with self.lock, self.db() as db:
            rows = db.execute('SELECT data FROM drafts WHERE owner=? ORDER BY updated DESC LIMIT 50', (owner(binding),)).fetchall()
        return [self.metadata(json.loads(r[0])) for r in rows]

    @staticmethod
    def metadata(row):
        return {k: v for k, v in row.items() if k != 'sections'} | {'artifacts': [
            {'section': key, 'title': title, 'characters': len(row['sections'][key])}
            for key, title in SECTIONS.items() if row['sections'][key].strip()]}

    def get(self, binding, ident):
        with self.lock, self.db() as db:
            row = self._get(db, binding, ident)
        publications = getattr(self.cdb, 'artifact_publications', lambda *a: [])
        return row | {'brain': publications(binding, ident)}

    def save_brain(self, binding, ident, revision, sections, area_id):
        if (not isinstance(sections, list) or not 1 <= len(sections) <= len(SECTIONS)
                or any(not isinstance(s, str) or s not in SECTIONS for s in sections)
                or len(set(sections)) != len(sections)):
            raise ValueError('Gewünschte Ergebnisse auswählen.')
        with self.lock, self.db() as db:
            row = self._get(db, binding, ident)
            if type(revision) is not int or revision != row['revision']:
                raise ValueError('Ergebnis wurde geändert. Bitte Auswahl erneut prüfen.')
            if any(not row['sections'][s].strip() for s in sections):
                raise ValueError('Leere Ergebnisse können nicht gespeichert werden.')
            documents = [{'section': s, 'title': row['title'] + ' · ' + SECTIONS[s],
                          'content': '# ' + SECTIONS[s] + '\n\n' + row['sections'][s].strip()}
                         for s in SECTIONS if s in sections]
        # A reviewed immutable snapshot may be queued while newer edits continue.
        # No audio, chat transcript or unselected section enters the publication.
        return self.cdb.enqueue_artifacts(binding, area_id, documents, ident, revision)

    def create(self, binding, kind, title, goal, minutes):
        if kind not in FORMATS or not isinstance(title, str) or not 1 <= len(title.strip()) <= 120:
            raise ValueError('Format und Titel wählen (höchstens 120 Zeichen).')
        if not isinstance(goal, str) or not 1 <= len(goal.strip()) <= 2000 or type(minutes) is not int or not 5 <= minutes <= 20:
            raise ValueError('Ziel angeben und 5 bis 20 Minuten wählen. Ein Live-Gespräch dauert höchstens 20 Minuten.')
        key = owner(binding)
        if binding != self.account(): raise ValueError('Anmeldung hat sich geändert.')
        row = {'id': str(uuid.uuid4()), 'format': kind, 'title': title.strip(), 'minutes': minutes,
               'phase': 'opening', 'revision': 1, 'paused': False,
               'sections': {k: goal.strip() if k == 'goal' else '' for k in SECTIONS},
               'composer': {'state': 'local', 'board_id': None, 'url': None, 'revision': 0, 'message': 'Noch nicht an Composer gesendet.'}}
        with self.lock, self.db() as db:
            db.execute('INSERT INTO drafts VALUES (?,?,?,?)', (row['id'], key, json.dumps(row), time.time()))
        return row

    def edit(self, binding, ident, revision, *, section=None, text=None, phase=None, paused=None):
        with self.lock, self.db() as db:
            row = self._get(db, binding, ident)
            if type(revision) is not int or revision != row['revision']: raise ValueError('Ergebnis wurde inzwischen geändert. Bitte neu laden.')
            if section is not None:
                if not isinstance(section, str) or section not in SECTIONS or not isinstance(text, str) or len(text) > 6000: raise ValueError('Ungültiger Ergebnistext.')
                if sum(len(v) for k,v in row['sections'].items() if k != section) + len(text) > 12000:
                    raise ValueError('Ergebnis ist zu lang. Bitte auf insgesamt 12.000 Zeichen verdichten.')
                row['sections'][section] = text
            elif phase is not None:
                if phase not in PHASES: raise ValueError('Unbekannte Phase.')
                row['phase'] = phase
            elif type(paused) is bool:
                row['paused'] = paused
            else: raise ValueError('Ungültige Änderung.')
            row['revision'] += 1
            self._put(db, row)
        return row

    def execute(self, scope, request):
        """The live session supplies the binding and selected ID, never the model."""
        binding, ident = scope.get('binding'), scope.get('workshop_id')
        if not ident: return {'ok': False, 'code': 'choose_workshop', 'message': 'Zuerst Interview oder Brainstorming am Pi wählen.'}
        name, args = request.get('name'), request.get('arguments')
        valid = isinstance(args, dict) and (
            name in ('get_workshop', 'save_workshop_to_composer') and not args or
            name == 'update_workshop_result' and set(args) == {'section', 'text', 'revision'} or
            name == 'set_workshop_phase' and set(args) == {'phase', 'revision'})
        if not valid: return {'ok': False, 'code': 'invalid_arguments'}
        expires = request.get('expires_at')
        if type(expires) not in (float, int) or not math.isfinite(expires) or expires <= time.time():
            return {'ok': False, 'code': 'expired'}
        request_id = request.get('id')
        if not isinstance(request_id, str) or not 16 <= len(request_id) <= 100: return {'ok': False, 'code': 'invalid_arguments'}
        key = hashlib.sha256(json.dumps([scope, request_id], sort_keys=True).encode()).hexdigest()
        payload = json.dumps(request, sort_keys=True)
        with self.lock:
            try: row = self.get(binding, ident)
            except ValueError: return {'ok': False, 'code': 'workshop_unavailable'}
            with self.db() as db:
                previous = db.execute('SELECT payload,result FROM receipts WHERE id=?', (key,)).fetchone()
                if previous:
                    if previous[0] != payload: return {'ok': False, 'code': 'request_conflict'}
                    return json.loads(previous[1])
                db.execute('INSERT INTO receipts VALUES (?,?,?)', (key, payload, json.dumps({'ok': False, 'code': 'result_unconfirmed'})))
            try:
                if row['paused'] and name in ('update_workshop_result', 'set_workshop_phase'):
                    result = {'ok': False, 'code': 'workshop_paused'}
                elif name == 'get_workshop': result = {'ok': True, 'workshop': row}
                elif name == 'save_workshop_to_composer': result = self.save(binding, ident, row['revision'])
                else:
                    fields = {'section': args['section'], 'text': args['text']} if name == 'update_workshop_result' else {'phase': args['phase']}
                    result = {'ok': True, 'workshop': self.edit(binding, ident, args['revision'], **fields)}
            except ValueError as exc:
                result = {'ok': False, 'code': 'workshop_conflict', 'message': str(exc)}
            with self.db() as db:
                db.execute('UPDATE receipts SET result=? WHERE id=?', (json.dumps(result), key))
            return result

    def save(self, binding, ident, revision):
        with self.lock, self.db() as db:
            row = self._get(db, binding, ident)
            if type(revision) is not int or row['revision'] != revision: raise ValueError('Ergebnis geändert. Vor dem Senden neu laden.')
            if row['composer']['state'] in ('saving', 'uncertain'): return {'ok': False, 'code': row['composer']['state'], 'message': row['composer']['message']}
            if row['composer']['revision'] == revision: return {'ok': True, 'state': 'saved', 'url': row['composer']['url']}
            row['composer'].update(state='saving', message='Übertragung an Composer läuft …')
            self._put(db, row)
        generation = self.cdb.generation
        self.spawn(lambda: self._publish(binding, generation, row))
        return {'ok': True, 'state': 'queued', 'message': 'Übertragung angefordert. Erst gespeicherten Status abwarten.'}

    def _publish(self, binding, generation, snapshot):
        ident = snapshot['id']
        composer = dict(snapshot['composer'])

        def call(name, args, suffix):
            if self.cdb.generation != generation or binding != self.account(): raise ValueError('Konto geändert; Übertragung angehalten.')
            key = f'{ident}:{snapshot["revision"]}:{suffix}'
            with self.lock, self.db() as db:
                old = db.execute('SELECT state,data FROM writes WHERE id=?', (key,)).fetchone()
                if old:
                    if old[0] == 'done': return json.loads(old[1])
                    raise ValueError('Ein Schreibvorgang ist unbestätigt. Bitte im Composer prüfen.')
                db.execute('INSERT INTO writes VALUES (?, ?, ?)', (key, 'uncertain', '{}'))
            # Fixed BFF path; Composer checks app enablement, tenant and board permissions.
            result = self.cdb.call('/api/v1/kb/voice/board-tools/call', {'name': name, 'args': args}, binding=binding)
            if not isinstance(result, dict) or result.get('success') is not True or not isinstance(result.get('data'), dict):
                raise ValueError('Composer hat die Übertragung nicht bestätigt. Freigabe und Board prüfen.')
            data = result['data']
            with self.lock, self.db() as db:
                db.execute('UPDATE writes SET state=?,data=? WHERE id=?', ('done', json.dumps(data), key))
            return data

        try:
            if not composer['board_id']:
                data = call('create_board', {'name': snapshot['title'] + ' · Pi ' + ident[:8]}, 'board')
                if type(data.get('board_id')) is not int or data['board_id'] <= 0: raise ValueError('Ungültige Board-Bestätigung.')
                composer['board_id'] = data['board_id']
                # Fixed environment, numeric server-confirmed ID; never render an arbitrary tool URL.
                host = 'https://composer-staging.cdbos.de' if binding['server'] == 'https://staging.cdbos.de' else 'https://composer.cdbos.de'
                composer['url'] = host + '/board/' + str(data['board_id'])
                self._composer_status(binding, ident, composer)
            notes = []
            for index, (section, title) in enumerate(SECTIONS.items()):
                text = snapshot['sections'][section]
                if not text.strip(): continue
                data = call('add_note', {'board_id': composer['board_id'], 'kind': 'text', 'title': title,
                    'text': text, 'x': (index % 3) * 520, 'y': snapshot['revision'] * 900 + (index // 3) * 380,
                    'width': 460, 'height': 300}, section)
                if not isinstance(data.get('node_id'), str): raise ValueError('Ergebnisnotiz nicht bestätigt.')
                notes.append(data['node_id'])
            if notes:
                call('add_frame', {'board_id': composer['board_id'], 'title': f'{snapshot["title"]} · Stand {snapshot["revision"]}', 'around_node_ids': notes}, 'frame')
            composer.update(state='saved', revision=snapshot['revision'], message='Als bearbeitbarer Ergebnisstand in Composer gespeichert.')
        except Exception:
            composer.update(state='uncertain', message='Übertragung nicht vollständig bestätigt. Arbeitsstand bleibt am Pi; bitte Composer prüfen, nicht erneut senden.')
        self._composer_status(binding, ident, composer, require_current=False)

    def _composer_status(self, binding, ident, composer, *, require_current=True):
        with self.lock, self.db() as db:
            raw = db.execute('SELECT data FROM drafts WHERE id=? AND owner=?', (ident, owner(binding))).fetchone()
            if not raw: return
            if require_current and binding != self.account(): raise ValueError('Konto geändert.')
            row = json.loads(raw[0]); row['composer'] = composer
            self._put(db, row)
