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
alle zwei Sekunden und bei einem abgeschlossenen Sprachsegment. Peak/RMS beziehen
sich auf das Fenster seit dem letzten Messpaket, nicht auf die ganze Äußerung;
ein niedriger Pegel beim Endpoint beweist deshalb keine zuvor fehlende Sprache. Die vorhandene
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

## Installierter Stand und neuer Messlauf

[Signiertes Deployment](deployment.json) bestätigt 0.5.51 aus Commit
`a34c5d09c73dba667c53a5ca33544edcbb8df98e` und erhaltene Einstellungen.
Der installierte Detektor und das neue Diagnosemodul stimmen mit dem getesteten
Quelltext überein: SHA256 `b73c7b915e57245be969370fa22da951140217aea6622b3ca008a1e8bf4dbb28`
und `d338c2e12b16d1d79266264f0d5e6287617b83243cbd779be8ad95f48421c5f8`.
Die API zeigt frische Messpakete, wachsende Blockzähler und laufenden Capture.
Das ist ein Funktionsnachweis der Diagnose, keine bestätigte Behebung des
gemeldeten akustischen Aussetzers.

Der vorherige Lauf ist unter `baseline-050` als `superseded` bewahrt. Er enthält
die Nutzeraufrufe, die ungültigen direkten Wiedergabetests und den ausdrücklich
isolierten Hardwaretest. Der neue unveränderliche Lauf beginnt am
**15.10.2026, 18:01:16 Europe/Berlin** und endet am **16.10.2026, 18:01:16**.
Diese Diagnose-Auslieferung wurde nach dem konkreten neuen Nutzerbefund nötig;
ein bloß abgelaufenes Warteintervall ist kein Grund für weitere Neustarts.
Automatische Reparaturen bleiben aus. Nutzeraufruf nach langer Pause und
vollständige 24-Stunden-Abnahme stehen weiter aus.
