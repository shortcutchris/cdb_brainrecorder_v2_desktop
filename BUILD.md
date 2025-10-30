# Build-Anleitung für Audio Sessions

Diese Anleitung beschreibt, wie Sie die Audio Sessions App als eigenständige Anwendung für **macOS** und **Windows** bauen können.

## 📋 Schnellübersicht

| Plattform | Build-Script | Spec-Datei | Dokumentation |
|-----------|--------------|------------|---------------|
| **macOS** | `./build_app.sh` | `AudioSessions.spec` | Siehe unten |
| **Windows** | `build_windows.bat` | `AudioSessions_windows.spec` | [WINDOWS_BUILD.md](WINDOWS_BUILD.md) ⭐ |
| **Raspberry Pi / Linux** | `./build_linux.sh` | `AudioSessions_linux.spec` | [RASPBERRY_PI_BUILD.md](RASPBERRY_PI_BUILD.md) 🍓 |

> **Windows-Build:** Bitte lesen Sie [WINDOWS_BUILD.md](WINDOWS_BUILD.md) für eine ausführliche Anleitung mit Test-Checkliste.
>
> **Raspberry Pi:** Bitte lesen Sie [RASPBERRY_PI_BUILD.md](RASPBERRY_PI_BUILD.md) für Hardware-Anforderungen, Audio-Setup und Performance-Tipps.

## Voraussetzungen

- Python 3.9+
- Alle Dependencies aus `requirements.txt` installiert
- PyInstaller >= 6.0.0
- **macOS:** ffmpeg & ffprobe (via Homebrew: `brew install ffmpeg`)
- **Windows:** siehe [WINDOWS_BUILD.md](WINDOWS_BUILD.md)
- **Raspberry Pi/Linux:** siehe [RASPBERRY_PI_BUILD.md](RASPBERRY_PI_BUILD.md)

---

## Build für macOS

### 1. Virtuelles Environment einrichten

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. App bauen

```bash
pyinstaller AudioSessions.spec --clean
```

Der Build-Prozess dauert ca. 1-2 Minuten.

### 3. Ergebnis

Die gebaute App befindet sich in:
```
dist/AudioSessions.app
```

Sie können die App öffnen mit:
```bash
open dist/AudioSessions.app
```

Oder die App in den `/Applications` Ordner ziehen.

## Build für Windows

Für Windows-Builds gibt es eine **separate Konfiguration** und ein **eigenes Build-Script**.

**📖 Vollständige Anleitung:** [WINDOWS_BUILD.md](WINDOWS_BUILD.md)

**Kurzfassung:**
```cmd
REM Auf Windows-Maschine:
cd path\to\project
build_windows.bat
```

**Ergebnis:** `dist\CorporateDigitalBrainRecorder\CorporateDigitalBrainRecorder.exe`

**Wichtig:**
- Windows-Build kann **nur auf Windows** erstellt werden (nicht Cross-Compile von macOS)
- ffmpeg & ffprobe müssen separat installiert werden (siehe [WINDOWS_BUILD.md](WINDOWS_BUILD.md))
- Vollständige Test-Checkliste in [WINDOWS_BUILD.md](WINDOWS_BUILD.md)

## Build für Raspberry Pi / Linux

Für Raspberry Pi und andere Linux-Systeme gibt es eine **eigene Konfiguration** mit besonderem Fokus auf ARM-Kompatibilität und Performance.

**📖 Vollständige Anleitung:** [RASPBERRY_PI_BUILD.md](RASPBERRY_PI_BUILD.md)

**Kurzfassung:**
```bash
# Auf Raspberry Pi / Linux-System:
cd path/to/project
chmod +x build_linux.sh
./build_linux.sh

# Wählen Sie Option 2: "Direkt mit Python" (empfohlen!)
```

**Ergebnis:** `run.sh` Script zum direkten Starten der App

**Wichtig:**
- **Empfohlene Hardware:** Raspberry Pi 4 (4GB+) oder Raspberry Pi 5
- **Audio-Setup ist kritisch:** USB-Mikrofon + ALSA/PulseAudio (siehe [RASPBERRY_PI_BUILD.md](RASPBERRY_PI_BUILD.md))
- **Option 2 empfohlen** (Python direkt statt PyInstaller) → Schneller auf ARM
- Desktop-Umgebung benötigt (GUI-Anwendung)
- Vollständige Hardware-Anforderungen & Test-Checkliste in [RASPBERRY_PI_BUILD.md](RASPBERRY_PI_BUILD.md)

**Performance-Hinweis:**
Raspberry Pi 4 funktioniert gut für Audio-Aufnahmen, Transkription (Audio-Konvertierung) kann 1-2 Minuten dauern.

---

## Wichtige Dateien

### macOS
- **AudioSessions.spec**: PyInstaller-Konfiguration für macOS
- **build_app.sh**: macOS Build-Script
- **Info.plist**: macOS-spezifische Konfiguration (Mikrofonberechtigungen)
- **icon.icns**: macOS App-Icon

### Windows
- **AudioSessions_windows.spec**: PyInstaller-Konfiguration für Windows
- **build_windows.bat**: Windows Build-Script
- **WINDOWS_BUILD.md**: Ausführliche Windows Build & Test-Anleitung
- **icon.ico**: Windows App-Icon

### Linux / Raspberry Pi
- **AudioSessions_linux.spec**: PyInstaller-Konfiguration für Linux/ARM
- **build_linux.sh**: Linux/Raspberry Pi Build-Script
- **RASPBERRY_PI_BUILD.md**: Ausführliche Raspberry Pi Setup, Audio-Config & Troubleshooting
- **run.sh**: Python-Runner für direkte Ausführung (empfohlen für RPi)

### Allgemein
- **requirements.txt**: Alle Python-Dependencies
- **hooks/runtime_hook.py**: Pfad-Konfiguration für alle Plattformen

## Hinweise für macOS

### Mikrofonberechtigung

Die `Info.plist` enthält den Eintrag `NSMicrophoneUsageDescription`, der bei der ersten Verwendung den macOS-Berechtigungsdialog auslöst.

### Code-Signierung (Optional)

Für die Verteilung außerhalb des App Stores sollte die App signiert werden:

```bash
codesign --force --deep --sign "Developer ID Application: Ihr Name" dist/AudioSessions.app
```

### Notarisierung (Optional)

Für die Verteilung an andere Nutzer empfiehlt sich die Notarisierung durch Apple:

```bash
# App als ZIP verpacken
ditto -c -k --keepParent dist/AudioSessions.app AudioSessions.zip

# Zur Notarisierung hochladen
xcrun notarytool submit AudioSessions.zip --keychain-profile "AC_PASSWORD" --wait

# Nach erfolgreicher Notarisierung das Ticket heften
xcrun stapler staple dist/AudioSessions.app
```

## Build-Artefakte

Die folgenden Ordner werden beim Build erstellt und sind in `.gitignore`:

- `build/` - Temporäre Build-Dateien
- `dist/` - Finale Anwendung
- `*.spec` - PyInstaller Konfiguration (im Repo enthalten)

## Troubleshooting

### Problem: "App kann nicht geöffnet werden"

**Lösung für macOS:**
```bash
xattr -cr dist/AudioSessions.app
```

### Problem: Missing modules

**Lösung:**
Prüfen Sie, ob alle Dependencies installiert sind:
```bash
pip install -r requirements.txt
```

### Problem: Build schlägt fehl

**Lösung:**
Löschen Sie Build-Cache und versuchen Sie erneut:
```bash
rm -rf build dist
pyinstaller AudioSessions.spec --clean
```

## DMG-Installer erstellen (macOS)

Für eine professionelle Distribution können Sie einen DMG-Installer erstellen:

```bash
# Mit create-dmg (Installation: brew install create-dmg)
create-dmg \
  --volname "Audio Sessions" \
  --window-pos 200 120 \
  --window-size 800 400 \
  --icon-size 100 \
  --app-drop-link 600 185 \
  "AudioSessions-1.0.0.dmg" \
  "dist/AudioSessions.app"
```

Oder manuell:

```bash
# Disk Image erstellen
hdiutil create -volname "Audio Sessions" -srcfolder dist/AudioSessions.app -ov -format UDZO AudioSessions.dmg
```

## Größe reduzieren

Um die App-Größe zu reduzieren:

1. **UPX verwenden** (bereits in `.spec` aktiviert)
2. **Unnötige Packages ausschließen**
3. **Strip verwenden** für kleinere Binaries

Die aktuelle App-Größe beträgt ca. 100-150 MB (typisch für PySide6-Apps).

## Weitere Informationen

- [PyInstaller Dokumentation](https://pyinstaller.org/en/stable/)
- [PySide6 Deployment Guide](https://doc.qt.io/qtforpython-6/deployment.html)
- [macOS Code Signing Guide](https://developer.apple.com/documentation/xcode/notarizing_macos_software_before_distribution)
