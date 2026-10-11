# Recorder Studio 0.4.0

Die HTML-Oberfläche übernimmt die ausgewählte zweite Studio-Variante. Das bestehende Python-Backend verarbeitet weiterhin Aufnahmen und lokale Modelle. `web_server.py` verwendet den vorhandenen `LocalController`, die ursprüngliche `data/sessions.db`, bestehende QSettings-Prompts und die unveränderte, fest versionierte gemeinsame Engine. Es gibt eine Aufnahmeinstanz und einen FIFO-Verarbeiter.

## Start auf dem Pi

Nach Sicherung und Beenden der bisherigen Anwendung:

```sh
./scripts/install-studio.sh
./kiosk.sh
```

Der Benutzerdienst `cdb-recorder-studio.service` startet das Python-Backend; der Desktop-Autostart startet Chromium im Kiosk. Die Oberfläche ist auf dem Pi unter `http://127.0.0.1:8088/` erreichbar. Der Server bindet ausschließlich an Loopback und prüft Host, Origin und CSRF. Chromium verwendet ein eigenes lokales Profil, ohne Schlüsselbundanmeldung. Schrift und Symbole werden lokal ausgeliefert. Das Mikrofon wird am Pi aufgenommen; der Browser erhält keine Mikrofonberechtigung. Für Fernzugriff ist ein SSH-Tunnel erforderlich.

Das Installationsskript ändert nur Anwendungsdienst und Starter; es installiert keine Systempakete oder Modelle. `run.sh` bleibt als Starter der bisherigen Python/Qt-Oberfläche erhalten. Sie kann wegen der gemeinsamen exklusiven Datensperre nicht gleichzeitig mit dem Studio laufen.

## Bedienung und Daten

Der Aufnahmebutton startet oder beendet eine Aufnahme unabhängig vom rechts ausgewählten Meeting. Transkription und Zusammenfassung laufen nacheinander in der bestehenden Warteschlange; weitere Aufnahmen sind dabei möglich. Notizen lassen sich parallel bearbeiten. Texte werden verzögert automatisch gespeichert und bei Register- oder Meetingwechsel geschrieben. Ein Konflikt mit einer neueren Fassung verhindert das Überschreiben; ein lokaler Entwurf bleibt erhalten. Während der KI-Verarbeitung sind deren Ergebnisfelder geschützt.

Bibliothek, Suche, Umbenennen, Markdown-Export, Wiedergabe, erneute Transkription, Fehlerwiederholung, vorhandene und eigene Prompts sowie Mikrofon- und Modelleinstellungen sind angebunden. Die integrierte Touch-Tastatur steht in der Seitenleiste und in Dialogköpfen bereit; sie unterstützt Umlaute, Großbuchstaben, Zahlen, Sonderzeichen und Zeilenumbrüche.

Ein Mikrofon muss gefunden, getestet und die Einrichtung abgeschlossen sein, bevor eine echte Aufnahme startet. Bestehende Modelle und Auswahlen werden übernommen. Der ausdrückliche Modelltest nutzt künstliche Sprache, denselben FIFO-Verarbeiter und erscheint nicht als persönliches Meeting. Er kann auf einem unzureichend gekühlten Pi erheblich länger dauern.

## Isolierte Funktionsvorschau

```sh
venv-local-ai/bin/python scripts/studio_preview.py /tmp/recorder-studio-preview --port 8094
```

Die Vorschau verwendet eine eigene dauerhafte Datenablage, künstliches Audio und einen austauschbaren Testprozessor. Aufnahme, Warteschlange, Speicherung und HTTP-Anbindung sind echt; die Vorschau misst keine Modellqualität. Sie greift nicht auf persönliche Pi-Meetings zu.

## Rückkehr zur bisherigen Oberfläche

Studio-Dienst beenden und deaktivieren, den eigenen Kiosk schließen und die zuvor gesicherten Desktop-/Autostart-Dateien zurückkopieren. Danach `./run.sh` starten. Die Datenbank bleibt dieselbe; aktuelle Bearbeitungen bleiben erhalten. Eine ältere Datenbanksicherung nur nach ausdrücklicher Entscheidung wiederherstellen, weil sonst neuere Änderungen verloren gingen.

Der Installationslauf vom 11.10.2026 verwendet die Sicherung `/home/chris/recorder-backups/before-studio-0.4.0/`: konsistente Sitzungs- und Queue-Datenbanken, QSettings, Starter, bisheriger Quelltext und SHA-256-Prüfsummen der 17 Audioaufnahmen. Die Aufnahmen selbst werden bei der Installation nicht geändert.

`AudioRecorderApp.clean.conf` enthält den geprüften Einstellungenstand nach Entfernung eindeutig eigener Test-Prompts. Die ursprünglichen und zwischenzeitlichen Dateien bleiben zur Nachvollziehbarkeit ebenfalls gesichert. Vorschau und Tests verwenden ausdrücklich eigene QSettings-Dateien; eine Änderung des globalen Qt-Standardformats allein isoliert den Konstruktor mit Organisationsnamen nicht.
