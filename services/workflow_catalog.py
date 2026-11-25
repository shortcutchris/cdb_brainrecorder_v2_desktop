"""Versioned, declarative conversation recipes. No scripts or tool credentials.

Repository recipes are reviewed with the release. Local proposals are inert until
an operator approves their exact digest and activates them. A future agent may
use propose(); neither approval nor activation is exposed to voice/HTTP clients.
"""
import copy
import contextlib
import hashlib
import json
import re
import sqlite3
import time
import unicodedata
from pathlib import Path

ID = re.compile(r'^[a-z][a-z0-9_]{0,47}$')
LEGACY_IDS = ('interview', 'brainstorming')
DEFINITIONS = Path(__file__).with_name('workflow_definitions')
FIELDS = {'schema_version', 'id', 'version', 'name', 'description', 'voice_aliases',
          'explanation', 'opening_question', 'moderation', 'default_minutes', 'phases', 'sections', 'outputs'}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def text(value, limit):
    return isinstance(value, str) and 0 < len(value.strip()) <= limit and not any(ord(c) < 32 and c not in '\n\t' for c in value)


def validate(value):
    """Strict schema; declarations can narrow existing outputs, never add tools."""
    if not isinstance(value, dict) or set(value) != FIELDS:
        raise ValueError('Workflow enthält fehlende oder unbekannte Felder.')
    if type(value['schema_version']) is not int or value['schema_version'] != 1:
        raise ValueError('Nicht unterstützte Workflow-Schemaversion.')
    if not isinstance(value['id'], str) or not ID.fullmatch(value['id']) or value['id'] == 'free_talk':
        raise ValueError('Ungültige oder reservierte Workflow-ID.')
    if type(value['version']) is not int or not 1 <= value['version'] <= 100000:
        raise ValueError('Workflow-Version muss eine positive ganze Zahl sein.')
    for field, limit in [('name', 60), ('description', 180), ('explanation', 1200),
                         ('opening_question', 400), ('moderation', 3000)]:
        if not text(value[field], limit): raise ValueError('Ungültiger Workflow-Text: ' + field)
    if type(value['default_minutes']) is not int or not 5 <= value['default_minutes'] <= 20:
        raise ValueError('Zeitrahmen muss zwischen 5 und 20 Minuten liegen.')
    aliases = value['voice_aliases']
    if not isinstance(aliases, list) or not 1 <= len(aliases) <= 8 or any(not text(a, 80) for a in aliases):
        raise ValueError('Ein bis acht kurze Sprachbezeichnungen angeben.')
    for field, extra, maximum in [('phases', 'instruction', 8), ('sections', 'hint', 8)]:
        rows = value[field]
        if not isinstance(rows, list) or not 2 <= len(rows) <= maximum:
            raise ValueError('Zwei bis acht ' + field + ' angeben.')
        ids = []
        for row in rows:
            if (not isinstance(row, dict) or set(row) != {'id', 'label', extra}
                    or not isinstance(row['id'], str) or not ID.fullmatch(row['id'])
                    or not text(row['label'], 60) or not text(row[extra], 700)):
                raise ValueError('Ungültiger Eintrag in ' + field)
            ids.append(row['id'])
        if len(set(ids)) != len(ids): raise ValueError('Doppelte IDs in ' + field)
    if value['sections'][0]['id'] != 'goal': raise ValueError('Erstes Ergebnisfeld muss goal sein.')
    if value['phases'][0]['id'] != 'opening' or value['phases'][-1]['id'] != 'closing':
        raise ValueError('Phasen müssen mit opening beginnen und mit closing enden.')
    outputs = value['outputs']
    if not isinstance(outputs, list) or any(o not in ('composer', 'brain') for o in outputs) or len(set(outputs)) != len(outputs):
        raise ValueError('Nur die vorhandenen Ausgaben composer und brain sind erlaubt.')
    if len(json.dumps(value)) > 24000: raise ValueError('Workflow ist zu groß.')
    return copy.deepcopy(value)


def load_definition(path):
    def pairs(items):
        row = {}
        for key, value in items:
            if key in row: raise ValueError('Doppelter JSON-Schlüssel: ' + key)
            row[key] = value
        return row
    raw = Path(path).read_bytes()
    if len(raw) > 32000: raise ValueError('Workflow-Datei ist zu groß.')
    return validate(json.loads(raw, object_pairs_hook=pairs))


def summary(definition):
    return {k: copy.deepcopy(definition[k]) for k in
            ('id', 'version', 'name', 'description', 'voice_aliases', 'default_minutes')}


def labels(definition, kind='sections'):
    return {r['id']: r['label'] for r in definition[kind]}


class WorkflowCatalog:
    def __init__(self, root, definitions=DEFINITIONS):
        self.builtins = {}
        for path in sorted(Path(definitions).glob('*.json')):
            definition = load_definition(path)
            if definition['id'] in self.builtins: raise ValueError('Doppelte mitgelieferte Workflow-ID.')
            self.builtins[definition['id']] = definition
        self.path = Path(root) / 'workflow-catalog.sqlite3'
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.db() as db:
            db.execute('CREATE TABLE IF NOT EXISTS proposals (digest TEXT PRIMARY KEY, data TEXT NOT NULL, origin TEXT NOT NULL, state TEXT NOT NULL, reviewer TEXT, created REAL NOT NULL, reviewed REAL)')
            db.execute('CREATE TABLE IF NOT EXISTS active (id TEXT PRIMARY KEY, digest TEXT)')
        self.path.chmod(0o600)
        self._check_names(self.definitions())

    @contextlib.contextmanager
    def db(self):
        db = sqlite3.connect(self.path, timeout=10)
        try:
            with db: yield db
        finally: db.close()

    @staticmethod
    def _check_names(rows):
        seen = {'free_talk': 'free_talk', 'freies gespräch': 'free_talk'}
        for row in rows:
            for alias in [row['id'], row['name'], *row['voice_aliases']]:
                key = unicodedata.normalize('NFKC', alias).strip().casefold()
                if key in seen and seen[key] != row['id']: raise ValueError('Mehrdeutige Sprachbezeichnung: ' + alias)
                seen[key] = row['id']
        if len(rows) > 32: raise ValueError('Höchstens 32 aktive Workflows.')
        if len(json.dumps([summary(row) for row in rows])) > 48000:
            raise ValueError('Workflow-Katalog ist zu groß. Beschreibungen oder Sprachbezeichnungen kürzen.')

    def definitions(self):
        rows = copy.deepcopy(self.builtins)
        with self.db() as db:
            for ident, sha in db.execute('SELECT id,digest FROM active'):
                if sha is None: rows.pop(ident, None); continue
                stored = db.execute("SELECT data FROM proposals WHERE digest=? AND state='approved'", (sha,)).fetchone()
                if not stored: raise ValueError('Aktivierter Workflow ist nicht freigegeben.')
                value = validate(json.loads(stored[0]))
                if value['id'] != ident or digest(value) != sha: raise ValueError('Workflow-Prüfsumme stimmt nicht.')
                rows[ident] = value
        return sorted(rows.values(), key=lambda d: (d['id'] not in LEGACY_IDS, d['name']))

    def list(self):
        return [summary(d) for d in self.definitions()]

    def get(self, ident):
        for row in self.definitions():
            if row['id'] == ident: return row
        raise ValueError('Workflow ist nicht verfügbar oder nicht aktiviert.')

    def propose(self, definition, *, origin='operator'):
        """Future agent boundary: stores an inert proposal, never executes it."""
        value = validate(definition)
        if origin not in ('operator', 'agent'): raise ValueError('Ungültiger Ursprung.')
        sha = digest(value)
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            known = list(self.builtins.values()) + [json.loads(r[0]) for r in db.execute('SELECT data FROM proposals')]
            for other in known:
                if (other['id'], other['version']) == (value['id'], value['version']) and digest(other) != sha:
                    raise ValueError('Diese Version existiert bereits. Neue Versionsnummer verwenden.')
            db.execute("INSERT OR IGNORE INTO proposals VALUES (?,?,?,'draft',NULL,?,NULL)", (sha, canonical(value), origin, time.time()))
        return sha

    def proposals(self):
        with self.db() as db:
            return [dict(digest=r[0], definition=json.loads(r[1]), origin=r[2], state=r[3], reviewer=r[4])
                    for r in db.execute('SELECT digest,data,origin,state,reviewer FROM proposals ORDER BY created')]

    def approve(self, sha, *, reviewer):
        if not text(reviewer, 100): raise ValueError('Prüfende Person angeben.')
        with self.db() as db:
            row = db.execute('SELECT data FROM proposals WHERE digest=?', (sha,)).fetchone()
            if not row or digest(validate(json.loads(row[0]))) != sha: raise ValueError('Unbekannter oder geänderter Entwurf.')
            db.execute("UPDATE proposals SET state='approved',reviewer=?,reviewed=? WHERE digest=?", (reviewer, time.time(), sha))

    def activate(self, sha):
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute("SELECT data FROM proposals WHERE digest=? AND state='approved'", (sha,)).fetchone()
            if not row: raise ValueError('Nur geprüfte Entwürfe können aktiviert werden.')
            value = validate(json.loads(row[0]))
            if digest(value) != sha: raise ValueError('Workflow-Prüfsumme stimmt nicht.')
            self._check_names([d for d in self.definitions() if d['id'] != value['id']] + [value])
            db.execute('INSERT OR REPLACE INTO active VALUES (?,?)', (value['id'], sha))

    def retire(self, ident):
        self.get(ident)
        with self.db() as db: db.execute('INSERT OR REPLACE INTO active VALUES (?,NULL)', (ident,))


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Gesprächs-Workflows prüfen und verwalten (nur Betreiberzugriff).')
    parser.add_argument('--root', type=Path, required=True, help='Privates Recorder-Datenverzeichnis')
    sub = parser.add_subparsers(dest='action', required=True)
    for name in ('list', 'proposals'): sub.add_parser(name)
    for name in ('validate', 'propose'):
        p = sub.add_parser(name); p.add_argument('file', type=Path)
        if name == 'propose': p.add_argument('--origin', choices=['operator', 'agent'], default='operator')
    p = sub.add_parser('approve'); p.add_argument('digest'); p.add_argument('--reviewer', required=True)
    p = sub.add_parser('activate'); p.add_argument('digest')
    p = sub.add_parser('retire'); p.add_argument('id')
    args = parser.parse_args()
    try:
        catalog = WorkflowCatalog(args.root)
        if args.action == 'validate': result = {'valid': True, 'digest': digest(load_definition(args.file))}
        elif args.action == 'propose': result = {'digest': catalog.propose(load_definition(args.file), origin=args.origin), 'state': 'draft'}
        elif args.action == 'approve': catalog.approve(args.digest, reviewer=args.reviewer); result = {'state': 'approved'}
        elif args.action == 'activate': catalog.activate(args.digest); result = {'state': 'active'}
        elif args.action == 'retire': catalog.retire(args.id); result = {'state': 'retired'}
        else: result = getattr(catalog, args.action)()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ValueError, OSError) as exc: parser.exit(2, str(exc) + '\n')


if __name__ == '__main__': main()
