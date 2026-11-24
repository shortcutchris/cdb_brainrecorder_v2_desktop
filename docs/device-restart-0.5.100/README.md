# Neustart direkt erreichbar · 0.5.100

24. November 2026. Chris möchte den Neustart neben dem Ausschalten direkt in
den Einstellungen finden. Der vorhandene Neustartknopf wurde aus „Wartung &
Neustart“ in die feste Aktionsleiste unter **Gerät & Verwaltung** verschoben.
„Weitere Wartung“ enthält nur noch Diagnose und das Neuladen der Oberfläche.
Die Übersichtskachel und lokale Hilfe nennen den Neustart ausdrücklich.

Die Aktionsleiste berücksichtigt auch den dynamisch ergänzten Knopf für
Anmeldung und Geräteschutz: fünf Spalten, alle Aktionen vollständig sichtbar,
auch bei 1024 × 600 und geöffneter Bildschirmtastatur. Neustart und Ausschalten
bleiben getrennt und verwenden die vorhandenen großen Bestätigungsdialoge.
Sperren bei Aufnahme, Gespräch, Timer, Wiedergabe und Verarbeitung sowie die
erneute Prüfung nach Bestätigung bleiben unverändert. Keine neue Systemaktion.

## Prüfung

- 8 bestehende JavaScript-Prüfungen für Bestätigung, konkurrierende Aktionen,
  Entwurfssicherung und Gerätesperren bestanden.
- 11 Python-Prüfungen für Neustart und Herunterfahren bestanden.
- Browserprüfung bei 1024 × 600 und 1280 × 720: direkt sichtbarer Neustart,
  Bestätigung, Abbrechen ohne Neustart sowie Tastatur und vollständig sichtbare
  Aktionsleiste. Nur lokale Vorschau, kein echter Neustart durch den Test.

![Einstellungen bei 1024 × 600](settings-1024.png)

![Große Neustartbestätigung](confirm-1280.png)

## Auslieferung

Die Änderungen an bestehenden App-Dateien sind von den vorhandenen Freigabelisten
für signierte Updates und saubere SD-Image-Baupakete erfasst. Keine neue Runtime,
Datenmigration oder Berechtigung. Kein SD-Image gebaut oder hardwaregeprüft.
Die Installation am Pi und deren Ergebnis werden nach dem Update ergänzt.
