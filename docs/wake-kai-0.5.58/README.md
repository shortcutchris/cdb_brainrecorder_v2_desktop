# Hey KAI: natürliche Ablehnungen messen und gezielt kalibrieren

16. Oktober 2026. Kandidat 0.5.58; Auslieferungsnachweis folgt nach Prüfung.

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
