# Fehlende Aktivierung nach Ruhe eingrenzen · 0.5.51

15. Oktober 2026. **Diagnose-Erweiterung, noch kein belegter Fix für den neu
gemeldeten Aussetzer.** Nach ungefähr 20 Minuten Ruhe berichtete der Nutzer,
dass erst der dritte „Hey Brain“-Ruf reagierte. Bei den ersten beiden blieb der
Startbildschirm unverändert. Der bisherige Beobachter konnte nur erfolgreiche
Erkennungen erfassen, keine davor verworfenen Sprachsignale. Die späteren
erfassten Gesprächsstarts verbanden sich nach zwei bis drei Sekunden; das
beweist nicht, dass die vorherigen Rufe gehört wurden.

## Hardware und korrigierter Akustiktest

ReSpeaker: USB `power/control=on`, `runtime_status=active`,
`runtime_suspended_time=0`; ALSA-Capture lief, Hardware-Mute war aus. Damit
liefert USB-Standby bislang keine Erklärung. Firmware oder Energieeinstellungen
wurden nicht geändert.

Die zunächst direkt am Pi abgespielten Testdateien waren **kein gültiger
Wake-Test**: `ambient_loop()` sperrt bei eigener Audioausgabe absichtlich die
Erkennung. Die dokumentierten Wechsel `waiting → loading → listening`
passten zu dieser Wiedergabesicherung. Der Testaufbau war falsch; aus diesen
Fehlversuchen folgt weder ein schlechteres Modell noch ein defektes Mikrofon.
Diese Sperre bleibt erhalten, damit eigene Antworten nicht erneut aktivieren.

Auf ausdrücklichen Nutzerauftrag entstanden natürliche ElevenLabs-Dateien
(Vincent, `eleven_multilingual_v2`, Deutsch; normale Geschwindigkeit 1, langsam
0,75). Die schnelle und langsame Datei werden direkt im identischen Decoder
mit `hey`/`brain` und jeweils Konfidenz 1 erkannt. Kein Absenken der Schwellen.
Die künstliche eSpeak-Wiedergabe ist nicht die Grundlage des Raumtests.

Der korrigierte [Akustiktest](acoustic-isolated.json) reserviert die vorhandene
atomare Wartungssperre, beendet damit die reguläre Capture-Instanz und verwendet
genau eine isolierte Erkennung am konfigurierten ReSpeaker. Die synthetische
Datei wird am gewählten 188A-Lautsprecherausgang mit unveränderten Einstellungen
abgespielt. Keine Raum-Audiodatei und keine Raumtranskripte werden gespeichert.
Nach Ende werden eigene Prozesse geschlossen und die Wartung freigegeben.

**Ergebnis: zwei von zwei langsamen Rufen beim ersten Abspielen erkannt.**
Der Peak lag bei −5,9 bzw. −6,2 dBFS. Die Datei enthält zwei Sekunden Vorlauf;
die Erkennungszeiten im Bericht sind ab Testfallbeginn und enthalten zusätzlich
eine Sekunde bis Wiedergabestart. Sie sind keine Cloud-Verbindungszeiten.
Dieser Test beweist die akustische Strecke und den lokalen Decoder für diese
Datei, nicht den produktiven Live-Übergang oder acht Stunden Standzeit.

## Diagnose in der laufenden Erkennung

`/api/wake/status` enthält nun einen begrenzten Diagnoseblock:
Anzahl gestarteter Erkenner, Alter des letzten Messpakets, empfangene Blöcke,
Peak/RMS sowie Zähler abgeschlossener Sprachsegmente. Feste Kategorien sind
`accepted`, `candidate_rejected`, `partial_wake_word` und `other_speech`.
Diese Kategorien behaupten nicht, ein beliebiger verwerfener Satz sei ein
beabsichtigter Wake-Ruf. Nicht abgeschlossene Sprache bleibt bis zum Endpoint
ohne Entscheidung. Der Pegel allein ist kein Sprachnachweis.

Die letzten 16 Entscheidungen bleiben über einen Kindprozesswechsel erhalten;
es gibt keine gespeicherten Wörter oder Audioblöcke. Messwerte erscheinen etwa
alle zwei Sekunden und bei einem abgeschlossenen Sprachsegment. Die vorhandene
Ready-/Alive-Überwachung bleibt unabhängig: Diagnosepakete können einen
hängenden Erkenner nicht künstlich als gesund erscheinen lassen. Der separate
Beobachter übernimmt nur freigegebene numerische Felder und feste Kategorien,
dedupliziert sie und begrenzt seinen eigenen Speicher.

Fünf gezielte neue Tests prüfen Pegel/Fenster, Datenschutz-Positivliste,
begrenzt erhaltene Entscheidungen, unveränderte Konfidenzschwelle und die
Stall-Erkennung trotz Diagnosepaketen. Der Beobachtertest prüft zusätzlich
Deduplizierung, Begrenzung und das Entfernen unerwarteter Textfelder.
Die Pegelberechnung für 300 Sekunden synthetisches Audio benötigte auf
dem Pi 0,906 CPU-Sekunden, also etwa 0,30 % eines Kerns zusätzlich bei Echtzeit.
Das ist nur die Pegelberechnung, kein gesamter App-Leistungswert.

[310 Python-Tests bestanden](python-tests.txt) auf der Pi-Laufzeit in einer
isolierten Codekopie. Die produktive Aufnahme-/Live-Instanz wurde dafür nicht
verwendet. Eine bestehende Qt-/GC-Warnung beim Prozessende ist im Log erhalten.

## Wiederholen und Auslieferungsgrenze

`scripts/check_wake_acoustic.py` ist ein **bedienergeführter Hardwaretest** und
spielt hörbar Ton ab. Nur mit ausdrücklicher Testfreigabe verwenden, nicht als
nächtlichen Watchdog. Synthetische MP3-Quellen liegen unter
`tests/fixtures/wake/`; vor dem Test in PCM-WAV konvertieren. Der Helfer akzeptiert
höchstens vier Dateien bis acht Sekunden, verweigert belegte Geräte und stellt
die Freigabe auch bei Fehlern im geschützten Testabschnitt wieder her. Er verändert
keine Firmware, Lautstärke, Modelle, Aufnahmeformate oder Kundeneinstellungen.

App-Update und zukünftiges Kunden-Image übernehmen die neue Service-Datei über
die bestehende Positivliste. Keine neue Laufzeitabhängigkeit. Diagnosehelfer,
Testaudio und temporärer Beobachtungsdienst sind nicht Teil der App-Auslieferung.
Das vorhandene SD-Image bleibt unverändert. Die offene Langzeitabnahme und der
Nutzerbefund dürfen nicht durch die zwei erfolgreichen Akustiktests ersetzt werden.
