# Abnahme 0.5.18 · 13. Oktober 2026

## Ergebnis

ReSpeaker-Statusring und CDB Voice One sind implementiert. Eine gemeinsame, abgeleitete Aktivitätsprüfung kontrolliert Aufnahme, pausierte Aufnahme, Live-Verbindungsaufbau/Gespräch/Beenden, Mikrofon- und Lautsprechertest sowie Modellinstallation und Modelltest. Alle Start-/Änderungsaktionen sind serverseitig serialisiert. Hintergrundverarbeitung verhindert keine neue Aufnahme oder Unterhaltung.

## Prüfungen

- 113 Python-Tests auf dem Pi bestanden (inklusive bestehenden Recorder-/CDB-/Audio-Tests).
- 55 JavaScript-Tests bestanden: verzögerte Berechtigung, Abbruch, Mikrofonfreigabe, gegenseitige Sperren, Freigabe des Recorder-Menüs, verlustfreie Chat-Seiten.
- Echte USB-Prüfung am angeschlossenen XVF3800 unter Benutzer chris: Aufnahme blau, Pause gelb, App-Stumm rot blinkend, Wiederaufnahme blau, Ende ursprünglicher DOA-Modus. Jede Farbe und jeder Effekt wurde vom Gerät zurückgelesen. [Messprotokoll](led-hardware-test.json). Die physische Mute-Taste wurde im Code simuliert; ihre Betätigung durch einen Menschen ist in dieser Abnahme nicht enthalten.
- Reale CDB-Staging-Sitzung über WebRTC vom Pi, ausschließlich synthetische Sprache, Bereich staging_playground. Verbindung über mehr als 36 Sekunden und mehrere Heartbeats gehalten. 1296 Audioframes empfangen; vollständige Benutzer- und Assistant-Mitschrift. Antwort: „Die Testverbindung funktioniert.“ Aufnahme währenddessen abgelehnt; nach Ende wieder freigegeben. [Protokoll](live-synthetic-test.json).
- Touchansicht im Browser bei 1280 × 720 geprüft: feste Kopf-/Fußleiste, direkte Bereichsseiten, Mehrfachauswahl, Verlauf und Navigation nach Ende. Synthetische Recorder-Aufnahme sperrt Live-Gespräch.

Der CDB-Test verwendet einen isolierten WebRTC-Client mit künstlicher WAV-Datei auf dem Pi. Er bestätigt die echte Modellverbindung, nicht die akustische Rückkopplung oder Mikrofonberechtigung im Chromium-Kiosk. Der erste persönliche Sprachtest auf dem Display steht noch aus. Die WebRTC-Audioquelle ist das Gerät des Browsers, nicht automatisch der Pi bei Fernzugriff.

## Behobene Fehler aus der Abnahme

- Gleichzeitig eintreffende Sprecherfragmente werden unabhängig gesammelt; verspätete Endsilben zerlegen keine Nachricht. Aktuelle CDB-Ereignisse haben keine Turn-ID: visuelle Abschnitte verwenden Zeitstempel und eine 2-Sekunden-Pause, ersatzweise Empfangszeit. Dies ist keine garantierte Sprechersegmentierung.
- HTTP 204 bei Heartbeat/Close wird als Erfolg akzeptiert, nicht als ungültige JSON-Antwort.
- Der Recorder-Menüpunkt wird nach dem Gespräch ausdrücklich wieder freigegeben.
- Mehrzeilige/lange Chattexte werden ohne Scrollbars auf vollständige Seiten verteilt.

## Screenshots

[Gespräch aktiv](live-active.png) · [Synthetischer Verlauf nach Ende](live-finished.png) · [Aufnahme sperrt Live](recording-locked.png) · [Bereiche wählen](live-setup.png)

## Installation

Version 0.5.18; Engine unverändert 0.2.7. PyUSB 1.3.1 und die eng auf USB 2886:001a begrenzte Audio-Gruppenregel eingerichtet. Keine Firmwareänderung und keine Audio-/Kontokonfiguration durch dieses Update. Deployment-Nachweis folgt nach produktiver Prüfung.
