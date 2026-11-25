# Retrospektive per Sprache bis zum Composer-Board

Abnahme am **25.11.2026, 18:46–18:55 Uhr (Europe/Berlin)** auf dem Recorder-Pi,
**1.0.0-rc7**, App-Quelle `7363e67eb5a60e71a654f5d656c391a16215f920`.
Ergebnis: **Der geprüfte Ablauf ist bestanden.**

[Composer-Testboard 121 öffnen](https://composer-staging.cdbos.de/board/121).
Das Board gehört zum angemeldeten Testkonto in **Staging** und ist nicht öffentlich.
Es enthält fünf bearbeitbare Textkarten in einem gemeinsamen Ergebnisrahmen,
„Retrospektive · Stand 10“. Es wurde genau ein Board angelegt.

## Tatsächlich getesteter Weg

Deutsche synthetische Sprache wurde als PCM-Audio durch die native Audioanbindung
des installierten Recorders und die echte WebRTC-Verbindung zu Staging geschickt.
Der echte Voice Agent wählte die Gerätewerkzeuge. Formatstart, Einführung,
Ergebnisänderungen, Abschluss und Speicherauftrag wurden nicht direkt im
Ergebnisspeicher ausgelöst. Der Test las die Arbeitsstände zur Kontrolle aus.
Die isolierte Testinstanz lief auf dem Pi neben dem unveränderten Kiosk.

1. „Ich möchte jetzt eine Retrospektive starten.“
   KAI nennt den Modus und fragt, ob er ihn erklären soll. Er wartet auf die Antwort.
2. „Ja, bitte erkläre mir den Ablauf.“
   Erklärung mit Rückblick, Erfahrungen, Erkenntnissen und bestätigten Maßnahmen.
3. Die fünf Bereiche werden nacheinander gesprochen, siehe Tabelle.
4. „Die Retrospektive ist abgeschlossen. Setze die Phase auf Abschließen und lies
   alle fünf Ergebnisbereiche vor. Bitte noch nichts im Composer speichern.“
   Alle Ergebnisse werden vorgelesen. Bis dahin gibt es keinen Composer-Aufruf.
5. „Speichere diese Retrospektive jetzt als neues Board im Composer.“
   Das Gerät erstellt ein Board, fünf Textkarten und einen Rahmen. Der Agent
   meldet während des Schreibens korrekt, dass die Speicherung noch läuft.
6. Der gespeicherte Stand wird erneut aus Composer gelesen. Danach wird in einer
   neuen Sprachverbindung mit demselben Testarbeitsstand gefragt:
   „Ist die Retrospektive jetzt erfolgreich im Composer gespeichert?
   Prüfe bitte den gespeicherten Status.“
   KAI liest den Status und bestätigt **gespeichert, Revision 10**.
   Dieser Nachtest veröffentlicht nichts erneut und verändert keine Ergebnisse.

## Inhaltliche Abnahme

| Ergebnisbereich | Gesprochene und gespeicherte Inhalte | Prüfung |
|---|---|---|
| Ziel und Zeitraum | Teamworkshop am Montag, Testprojekt Alpha; bessere Vorbereitung | Vollständig |
| Was lief gut? | Klare Agenda; alle kamen zu Wort | Beide Punkte vorhanden |
| Was war schwierig? | Technikprüfung fehlte; Pause begann zu spät | Beide Punkte vorhanden, Aussage unverändert |
| Was lernen wir? | Technik vorher prüfen; Puffer für Pausen einplanen | Beide Erkenntnisse vorhanden |
| Vereinbarte Verbesserungen | Anna prüft die Technik bis Donnerstag; Ben verschickt die Agenda bis Freitag | Namen, Aufgaben und Termine korrekt |

Die fünf lokalen Texte wurden zusätzlich vollständig mit den gesprochenen
Beiträgen verglichen; keine zusätzlichen Beschlüsse oder Verantwortlichkeiten.
„Test Projekt“ statt „Testprojekt“ ist lediglich eine Schreibweise. Automatisch
wurde danach für jede Composer-Karte geprüft: richtige Überschrift, vollständiger
Text identisch zum lokalen Stand (nur Leerzeichen/Zeilenumbrüche normalisiert),
eindeutige Karten-ID, genau eine Karte pro Bereich und Zuordnung zum selben Rahmen.
Die Prüfung akzeptiert keine vertauschten Namen, Termine, fehlenden Karten oder
abgeschnittenen Inhalte. Der Status des Boards wurde nach Verbindungsende erneut
abgerufen; die Aussage „gespeichert“ beruht nicht allein auf einer Modellantwort.

## Befunde und Grenzen

- Ein erster Versuch mit dem synthetisch gesprochenen Projektnamen „Nordstern“
  wurde als „Nordstrand“ erkannt. Die Inhaltsprüfung stoppte **vor** einem
  Composer-Schreibvorgang. Der wiederholte Test verwendete „Alpha“ und eine
  langsamere synthetische Stimme. Das ist keine Fehlerbehebung der Spracherkennung;
  Eigennamen können weiterhin falsch verstanden werden. Das vollständige Vorlesen
  vor der Veröffentlichung war deshalb Teil der Prüfung.
- Im vollständigen zweiten Sprachlauf war das Board bereits korrekt gespeichert,
  aber der erste Rücklese-Prüfer erwartete Kartenobjekte. Die reale MCP-Antwort
  liefert eine strukturierte Textansicht unter `data.text`. Der Prüfer wurde
  korrigiert und durch sechs Offline-Tests abgesichert. Das unveränderte Original-
  protokoll bleibt mit `passed: false` erhalten. Ein frischer, nur lesender Nachtest
  desselben Boards bestätigt alle Inhalte und den Speicherstatus. Es wird kein
  fehlerfreier Einzelanlauf behauptet.
- Der Test umfasst echten Pi, installierte App, Voice-Verbindung und Composer-
  Speicherung. Er umfasst **keine** physische Mikrofon-/Lautsprecherprobe, kein
  Gruppenmeeting mit Raumgeräuschen und keine visuelle Browserabnahme des Boards.
  Die Audioausgabe wurde verworfen; die vom Dienst gelieferten Antworttexte sind
  protokolliert. Brain-Export, weitere Formate und Ausfallfälle sind keine neuen
  Abnahmepunkte dieses Tests.
- Anmeldung, Einstellungen, vorhandene Aufnahmen und Timer des Kiosks blieben
  erhalten. Nachher: rc7, angemeldet, idle, keine Aufnahme, keine Wartung.
  Vorübergehende Zugangsdaten wurden auf dem Pi entfernt. Im Repository liegen
  ausschließlich synthetische Gesprächsinhalte und bereinigte Belege, keine
  Sitzungsschlüssel, Aufnahmen oder privaten Ergebnisdatenbanken.

## Belege

- [Zusammengefasste Abnahme](retrospective-composer/acceptance.json)
- [Vollständiger Sprachlauf einschließlich ursprünglichem Prüferfehler](retrospective-composer/speech-run.json)
- [Erneutes Rücklesen und gesprochene Statusbestätigung](retrospective-composer/readback-and-status.json)
- Ausführbares Testwerkzeug: `scripts/check_retrospective_composer_voice.py`
- Offline-Prüfungen: `tests/test_retrospective_voice_probe.py`

Composer wird über den bestehenden angemeldeten CDB-Zugang
`/api/v1/kb/voice/board-tools/call` angesprochen. Dieser führt die Composer-MCP-
Werkzeuge mit den Rechten des Benutzers aus. Für die Veröffentlichung wurden
`create_board`, fünfmal `add_note` und `add_frame` verwendet; die Abnahme ergänzt
`read_board`. Es wurde kein zusätzlicher frei konfigurierbarer MCP-Server am Pi
eingerichtet.

## Test wiederholen

Offline, ohne Netzwerk oder Hardware:

```sh
python3 -m unittest tests.test_retrospective_voice_probe -v
```

Live nur auf einem freien, angemeldeten Staging-Pi mit `staging_playground`,
synchronisierter Uhr, `espeak-ng`, `ffmpeg` und der Python-Umgebung der App.
Jeder vollständige Lauf legt nach gesprochenem Auftrag ein neues Testboard an.
Ausgabeordner müssen neu sein. Der folgende Aufruf ist direkt **auf dem Pi**:

```sh
/home/bik/cdb-timer-recorder/current/venv-local-ai/bin/python \
  scripts/check_retrospective_composer_voice.py \
  --app-source /home/bik/cdb-timer-recorder/current \
  --data-root /home/bik/.local/share/cdb-recorder-local \
  --output /home/bik/.local/share/cdb-recorder-updates/retro-test-neu \
  --execute-staging-write
```

Mit `--resume-from /pfad/zum/bisherigen-test` wird dessen bereits gespeichertes
Board erneut gelesen und der Status per Sprache erfragt. Das Werkzeug übernimmt
dabei nur den isolierten Testarbeitsstand; es erstellt kein weiteres Board.
Auch dieser Modus verlangt die ausdrückliche Testfreigabe im Aufruf. Private
Zwischendateien bleiben im geschützten Testordner auf dem Pi; vor dem Commit
ausschließlich `result.json` prüfen und gegebenenfalls bereinigen.

**Update-/Image-Auswirkung:** ausschließlich Testwerkzeug, Testfälle und
Dokumentation. Keine Änderung der laufenden Anwendung, Abhängigkeiten, Dienste
oder Factory-Konfiguration; kein neues Release, keine Installation und kein
neues SD-Image erforderlich oder für diese Abnahme erstellt.
