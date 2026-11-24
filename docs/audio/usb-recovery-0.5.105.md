# USB-Soundbar: Wiederherstellung und Diagnose · 0.5.105

Stand: 24.11.2026. Recorder-Pi 5, interne 188A (`0020:0b21`), Waveshare
PCIe TO USB 3.2 Gen1 Board (C), VIA VL805/806 (`1106:3483`).

## Befund und offene Ursache

Am 24.11. um 09:40:21 MEZ wurde ein Lautsprechertest gestartet. Um 09:40:26
meldete der Kernel Configure-Endpoint-Timeout und `HC died`. Danach fehlten Hub
und 188A in USB/ALSA/PipeWire. Der PCIe-Controller blieb vorhanden. PipeWire und
WirePlumber liefen weiter. reSpeaker, NFC und Zusatzdisplay hängen an anderen
Controllern. Ein Timer-Zusammenhang ist bisher **nicht nachgewiesen**.

Die Bandbreitenmeldung mit Fehler `-62` beweist keine erschöpfte Bandbreite.
Gen1, 100 ms Resetverzögerung und 40-Bit-DMA waren bereits aktiv. Kein
Unterspannungsflag; separate Boardversorgung und PCIe-Kabel sind damit nicht
entlastet. Kein Vergleich am direkten Pi-USB-Port: Das Gehäuse ist geschlossen.

Primärquellen: [USB-Interface-Wechsel](https://github.com/raspberrypi/linux/blob/rpi-6.18.y/drivers/usb/core/message.c),
[xHCI](https://github.com/raspberrypi/linux/blob/rpi-6.18.y/drivers/usb/host/xhci.c),
[PCI-Quirks](https://github.com/raspberrypi/linux/blob/rpi-6.18.y/drivers/usb/host/xhci-pci.c).

## Bedienung und Einrichtung

**Einstellungen → Audio → Lautsprecher → USB-Audio wiederherstellen**.
Eigener Dialog mit zwei großen Kacheln. Aufnahme/Pause, Talk, Testausgabe,
Wiedergabe, Timer, Verarbeitung, Upload, Anmeldung und Wartung blockieren den
Start erneut im Backend. Der Pi bleibt eingeschaltet. Konto und gespeicherte
Lautsprecherwahl werden nicht absichtlich geändert. Danach bei Bedarf 188A
wählen und den Testton hören. USB-Erkennung allein gilt nicht als Audio-Erfolg.

Bestehende Geräte benötigen einmalig aus dem geprüften Repository:

```sh
sudo bash scripts/install-usb-audio-recovery.sh BENUTZERNAME
```

Der Installer installiert `/usr/local/sbin/cdb-usb-audio-recover` und erlaubt
dem App-Benutzer ausschließlich `check`/`recover`. sudoers wird vorher validiert.
Keine weiteren Root-Kommandos, frei wählbaren Controller oder Shellparameter.
Die Installation selbst führt keinen Reset aus.

Der Helfer akzeptiert genau einen passenden VIA-Controller mit freigegebenen
Root-Hubs, VIA-Hub und 188A. Speicher, Netzwerk und unbekannte Geräte sperren.
Ein toter Controller ohne USB-Kinder ist wiederherstellbar. Unmittelbar vor
einem einzelnen Unbind/Bind wird erneut geprüft. Kein globales Modulentladen,
PCI-Remove oder Busreset. Root-Dateirechte, Sperrdatei, 30-s-Abstand und Zeitlimit
sind unabhängig vom Webprozess. Abbruchsignale versuchen abschließend das
Binden; die App bleibt bis zum bestätigten Prozessende gesperrt. Kein
automatischer Reset bei Alarmen und keine Wiederholungsschleife.

## Reproduzierbare Testreihe

```sh
python3 scripts/diagnose_usb_audio.py --output /tmp/usb-audio-preflight.json
python3 scripts/diagnose_usb_audio.py --run --output /tmp/usb-audio-run.json
```

Ohne `--run` nur lesende Vorprüfung. Für den Lauf: angemeldet, Betreiberzugriff
frei, 188A gewählt, hörbare Lautstärke. Gerät etwa zwei Minuten exklusiv für
den Test freihalten, insbesondere keine weiteren manuellen Klangtests.

| Szenario | Prüfung |
| --- | --- |
| Normaler Test | Links/rechts, Ausgang bleibt vorhanden |
| Warme Wiederholung | Erneuter vollständiger Stereotest vor fünf Sekunden Ruhe |
| Wiederaufnahme nach Ruhe | Sieben Sekunden überwachte Ruhe, danach vollständiger Stereotest |
| Drei Alarmklänge | Glocke, Klang, Impuls separat |
| Sechs Start-/Stoppwechsel | Prozessende und Freigabe der Ausgabe |
| Drei kurze echte Timer | Ablauf, Alarmstart, eigenen Alarm quittieren |
| Lokale Ansagen/Countdown | Bestehende Einstellung bleibt; vorhandenen Countdown mitprüfen |
| Gleichzeitige Starts | Genau ein Start, zweite Anfrage gesperrt |
| 30 Sekunden Ruhe | Kein verspäteter Ausfall |

Keine Mikrofonaufnahme, Cloud-Konversation oder Änderung von Route, Lautstärke
und Ansagen. Nur eigene markierte Testtimer werden beendet. Fremde Timer oder
Benutzerwechsel brechen ab. Bei Verlust der 188A sofortiger Abbruch und
gefilterte USB-/ALSA-/Kernelbefunde mit Zeiten. Bericht ohne Kontoinhalte,
Tokens oder Aufnahmen; kein Ersatz für einen Hörtest. Audio-Testläufe haben
keine individuelle API-Kennung, daher die exklusive Gerätebenutzung.

Die Ereignisse `warm_repeat` und `idle_resume` enthalten Zeitpunkte und
USB-Befunde unmittelbar vor/nach den Vergleichsläufen. Der warme Vergleich
berücksichtigt die normale Ausgabesperre nach dem Ton. Sein Fünfsekundenfenster
wird konservativ ab der letzten als laufend bestätigten Ausgabe geprüft,
unmittelbar vor der Startanfrage und nochmals nach deren Bestätigung. Wird es
wegen langsamer Antworten verpasst, bricht der Test mit
`warm_repeat_window_missed` ab. Ein solcher Lauf beweist keine warme
Wiederaufnahme. Die USB-Abfragen in diesen Phasen lesen nur sysfs; der langsamere
Journalabruf bleibt vor/nach der Testreihe.

Die Offline-Zeitmodellprüfung mit dreisekündigen Tönen, zweisekündiger
Ausgabesperre und aktiviertem Countdown benötigt rund 119 Sekunden. Das
150-Sekunden-Limit bleibt bestehen und enthält somit rund 30 Sekunden Reserve
für lokale Abfragen. Ein langsamer oder blockierter Lauf wird abgebrochen;
abschließende Diagnose und sichere Bereinigung können darüber hinaus dauern.
Das ist eine Budgetabschätzung, keine gemessene Laufzeit am Pi.

## Offener Vergleichskandidat: gerätespezifischer Linux-Quirk

**Nicht angewandt und nicht als Lösung dieses Ausfalls bewiesen.** Upstream
Commit `5a36d2bda9c8303a46a52beafcb0711eff8d6a42` ergänzt für die genaue USB-ID
`0020:0b21` die Flags `FORCE_IFACE_RESET` und `IFACE_DELAY`. Der ursprüngliche
Bericht betrifft Interfacefehler nach Suspend/Resume an einem als GHW-123P
bezeichneten Gerät. Unsere Soundbar meldet sich als 188A: die ID stimmt überein,
eine identische Hardwareausführung ist damit nicht bewiesen.
[Originalpatch](https://www.spinics.net/lists/kernel/msg6047888.html),
[Upstream-Tabelle](https://github.com/torvalds/linux/blob/master/sound/usb/quirks.c).

Der geprüfte Pi läuft mit `6.18.60-1+rpt1` vom 03.11.2026. Im passenden
Raspberry-Pi-Quellstand `stable_20261103` fehlt der Eintrag für `0020:0b21`.
Die beiden Flags und der VID/PID-begrenzte `quirk_flags`-Parser sind bereits
implementiert; der Parameter am Pi war bei der lesenden Prüfung leer.
Der eng begrenzte Vergleichswert wäre
`0020:0b21:FORCE_IFACE_RESET|IFACE_DELAY`. Er wird beim Erstellen der ALSA-Karte
eingelesen, also erst bei einem neuen Probe wirksam. Weder Diagnosewerkzeug
noch Wiederherstellungsbutton setzen diesen Parameter. Ein Vergleich müsste
separat geplant, mit gesichertem Ausgangswert und anschließendem Rückbau
dokumentiert werden; kein globales Modulentladen und kein Firmwarewechsel.
[Pi-Gerätetabelle und Parser](https://github.com/raspberrypi/linux/blob/stable_20261103/sound/usb/quirks.c),
[Einlesen beim Probe](https://github.com/raspberrypi/linux/blob/stable_20261103/sound/usb/card.c).

Die Verzögerung beträgt 50 ms **nach erfolgreichem** USB-Interfacewechsel.
Unser Configure-Endpoint-Timeout entsteht davor. Der Quirk könnte eine
problematische Abfolge beim Stoppen/Wiederstarten vermeiden; ein bereits
abgestürzter Hostcontroller wird dadurch nicht repariert. Deshalb zuerst einen
normalen Test nach Wiederherstellung prüfen, bei erneutem `HC died` sofort
abbrechen und erst danach einen einzelnen kontrollierten Vergleich erwägen.
[Endpoint-Ablauf](https://github.com/raspberrypi/linux/blob/stable_20261103/sound/usb/endpoint.c).

## Fehlererkennung, Update und Image

Ein mit Status 0 beendetes `paplay` gilt nicht als bestandene Wiedergabe, wenn
der ursprüngliche Ausgang verschwunden ist. Fehlender/stummer Ausgang ersetzt
alte Erfolgsmeldungen. Fehlgeschlagene Alarmstarts protokollieren ihre Ursache,
ohne Timertexte.

Service, Oberfläche und Hilfe liegen in der signierten App-Allowlist.
App-Updates richten keine neuen Systemrechte ein. Das Diagnosewerkzeug bleibt
ein separat aufgerufenes Repository-Werkzeug. Das Image-Rezept kopiert beide
USB-Factorydateien aus getrackten Quellen und installiert für `cdb` im neuen
Root-Dateisystem. Exporttests prüfen den Factory-Einschluss und Ausschluss aus
App-Updates. Keine gemeinsamen Passwörter, Aufnahmen oder Geräteschlüssel.
Rezept vorbereitet bedeutet weder Image gebaut noch Boot-zertifizierung.

## Abnahmestand

226 Python-Prüfungen über die betroffenen Testsuiten bestanden (223 im breiten
Lauf, Diagnosewerkzeug danach von 18 auf 21 bestandene Fälle erweitert).
171 JavaScript-Prüfungen bestanden. Abgedeckt sind Helfer, Service,
API-/Aktivitätssperren, Audiofehler, Timer/Countdown, Sitzungsübergabe und
Factory-Export. Die neue Aktion und der Dialog wurden in einer lokalen Fixture
bei 1280 × 720 und 1024 × 600 in hellem und CDB-Design geprüft. Die Aktion ist
direkt sichtbar; der Dialog bietet zwei große Kacheln. Abbrechen startet keine
Wiederherstellung. Dies ersetzt keinen Fingertest am Pi.

### Installation und physische Anzeige

0.5.105 wurde am 24.11.2026 um 14:11 MEZ auf dem Recorder-Pi installiert:
Quellstand `c4e367ce06b8a02f126204e83a979dfe4bb3aa80`, signiertes Paket
`f5699e92d56fe5ed88b3da79b55499b4947ecce43c0156c457c6af54c6a3d0a4`.
158 App-Dateien verifiziert. Einstellungen, NFC-Zuordnungen, Raumpolicy und
Aufnahmebestand unverändert. App und Kiosk neu gestartet; Boot-ID unverändert,
Zusatzdisplaydienst unverändert, Wartungssperre freigegeben. Vor der Installation
war niemand mehr angemeldet; daher kein neuer Live-Nachweis der Kontoübergabe.

Die Lautsprecherseite wurde über einen privaten Bildschirmzugriff auf dem
tatsächlichen Pi-Kiosk geöffnet. Der neue Knopf ist sichtbar und gesperrt mit
Einrichtungshinweis. Der ausgewählte Ausgang ist weiterhin reSpeaker (40 %);
die interne 188A fehlt. Kein Testton an einen anderen Ausgang als vermeintlichen
Soundbar-Erfolg ausgegeben. Screenshots bleiben im privaten Arbeitsartefakt
`output/usb-audio-20261124`; keine privaten Bildschirmkopien im Repository.

Der neue Image-Bausatz wurde aus dem sauberen Commit exportiert: 165 Quelldateien,
200 Integritätseinträge, Factory-Helfer enthalten und aus dem App-Update
ausgeschlossen. Kein SD-Image gebaut oder auf Hardware gestartet.

### Noch offen

Der Administrator-Installer liegt geprüft auf dem Pi bereit, wurde aber noch
nicht ausgeführt. `sudo -n` erlaubt keine zusätzliche Systemeinrichtung.
Die automatische Terminal-Bedienung wurde vom Computer-Use-Schutz abgelehnt;
der Nutzer erhielt den konkreten Befehl zur eigenen Eingabe. Keine Umgehung,
kein USB-Reset und keine Kernelparameteränderung ausgeführt.

Die Diagnose-Vorprüfung um 14:12 MEZ brach vor Klangausgabe korrekt mit
`sign_in_required` ab. Dabei USB-/ALSA-Befund bestätigt: 188A fehlt,
NFC/reSpeaker/Zusatzdisplay vorhanden. Für die komplette echte Timer-Testreihe
sind erst Einrichtung, Wiederherstellung und Anmeldung erforderlich. Kein
bestandener Hardware- oder Hörtest behauptet. Wiederanlauf allein wäre zudem
kein Nachweis einer behobenen Hardwareursache.
