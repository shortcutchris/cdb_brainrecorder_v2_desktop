# Gesprächs-Workflows ergänzen und verwenden

Stand 25.11.2026, Recorder 1.0.0-rc7. Der neue Katalog enthält Interview,
Brainstorming und Retrospektive. Touch und Sprache verwenden dieselben
freigegebenen Vorlagen. Weitere Formate pflegen wir zunächst im Repository;
ein Nutzer muss keine JSON-Dateien bearbeiten. Die spätere Erstellung durch
KAI ist vorbereitet, aber noch nicht als Sprachfunktion angeschlossen.

## Am Pi

1. Am Brain anmelden, **Live-Gespräch → Gesprächsformate** öffnen.
2. Format über die großen Kacheln auswählen; weitere Formate mit **Weiter**.
3. Titel, Ziel und Zeitrahmen festlegen, danach Gesprächswissen wählen und starten.
   Alternativ in einem laufenden Talk sagen: „Starte eine Retrospektive“.
4. KAI nennt den Modus und fragt „Soll ich ihn dir erklären?“ Erst deine Antwort
   startet den Ablauf: Ja mit Erklärung, Nein direkt; Abbrechen lässt alles wie zuvor.
5. Ergebnisbereiche folgen dem Format. Retrospektive bietet Ziel/Zeitraum,
   Was lief gut?, Was war schwierig?, Was lernen wir? und Vereinbarte Verbesserungen.
6. Ergebnisse bearbeiten und bei Bedarf ausdrücklich in Composer speichern oder
   nach Gesprächsende einzelne Texte in einen Brain-Wissensbereich übertragen.
   Welche Ausgaben angeboten werden, bestimmt die geprüfte Vorlage.

Ein Format startet keine Aufnahme und gibt keine Daten automatisch frei.
Zeitvorgaben sind Moderationshilfen, keine zusätzlichen Timer. Im selben Dialog
zeigt **Gespeicherte Ergebnisse** die eigenen Arbeitsstände mit Vorlagenversion.

## Neue Vorlage pflegen

Quelle: `services/workflow_definitions/*.json`, striktes Schema in
`services/workflow_catalog.py`. Die Retrospektive dient als vollständiges Beispiel.

| Feld | Inhalt |
|---|---|
| `schema_version` | Aktuell 1; unbekannte Versionen werden abgewiesen |
| `id`, `version` | Stabile ID und positive, unveränderliche Versionsnummer |
| `name`, `description`, `voice_aliases` | Kachel, Beschreibung und Sprachbezeichnungen |
| `explanation`, `opening_question`, `moderation` | Einführung, Einstiegsfrage, Moderationsregeln |
| `default_minutes` | 5–20 Minuten |
| `phases` | 2–8 Einträge mit ID, Beschriftung und Anweisung; opening bis closing |
| `sections` | 2–8 Ergebnisfelder mit ID, Beschriftung und Hinweis; goal zuerst |
| `outputs` | Vorhandene Ausgaben brain/composer, einzeln, gemeinsam oder keine |

IDs: Kleinbuchstaben, Ziffern und Unterstriche, maximal 48 Zeichen; Beginn mit
Buchstabe. Keine doppelten IDs/JSON-Schlüssel. Namen und Sprachbezeichnungen
müssen über den aktiven Katalog eindeutig sein. Unbekannte Felder, ausführbarer
Code als eigenes Feld und neue Werkzeugtypen sind nicht zulässig. Das ist eine
Moderationsvorlage, keine frei programmierbare Automation. Vorlagen können
vorhandene Fähigkeiten begrenzen, niemals Kontorechte erweitern.

Neue Repository-Vorlagen werden mit Tests, Commit und signiertem App-Release
aktiv. Änderungen erhalten immer eine höhere Versionsnummer. Alte Arbeitsstände
tragen bereits einen vollständigen Snapshot und behalten ihre ursprüngliche
Vorlage. Aktive lokale Betreiber-Versionen haben Vorrang vor Repository-Versionen.
Der Katalog bietet maximal 32 aktive Formate; die Oberfläche ergänzt ab sieben
Formaten eine Suche und zeigt immer zwei große Kacheln pro Seite.

## Betreiberweg und spätere Agentenentwürfe

Nur mit lokalem Betreiberzugriff auf das Recorder-Datenverzeichnis:

```sh
python -m services.workflow_catalog --root /pfad/zu/recorder-daten validate vorlage.json
python -m services.workflow_catalog --root /pfad/zu/recorder-daten propose vorlage.json --origin operator
python -m services.workflow_catalog --root /pfad/zu/recorder-daten proposals
python -m services.workflow_catalog --root /pfad/zu/recorder-daten approve SHA256 --reviewer Betreiber
python -m services.workflow_catalog --root /pfad/zu/recorder-daten activate SHA256
python -m services.workflow_catalog --root /pfad/zu/recorder-daten list
python -m services.workflow_catalog --root /pfad/zu/recorder-daten retire workflow_id
```

`SHA256` durch die ausgegebene Prüfsumme ersetzen. Entwurf, Freigabe und
Aktivierung sind getrennt. Freigabe allein macht das Format nicht auswählbar.
Eine ältere freigegebene Version kann durch ihre Prüfsumme reaktiviert werden;
Stilllegung verhindert neue Starts, erhält aber vorhandene Ergebnisse.
Lokale Aktivierungen werden ohne App-Neustart gelesen. Neue Repository-Dateien
werden beim nächsten App-Start geladen.

Die Schnittstelle `WorkflowCatalog.propose(definition, origin='agent')` ist der
vorbereitete spätere Übergabepunkt. Sie speichert nur einen inaktiven Entwurf.
Es gibt bewusst noch kein Agentenwerkzeug und keinen HTTP-Endpunkt zum Anlegen,
Freigeben oder Aktivieren. Eine spätere Anbindung benötigt eine authentisierte
Berechtigung für Entwürfe, sichtbare Prüfung und weiterhin Betreiberfreigabe.
Das aktuelle System ist kein allgemeiner grafischer Workflow-Editor.

## Speicherung, Update und Grenzen

`workflow-catalog.sqlite3` ist privat (0600), getrennt von `workshops.sqlite3`.
Beim Update erhalten alte Interview-/Brainstorming-Ergebnisse additiv einen
Vorlagen-Snapshot; Text, Revision und Konto bleiben gleich. Neue Gespräche
halten die genaue Version samt Prüfsumme fest. Eine ausstehende Erklärungsfrage
hält ebenfalls ihre Version; Stilllegung blockiert noch nicht begonnene Abläufe.

Version 5 des Geräteprotokolls ist für neue Vorlagen erforderlich. Ältere Server
nutzen weiterhin die bisherigen Formate und erhalten keine Katalog-/Autorenrechte.
Für ein neues Format meldet der Pi eine verständliche Aktualisierungsgrenze,
bevor eine Sprachsitzung angelegt wird. Ergebnisse bleiben auch dann bearbeitbar.

Vorlagen sind insgesamt auf 24 KB JSON, Texte auf 6.000 Zeichen pro Feld und
12.000 Zeichen je Ergebnis begrenzt; zusätzliche Transportgrenzen berücksichtigen
Unicode. Keine automatische Kürzung. Modellantworten bleiben KI-generiert und
müssen vor Veröffentlichungen geprüft werden. Das Moderationsmodell führt die
Phasen anhand der Vorlage; die Anwendung erzwingt gültige IDs, Rechte und Revisionen,
aber keine starre, unbeeinflussbare Phasenreihenfolge.

Saubere SD-Images und App-Releases übernehmen das neue Modul und die drei JSON-
Dateien automatisch aus der vorhandenen Positivliste `services/`. Keine neue
Bibliothek, Root-Regel oder Factory-Anpassung. Private Kataloge, Konten und
Ergebnisse sind ausgeschlossen. Ein Baupaket ist kein gebautes/bootgeprüftes Image.
Nach Nutzung neuer Ergebnisfelder ist für deren Bearbeitung mindestens rc7 nötig;
ein ungeprüftes Zurückschalten auf ältere Apps ist dafür nicht unterstützt.

## Prüfung und Rollout

Automatisch: Definition/Validierung, Freigabe, Aktivierung, Versionstausch,
Stilllegung, alte Ergebnisse, Neustart, kontogebundene Aufträge, Protokolle v1–v5,
Einführungsfrage, dynamische Phasen/Felder, Ausgabesperren, Unicode-Transport und
Image-Export. Auf dem Server zusätzlich bestehende Voice-/Auth-/Chat-/Reconnect-Tests.
UI-Proben verwenden ausschließlich synthetische Daten auf 1024×600 und 1280×720.
Sie sind kein Nachweis der physischen Touch-/Sprachabnahme.

Rollout: zuerst TQS Staging mit v5 und natürlicher Sprachprobe; anschließend
signiertes Pi-Update mit bestehendem Wartungsschutz. Produktionsfreigabe ist nicht
Teil dieser Änderung. Der abschließende Installationsstand steht im Abnahmebeleg;
solange kein erfolgreicher Beleg existiert, gilt rc7 als vorbereitet, nicht installiert.
