# Autostart Configuration für CDB Recorder

## Autostart aktivieren

So startest du die App automatisch beim System-Login:

```bash
./install-autostart.sh
```

**Was passiert:**
- Die App startet automatisch im Fullscreen-Modus nach dem Login
- Funktioniert nach jedem Neustart
- Verwendet die Desktop-Autostart-Funktionalität

## Autostart deaktivieren

So entfernst du den Autostart wieder:

```bash
./remove-autostart.sh
```

**Was passiert:**
- Die App startet nicht mehr automatisch
- Du kannst sie weiterhin manuell mit `./run.sh` starten

## Manuelle Kontrolle

### Autostart prüfen
```bash
ls -la ~/.config/autostart/cdb-recorder.desktop
```

### Autostart manuell löschen
```bash
rm ~/.config/autostart/cdb-recorder.desktop
```

### Desktop-Datei bearbeiten
```bash
nano ~/.config/autostart/cdb-recorder.desktop
```

## Fullscreen-Steuerung

Die App startet automatisch im Fullscreen auf dem Raspberry Pi.

**Fullscreen verlassen:**
- 5x schnell auf das Logo links oben klicken
- F11-Taste drücken
- ESC-Taste drücken

**Fullscreen beim Autostart deaktivieren:**

Bearbeite die Desktop-Datei:
```bash
nano ~/.config/autostart/cdb-recorder.desktop
```

Ändere die `Exec` Zeile zu:
```
Exec=env FULLSCREEN=false /home/chris/projects/cdb_brainrecorder_v2_desktop/run.sh
```

## Alternative: Systemd Service (für Headless)

Falls du die App als System-Service ohne Desktop-Login starten möchtest, kontaktiere den Support für eine systemd-Service-Konfiguration.

## Troubleshooting

### App startet nicht automatisch

1. Prüfe ob die Desktop-Datei existiert:
   ```bash
   ls -la ~/.config/autostart/cdb-recorder.desktop
   ```

2. Prüfe die Berechtigungen:
   ```bash
   chmod +x ~/projects/cdb_brainrecorder_v2_desktop/run.sh
   ```

3. Teste manuellen Start:
   ```bash
   ./run.sh
   ```

### App schließt sich sofort

Prüfe die Logs:
```bash
journalctl --user -xe
```

Oder teste mit Terminal-Output:
```bash
# Bearbeite cdb-recorder.desktop
nano ~/.config/autostart/cdb-recorder.desktop

# Ändere Terminal=false zu Terminal=true
Terminal=true
```

## Deinstallation

So entfernst du alle Autostart-Komponenten:

```bash
./remove-autostart.sh
rm install-autostart.sh remove-autostart.sh cdb-recorder.desktop AUTOSTART.md
```
