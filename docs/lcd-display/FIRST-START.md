# LCD-Timerdisplay: Vorbereitung und erster Start

Auftrag vom **21. Oktober 2026**: Software auf dem Pi vorbereiten. Chris erwartet
das Display am **22. Oktober** und meldet sich nach dessen Ankunft. **Heute kein
Display flashen und keine Hardwareabnahme behaupten.** Kein automatisches Flashen
beim Anstecken. Diese Anleitung ist der Einstieg für die Fortsetzung.

## Zwei getrennte Installationen

1. **Pi:** Recorder 0.5.70 mit lesender Timer-API und separatem
   `cdb-lcd-display.service`, eigene Umgebung mit pyserial 3.5. Nach Einrichtung
   startet der Begleitdienst mit der Benutzersitzung und wartet auf unser Display.
2. **Display, nach Lieferung:** Firmware 0.2.0 gezielt auf das geprüfte Modul
   flashen. Werksfirmware wird nicht automatisch erkannt. Erst unsere Firmware
   meldet `CDB Timer Display` und unterstützt das Timerprotokoll.

Der Pi bleibt Timerquelle. Anstecken übernimmt vorhandene und neue Timer ohne
Schalter pro Timer; ohne Timer erscheint „Keine offenen Timer“. Touch wählt
Seite/Einzelansicht. Ton, deutsche Ansagen und Timerbedienung bleiben am Pi.

## Vorbereiteter Softwarestand

[PR #16](https://github.com/shortcutchris/cdb_brainrecorder_v2_desktop/pull/16),
Zielbranch `codex/recording-source-fix` (der bisherige produktive Entwicklungszweig).
Der konkrete Installationsnachweis steht nach Durchführung in
`pi-deployment-0.5.70.json` neben dieser Datei; Versionen nicht aus diesem Plan
als bereits installiert ableiten.

Geprüfter Firmware-Build: [Actions 39670925360](https://github.com/shortcutchris/cdb_brainrecorder_v2_desktop/actions/runs/39670925360),
Quellstand `4c4287c8dfbf05b50b4d2d9354d4c9d2282d494c`. Firmwaredateien in
nachfolgenden 0.5.70-Vorbereitungskommitts unverändert. Artefakt
`lcd-usb-compile-candidate` enthält Anwendung, Bootloader, Partitionstabelle,
`flasher_args.json` und aufgelöste Abhängigkeiten. Anwendungsdatei 838192 Bytes,
SHA-256 `191c6e05628584cfc303f7910d9e6bde3b93a82dfa9a34b93530ae134c3ae2b6`.
Lokale gesicherte Kopie auf Chris' Mac:
`/Users/chris/.local/share/cdb-lcd-research-20261021/build-auto-4c4287c/`.
Keine Binärdateien in Git. Vollständiges Artefakt zusammenhalten, nicht nur die
Anwendungsdatei flashen. Künftige Builds nur mit ihrem eigenen Manifest verwenden.

## Am Liefertag: Reihenfolge

1. Chris bestätigt die Ankunft. Platinenaufdruck, Modell und tatsächliche Revision
   prüfen: **Waveshare ESP32-S3-Touch-LCD-5B, SKU 28151, Touch, 1024 × 600**.
   Bei abweichendem Modell/800×480 stoppen und Firmwarezuordnung klären.
2. USB-Datenkabel, Herstellerunterlagen, Werksfirmware und dokumentierten
   BOOT/RESET-Wiederherstellungsweg bereithalten. Versorgung/Einschaltlast und
   Anschluss anhand des konkreten Boards prüfen. Nominale Herstellerangabe
   450 mA bei 5 V ersetzt keine Messung am vollständigen Pi-Aufbau.
3. Zuerst an einem separaten Computer anschließen. Den neu auftauchenden
   Geräteport eindeutig diesem Board zuordnen. **Nur diesen Port** verwenden;
   keine pauschale Suche mit Flashversuchen und kein `erase-all` aller Geräte.
4. Den geprüften Build mit ESP-IDF 5.5.2/esptool flashen. Im passenden
   Firmware-Buildverzeichnis ist `idf.py -p GEPRUEFTER_PORT flash` vorgesehen.
   Bei Verwendung des heruntergeladenen Artefakts die Offsets und Optionen aus
   dessen `flasher_args.json` übernehmen: Bootloader `0x0`, Partitionen `0x8000`,
   Anwendung `0x10000`, ESP32-S3, DIO, 16 MB, 80 MHz. Keine geratenen Offsets;
   die konkrete Flashzeile erst aus dem vorhandenen Artefakt und bestätigten Port
   bilden. Falls nötig den Hersteller-BOOT-Modus verwenden; keine eFuses ändern.
5. Neustart: USB muss als `CDB Timer Display`, Hersteller `CDB`, VID/PID
   `303a:4001`, zwölfstellige Chip-Seriennummer erscheinen. UART ist Diagnose;
   USB transportiert nur Timerdaten. Bild, Ausrichtung, Umlaute und Touch prüfen.
6. Zunächst synthetische Timer über den Begleitdienst am Computer prüfen. Danach
   Pi-Zustand rein lesend kontrollieren. Keine Aufnahme, Pause, Unterhaltung,
   laufende Audioausgabe oder andere Wartung für den ersten Hardwaretest stören.
   Falls belegt, warten. Keine bestehende Nutzeraktivität beenden.
7. Ein Display per USB an den vorbereiteten Pi stecken. Kein Port muss eingestellt
   werden. Dienststatus und `/api/lcd/timers` prüfen, nur technische Daten anzeigen;
   keine Timertexte, Aufnahmen oder Gesprächsinhalte exportieren.
8. Kontrollierte Tests mit Chris: kein Timer, ein Timer, mehrere Timer/Seiten,
   Einzelansicht, neuen Timer übernehmen, Änderung/Abbruch/Quittierung. Alarm und
   Ansage nur im vereinbarten freien Zustand testen. Bei Quellenverlust verschwinden
   nach drei Sekunden die Zahlen; sie dürfen nicht veraltet weiterzählen.
9. Kabel abziehen/neu stecken, Display neu starten und später Pi-Kaltstart im
   freien Zustand prüfen. Erkennung muss auch bei neuer Anschlussnummer gelingen.
   Bei mehreren passenden Displays wird keines neu automatisch ausgewählt.
10. Versorgung unter gemeinsamer Last und längeren Betrieb prüfen. Anschließend
    Aufnahme- und Rufwortfunktion vorsichtig mit Chris prüfen. Technisches
    `listening` allein ist keine natürliche Erkennungsabnahme.

Ergebnisse mit Datum, Boardrevision, Firmwarehash, Versorgung und tatsächlichen
Beobachtungen hier ergänzen und im Pi-Studio-Projektbuch sichern. Fehlende Tests
bleiben offen. Kein CAD-/Druckstand ändert sich durch diesen Softwaretest.

## Diagnose und Rücknahme

- `systemctl --user status cdb-lcd-display.service`: Ohne Display darf der Dienst
  aktiv warten; das beweist noch keine physische Verbindung.
- `systemctl --user disable --now cdb-lcd-display.service`: Zusatzdienst beenden.
  Timer und Recorder bleiben davon unabhängig.
- Keine Anzeige: Datenkabel/Boardmodus, Produktkennung, USB-Rechte, ein statt
  mehrere Displays und lokale Timer-API prüfen. Generische ESP-Werksfirmware wird
  absichtlich ignoriert. Kein probeweises Öffnen anderer Audio-/USB-Geräte.
- Vor App-Rollback den Zusatzdienst deaktivieren. Vorversion 0.5.69 besitzt die
  neue Timer-API nicht. Signierte Rücknahme benötigt den etablierten Updateweg;
  keine Release-Sequenz oder Prüfsignatur umgehen.
- Firmware-Rücknahme erfolgt separat über den bestätigten Board-Port und die
  passende gesicherte Herstellerfirmware. Nie automatisch beim USB-Anstecken.

## Kundenimage und bestehende Geräte

Das signierte App-Paket enthält API und Begleitmodul, aber keinen Installer,
keine zusätzliche Python-Umgebung und keine Displayfirmware. Der Installer wird
separat aus dem geprüften Commit bereitgestellt, auf signierten Geräten mit
`--app-root /home/chris/.local/share/cdb-recorder-app/current`. Die stabile
Symlinkadresse bleibt in der Dienstkonfiguration erhalten. Die Factory-Rezeptur
aktiviert den Zusatzdienst vor Hardwareabnahme weiterhin nicht. Es wurde für
diese Änderung kein SD-Image gebaut oder bootgeprüft.
