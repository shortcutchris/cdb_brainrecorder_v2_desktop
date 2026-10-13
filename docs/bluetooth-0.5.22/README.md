# Bluetooth-Audio 0.5.22

13.10.2026. Korrigiert die Unterscheidung zwischen gespeicherter Kopplung, Bluetooth-Verbindung und tatsächlich verfügbarem Audio.

- Audioausgänge und Eingänge werden der exakten Bluetooth-Adresse zugeordnet. Monitorquellen und nicht verfügbare Profile werden ausgeschlossen.
- „Als Lautsprecher“ aktiviert genau den markierten Bluetooth-Ausgang. Bei fehlendem Ausgang bleibt der Button gesperrt. Kein stiller Wechsel zum USB-Lautsprecher.
- Verbindungsausfälle zeigen Hinweise zu Handyverbindung und erneutem Koppeln; Trennen und Entfernen erhalten eigene Rückmeldungen.
- Eine reine Musikbox bietet keinen Mikrofon-Shortcut.

## Abnahme

142 Python-Tests auf dem Pi und 61 JavaScript-Tests bestanden. Zusätzlich echte PipeWire-Audiozuordnung geprüft. Tests decken fehlende Endpunkte, veraltete Verbindungsdaten, Fehlerbehandlung und die exakte Lautsprecherauswahl ohne Navigation bei Fehler ab.

Marshall EMBERTON II war zunächst gespeichert, aber getrennt. Nach erneuter Aktivierung des Kopplungsmodus ließ sich die A2DP-Verbindung herstellen. Kein Löschen der Kopplung und keine Treiberänderung nötig. Ursache der ursprünglichen Verbindungsablehnung nicht abschließend belegt.

Marshall wurde bei 25 % ausgewählt; der Testton wurde auf ihrem eigenen PipeWire-Ausgang vollständig abgespielt. **Benutzer bestätigt: beide Töne gehört.** ReSpeaker bleibt als Mikrofon eingestellt.
