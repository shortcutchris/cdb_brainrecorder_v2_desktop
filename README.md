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
- **AI-Integration mit OpenAI**
  - Automatische Transkription mit gpt-4o-transcribe
  - Text-Transformation mit GPT-5 (Zusammenfassen, Übersetzen, Strukturieren)
  - Hintergrund-Verarbeitung ohne UI-Blockierung

## OpenAI Integration

Die App unterstützt automatische Transkription und AI-gestützte Textverarbeitung.

### Setup

1. **API-Key konfigurieren**: Öffne die Einstellungen (⚙️ in der Toolbar) und trage deinen OpenAI API-Key ein
2. Der API-Key wird sicher in `~/.config/audio_sessions/settings.json` gespeichert

### Transkription

Die Transkription verwendet das Modell **gpt-4o-transcribe** (Nachfolger von whisper-1):

```python
# Modell: gpt-4o-transcribe
# Response Format: json (nicht verbose_json!)
# Sprache: auto-detect oder manuell (de, en, etc.)
# Prompt: "Audio Sessions, Transkription, Notizen"
```

**Wichtig**: Das `gpt-4o-transcribe` Modell unterstützt nur `response_format="json"` oder `"text"`, nicht `"verbose_json"`. Die Response enthält:
- `text`: Der transkribierte Text
- `language`: Erkannte Sprache (falls verfügbar)
- `duration`: Audio-Länge (falls verfügbar)

**Verwendung**:
1. Wähle eine Session in der Tabelle
2. Öffne den AI-Tab im Detail-Bereich
3. Klicke auf "Transkribieren"
4. Die Transkription läuft im Hintergrund (Worker-Thread)
5. Status wird in der Tabelle angezeigt (🔄 laufend, ✓ fertig)

### Text-Transformation mit GPT-5

Die Text-Transformation verwendet **GPT-5** mit dem Chat Completions API:

```python
# Modell: gpt-5
# API: Chat Completions (client.chat.completions.create)
# Parameter: reasoning_effort (minimal, low, medium, high)
# Parameter: verbosity (low, medium, high) - wird im Prompt verarbeitet
```

**Wichtig**:
- GPT-5 verwendet die **Chat Completions API**, nicht die Responses API
- Der Parameter `reasoning_effort` steuert die Denktiefe des Modells
- `max_completion_tokens` statt `max_tokens` verwenden
- Response-Struktur: `response.choices[0].message.content`

**Verfügbare Transformationen**:
1. **Zusammenfassen**: Erstellt eine prägnante Zusammenfassung
2. **Übersetzen**: Übersetzt ins Englische
3. **Strukturieren**: Gliedert den Text in übersichtliche Abschnitte

**Verwendung**:
1. Transkribiere zuerst eine Session (siehe oben)
2. Wähle eine Transformation (Zusammenfassen/Übersetzen/Strukturieren)
3. Passe optional Reasoning Effort und Verbosity an
4. Klicke auf "Ausführen"
5. Das Ergebnis erscheint im unteren Textfeld

**Fallback**: Falls GPT-5 nicht verfügbar ist (z.B. API-Fehler), wird automatisch auf GPT-4o mit äquivalenten Parametern zurückgegriffen.

### Technische Details

**Service-Architektur**:
- `services/audio_session_service.py`: OpenAI API-Aufrufe
- `services/workers.py`: Qt QThread Worker für async Verarbeitung
- Cache-System für Transkriptionen (verhindert doppelte API-Calls)

**Python 3.9 Kompatibilität**:
```python
# Statt: dict | None (Python 3.10+)
# Verwenden: Optional[dict] (Python 3.9)
from typing import Optional, Dict, Any
```

**GPT-5 vs GPT-4o**:
| Feature | GPT-5 | GPT-4o (Fallback) |
|---------|-------|-------------------|
| API | Chat Completions | Chat Completions |
| Reasoning | `reasoning_effort` Parameter | Gemappt auf `temperature` |
| Verbosity | Im Prompt | Im Prompt |
| Max Tokens | `max_completion_tokens` | `max_tokens` |

**Fehlerbehandlung**:
- Netzwerkfehler werden abgefangen und im UI angezeigt
- API-Fehler zeigen Details in der Terminal-Ausgabe
- Transkriptionsstatus wird in der Datenbank persistiert

## Technologie

- **Python 3.9+** (getestet mit Python 3.9.6)
- **PySide6 (Qt)** für die GUI
- **sounddevice + soundfile** für Audio I/O
- **SQLite** für die Datenbank
- **OpenAI SDK** (>=1.57.0) für AI-Features
  - gpt-4o-transcribe für Transkription
  - GPT-5 für Text-Transformation

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
# Mit virtuellem Environment (empfohlen)
./venv/bin/python3 app.py

# Oder wenn venv aktiviert ist
python app.py
```

**Wichtig**: Stelle sicher, dass die OpenAI SDK im virtuellen Environment installiert ist. Falls `ModuleNotFoundError: No module named 'openai'` erscheint:
```bash
./venv/bin/pip install "openai>=1.57.0"
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
├── app.py                          # Main-Einstiegspunkt
├── recorder.py                     # Audio-Recorder Klasse
├── ui/
│   ├── main_window.py              # Hauptfenster
│   ├── session_form.py             # Session-Formular
│   ├── table_widget.py             # Sessions-Tabelle
│   ├── ai_view.py                  # AI-Integration UI
│   ├── settings_dialog.py          # Einstellungen-Dialog
│   └── player_widget.py            # Audio-Player
├── services/
│   ├── audio_session_service.py    # OpenAI API Service
│   ├── workers.py                  # Qt Worker für async AI-Tasks
│   └── settings_manager.py         # Settings Management
├── data/
│   ├── repo.py                     # SQLite Repository
│   └── sessions.db                 # Datenbank (wird automatisch erstellt)
├── recordings/                     # Aufnahmen (wird automatisch erstellt)
├── translations/                   # i18n Übersetzungen
└── requirements.txt                # Dependencies
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

## Troubleshooting

### OpenAI API Fehler

**Problem**: `ModuleNotFoundError: No module named 'openai'`
```bash
# Lösung: OpenAI SDK im virtuellen Environment installieren
./venv/bin/pip install "openai>=1.57.0"

# App mit venv starten
./venv/bin/python3 app.py
```

**Problem**: `TypeError: unsupported operand type(s) for |: 'type' and 'NoneType'`
- **Ursache**: Python 3.9 unterstützt keine Union Types mit `|` Operator
- **Lösung**: Code verwendet jetzt `Optional[dict]` statt `dict | None`

**Problem**: `response_format 'verbose_json' is not compatible with model 'gpt-4o-transcribe'`
- **Ursache**: Das neue gpt-4o-transcribe Modell unterstützt kein `verbose_json` Format
- **Lösung**: Code verwendet jetzt `response_format="json"`

**Problem**: `GPT-5 nicht verfügbar, Fallback auf GPT-4o`
- **Ursache**: Frühere Version versuchte die Responses API zu nutzen
- **Lösung**: Code verwendet jetzt Chat Completions API für GPT-5
- **Parameter**: `reasoning_effort`, `max_completion_tokens`
- **Response**: `response.choices[0].message.content`

**Problem**: `'NoneType' object is not subscriptable` bei Transformation
- **Ursache**: Fehlerhafte Zugriffe auf Responses API Struktur
- **Lösung**: Umstellung auf Chat Completions API mit korrekter Response-Struktur

### API-Key Konfiguration

Falls die AI-Features nicht funktionieren:
1. Öffne Einstellungen (⚙️)
2. Trage deinen OpenAI API-Key ein
3. Speichere und starte die App neu
4. Prüfe die Terminal-Ausgabe auf Fehlermeldungen

## Lizenz

MIT
