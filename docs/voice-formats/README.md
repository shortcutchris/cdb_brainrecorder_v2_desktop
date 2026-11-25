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

## Zwischenprüfung der echten Sprachverbindung

Die erste natürliche Sprachprobe erkannte den Moduswunsch und sprach die Frage,
löste aber noch keinen Geräteauftrag aus. Die Ursache war die fehlende explizite
Weiterleitung durch das Sprachmodell. Die Korrektur liegt in TQS PR 2934:
Moduswunsch und Ja/Nein/Abbrechen immer ans Backend geben; dort die aktuelle
Auswahl lesen. Dies verändert keine Berechtigungen und interpretiert keine
Transkripte über Schlüsselwörter.

Die gezielte Gegenprobe am Pi (25.11.2026, 16:35 MEZ) bestand mit einem ausdrücklich
formulierten Weiterleitungsauftrag: Brainstorming/Nein, Interview/Ja,
freies Gespräch/Abbrechen, freies Gespräch/Nein, vorgewähltes Interview/Nein.
Alle fünf Erklärungsfragen wurden gesprochen; vorher wurde kein Modus aktiviert.
Die Verbindung blieb beim Wechsel bestehen, alte Ergebnisse und die normale
Pi-Konfiguration blieben erhalten. Ein kurz fehlgeschlagener Abruf wurde ohne
Doppelaktion überwunden. Kein Raumton, keine automatische Veröffentlichung.
Diese Gegenprobe ersetzt noch nicht die Abnahme mit normalen Sprachsätzen nach
der Serverkorrektur. Bis dahin bleibt auf dem normalen Pi die Version rc5 aktiv.
