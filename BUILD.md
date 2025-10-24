# Build-Anleitung für Audio Sessions

Diese Anleitung beschreibt, wie Sie die Audio Sessions App als eigenständige Anwendung für macOS (und Windows) bauen können.

## Voraussetzungen

- Python 3.9+
- Alle Dependencies aus `requirements.txt` installiert
- PyInstaller >= 6.0.0

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

Für Windows-Builds verwenden Sie dieselbe `.spec` Datei, aber auf einem Windows-System:

```powershell
# Virtuelles Environment erstellen
python -m venv venv
.\venv\Scripts\activate

# Dependencies installieren
pip install -r requirements.txt

# App bauen
pyinstaller AudioSessions.spec --clean
```

Das Ergebnis ist eine `AudioSessions.exe` in `dist/AudioSessions/`.

## Wichtige Dateien

- **AudioSessions.spec**: PyInstaller-Konfiguration
- **Info.plist**: macOS-spezifische Konfiguration (Mikrofonberechtigungen)
- **requirements.txt**: Alle Python-Dependencies

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
