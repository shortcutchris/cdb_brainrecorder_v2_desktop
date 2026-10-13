# ReSpeaker XVF3800: Anschluss, Einrichtung und Wartung

Gültig für unseren Raspberry-Pi-Recorder mit **Seeed Studio reSpeaker XVF3800 USB 4-Mic Array mit Gehäuse**. Geprüfter Stand: 13.10.2026, Recorder Studio 0.5.18, USB-Firmware 2.1.1.

## Muss bei jedem Anschließen die Firmware installiert werden?

**Nein. Die Firmware wird im Mikrofon gespeichert und bleibt beim Abziehen, Neustarten und Wechseln des Raspberry Pi erhalten.** Das bereits eingerichtete ReSpeaker wird normalerweise einfach wieder angeschlossen.

Ein **neues oder ausgetauschtes ReSpeaker** kann dagegen eine andere Firmware haben. Besonders die Variante mit XIAO ESP32S3 wird laut Seeed mit I²S-Firmware ausgeliefert. Für unseren USB-Recorder muss sie einmalig auf USB-Firmware umgestellt werden. Das gilt pro Mikrofon, nicht pro USB-Verbindung. [Seeed: Betriebsmodi der XIAO-Variante](https://wiki.seeedstudio.com/respeaker_xvf3800_xiao_getting_started/)

| Situation | Was ist zu tun? |
| --- | --- |
| Dasselbe eingerichtete Mikrofon erneut anschließen | Anschließen, Geräte aktualisieren, kurzen Mikrofontest machen. Kein Flashen. |
| Pi neu starten oder dieselbe SD-Karte in einen anderen Pi einsetzen | Mikrofon anschließen und Auswahl prüfen. Die Firmware befindet sich weiterhin im Mikrofon. |
| Pi mit neuer SD-Karte / neu installiertem System | Recorder und Diagnosewerkzeuge bei Bedarf neu einrichten. Die Mikrofon-Firmware bleibt erhalten. |
| Neues oder anderes ReSpeaker anschließen | USB-Erkennung und Firmware prüfen; nur bei Bedarf auf USB umstellen. |
| Hersteller veröffentlicht eine neue Firmware | Änderungen und Kompatibilität prüfen; gezieltes Wartungsupdate, kein automatischer Zwang. |
| Gerät erscheint plötzlich nicht mehr | Zuerst Verbindung und Betriebsmodus prüfen. Nicht sofort erneut flashen. |

## Im Alltag anschließen

1. Eine laufende Aufnahme einschließlich Pause zuerst mit **Stoppen** beenden. Das Mikrofon während der Aufnahme nicht abziehen.
2. Ein USB-**Datenkabel** vom Pi zum **XMOS-USB-C-Anschluss direkt neben der 3,5-mm-Klinkenbuchse** verwenden. Der blaue USB-A-Port des Pi ist geeignet. Der zweite USB-C-Port einer XIAO-Variante ist nicht der USB-Audioanschluss des XMOS.
3. In der App **Einstellungen → Audio → Mikrofon → Geräte aktualisieren** öffnen.
4. **reSpeaker XVF3800 4-Mic Array** auswählen. Auf unserem Pi ist die getestete Quelle `plughw:CARD=Array,DEV=0`. Gerätenummern können sich ändern; nicht dauerhaft auf „Karte 2“ verlassen.
5. **Mikrofon testen · 5 Sekunden** antippen und sofort einen vollständigen kurzen Satz sprechen. Den Pegel beobachten und die Testaufnahme im Player anhören.
6. Falls die Einrichtung als offen angezeigt wird, die noch offenen Prüfpunkte abschließen. Danach zum Recorder zurückgehen.

LEDs zeigen zunächst nur, dass das Gerät Strom hat. Erst die Geräteliste und ein erfolgreicher Audiotest bestätigen die Aufnahmeverbindung. [Seeed: USB-Diagnose](https://wiki.seeedstudio.com/respeaker_xvf3800_faq/)

## Was auf unserem Gerät eingerichtet ist

| Eigenschaft | Geprüfter Wert |
| --- | --- |
| Mikrofon-Firmware | USB 2.1.1 |
| USB-Kennung | `2886:001a` |
| Hardware-Audioformat | 16 kHz, 16 Bit, zwei Kanäle für Aufnahme und Wiedergabe |
| Aufnahme in der App | 16-kHz-Mono; ALSA übernimmt die Konvertierung |
| Audio-Treiber | Vorhandener Linux-Treiber `snd-usb-audio`; kein separater Seeed-Audiotreiber installiert |
| Hardware-Mute | Weiter aktiviert |
| LED-Ausgangszustand | DOA-Modus (Richtungsanzeige), nach dem LED-Test wiederhergestellt |

Vier eingebaute Mikrofone bedeuten nicht vier Einträge in der Geräteauswahl. Unser USB-Profil stellt ein Array mit zwei Audiokanälen bereit. Die ebenfalls verfügbaren 6-Kanal- und 48-kHz-Firmwarevarianten wurden hier nicht installiert und sind kein notwendiger Schritt für den Recorder.

## Stumm, Pause und LEDs

| Bedienung | Wirkung |
| --- | --- |
| **Mikro stumm** in der App | Schreibt Stille in dieselbe Aufnahme; die Zeit läuft weiter. Die Audioquelle bleibt geöffnet. |
| **Pause** in der App | Verwirft eingehendes Audio; die gespeicherte Aufnahmedauer bleibt stehen. |
| **Fortsetzen** | Setzt dieselbe Aufnahme fort. Ein zuvor stummgeschaltetes Mikro bleibt stumm, bis es eingeschaltet wird. |
| **Stoppen** | Beendet auch eine pausierte Aufnahme und reiht sie in die Verarbeitung ein. |
| Physische Mute-Taste am ReSpeaker | Eigene Hardware-Stummschaltung. Die App zeigt sie während einer Aufnahme an; Einschalten erfolgt an der physischen Taste. |

Auch während Pause bleiben Bibliothek und Einstellungen gesperrt. Notizen sind weiterhin möglich.

Ab Studio 0.5.18 zeigt der Ring bei ausdrücklich ausgewähltem ReSpeaker den App-Status:

| LED-Ring | Bedeutung |
| --- | --- |
| Blau | Aufnahme oder fünfsekündiger Mikrofontest läuft |
| Gelb | Aufnahme pausiert |
| Rot blinkend | Mikro in der App stumm; bei gleichzeitiger Pause hat Stumm Vorrang |
| Hardware-eigene rote Mute-Anzeige | Physische Mute-Taste aktiv; die App lässt diese Anzeige unverändert |
| Ursprünglicher Modus (bei uns DOA) | Aufnahme gestoppt / Recorder bereit |

Die Steuerung verändert weder die Hardware-Mute-Funktion noch die gespeicherte Firmware-Konfiguration. Ein separater Thread führt die USB-Zugriffe aus; Audioaufnahme und HTTP-Antworten warten nicht auf USB-Kommandos. Bei fehlendem Gerät oder Zugriffsfehler läuft die Audioverarbeitung weiter. Der Aufnahmescreen meldet einen LED-Fehler. Vorherige Ringwerte werden beim Stop und ordentlichen Dienstende wiederhergestellt; nach einem Prozessabbruch stellt der nächste Dienststart sie anhand einer lokalen Sicherung wieder her. Während der Dienst ausgefallen ist, kann die letzte Farbe stehen bleiben – die LED ersetzt keine Kontrolle des App-Status.

Für eine neue Pi-Installation einmalig `scripts/install-respeaker.sh` aus dem Repository ausführen. Das installiert PyUSB und eine auf USB-ID `2886:001a` begrenzte Geräteberechtigung für die Gruppe `audio`. Der Recorder läuft weiterhin als normaler Benutzer. Dies ist eine Host-Einrichtung, **kein Firmwareupdate**. Beim bloßen Umstecken ist sie nicht zu wiederholen. Die Quelle muss ausdrücklich als ReSpeaker-Karte gewählt sein; bei einer unbestimmten „default“-Quelle steuert die App keinen beliebigen USB-Ring.

## Fehler gezielt eingrenzen

| Beobachtung | Nächster Schritt |
| --- | --- |
| LEDs leuchten, aber kein Mikrofon in der App | Geräte aktualisieren; richtigen USB-C-Anschluss und ein sicher datenfähiges Kabel prüfen. |
| Auch `lsusb` zeigt kein ReSpeaker | Anderes Datenkabel und direkten Pi-Port testen. Bei weiterhin fehlender Erkennung Safe Mode prüfen. |
| ReSpeaker nur im Safe Mode sichtbar | USB-Verbindung funktioniert grundsätzlich; USB-Firmware / Recovery prüfen. Im Safe Mode ist keine normale Aufnahme möglich. |
| `lsusb` zeigt das Gerät, `arecord -l` aber keine Aufnahmequelle | Betriebsmodus und USB-Audio-Treiber prüfen; nicht wahllos Gerätepfade in der App ändern. |
| Quelle vorhanden, Aufnahme sehr leise | Normal sprechen, Hardware-Mute prüfen, Mikrofonöffnungen freihalten und Testaufnahme anhören. Ruhiger Raum allein kann einen niedrigen Pegel erklären. |
| „Gerät belegt“ / Aufnahme startet nicht | Laufenden Mikrofontest und andere Aufnahmeprogramme beenden; anschließend erneut testen. |
| Nach Abziehen erscheint die Quelle nicht mehr | Wieder anschließen und Geräte aktualisieren. Falls während einer Aufnahme abgezogen: betroffene Aufnahme und Fehlerhinweis prüfen. |
| Gute Pegel, aber Fehler im Transkript | Längere Sprachprobe aufnehmen; Mikrofonposition, Raumakustik und Transkriptionsmodell getrennt beurteilen. Firmware nicht allein wegen eines Erkennungsfehlers neu installieren. |

Unser erster Test im ruhigen Raum war sehr leise. Im gesprochenen Folgetest erreichte der Pegel **61/100**, ohne übersteuerte Samples. Whisper Medium erkannte Sprache, aber nicht fehlerfrei; die fünf Sekunden benötigten rund **80 Sekunden**. Dies ist ein einzelner Kurztest und keine belastbare Hochrechnung für eine Stunde Audio. [Messwerte und Installationsprotokoll](respeaker-2026-10-13/README.md)

## Technische Prüfung auf dem Pi

Diese Befehle lesen den Zustand aus; sie installieren keine Firmware:

```bash
lsusb
arecord -l
cat /proc/asound/card*/stream0
sudo /home/chris/respeaker-tools/venv/bin/python \
  /home/chris/respeaker-tools/xvf_host.py VERSION
```

Erwartet werden das ReSpeaker als USB- und ALSA-Gerät sowie `VERSION: [2, 1, 1]` für unseren geprüften Stand. `VERSION` ist im Safe Mode nicht als normaler Firmware-Nachweis zu erwarten.

Die Diagnosewerkzeuge liegen auf unserem Pi unter `/home/chris/respeaker-tools/`. Die separate Python-Umgebung enthält PyUSB 1.3.1 und libusb-package 1.0.30.0; das offizielle `xvf_host.py` ist unverändert. Die App benötigt diese Werkzeuge nicht für normale USB-Aufnahmen. Bei einer frischen SD-Karte müssen sie bei Bedarf neu eingerichtet werden.

## Firmware umstellen oder wiederherstellen – nur bei Bedarf

Ein Firmwarewechsel ersetzt die Betriebsfirmware im Mikrofon. Vorher den laufenden Recorder-Test beziehungsweise die Aufnahme beenden, das konkrete Image festlegen und die Änderung mit dem Geräteverantwortlichen abstimmen. Während des Schreibens USB und Strom verbunden lassen.

1. Wenn normale USB-Erkennung vorhanden ist, zuerst die Version auslesen und den Bedarf prüfen. Safe Mode ist für ein regulär erreichbares DFU-Gerät nicht bei jedem Update nötig.
2. Falls I²S-Firmware oder eine nicht startende Betriebsfirmware vermutet wird: vollständig von Strom trennen, **Mute gedrückt halten**, USB wieder anschließen. Rot blinkende LED signalisiert Safe Mode.
3. `sudo dfu-util -l` ausführen. Es muss beim richtigen ReSpeaker **DFU Upgrade, alt=1** erscheinen. Wenn auch Safe Mode nicht erkannt wird, bei Kabel, Port und Stromversorgung weitersuchen statt blind zu flashen.
4. Nur ein offizielles USB-Image aus dem Herstellerrepository verwenden. Für den hier dokumentierten Stand sind Datei, Commit und Prüfsumme unten festgehalten.
5. Nach der Installation Neustart, USB-/ALSA-Erkennung, Versionsabfrage und den gesprochenen Mikrofontest prüfen.

Der am 13.10.2026 verwendete Ablauf für das **bereits auf unserem Pi vorhandene, geprüfte Image** lautet:

```bash
cd /home/chris/respeaker-tools
printf '%s\n' \
  '85e9a89d859f0a73c52df661190adf77a6fb655c58d8bf4162924d45849c5057  firmware/respeaker_xvf3800_usb_dfu_firmware_v2.1.1.bin' \
  | sha256sum -c -

# Erst bei erfolgreicher Prüfsumme und eindeutig erkanntem Zielgerät ausführen.
# Bei mehreren ReSpeakern das gewünschte Gerät zusätzlich gezielt auswählen.
sudo dfu-util -d 2886:001a -R -e -a 1 \
  -D firmware/respeaker_xvf3800_usb_dfu_firmware_v2.1.1.bin
```

`alt=1` bezeichnet die Upgrade-Partition. Factory- und DataPartition nicht als Schreibziel verwenden. Keine pauschale Flash-Löschung und kein `CLEAR_CONFIGURATION` zur gewöhnlichen Anschlussdiagnose. Das ursprüngliche Firmware-Image unseres Geräts wurde vor dem Wechsel nicht gesichert; eine Wiederherstellung bedeutet daher eine gezielte Installation eines passenden offiziellen Images, nicht ein versprochenes Zurücksetzen auf den unbekannten Ausgangsstand.

Geprüftes Herstellerrepository: Commit `4b49bfd19977c63cf6e90dfe9e5827e74e20bf6d`, Datei `xmos_firmwares/usb/respeaker_xvf3800_usb_dfu_firmware_v2.1.1.bin`. Die Prüfsumme gilt ausschließlich für diese Datei. Bei zukünftigen Releases Version, Profil und neue Prüfsumme separat prüfen.

[Hersteller: DFU-Anleitung](https://github.com/respeaker/reSpeaker_XVF3800_USB_4MIC_ARRAY/blob/master/xmos_firmwares/dfu_guide.md) · [USB-Images und Änderungen](https://github.com/respeaker/reSpeaker_XVF3800_USB_4MIC_ARRAY/blob/master/xmos_firmwares/usb/readme.md) · [Python-Steuerung](https://github.com/respeaker/reSpeaker_XVF3800_USB_4MIC_ARRAY/blob/master/python_control/readme.md)

## Lautsprecher und Bluetooth

Das ReSpeaker stellt auch einen Audioausgang bereit; das ist kein Nachweis, dass angeschlossene Lautsprecher bereits geprüft wurden. Diese unter **Einstellungen → Audio → Lautsprecher** separat auswählen, Lautstärke setzen und den Testton prüfen. Kopfhörer-/Lautsprecheranschlüsse entsprechend der Herstellerdokumentation verwenden.

Das hier eingerichtete ReSpeaker wird über **USB** genutzt. Bluetooth-Geräte sind ein separater Weg: Die App listet verbundene Bluetooth-Mikrofone, wenn PipeWire/PulseAudio sie als Aufnahmequelle bereitstellt. Bloßes Pairing oder ein reines Musik-Wiedergabeprofil genügt nicht. [Details zur Aufnahmesteuerung und Bluetooth](capture-0.5.17/README.md)
