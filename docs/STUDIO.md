# Recorder Studio 0.4.3

Die HTML-Oberfläche übernimmt die ausgewählte zweite Studio-Variante. Das bestehende Python-Backend verarbeitet weiterhin Aufnahmen und lokale Modelle. `web_server.py` verwendet den vorhandenen `LocalController`, die ursprüngliche `data/sessions.db`, bestehende QSettings-Prompts und die fest versionierte gemeinsame Python-Engine 0.2.6. Es gibt eine Aufnahmeinstanz und einen FIFO-Verarbeiter.

## Start auf dem Pi

Nach Sicherung und Beenden der bisherigen Anwendung:

```sh
./scripts/install-studio.sh
./kiosk.sh
```

Der Benutzerdienst `cdb-recorder-studio.service` startet das Python-Backend; der Desktop-Autostart startet Chromium im Kiosk. Die Oberfläche ist auf dem Pi unter `http://127.0.0.1:8088/` erreichbar. Der Server bindet ausschließlich an Loopback und prüft Host, Origin und CSRF. Chromium verwendet ein eigenes lokales Profil, ohne Schlüsselbundanmeldung. Schrift und Symbole werden lokal ausgeliefert. Das Mikrofon wird am Pi aufgenommen; der Browser erhält keine Mikrofonberechtigung. Für Fernzugriff ist ein SSH-Tunnel erforderlich.

Das Installationsskript ändert nur Anwendungsdienst und Starter; es installiert keine Systempakete oder Modelle. `run.sh` bleibt als Starter der bisherigen Python/Qt-Oberfläche erhalten. Sie kann wegen der gemeinsamen exklusiven Datensperre nicht gleichzeitig mit dem Studio laufen.

## Bedienung und Daten

Der Aufnahmebutton startet oder beendet eine Aufnahme unabhängig vom rechts ausgewählten Meeting. Transkription und Zusammenfassung laufen nacheinander in der bestehenden Warteschlange; weitere Aufnahmen sind dabei möglich. Notizen lassen sich parallel bearbeiten. Texte werden verzögert automatisch gespeichert. Bei einem Speicherfehler bleibt die Navigation möglich und der Entwurf lokal erhalten. Ein Konflikt mit einer neueren Fassung verhindert das Überschreiben; ein lokaler Entwurf bleibt erhalten. Während der KI-Verarbeitung sind deren Ergebnisfelder geschützt.

Bibliothek, Suche, Umbenennen, Markdown-Export, Wiedergabe, erneute Transkription, Fehlerwiederholung, vorhandene und eigene Prompts sowie Mikrofon- und Modelleinstellungen sind angebunden. Die integrierte Touch-Tastatur steht in der Seitenleiste und in Dialogköpfen bereit; sie unterstützt Umlaute, Großbuchstaben, Zahlen, Sonderzeichen und Zeilenumbrüche.

Ein Mikrofon muss gefunden, getestet und die Einrichtung abgeschlossen sein, bevor eine echte Aufnahme startet. Bestehende Modelle und Auswahlen werden übernommen. Der ausdrückliche Modelltest nutzt künstliche Sprache, denselben FIFO-Verarbeiter und erscheint nicht als persönliches Meeting. Die konservative Pi-Vorprüfung sperrt ihn bei angeforderter Kühlung ohne Lüfter-Tachosignal, ab 65 °C oder unter 4 GiB verfügbarem RAM.

## Isolierte Funktionsvorschau

```sh
venv-local-ai/bin/python scripts/studio_preview.py /tmp/recorder-studio-preview --port 8094
```

Die Vorschau verwendet eine eigene dauerhafte Datenablage, künstliches Audio und einen austauschbaren Testprozessor. Aufnahme, Warteschlange, Speicherung und HTTP-Anbindung sind echt; die Vorschau misst keine Modellqualität. Sie greift nicht auf persönliche Pi-Meetings zu.

## Rückkehr zur bisherigen Oberfläche

Studio-Dienst beenden und deaktivieren, den eigenen Kiosk schließen und die zuvor gesicherten Desktop-/Autostart-Dateien zurückkopieren. Danach `./run.sh` starten. Die Datenbank bleibt dieselbe; aktuelle Bearbeitungen bleiben erhalten. Eine ältere Datenbanksicherung nur nach ausdrücklicher Entscheidung wiederherstellen, weil sonst neuere Änderungen verloren gingen.

Der Installationslauf vom 11.10.2026 verwendet die Sicherung `/home/chris/recorder-backups/before-studio-0.4.0/`: konsistente Sitzungs- und Queue-Datenbanken, QSettings, Starter, bisheriger Quelltext und SHA-256-Prüfsummen der 17 Audioaufnahmen. Die Aufnahmen selbst werden bei der Installation nicht geändert.

`AudioRecorderApp.clean.conf` enthält den geprüften Einstellungenstand nach Entfernung eindeutig eigener Test-Prompts. Die ursprünglichen und zwischenzeitlichen Dateien bleiben zur Nachvollziehbarkeit ebenfalls gesichert. Vorschau und Tests verwenden ausdrücklich eigene QSettings-Dateien; eine Änderung des globalen Qt-Standardformats allein isoliert den Konstruktor mit Organisationsnamen nicht.

## Auditkorrekturen 0.4.1

Die vom Server gelieferten Aktionsregeln gelten auch unabhängig von der Oberfläche:

| Zustand | Erlaubt | Wartet / gesperrt |
| --- | --- | --- |
| Normale KI-Verarbeitung / Queue | Neue Aufnahme, Notizen, Lesen, Konfiguration für neue Aufträge | Downloads, Modelltest; Löschen/Neuverarbeitung des beschäftigten Meetings |
| Aufnahme | Stop auch im Dialogkopf, Notizen, normale KI-Queue | Mikrofontest, Konfiguration, Modellinstallation/-test, Einrichtung abschließen |
| Mikrofontest | Lesen und Notizen, normale KI-Queue | Aufnahme und weitere Audio-/Modelloperationen |
| Modelldownload / Modelltest | Lesen, lokale Entwürfe, Prompts | Neue Aufnahme, Konfiguration, konkurrierende Modelloperationen und neue KI-Aufträge |
| Zu wenig Speicher | Lesen, Notizen, laufende Aufnahme sicher stoppen | Neue Aufnahme / Mikrofontest / Modelltest |
| Verbindung unterbrochen / veraltet | Gelesene Texte und lokale Entwürfe bearbeiten, lokal exportieren | Serveraktionen bis frischer Zustand vorliegt |

Threadzahl, Whisper-Programm, Modellwahl und Prompt werden pro Auftrag festgehalten. Ein aktiver technischer Modelltest behält seine Identität über einen Dienstneustart. HTTP-Aktionen verwenden dieselbe Lockreihenfolge wie die Statusabfrage; paralleles Polling und Stoppen wird getestet.

„Entwurf lokal sichern“ zeigt alle aktuell bearbeiteten Textfelder zum Kopieren oder als Markdown-Datei, ohne vorheriges Speichern. „Erneut speichern“ wiederholt die optimistisch geprüfte Speicherung. „Aktuelles Feld vergleichen“ zeigt lokale und gespeicherte Fassung; erst die ausdrückliche Auswahl übernimmt eine Fassung. Eine zwischenzeitliche weitere Änderung wird erneut als Konflikt abgefangen. Lokale Browserdaten bleiben im gleichen Kioskprofil erhalten; Löschen des Browserprofils entfernt lokale Entwürfe.

Eine neue Verarbeitung bewahrt bisherige Ergebnisse, bis neue Ergebnisse vorliegen. Beim Löschen bleibt Audio erhalten, wenn eine andere Sitzung dieselbe Datei verwendet. Wiedergabe wird beim Aufnahmestart pausiert; während Aufnahme erfordert die Wiedergabe einen Kopfhörerhinweis. Die Tastatur wählt sichtbare Textfelder; die Ansicht passt sich bei geöffneter Warteschlange und bei 1024×600 mit Tastatur an.

Die Abnahme nutzt ausschließlich isolierte synthetische Sitzungen und kontrollierte Fehlerzustände. Echte Mikrofonqualität und Modellleistung werden dadurch nicht nachgewiesen. Keine Firmware-, Lüfter- oder Betriebssystemänderungen gehören zu diesem Update.

## Modellkatalog 0.4.2

Die Dropdowns wählen einen Kandidaten zur Ansicht; sie ändern keine aktive Modellwahl. Quelle, Lizenz, Downloadgröße, Installation, Kompatibilität, Gerätetest und Aktivierung sind getrennt sichtbar. Neue Kandidaten benötigen einen erfolgreichen technischen Test vor der ausdrücklichen Aktivierung. Der Test verwendet einen eigenen Auftrags-Snapshot; aktive Modelle und vorhandene Aufträge bleiben erhalten. Ein geänderter Modelldigest oder eine geänderte Ollama-Version macht den Testnachweis ungültig.

Whisper medium, large-v3-turbo und large-v3 bleiben mehrsprachige whisper.cpp-Modelle. Qwen3.5 4B Q4_K_M ist ein ungeprüfter zusätzlicher Textkandidat mit ausdrücklich benanntem Hugging-Face-GGUF. Thinking wird über `think:false` der Runtime abgeschaltet; `/nothink` wird nicht als Ersatz verwendet. Architektur, Quantisierung und Thinking-Vorlage müssen passen; unerwartetes Thinking lässt den echten Test scheitern. Quellen, technische Grenzen und spätere Kandidaten: [kanonische Modelldokumentation](https://github.com/shortcutchris/raspberry_pi_meeting_recorder/blob/main/docs/modelle.md).

## Touch-Dialoge 0.4.3

Dialograhmen und Kopf bleiben fest. In den Einstellungen bleiben Audio/Modelle/Prompts und die Hauptaktion sichtbar; nur der Inhalt des ausgewählten Bereichs scrollt. Bibliothekssuche ist ebenfalls fest. Meetingdetails, Export, Wiedergabehinweis und Konfliktvergleich nutzen denselben Aufbau. Schließen und Aufnahme-Stopp bleiben im Kopf erreichbar.

Touchfelder sind mindestens 56 Pixel hoch; die vierzeilige Bildschirmtastatur verwendet eigene 44-Pixel-Mindesthöhen, damit Tasten nicht überlappen. Bei geöffneter Tastatur schrumpft der Dialog oberhalb der Tastatur und das fokussierte Eingabefeld wird in den sichtbaren Inhaltsbereich gescrollt. Prompt löschen befindet sich bewusst im Inhalt, Speichern bleibt unten. Änderungen an Aufnahme-/Queue-/Modellsperren waren nicht erforderlich.

Geprüft am 12.10.2026 mit isolierter synthetischer Bibliothek und bestehendem Python-Backend auf dem Pi: 1280×720 und 1024×600, Modelle lang gescrollt, Bibliothek mit 28 Einträgen, Prompt-Eingabe mit Tastatur, Meetingdetails/Export, laufende Aufnahme mit gesperrter Modellwahl und Stopp im Dialogkopf. 29 vorhandene Native-/Studio-Tests bestanden. [Screenshots und Prüfdetails](touch-dialogs/README.md). Keine echten Meetings oder Mikrofonaufnahmen für diese Prüfung.

[CAD, Gehäusevorschauen und Einkaufsliste im gemeinsamen Raspberry-Pi-Repository](https://github.com/shortcutchris/raspberry_pi_meeting_recorder/tree/main/hardware/enclosure).
