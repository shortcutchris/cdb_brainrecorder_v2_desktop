# Audio Sessions - Desktop App

Eine Desktop-Anwendung zum Aufzeichnen, Verwalten und Wiedergeben von Audio-Sessions.

## Features

- **Audio-Aufnahme** mit Live-Pegelanzeige und Laufzeit-Anzeige
- **Audio-Wiedergabe** mit Play/Pause/Stop und Fortschrittsbalken
- **CRUD-Verwaltung** für Sessions (Create, Read, Update, Delete)
- **Geräteauswahl** zwischen allen verfügbaren Mikrofonen
- **Suchfunktion** nach Titel und Notizen
- **CSV-Export** der Session-Liste
- **Datei öffnen** im Standard-Audio-Player

## Technologie

- **Python 3.11+**
- **PySide6 (Qt)** für die GUI
- **sounddevice + soundfile** für Audio I/O
- **SQLite** für die Datenbank

## Installation

1. Erstelle ein virtuelles Environment (empfohlen):
```bash
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# oder
venv\Scripts\activate  # Windows
```

2. Installiere die Dependencies:
```bash
pip install -r requirements.txt
```

## Verwendung

Starte die App mit:
```bash
python app.py
```

### Aufnahme

1. Wähle dein Mikrofon aus dem Dropdown
2. Klicke auf "Aufnahme starten"
3. Beobachte den Live-Pegel und die Laufzeit
4. Klicke auf "Aufnahme stoppen"
5. Die Session wird automatisch in der Datenbank gespeichert

### Session-Verwaltung

- **Suchen**: Nutze das Suchfeld in der Toolbar
- **Auswählen**: Klicke auf eine Session in der Tabelle
- **Bearbeiten**: Ändere Titel und Notizen im Formular rechts
- **Speichern**: Klicke auf "Speichern"
- **Löschen**: Wähle eine Session und klicke auf "Löschen" in der Toolbar
- **CSV-Export**: Klicke auf "CSV Export" in der Toolbar
- **Datei öffnen**: Wähle eine Session und klicke auf "Datei öffnen"

## Projektstruktur

```
audio_sessions/
├── app.py                 # Main-Einstiegspunkt
├── recorder.py            # Audio-Recorder Klasse
├── ui/
│   ├── main_window.py     # Hauptfenster
│   ├── session_form.py    # Session-Formular
│   └── table_widget.py    # Sessions-Tabelle
├── data/
│   ├── repo.py            # SQLite Repository
│   └── sessions.db        # Datenbank (wird automatisch erstellt)
├── recordings/            # Aufnahmen (wird automatisch erstellt)
└── requirements.txt       # Dependencies
```

## macOS Hinweis

Bei macOS muss die App Mikrofonberechtigungen erhalten. Beim ersten Start wird ein Dialog angezeigt. Falls die Berechtigung verweigert wurde, kann sie in den Systemeinstellungen unter "Sicherheit & Datenschutz" → "Mikrofon" aktiviert werden.

## Packaging / Distribution

Die App kann als eigenständige Anwendung gebaut werden:

```bash
# App bauen
pyinstaller AudioSessions.spec --clean

# Gebaute App öffnen
open dist/AudioSessions.app
```

Die gebaute `.app` kann in den `/Applications` Ordner verschoben und ohne Python-Installation verwendet werden.

Detaillierte Anleitung: siehe [BUILD.md](BUILD.md)

## Lizenz

MIT
