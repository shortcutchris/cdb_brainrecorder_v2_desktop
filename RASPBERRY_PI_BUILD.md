# Raspberry Pi Build-Anleitung - Corporate Digital Brain Recorder

Diese Anleitung beschreibt, wie Sie die App auf einem **Raspberry Pi** zum Laufen bringen.

## 🍓 Hardware-Anforderungen

### Minimum (funktioniert, aber langsam):
- **Raspberry Pi 4 Model B** (4 GB RAM) oder neuer
- **Raspberry Pi 400** (Tastatur-PC)
- **Raspberry Pi 5** (empfohlen!)

### Nicht empfohlen (zu langsam):
- Raspberry Pi 3 oder älter
- Raspberry Pi Zero

### Zusätzlich benötigt:
- **MicroSD-Karte:** Mindestens 16 GB (32 GB empfohlen)
- **USB-Mikrofon:** Für Audio-Aufnahmen
- **Monitor, Tastatur, Maus:** Für Desktop-Bedienung
- **Stromversorgung:** Original Raspberry Pi Netzteil
- **Optional:** USB-Soundkarte (bessere Audio-Qualität)

## 📀 OS-Installation

### Empfohlenes OS: Raspberry Pi OS (64-bit) mit Desktop

**Download & Installation:**
1. Raspberry Pi Imager herunterladen: https://www.raspberrypi.com/software/
2. OS auswählen: **Raspberry Pi OS (64-bit)** mit Desktop
3. Auf microSD-Karte schreiben
4. Raspberry Pi booten

**Erste Schritte:**
```bash
# System aktualisieren
sudo apt-get update
sudo apt-get upgrade -y

# Neustarten
sudo reboot
```

## 🔊 Audio-Setup (WICHTIG!)

Audio-Konfiguration ist **kritisch** für die App!

### 1. Audio-Treiber installieren

```bash
# ALSA und PulseAudio installieren
sudo apt-get install -y pulseaudio pulseaudio-utils alsa-utils

# PulseAudio starten
pulseaudio --start

# Audio-Geräte prüfen
arecord -l    # Aufnahme-Geräte
aplay -l      # Wiedergabe-Geräte
pactl list sources   # PulseAudio Quellen
```

### 2. USB-Mikrofon einrichten

```bash
# USB-Mikrofon anschließen und prüfen
lsusb | grep -i audio

# Test-Aufnahme (5 Sekunden)
arecord -D plughw:1,0 -d 5 -f cd test.wav
aplay test.wav

# Falls kein Ton: Lautstärke erhöhen
alsamixer
# Mit F4 zu "Capture" wechseln, Pegel erhöhen
```

### 3. Standard-Gerät setzen (Optional)

**Über GUI:**
- Raspberry Pi Menü → Preferences → Audio Device Settings
- Mikrofon als Standard-Eingabegerät setzen

**Über Kommandozeile:**
```bash
# Liste der Geräte anzeigen
pactl list sources short

# Standard setzen (ersetze DEVICE_NAME)
pactl set-default-source DEVICE_NAME
```

## 🚀 App-Installation

### Schritt 1: Repository auf Raspberry Pi bringen

**Option A - Mit Git:**
```bash
sudo apt-get install git
git clone <repository-url>
cd cdb_brainrecorder_v2_desktop
```

**Option B - USB-Stick/Netzwerk:**
- Kopieren Sie den Projektordner auf den Raspberry Pi
- Via USB-Stick, SFTP, oder Samba-Share

### Schritt 2: System-Dependencies installieren

```bash
cd cdb_brainrecorder_v2_desktop

# Dependencies installieren
sudo apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    ffmpeg \
    portaudio19-dev \
    libsndfile1 \
    libxcb-xinerama0 \
    libxcb-cursor0

# Für PySide6 (GUI):
sudo apt-get install -y \
    libqt6gui6 \
    libqt6widgets6 \
    qt6-qpa-plugins
```

### Schritt 3: Build-Script ausführen

```bash
chmod +x build_linux.sh
./build_linux.sh
```

**Das Script fragt Sie:**
```
Ihre Wahl (1 oder 2):
  [1] PyInstaller Build (standalone Binary)
  [2] Direkt mit Python starten (EMPFOHLEN)
```

**Wählen Sie Option 2** für Raspberry Pi!
- Schnellerer Start
- Weniger Speicher
- Einfacher zu debuggen

## 📱 App starten

### Methode 1: Terminal-Starter

```bash
# Mit run.sh (erstellt von build_linux.sh)
./run.sh
```

### Methode 2: Desktop-Starter erstellen

Erstellen Sie eine `.desktop` Datei für das Anwendungsmenü:

```bash
cat > ~/.local/share/applications/cdb-recorder.desktop << 'EOF'
[Desktop Entry]
Version=1.0
Type=Application
Name=Corporate Digital Brain Recorder
Comment=Audio Recording and AI Transcription
Exec=/home/pi/cdb_brainrecorder_v2_desktop/run.sh
Icon=/home/pi/cdb_brainrecorder_v2_desktop/icon.png
Terminal=false
Categories=AudioVideo;Audio;Recorder;
Keywords=audio;recording;transcription;ai;
EOF

# Ausführbar machen
chmod +x ~/.local/share/applications/cdb-recorder.desktop

# Desktop-Datenbank aktualisieren
update-desktop-database ~/.local/share/applications/
```

**Hinweis:** Passen Sie die Pfade (`/home/pi/...`) an Ihre Installation an!

Danach erscheint die App im **Anwendungsmenü** unter "Sound & Video".

### Methode 3: Autostart (Optional)

App beim Systemstart automatisch starten:

```bash
mkdir -p ~/.config/autostart

cat > ~/.config/autostart/cdb-recorder.desktop << 'EOF'
[Desktop Entry]
Type=Application
Name=Corporate Digital Brain Recorder
Exec=/home/pi/cdb_brainrecorder_v2_desktop/run.sh
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
EOF
```

## 🧪 Test-Checkliste für Raspberry Pi

Nach der Installation bitte alle Funktionen testen:

### 1. ✅ App-Start
- [ ] App startet ohne Fehler
- [ ] GUI erscheint (ca. 5-10 Sekunden Ladezeit ist normal)
- [ ] Splash Screen wird angezeigt

### 2. ✅ Mikrofon-Auswahl
- [ ] USB-Mikrofon wird in Dropdown angezeigt
- [ ] Pegel-Anzeige reagiert auf Audio-Input
- [ ] Keine "Geräte nicht gefunden" Fehler

### 3. ✅ Audio-Aufnahme
- [ ] Aufnahme startet
- [ ] Waveform-Visualisierung funktioniert
- [ ] Aufnahme stoppt und speichert
- [ ] WAV-Datei wird erstellt in: `~/.local/share/AudioSessions/recordings/`

**Speicherort prüfen:**
```bash
ls -lh ~/.local/share/AudioSessions/recordings/
```

### 4. ✅ Datenbank
- [ ] Session erscheint in Tabelle
- [ ] SQLite DB existiert: `~/.local/share/AudioSessions/data/sessions.db`

```bash
# Datenbank prüfen
ls -lh ~/.local/share/AudioSessions/data/
sqlite3 ~/.local/share/AudioSessions/data/sessions.db "SELECT * FROM sessions;"
```

### 5. ✅ Audio-Player
- [ ] Play/Pause funktioniert
- [ ] Slider funktioniert
- [ ] Lautstärke-Regler funktioniert
- [ ] Kein Knistern oder Aussetzer

### 6. ✅ Transkription (Internet benötigt!)
- [ ] OpenAI API Key eingegeben
- [ ] Transkription startet
- [ ] ffmpeg konvertiert Audio (kann auf RPi langsam sein)
- [ ] Transkript erscheint

**Hinweis:** Transkription kann auf Raspberry Pi 4 **1-2 Minuten** dauern (Audio-Konvertierung)!

### 7. ✅ Performance
- [ ] GUI reagiert flüssig (30+ FPS)
- [ ] Keine Freezes beim Scrollen
- [ ] Audio-Aufnahme ohne Aussetzer

## ⚡ Performance-Optimierung

### Problem: App ist langsam / ruckelt

**Lösung 1: Overclocking (Raspberry Pi 4)**
```bash
# /boot/config.txt bearbeiten
sudo nano /boot/config.txt

# Folgende Zeilen hinzufügen:
over_voltage=6
arm_freq=2000

# Speichern, Neustarten
sudo reboot
```

**Lösung 2: GPU-Speicher erhöhen**
```bash
sudo raspi-config
# → Performance Options → GPU Memory → 256 MB

sudo reboot
```

**Lösung 3: Unnötige Dienste deaktivieren**
```bash
# Bluetooth deaktivieren (falls nicht benötigt)
sudo systemctl disable bluetooth

# WLAN Power-Management deaktivieren
sudo nano /etc/rc.local
# Vor "exit 0" einfügen:
iwconfig wlan0 power off

sudo reboot
```

### Problem: Audio knistert / hat Aussetzer

**Lösung: PulseAudio Buffer erhöhen**
```bash
nano ~/.config/pulse/daemon.conf

# Folgende Zeilen hinzufügen/ändern:
default-fragments = 8
default-fragment-size-msec = 10

# PulseAudio neustarten
pulseaudio -k
pulseaudio --start
```

## 🐛 Troubleshooting

### Problem 1: "No module named 'PySide6'"

**Ursache:** PySide6 nicht korrekt installiert

**Lösung:**
```bash
# Virtual Environment aktivieren
source venv/bin/activate

# PySide6 manuell installieren
pip install PySide6

# Falls Fehler: System-Qt nutzen
sudo apt-get install python3-pyside6.qtcore python3-pyside6.qtwidgets python3-pyside6.qtgui
```

### Problem 2: "Qt platform plugin not found"

**Ursache:** Qt-Plugins fehlen

**Lösung:**
```bash
# Qt6-Plugins installieren
sudo apt-get install qt6-qpa-plugins

# Umgebungsvariable setzen
export QT_QPA_PLATFORM=xcb

# In run.sh hinzufügen:
echo 'export QT_QPA_PLATFORM=xcb' >> run.sh
```

### Problem 3: Kein Audio-Gerät gefunden

**Symptom:** Dropdown zeigt "Kein Mikrofon" oder ist leer

**Lösung:**
```bash
# 1. USB-Gerät prüfen
lsusb | grep -i audio

# 2. ALSA-Geräte prüfen
arecord -l

# 3. PulseAudio-Quellen prüfen
pactl list sources short

# 4. Berechtigungen prüfen (User muss in 'audio' Gruppe sein)
sudo usermod -a -G audio $USER

# 5. Ausloggen und wieder einloggen
# Oder neustarten
```

### Problem 4: ffmpeg fehlt / Transkription schlägt fehl

**Symptom:** "FileNotFoundError" bei Transkription

**Lösung:**
```bash
# ffmpeg installieren
sudo apt-get install ffmpeg

# Prüfen
which ffmpeg
ffmpeg -version
```

### Problem 5: App startet nicht (ImportError)

**Symptom:** `ImportError: libxxx.so.X: cannot open shared object file`

**Lösung:**
```bash
# Fehlende Bibliotheken finden und installieren
sudo apt-get install libxcb-xinerama0 libxcb-cursor0 libxcb-icccm4

# Liste aller fehlenden libs anzeigen:
ldd venv/lib/python3.*/site-packages/PySide6/Qt/lib/libQt6Core.so.6
```

### Problem 6: Sehr langsamer Start (> 30 Sekunden)

**Ursache:** SD-Karte zu langsam oder PyInstaller-Build

**Lösung:**
1. **Schnellere SD-Karte verwenden** (Class 10, A2-Rating)
2. **Option 2 nutzen** (Python direkt statt PyInstaller)
3. **USB-SSD Boot** (deutlich schneller als SD-Karte)

## 💾 Speicherplatz-Management

### Verfügbaren Speicher prüfen

```bash
# Gesamtübersicht
df -h

# App-Daten
du -sh ~/.local/share/AudioSessions/
```

### Alte Aufnahmen löschen

```bash
# Aufnahmen älter als 30 Tage löschen
find ~/.local/share/AudioSessions/recordings/ -name "*.wav" -mtime +30 -delete

# Oder über die App: Session auswählen → Löschen-Button
```

## 🌐 Fernzugriff (Optional)

### VNC aktivieren für Remote Desktop

```bash
# VNC aktivieren
sudo raspi-config
# → Interface Options → VNC → Enable

# Oder installieren:
sudo apt-get install realvnc-vnc-server

# VNC Server starten
vncserver
```

**Von anderem Computer verbinden:**
- VNC Viewer installieren: https://www.realvnc.com/download/viewer/
- Verbinden zu: `raspberry-pi-ip:5901`

### SSH für Kommandozeilen-Zugriff

```bash
# SSH aktivieren
sudo raspi-config
# → Interface Options → SSH → Enable

# Von anderem Computer:
ssh pi@raspberry-pi-ip
```

## 📊 System-Monitoring

### Ressourcen-Überwachung während der Nutzung

```bash
# CPU & RAM Monitoring
htop

# Temperatur überwachen (wichtig!)
watch -n 1 vcgencmd measure_temp

# Throttling prüfen (zeigt ob CPU gedrosselt wird)
vcgencmd get_throttled
```

**Hinweis:** Bei Temperatur > 80°C wird die CPU gedrosselt!
→ Kühlkörper oder Lüfter empfohlen

## 🔄 Updates

### App aktualisieren

```bash
cd cdb_brainrecorder_v2_desktop

# Git Pull (falls via Git installiert)
git pull

# Dependencies aktualisieren
source venv/bin/activate
pip install -r requirements.txt --upgrade

# Neustart der App
./run.sh
```

### System aktualisieren

```bash
sudo apt-get update
sudo apt-get upgrade -y
sudo reboot
```

## 🎯 Alternative: Headless-Betrieb (Zukunft)

Aktuell benötigt die App eine **Desktop-Umgebung** (GUI).

**Mögliche zukünftige Erweiterungen:**
- Web-Interface (Flask/FastAPI)
- CLI-Version (nur Aufnahme + Transkription)
- Systemd-Service (im Hintergrund laufen)

Falls Interesse besteht, kann dies implementiert werden!

## 📖 Weitere Ressourcen

- **Raspberry Pi OS:** https://www.raspberrypi.com/software/
- **PySide6 auf ARM:** https://doc.qt.io/qtforpython-6/
- **ALSA Config:** https://wiki.archlinux.org/title/Advanced_Linux_Sound_Architecture
- **PulseAudio:** https://wiki.archlinux.org/title/PulseAudio

## 💡 Tipps & Tricks

### 1. Schnellerer Boot

```bash
# Desktop-Umgebung nur bei Bedarf starten
sudo systemctl set-default multi-user.target

# Desktop starten mit:
startx

# Zurück zu Auto-Start:
sudo systemctl set-default graphical.target
```

### 2. Netzwerk-Share für Aufnahmen

```bash
# Samba installieren
sudo apt-get install samba samba-common-bin

# Aufnahme-Ordner teilen
sudo nano /etc/samba/smb.conf

# Am Ende hinzufügen:
[recordings]
path = /home/pi/.local/share/AudioSessions/recordings
browseable = yes
read only = no
guest ok = yes

# Neustarten
sudo systemctl restart smbd
```

**Von anderem Computer zugreifen:**
- Windows: `\\raspberry-pi-ip\recordings`
- macOS: `smb://raspberry-pi-ip/recordings`

### 3. Automatisches Backup

```bash
# Backup-Script erstellen
cat > ~/backup_recordings.sh << 'EOF'
#!/bin/bash
rsync -av ~/.local/share/AudioSessions/recordings/ \
    /mnt/usb/backup/recordings/
EOF

chmod +x ~/backup_recordings.sh

# Cron-Job für tägliches Backup um 2 Uhr nachts
crontab -e
# Hinzufügen:
0 2 * * * /home/pi/backup_recordings.sh
```

## 🎬 Zusammenfassung - Schnellstart

```bash
# 1. System vorbereiten
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y python3 python3-pip python3-venv ffmpeg portaudio19-dev libsndfile1

# 2. Projekt clonen
git clone <repo-url>
cd cdb_brainrecorder_v2_desktop

# 3. Build-Script ausführen (Option 2 wählen!)
chmod +x build_linux.sh
./build_linux.sh

# 4. App starten
./run.sh
```

**Viel Erfolg mit Ihrem Raspberry Pi Recorder! 🍓🎙️**
