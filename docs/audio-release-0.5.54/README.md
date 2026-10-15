# Audiofreigabe erst nach bestätigtem Beenden · 0.5.54

15. Oktober 2026. Im isolierten Fehleraudit von `fddfb50` wurden zwei
Sicherheitslücken reproduziert: Nach einem abgewiesenen Prozesssignal verlor
WakeWord die Referenz auf den noch laufenden Detektor. Nach einem Fehler beim
Schließen des nativen Live-Audios gab LiveConversation die Reservierung frei
und verwarf das Audioobjekt. Die Prüfwerte `wake_tracks_unreleased_child`,
`live_blocks_second_owner_after_close_failure` und
`live_tracks_unreleased_audio` waren jeweils `false`.

Das sind gezielt injizierte Fehler, kein Nachweis ihrer Ursache bei den früheren
natürlichen Wake-Aussetzern. Es wurden weder ein produktiver Prozess beschädigt
noch Raumaufnahmen erzeugt.

## Korrektur

- Der Wake-Prozess bleibt bis zum bestätigten Ende im Besitz der App. Bei
  fehlgeschlagenem Signal oder Timeout wird die Freigabe nach zehn Sekunden
  erneut versucht. Bis dahin werden weder Erkennungen übernommen noch neue
  Detektoren gestartet. Die normale Aufnahmesperre bleibt erhalten.
- Ein zweiter Fehler beim Aufräumen beendet die Bereitschaftsschleife nicht.
  Der Benutzer erhält einen lokalen Hinweis statt interner Fehlerdetails.
- Live bleibt bei fehlgeschlagener Audiofreigabe im gesperrten Zustand
  `closing`. Audioobjekt, Sitzungsgeneration und Reservierung bleiben erhalten;
  erst eine erfolgreiche Wiederholung gibt sie frei. Die Prüfung läuft im
  vorhandenen lokalen Überwachungsthread mit fünf Sekunden Wiederholabstand.
- Native Audio unterscheidet jetzt „Stopp angefordert“ von „Ressourcen
  vollständig geschlossen“. Die Eingabe wird sofort stummgeschaltet. Bei einem
  fehlgeschlagenen Aufräumen bleibt die Ereignisschleife für den nächsten Versuch
  verfügbar. Ein gesetztes Stopp-Flag allein zählt nicht mehr als Freigabe.

Bei einer dauerhaft nicht behebbaren Betriebssystemstörung bleibt das Gerät
sichtbar gesperrt. Ein zweiter Audiobesitzer wird nicht als Ausweg gestartet.
Diese Korrektur aktiviert keinen Browser-, Backend- oder Pi-Neustart und keinen
automatischen Wartungs-Watchdog.

## Prüfung und Grenzen

Die neuen Regressionen in `tests/test_audio_release.py` prüfen verweigerte
Signale, Timeout auch nach SIGKILL, einen echten ausschließlich vom Test
gestarteten stillen Kindprozess, verhinderte zweite Reservierung, erneute
Freigabe und eine Cloud-Schließbestätigung vor dem lokalen Abschluss.
`test_studio.py` prüft zusätzlich, dass wiederholte Freigabefehler die
Bereitschaftsschleife nicht beenden. Alle Profile und Dienste sind isoliert;
keine produktiven Zugangsdaten, Mikrofone oder Lautsprecher werden verwendet.

Die vollständigen Testläufe bestehen mit jeweils **338 Tests**: [Mac](python-tests-mac.txt)
und [Pi](python-tests-pi.txt). Die Pi-Prüfung läuft aus einem separaten
Testverzeichnis; die produktive App bleibt währenddessen unverändert. Die
anschließende sichere Auslieferung wird separat belegt.
Eine echte dauerhafte Kernelblockade wird nicht erzeugt. Die Tests belegen
die lokale Reservierungslogik, keine fehlerfreie Hardware unter allen Bedingungen.

## App-Update und Kunden-Image

Geändert werden die vorhandenen Dateien `services/wake_word.py`,
`services/live_audio.py`, `services/live_conversation.py` und `web_server.py`.
Keine neue Abhängigkeit, Firmware, Berechtigung, Datenmigration, Audioauswahl
oder Modellkonfiguration. Alle Laufzeitdateien gehören bereits zur App-
Positivliste. Ein neues Kunden-Image übernimmt sie aus dem ausgewählten Commit;
das vorhandene Image 0.5.44 bleibt unverändert. Testdateien und Berichte sind
keine zusätzlichen Produktdienste.

Die laufende Beobachtung von 0.5.53 wird nicht als Prüfung von 0.5.54 ausgegeben.
Nach einer bestätigten Auslieferung ist für die neue Version eine eigene
24-Stunden-Beobachtung nötig; der bisherige Teilbericht bleibt erhalten.

## Ausgeliefert und am Gerät geprüft

[Signiertes Update, Sequenz 11](deployment.json) aus Commit
`14f9dc571b5d7f712bd12f4ba139009f893cb8d5`: Version 0.5.54, gespeicherte
Einstellungen unverändert. Der vorhandene Verwaltungsagent reservierte die
Wartung atomar und prüfte Signatur, kompatible Runtime und Startgesundheit.
Keine laufende Aufnahme wurde beendet.

[Installationsprüfung](installation-check.json): API und ausgeliefertes HTML
melden 0.5.54; sämtliche vier geänderten Laufzeitdateien haben dieselben
SHA256-Werte wie der getestete Quellstand. 18 Stichproben über rund 34 Sekunden
zeigen durchgehend Bereitschaft mit genau einem unveränderten Wake-Prozess.
Das ist eine Startprüfung, kein Sprach- oder Langzeitnachweis.

![Echter Pi-Touchbildschirm nach der Installation](pi-home.png)

Der [neue Messplan](observation-plan.json) reicht vom **15.10.2026, 20:56:47 Uhr
bis 16.10.2026, 20:56:47 Uhr Europe/Berlin**. Der echte Beobachterprozess wurde
als aktiv bestätigt; unveränderte Revision 2, weiterhin ausschließlich lesend.
Okay KAI bleibt aktiviert. Die automatische Nachprüfung wurde auf diese Version
und Frist aktualisiert und reicht bis 16.10., 22:00 Uhr.

Der [vorherige Teilbericht](previous-partial-observation.json) umfasst etwa
55 Minuten. Archiv auf dem Pi: `baseline-053-before-audio-release-fix`.
Sein abschließender Backend-Wechsel und die Beobachtungslücke gehören zur
bestätigten Installation; sie werden nicht aus den Daten entfernt. Der isolierte
Pi-Testlauf erzeugte vor dem Update zusätzliche Testlast. Weder diese Zeitreihe
noch die 18 Startstichproben zählen als bestandener 24-Stunden-Lauf.

Offen bleiben die vollständige neue Langzeitmessung, ein echter Wake nach
mindestens acht Stunden Pause und die akustischen Grenzen der KAI-Varianten.
Diese Freigabekorrektur ändert weder Modell noch Erkennungsschwellen.

## Ergänzender Wiederholungstest ohne Änderung am Pi

Die neue Regression `test_100_concurrent_close_retries_leave_no_audio_threads`
führt auf dem Mac 100 Runden mit jeweils zwei gleichzeitigen Aufrufern aus.
Jede Runde verwendet eine echte neue Python-Ereignisschleife und deren Thread.
Der erste Aufräumversuch wird absichtlich mit einem Fehler beendet; der zweite
muss erfolgreich schließen. Nach jeder Runde werden geschlossener Loop,
beendeter Thread und null aktive Audioprozesse geprüft. **100/100 Runden
bestanden**, zusammen mit den übrigen sieben gezielten Freigabetests.
[Testprotokoll](concurrent-close-tests-mac.txt).

Keine Audiohardware, keine Cloud-Verbindung und keine produktiven Daten waren
beteiligt. Das prüft Wiederholbarkeit und Nebenläufigkeit des lokalen
Aufräumpfads, nicht 100 echte Sprachgespräche. Ausschließlich Test und Bericht
werden ergänzt; produktives Paket 0.5.54, Kunden-Image und laufender Messzeitraum
bleiben unverändert. Der neue Test ist nicht Bestandteil des früheren
338-Test-Protokolls und wird nicht nachträglich in dessen Zähler eingerechnet.

## Eingrenzung des Browser-Speicherverlaufs

Zwei rein lesende `/proc`-Stichproben im Abstand von **9,36 Minuten** zeigen
weiter dieselben neun Kiosk-Prozesse. Der anteilig zugerechnete Speicher (PSS)
steigt von 659,54 auf 666,25 MiB. Nahezu die gesamte Zunahme entfällt auf einen
Renderer: +6,68 MiB PSS beziehungsweise +6,67 MiB private veränderte Seiten.
Browser-Hauptprozess, GPU-Prozess und übrige Helfer bleiben in diesem kurzen
Vergleich nahezu konstant. [Rohwerte und Vergleich](browser-memory-samples.json).

Die summierten RSS-Werte enthalten mehrfach gezählte gemeinsame Seiten und
sind deshalb kein exklusiver RAM-Verbrauch. Diese Detailstichprobe verwendet
`smaps_rollup`; der laufende Beobachter verwendet die leichtere `/proc/stat`-
RSS-Abfrage. Unterschiedliche Zeitpunkte und Erfassungswege werden nicht als
identische Messwerte behandelt. PID und Startkennung wurden abgeglichen;
Debian Chromium schreibt seine Typangabe in einen zusammengefassten Prozesstitel.

Das grenzt die nächste Profilierung auf den Renderer ein, beweist aber weder
einen JavaScript-/DOM-Speicherverlust noch die Ursache in einem bestimmten
Frontend-Modul. Kein Heap-Dump, keine erzwungene Speicherbereinigung, kein
Neuladen und kein Eingriff in Audio oder App-Konfiguration. Der vollständige
Verlauf bleibt abzuwarten; die Abnahmekriterien und Warnschwellen ändern sich
nicht. Nur Messbericht und Dokumentation, kein App-/Image-Update.

### Lokale Browserprüfung: temporäre DOM-Objekte

Eine isolierte Playwright-CLI-Sitzung auf dem Mac verwendet die lokale Vorschau
bei 1280 × 720. Nur die Browserantworten für den Wake-Zustand werden auf
synthetische Bereitschaft gesetzt; kein echter Detektor oder Cloud-Start.
Das unveränderte Frontend führt seine normalen Statusabfragen aus.

Nach fünf Sekunden Anlauf folgen drei Messintervalle zu je 20 Sekunden.
Chromes DevTools-Protokoll erfasst DOM-Zähler und Heap vor und nach expliziter
Speicherbereinigung. Diese Methode folgt der Unterscheidung zwischen temporären
Allokationen und verbleibenden Objekten in der
[offiziellen Chrome-Dokumentation](https://developer.chrome.com/docs/devtools/memory-problems).

| Messpunkt nach Bereinigung | DOM-Knoten | Ereignisbehandler | JavaScript-Heap |
| --- | ---: | ---: | ---: |
| Vor den Intervallen | 2.421 | 297 | 1,895 MiB |
| Nach 20 Sekunden | 2.421 | 297 | 2,040 MiB |
| Nach 40 Sekunden | 2.421 | 297 | 2,043 MiB |
| Nach 60 Sekunden | 2.421 | 297 | 2,048 MiB |

Vor der Bereinigung lagen die Knotenzähler jeweils höher (4.777, 3.810 und
4.674); nachher kehrten sie zum Ausgangswert zurück. 66 vollständige Status-
und 216 Wake-Abfragen einschließlich Anlauf. [Rohmesswerte und Quelltext-Hashes](local-browser-retention.json)
sowie [reproduzierbare Playwright-CLI-Prüffunktion](local-browser-retention.js).
Sie wird mit `run-code --filename` auf einer eigenen Sitzung der synthetischen
Vorschau ausgeführt, nicht auf dem produktiven Pi. Die Prüfsitzung wurde beendet.

Dieser kurze Lauf belegt keinen fortlaufenden Aufbau zurückgehaltener DOM-Knoten
oder Listener in dieser Vorschau. Der Heap ist nicht exakt konstant. Erzwungene
Bereinigung, anderer Browser/Host und kleinere synthetische Daten begrenzen die
Aussage: weder Ausschluss jedes Speicherlecks noch Erklärung des Pi-RSS-Verlaufs.
Am Pi ist keine Remote-Debugging-Schnittstelle eingeschaltet; sie wurde für diese
Prüfung nicht aktiviert. Keine Pi-Speicherbereinigung, kein App-/Browser-Neustart,
keine Schwellenänderung und keine weitere Auslieferung aufgrund dieser Stichprobe.

### Erste volle Stunde: Zwischenstand, keine Langzeitabnahme

Der unveränderte Messplan wurde für den festen Abschnitt **15.10.2026,
20:56:47 bis 21:56:47 Europe/Berlin** ausgewertet: 240 technische Stichproben,
99,991 % Abdeckung, kein Wechsel der Browsergeneration und keine Warnung.
Der echte Beobachterdienst wurde zusätzlich mit PID 1200644 als laufend geprüft.
Die lokale Gesundheitsabfrage liegt bei p95 **97,49 ms**. Die Browser-CPU hat
einen Median von **29,46 % eines CPU-Kerns**, p95 31,53 %.
[Maschinenlesbarer Zwischenbericht](first-hour-observation.json).

Der summierte Browser-RSS fällt kurz nach Beginn von 1.156,19 auf 1.111,97 MiB
und steigt anschließend bis zur letzten Stichprobe auf 1.170,98 MiB. Deshalb
werden sowohl der Anfang als auch das Minimum ausgewiesen: +14,79 MiB gegenüber
dem ersten Wert, aber **+59,01 MiB gegenüber dem frühen Minimum**. Der wachsende
Verlauf bleibt ungeklärt; fehlende Warnungen sind kein Nachweis eines Plateaus.
Die oben beschriebene PSS-Prüfung und der kurze lokale Browserversuch erklären
diesen Verlauf noch nicht abschließend.

In dieser Stunde wurde kein Wake-Ereignis beobachtet. `listening` belegt allein
den gemeldeten Bereitschaftszustand, weder erfolgreiche Spracherkennung noch
einen Aufruf nach acht Stunden Pause. Die vollständige Abnahme bleibt offen.
Der Bericht enthält Prüfsummen der außerhalb von Git gesicherten technischen
Quelldateien. Messplan, Frist, produktive Anwendung und Kunden-Image bleiben
unverändert; diese Ergänzung enthält ausschließlich Dokumentation.

### Freigabefehler über die echten HTTP-Endpunkte

Die zusätzliche Regression
`test_failed_detector_release_blocks_http_capture_and_live_until_retry`
prüft den Weg HTTP → App-Steuerung → `WakeWord.suspend`, zusätzlich zu den
oben beschriebenen Komponententests. Ein synthetischer, weiterhin laufender
Detektor verweigert sein Beenden. `/api/record/start` und `/api/live/reserve`
müssen daraufhin beide mit einer verständlichen Fehlermeldung abbrechen,
ohne den Aufnahme- oder Gesprächsstart aufzurufen. Die alte Prozessreferenz
und der offene Ausgabekanal bleiben erhalten. Nach einem bestätigten erneuten
Beenden dürfen beide Endpunkte wieder starten; Prozess und Kanal sind freigegeben.

Der Test verwendet einen echten lokalen HTTP-Server und die normale
Anwendungssteuerung, aber künstliche Anmeldung, Prozesssignale und neue
Audioverbraucher. Er erzeugt keine echte Aufnahme oder Cloud-Sitzung und
beansprucht keine Pi-Hardware. Zusammen mit den acht Freigabe-Regressionen
bestanden **9 gezielte Tests auf dem Mac**;
[Protokoll](http-audio-release-tests-mac.txt). Dieser zusätzliche Test zählt
nicht rückwirkend zu den früheren 338 vollständigen Tests. Nur Test und Bericht
wurden ergänzt; keine Laufzeitänderung oder erneute Pi-/Image-Auslieferung.
