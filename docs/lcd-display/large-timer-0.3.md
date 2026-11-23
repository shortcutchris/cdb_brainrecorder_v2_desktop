# Timerdisplay 0.3.0: automatische Großansicht

23. November 2026. Zielgerät bleibt das Waveshare ESP32-S3-Touch-LCD-5B mit
1024 × 600 Pixeln. Dies ist die Firmware des zusätzlichen USB-Displays; die
Recorder-Anwendung auf dem Pi erhält ihre Großansicht separat.

## Bedienung und Darstellung

- Ein offener Timer erscheint automatisch groß. Die türkisfarbenen Ziffern sind
  als Siebensegmentanzeige gezeichnet und 200 Pixel hoch. Stunden, Minuten und
  Sekunden bleiben eindeutig getrennt. Auch mehr als 99 Stunden passen hinein.
- Ab zwei Timern erscheint wieder die Übersicht mit bis zu vier Karten pro Seite.
  Antippen einer Karte öffnet deren Großansicht. „Alle Timer“ führt zurück.
  Die Auswahl bleibt beim Umsortieren am selben Timer gebunden. Verschwindet er,
  erscheint die Übersicht beziehungsweise der letzte einzelne Timer.
- „Weitere Timer“ wechselt zwischen den tatsächlich vorhandenen Seiten.
- Ein vom Pi als abgelaufen oder verpasst gemeldeter Timer wird bernsteinfarben
  gekennzeichnet. Eine lokal auf null gezählte Restzeit allein löst keine falsche
  Ablaufmeldung aus: Dann steht ausdrücklich „Warte auf Timerstatus“.
- Bei unbekannter Uhrzeit stehen Striche statt einer erfundenen Restzeit. Nach
  drei Sekunden ohne gültige Daten verschwinden alle Zahlen. Das Display zeigt
  den Verbindungsverlust und zählt keine alten Daten weiter.
- Touch wechselt ausschließlich die Ansicht. Timer starten, stoppen und
  quittieren sowie Alarmton und Ansage bleiben Aufgabe des Pi.

## Ansichten aus der tatsächlichen Oberfläche

Die Bilder wurden mit derselben `display_ui.c` und LVGL 9.6.0 auf dem Mac erzeugt,
mit ausschließlich künstlichen Timerdaten. Sie sind keine Fotos des Geräts.

![Ein Timer in der automatischen Großansicht](large-timer-0.3/single.png)

![Vier Timer in der Übersicht](large-timer-0.3/multiple.png)

[Vom Pi bestätigter Ablauf](large-timer-0.3/due.png) ·
[Verbindung unterbrochen](large-timer-0.3/offline.png)

Die Vorschau ist unter `firmware/lcd-usb/host-preview` nachbaubar. Sie benötigt
vorhandene LVGL-9.6.0- und cJSON-Quellen, lädt nichts nach und öffnet keine Hardware:

```sh
cmake -S firmware/lcd-usb/host-preview -B /tmp/lcd-preview-build \
  -DLVGL_ROOT=/pfad/zu/lvgl-9.6.0 -DCJSON_ROOT=/pfad/zu/cjson
cmake --build /tmp/lcd-preview-build -j 8
mkdir -p /tmp/lcd-preview-images
/tmp/lcd-preview-build/preview /tmp/lcd-preview-images
```

Erzeugt vier PPM-Bilder. Die dokumentierten PNGs wurden verlustfrei daraus
konvertiert. Die Vorschau nutzt einen 32-Bit-Bildpuffer; auf der Hardware bleibt
die vorhandene 16-Bit-Ausgabe erhalten. Sie ersetzt keinen Hardwaretest.

## Prüfstand

- Native C-Prüfungen mit AddressSanitizer und UndefinedBehaviorSanitizer bestanden:
  Einzelansicht, Übergang zu mehreren Timern, Auswahl nach ID, Rückweg, Seitenzahl,
  Entfernen, Sekundenrundung, Zeitgrenzen, Segmentmuster und Datenverlust.
- Bestehende Protokollprüfung bestanden: Bindung, Wiederholungen, Ablauf der
  Datenfrist, neue Verbindung, ungültige Pakete und geleerte Timerliste.
- Dieselbe LVGL-Oberfläche kompiliert und bei 1024 × 600 für Einzel-, Mehrfach-,
  Alarm- und Offlinezustand visuell geprüft.
- Vollständiger ESP32-S3-Build mit ESP-IDF 5.5.2 erfolgreich:
  [CI-Lauf 45235773704](https://github.com/shortcutchris/cdb_brainrecorder_v2_desktop/actions/runs/45235773704),
  Quellstand `50162796614cb03053bd4d182024befbf84f9f4e`. Native Tests, simulierte
  USB-Integration und Prüfung der Hardwarekonfiguration bestanden.
- Das Anwendungsbild meldet 0.3.0, Projekt `cdb_lcd_usb`, IDF `v5.5.2` und ist
  838.288 Bytes groß. Es passt in die bestehende 1-MiB-Anwendungspartition.
  [Dateigrößen, Prüfsummen und aufgelöste Abhängigkeiten](large-timer-0.3/build-manifest.json).
  Dieses erste Paket ist wegen der zusätzlich aufgelösten indirekten
  Abhängigkeiten **nicht für den Firmwarewechsel freigegeben**.
- Der gezielte, rein lesende Verbindungsversuch am angeschlossenen Pi-Display
  (`read_mac`) erhielt keine Bootloaderantwort. Keine Flashdaten geschrieben;
  der USB-Begleitdienst wurde danach wieder gestartet. Der Firmwarewechsel
  benötigt den bestätigten BOOT/RESET-Ablauf des konkreten Geräts.
- Die tatsächliche Touchbedienung, Anzeigeausrichtung und Darstellung am
  Zusatzdisplay müssen nach dem gezielten Firmwarewechsel bestätigt werden.

## Auslieferung und Rücknahme

USB-Protokoll `cdb.lcd/1`, Produktkennung, Speicherlayout, Displaytreiber und
die bisherigen direkten Komponenten bleiben unverändert. Für einen zweiten
Build werden auch die indirekten Komponenten ausdrücklich auf die Versionen
der ersten Auflösung des erfolgreichen 0.2-Builds festgelegt
([CI 39670925360](https://github.com/shortcutchris/cdb_brainrecorder_v2_desktop/actions/runs/39670925360)).
Die Vorgaben stehen in `firmware/lcd-usb/main/idf_component.yml`; IDF bleibt 5.5.2.
Der alte finale Lock wird nicht übernommen: Er enthält lokale CI-Pfade und
stammt aus einem zweiten Auflösungslauf. Insbesondere war `cmake_utilities`
zunächst 0.5.3, im finalen Lock zusätzlich 1.1.1. Eine erfolgreiche neue
Auflösung und ein vollständiger Build mit den festen Vorgaben stehen noch aus.
Der erste, ungeflashte 0.3-Build bleibt als nachweislich kompilierender Kandidat
dokumentiert. Es wird keine binäre Reproduzierbarkeit behauptet. Firmwareversion:
0.3.0. Ein erfolgreiches Kompilat ersetzt weiterhin keine Geräteprüfung.
Die Anwendung benötigt ein separates Firmware-Update des Zusatzdisplays;
ein Recorder-App-Update oder ein neues Pi-SD-Image allein verändert es nicht.
Das Kundenimage übernimmt die bereits vorhandene Brücke und die passende
Recorder-Anwendung; kein automatisches Flashen beim Anstecken.

Vor dem Schreiben Gerät und Port eindeutig zuordnen, Flashbestand sichern und
den Begleitdienst freigeben. Die konkret erzeugten `flasher_args.json`,
Partitionstabelle und Bootloader prüfen. Das geprüfte Paket verwendet DIO,
16 MB und 80 MHz; Anwendungsstart `0x10000`. Seine Partitionstabelle ist
binär identisch mit dem archivierten 0.2-Build. Der Bootloader hat eine andere
Prüfsumme und darf nicht als binär unverändert bezeichnet werden. Keine geratenen
Offsets und kein pauschales Löschen des Flashs.
Eine Rücknahme verwendet den gesicherten, zum selben Gerät gehörenden Stand.
