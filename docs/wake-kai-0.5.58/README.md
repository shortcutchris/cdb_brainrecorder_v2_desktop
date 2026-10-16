# Hey KAI: natürliche Ablehnungen messen und gezielt kalibrieren

16. Oktober 2026. 0.5.58 ist signiert auf dem Pi installiert; Hey KAI ist für den Praxistest aktiviert.

## Fehler und Änderung

Der Benutzer meldete bei **Okay KAI** keine Reaktion. Die bisherige Diagnose
zeigte erkannte, aber verworfene Wortpaare. Ein angekündigter Test am tatsächlichen
ReSpeaker lieferte für ein vollständiges „Okay KAI“ einen zweiten Wortwert von
0,471757; zwei weitere abgeschlossene Segmente enthielten nur einen Teil des
Rufworts. Im Vergleich mit **Hey KAI** lieferte der Decoder zwei vollständige
Wortpaare mit Werten 0,525806 und 0,657463 für „Kai“. Bisher verlangte die App
für jedes zweite Wort 0,90. Audio kam an, aber es wurde kein Live-Start ausgelöst.

Nur die bereits als Testvariante angebotene Phrase **Hey KAI** verlangt jetzt
0,50 für „Kai“. Der Mindestwert für „Hey“ bleibt 0,80. Exaktes benachbartes
Wortpaar, konsistente Ergebniswörter und Dauer 0,25–2,5 Sekunden bleiben nötig.
Keine Erweiterung auf Guy, Kyle, Kay oder einzelne Wörter. Hey Brain und Okay KAI
bleiben bei 0,80/0,90; insbesondere ist Okay KAI mit seinen Teilerkennungen damit
nicht repariert. Die Vosk-Werte sind Decoder-Konfidenzen, keine kalibrierten
Wahrscheinlichkeiten einer richtigen Aktivierung.

Das ist eine begrenzte Kalibrierung anhand der verfügbaren Daten, kein neu
trainiertes KAI-Modell und keine allgemeine Fehlstartgarantie. Die kleinere
Schwelle kann auf bisher unbekannten Geräuschen oder Stimmen mehr Fehlstarts
erzeugen. Das ist im weiteren Praxistest ausdrücklich zu beobachten.

## Natürlicher Test auf dem Pi

Unter atomarer Wartungsreservierung lief jeweils nur ein Mikrofonbesitzer.
Ein lokaler Diagnoseprozess nutzte das eingerichtete Gerät, den installierten
Vosk-Stack und die unveränderte Grammatik. Keine Raumaufzeichnung, kein gespeichertes
Raumtranskript und kein Cloud-Gespräch. Der produktive Listener wurde nach jedem
Lauf wieder freigegeben. Die angepasste Datei lag dabei nur in einem isolierten
Testverzeichnis; der produktive Release wurde für diese Messung nicht verändert.

| Variante | Vollständige akzeptierte Segmente | Befund |
| --- | ---: | --- |
| Okay KAI, bisher | 0 | 1 verworfener Kandidat, 2 Teilsegmente |
| Hey KAI, bisher | 0 | 2 verworfene vollständige Kandidaten |
| Hey KAI, angepasst | 2 | Werte 0,505113 und 1,0; beide akzeptiert |

[Sanitisierte numerische Messwerte](natural-tests.json).
Die Tests fanden nacheinander statt; es ist nicht dasselbe wiederabgespielte
Audiosignal. Ohne Mitschnitt wird keine unabhängige Transkription behauptet.
Die erste neue Konfidenz liegt nahe der Grenze: Zwei Treffer beweisen keine
zuverlässige Erkennung nach langer Pause. Begrüßung und sprachliches Ende sind
in diesen lokalen Tests noch nicht geprüft.

Die laufende 0.5.57-Beobachtung enthält bewusste Wartungseingriffe am 16.10.:
06:19:06–06:20:08 und 06:20:23–06:21:10 UTC für die alten Einstellungen sowie
einen anschließenden Test der angepassten Variante. Sie darf nicht als
ununterbrochener 24h-Akustiknachweis gelten. Der Messprozess selbst blieb aktiv.
Nach Auslieferung wird die Teilmessung archiviert und ein neuer Lauf begonnen.

## Reproduzierbare Datei- und Negativprüfungen

`scripts/check_wake_confidence.py AUSGABE.json` prüft die vorhandenen drei
synthetischen Stimmen, Faktoren 1/0,03 und Einzel-/Doppelrufe. Zusätzlich kommen
zwei kontinuierliche Verwechslungsskripte mit Hey/Okay plus Karl, Kyle, Guy,
Sky sowie Hey Brian/Rain/Jana, „Kai, kannst du bitte später kommen?“ und normaler
Hintergrundsprache hinzu. Herkunft und genaue Synthesetexte stehen im neuen
`tests/fixtures/wake/confusers/manifest.json`. Die negativen Skripte wurden mit
ElevenLabs generiert, nicht über den Pi-Lautsprecher abgespielt. Referenztexte
sind Syntheseaufträge und keine unabhängig geprüften Transkripte.

[Vorheriger Vergleich](confidence-before.json),
[angepasster Vergleich](confidence-after.json),
[zusätzliche Negativprüfung](confusers-before.json),
[vollständiger Vergleich einschließlich neuer Skripte](confidence-final.json).

| Produktive Kandidatenregel | Genau erkannte positive Fälle | Negativfälle mit Fehlaktivierung |
| --- | ---: | ---: |
| Hey Brain unverändert | 12/12 | 0/68 |
| Hey KAI angepasst | 12/12 | 0/68 |
| Okay KAI unverändert | 8/12 | 0/68 |

24 mehrdeutige Kay-Proben stehen getrennt und werden nicht als korrekt oder
falsch gezählt. Pegelvariationen und wiederholte Dateien sind keine zusätzlichen
unabhängigen Stimmen. Ein separater Vergleich mit drei Pegeln der neuen
Negativskripte blieb ebenfalls ohne Aktivierung. Die Tabelle ersetzt weder einen
Stunden-Negativtest mit Alltagsgeräuschen noch den natürlichen Langzeittest.

## Regressionen und Auslieferungsgrenze

27 gezielte lokale Tests bestehen: neue Messwerte, Schwellenränder, unveränderte
andere Rufwörter, ähnlich klingende Wörter, Teil-/inkonsistente Ergebnisse sowie
Mikrofonreservierung und Diagnosebereinigung. 51 Studio-Tests nach Versionssprung
bestehen. Der vollständige Mac-Lauf hat 379 Tests ausgeführt und einen
`PermissionError` beim Beenden eines Suchton-Testprozesses gemeldet. Er zählt
nicht als grüner Gesamtlauf; der gleiche Fehlertyp wurde bereits vor dieser
Änderung dokumentiert. [Mac-Protokoll](python-tests-mac.txt),
[Studio-Protokoll](studio-tests-mac.txt). Der erste Pi-Testlauf meldete zwei Probleme der Testumgebung: Im isolierten
Quellpaket fehlte `player.py`, und ein synthetisches Transkript wurde ohne
explizites UTF-8 geschrieben. Das Quellpaket wurde ergänzt; der Test schreibt
seine Datei jetzt ausdrücklich im vom Produktionsleser erwarteten UTF-8.
**Der korrigierte vollständige Pi-Lauf besteht mit 379 Tests in 73 Sekunden.**
[Endgültiges Pi-Protokoll](python-tests-pi.txt). Auch der zuvor auf dem Mac
fehlgeschlagene Suchton-Test ist darin bestanden. Ein abgefangener Ausgabefehler
des alten Qt-Übersetzers unter der SSH-Latin-1-Locale und ResourceWarnings bleiben
im Protokoll sichtbar; keine Änderung an dieser alten Qt-Oberfläche oder der
produktiven Audio-Bereinigung wird hier behauptet. Die ersten Paketläufe bleiben
als [erster](python-tests-pi-first.txt) und [zweiter](python-tests-pi-second.txt)
fehlgeschlagener Vorlauf erhalten.

## Bestehendes Gerät und Kunden-Image

Nur App-Code und Tests ändern sich; keine neue Abhängigkeit, kein zusätzliches
Modell, kein Datenformatwechsel und kein Firmware-Update. `services/wake_phrase.py`
und `web_server.py` gehören zur bestehenden Release-/Image-Positivliste. Die
Erkennungsauswahl, Konten und Audioeinstellungen werden bei einem App-Update
nicht umgeschrieben. Für den gewünschten KAI-Praxistest wird Hey KAI anschließend
bewusst über die App-Steuerung gewählt, getrennt vom Installationsnachweis.

Neue Kundenprofile behalten den bisherigen ausgeschalteten Hey-Brain-Standard.
Ein zukünftiger Image-Build übernimmt den versionierten Code; das bereits gebaute
Image 0.5.44 bleibt unverändert. Diagnosewerkzeug, Vergleichsskripte und synthetische
Fixtures werden nicht als Kundeninhalt in das App-Paket eingebaut. Signatur,
kompatible Runtime, atomare Wartungsprüfung und Rückkehr bleiben erforderlich.


## Bestätigte Auslieferung und neue Langzeitmessung

[Installation](deployment.json): Quellcommit
`9c77e4962f4aa4966927e341ba0c45c88a41b5eb`, signierte Sequenz 15,
Release `45435e88753fcc4a3f08499267e660a1117efd327ccb7c5f0a541ccbe3ac8dae`.
Signatur, Runtime, Dateihashes und exakte Paketdifferenz sind geprüft: nur
`services/wake_phrase.py` und `web_server.py` ändern sich im App-Paket.
Die atomare Wartungssperre war erfolgreich, und die erfassten Einstellungen
waren nach Installation unverändert. Kein Browser-/Pi-Neustart; der Backend-
Neustart ist Bestandteil der App-Aktivierung.

Anschließend wurde **Hey KAI bewusst über die App-API aktiviert**.
[Separater Auswahlnachweis](phrase-activation.json): Audio-, Zielbereichs- und
Wissensauswahlprüfsummen bleiben gleich. Neue Kundenprofile werden davon nicht
berührt. Nach dem Umschalten war die erste Probe noch im regulären Wartezustand,
17 folgende Proben bereits hörbereit. Der anfängliche strenge Prüfversuch ist
als [Startübergang](installation-startup.json) erhalten und nicht als bestanden
umetikettiert. Eine erneute, unveränderte Prüfung besteht mit
[18 aufeinanderfolgenden Proben](installation-check.json): ein stabiler
Wake-Kindprozess, aktiver Release-Pfad, passender Quellhash und API/HTML 0.5.58.

Das [echte Touchdisplay](display-after.png) zeigt die unverdeckte Startseite und
„Bereit für Hey KAI“. Das ist eine Sichtprüfung, kein akustischer Erfolg und
kein Nachweis der intern ausgeführten JavaScript-Version. Der Benutzer wurde
anschließend um einen produktiven Ruf mit Begrüßung und „Gespräch beenden“
gebeten; die Bestätigung steht zu diesem Dokumentationsstand noch aus.

[Frischer Image-Export](image-export-check.json): 119 erlaubte Quelldateien,
passende Hashes der beiden geänderten App-Dateien, keine Teststimmen oder
Diagnoseskripte im Kundeninhalt. Das Exportpaket liegt außerhalb Git unter
`/tmp/cdb-058-image-kit`. Es ist ein geprüftes Baupaket, **kein neu gebautes oder
gebootetes SD-Image**. Das vorhandene Image 0.5.44 bleibt unverändert.

Der [neue 24h-Messplan](observation-plan.json) läuft vom **16.10.2026, 08:34:20**
bis **17.10.2026, 08:34:20 Europe/Berlin**. Beobachterprozess **1767736** wurde
als aktiv geprüft. Die bestehende 15-Minuten-Nachprüfung ist auf diesen Lauf
umgestellt und bleibt bei unverändertem Stand still; automatische Reparaturen
sind weiterhin aus. Ein echter Wake nach mindestens acht Stunden bleibt offen.

Die [vorige Teilmessung](previous-partial-observation.json) umfasst rund
6,32 Stunden und 1.517 gültige Ressourcenproben mit 99,9904 % Abdeckung, ohne
Ressourcenwarnung oder Browsergenerationwechsel. Sie enthält jedoch die
angekündigten Tests und den Update-/Rufwortwechsel und ist **kein bestandener
24h-Lauf**. Zwei als `backend_instance_changed` bezeichnete Ereignisse liegen
beim Update um 06:31:43 UTC und beim Rufwortwechsel um 06:32:09 UTC. Der zweite
entsteht durch die absichtliche Erneuerung der Wake-Instanz beim Phrase-Wechsel,
nicht durch einen zweiten behaupteten Backend-Neustart. Der vollständige
Vorversuch bleibt unter `baseline-057-before-hey-kai-calibration` erhalten.
Alte und neue Messzeiten werden nicht zusammengezählt.


## Kontinuierlicher KAI-Nachtest bei unverändertem produktivem Stand

Der neue `scripts/check_wake_kai_stability.py` lief ausschließlich auf dem Mac
mit dem aktuellen Erkenner-Quellhash, Vosk 0.3.44 und vorhandenen synthetischen
Dateien. Kein Pi-Mikrofon, keine Wiedergabe, keine Cloud-Sitzung, keine Änderung
am laufenden 0.5.58 oder an dessen Messfenster. Ein einziger Detektor wurde über
die ganze Folge beibehalten; seine produktive interne Segmenterneuerung blieb
aktiv. Alle Frames sind wie beim Pi 50 ms lang.

[Messwerte](continuous-stress-mac.json): zunächst **3.600 Sekunden synthetische
Hintergrundsprache ohne Aktivierung**, danach **300 gemischte Zyklen mit genau
450 erwarteten und erkannten Rufen**, ohne zusätzliche Aktivierung. Die Folge
wechselt drei Stimmen, Einzel-/Doppelrufe und die beiden Verwechslungsskripte.
Alle Zyklen bestanden. Insgesamt 10.260 Sekunden simulierte Audiodauer wurden
in 48,10 Sekunden Wandzeit verarbeitet. Das ist **kein realer Standby-Test**.
Die positive Erkennung erfolgte 1,25–1,60 Sekunden nach jeweiligem Dateianfang
(einschließlich Dateivorlauf und Segmentabschluss), nicht gemessen ab menschlichem
Sprechbeginn und nicht als Cloud-Verbindungszeit.

Der gemessene RSS des lokalen Testprozesses lag anfangs bei 161,17 MiB,
zwischenzeitlich bei etwa 166,52 MiB und zuletzt bei 160,06 MiB. Daraus wird
weder eine Pi-Speicherverbesserung noch eine 24h-Speichergarantie abgeleitet.
Wiederholungen derselben Dateien sind keine 450 unabhängigen Sprecherproben.

**Offene Rauschgrenze:** Der unveränderte deterministische Vergleich mit zwei
synthetischen Audiominuten Vorlauf pro Fall, vier Grundrauschpegeln und drei
Sprachpegeln ergibt für Hey KAI jetzt **5/12** bestandene Kombinationen statt
**3/12** vor der Kalibrierung. Keine Rausch-Aktivierung in den zwölf Fällen.
[Neue Einzelmesswerte](noise-mac.json),
[alter Vergleich](../wake-phrases-0.5.53/hey-kai-noise-mac.json).

| Rauschen, Standardabweichung PCM | Sprachfaktor 1 | 0,03 | 0,003 |
| --- | --- | --- | --- |
| 0 | erkannt | erkannt | erkannt |
| 4 | erkannt | erkannt | nicht erkannt |
| 16 | nicht erkannt | nicht erkannt | nicht erkannt |
| 64 | nicht erkannt | nicht erkannt | nicht erkannt |

Damit ist die Rauschtoleranz weiterhin eingeschränkt, auch bei nominell vollem
Dateipegel. Diese Fehlfälle dürfen nicht durch die erfolgreiche kontinuierliche
Serie verdeckt werden. Die Daten sind keine Messung des tatsächlichen akustischen
Signal-Rausch-Verhältnisses beim Benutzer; es wurde kein Raumton gespeichert.
Die neue Schwelle allein löst diese Grenze nicht. Weitere Eingrenzung muss
Decoderentscheidung, vollständige Wortpaare und tatsächliche Mikrofonbedingungen
auseinanderhalten. Das Gesamtziel bleibt offen.

Diese Ergänzung betrifft nur Laborwerkzeug, Messwerte und Dokumentation.
Kein weiteres App-Paket nötig; das Kunden-Image enthält weder Laborstimmen noch
Tests. Der produktive 24h-Lauf wird hierfür nicht zurückgesetzt.


## Übergabe vor Rechnerabschaltung – 16.10.2026

Der Benutzer bestätigt den produktiven Sprachtest mit **„ja beim 2ten“**.
Der erste Ruf ist damit weiterhin ausgefallen; keine bestandene Erst-Ruf-Abnahme.
Die anschließende API-Prüfung bestätigt eine Aktivierung, anschließend wieder
`listening` mit Hey KAI, laufende Mikrofonerfassung und Live-Zustand `ended`.
[Datensparsame Statusaufnahme](production-second-call.json).
Vor der Aktivierung enthält die Diagnose wiederholt `partial_wake_word`,
keine vollständigen abgewiesenen Kandidaten. Die genaue Zuordnung eines
Diagnoseereignisses zum ersten Ruf ist ohne synchronisierte Einzelmessung offen.
Keine Aussage, dass Mikrofon-Standby die Ursache sei.

Der zusätzliche **rein synthetische** Rauschtest protokolliert jetzt die
Decoderergebnisse: [Einzelentscheidungen](noise-decisions-mac.json).
Bei Rauschpegel 16 und voller/0,03 Sprachlautstärke bleibt beim Ziel nur `kai`
übrig; bei Pegel 64 und voller Lautstärke `[unk] kai`. In den leisen Fehlfällen
entsteht gar kein vollständiges Zielpaar. Die Kandidatenschwelle allein erklärt
also diese Ausfälle nicht. Schon synthetische Stille/Rauschen erzeugt gelegentlich
lange einzelne `hey`-Segmente; diese werden korrekt nicht aktiviert. Die Daten
stammen ausschließlich aus bekannten synthetischen Dateien, nicht aus Raumton.

**Nächster Ansatz:** Verlust des Wortanfangs, Segmentgrenzen und Onset-Erneuerung
mit denselben Dateien kontrolliert vergleichen. Keine bloße Freigabe von `kai`
allein und keine pauschale weitere Schwellenabsenkung. Ein möglicher Fix muss
negative Beispiele und wiederholte Rufe bestehen, bevor er auf den Pi kommt.
Der produktive Code bleibt während dieser Übergabe unverändert auf 0.5.58.

Die Arbeit am Ziel wird auf Benutzerwunsch bis zur Fortsetzung pausiert.
Der Pi-Beobachter wurde unmittelbar davor als `active/running`, PID 1767736,
geprüft und bleibt lokal aktiv. Sein aktuelles 24h-Fenster endet am
17.10.2026 um 08:34:20 Europe/Berlin. Die Rechnerabschaltung verhindert unsere
laufende Fernprüfung; sie beendet nicht von sich aus die Messung auf dem Pi.
Nach Rückkehr zuerst Beobachterprozess, Messlücken, aktive App-Version und
Rufwort kontrollieren; bestehende Messdaten nicht zurücksetzen. Es gibt weiterhin
keine abgeschlossene 24h-/8h-Abnahme und keinen automatischen Reparatur-Watchdog.

### Wiederaufnahme

- Repository: `cdb_brainrecorder_v2_desktop`, Branch `main`; installiert 0.5.58.
- Pi: `chris@raspberrypi5.local`, Backend Port 8088; private Daten nicht ausgeben.
- Messdaten: `~/.local/share/cdb-stability-20261015/run/` auf dem Pi.
- Aktueller Gesamtplan: `docs/idle-wake-0.5.45/stability-goal.md`.
- Erst-Ruf-Verlässlichkeit, echter Wake nach mindestens acht Stunden und die
  vollständige 24h-Auswertung bleiben offen. Die guten Labortests ersetzen sie nicht.
- Keine weiteren Testtöne oder isolierten Mikrofontests laufen aus dieser Sitzung.
- Diese Übergabe ändert nur Dokumentation/Messnachweise; kein neues App-Paket
  oder SD-Image nötig. Konfiguration und Aufnahmen auf dem Pi bleiben erhalten.
