# Gesprächsformate per Sprache · 1.0.0-rc6

Stand 25.11.2026. Implementiert sind Interview, Brainstorming und Rückkehr ins freie Gespräch
innerhalb einer aktiven Online-Talk-Verbindung. Nach Ankündigung
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
- Natürliche Live-Sprachabnahme und Installation: noch ausstehend. Der Pi läuft
  weiterhin mit rc5; die vorbereitete rc6 wird bis zur Abnahme nicht aktiviert.

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

Der bereinigte [Diagnosebericht](diagnostic-2026-11-25.json) enthält ausschließlich
synthetische Testdaten, keine Konten, Zugangsdaten oder Raumaufnahmen.

## Veröffentlichungsstand und Fortsetzung

- Pi-Implementierung: `b56ab62`; signiertes rc6-Paket, Sequenz 111, 167
  Programmdateien. Image-Kit mit 174 Dateien vorbereitet; kein neues SD-Image
  gebaut oder auf einer zweiten Karte abgenommen.
- TQS-Grundfunktion: [PR 2933](https://github.com/BIK-GmbH/cdb_tqs/pull/2933),
  Staging-Merge `00d5c2f721bbf2e85f9010fd97e4097b8ddc8086`, Deployment
  [45644481481](https://github.com/BIK-GmbH/cdb_tqs/actions/runs/45644481481) erfolgreich.
- Changelog: webOS PR 2197 zusammengeführt und auf Staging veröffentlicht.
- Natürliche Sprachweiterleitung: [TQS PR 2934](https://github.com/BIK-GmbH/cdb_tqs/pull/2934),
  Head `2824ca42a3316d8607611fab7186da0d9085cf41`. Beide vollständigen CI-Läufe
  [45646849304](https://github.com/BIK-GmbH/cdb_tqs/actions/runs/45646849304) und
  [45649630120](https://github.com/BIK-GmbH/cdb_tqs/actions/runs/45649630120) grün.
  Noch nicht zusammengeführt oder veröffentlicht.
- GitHub liefert bei Merge und manuellem Workflow-Start HTTP 500/502; ein Versuch
  meldete „Merge already in progress“, die anschließende Prüfung zeigte den PR
  weiterhin offen. Kein neuer Deployment-Lauf wurde angelegt. GitHub bestätigte
  die [Störung](https://www.githubstatus.com/incidents/qn8mfv6q5hlx) am 25.11.2026.
  Schutzregeln wurden nicht verändert; kein Production-Deploy.

Nach Behebung der Störung zuerst tatsächlichen PR- und Deployment-Stand lesen,
um einen verspätet erfolgreichen Auftrag nicht doppelt auszuführen. Dann:

1. PR 2934 mit unverändertem geprüften Head zusammenführen; neue Änderungen
   erfordern erneut grüne Checks. Staging-Deployment des neuen Commits abwarten.
2. Am Pi die natürliche Sprachprobe aus
   `/home/bik/.local/share/cdb-recorder-updates/voice-formats-rc6/e2e.py` starten.
   Sie nutzt isolierte Daten, synthetische Sprache und keine Raumaufnahme.
   Pflichtfälle: Brainstorming/Nein, Ergebnis speichern, Interview/Ja,
   freies Gespräch/Abbrechen, freies Gespräch/Nein, Touch-Vorauswahl/Nein.
   Nicht mit `e2e-diagnostic.py` verwechseln: diese Gegenprobe fordert die
   Backend-Weiterleitung ausdrücklich an und ist keine natürliche Sprachabnahme.
3. Erst bei bestandener Probe den vorbereiteten signaturprüfenden `deploy.py`
   aus demselben Verzeichnis ausführen. Er erwartet den installierten Stand
   `c8039178` (rc5), prüft laufende Aktionen, bewahrt Anmeldung und Arbeitsstände
   und wechselt nur Programmdateien. Bei anderem Stand zuerst neu abgleichen.
4. Anmeldung, Hilfe und Darstellung am echten Display prüfen; Abnahme und
   Installationsbericht ergänzen, diese Statusangaben aktualisieren und pushen.
