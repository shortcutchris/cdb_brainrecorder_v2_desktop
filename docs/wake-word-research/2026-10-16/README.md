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
Die gemessene CPU-Zeit umfasst Modellneuanlage und aufgefüllte Stille;
es ist kein gemessener Dauerverbrauch. Trefferframes sind keine Anzahl
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
280,013 Sekunden Testaudio einschließlich Vor-/Nachstille und frischer Modelle.
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
