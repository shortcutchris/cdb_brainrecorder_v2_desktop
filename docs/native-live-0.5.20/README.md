# Abnahme 0.5.20 – Python-Audio für Live-Gespräche

13.10.2026, Raspberry Pi 5, Debian 13 arm64, Python 3.13, ReSpeaker XVF3800 USB-Firmware 2.1.1.

## Ergebnis

CDB Voice One erhält Audio direkt aus Python. Die Oberfläche zeigt die vorhandenen Pi-Audiogeräte und bietet keine Browserfreigabe oder getrennte Mikrofonliste mehr. Der konfigurierte ReSpeaker-Eingang wird eindeutig auf seine PipeWire-Quelle abgebildet, damit Ein- und Ausgabe derselben USB-Karte gleichzeitig funktionieren.

## Prüfungen

- Vollständige Python-Suite und JavaScript-Suite auf dem finalen Stand: siehe Deployment-Protokoll.
- Echte CDB-Staging-Sitzung mit künstlicher Sprache, `staging_playground`. Native WebRTC-Verbindung vom Pi, Rückkanal mit mehr als 1.800 empfangenen Audioblöcken. Vollständiger synthetischer Satz im Chat; Antwort unter anderem „Verstanden, Test erfolgreich.“ Keine Raumaufnahme an CDB übertragen.
- Im Browser geprüft: Start ohne Berechtigungsabfrage, gesperrte Navigation, Stummschaltung bestätigt, Beenden, Navigation wieder freigegeben. Aufnahme und Einstellungen auch über die API während des Gesprächs abgewiesen; nach Ende wieder erlaubt.
- Echter Hardwaretest ohne Cloud: ReSpeaker-Eingang und gewählter Ausgang gleichzeitig geöffnet, 102 PCM-Blöcke in etwa zwei Sekunden erfasst. Danach beide Kindprozesse beendet. Keine Audioaufzeichnung gespeichert.
- Native Loopback-Prüfung mit künstlichem PCM: bidirektionale Übertragung, Stille bei Stumm, Abbruch während des Starts in etwa 0,05 Sekunden, keine verwaisten Audioprozesse.
- Regressionen: Blöcke über einen Stumm/Weiter-Wechsel bleiben stumm, Puffer begrenzt, verzögerte Startantwort nach Abbruch, Factory-Fehler, eindeutige Zuordnung von Audioquellen, keine Monitor-/Default-Quelle als Ersatz.

Die Testquellen sind von der produktiven Meeting-Bibliothek getrennt. Die temporäre Brain-Sitzungsdatei wird nach dem Test entfernt. Die synthetische Quelle ist keine Messung der Raumakustik oder Echo-Unterdrückung. Die physische Hörbarkeit und ein persönlicher Sprachdialog sind anschließend am Gerät zu prüfen.

## Nachweise

- [CDB-Testdaten](cdb-synthetic.json), ohne Token oder Sitzungsschlüssel
- [Hardwaretest](hardware.json), ohne Rohaufnahme
- [Stumm und gesperrte Navigation](live-muted.png)
- [Beendet und entsperrt](live-ended.png)
- [Produktive Startansicht](live-ready.png)
