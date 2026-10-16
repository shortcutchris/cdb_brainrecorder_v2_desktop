# Wake Word: vertiefte Recherche und Vergleich auf dem Pi

Stand: 16. Oktober 2026. Der Benutzer hat die aktive Optimierung erneut beauftragt.
Das Ziel ist wieder aktiv; die automatische 24h-Beobachtung bleibt trotzdem rein
lesend. **Noch keine vollständige akustische oder Langzeitabnahme.**

## Entscheidungskriterien

Ein brauchbarer Ersatz muss den ersten Ruf auf Deutsch aus dem Raum erkennen,
ähnliche Alltagssätze ablehnen, nach langer Ruhe und Gesprächsende funktionieren
und die vorhandene atomare Audioreservierung respektieren. Ein Wortwechsel oder
ein niedrigerer Schwellwert allein gilt nicht als Verbesserung. Gewichtedatei,
Frontend, Laufzeit, Sprache und Lizenz müssen zusammen betrachtet werden.

## Projekte und konkrete Kandidaten

| Projekt | Eignung / aktueller Nachweis | Entscheidung |
| --- | --- | --- |
| microWakeWord / pymicro-wakeword | Sehr kleine lokale Streaming-Modelle. Installiertes **mehrsprachiges** Nabu mit Deutsch, Schwelle 0,85 und Fenster 5. Auf unserem Pi digital schnell, aber echte Raumtests lückenhaft. | Beibehalten als gemessene Baseline, nicht als bereits zuverlässiger Sieger. |
| ESPHome micro-wake-word-models v2 | Ebenfalls Nabu, aber **andere Gewichte**, Manifest Englisch, Schwelle 0,97. Repository erklärt Apache-2.0 ausdrücklich auch für Gewichte. | Separater Vergleich; nicht mit dem installierten mehrsprachigen Nabu verwechseln. |
| openWakeWord / pyopen-wakeword | Eigener Nabu-Klassifikator in der Rhasspy-Distribution. Mel-Spektrum → Embedding → Wortklassifikator. Vortrainierte dscripka-Gewichte haben CC BY-NC-SA 4.0; Apache-Code macht diese nicht automatisch kommerziell frei. Herkunft/Rechte aller übernommenen Gewichte separat klären. | Isolierter technischer Vergleich, noch kein Kundenpaket. |
| sherpa-onnx KWS | Kleines Zipformer-Transducer-Modell, konfigurierbare Phonemfolgen ohne Wort-Neutraining; ARM64/Python verfügbar. Offiziell gelistete KWS-Modelle Englisch bzw. Chinesisch/Englisch, kein ausgewiesenes Deutsch-KWS. | int8-3M-Modell als unabhängiger Vergleich, keine automatische Umstellung. |
| OHF Linux Voice Assistant | Linux-/Pi-Satellit mit microWakeWord und openWakeWord, separaten Audiozuständen und Refraktärzeit. | Referenz für Lebenszyklus und Audio; kein Ersatz für unsere CDB-/Recorder-App. |
| Mycroft Precise | Trainingsfähiger RNN-Wake-Detektor. Dokumentation enthält ältere Raspbian-/armv7-Installationswege. Aktuelle Pi-5-/Python-3.13-Qualifikation hier nicht nachgewiesen. | Kein schneller produktiver Ersatz. |
| Vosk / PocketSphinx | Offene Spracherkennung mit eingeschränktem Wortschatz möglich. Vosk-Brain/KAI hat im eigenen Projekt bereits natürliche Erst-Ruf-Fehler. | Nicht ohne neue Vergleichsevidenz zurückwechseln. |
| Voice Satellite / vsWakeWord | Browser-/WebGPU-orientierte Phonemerkennung; Integration AGPL-3.0. Projekt-Benchmarks sind keine Messung an unserem Pi. | Interessant, aber zusätzliche Browser-/Lizenz-/Hardwareprüfung; kein belegter Vorteil für die lokale Python-Audioführung. |

**Lizenzkorrektur sherpa:** Der Modellautor erklärt am 8.10.2026 in Issue #3802,
dass die ModelScope-Lizenz auf Apache 2.0 aktualisiert wurde. Der am 16.10.
abgerufene ModelScope-README enthält diese Angabe. Das GitHub-Modellarchiv selbst
enthält weiterhin keine entsprechende Lizenzdatei. Bei einer Auslieferung
Modellkarte, genaue Hashes und Lizenz-/Quellenhinweise zusammen konservieren;
Framework-Lizenz und Modelllizenz nicht gleichsetzen. Es wurde noch nichts davon
in das Kunden-Image aufgenommen.

## Methodik und Grenzen

Die Testmatrix enthält drei offizielle Nabu-Dateien, neun andere Rufwörter,
zwei neu erzeugte deutsche Nabu-Stimmen und einen deutschen Negativtext mit
ähnlichen Formulierungen. Je Original, 0,25-facher Pegel sowie 0,25-facher Pegel
plus deterministisches Rauschen (Standardabweichung 0,002, Seed 743).
Das sind **15 positive und 30 negative Varianten, aber nur fünf positive und
zehn negative Ausgangsdateien**. Varianten sind korreliert, keine 45 Personen.

Neue Teststimmen: ElevenLabs multilingual_v2, Deutsch, Geschwindigkeit 1,0,
Vincent und Pauli; keine Stimme geklont. MP3 anschließend korrekt auf 16 kHz,
16 Bit, Mono gewandelt. Negativtext beginnt mit „Okay, na gut.“ und enthält
kein beabsichtigtes Nabu. Generierte Aussprache und realer Raum bleiben eigene
Prüfpunkte; eine TTS-Sollbeschriftung ist keine menschliche Hörabnahme.

Alle Kandidaten laufen getrennt von der produktiven App. Auf dem Pi werden nur
bekannte Testdateien verarbeitet, mit niedriger Prozesspriorität. Keine
Raumaufnahme, keine Cloud-Sitzung, keine produktive Runtime-Installation.
Die gemessene CPU-Zeit umfasst aufgefüllte Stille. Bei micro/open wird das
Modell je Fall innerhalb der Messung neu angelegt; bei sherpa liegt die
einmalige Modellanlage außerhalb. Die CPU-Werte sind deshalb **kein fairer
reiner Inferenzvergleich** und kein gemessener Dauerverbrauch. Trefferframes sind keine Anzahl
unabhängiger Aktivierungen. Produktiv wird der Detektor nach dem ersten Treffer
freigegeben und der Übergang genau einmal reserviert.

## Akustik bereits eingegrenzt

[Raumtest und Kanalvergleich](../../observer-nabu-20261016/README.md):
Mac-Studio-Lautsprecher explizit statt externem Kopfhörerausgang, unveränderte
Systemlautstärke. Dateiwiedergabe mit Originalrate. PCM nur vorübergehend im RAM,
gespeichert werden Pegel, Modellwerte und Korrelation zur bekannten Testdatei.
Korrelation zeigt Signaltransport, nicht Verständlichkeit.

Der ReSpeaker hat verarbeitete Conference-/ASR-Kanäle. Beide separat und ihr
Mittel wurden mit identischen Modellen am selben Mitschnitt verglichen. Kein
Kanal gewinnt zuverlässig; daher kein unbewiesener Kanalwechsel im Produkt.
Höhere Lautstärke hilft einzelnen Dateien, behebt aber nicht alle Aussetzer.

## Abnahme und weitere Umsetzung

1. Kandidaten unter identischen Dateien vergleichen, inklusive bewusster
   Verwechslungswörter. Kein Schwellen-Tuning auf dem späteren Abnahmesatz.
2. Besten begründeten Kandidaten mit neuen Stimmen und denselben Raumwegen
   prüfen. Natürliche Erst-Rufe bleiben zusätzlich notwendig.
3. Erst mit besserer Trefferquote **ohne neue Fehlstarts** produktive Integration:
   lokale Inferenz, genau ein Mikrofonbesitzer, Aufnahme/Pause/Gespräch geschützt,
   begrenzter Start/Abbruch und erneute Bereitschaft. Keine Wortfetzen speichern.
4. Neue Abnahmeserie mit unabhängigen Stimmen, mindestens 100 natürlichen Rufen
   in definierten Bedingungen und acht Stunden negativer Umgebung. Bestehende
   Zielwerte ≥95 % Erst-Ruf-Treffer und höchstens ein Fehlstart in acht Stunden
   sind Entwicklungsziele, keine statistische Garantie.
5. 24h-Ressourcenprüfung plus tatsächlicher Ruf nach acht Stunden belegter Ruhe,
   Doppelnennungen, wiederholte Gespräche, Fehler-/Rückkehrtests. Historische
   Fehlschläge bleiben Teil der Bewertung. Das aktuelle Beobachtungsfenster
   enthält Testlast und Wartungsunterbrechungen, also keine saubere Langzeitabnahme.

## App- und Image-Auswirkung

Diese Vergleichsstufe verändert noch keine produktive Engine, Schwelle,
Mikrofonkonfiguration oder Firmware. Diagnose-/Laborskripte sind keine
Runtime-Abhängigkeiten und werden nicht ins SD-Image kopiert. Ein späterer
Enginewechsel verlangt gepinnte Pakete, Gewichte/Hashes, überprüfte Rechte,
Runtime-Migration für vorhandene Geräte sowie Factory-Anpassung und erneuten
Boot-/Audiotest für neue Images. App-Code allein installiert keine neue Runtime.

## Primärquellen (abgerufen 16.10.2026)

- [microWakeWord Training](https://github.com/OHF-Voice/micro-wake-word)
- [Python-API und Streamingvertrag](https://github.com/OHF-Voice/pymicro-wakeword)
- [Installiertes mehrsprachiges Nabu-Manifest](https://github.com/OHF-Voice/pymicro-wakeword/blob/main/pymicro_wakeword/models/okay_nabu.json)
- [Separates ESPHome-v2-Manifest](https://github.com/esphome/micro-wake-word-models/blob/main/models/v2/okay_nabu.json) und [Gewichtelizenz](https://github.com/esphome/micro-wake-word-models#license)
- [openWakeWord: Architektur, Evaluation und Lizenz](https://github.com/dscripka/openWakeWord)
- [Rhasspy Python-Nabu-Implementierung](https://github.com/rhasspy/pyopen-wakeword)
- [sherpa-KWS-Grundlagen](https://k2-fsa.github.io/sherpa/onnx/kws/index.html), [konkrete Modelle](https://k2-fsa.github.io/sherpa/onnx/kws/pretrained_models/index.html)
- [Modellautor zur Lizenz, #3802](https://github.com/k2-fsa/sherpa-onnx/issues/3802), [ModelScope-Modellkarte](https://modelscope.cn/models/pkufool/icefall-kws-zipformer-zh-en-3M-2025-12-20)
- [OHF Linux Voice Assistant](https://github.com/OHF-Voice/linux-voice-assistant)
- [Mycroft Precise](https://github.com/MycroftAI/mycroft-precise), [PocketSphinx](https://cmusphinx.github.io/wiki/about/)
- [Voice Satellite](https://github.com/jxlarrea/voice-satellite-card-integration)
- [Seeed: Conference/ASR](https://wiki.seeedstudio.com/respeaker_xvf_3800_arm/), [Seeed: Kanalvergleich und SNR](https://wiki.seeedstudio.com/respeaker_xvf3800_faq/)

## Gemessene Ergebnisse auf dem Pi 5

Alle Fälle desselben Korpus, ohne Raumweg. Laufzeiten sind CPU-Sekunden für
280,013 Sekunden Testaudio einschließlich Vor-/Nachstille. Modellanlage bei
micro/open enthalten, bei sherpa ausgeschlossen; siehe Methodik.
Schwellen gehören zu verschiedenen Modellen und sind nicht direkt vergleichbar.

| Kandidat | Positive Varianten | Negative Varianten mit Treffer | CPU-Zeit |
| --- | ---: | ---: | ---: |
| [microWakeWord mehrsprachig, 2.5.0](micro-initial-pi.json), 0,85 | 12/15 | 3/30 | 1,48 s |
| [ESPHome-v2-Nabu via 2.5.0](micro-v2-initial-pi.json), 0,97 | 12/15 | 3/30 | 1,41 s |
| [pyopen-wakeword 1.1.0 Nabu](open-1.1-pi.json), 0,5 | 5/15 | 3/30 | 37,80 s |
| [sherpa-onnx 1.13.8 zh-en-3M int8](sherpa-1.13.8-pi.json), Standardparameter | 0/15 | 0/30 | 12,60 s |

Die drei negativen Varianten mit microWakeWord-Treffer sind derselbe deutsche
Negativtext in drei Signalbedingungen, **nicht drei unabhängige Wörter**.
Die erste Aktivierung liegt bereits im Anfang „Okay, na gut“. Bei microWakeWord
wurden zwei neue deutsche Positivdateien digital ohne zusätzliches Rauschen
angenommen. Daraus folgt trotzdem keine akustische Raumtauglichkeit.

sherpa wurde mit der expliziten englischen Phonemfolge
`OW2 K EY1 N AA1 B UW1` geprüft. Das ist eine Versuchs-Konfiguration, kein
optimiertes deutsches Modell. Ein [Kontrolltest](sherpa-controls.json) erkennt
den offiziellen „LIGHT UP“-Clip; fünf Nabu-Aussprachevarianten erkennen die
zusätzlich geprüften Dateien weiterhin nicht. 0/30 ist damit kein Gütesiegel:
Ein Detektor, der gar nicht auf Nabu anspricht, ist unbrauchbar. Modelltraining
oder weitere Sprach-/Phonemanpassung kann andere Ergebnisse liefern.

Erste Vergleichsläufe nutzten pyopen-wakeword 1.0.0 und sherpa 1.12.37; ihre
Berichte bleiben als `*-initial-pi.json` erhalten. Danach wurde bewusst auf
aktuell veröffentlichte 1.1.0 bzw. 1.13.8 **nur in /tmp-Laborumgebungen**
aktualisiert und wiederholt. Die Trefferzahlen blieben gleich. 1.0.0 hatte zudem
eine fehlende gebündelte TFLite-Bibliothek und keinen close-Adapter; im begrenzten
Vorversuch wurde die vorhandene Bibliothek nur lesend referenziert. Kein solcher
Workaround wird produktiv ausgeliefert. Ein früher sherpa-Kontrolllauf las ein
verbrauchbares Resultat zweimal; der bestätigte Kontrolltest liest es einmal.
Mac-Archiv-Metadaten wurden als WAV fehlinterpretiert; die Werkzeuge überspringen
inzwischen `._`-Dateien. Fehlgeschlagene Vorläufe sind keine erfolgreichen Tests.

**Auswahlentscheidung:** Keiner dieser Vergleiche rechtfertigt jetzt einen
produktiven Enginewechsel. Insbesondere würden eine bloße Schwellenabsenkung
oder der Wechsel auf einen anderen ReSpeaker-Kanal die gemessene Verwechslung
nicht beheben. Nächste Arbeitsstufe: natürliche Baseline mit der neuen
Diagnose, unabhängige Negativsprache, dann gezielter Verifikator bzw. Nachtraining
mit getrennten Trainings- und Abnahmedaten. Kein Training auf Testdateien und
anschließendes Ausgeben derselben Dateien als unabhängige Abnahme.

## Umgesetzte Verbesserung 0.5.60: verpasste Rufe sichtbar machen

Der Nabu-Adapter liefert zusätzlich den höchsten Modellwert je Audioblock.
Die Entscheidung verwendet weiterhin exakt den dokumentierten strikten
Vergleich `probability > probability_cutoff`; Fenster, Feature-Verarbeitung,
Modell und Schwelle bleiben gleich. Auch nach einem Treffer werden alle fünf
10-ms-Unterblöcke verarbeitet. Ungültige Modellwerte werden nicht akzeptiert.

Die vorhandene lokale Diagnose aggregiert das Maximum bis zur nächsten Meldung.
Ein begrenzter Ring hält höchstens 16 relevante Meldungen mit Pegel, Modellwert
und Schwelle fest. Auch ein Wert unter 0,85 kann so sichtbar bleiben. Die Grenze
0,1 dient ausschließlich der Diagnoseauswahl, **niemals der Aktivierung**.
Diagnosedaten starten kein Gespräch und ersetzen weder Audio-Heartbeat noch
Bereitschaftsmeldung. Keine PCM-Samples oder entschlüsselten Raumtexte werden
gespeichert. Bestehende Diagnosemeldungen ohne diese Felder bleiben gültig.

Damit ist eine Diagnose-Lücke geschlossen, **noch keine Erkennungsrate verbessert**.
Die 45 Vergleichsfälle müssen vor/nach Änderung dieselben Entscheidungen und
Modellmaxima haben. Natürliche Fehlschläge lassen sich danach ohne neuen
Mikrofonbesitzer untersuchen.

App-/Image-Auswirkung dieser konkreten Änderung: nur vorhandene Python-Dateien
und Versionsquelle, keine neue Runtime oder Gewichte. Ein signiertes App-Update
übernimmt die Änderung unter Wartungssperre; das nächste Kunden-Image enthält
sie über die bestehende Positivliste. Bestehende Konten, Aufnahmen und Audio-
Auswahl bleiben erhalten. Ein Image-Export ist kein gebautes/gebootetes Image.

## Validierung der Diagnoseänderung

[Prüfprotokoll](validation.json): 34 gezielte lokale Tests und **397 Python-Tests
auf dem Pi** bestanden. Der Pi-Gesamtlauf meldete zusätzlich einen nicht
fehlschlagenden älteren Übersetzungsfehler bei Latin-1-Konsolenausgabe sowie
einen ResourceWarning beim Interpreter-Ende; diese Warnungen werden nicht
als behoben ausgegeben. Der lokale Wake-Zustandstest war zuvor ungewollt von
installierten Vosk-Dateien abhängig und setzt nun die Runtime-Verfügbarkeit
für seine isolierten Zustandstests ausdrücklich; separate Fehlende-Runtime-
Tests bleiben erhalten.

[45 Vorher-/Nachher-Fälle](micro-060-pi.json): exakt gleiche Entscheidungen,
Trefferframes, erste Trefferzeit und Modellmaxima. [Offizielle Regression](wav-regression-060.json):
3/3 positive Dateien, 0/9 andere Rufwörter, 100/100 erneuerte Zyklen und zehn
Minuten beschleunigte digitale Stille mit anschließendem Treffer bestanden.
Dies hebt die dokumentierten deutschen Negativ-/Raumfehler nicht auf.

`benchmark_wake_candidates.py` ist ein explizites Laborwerkzeug. Referenzordner
und deutscher Korpus werden als Argumente angegeben, zusätzliche Modelle und
TFLite-Bibliothek optional über eigene Pfade. Maximal 64 bekannte Dateien bis
je 60 Sekunden; keine Audio-Geräte, kein automatischer Download. Für lange
native Vergleiche zusätzlich einen Prozess-Timeout setzen. Der Korpus bleibt
außerhalb des Kundenpakets; JSON-Berichte enthalten Hashes und technische Werte.

## Auslieferung bestätigt

App **0.5.60**, signierte Sequenz **17**, Quellcommit
`2ad59b3c4d5eb513ccf1d4cfae44564a23e1245b`. [Installation](deployment.json)
bestätigt erhaltene Einstellungen und unveränderte produktive Runtime.
[Sechs Nachprüfungen](installation-check.json): API und HTML 0.5.60,
Nabu aktiv/listening, genau ein stabiler Wake-Prozess, neue numerische Diagnose
mit unveränderter Schwelle 0,85. Alle vier installierten Datei-Hashes entsprechen
dem signierten Manifest. Keine alternative Engine auf dem Produktivpfad.

[Image-Export](image-export-check.json): 121 zugelassene Dateien, geänderte
Laufzeitdateien exakt enthalten. Nur Baupaket, kein neues bootgeprüftes SD-Image.
Der Beobachter läuft weiter mit Originalplan und markiert Versionswechsel;
kein Zurücksetzen oder Zusammenzählen früherer Zeitfenster.


## Deutscher Vosk-Gegencheck und unabhängige neue Beispiele

Das offizielle [kleine deutsche Modell 0.15](https://alphacephei.com/vosk/models)
(45 MB, Apache-2.0 laut Modellliste) wurde ausschließlich unter `/tmp` auf dem Pi
entpackt. [Herkunft und Archivhash](vosk-provenance.json). Kein Paket, kein
Audio-Gerät und keine produktive Einstellung wurden dafür geändert.

Der [Wortschatztest](vosk-vocabulary-probe.json) zeigt: **„nabu“ fehlt**, „naboo“
ist enthalten. Freie Erkennung deutet die zwei positiven deutschen TTS-Dateien
als „okay abo“ / „kein abo“. Den problematischen Negativclip erkennt sie dagegen
als „okay na gut …“. Das ist ein unabhängiges Indiz für die Fehlaktivierung,
keine menschliche Hörabnahme. Ein vorheriger Whisper-medium-Gegencheck blieb
nach 120 Sekunden ohne Ausgabe und wurde vom gesetzten Timeout beendet;
dieser Versuch gilt ausdrücklich nicht als erfolgreiche Transkription.

Eine explorative Grammatik verwendet „naboo“ als phonetischen Stellvertreter,
mit `[unk]` und einigen Gegenphrasen. Das fügt **kein echtes Nabu-Lexikon** hinzu.
Die Gegenphrasen wurden anhand bereits bekannter Beispiele gewählt, weshalb
alle Ergebnisse auf diesem Basissatz nur Entwicklungsevidenz sind.

| Unveränderte Versuchskonfiguration | Positive Varianten | Negative Varianten mit Treffer |
| --- | ---: | ---: |
| [Deutsche Grammatik, bisheriger Basissatz](vosk-de-baseline-pi.json) | 15/15 | 0/30 |
| [Deutsche Grammatik, neue Otto-/Ben-Stimmen](vosk-de-holdout-pi.json) | 6/6 | **1/6** |
| [Produktives microWakeWord auf denselben neuen Dateien](micro-holdout-pi.json) | 6/6 | **3/6** |

Der neue Satz besteht aus nur zwei positiven und zwei negativen Ausgangsdateien,
jeweils mit drei Signalvarianten, **nicht zwölf unabhängigen Sprechern**.
Neue Negativformulierungen enthalten unter anderem „Okay, na bitte“, „Okay, na
und“, „Abo“, „Angebot“, „Nanu“, „nach Hause“ und „Nachbar“. Grammatik und
Entscheidungsregel wurden vor ihrer Generierung festgeschrieben und danach
nicht angepasst. Vosk verwechselt den Otto-Negativtext bei 0,25 Pegel plus
Rauschen mit „ok naboo“. Diese Datei darf bei künftigem Tuning nicht mehr als
unberührter Abnahmesatz ausgegeben werden.

**Entscheidung:** Deutsches Vosk bleibt ein Forschungskandidat für eine zweite
Kontrolle. Die neuen Daten rechtfertigen keine Produktionsumstellung. Weder
„15/15“ noch eine bessere Fehlerzahl im winzigen Vergleich beweisen eine
stabile Erkennung. Eine Grammatik mit immer mehr bekannten Fehlersätzen würde
das eigentliche Generalisierungsproblem verschleiern.

### Reproduzierbarkeit und Werkzeugkorrektur

`scripts/benchmark_vosk_wake.py` benötigt explizite synthetische Dateimanifeste,
ein vorhandenes Modell und eine Grammatik. Es prüft 16-kHz-Mono-PCM, maximal
64 Dateien mit je 60 Sekunden sowie sämtliche Wörter gegen das Modelllexikon.
Fehlende Wörter werden abgewiesen statt unbemerkt aus der Grammatik gestrichen.
[Basissatz](vosk-baseline.json), [neuer Satz](vosk-holdout.json) und
[Grammatik](vosk-grammar.json) halten Eingaben fest; die WAVs liegen nur im Labor.

Auf dem Pi, mit vorhandener Vosk-/NumPy-Laborruntime, beispielsweise:

```sh
nice -n 15 timeout 90 python scripts/benchmark_vosk_wake.py \
  --model /tmp/cdb-vosk-de-lab/vosk-model-small-de-0.15 \
  --manifest docs/wake-word-research/2026-10-16/vosk-holdout.json \
  --grammar docs/wake-word-research/2026-10-16/vosk-grammar.json \
  --output /tmp/vosk-holdout.json
```

Die Vosk-CPU-Messung umfasst Recognizer-Neuanlage und Inferenz; Modellladen
wird separat als Wandzeit ausgewiesen. Sie ist keine gemessene Wake-Latenz.
20 lokale gezielte Tests bestanden, darunter OOV-Abweisung und Eingabegrenzen.
Beide Vosk-Matrizen wurden mit dem gespeicherten Werkzeug auf dem Pi wiederholt.

Zusätzlich korrigiert der allgemeine Benchmark beim Austausch des micro-v2-
Modells jetzt dessen seit 0.5.60 gecachten Schwellwert. Der
[erneute v2-Lauf](micro-v2-060-pi.json) stimmt in allen 45 Fällen einschließlich
Trefferframes, Zeit und Modellmaxima mit dem alten, vor dem Cache aufgenommenen
Lauf überein. Die alten Messwerte waren gültig; die Korrektur verhindert falsche
künftige Vergleiche mit der Schwelle des zuvor erzeugten Modells.

### Nächste belastbare Entwicklungsstufe

Ein eigenes Nabu-Modell bzw. eine zweite lokale Prüfung braucht getrennte
Trainings-, Validierungs- und Abnahmedaten mit mehreren deutschen Stimmen,
Raum-/Entfernungsvariation und längeren negativen Umgebungen. Die bislang
gefundenen Verwechslungen gehören zu Entwicklungsdaten. Neue Sprecher und
neue Negativformulierungen bleiben bis zur Abnahme unangetastet.

[microWakeWord](https://github.com/OHF-Voice/micro-wake-word) unterstützt dieses
Vorgehen mit synthetischen Daten, Augmentierung und getrennten negativen
Umgebungssets; das Projekt warnt selbst vor der Schwierigkeit guten Trainings.
[openWakeWords Sprecher-Verifier](https://github.com/dscripka/openWakeWord/blob/main/docs/custom_verifier_models.md)
kann Fehlaktivierungen reduzieren, benötigt aber Beispiele der Zielsprecher
und ähnlicher Räume. Ein ausschließlich auf Chris trainierter Filter wäre
kein allgemeiner Ersatz für ein Kundengerät. Für Vosk sind
[Lexikon-/Graphanpassung und Akustik-Finetuning](https://alphacephei.com/vosk/adaptation)
getrennte Schritte; eine eingeschränkte Grammatik allein erweitert den
Wortschatz nicht.

Der Benutzer ist aktuell nicht am Pi. Der natürliche Erst-Ruf-Test bleibt
offen; die Frage wird bis zu seiner Rückkehr nicht wiederholt. Produktiv bleibt
0.5.60 mit derselben Engine, Schwelle und Audioführung. Diese Ergänzung betrifft
nur Laborwerkzeuge/Dokumentation und hat keinen App-Update- oder SD-Image-Inhalt.
Der laufende Beobachtungsplan bleibt erhalten; zusätzliche CPU-Testlast ist
keine ungestörte Ruhezeit. Das Gesamtziel bleibt aktiv und nicht abgenommen.


## ReSpeaker-Raumvergleich der deutschen Zusatzprüfung

Am 16.10.2026 von **13:49:04 bis 13:51:31 Europe/Berlin** wurden vier bekannte
synthetische Dateien über den Mac-Studio-Lautsprecher abgespielt, jeweils nach
30 Sekunden echter Ruhe. Derselbe 16-kHz-Mono-Eingang ging an microWakeWord und
nach dem begrenzten Mitschnitt im RAM an den unveränderten deutschen Vosk-
Versuch. [Vollständige technische Messwerte](acoustic-vosk-comparison.json).

| Gespielte Datei | microWakeWord | Deutscher Versuch |
| --- | --- | --- |
| Otto: Okay Nabu | erkannt, Maximum 0,91719 | verpasst |
| Ben: Okay Nabu | erkannt, Maximum 0,97734 | verpasst |
| Bekannter Gegenclip: Okay, na gut … | **Fehlaktivierung**, Maximum 0,99141 | abgelehnt |
| Otto-Negativtext, erste 7,8 Sekunden | abgelehnt, Maximum 0,66250 | abgelehnt |

Damit **2/2 positive und 1/2 negative Dateien ausgelöst** bei microWakeWord,
**0/2 positive und 0/2 negative** bei der deutschen Zusatzprüfung. Die besseren
Datei-Ergebnisse von Vosk übertragen sich hier nicht auf den Raum. Ein AND-
Filter mit dieser Prüfung würde beide funktionierenden Rufe blockieren; ein
solcher Produktivumbau wird verworfen. Die hohe Modellwahrscheinlichkeit des
Gegenclips zeigt auch, weshalb eine bloße Schwellenänderung nicht ausreicht.

Der Gegenclip mit 7,8 Sekunden ist ein explizit gekürzter synthetischer
Laborclip, keine neu behauptete unabhängige Stimme. Trefferframes (z.B. neun
Frames im ersten Ruf) sind keine neun Gespräche. Vosk-Zeiten von 0,115–0,344
CPU-Sekunden betreffen Auswertung nach der Aufnahme, **keine gemessene Live-
Antwortzeit**. Es wurden weder Raum-PCM noch erkannte Raumtexte gespeichert.
Die optionale Zweitprüfung des Laborwerkzeugs gibt nur feste Trefferzahlen aus.
Acht gezielte Tests, einschließlich Schutz vor Ausgabe von erkanntem Raumtext,
bestanden. Originalrate und expliziter Mac-Studio-Lautsprecher wurden bestätigt,
Player-Lautstärke 1,0 bei unveränderter Hardwarelautstärke ca.0,5.

Die atomare Wartungssperre wurde erfolgreich freigegeben; danach listening,
frische Audioblöcke und genau ein Wake-Kind mit einem Capture-Prozess geprüft.
Keine Aufnahme oder Cloud-Unterhaltung gestartet. Dieser angekündigte Test
unterbricht die Ruhezeitevidenz; der ursprüngliche Beobachtungsplan wird nicht
zurückgesetzt. Werkzeug und Bericht betreffen weiterhin keine Kunden-Runtime,
kein App-Paket und kein SD-Image.


## Whisper Tiny als begrenzte zweite Wortprüfung

[Whisper](https://github.com/openai/whisper) mit
[whisper.cpp](https://github.com/ggml-org/whisper.cpp) ist hier ein separater
ASR-Gegencheck nach einem möglichen Ruf, kein neuer Dauermikrofonprozess.
Das mehrsprachige Tiny-Modell wurde nur unter `/tmp/cdb-whisper-verifier`
heruntergeladen; weder die App-Modellauswahl noch das Kunden-Image geändert.
Gewichtsquelle: `https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.bin`.
SHA256 `be07e048e1e599ad46341c8d2a135645097a538221678b7acdd1b1919c6e1b21`.

Drei vorab begrenzte Varianten wurden auf denselben bekannten Dateien geprüft:

- [Standardkontext, kein Schreibhinweis](whisper-tiny-file-probe.json): 2,22–2,42
  Sekunden inklusive Prozess-/Modellstart; positive Namen als „na, bo“/„Nabum“.
- [Audiokontext 256, kein Hinweis](whisper-tiny-short-context.json): 0,29–0,38
  Sekunden, aber weiterhin Namensfehler („nable“/„Nabum“).
- [Audiokontext 256, Hinweis `Nabu.`](whisper-tiny-prompt-probe.json): 0,31–0,40
  Sekunden, beide positiven Dateien korrekt und „na gut“ weiterhin unterschieden.

Keine unscharfe Namenssuche, keine Akzeptanz von „Nabum“/„nable“. Die eingefrorene
Regel verlangt als erste zwei normalisierte Wörter exakt `okay`/`ok` und `nabu`.
Der Namenshinweis kann Halluzinationen begünstigen; deswegen genügt ein positiver
Einzeltest nicht. [Erweiterter Dateivergleich](whisper-tiny-matrix.json):
**21/21 positive Varianten, 0/36 negative Varianten**, keine Timeouts.
Das sind sieben positive und zwölf negative Ausgangsdateien, je drei korrelierte
Pegel-/Rauschvarianten. Mehrere Stimmen und Formulierungen waren aus vorigen
Experimenten bereits bekannt. Keine unabhängige statistische Zuverlässigkeits-
oder natürliche Sprachabnahme. Zwei längere Negativtexte und die längere offizielle Nabu-Datei `3.wav` wurden
ausdrücklich auf die ersten 4,8 Sekunden begrenzt; spätere Abschnitte sind nicht
geprüft. Über alle 57 Varianten liegt die Wandzeit bei 0,295–1,850 Sekunden,
Median 0,323 Sekunden. Die kurzen Vorproben von 0,3–0,4 Sekunden sind deshalb
keine allgemeine Latenzgarantie.

Die [exakte Matrix-Reproduktion](reproduce_whisper_matrix.py) ist Laborcode mit
bekannten `/tmp`-Pfaden, ohne Mikrofon/Netzwerk. Der Aufruf verlangt die vorhandene
Pi-NumPy-Runtime und sollte durch `nice -n 15 timeout 180 python ...` begrenzt
werden. Modelle, Originaldateien und Roh-Audio werden nicht ins Repository kopiert.

Für den Raumversuch verwendet `scripts/wake_whisper_probe.py` Linux `memfd`:
WAV-Header und höchstens 4,8 Sekunden PCM liegen nur in einem anonymen RAM-
Deskriptor, der an den begrenzten Kindprozess vererbt und danach geschlossen
wird. Keine temporäre Raum-Audiodatei, kein gespeicherter erkannter Raumtext.
Berichte enthalten nur Entscheidung, begrenzte Laufzeit und Rückgabecode.
Fehlgeschlagener Prozess oder Timeout dürfen nicht als erkannter Ruf gelten.
Diese Prüfung läuft nach der Erfassung auf identischem PCM unter der bestehenden
Wartungssperre; sie ist weiterhin keine produktive Streaming-Integration.


### Whisper: erstes positives Raumergebnis, Integration noch offen

[Raumvergleich](acoustic-whisper-comparison.json) am 16.10.2026 von **13:59:43
bis 14:02:16 Europe/Berlin**, gleiche Lautsprecher-/Mikrofonführung und je
30 Sekunden Ruhe. Otto und Ben korrekt bestätigt, beide Negativclips abgelehnt:
**2/2 positive, 0/2 negative Dateien ausgelöst**. Gleichzeitig löst die
unveränderte microWakeWord-Baseline bei „Okay, na gut“ wieder aus.

Die Whisper-Prüfung benötigte hier **1,773–1,836 Sekunden** nach der Erfassung.
Ein schneller Dateitest ist somit kein Nachweis dieser Geschwindigkeit im Raum.
Nur jeweils die ersten maximal 4,8 Sekunden ab Abspielhinweis wurden in den
Verifier gegeben; das enthält auch die Anlaufzeit der entfernten Wiedergabe.
Der längere Negativtext ist dadurch nur teilweise überprüft. Der Bericht hält
Kürzung, WAV-Hash, Signaltransport und tatsächliche Wiedergabe getrennt fest.

**Dies ist ein belegter Kandidat, noch keine produktive Verbesserung:** Die
Prüfung wurde erst nach der Erfassung ausgeführt. Ein laufender Ringpuffer,
geeignetes Kandidatenfenster, Rate-Limit für Fehlkandidaten, Audio-Rückstau,
begrenzter Abbruch und Rückkehr zur Bereitschaft sind damit noch nicht geprüft.
Die geprüften synthetischen Stimmen ersetzen außerdem den ausstehenden
natürlichen Erst-Ruf-Test nicht. Aktuell gibt es keine geänderte produktive
Erkennungsregel, keine zusätzliche Runtime und keinen neuen Download im Image.

Vor einer Auslieferung:

1. Lokalen Kandidatenpfad innerhalb desselben Wake-Kindprozesses entwickeln;
   genau ein Audioeingang, begrenzter RAM-Ring, keine PCM-Dateien/Transkripte.
2. Niedrigere Kandidatenschwelle nur für die Prüfung, niemals direkte Aktivierung.
   Kandidatenende und Zeitfenster anhand von getrennten Entwicklungsdaten prüfen;
   volle Wortprüfung entscheidet erst nach vollständiger Phrase.
3. Begrenzte Verifier-Prozesse, Rate-Limit, Timeout, kein Kindprozess nach Abbruch.
   Aufnahme-/Live-/Wartungsreservierungen behalten Vorrang; nicht nebenbei im
   Backend-Control-Lock rechnen. Hardware-/Netzfehler dürfen kein Erfolg sein.
4. Konkurrierende Zustände, lange negative Umgebung, 100 Zyklen und neue
   akustische Rufe mit unveränderten Entscheidungskriterien prüfen. Erst dann
   signierte App-/Runtime-Auslieferung mit gepinntem Modellhash und Factory-
   Installation vorbereiten; vorhandene Konfiguration weiterhin erhalten.

Elf gezielte Labor-/Datenschutz-/Eingabe-/Timeouttests bestanden. Nach dem
Raumtest: Wartung freigegeben, `listening`, frische Audioblöcke, ein Wake-Kind und
ein Capture-Prozess, keine laufende Whisper-Testinstanz. Beobachtungsplan und
alte Befunde bleiben erhalten. Der natürliche Nutzer-Test ist weiterhin offen.


## Streaming-Prototyp: Schutzmechanik geprüft, Raumqualität noch nicht bestanden

`scripts/wake_streaming_probe.py` ist **unveröffentlichter Laborcode**, außerhalb
der App-/Image-Positivliste. Der produktive Pi bleibt auf 0.5.60. Er verwendet
nur vom Aufrufer gelieferte 50-ms-Blöcke, maximal 4,8 Sekunden RAM-Ring, einen
asynchron abgefragten nativen Verifier und keine Threads oder zweite Aufnahme.
Die vor dem Raumtest festgelegte Kandidatenschwelle 0,15 startet ausschließlich
Prüfungen, niemals Live. Zwei Sekunden Rückblick plus 0,8 Sekunden Nachlauf
bilden den 2,8-Sekunden-Prüfausschnitt. Nach Ablehnung erfordern erneute Prüfungen
mindestens zwei Sekunden Abstand und 300 ms niedrigen Primärscore. Annahme wird
bis zur Freigabe des Detektors einmalig verriegelt.

Der Verifier nutzt denselben anonymen RAM-Deskriptor wie die Vorprüfung, begrenzt
Ausgabe auf 8192 Bytes und Laufzeit auf drei Sekunden. Abfragen sind nichtblockierend.
Eine fehlgeschlagene Beendigung behält die Prozesszuordnung; darüber kann kein
zweiter Prozess gestartet werden. Fehler/Timeout führen niemals zur Aktivierung.
Native Inferenz läuft als Child mit Parent-Death-Signal, nicht im App-Control-Lock.

**12 isolierte Tests auf dem Pi** bestanden (neun Streaming-/Prozesstests plus
drei Verifier-Tests), lokal zusätzlich zwei akustische Helfertests, insgesamt
14. Darunter echte Teilantwort-/Fehler-/Ausgabelimit-Kindprozesse, 100 isolierte
Annahme-/Schließzyklen und Ablehnung bei nicht bestätigter Freigabe. Der separate
[Linux-Absturztest](streaming-owner-death.json) beendet einen eigens gestarteten
Laborbesitzer per SIGKILL: Sein nativer Testprozess war nach rund 1,2 ms nicht
mehr vorhanden. Keine produktiven Prozesse wurden dafür beendet.

[Dateistrom im echten Audiotakt](streaming-file-probe.json): vier positive und
zwei negative Fälle korrekt, ohne Mikrofon/Lautsprecher. Zwei verrauschte
positive Dateien mit Primärmaxima 0,678 und 0,804 wurden nun bestätigt, obwohl
sie die bisherige 0,85-Schwelle nicht erreichen. Kein Audioschritt dauerte in
diesem Lauf länger als ca.6 ms; die Prüfungen liefen parallel zum weiteren
Einlesen. [Exakte Labor-Reproduktion](reproduce_streaming_matrix.py).
Dies ist ein konkreter Dateifortschritt, noch keine akustische Abnahme.

### Der anschließende Raumtest widerspricht einer Freigabe

[Unveränderte Rohmessung](acoustic-streaming-probe.json), **16.10.2026,
14:14:35–14:17:01 Europe/Berlin**: Beide positiven synthetischen Rufe wurden
letztlich verworfen, und „Okay, na gut“ wurde diesmal fälschlich bestätigt.
Der zweite Negativclip blieb ohne Aktivierung. **0/2 positive, 1/2 negative
Dateien ausgelöst**; kein Gespräch gestartet, da der Versuch unter Wartung lief.
Die erfolgreiche nachträgliche Whisper-Prüfung auf längerem PCM beweist damit
nicht die Zuverlässigkeit des kürzeren dynamischen Kandidatenfensters.

Zusätzlich sichtbar: Die zweite Prüfung war am Ende ihres Erfassungsabschnitts
noch offen und wurde erst in der Ruhephase der dritten Zeile abgelehnt. Die
zweite Zeile enthält deshalb einen alten last_report; die erste Ablehnung der
dritten Zeile gehört zur zweiten Rufdatei. Rohdaten bleiben unverändert. Der
Laborablauf wurde korrigiert: Ein offener Kandidat wird vor dem nächsten Clip
höchstens vier Sekunden weiter bedient; wenn er dann noch offen ist, wird der
Versuch abgebrochen. Alte Ergebnisse werden nicht in eine neue leere Zeile
übernommen. Dieser Messfehler erklärt **nicht** den tatsächlichen Fehlstart
bei „na gut“ und macht aus dem Raumtest keinen Erfolg.

**Keine produktive Auslieferung dieses Kandidaten.** Nächste Untersuchung:
kurze isolierte Verwechslungsphrasen, Zuschnitt-/Kontextrobustheit und stärkerer
lokaler Verifier. Der Schreibhinweis „Nabu“ darf nicht über eine fälschliche
Bestätigung hinwegtäuschen. Neue Entscheidungskriterien benötigen wieder
getrennte Dateien und Raumprüfung; nicht bloß die bekannten Fälle passend tunen.
Natürlicher Nutzertest und Langzeitabnahme bleiben offen.

Nach dem Raumtest: Wartung erfolgreich freigegeben, ein neuer Wake-/Capture-
Besitzer, frische Audioblöcke und listening. Der echte Beobachter PID 1894368
läuft weiter; um 14:20 Uhr keine aktiven Warnungen, Browser ca.28 % eines Kerns,
RSS ca.1308 MB, Temperatur51,8 °C. Diese Stichprobe beweist weder dauerhafte
Ressourcenstabilität noch Erkennungsqualität. Ursprünglicher 24h-Plan erhalten;
der angekündigte Raumtest unterbricht die Ruhezeitevidenz. Alle neuen Dateien
sind Laborwerkzeuge, Tests und Doku; kein Kundenpaket und kein SD-Image geändert.

## Kurze Ausschnitte: Tiny gegen Base, mit und ohne Namenshinweis

[64 reproduzierbare Dateiprüfungen](whisper-short-window-comparison.json),
[Laborrezept](reproduce_window_comparison.py): dieselben vier synthetischen
positiven Stimmen, die ersten zwei Sekunden dreier ähnlicher Negativtexte sowie
exakte digitale Stille. Je ohne Vorlauf und mit 1,6 Sekunden digitaler Stille,
je Tiny/Base sowie ohne/mit `Nabu.` als Schreibhinweis. Das sind wiederholte
Varianten bekannter Dateien, keine neuen unabhängigen Sprecher und keine
Raum-Abnahme. Die abgeschnittenen Negativtexte sind ausdrücklich nur Präfixe.
Entscheidungsregel unverändert: erste zwei normalisierte Wörter `okay`/`ok` und
exakt `nabu`; acht Sekunden Testtimeout, zwei CPU-Threads, Kontext 256.

| Modell / Hinweis | Positive | Negative ausgelöst | Median / Maximum |
| --- | --- | --- | --- |
| Tiny ohne Hinweis | 0/8 | 0/8 | 0,340 / 1,788 s |
| Tiny mit Nabu | 8/8 | 0/8 | 0,343 / 1,814 s |
| Base ohne Hinweis | 0/8 | 0/8 | 0,614 / 3,147 s |
| Base mit Nabu | 8/8 | 0/8 | 0,624 / 0,719 s |

Ohne Hinweis erscheinen bei den positiven Dateien Schreibweisen wie „Naboo“,
„na bo“, „Nabel“ oder „Nabum“. Das beweist keine Unhörbarkeit: Die strikte
Namensprüfung verwirft diese Ausgaben bewusst. Eine nachträglich erweiterte
Akzeptanzliste wäre eine andere Entscheidung und müsste getrennt gegen neue
Verwechslungsfälle geprüft werden. Digitale Stille erzeugt teils Musikmarker,
aber keine Aktivierung. Das Ergebnis erklärt den früheren Raumfehlstart noch
nicht. Base hat in dieser Dateiprüfung keinen Qualitätsvorsprung gegenüber Tiny.

Base wurde ausschließlich in den temporären Pi-Laborordner geladen. Die
147.951.465 Bytes stimmen mit dem offiziellen Git-LFS-Zeiger überein:
SHA256 `60ed5bc3dd14eea856493d334349b405782ddcaf0028d4b5df4088345fba2efe`.
[Gewichte und Herkunft](https://huggingface.co/ggerganov/whisper.cpp/blob/main/ggml-base.bin).
Dateimessung mit niedriger Prozesspriorität, kein Mikrofon, keine Wiedergabe,
keine Änderung der App oder ihrer Modelle. Laufzeiten enthalten Prozessstart
und Modellladen; kein isolierter Dauer-Inferenzbenchmark. Base bleibt außerhalb
von Kundenpaket und Image. Für eine spätere Aufnahme wären gepinnter Download,
Runtime-/Factory-Pfad und Upgrade-Abnahme weiterhin erforderlich.

### Base im laufenden Raumfenster: weiterhin keine Freigabe

[Raumbericht](acoustic-streaming-base-probe.json), **16.10.2026,
14:28:52–14:31:18 Europe/Berlin**. Gleicher Mac-Studio-Ausgang und dieselben vier
Dateien wie im vorherigen Tiny-Versuch, korrigierter Abschluss offener Prüfungen,
unverändertes Kandidatenfenster und dieselbe strikte Entscheidungsregel:
**1/2 positive Rufe erkannt, 0/2 negative Dateien aktiviert**. Otto bestätigt,
Ben abgelehnt; beide Verwechslungstexte abgelehnt. Fünf native Prüfungen dauerten
0,640–0,768 Sekunden. Beim angenommenen Ruf beträgt der Abstand vom geschätzten
akustischen Beginn bis zur Annahme rund 2,1 Sekunden; das ist kein Live-
Verbindungs- oder Begrüßungswert, weil kein Gespräch gestartet wurde.

Die Vergleichsaufnahmen sind nicht identisch: Schon der primäre Otto-Score
schwankt zwischen den beiden Raumversuchen von 0,594 auf 0,996. Deshalb ist dies
kein kontrollierter Nachweis, dass Base grundsätzlich besser als Tiny wäre.
Der weiterhin verpasste Ben-Ruf erreicht im Primärmodell 0,965; hier verwirft
also die neue Prüfung einen vom bestehenden Modell erkannten Ruf. Eine
produktive Zuschaltung würde damit eine Regression riskieren. **Nicht ausgeliefert.**
Für einen fairen nächsten Vergleich müssten mehrere Prüfer exakt denselben
flüchtigen Kandidatenblock erhalten; die gemessene Rechenlast wäre dann aber
Laborlast, nicht die Latenz eines einzelnen produktiven Prüfers.

Wartung freigegeben, produktives `listening`, frische Audioblöcke (0,37 Sekunden),
Beobachter PID1894368 weiterhin aktiv. Stichprobe 14:31:36: Browser28,13 % eines
Kerns, RSS1308,2 MB, 51,25 °C, keine aktiven Warnungen. Original-Beobachtungsplan
unverändert; dieser Raumtest unterbricht erneut den Ruhezeitnachweis. Keine
Raumaudiodateien oder Raumtranskripte gespeichert. App-Version, Rufwort,
Lautstärke, Mikrofon-/DSP-Konfiguration und Kunden-Image unverändert.

## Gepaarter Vergleich auf identischen Raum-Ausschnitten

**16.10.2026, 15:32:27–15:35:08 Europe/Berlin.**
[Messwerte](acoustic-paired-windows.json),
[Werkzeug](../../../scripts/wake_candidate_comparison.py),
[gezielte Tests](paired-window-tests.txt).

Einmalige Wiedergabe derselben vier bekannten Dateien über den eingebauten
Mac-Studio-Lautsprecher, unveränderte Systemlautstärke und ursprüngliche Rate.
Die App reserviert Wartung atomar; der Test besitzt genau einen Mikrofoneingang.
Zwei Sekunden echter Vorlauf werden nur im RAM gehalten. Der erste Nabu-Score
von mindestens 0,15 nach dem Wiedergabesignal definiert den Kandidaten. Für
beide Modelle werden daraus exakt dieselben Bytes mit zwei Sekunden Rückblick
und entweder 0,8 oder 1,6 Sekunden Nachlauf ausgeschnitten. Fehlender Kontext
wird als fehlend markiert, weder aufgefüllt noch still gekürzt. Alle 16 nativen
Prüfungen waren vollständig, ohne Timeout oder Prozessfehler.

| Prüfer | Nachlauf | Positive erste Kandidaten | Negative erste Kandidaten angenommen |
| --- | --- | --- | --- |
| Tiny | 0,8 s | 0/2 | 0/2 |
| Tiny | 1,6 s | 0/2 | 0/2 |
| Base | 0,8 s | 2/2 | 0/2 |
| Base | 1,6 s | 1/2 | 0/2 |

Die bestehende Nabu-Schwelle 0,85 wurde in beiden positiven Raumdateien nicht
überschritten (Maxima 0,633 und 0,584), aber im ersten Negativtext erreicht
(0,931). Sieben positive Modellframes in diesem Text sind **ein** fehlerhafter
Dateifall, nicht sieben unabhängige Live-Starts. Die App startete kein Gespräch.
Die Signal-Korrelationen von 0,111–0,184 bestätigen keine Verständlichkeit;
ihre geschätzte Position ist keine verlässliche Sprachbeginn-Zeitmarke.

Base mit kurzem Nachlauf benötigt hier 0,603–0,653 Sekunden je Prüfung,
Tiny je nach Fall 0,336–1,852 Sekunden. Gemessen sind native Prozess-/Modellstarts
nach Aufnahme, nicht die Verbindung oder Begrüßung eines Live-Gesprächs.
Die Modelle wurden sequenziell geprüft, nicht parallel. Der größere Nachlauf
verbessert die Erkennung nicht monoton: Bei identischem Anfang wird Ottos Ruf
in Base damit verworfen. Dieses Ergebnis stützt **keine** pauschale Verlängerung
und keine nachträglich geänderte Akzeptanzregel. Alle Prüfer benutzen weiterhin
den Namenshinweis `Nabu.` und dieselbe strikte Wortprüfung.

**Grenzen und nächste Entscheidung:** Dies sind bekannte TTS-Stimmen und nur
der erste Kandidat je Datei. Spätere Kandidaten desselben Negativtexts, neue
Sprecher, natürliche Erst-Rufe und acht Stunden negative Umgebung sind damit
nicht geprüft. Base hatte im vorherigen Streaming-Raumtest zudem einen
positiven Ruf verworfen. Deshalb weiterhin keine Produktionsintegration.
Vor einem Kandidatenentscheid sind unabhängige Stimmen und die vollständige
laufende Kandidatenfolge mit eingefrorenen Parametern zu prüfen. Bestehende
Fehlversuche bleiben Teil der Auswertung; ein guter kleiner Ausschnitt ersetzt
sie nicht.

Validierung: drei neue Auswahl-/Grenztests und zwölf vorhandene Verifier-/Prozess-
Tests bestanden. Die neue Auswahlprüfung bestätigt identische Bytes für beide
Modelle und verweigert fehlenden Kontext. Kein vollständiger App-Gesamtlauf
für diese isolierte Laborerweiterung behauptet. Testdateien sind bekannte
synthetische Eingaben; Raum-PCM und Raumtranskripte wurden nicht gespeichert.

Wartung bestätigt freigegeben. Beobachter PID1894368 läuft weiter; Stichprobe
15:36:06: App 0.5.60, `idle`, `listening`, Browser 28,26 % eines Kerns,
RSS 1310,41 MB, 52,9 °C, keine aktiven Warnungen. Dieser angekündigte Raumtest
unterbricht erneut den Ruhezeitnachweis; ursprünglicher Plan bleibt erhalten.
Alle Änderungen liegen unter Labor-Skripten, Tests und Dokumentation, außerhalb
der App-/Image-Positivliste. Keine neue Abhängigkeit, keine produktive Änderung,
kein neues Image. Die Dateien werden separat zur Prüfung gepusht.

Reproduktion unter bestehender Testfreigabe: `check_wake_acoustic.py` mit
`--phrase okay-nabu --external-playback --signal-diagnostics --quiet-seconds 30`,
vorhandenem `--whisper-binary`, Tiny als `--whisper-model` und Base als
`--compare-whisper-model`; `--clips` enthält die vier anhand der Bericht-Hashes
identifizierten synthetischen Dateien. Ein externer Controller spielt jede
Datei erst nach `play_clip` mit Originalrate ab und protokolliert ihren Exit.
Ohne externe Wiedergabe gelten diese Messwerte nicht als reproduziert. Der
Bericht enthält die Modell-/Binary-Hashes und die tatsächlichen Wiedergaben.

## Unabhängiger Streaming-Dateitest: erster Ruf bleibt kritisch

Vor Erzeugung der neuen Charlie-/HL-Dateien wurden Parameter und Abnahme in
[independent-stream-plan.json](independent-stream-plan.json) eingefroren. Der
native Base-Prüfer verarbeitete sechs vollständige Echtzeit-Dateiströme auf dem
Pi (16.10., 15:43:14–15:44:38). Kein Mikrofon, Lautsprecher oder Cloud-Gespräch;
der ursprüngliche Beobachterplan blieb unverändert. Die CPU-Testlast zählt
nicht als unbeeinflusste Ruhezeit.

**4/6 Szenarien bestanden:** HL wurde einzeln und vor der Wiederholung erkannt,
beide Negativdateien lösten nicht aus. Charlie scheiterte einzeln und in der
Doppelnennung am ersten Ruf; erst die identische Wiederholung wurde angenommen.
Der primäre Nabu-Wert erreichte dabei 0,996. Alle Prüfer wurden geschlossen,
kein offenes Ergebnis blieb übrig. [Vollständiger Bericht](independent-stream-result.json)
und [Dateihashes](independent-fixtures.json). Keine Ersetzung fehlgeschlagener
Dateien und keine nachträgliche Lockerung dieses Prüfstands.

Eine getrennte Diagnose ausschließlich der bekannten synthetischen Charlie-Datei
zeigt die Ursache **dieses Laborfalls**: Base liefert beim ersten Kandidaten
`Oknabu.`, beim zweiten `Ok Nabu.`. Die bisherige Prüfung verlangt zwei Wörter
und verwirft daher die erste Schreibweise. Beide nativen Aufrufe brauchten rund
0,65 Sekunden. [Diagnose mit Fensterhashes](independent-synthetic-diagnosis.json).
Dies erklärt nicht automatisch die zuvor vom Benutzer erlebten Produktionsfehler;
produktiv arbeitet weiterhin das direkte microWakeWord-Modell, ohne Base-Prüfer.

Eine eng begrenzte Behandlung zusammengezogener Schreibweisen ist eine nächste
Laborhypothese. Die sechs Fälle sind nach dieser Diagnose bekannte Regressionen,
keine unabhängige Abnahme einer darauf angepassten Variante. Neue Teststimmen und
Negativbeispiele müssen getrennt ausgewertet werden. Bis dahin keine Integration.

Image-/Update-Einfluss: ausschließlich nicht ausgelieferte Laborskripte,
synthetische Metadaten und Dokumentation; keine Runtime- oder Profiländerung.
Der separat autorisierte Mobile-Fernbedienungstest hat inzwischen App 0.5.61
installiert, mit unveränderter produktiver Nabu-Konfiguration. Der Beobachter
PID1894368 wurde am 16.10. um 15:57 erneut als tatsächlicher Prozess bestätigt;
keine Warnung, Browser 27,66 % eines Kerns und RSS 1320,17 MB. Kein Langzeitabschluss.
