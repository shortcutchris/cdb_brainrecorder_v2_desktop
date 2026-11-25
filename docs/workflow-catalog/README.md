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
Beim Beenden bleibt ein neues Gespräch gesperrt, bis das Brain die vorige Sitzung
wirklich freigegeben hat. Mikrofon und Wiedergabe enden sofort. Eine lediglich
angenommene Beenden-Anfrage (HTTP 202) zählt nicht als abgeschlossene Freigabe;
fehlende Bestätigung wird sichtbar gemeldet, ohne automatisch eine neue Sitzung
anzulegen. Dies behebt den beim Sprachtest beobachteten Konflikt bei schnellem
Beenden und erneutem Starten.

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

Am 25.11.2026 um 18:34 Uhr (Europe/Berlin) wurde rc7 auf dem Recorder-Pi
installiert. Der Server läuft in Staging; eine Produktionsfreigabe ist nicht
Teil dieser Änderung. Das signierte Paket prüfte 171 Dateien. Anmeldung,
Einstellungen, Aufnahmen, Gesprächsergebnisse, NFC-Zuordnungen und Raummodus
blieben erhalten. Kiosk und Zusatzdisplay-Dienst wurden ohne Systemneustart
neu gestartet. Beleg: [deployment.json](deployment.json).

Die vollständige Sprachprobe mit synthetischem Audio lief über echtes Staging,
WebRTC und Gerätewerkzeuge: 36 erfolgreiche Aufträge, Ja/Nein/Abbrechen, alle drei
Formate, eigene Retrospektive-Felder, Rückkehr ins freie Gespräch und direkt ein
zweites Gespräch mit vorbereiteter Auswahl. Ein dabei zunächst gefundener
Freigabefehler beim Gesprächsende wurde behoben; der ganze Ablauf danach wiederholt.
Keine Raumaufnahme und keine unbeauftragte Veröffentlichung. Beleg:
[acceptance.json](acceptance.json).

Zusätzliche Abnahme am selben Tag: [Retrospektive vollständig per Sprache bis
zum Composer-Board](retrospective-composer.md). Alle fünf Ergebnisbereiche wurden
auf Staging-Board 121 gespeichert, frisch zurückgelesen und mit dem gesprochenen
Inhalt verglichen; der Agent bestätigte den gespeicherten Stand per Sprache.
Testgrenzen und der korrigierte Rücklese-Prüfer sind dort ausdrücklich dokumentiert.

145 lokale Python-, 171 JavaScript- und 199 gezielte Serverprüfungen sind
bestanden, zusätzlich 68 Workflow-/Gesprächstests mit Python 3.13 direkt auf dem Pi
und die vollständigen Server-CI-Läufe. Das physische 1280×720-Display wurde nach
dem Update auf korrekte Startseitenanzeige geprüft. Die neuen Dialoge wurden mit
synthetischen Daten im Browser auf beiden Displaygrößen geprüft; eine Bedienprobe
mit dem Finger bleibt dem Nutzer. Das aktualisierte Image-Baupaket enthält 178
Quelldateien; weiterhin kein neues gebautes oder bootgeprüftes SD-Image.
