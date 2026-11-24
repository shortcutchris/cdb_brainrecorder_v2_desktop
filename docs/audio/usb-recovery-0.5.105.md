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

### Einrichtung, Wiederherstellungsversuch und Neustart

Der Nutzer hat den Administrator-Installer anschließend selbst ausgeführt.
Root-Eigentümer, enge sudo-Regel und Helferinhalt wurden verifiziert
(SHA-256 `8ef152d6d0203c9e89c7486dfd64f19259fba06dfd25986edeeb927e50ce5970`).
Die Vorprüfung um 14:12 MEZ hatte noch korrekt mit `sign_in_required`
abgebrochen; sie ist kein bestandener Klangtest.

Um **14:17 MEZ** wurde einmal über die normale, aktivitätsgeschützte
Wiederherstellungs-API versucht, den bereits ausgefallenen Controller neu zu
binden. Das schlug fehl: `Unable to change power state from D3cold to D0,
device inaccessible`, anschließend `Host controller not accessible` und
Fehler `-19`. Der abschließende Sicherheitsversuch des Helfers konnte ebenfalls
nicht binden. Die Oberfläche meldete den notwendigen Geräteneustart; die
Wartungssperre wurde freigegeben. Keine automatische Resetschleife.

Danach waren PCI-Konfigurationswerte ungültig (Header `7f`, Linkbreite `63`),
obwohl sysfs noch die gespeicherte Gerätekennung enthielt. `power/control=on`
und aktiver Runtime-Status waren bereits gesetzt. **D3cold ist hier kein Beweis
für eine absichtliche Energiesparabschaltung**: Bei unlesbarer Konfiguration
kann der PCI-Kern diesen Zustand ebenfalls annehmen. Ob die PCI-Verbindung
bereits vor dem Unbind vollständig unlesbar war, wurde nicht erfasst.
[PCI-Zustandsprüfung](https://github.com/raspberrypi/linux/blob/stable_20261103/drivers/pci/pci.c),
[xHCI-Initialisierung](https://github.com/raspberrypi/linux/blob/stable_20261103/drivers/usb/host/xhci.c).

Der reguläre, autorisierte Neustart über die Gerätefunktion um **14:19 MEZ**
stellte Hub und 188A wieder her. Anschließend wurde gezielt die interne 188A
mit 40 % und ohne Stummschaltung ausgewählt; der zuvor gespeicherte reSpeaker
war nicht die gewünschte interne Soundbar. Der Nutzer meldete sich erneut an.
Keine Änderung an Kernelparametern, Firmware, Ansagen oder Verkabelung.

### Echte Testläufe und Hörabnahme

Alle Zeiten am 24.11.2026, Europe/Berlin. App bleibt **0.5.105 / c4e367c**;
das separat gestartete Diagnosewerkzeug wurde auf **955c163** korrigiert.

| Lauf | Ergebnis | Dauer |
| --- | --- | --- |
| 14:21:09–14:22:03 | Diagnose abgebrochen, Soundbar blieb vorhanden | 54,520 s |
| 14:23:25–14:25:17 | Vollständige Reihe bestanden | 112,228 s |
| 14:26:07–14:27:59 | Vollständige Wiederholung bestanden | 111,562 s |
| 14:30:01–14:31:45 | 90 s überwachte Tonpause, vollständiger Stereotest, weitere 10 s Beobachtung bestanden | 104,011 s |

Der erste Abbruch war ein Fehler im Diagnosewerkzeug: Eine reale API-Abfrage
konnte die Wartefrist überschreiten und eine negative Schlafdauer verursachen.
Die Wartezeit wird jetzt nach der Abfrage erneut geprüft. Zwei zusätzliche
Regressionstests decken die Latenz und die datensparsame Fehlerausgabe ab;
**23 Diagnoseprüfungen bestanden**. Dieser Abbruch wird nicht als bestandene
Timerreihe und nicht als USB-Ausfall gewertet.

Die zwei vollständigen Reihen umfassen zusammen **sechs echte Timeralarme**,
zweimal alle drei Alarmklänge, zwölf Start-/Stoppzyklen, warme Wiederaufnahme,
Wiederaufnahme nach sieben Sekunden Ruhe und zwei parallele Startversuche je
Reihe. Jeweils genau ein paralleler Start wurde angenommen, der andere normal
gesperrt. Alle eigenen Timer wurden quittiert. In den gefilterten
Kernelbefunden aller vier Läufe gab es keine neuen USB-Fehler oder Abmeldungen.
Die 188A blieb verfügbar und ausgewählt. Der Nutzer bestätigte ausdrücklich:
**Testtöne und Timeralarme waren aus der eingebauten Soundbar hörbar.** Diese
Hörbestätigung gilt für die Testreihe, nicht als getrennte Kanal- oder
Langzeitabnahme jedes einzelnen Tons.

Das lokale Sprachpaket fehlt bzw. ist nicht gültig; `ready` und
`countdown_ready` sind false, alle Ansageschalter sind aus. Deshalb wurden
**gesprochene Ansagen und Countdown nicht am echten Gerät getestet**.
Einstellungen unverändert belassen. Kein Live-Cloudgespräch und keine
Mikrofonaufnahme für diese Prüfung angelegt.

Am tatsächlichen 1280×720-Pi-Kiosk nachgeprüft: 188A verbunden, 40 %, neuer
Wiederherstellungsbutton verfügbar, eigener Dialog mit zwei großen Kacheln.
„Zurück“ schließt ohne Reset. Der erledigte Timer zeigt eine große
Schließen-Kachel. Private Bildschirmnachweise und vollständige Laufberichte
liegen im Arbeitsartefakt `output/usb-audio-20261124`, nicht in Git.

Abschlusszustand: App, Kiosk und Zusatzdisplaydienst aktiv, angemeldet,
aufnahmebereit, kein offener Timer oder Alarm, Stereotest abgeschlossen.
Bereinigte Messdaten: [Abnahmeprotokoll](usb-recovery-0.5.105-acceptance.json).

### Verbleibende Grenze und nächster Fehlerfall

**Betrieb wiederhergestellt, dauerhafte Ursache nicht behoben oder bewiesen.**
Die Testreihe hat den früheren Controllerabsturz nicht reproduziert. Sie
entlastet weder Boardversorgung noch PCIe-Kabel, Controllerfirmware oder
Treiber vollständig. Der Wiederherstellungsbutton hilft nur, wenn der
Controller noch neu initialisiert werden kann; bei unzugänglichem PCI-Gerät
bleibt der reguläre Neustart notwendig.

Bei erneutem Ausfall zuerst USB-/PCI-/Kernelzustand sichern, bevor ein Reset
ausgeführt wird. Keine wiederholten Tontests bei verschwundener 188A. Für die
weitere Eingrenzung ist ein kontrollierter Vergleich der internen Boardkette
(Versorgung und FPC) bzw. ein späterer Direktanschluss hilfreich. Das ist am
derzeit verschlossenen Gehäuse noch nicht erfolgt. Keine unbewiesene
Kernel-/Firmwareänderung als dauerhaften Fix ausrollen.

Die Diagnosekorrektur und diese Abnahme ändern weder App-Paket noch
Systemrechte oder Image-Rezept. Das bereits dokumentierte Factory-Setup für
0.5.105 bleibt erforderlich; weiterhin kein neu gebautes oder bootgeprüftes
SD-Image.
