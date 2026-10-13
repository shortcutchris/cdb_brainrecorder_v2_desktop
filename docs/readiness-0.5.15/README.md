# Recorder-Status – 0.5.15

Die bisherige Aktion „Mikrofon eingerichtet“ ist eine Statusanzeige mit LED und Text. Grün: Aufnahmebereit, ohne Aktion. Rot: konkreter offener Punkt, direkt mit Audio, Brain-Konto, Transkriptions- oder Zusammenfassungsmodell verknüpft. Bei Speicherknappheit führt die Aktion zur Bibliothek. Gelb: Prüfung, belegtes Gerät oder Verbindungsproblem. Während der Aufnahme bleibt der Status gesperrt und Stoppen erreichbar.

Die Anzeige liest alle zehn Sekunden die vorhandene Geräteübersicht und Einrichtungsprüfungen. Änderungen der aktiven Konfiguration oder Testergebnisse verwerfen den Cache; nach Verbindungsverlust wird neu geprüft. Ein früher erfolgreich getestetes, inzwischen abgezogenes Mikrofon wird nicht als bereit angezeigt. Neue Aufnahmen warten auf die Bereitschaft; normale Queue-Verarbeitung darf parallel weiterlaufen. Dies prüft technische Voraussetzungen, nicht die akustische Qualität oder die Erreichbarkeit eines Cloud-Modells durch einen erneuten Inferenztest.

## Prüfung

78 Python- und 43 JavaScript-Tests bestanden. Sechs zusätzliche Tests prüfen Zielseiten, fehlende Mikrofone, Cloud-Anmeldung, Speicher, Offline-/Busy-Zustände und Cache-Schlüssel. Browserprüfung auf isolierter Pi-Vorschau bei 1280 × 720: grüne nicht klickbare Anzeige, sechs Sekunden synthetische Aufnahme, Stoppen und Freigabe während Queue-Verarbeitung, fehlendes Mikrofon und direkte Navigation zu Audio. Keine produktive Aufnahme und kein Cloud-Auftrag ausgelöst.

- [Bereit](01-ready.png)
- [Aufnahme läuft](02-recording.png)
- [Mikrofon fehlt](03-missing.png)
- [Direkt zur Audio-Einstellung](04-settings.png)
