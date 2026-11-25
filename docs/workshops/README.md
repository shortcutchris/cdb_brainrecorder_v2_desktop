# Geführte Gespräche und Composer · 1.0.0-rc4

Ergänzung ab rc5: [Ergebniskarte im Chat und ausgewählte Dokumente in einer
Brain Knowledge Area speichern](../workshop-assets/README.md).

Stand 25.11.2026. Interview und Brainstorming sind ausdrücklich gewählte
Talk-Formate. Das Gerät sammelt einen strukturierten Arbeitsstand; auf Wunsch
entsteht daraus ein bearbeitbares Composer-Board. Keine automatische Aufnahme,
kein ungefragtes Teilen und keine zweite Anmeldung oder technischen Service-Keys.

## Per Sprache starten (ab 1.0.0-rc6)

Am Brain anmelden und **Live-Gespräch** starten (oder den Talk-Aufsteller nutzen).
In dieser aktiven Online-Verbindung kannst du sagen:

- „Starte den Brainstorming-Modus.“
- „Ich möchte ein Interview führen.“
- „Zurück zum freien Gespräch.“

KAI nennt den gewünschten Modus und fragt **„Soll ich ihn dir erklären?“**.
Er wartet auf deine Antwort: **Ja** erklärt kurz und beginnt, **Nein** beginnt
ohne Erklärung, **Abbrechen** behält den bisherigen Modus. Bei Unklarheit fragt
er nach. Auch ein per Touch vorgewähltes Format bekommt diese Einführung.
Ein Wechsel beendet die Sprachverbindung nicht. Alte Ergebnisse bleiben in der
Format-Auswahl erhalten. Neue Sprachformate beginnen mit einem Zehn-Minuten-
Moderationsrahmen und der gemeinsamen Zielklärung; es entsteht kein Timer.

Die Frage gilt fünf Minuten in derselben angemeldeten Verbindung. Danach den
Modus erneut anfragen. Die Worte starten kein ausgeschaltetes Mikrofon und
keine Meeting-Aufnahme. Composer und Brain bleiben ausdrücklich zu speichern.

## Bedienung am Pi

1. Brain anmelden → Live-Gespräch → **Interview & Ideen**.
2. Format, Titel, Ziel und Zeitrahmen wählen. 5–20 Minuten sind eine
   Moderationsvorgabe; kein zusätzlicher Timer wird gestartet. Die bestehende
   20-Minuten-Grenze einer Live-Verbindung bleibt bestehen.
3. **Gespräch fortsetzen** → Gesprächswissen wählen → **Gespräch starten**.
   Beispiel: „Führe ein Interview zu diesem Ziel. Stelle eine Frage nach der
   anderen und halte die Erkenntnisse fest.“
4. Im Brainstorming erst Ideen sammeln, dann gruppieren, gemeinsam priorisieren
   und bestätigte nächste Schritte festhalten. Vorschläge sind keine Beschlüsse.
5. **Ergebnis & Format** öffnet Ziel, Fragen, Erkenntnisse, Ideen, Entscheidungen
   und nächste Schritte. Text lässt sich am Touchscreen korrigieren.
   **Tastatur** öffnet die große Bildschirmtastatur im Dialog. Änderungen bewusst
   übernehmen oder verwerfen. Bei einem Versionskonflikt bleibt die Eingabe stehen.
6. **Gespräch pausieren** beendet die Sprachverbindung und bewahrt das Ergebnis.
   Zum Fortsetzen den Arbeitsstand auswählen und die Verbindung neu starten.
7. „Speichere das Ergebnis im Composer“ oder **In Composer speichern**.
   Erst „gespeichert“ bedeutet Erfolg; „angefordert“ ist noch kein Speicherbeleg.

## Composer-Fähigkeit

Die in CDB All geprüfte Schnittstelle ist der bestehende angemeldete
`/api/v1/kb/voice/board-tools/call`-Zugang. Er führt dieselben MCP-Werkzeuge mit
persönlichen Mandanten- und Board-Rechten aus. Der Pi verwendet nur `create_board`,
`add_note` und `add_frame`. Keine frei vom Modell gewählten Zieladressen, Board-IDs,
Freigaben, Löschungen oder Änderungen an fremden Notizen.

Ein neues Gesprächsergebnis erzeugt ein eigenes Board mit dem Titel und einem
kurzen Pi-Kennzeichen. Jeder spätere Speicherstand ergänzt neue Textnotizen in
einem Rahmen; Bearbeitungen im Composer werden nicht überschrieben. Die zuvor
gewählten Brain-Wissensbereiche begrenzen die Recherche, sie sind keine
automatische Projektzuordnung oder Schreibfreigabe für bestehende Boards.

Die tatsächlichen Laufzeitregeln stehen im TQS-Modul
`app/services/voice_live/workshop_tools.py`. Das ist die ausgehandelte
Moderations-/Composer-Fähigkeit des Voice Agent; ein lokales Codex-SKILL.md wird
vom Sprachmodell nicht automatisch geladen. Bei angekündigter `workshop_voice_start_v1`-Fähigkeit fordert der Pi v4 an, auch
im freien Gespräch. Ältere Server bleiben bei v2 beziehungsweise v3 für ein
vorgewähltes Format; dort ist weiterhin die Touch-Auswahl nötig.

## Grenzen und Ausfallschutz

- Ergebnisse sind an Server, Benutzer und Mandant gebunden. Nach Abmeldung sind
  sie für den nächsten Benutzer weder sichtbar noch bearbeitbar.
- Gleichzeitige Änderungen benötigen dieselbe Revision. Menschliche Korrekturen
  werden nicht still durch einen älteren Agentenstand überschrieben.
- Wiederholte Geräteaufträge haben dauerhafte Belege auf dem Pi; ein Auftrag
  kann nicht zweimal dieselbe Änderung ausführen.
- Ein unsicher bestätigter Composer-Schreibvorgang wird niemals automatisch
  wiederholt. Der Arbeitsstand bleibt lokal, der Status verlangt eine Prüfung
  im Composer. Es gibt absichtlich keine blinde Wiederholen-Schaltfläche.
- Inhaltlich leere Bereiche werden nicht als Notiz veröffentlicht. Maximal
  6.000 Zeichen je Bereich, insgesamt 12.000 Zeichen pro Ergebnis.
- Die Formate sind online, da sie die bestehende Live-Verbindung verwenden.
  Lokale Ergebnisbearbeitung funktioniert ohne aktive Sprachverbindung.
  Offline-Meeting-Transkription bleibt eine separate Funktion.

## Daten und Installation

`workshops.sqlite3` liegt im privaten App-Datenverzeichnis mit Modus 0600. Es
enthält bewusst gespeicherte Arbeitsstände, Gerätebelege und das Schreibjournal;
keine Audioaufnahme. Bestehende Talk-Verlaufsregeln bleiben unverändert.
Die Ergebnisablage bleibt bis zu einer gezielten Datenbereinigung erhalten;
es gibt in dieser Iteration noch keine automatische Löschfrist oder Lösch-UI.
Aufträge und Ergebnisbelege mit Text werden im TQS-Relay maximal 60 Sekunden
aufbewahrt. Composer hat seine eigene reguläre Board-Ablage.

Bestandsupdate: additive private Datenbank, keine Änderung bestehender
Aufnahme-/Anmeldedatenbanken, keine neuen Pakete, Root-Rechte oder OS-Dienste.
Die bestehenden Anmeldedaten, Audio-, NFC-, Timer- und Geräteeinstellungen müssen
beim Update erhalten bleiben. Clean Install: vorhandene Positivliste exportiert
die versionierten Module und Touch-Assets; eine leere Datenbank entsteht erst
auf dem neuen Gerät. Keine persönlichen Ergebnisse gehören in ein Kundenimage.
Ein exportiertes Baupaket ist weder ein gebautes noch ein bootgeprüftes SD-Image.

## Prüfung

Automatisiert: Eigentümer-/Umgebungstrennung, leere Installation und Neustart,
Revisionen, Pausen, Belege, unterbrochene Composer-Antworten, Kontowechsel während
Speicherung, API-/Aktivitätsschutz und Ausschluss privater Daten aus dem Image.
TQS prüft v2/v3-Aushandlung und echte Gerätebelege sowie die vorhandenen
Voice-Authentifizierungsgrenzen. Touch-Prüfung mit beiden Pi-Auflösungen und
heller/CDB-Darstellung. Installation und Verbundtest werden separat belegt;
eine lokale Vorschau ist kein Hardware-Nachweis.


Technische Nachweise: 122 bestehende Pi-Tests zu
Studio/Voice sowie 13 Ergebnis-/API-Tests, 25 Paket-/Image-Tests und 171
JavaScript-Tests bestanden. TQS: 211 gezielte Prüfungen einschließlich der
bestehenden Live-, Reattach- und Portal-Key-Grenzen; webOS: 333 Changelog-Prüfungen.

Isolierte Touch-Vorschau: [Talk 1024×600](screenshots/talk-1024.png),
[Ergebnis mit Tastatur 1024×600](screenshots/keyboard-1024.png),
[Interview im CDB-Design 1280×720](screenshots/interview-cdb-1280.png).
[Formatwahl 1024×600](screenshots/formats-final-1024.png) und
[Formatwahl im CDB-Design 1280×720](screenshots/formats-final-cdb-1280.png).
Eingabe, Übernehmen, Verwerfen und Schließen außerhalb des Dialogs geprüft.
Escape verwirft einen ungespeicherten Text nicht. Mindesthöhe der neuen Aktionen
56 px, Formatkacheln 148 px; Bildschirmtastatur nutzt die bestehenden 44-px-Tasten.
Die Liste gespeicherter Formate verwendet Seiten: ein Eintrag bei 600 px Höhe,
zwei bei 720 px. Ein simulierter unsicherer Composer-Schreibvorgang zeigt den
Prüfhinweis und verhindert einen zweiten Versand; der Text bleibt erhalten.

Composer-Integration am echten Pi mit separater Testablage: Board 117 auf
Staging angelegt, synthetische Ziel-/Ideennotizen samt Rahmen geschrieben und
über `read_board` zurückgelesen. Persönliche Daten verblieben auf dem Pi; die
vorübergehende Test-Anmeldung wurde danach gelöscht. Keine vorhandenen Boards
verändert.

Sprachabnahme am echten Pi mit der realen Staging-Verbindung und synthetischem
Audio: Das Interview stellte eine Frage, übernahm eine Erkenntnis und speicherte
auf gesprochenen Auftrag [Board 118](https://composer-staging.cdbos.de/board/118).
Brainstorming wurde in einer getrennten Verbindung geprüft: Idee ergänzt,
Entscheidungsbereich leer gelassen, ohne Auftrag nicht gespeichert, anschließend
auf ausdrücklichen Sprachbefehl [Board 120](https://composer-staging.cdbos.de/board/120)
erstellt. Beide Boards wurden über die Composer-Schnittstelle zurückgelesen;
die letzte Statusabfrage des Agenten bestätigte jeweils `saved`.

Version 3 der Gerätewerkzeuge wurde tatsächlich ausgehandelt. Während des
Gesprächs waren konkurrierende Aufnahme-/Einstellungsaktionen gesperrt. Beide
Verbindungen wurden sauber freigegeben; Aufnahmebestand, Einstellungen und Timer
der regulären Pi-Anwendung blieben unverändert. Die Anmeldung bestand weiterhin.
Die vorübergehenden Test-Anmeldedateien wurden entfernt. Es wurde weder Raumton
aufgenommen noch ein erneuter menschlicher Hörtest durchgeführt.
Beleg: [Sprachabnahme mit Grenzen der Testreihe](voice-acceptance-rc4.json).

Bei der ersten kombinierten Testreihe spielte der Testeingang nach dem
Verbindungswechsel alte synthetische Sätze erneut ab; daraus wird nur der davor
abgeschlossene Interview-Test übernommen. Brainstorming wurde deshalb separat
erneut erfolgreich geprüft. Ein weiterer synthetischer Interview-Versuch erkannte
einen Satz unvollständig und fragte nach; dieser abgebrochene Versuch zählt nicht
als bestandene Abnahme.

## Auslieferung auf den Recorder-Pi

Am 25.11.2026 um 13:29 Uhr MEZ wurde **1.0.0-rc4** aus Commit
`3fe2285edb83894839abbc39196a4ca1c0a79457` als signiertes Update mit Sequenz 109
installiert. 165 Paketdateien wurden geprüft. Anmeldung, Aufnahmen,
Geräteeinstellungen, NFC-Zuordnungen und Raumregeln blieben erhalten. Studio und
Zusatzdisplay-Dienst wurden neu gestartet, der Pi selbst nicht. Die Oberfläche
lief danach wieder im CDB-Design bei 1280×720, weiterhin angemeldet.
Beleg: [Installationsprüfung](deployment-rc4.json).

Die neuen Dialoge wurden in einer isolierten Vorschau bei beiden Displaygrößen
bedient; das tatsächliche Pi-Bild belegt den erfolgreichen App-Start. Daraus wird
keine vollständige manuelle Touch-Abnahme am Gerät abgeleitet.

Das vorbereitete Kundenimage-Baupaket enthält 172 versionierte Quelldateien und
keine private Ergebnisdatenbank. Ein neues bootgeprüftes SD-Image ist damit noch
nicht erstellt.

Die Server-Ergänzung ist über [TQS #2916](https://github.com/BIK-GmbH/cdb_tqs/pull/2916)
nach bestandener CI in Staging übernommen. Deployment
[45615261771](https://github.com/BIK-GmbH/cdb_tqs/actions/runs/45615261771)
ist erfolgreich; der bereite Backend-Stand ist `staging-e112242`, Revision
`tqs-backend-stg--r45615261771-1`. Der angemeldete Pi bestätigt die neue Fähigkeit
über seinen normalen Live-Einrichtungsweg. Die Hinweise für Benutzer sind mit
[webOS #2189](https://github.com/BIK-GmbH/cdb_webos/pull/2189) übernommen;
der bereite BFF-Stand ist `staging-3f73972`, Deployment
[45614743633](https://github.com/BIK-GmbH/cdb_webos/actions/runs/45614743633) erfolgreich.
Produktionsumgebungen wurden nicht aktualisiert.

## Sprachstart: Daten und Update

Die zusätzliche Tabelle `format_sessions` in der privaten `workshops.sqlite3`
hält nur die Verbindungszuordnung und die ausstehende Frage. Sie wird bei alten
Installationen additiv angelegt; Arbeitsstände und Belege bleiben bestehen.
Sitzungseinträge älter als einen Tag werden beim Start entfernt. Auswahl,
Aktivierung und deren Beleg werden atomar gespeichert. Eine doppelte Bestätigung
legt kein zweites Ergebnis an. Ein Formatwechsel veröffentlicht nichts.

Der Server benötigt die v4-Werkzeuge zuerst. Normale Browser-Clients und v1–v3
behalten ihre bisherigen Befehle. [Abnahme rc6](../voice-formats/README.md).
