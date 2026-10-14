# Hey Brain · Studio 0.5.36

## Bedienung

Einstellungen → Audio → Aktivierungswort: Brain-Konto, Audiogeräte und
Wissensbereiche wie bisher prüfen, dann einschalten. „Hey Brain“ (englisches
Brain) sprechen, kurze Pause bis „Hört zu“, dann die Frage stellen.
„Gespräch beenden“ als eigenen Satz sprechen und kurz warten. Danach wird der
lokale Erkenner wieder gestartet, wenn das Aktivierungswort weiterhin aktiviert
ist und keine Aufnahme, Wiedergabe, Test oder Alarm das Mikrofon blockiert.
Kontoänderung schaltet die Bereitschaft wie bisher aus.

## Umsetzung und Quellen

Für die genaue Phrase ist kein überprüftes fertiges Micro-Wake-Word-Modell
gefunden worden. Deshalb verwendet dieser Stand eine kleine **lokale
Spracherkennung mit eingeschränktem Wortschatz**, kein umbenanntes Okay-Nabu-
Modell und kein neu trainiertes neuronales Wake-Word-Modell.

- [Vosk-Modellübersicht](https://alphacephei.com/vosk/models):
  `vosk-model-small-en-us-0.15`, 40 MB Download, Apache 2.0, für Raspberry Pi.
- [Offizielle Vosk-Installation](https://alphacephei.com/vosk/install).
- [Vosk Python-Beispiel für Wortergebnisse](https://github.com/alphacep/vosk-api/blob/master/python/example/test_words.py).
- Archiv SHA256: `30f26242c4eb449f948e42cb302dd7a686cb29a3423a8367f99ff41780942498`.

Decoder enthält auch Gegenphrasen (Brian, Rain, Train usw.) und unbekannte
Wörter. Nur ein abgeschlossenes „hey brain“ mit mindestens 0,8 für „hey“ und
0,9 für „brain“ sowie plausibler Dauer löst aus. Keine Teilhypothesen.
Gewichte liegen unter `models/`, Installation atomar, SHA256 geprüft.

Das Beenden wertet ausschließlich den Nutzertext des laufenden CDB-Gesprächs
aus. TQS liefert Textfragmente ohne endgültiges Satzsignal: deshalb 1,5 Sekunden
Ruhe nach dem letzten Fragment, maximal 6 Sekunden Gültigkeit. Der gesamte
Satz muss dem erlaubten Befehl entsprechen; Fragen, Zitate, Negationen,
Assistententext und alte Kontositzungen lösen nicht aus. Ein innerhalb der
Wartezeit ankommender Zusatz verwirft den Kandidaten. Ein erst nach längerer
Pause gesprochener Zusatz kann nicht rückwirkend berücksichtigt werden.
Der vorhandene Endpunkt schließt die Cloud-Sitzung; der native Audioabschluss
und das vorhandene Aktivitätsmanagement geben das Mikrofon wieder frei.
Es ist keine Änderung oder neuer Tool-Auftrag auf dem CDB-Server nötig.

## Grenzen und reproduzierbare Prüfung

Synthetische Sprachproben sind keine Feldmessung für Raumakustik, Dialekte,
Fernsehton oder Fehlaktivierungen pro Stunde. Das englische „Brain“ wird
absichtlich von „Brian“ unterschieden. Ein deutscher TTS-Sprecher, der „Brain“
wie „Brian“ ausspricht, wird nicht als positive Probe gewertet. Zum Prüfen der
eigenen Aussprache gibt es weiterhin „Erkennung testen“ ohne Cloud-Start.

`venv-local-ai/bin/python -m scripts.check_wake_phrase` prüft sechs englische
synthetische Stimmen, 20 negative Beispiele und 60 Sekunden Stille. Der
Prüfbericht enthält reale Pi-Messwerte; CPU-Prozent bezieht sich auf **einen**
Kern und auf Decoderzeit ohne einmaliges Laden. Der Spitzen-RAM-Wert des
Korpus enthält wiederholte Modellinitialisierungen und ist kein Leerlaufwert.

## Ergebnis auf dem Raspberry Pi 5 (16 GB)

- 197 Python-Tests und 94 JavaScript-Tests bestanden.
- Wake-Korpus: 6/6 positive Stimmen, 20/20 Gegenbeispiele korrekt, keine
  Erkennung in 60 Sekunden Stille. 78,23 Sekunden Sprach-/Pausenmaterial,
  2,075 Sekunden Decoder-CPU (2,65 % eines Kerns); Stille 1,861 Sekunden CPU
  pro Minute. [Rohdaten](wake-acceptance.json).
- Echter CDB/WebRTC-Test in `staging_playground`: synthetisches „Hey Brain“
  durch den separaten Erkennungsprozess startet das Gespräch; Frage nach dem
  Beenden bleibt offen; eigenständiges „Gespräch beenden“ schließt es mit
  `end_reason=voice_command`. Audio freigegeben, Aufnahme/Einstellungen wieder
  erlaubt, Erkennungsprozess erneut im Zustand `listening`.
  [Ablaufprotokoll](live-cycle.json). Aufnahme und Wiedergabe im Test wurden
  durch synthetische PCM-Eingabe und einen stillen Testausgang ersetzt. Es wurde
  kein Raumton hochgeladen und kein Alarm auf dem Produktivgerät angelegt.
