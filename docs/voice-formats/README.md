# Gesprächsformate per Sprache · 1.0.0-rc6

Stand 25.11.2026. Interview, Brainstorming und Rückkehr ins freie Gespräch
funktionieren innerhalb einer aktiven Online-Talk-Verbindung. Nach Ankündigung
wartet KAI auf Ja (erklären, dann beginnen), Nein (direkt beginnen) oder Abbrechen.
Die Touch-Auswahl bleibt möglich und verwendet denselben Einführungsschritt.

## Verhalten und Grenzen

- Eine ausstehende Frage ändert das aktive Format noch nicht. Sie blockiert
  Ergebnisänderungen bis zur Antwort und ist fünf Minuten gültig.
- Auswahl und Bestätigung sind an Konto und Verbindung gebunden. Unklare
  Antworten werden nachgefragt; abgelaufene Antworten starten nichts.
- Wiederholte Bestätigungen über Neustart oder geänderte Auswahl hinweg erzeugen
  keine doppelten Entwürfe. Vorhandene Ergebnisse werden nicht gelöscht.
- Derselbe vorgewählte Modus verwendet seinen vorhandenen Arbeitsstand weiter.
  Der Wechsel in ein anderes Format erzeugt einen neuen Arbeitsstand.
- Kein automatisches Composer-/Brain-Speichern, keine Meeting-Aufnahme.
- Das Sprachmodell steuert die Gesprächsfolge anhand verbindlicher Anweisungen;
  Gerätelogik prüft Auswahl, Bindung, Antwort und Belege. Die Bedeutung eines
  gesprochenen Ja/Nein wird vom Sprachmodell erkannt, nicht über Text-Schlüsselwörter.

## Tests und Installation

- 134 Python-Prüfungen für Arbeitsstände, Live-Verbindung, Studio und Gerätebefehle.
- 171 JavaScript-Prüfungen.
- 193 TQS-Prüfungen für Werkzeuge, Rechte, Relay, Live/Chat und Wiederverbindung.
- Changelog: 339 Prüfungen. Keine neuen Abhängigkeiten oder Systemrechte.
- 6 Kundenimage-Prüfungen, zusätzlich leere Neuinstallation und additive SQLite-Erweiterung.
- Live-Sprachabnahme und Installation: noch ausstehend; Nachweise folgen hier.

Bestandsgeräte erhalten nur signierte Programmdateien. Anmeldung, Aufnahmen,
Timer und Konfiguration werden erhalten. Neue Geräte erhalten die Programmdateien
über die bestehende Image-Positivliste und eine leere private SQLite-Ablage.
