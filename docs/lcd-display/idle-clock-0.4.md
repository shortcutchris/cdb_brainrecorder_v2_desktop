# Zusatzdisplay 0.4.0 · Uhr im Leerlauf

24. November 2026. Recorder-Begleitdienst 0.5.102; Waveshare ESP32-S3-Touch-LCD-5B,
1024×600. Keine Änderung am Pi-Touchlayout oder am Gehäuse.

## Verhalten

- Keine sichtbaren offenen Timer: große türkise Siebensegment-Uhr, HH:MM im
  24-Stunden-Format. Vier 220 Pixel hohe Ziffern. Funktioniert auch abgemeldet.
- Ein Timer: automatische Großansicht mit Restzeit einschließlich Sekunden.
  Mehrere Timer: bisherige Auswahl/Übersicht. Abgelaufene und verpasste Timer
  behalten Vorrang, bis sie am Pi bestätigt oder beendet wurden.
- Die Ortszeit kommt vom Pi; seine Zeitzone und Sommerzeit werden übernommen.
  Der Begleitdienst berechnet sie bei jeder Aktualisierung neu. Das Display
  zählt zwischen den Sekundenschnappschüssen monoton weiter, inklusive Mitternacht.
- Ohne bestätigten Zeitabgleich: `--:--` und „Zeitabgleich am Pi ausstehend“.
  Nach drei Sekunden ohne gültige Daten verschwinden die Zahlen und es erscheint
  der bestehende Verbindungshinweis. Keine scheinbar richtige eingefrorene Uhr.
- Kontotrennung bleibt erhalten. Die Uhr erscheint, wenn für die aktuelle Sitzung
  keine Timer sichtbar sind; fremde Timer und persönliche Titel werden nicht freigegeben.

![Uhr aus derselben LVGL-Oberfläche wie auf dem Display](idle-clock-0.4/clock.png)

## Prüfstand

- 12 Python-Tests für Zeitfreigabe, Ortszeit, Mitternacht, Datenschutz, API und Erkennung bestanden. Zusätzlich 37 Prüfungen für Raummodus und Image-Bau sowie die echte Begleitdienst-Integration über simuliertes USB bestanden.
- Native C-Prüfungen mit Address/UndefinedBehaviorSanitizer: Mitternacht, veraltete
  und rückwärts laufende Messzeit, unbekannte Uhrzeit, Alarmvorrang, alte Begleitdienste,
  ungültige Zeitpakete, transaktionales Aktualisieren und bisherige Timerbedienung.
- Vorschau mit derselben `display_ui.c` und LVGL 9.6.0: Uhr, Timer, Ablauf,
  Rückkehr zur Uhr, unbekannte Zeit, Verbindungsausfall. Keine Gerätefotos.
- Firmware 0.4.0 vollständig mit ESP-IDF 5.5.2 gebaut: [CI 45373390089](https://github.com/shortcutchris/cdb_brainrecorder_v2_desktop/actions/runs/45373390089). Native Tests, simuliertes USB und Hardwarekonfigurationsprüfung erfolgreich. Anwendung 839.456 Bytes; finaler Abhängigkeitsstand und Partitionstabelle identisch mit 0.3.0. [Buildnachweis](idle-clock-0.4/build-manifest.json).

## Kompatibilität, Update und Image

Das optionale Feld `local_time_ms` erweitert `cdb.lcd/1` um die Millisekunden seit
lokaler Mitternacht; `clock_ready` muss wahr sein. Alte Displayfirmware ignoriert
das Feld und zeigt weiter Timer. Neue Firmware mit altem Begleitdienst zeigt
`--:--`, bis eine verlässliche Uhrzeit geliefert wird. Alte Zeitwerte werden bei
fehlendem Feld gelöscht. Keine neue Bibliothek oder Änderung der Partitionsaufteilung.

Bestehender Pi: signiertes App-Update 0.5.102 und Neustart ausschließlich des
separaten USB-Begleitdienstes zusätzlich zum normalen App-Update. Display: eigenes
gezieltes Update auf 0.4.0 nach BOOT, mit Sicherung und Rücklesen, ausschließlich
Anwendung ab 0x10000. Bootloader, Partitionen, NVS und PHY bleiben bestehen.

Frisches SD-Image: die versionierte Brücke und Hilfe sind in den vorhandenen
Positivlisten; der bestehende optionale Displaydienst wird weiterverwendet.
Ein neues Pi-Image flasht das Zusatzdisplay niemals automatisch. Neue Displays
benötigen separat Firmware 0.4.0. Kein neues SD-Image gebaut oder hardwarezertifiziert.

## Pi-Installation am 24. November 2026

Recorder **0.5.102** wurde um **11:18 Uhr (Europe/Berlin)** signiert installiert
(155 geprüfte Dateien). Der USB-Begleitdienst wurde neu gestartet. Er liefert
bereits die bestätigte Pi-Ortszeit in `Europe/Berlin` bei leerer Timerliste.
Einstellungen, Aufnahmen, NFC-Zuordnungen und Raumpolitik sind erhalten.
[Pi-Installationsnachweis](idle-clock-0.4/pi-deployment.json).

Sauberes Image-Baupaket aus `c01df2c9cb7bd19c261d1b3ff64b06405b1d0b64`
mit 162 Quelldateien erstellt und sämtliche Build-Prüfsummen geprüft.
Das ist kein gebautes oder auf Hardware gebootetes SD-Image.

Die Uhr wird erst mit der separat zu installierenden Display-Firmware sichtbar.

## Display-Update vorbereitet, BOOT noch ausstehend

Die neue Anwendung und ein geprüftes Skript für Sicherung, gezieltes Schreiben
und Rücklesen liegen privat auf dem Pi unter
`~/.local/share/cdb-lcd/update-0.4.0-c01df2c/`. Die Dateiprüfsumme und der interne
ESP32-S3-Image-Hash sind gültig. Es wurde noch keine Display-Firmware geschrieben.
Der normale Display-Port ist weiterhin vorhanden; die vorhandene 0.3-Firmware
kann mit dem aktualisierten Begleitdienst weiterhin Timer anzeigen.

Für die Fortsetzung: nur das USB-Kabel des Zusatzdisplays abziehen, BOOT gedrückt
halten, USB wieder am Pi einstecken, BOOT loslassen. Der Pi bleibt eingeschaltet.
Nach dem bestätigten Firmware-Update gegebenenfalls kurz RESET drücken.
[Herstelleranleitung zum USB-Download](https://docs.waveshare.com/ESP32-S3-Touch-LCD-5/Instructions-For-Use#%EF%B8%8F-usb-download-precautions-important).

Vor Schreiben prüft das Skript die aktuelle Anwendung 0.3, Bootloader und
Partitionstabelle des eindeutig zugeordneten Displays. Es sichert die ersten
64 KiB und die gesamte 1-MiB-Anwendungspartition privat, schreibt nur die neue
Anwendung und vergleicht danach alle geschriebenen Bytes sowie den unveränderten
64-KiB-Vorbereich. Der Begleitdienst wird anschließend wieder gestartet.
Am echten Display bleiben Uhranzeige, Timerwechsel und Touch nach dem Update zu prüfen.
