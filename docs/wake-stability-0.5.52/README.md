# Wake nach sehr leisem Grundrauschen · 0.5.52

15. Oktober 2026. Aufbauend auf der
[Diagnose und dem korrigierten Hardwaretest](../wake-stability-0.5.51/README.md).

## Reproduzierbarer Fehler

Die neue Pi-Diagnose sah bei sehr leisem Grundrauschen ungefähr alle 25,4 Sekunden
unvollständige Wortkandidaten. Das bedeutet nicht, dass ein Mensch alle 25 Sekunden
sprach. Ein isolierter Vergleich mit natürlicher ElevenLabs-Sprache reproduziert
eine passende Schwäche: Nach 120 Audiosekunden Rauschen mit Standardabweichung
4 PCM-Einheiten wird derselbe klare „Hey, Brain“-Ruf verworfen, der nach digitalen
Nullen sofort akzeptiert wird. USB-Standby war am realen Gerät nicht aktiv.
Dieser Zusammenhang passt zum Nutzerbefund, beweist aber nicht rückwirkend die
genaue Ursache jedes zuvor nicht protokollierten Rufes.

Eine einfache Nullsetzung sehr leiser Blöcke wurde verworfen: Sie verbesserte
den Rauschfall, entfernte aber auch eine extrem leise Stimme in stiller Umgebung.
Der [vollständige verworfene Vergleich](../wake-stability-0.5.51/rejected-floor-experiment.json)
bleibt erhalten. Die produktive Lösung verändert keine PCM-Samples und senkt
keine Erkennungskonfidenz.

## Änderung

Nach mindestens zwei Sekunden stabilen, sehr niedrigen, **nicht digitalen**
Rauschpegels wird beim deutlichen Pegelanstieg nur der Decoder erneuert; das
akustische Modell bleibt geladen. Der Median des ruhigen RMS liegt dafür zwischen
1 und 8 PCM-Einheiten; der neue Block muss RMS größer als `max(8, 2 × Median)`
oder Peak größer als 48 haben. Ruhige Blöcke dürfen RMS 8 und Peak 48 nicht
überschreiten. Die Prüfung gilt ausschließlich für die 50-ms-Blöcke des nativen
16-kHz-/S16LE-Eingangs. Andere Blockgrößen behalten den bisherigen Pfad.

Die letzten 200 ms bleiben begrenzt im RAM und werden dem erneuerten Decoder
vor dem aktuellen Block gegeben, damit der Wortanfang erhalten bleibt. Nichts
wird gespeichert oder zusätzlich hochgeladen. Kurze Pausen innerhalb eines Rufs
reichen nicht für eine erneute Aktivierung dieser Logik. Digitale Stille und
lautere Hintergründe lösen diesen neuen Reset nicht aus. Die vorhandene Erneuerung
nach abgeschlossenen Sprachsegmenten bleibt bestehen.

Die Diagnose zählt `onset_renewals`; damit lässt sich eine Erneuerung beim
Pegelanstieg von einem Capture-/Prozessneustart unterscheiden. Aufnahme-,
Wiedergabe- und Gesprächssperren bleiben unverändert. Eigene Lautsprecherwiedergabe
ist weiterhin kein erlaubter produktiver Wake-Trigger.

## Vergleich und Grenzen

[A/B-Vergleich](comparison.json) mit vier Rauschstärken und drei Sprachpegeln,
jeweils nach 120 Audiosekunden Vorlauf; [anschließende Prüfung des tatsächlichen
Produktionskandidaten](production-candidate.json):

| Fall | Vorher | Neuer Code |
| --- | --- | --- |
| Digitale Stille, alle drei Sprachpegel | 3/3 erkannt | 3/3 erkannt |
| Sehr leises Grundrauschen, normaler und reduzierter Sprachpegel | 0/2 erkannt | 2/2 erkannt |
| Übrige schwierigere Pegel-/Rauschkombinationen | 3/7 erkannt | 3/7 erkannt |
| Unbeabsichtigte Aktivierung während des Vorlaufs | 0 | 0 |

Insgesamt **8 von 12 statt 6 von 12** erkannten Zielrufen, keine zusätzliche
Verschlechterung in diesem Vergleich. Vier extreme Kombinationen bleiben
Fehlversuche; keine pauschale Erkennungsgarantie. Die Daten wurden schneller als
Echtzeit verarbeitet, nicht zwei Minuten tatsächlich gewartet. Die periodisch
wiederverwendete künstliche Rauschfolge ist kein vollständiges Raummodell.

- [315 Python-Tests bestanden](python-tests.txt), darunter fünf neue Tests für
  begrenzte unveränderte PCM-Vorgeschichte, einmalige Erneuerung, Erhalt sehr leiser
  Sprache nach digitaler Stille, kurze Wortpausen, stärkere Hintergründe und
  abweichende Blockgrößen. Bestehende Reservierungs-/Stall-/Fehlertests bleiben grün.
- [28 Sprachfälle bestanden](phrase-corpus.json), einschließlich Doppelnennung
  und ähnlich klingender Negativbeispiele. Die Quelle ist synthetisch; das ersetzt
  keine Feldmessung der Fehlaktivierungsrate. Das ursprüngliche Latin-1-Log wurde
  für die Ablage verlustfrei in UTF-8 umkodiert.

`scripts/check_wake_room_noise.py` reproduziert die Rauschmatrix ohne Hardware.
Für A/B optional `--baseline-source` mit dem historischen `wake_phrase.py` aus
Commit `a34c5d0`, Modellpfad über `CDB_WAKE_MODEL`, Ergebnisdatei über `--output`.
Die mitgelieferte natürliche MP3 wird identisch mit zwei Sekunden Vorlauf und
einer Sekunde Nachlauf dekodiert. Alle nicht erkannten Fälle bleiben im Ergebnis.

Der [echte akustische Test nach 30 Sekunden Raumruhe](acoustic-after-30s.json)
erkannte den ersten natürlichen Ruf und gab die Wartung wieder frei. Ein
isolierter Erkenner führte den Kandidatencode aus; die weiterhin installierte
App meldete dabei noch 0.5.51. In dieser Runde war `onset_renewals=0`: Sie
bestätigt den erhaltenen Hardwarepfad, aber nicht eine tatsächlich ausgelöste
Rauschkorrektur im Raum. Kein produktiver Live-Start wurde dabei erzwungen.

## Update und Image

Keine neue Abhängigkeit, Firmware-Änderung oder Änderung an Kundeneinstellungen.
App-Updates und künftige saubere Image-Builds übernehmen die veränderten Services
über die bestehende Positivliste; Testskripte und Teststimmen gehören nicht ins
App-Paket. Das vorhandene SD-Image wird nicht ersetzt. Produktive Auslieferung
erfolgt nur unter atomarer Wartung bei freiem Gerät. 24 Stunden Standzeit und ein
echter Nutzeraufruf nach mindestens acht Stunden bleiben getrennte offene
Abnahmepunkte; sie werden durch diese kürzeren Tests nicht ersetzt.

## Produktive Auslieferung und Beobachtung

0.5.52 wurde am 15.10.2026 unter atomarer Wartung installiert:
[Installationsbeleg](deployment.json), Quellcommit `b734a43`, signierte Sequenz 9.
Die geprüften Einstellungsdateien sind unverändert. Danach stimmen die SHA256
von `wake_phrase.py` und `wake_word.py` mit dem Repository überein; auch das
Arbeitsverzeichnis des echten Detektorprozesses zeigt auf die neue unveränderliche
Release. Der Status meldet `listening`, frische Audioblöcke und genau einen
Detektorstart. Keine Testwiedergabe oder isolierte Akustikprüfung läuft weiter.
Der produktive Zähler `onset_renewals` stieg bereits an; das belegt die Ausführung
des neuen Pfades, noch keinen erfolgreichen natürlichen Nutzeraufruf.

Der bisherige 0.5.51-Lauf liegt unverändert als `baseline-051` neben den früheren
Vorläufen und ist als abgelöst markiert. Der neue rein lesende 24-Stunden-Lauf
beginnt am **15.10.2026 um 18:21:33 Europe/Berlin** und endet am
**16.10.2026 um 18:21:33**. Die automatische Auswertung darf weder diesen
Zeitraum vorwegnehmen noch `listening` als Nachweis akustischer Erkennung werten.
Die Wiedergabesicherung bleibt aktiv; eigene Pi-Lautsprechertests können daher
keinen normalen Wake-/Live-Durchlauf nachweisen. Ein echter Nutzeraufruf nach
mindestens acht Stunden bleibt erforderlich.

### Sichtprüfung während des laufenden Tests

[Direkter Bildschirmabzug des Pi](pi-home.png), 15.10.2026 gegen 18:43 Uhr:
Startseite vollständig sichtbar, unten „Aufnahmebereit“ und „Bereit für Hey Brain“.
Kein stehengebliebener Erkennungshinweis oder Verbindungsdialog. Der Abzug
verändert weder Navigation noch Audiozustand. Er belegt den sichtbaren
Bereitschaftszustand, nicht die Reaktion auf Berührung oder Sprache.

### Echter Nutzeraufruf nach 32 Minuten Ruhe

Am 15.10.2026 um 18:53:37 Europe/Berlin beobachtet der unveränderte Messlauf
nach 1.924,2 Sekunden Ruhe einen echten Wake-Aufruf. Der Nutzer bestätigt im
Chat: „Also ich habe gerade mal per Hand, also mit Eigenstimme getestet. Da
hat's geklappt.“ Es lief kein synthetischer Audiotest.

Die [technischen Ereignisse](real-user-wake.json) zeigen Verbindung nach 2,0 s,
erste Audioausgabe nach 6,0 s, Gesprächsende um 18:53:51 und erneute
Wake-Bereitschaft um 18:53:54. Die Zeiten stammen aus Zustandsabfragen ungefähr
im Sekundentakt und beginnen bei beobachteter Erkennung, nicht beim Anfang des
gesprochenen Wortes. Die Beobachtung liest weder Gesprächsinhalte noch Audio;
der genaue Ende-Befehl und der Inhalt der ersten Antwort werden hier nicht
behauptet. Ein einzelner erfolgreicher Eigenstimmen-Test bestätigt den realen
Pfad nach dieser Pause, ersetzt aber weder acht Stunden Ruhe noch 24 Stunden
Stabilitätsmessung. Der Dauerlauf wurde dafür nicht neu gestartet.

### Zweiter produktiver Durchlauf

Der [Beobachter erfasste einen weiteren Wake](second-observed-wake.json) um
19:00:44 Europe/Berlin nach 410,1 s Ruhe: verbunden nach 3 s, erste Audioausgabe
nach 5 s, beendet um 19:00:56 und wieder in Wake-Bereitschaft um 19:00:59.
Keine synthetische Wiedergabe oder Testsession wurde durch den Agenten gestartet.
Für diesen zweiten Durchlauf liegt keine gesonderte menschliche Bestätigung vor;
die Ereignisse beweisen daher weder die beabsichtigte Auslösung noch gehörten
Antwortinhalt oder einen bestimmten gesprochenen Ende-Befehl. Sie belegen einen
weiteren abgeschlossenen produktiven Zustandsablauf ohne beobachteten Startfehler.
Der Messdienst und der Browser liefen dabei ohne Neustart weiter.

### Auf Nutzerwunsch abgelöster Dauerlauf

Der Nutzer beauftragte am 15.10.2026 ausdrücklich den Einbau und Test von
„Hey KAI“ und „Okay KAI“. Der Beobachter wurde vor den neuen Pi-Tests beendet
und sein vollständiger Lauf unverändert unter `baseline-052` archiviert.
[Teilbeobachtung](partial-observation.json): kein bestandener 24-Stunden-Lauf,
kein Acht-Stunden-Ruhetest. Drei produktive Aktivierungen wurden erfasst, keine
Warnung oder Prozessgeneration gewechselt. Der ansteigende Browser-RSS ist
nicht abschließend bewertet. Für den neuen Release und das gewählte Rufwort
ist eine neue Langzeitmessung erforderlich.
