"""Native session mapping; all inference lives in pinned shared meeting_recorder."""
import json
import threading
from pathlib import Path
from datetime import datetime
from meeting_recorder.desktop import DesktopEngine


class LocalController:
    def __init__(self, repo, root, **kwargs):
        self.lock = threading.RLock()
        self.repo = repo
        self.engine = DesktopEngine(root, **kwargs)
        # Legacy transient workers have no durable job after this engine takes over.
        # Preserve all content; expose an actionable interruption instead of a stale spinner.
        with self.repo.connection() as db:
            db.execute("UPDATE sessions SET transcription_status='failed', local_error=? WHERE local_job_id IS NULL AND transcription_status IN ('pending','processing','transcribing','summarizing')",
                       ('Frühere Verarbeitung wurde unterbrochen. In der KI-Ansicht Wiederholen wählen.',))
        self.sync()

    def sync(self):
        with self.lock:
            return self._sync()

    def _sync(self):
        # Immutable mapping, never depend on the selected UI row.
        sessions = {s.get('local_job_id'): s for s in self.repo.get_all() if s.get('local_job_id')}
        with self.engine.store.db() as db:
            db.execute('CREATE TABLE IF NOT EXISTS hidden_jobs (id TEXT PRIMARY KEY)')
            hidden = {r[0] for r in db.execute('SELECT id FROM hidden_jobs')}
        for job in self.engine.store.list():
            if job['id'] in hidden: continue
            ident = job['id']
            session = sessions.get(ident)
            if not session:
                sid = self.repo.create(job['title'], datetime.fromtimestamp(job['created']).isoformat(),
                       str(self.engine.store.folder(ident)/'audio.wav'), samplerate=16000)
                self.repo.update(sid, local_job_id=ident)
            else:
                sid = session['id']
            result = self.engine.result(ident)
            changes = dict(transcription_status=job['state'], local_error=job['error'],
                           local_metrics=job['metrics'], duration_sec=int(job['duration']))
            # Completed model artefacts are immutable audit data. Import them once,
            # then preserve the user's edits in the session database on every poll/restart.
            current = self.repo.get_by_id(sid)
            transitioning = current.get('transcription_status') != job['state']
            if result['transcript'] and transitioning:
                changes['transcript_text'] = result['transcript']
            if result['summary'] and transitioning:
                changes['summary_text'] = result['summary']
            # Avoid unnecessary WAL/SD writes on each UI poll.
            changes = {k:v for k,v in changes.items() if current.get(k) != v}
            if changes: self.repo.update(sid, **changes)

    def process(self, sid, prompt='', reuse_transcript=True):
        with self.lock:
            return self._process(sid, prompt, reuse_transcript)

    def _process(self, sid, prompt='', reuse_transcript=True):
        session = self.repo.get_by_id(sid)
        if not session: raise ValueError('Meeting fehlt.')
        old = session.get('local_job_id')
        if old and self.engine.store.get(old)['state'] in ('importing','recording','queued','transcribing','summarizing'):
            raise ValueError('Dieses Meeting wird bereits verarbeitet.')
        ident = self.engine.enqueue(session['path'], session['title'],
                   session.get('transcript_text') if reuse_transcript else None, prompt)
        # Archive old mapping; its job stays preserved but must not resurrect duplicate sessions.
        if old:
            with self.engine.store.db() as db:
                db.execute('CREATE TABLE IF NOT EXISTS hidden_jobs (id TEXT PRIMARY KEY)')
                db.execute('INSERT OR IGNORE INTO hidden_jobs VALUES(?)', (old,))
        self.repo.update(sid, local_job_id=ident, transcription_status='importing', local_error='')
        return ident

    def delete(self, sid):
        """Prevent a deleted UI row from being recreated by a preserved queue job."""
        with self.lock:
            session=self.repo.get_by_id(sid)
            if not session:raise ValueError('Meeting fehlt.')
            ident=session.get('local_job_id')
            if ident:
                job=self.engine.store.get(ident)
                if job['state'] not in ('completed','failed'):
                    raise ValueError('Aufnahme oder Verarbeitung zuerst abschließen.')
                with self.engine.store.db() as db:
                    db.execute('CREATE TABLE IF NOT EXISTS hidden_jobs (id TEXT PRIMARY KEY)')
                    db.execute('INSERT OR IGNORE INTO hidden_jobs VALUES(?)',(ident,))
            return self.repo.delete(sid)
