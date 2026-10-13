# Lautsprechereinstellungen – 0.5.16

Einstellungen → Audio führt zu Mikrofon und Lautsprecher. Beide Unterseiten haben dieselben Spalten, 56-px-Touchflächen, feste Kopf-/Fußleisten und Breadcrumbs. Lautsprecheraktionen sind 208 × 56 px. Auswahl und Änderungen werden sofort übernommen.

- Ausgang aus der Geräteübersicht des Pi wählen; stabiler Gerätename bleibt in `speaker.json` gespeichert. Der Systemstandard wird über das bestehende PipeWire/PulseAudio geändert; dessen Sitzungsverwaltung hält Routing und Lautstärke vor. Fehlender gespeicherter Ausgang wird nicht still durch einen anderen ersetzt.
- Lautstärke in 5-%-Schritten zwischen 0 und 100, Stummschaltung, Ausgabezustand. Nach Änderungen wird der tatsächliche Systemwert zurückgelesen; nicht übernommene Werte führen zu einem Fehler.
- Zwei Sekunden Testton direkt auf dem Pi: zunächst links 440 Hz, dann rechts 660 Hz, mit Ein-/Ausblendung und begrenzter Amplitude. Erfolg bedeutet abgeschlossene technische Wiedergabe; ob der Ton hörbar ist, bestätigt der Nutzer selbst.
- Während Aufnahme, Mikrofontest, Modelldownload oder Modelltest sind Änderungen und Testton gesperrt. Während des Testtons sind eine neue Aufnahme und Mikrofontests ebenfalls blockiert. Testton kann abgebrochen werden und wird beim Beenden des Dienstes gestoppt.
- Browserwiedergabe bleibt lokal zum Browsergerät. Der Testton und die Lautsprechereinstellungen steuern hingegen immer den Pi. „Dummy Output“ und virtuelle Null-Ausgänge erscheinen nicht als physische Lautsprecher.

## Validierung

86 Python- und 47 JavaScript-Tests bestanden. API-Prüfung umfasst CSRF, Aufnahmeinterlock, Gerätevalidierung, Wertebereiche, ignorierte Hardwarewerte, Testabbruch und Stereo-WAV-Erzeugung. Browserprüfung bei 1280 × 720: Audioübersicht, Breadcrumb zu Mikrofon und Lautsprecher, Auswahl, 55 → 50 % Lautstärke, Stummschaltung/Testtonsperre, Testton und Abbruch, Wiederfreigabe nach synthetischer 10-s-Aufnahme.

Zwei temporäre virtuelle PipeWire-Sinks erlaubten den Test ohne echte Lautsprecher. Geräte-/Volume-/Mute-Befehle und paplay liefen tatsächlich auf dem Pi; nur die Standardroute wurde im Vorschauadapter emuliert, um die produktive Route nicht ausdrücklich umzustellen. Ein Monitor-Mitschnitt belegt die getrennte links/rechts-Ausgabe am ausgewählten zweiten Sink (`pi-audio-proof.json`). Initial unbenutzte Null-Sinks nahmen auf diesem Pi Lautstärkewerte erst nach ihrer ersten Wiedergabe an; deshalb wird die Übernahme jetzt ausdrücklich geprüft. Keine akustische Prüfung möglich: aktuell ist kein physischer Lautsprecher angeschlossen. Virtuelle Sinks und temporäre Vorschau-Anmeldung wurden anschließend entfernt.

PipeWire-Dokumentation zum verwendeten Testausgang: [Null Sink](https://docs.pipewire.org/1.4/page_pulse_module_null_sink.html).

## Vorschauen

[Audioübersicht](01-audio.png) · [Lautsprecher hell](02-speakers-light.png) · [Stumm](03-muted.png) · [Testton läuft](04-tone-running.png).
