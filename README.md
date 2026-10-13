# Corporate Digital Brain Desktop Recorder

## 0.5.11 – Mikrofon und Testplayer

Die Audioseite nutzt zwei feste Spalten: Mikrofon, Live-Pegel und ein Player im aktiven Theme links, geordnete Einrichtungsprüfungen rechts. Alte Testaufnahmen werden von einem aktuellen Eingangssignal unterschieden. [Prüfung und Screenshots](docs/audio-0.5.11/README.md).

## 0.5.10 – Einheitliche Touchansichten und dauerhafte Modellnachweise

Aktives Modell und Teststatus bleiben klar getrennt. Ergebnisse bleiben pro Modell gespeichert; die übernommenen Pi-Nachweise werden gegen Modell und Laufzeit geprüft. Header, Fußleisten, Auswahlfelder und Such-/Seitennavigation sind vereinheitlicht. Bibliothek und Queue zeigen vollständige Seiten. Siehe [Audit und Screenshots](docs/stable-models-0.5.10/README.md).


Eine Desktop-Anwendung zum Aufzeichnen, Verwalten und Wiedergeben von Audio-Sessions mit Raspberry Pi Touch-Optimierung.

## Aktueller Raspberry-Pi-Stand: Touch-Oberfläche 0.5.11

Der Pi verwendet die HTML-Studio-Oberfläche mit dem vorhandenen Python-Backend, der bisherigen Meeting-Datenbank und lokalen Whisper-/Ollama-Modellen. Installation, Autostart, isolierte Funktionsvorschau und Rückkehr zur bisherigen Oberfläche: [docs/STUDIO.md](docs/STUDIO.md). Gestaltung und Prüfungsumfang: [design-qa.md](design-qa.md). Die gemeinsame Python-Engine ist auf Version 0.2.6 gepinnt. Zustandsregeln und Entwurfswiederherstellung: [docs/STUDIO.md](docs/STUDIO.md).

Die Bibliothek bietet einen festen Rückweg „Zur Aufnahmeliste“ mit großer Touchfläche und eigener Positionsanzeige. CDB-Zusammenfassungen wiederholen abgeschnittene Antworten einmal mit größerem Ausgabebudget; unvollständige Texte bleiben Fehler. Prüfung mit einer Stunde synthetischem Audio: [Testbericht](docs/cdb-hour-0.5.5/README.md).

Neu in 0.5.9: Brain-Konto und KI & Modelle bündeln Anmeldung, Standardbereich und aktive Verarbeitung. Lokale und Online-Modelle lassen sich direkt mit synthetischen Daten testen und ausdrücklich aktivieren. [Prüfung und Screenshots](docs/brain-models-0.5.9/README.md).

Neu in 0.5.8: Kachelübersicht für Einstellungen, Unterseiten mit Rückweg statt Seitennavigation, eingerückte App-Icons und einheitliche Touch-Abstände. Standard-Zusammenfassungen prüfen Aufgaben, Namen und Fristen gegen wörtliche Transkriptbelege. Ergebnisse und Grenzen des frischen CDB-Stundentests: [Prüfbericht](docs/task-quality-0.5.8/README.md).

Die folgenden Abschnitte beschreiben auch historische Funktionen der Desktop-Anwendung. Für den aktuellen Pi gelten die lokalen Einrichtungsanweisungen in [docs/STUDIO.md](docs/STUDIO.md) und [docs/LOCAL_AI.md](docs/LOCAL_AI.md).

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
- **Raspberry Pi Optimierung**
  - Automatische Touch-optimierte UI auf ARM-Systemen
  - 24px breite Scrollbars für einfache Touch-Bedienung
  - 50px große Buttons für Finger-Bedienung
  - Kompaktes Layout für 1280x720 Displays
  - Fullscreen-Modus mit verstecktem Toggle (5x Logo klicken)
  - Autostart-Konfiguration für Kiosk-Systeme

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

### Desktop (Mac/Windows/Linux)

Starte die App mit:
```bash
./run.sh
```

Oder manuell:
```bash
source venv/bin/activate
python3 app.py
```

### Raspberry Pi (Touch-optimiert)

Die App erkennt automatisch Raspberry Pi (ARM-Architektur) und aktiviert:
- Touch-optimierte UI mit 24px Scrollbars
- 50px große Buttons für Finger-Bedienung
- Kompaktes Layout für 1280x720 Displays
- Automatischer Fullscreen-Modus

**Starten:**
```bash
./run.sh
```

**Fullscreen beenden:**
- 5x schnell auf das Logo klicken (links oben)
- F11-Taste drücken
- ESC-Taste drücken

**Autostart einrichten:**
```bash
./install-autostart.sh
```

Zum Deaktivieren:
```bash
./remove-autostart.sh
```

**Environment Variables:**
```bash
FULLSCREEN=false ./run.sh      # Kein Fullscreen
LAYOUT_MODE=desktop ./run.sh   # Desktop-Layout erzwingen
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

Die App kann als eigenständige Anwendung gebaut werden. **Wichtig**: Verwende das automatisierte Build-Skript, das die notwendigen Mikrofon-Berechtigungen korrekt setzt:

```bash
# App bauen (empfohlen - automatisiert)
./build_app.sh

# Gebaute App öffnen
open dist/CorporateDigitalBrainRecorder.app

# Optional: Installation in /Applications
cp -r dist/CorporateDigitalBrainRecorder.app /Applications/
```

### Manueller Build (nur falls notwendig)

Falls du manuell bauen möchtest:

```bash
# 1. App mit PyInstaller bauen
./venv/bin/pyinstaller AudioSessions.spec --clean

# 2. WICHTIG: Berechtigungen fixen (sonst funktioniert Mikrofon nicht!)
./fix_app_permissions.sh

# 3. App öffnen
open dist/CorporateDigitalBrainRecorder.app
```

**Warum das Fix-Skript notwendig ist:**
- PyInstaller überschreibt die `Info.plist` beim Build
- Die `NSMicrophoneUsageDescription` (Mikrofon-Berechtigung) geht verloren
- Das Fix-Skript fügt sie wieder hinzu und signiert die App mit Audio-Input Entitlements

### Build-Dateien

- `build_app.sh` - Kompletter automatisierter Build-Prozess
- `fix_app_permissions.sh` - Patcht Info.plist und signiert die App
- `entitlements.plist` - Entitlements für Mikrofon-Zugriff
- `AudioSessions.spec` - PyInstaller Konfiguration
- `Info.plist` - Basis Info.plist mit App-Metadaten

Die gebaute `.app` kann ohne Python-Installation verwendet werden.

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

### Mikrofon funktioniert nicht in gebauter .app

**Problem**: Die gebaute App (`.app` Datei) zeigt keinen Mikrofon-Pegel / keine Waveform, obwohl es beim Start über Python funktioniert.

**Ursache**:
- PyInstaller überschreibt beim Build die `Info.plist`
- Die `NSMicrophoneUsageDescription` (Mikrofon-Berechtigung) fehlt in der gebauten App
- macOS verweigert daher den Mikrofon-Zugriff

**Lösung**:
```bash
# Option 1: Automatisiertes Build-Skript verwenden (empfohlen)
./build_app.sh

# Option 2: Manuell fixen nach dem Build
./venv/bin/pyinstaller AudioSessions.spec --clean
./fix_app_permissions.sh
```

**Verifikation**:
```bash
# Prüfe ob NSMicrophoneUsageDescription in der gebauten App enthalten ist
/usr/libexec/PlistBuddy -c "Print :NSMicrophoneUsageDescription" \
  dist/CorporateDigitalBrainRecorder.app/Contents/Info.plist

# Prüfe Code-Signing Entitlements
codesign -d --entitlements - dist/CorporateDigitalBrainRecorder.app
```

**Wenn das Problem weiterhin besteht**:
1. Öffne Systemeinstellungen → Sicherheit & Datenschutz → Mikrofon
2. Entferne "Corporate Digital Brain Desktop Recorder" aus der Liste (falls vorhanden)
3. Starte die App neu - macOS wird erneut nach Mikrofon-Berechtigung fragen
4. Erlaube den Zugriff

## Lizenz

MIT

## Recorder Studio 0.5.0: Firmenanmeldung und CDB

Die Pi-Oberfläche bietet direkt anwählbare Einstellungsseiten sowie Microsoft-Anmeldung,
getrennt wählbare lokale/CDB-Transkription und Zusammenfassung und die bewusste
Textübertragung in eine Knowledge Area. Lokale Aufnahme und Verarbeitung bleiben verfügbar.
Bedienung, Datenschutzgrenzen, Auslieferungsnachweise und noch offene Live-Abnahme:
[docs/cdb-integration/README.md](docs/cdb-integration/README.md).

### Studio 0.5.1: Standardbereich für „Ins Brain“

Nach der Microsoft-Anmeldung werden die Knowledge Areas automatisch geladen. Unter **Einstellungen → Verbindung** einen Standardbereich wählen; die Auswahl bleibt für dieses Firmenkonto gespeichert und ist dort oder unter **Knowledge Areas** jederzeit änderbar. Am Meeting öffnet **Ins Brain übertragen …** ein eigenes Touchfenster mit vorbelegtem Ziel. Ein dort gewählter anderer Bereich gilt nur für dieses Meeting. **Jetzt übertragen** startet den Versand. Aufnahme und lokale Verarbeitung bleiben unabhängig davon verfügbar.

## Studio 0.5.2

[Rechte Arbeitsansichten, Touchbedienung und Meetingaufgaben](docs/workspace-0.5.2/README.md): Bibliothek und Einstellungen öffnen neben der Aufnahme; Zusammenfassung bietet Meetingprotokoll oder vereinbarte Aufgaben statt Übersetzung.

## Stummschaltung, Pause und Bluetooth (Studio 0.5.17)

Während der Aufnahme stehen unter der Pegelanzeige zwei Touchbuttons bereit:
**Mikro stumm** speichert Stille, die Aufnahmedauer läuft weiter.
**Pause** speichert keine Audiodaten; **Fortsetzen** führt dieselbe Aufnahme weiter.
Ein stummgeschaltetes Mikrofon bleibt auch nach dem Fortsetzen stumm, bis es ausdrücklich eingeschaltet wird.
Bibliothek, Warteschlange und Einstellungen bleiben während einer Pause gesperrt.
**Stoppen** schließt die Aufnahme auch im Pausenzustand ab und stellt genau einen Auftrag in die Warteschlange.
Notizen können weiterhin bearbeitet werden. Die App-Stummschaltung steuert noch keine Hardware-LEDs.

Verbundene Bluetooth-Mikrofone erscheinen zusätzlich in der Mikrofonauswahl, wenn
PipeWire/PulseAudio sie im Headset-/Freisprechprofil als Quelle bereitstellt.
Bloßes Pairing oder ein reines A2DP-Wiedergabeprofil reicht nicht. Die App übernimmt
keine Kopplung und schaltet Profile nicht selbstständig um. Bluetooth-Lautsprecher
werden bereits über die Lautsprecherauswahl angeboten, sobald sie verbunden sind.

Details, Tests und ReSpeaker-Diagnose: [Aufnahmesteuerung 0.5.17](docs/capture-0.5.17/README.md).

## ReSpeaker XVF3800 am Raspberry Pi

[Anschluss, erneutes Verbinden, Firmware und Fehlerbehebung](docs/respeaker.md).
Die Firmware bleibt im Mikrofon gespeichert: Beim erneuten Anschließen ist **kein erneutes Flashen** nötig. Ein neues Gerät mit I²S-Firmware muss dagegen einmalig auf USB umgestellt werden. Die Anleitung enthält die geprüfte Version, Safe Mode, Mikrofontest, Mute/Pause, LED-Status und Diagnosebefehle.
