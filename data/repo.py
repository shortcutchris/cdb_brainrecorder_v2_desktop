"""
SQLite Repository für Session-Verwaltung
"""
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any


class SessionRepository:
    """Repository für Audio-Session CRUD-Operationen"""

    def __init__(self, db_path: str = "data/sessions.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialisiert die Datenbank und erstellt Tabellen falls nicht vorhanden"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    recorded_at TEXT NOT NULL,
                    duration_sec INTEGER DEFAULT 0,
                    path TEXT NOT NULL,
                    samplerate INTEGER DEFAULT 44100,
                    channels INTEGER DEFAULT 1,
                    notes TEXT DEFAULT ''
                )
            """)
            conn.commit()

        # Migration für neue Spalten
        self._migrate_db()

    def _migrate_db(self):
        """Fügt neue Spalten für Transkription hinzu (falls noch nicht vorhanden)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Prüfe welche Spalten existieren
            cursor.execute("PRAGMA table_info(sessions)")
            columns = [col[1] for col in cursor.fetchall()]

            # Füge fehlende Spalten hinzu
            if 'transcript_text' not in columns:
                conn.execute("ALTER TABLE sessions ADD COLUMN transcript_text TEXT")

            if 'transcript_tokens' not in columns:
                conn.execute("ALTER TABLE sessions ADD COLUMN transcript_tokens INTEGER")

            if 'transcription_status' not in columns:
                conn.execute("ALTER TABLE sessions ADD COLUMN transcription_status TEXT")

            conn.commit()

    def create(self, title: str, recorded_at: str, path: str,
               duration_sec: int = 0, samplerate: int = 44100,
               channels: int = 1, notes: str = '') -> int:
        """Erstellt eine neue Session und gibt die ID zurück"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO sessions (title, recorded_at, duration_sec, path,
                                     samplerate, channels, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (title, recorded_at, duration_sec, path, samplerate, channels, notes))
            conn.commit()
            return cursor.lastrowid

    def get_all(self, search_term: str = '') -> List[Dict[str, Any]]:
        """Holt alle Sessions, optional gefiltert nach Suchbegriff"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            if search_term:
                cursor = conn.execute("""
                    SELECT * FROM sessions
                    WHERE title LIKE ? OR notes LIKE ? OR transcript_text LIKE ?
                    ORDER BY recorded_at DESC
                """, (f'%{search_term}%', f'%{search_term}%', f'%{search_term}%'))
            else:
                cursor = conn.execute("""
                    SELECT * FROM sessions
                    ORDER BY recorded_at DESC
                """)

            sessions = [dict(row) for row in cursor.fetchall()]

            # Dateigröße für jede Session berechnen
            for session in sessions:
                if session.get('path'):
                    file_path = Path(session['path'])
                    try:
                        if file_path.exists():
                            session['file_size'] = file_path.stat().st_size
                        else:
                            session['file_size'] = 0
                    except Exception:
                        session['file_size'] = 0
                else:
                    session['file_size'] = 0

            return sessions

    def get_by_id(self, session_id: int) -> Optional[Dict[str, Any]]:
        """Holt eine Session anhand der ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def update(self, session_id: int, **kwargs):
        """Aktualisiert eine Session mit den übergebenen Feldern"""
        if not kwargs:
            return

        fields = ', '.join([f"{key} = ?" for key in kwargs.keys()])
        values = list(kwargs.values()) + [session_id]

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(f"UPDATE sessions SET {fields} WHERE id = ?", values)
            conn.commit()

    def delete(self, session_id: int) -> dict:
        """Löscht eine Session und die zugehörige Audio-Datei"""
        # Zuerst Session-Daten holen für Dateipfad
        session = self.get_by_id(session_id)

        # Datenbankeintrag löschen
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            conn.commit()

        # Audio-Datei löschen falls vorhanden
        if session and session.get('path'):
            file_path = Path(session['path'])
            try:
                if file_path.exists():
                    file_path.unlink()
                    return {"success": True, "file_deleted": True}
                return {"success": True, "file_deleted": False, "reason": "Datei existiert nicht"}
            except PermissionError:
                return {"success": True, "file_deleted": False, "reason": "Keine Berechtigung"}
            except Exception as e:
                return {"success": True, "file_deleted": False, "reason": str(e)}

        return {"success": True, "file_deleted": False, "reason": "Kein Pfad vorhanden"}

    def update_transcript(self, session_id: int, text: str, tokens: int, status: str = "completed"):
        """Aktualisiert Transkript einer Session"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE sessions
                SET transcript_text = ?,
                    transcript_tokens = ?,
                    transcription_status = ?
                WHERE id = ?
            """, (text, tokens, status, session_id))
            conn.commit()

    def set_transcription_status(self, session_id: int, status: str):
        """Setzt nur den Status (pending/completed/error)"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE sessions
                SET transcription_status = ?
                WHERE id = ?
            """, (status, session_id))
            conn.commit()

    def export_to_csv(self, output_path: str):
        """Exportiert alle Sessions als CSV"""
        import csv

        sessions = self.get_all()
        if not sessions:
            return

        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=sessions[0].keys())
            writer.writeheader()
            writer.writerows(sessions)
