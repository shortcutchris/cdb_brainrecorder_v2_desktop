# Windows Build-Anleitung - Corporate Digital Brain Recorder

Diese Anleitung beschreibt, wie Sie die App für Windows als eigenständige `.exe` Anwendung bauen.

## Voraussetzungen

### Auf Windows-System benötigt:

1. **Python 3.9 oder höher**
   - Download: https://www.python.org/downloads/
   - ✅ Bei Installation: "Add Python to PATH" aktivieren!

2. **ffmpeg & ffprobe** (für Audio-Transkription)
   - Download: https://github.com/BtbN/FFmpeg-Builds/releases
   - Laden Sie: `ffmpeg-master-latest-win64-gpl.zip`
   - Extrahieren Sie: `ffmpeg.exe` und `ffprobe.exe`
   - **Option A (empfohlen):** Zum PATH hinzufügen
   - **Option B:** Später in `dist/CorporateDigitalBrainRecorder/` kopieren

3. **Git** (optional, zum Klonen des Repos)
   - Download: https://git-scm.com/download/win

## Build-Prozess

### Schritt 1: Repository auf Windows-Maschine bringen

**Option A - Mit Git:**
```cmd
git clone <repository-url>
cd cdb_brainrecorder_v2_desktop
```

**Option B - Manuell:**
- Kopieren Sie den gesamten Projektordner auf die Windows-Maschine
- Per USB-Stick, Netzwerk, oder Cloud-Sync

### Schritt 2: Build ausführen

```cmd
cd path\to\cdb_brainrecorder_v2_desktop
build_windows.bat
```

Das Script führt automatisch aus:
1. ✅ Prüft Python-Installation
2. ✅ Erstellt virtuelles Environment
3. ✅ Installiert alle Dependencies
4. ✅ Prüft ffmpeg (Warnung falls nicht vorhanden)
5. ✅ Löscht alten Build
6. ✅ Baut App mit PyInstaller

**Dauer:** Ca. 3-5 Minuten (erste Build), 1-2 Minuten (nachfolgende Builds)

### Schritt 3: ffmpeg kopieren (falls nicht im PATH)

Falls ffmpeg NICHT im PATH ist:

```cmd
copy C:\path\to\ffmpeg.exe dist\CorporateDigitalBrainRecorder\
copy C:\path\to\ffprobe.exe dist\CorporateDigitalBrainRecorder\
```

## Ergebnis

Nach erfolgreichem Build:

```
dist/
└── CorporateDigitalBrainRecorder/
    ├── CorporateDigitalBrainRecorder.exe  ← Hauptprogramm
    ├── _internal/                         ← Python Runtime + Libraries
    ├── icon.png                           ← App Icon
    ├── translations/                      ← Sprachdateien (DE/EN)
    ├── ffmpeg.exe                         ← (falls manuell kopiert)
    └── ffprobe.exe                        ← (falls manuell kopiert)
```

**Größe:** Ca. 200-250 MB (typisch für PySide6-Apps mit Audio-Libraries)

## App starten

```cmd
dist\CorporateDigitalBrainRecorder\CorporateDigitalBrainRecorder.exe
```

Oder per Doppelklick auf die `.exe` Datei.

## Test-Checkliste

Nach dem Build bitte **alle** folgenden Funktionen testen:

### 1. ✅ App-Start
- [ ] App startet ohne Fehler
- [ ] Hauptfenster erscheint
- [ ] Splash Screen wird angezeigt
- [ ] Keine Fehlermeldungen in der Konsole

### 2. ✅ Mikrofonauswahl
- [ ] Dropdown zeigt verfügbare Windows-Mikrofone
- [ ] Mikrofon kann ausgewählt werden
- [ ] Pegel-Anzeige reagiert auf Audio-Input

### 3. ✅ Audio-Aufnahme
- [ ] "Aufnahme starten" Button funktioniert
- [ ] Aufnahme läuft (roter Button, Waveform sichtbar)
- [ ] Dauer wird angezeigt
- [ ] "Aufnahme stoppen" speichert Session
- [ ] WAV-Datei wird erstellt in: `%APPDATA%\AudioSessions\recordings\`

**Speicherort prüfen:**
```cmd
explorer %APPDATA%\AudioSessions\recordings
```

### 4. ✅ Datenbank & Tabelle
- [ ] Session erscheint in der Tabelle
- [ ] ID, Titel, Datum, Dauer werden angezeigt
- [ ] Dateigröße wird korrekt berechnet
- [ ] Sessions.db existiert in: `%APPDATA%\AudioSessions\data\`

**Datenbank prüfen:**
```cmd
explorer %APPDATA%\AudioSessions\data
```

### 5. ✅ Audio-Player
- [ ] Session in Tabelle auswählen
- [ ] Player lädt Audio-Datei
- [ ] Play/Pause/Stop Buttons funktionieren
- [ ] Seek-Slider funktioniert
- [ ] Lautstärke-Regler funktioniert

### 6. ✅ Löschen
- [ ] Session auswählen
- [ ] "Löschen" Button klicken
- [ ] Bestätigungsdialog erscheint
- [ ] Nach Bestätigung: Session UND Audio-Datei werden gelöscht
- [ ] Datei verschwindet aus `recordings/` Ordner

### 7. ✅ Transkription (WICHTIG für ffmpeg-Test!)
- [ ] Session auswählen → "KI-Funktionen" Button
- [ ] AI-View öffnet sich
- [ ] "Transkription starten" Button klicken
- [ ] OpenAI API Key eingegeben (in Einstellungen)
- [ ] Transkription läuft ohne "Datei nicht gefunden" Fehler
- [ ] **Bei großen Dateien:** Progress "X/Y" Chunks wird angezeigt
- [ ] Transkript erscheint im linken Textfeld
- [ ] Status-Icon in Tabelle ändert sich zu ✅

**Falls Fehler:** "Datei nicht gefunden"
→ ffmpeg fehlt! Siehe Troubleshooting unten.

### 8. ✅ Einstellungen
- [ ] Einstellungen-Button öffnet Dialog
- [ ] Sprache wechseln: Deutsch ↔ English
- [ ] OpenAI API Key speichern
- [ ] Auto-Transkription Checkbox funktioniert
- [ ] AI Prompts anzeigen/bearbeiten/löschen
- [ ] Nach Sprachwechsel: UI-Texte ändern sich

### 9. ✅ CSV Export
- [ ] "CSV Export" Button klicken
- [ ] Datei-Speichern-Dialog erscheint
- [ ] CSV-Datei wird erstellt
- [ ] CSV enthält alle Session-Daten

### 10. ✅ Text-Transformation (AI View)
- [ ] Nach Transkription: Prompt auswählen (z.B. "Zusammenfassen")
- [ ] "Generieren" Button klicken
- [ ] Transformierter Text erscheint im rechten Textfeld

## Windows-spezifische Probleme & Lösungen

### Problem 1: "ffmpeg not found" oder Transkription schlägt fehl

**Symptom:**
- Transkription startet, aber bricht mit Fehler ab
- Log zeigt: `FileNotFoundError` oder `ffmpeg not found`

**Lösung:**
```cmd
REM Prüfen ob ffmpeg im PATH ist:
where ffmpeg

REM Falls nicht gefunden:
REM 1. ffmpeg.exe und ffprobe.exe nach dist\ kopieren:
copy C:\Downloads\ffmpeg.exe dist\CorporateDigitalBrainRecorder\
copy C:\Downloads\ffprobe.exe dist\CorporateDigitalBrainRecorder\

REM 2. ODER zum PATH hinzufügen (System → Umgebungsvariablen)
```

### Problem 2: Windows Defender SmartScreen Warnung

**Symptom:**
```
Windows hat diesen PC geschützt.
Microsoft Defender SmartScreen hat den Start einer unbekannten App verhindert.
```

**Ursache:** Die `.exe` ist nicht digital signiert.

**Lösung (für Testing):**
1. "Weitere Informationen" klicken
2. "Trotzdem ausführen" wählen

**Lösung (für Distribution):**
- App mit Code-Signing-Zertifikat signieren

### Problem 3: Mikrofonberechtigung verweigert

**Symptom:**
- Keine Mikrofone werden angezeigt
- Oder: Aufnahme startet nicht

**Lösung:**
1. Windows-Einstellungen → Datenschutz → Mikrofon
2. "Apps Zugriff auf Mikrofon erlauben" aktivieren
3. App neu starten

### Problem 4: "DLL load failed" oder Import-Fehler

**Symptom:**
```
ImportError: DLL load failed while importing _xxx
```

**Ursache:** Fehlende System-DLLs (meist Visual C++ Redistributables)

**Lösung:**
Installieren Sie: **Microsoft Visual C++ Redistributable**
- Download: https://aka.ms/vs/17/release/vc_redist.x64.exe

### Problem 5: Pfade mit Umlauten funktionieren nicht

**Symptom:** Fehler bei Dateipfaden mit ä, ö, ü, ß

**Ursache:** Encoding-Problem

**Lösung:**
- Vermeiden Sie Umlaute in Dateinamen
- Oder: Windows auf UTF-8 Modus umstellen (Beta-Feature)

### Problem 6: App ist sehr langsam beim Start

**Ursache:** Windows Defender scannt die .exe

**Lösung:**
1. Ausnahme in Windows Defender hinzufügen:
   - Windows Security → Viren- & Bedrohungsschutz
   - Ausschlüsse hinzufügen → Ordner
   - `dist\CorporateDigitalBrainRecorder\` hinzufügen

## Distribution

### Option A: Portable App (einfach)

Die gesamte `dist\CorporateDigitalBrainRecorder\` Ordner kann:
- Auf USB-Stick kopiert werden
- Als ZIP verteilt werden
- Direkt gestartet werden (keine Installation nötig)

**Verteilen:**
```cmd
REM ZIP erstellen (mit 7-Zip oder Windows Explorer)
7z a CorporateDigitalBrainRecorder-v1.0-Windows.zip dist\CorporateDigitalBrainRecorder\
```

### Option B: Installer mit Inno Setup (professionell)

**1. Inno Setup installieren:**
- Download: https://jrsoftware.org/isdl.php

**2. Installer-Script erstellen:** `installer.iss`

```ini
[Setup]
AppName=Corporate Digital Brain Recorder
AppVersion=1.0
DefaultDirName={autopf}\CorporateDigitalBrainRecorder
DefaultGroupName=Corporate Digital Brain
OutputDir=output
OutputBaseFilename=CorporateDigitalBrainRecorder-Setup

[Files]
Source: "dist\CorporateDigitalBrainRecorder\*"; DestDir: "{app}"; Flags: recursesubdirs

[Icons]
Name: "{group}\Corporate Digital Brain Recorder"; Filename: "{app}\CorporateDigitalBrainRecorder.exe"
Name: "{autodesktop}\Corporate Digital Brain Recorder"; Filename: "{app}\CorporateDigitalBrainRecorder.exe"
```

**3. Kompilieren:**
```cmd
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
```

**Ergebnis:** `CorporateDigitalBrainRecorder-Setup.exe` (ca. 250 MB)

## Performance-Optimierung

### Build-Größe reduzieren

**Option 1: UPX Kompression** (bereits aktiviert in .spec)
- Reduziert DLL-Größen um ~50%
- Kein Code-Änderung nötig

**Option 2: Unnötige Packages ausschließen**

Bearbeiten Sie `AudioSessions_windows.spec`:
```python
excludes=[
    'tkinter',        # Nicht benötigt
    'matplotlib',     # Nicht benötigt
    'PIL',            # Nicht benötigt
],
```

**Option 3: One-File Build** (NICHT empfohlen)

Ändert `exe = EXE(...)` zu:
```python
exe = EXE(
    ...
    exclude_binaries=False,  # Ändert von True zu False
)
```
→ Erstellt eine einzelne `.exe`, aber **langsamer Start** (~10 Sekunden)

## Debug-Modus aktivieren

Falls Probleme auftreten, können Sie eine Konsolen-Version bauen:

**1. Bearbeiten Sie `AudioSessions_windows.spec`:**
```python
exe = EXE(
    ...
    console=True,     # Ändert von False zu True
    debug=True,       # Ändert von False zu True
)
```

**2. Neu bauen:**
```cmd
pyinstaller AudioSessions_windows.spec --clean
```

→ Zeigt alle Fehler und Logs in einer Konsole

## Logs finden

**App-Logs:**
```cmd
REM Prüfen Sie:
%APPDATA%\AudioSessions\
```

**Windows Event Viewer:**
```cmd
eventvwr.msc
```
→ Unter "Windows Logs" → "Application"

## Weitere Ressourcen

- **PyInstaller Windows Guide:** https://pyinstaller.org/en/stable/usage.html
- **PySide6 Deployment:** https://doc.qt.io/qtforpython-6/deployment.html
- **FFmpeg Windows Builds:** https://github.com/BtbN/FFmpeg-Builds
- **Inno Setup:** https://jrsoftware.org/isinfo.php

## Support

Bei Problemen bitte folgende Informationen bereitstellen:

```cmd
REM 1. System-Info
systeminfo | findstr /B /C:"OS Name" /C:"OS Version"

REM 2. Python Version
python --version

REM 3. ffmpeg Version (falls installiert)
ffmpeg -version

REM 4. App-Logs
type %APPDATA%\AudioSessions\app.log
```
