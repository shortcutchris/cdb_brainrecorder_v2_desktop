# Live-Test Studio 0.5.1 – lokal und CDB

12.10.2026, produktiver Raspberry Pi 5 mit 16 GB, Studio 0.5.1 (`00a82cf`), gemeinsame Engine 0.2.6. Beide Durchläufe einschließlich echter Übertragung nach `staging_playground` erfolgreich.

## Testquelle und Ablauf

24,4116 Sekunden künstliche deutsche Sprache, mit espeak-ng erzeugt und als WAV mit 16 kHz/Mono importiert. Keine Kundendaten. Kein Test des angeschlossenen Mikrofons oder einer tatsächlichen Raumaufnahme.

Erwarteter Inhalt:

> Dies ist eine künstliche Testaufnahme für den Recorder. Es sind keine Kundendaten enthalten. Frau Meier erstellt bis Mittwoch die Checkliste. Herr Fischer prüft am Donnerstag das Mikrofon. Das Testbudget beträgt vierhundert Euro. Eine Bestellung ist noch nicht freigegeben. Der nächste Test findet am Freitag um elf Uhr statt.

SHA256 der Quelle und beider gespeicherten Job-Audiodateien identisch: `76cc416b4fc635c5b5d9bfda2fc769c56b7c061df1047bf2efd4990617a6ef37`.

Sitzung 31 wurde mit lokal/lokal eingereiht, Sitzung 32 unmittelbar dahinter mit CDB/CDB. Die ursprünglichen globalen Einstellungen lokal/lokal wurden direkt nach dem Einreihen wiederhergestellt. Beide Aufträge behielten ihren eigenen Provider-Snapshot. Die dauerhafte FIFO zeigte den lokalen Auftrag in Verarbeitung und den CDB-Auftrag wartend; der CDB-Auftrag startete anschließend. Für CDB-ASR konvertiert der Adapter eine Uploadkopie nach Opus; das ursprüngliche WAV bleibt erhalten.

## Gemessene Zeiten

| Verarbeitung | Lokal auf Pi | Über CDB |
| --- | ---: | ---: |
| Transkription | 119,92 s | 6,99 s |
| Zusammenfassung | 42,40 s | 6,80 s |
| Verarbeitungsversuch gesamt | 162,34 s | 13,87 s |
| ASR / Audiodauer | 4,912 | 0,286 |

Die Zeiten schließen die Wartezeit in der FIFO aus. CDB-ASR beinhaltet Uploadkonvertierung, Netzwerk und Statusabfrage; der Server meldet etwa 4,76 Sekunden zwischen Jobanlage und Abschluss. Dies ist ein einzelner kurzer Funktionstest, kein Stundenbenchmark und keine belastbare Hochrechnung für lange Meetings.

Lokale Modelle: Whisper medium (`ggml-medium.bin`) und `qwen3:4b-instruct`. ASR-Spitzen-RSS 2072,5 MiB, aggregierte Ollama-Spitzen-RSS 3410,1 MiB; diese Spitzen müssen nicht gleichzeitig auftreten. Mindestens 11670,2 MiB verfügbarer Systemspeicher während des lokalen Versuchs. CDB-Endpunkte: `transcription-jobs` und `agent-structure-text`. Der konkrete serverseitige Modellname wurde nicht zurückgeliefert und ist damit nicht verifiziert.

## Qualität in dieser Probe

Lokal wurden Aufgaben, Wochentage, Budget 400 Euro, fehlende Bestellfreigabe und Folgetermin Freitag 11 Uhr erkannt. Drei Abweichungen: „Recorder“ → „E-Code“, „Checkliste“ → „Heckliste“, „Meier“ → „Meyer“. Die lokale Zusammenfassung übernimmt „Heckliste“ und „Meyer“ aus dem Transkript.

CDB erkennt den erwarteten Inhalt dieser Probe korrekt, einschließlich Recorder, Checkliste und Meier. Die Zusammenfassung enthält Aufgaben, Budget, offene Bestellung und Termin und kennzeichnet fehlende Angaben zu Kalenderwoche, Freigabeverantwortung und Ort. Daraus folgt keine allgemeine Qualitätsgarantie für reale Meetings, Dialekt, Störgeräusche oder mehrere Sprecher.

## Übertragung und bestätigte Verarbeitung

Beide Sendungen wurden im echten Browser über „Ins Brain übertragen“ und jeweils einmal „Jetzt übertragen“ ausgelöst. Der gespeicherte Standard „Staging Playground“ war vorausgewählt und wurde nicht geändert. Übertragen wurden synthetische Notizen, Transkript und Zusammenfassung als Text; dieser Text-Ingest archiviert beziehungsweise verknüpft nicht die Originalaufnahme.

| Lauf | Dokument-ID | CDB-Ingest-Job | Serververarbeitung |
| --- | --- | --- | ---: |
| Lokal, Sitzung 31 | `0956f904-13dc-42a6-b82e-6605229b0ca4` | `1be185ad-ef6d-44ce-b3f9-5056e1268179` | 17,32 s |
| CDB, Sitzung 32 | `99ca7c24-23e3-49ec-be2a-9875c332cc0e` | `ea9471a1-73d5-46d3-9042-9ad85203398b` | 10,70 s |

Lokaler Publikationsstatus und abgefragter Serverstatus jeweils `completed`; Dokument-/Job-IDs stimmen mit der Annahmequittung überein. Alle sechs Schritte bestätigt: Markdown-Konvertierung, Bereinigung, Chunking, Graphgenerierung, Knowledge Graph und Vektorisierung. Beide kurzen Dokumente melden lediglich „Very few chunks created - document may be short“. Die Serverzeiten betreffen nur den Ingest und sind kein End-to-End-Wert inklusive manueller Bedienzeit.

CDB-ASR separat bestätigt: Aufnahme `41e901a4-c67d-43ea-b959-d64a2d392a67`, Job `28304ccd-fecc-46c0-b190-a00402ed9da9`, Status `completed`, Fortschritt `done` / 100 %, kein Fehler.

## Oberfläche und Abschlusszustand

- Versand während laufender Verarbeitung gesperrt; nach Abschluss verfügbar.
- Während Versand waren Ziel und Sendetaste gesperrt.
- Aufnahmetaste blieb während Hintergrundverarbeitung verfügbar. Eine echte parallele Mikrofonaufnahme wurde in dieser Probe nicht gestartet.
- Standardbereich und Microsoft-Sitzung blieben erhalten; globale Provider weiterhin lokal/lokal.
- Nach Abschluss Queue leer, keine laufende Aufnahme; zwei neue synthetische Sitzungen, insgesamt 21 Sitzungen.

Browsernachweise vom produktiven Pi über den lokalen Tunnel, Browserfenster 1024 × 880; keine Behauptung eines physischen Touchtests:

1. [FIFO: lokal aktiv, CDB wartet](evidence-0.5.1/01-queue.png)
2. [Versand während Verarbeitung gesperrt](evidence-0.5.1/02-versand-gesperrt.png)
3. [Standardbereich im Versanddialog](evidence-0.5.1/03-standard-versand.png)
4. [CDB-Ergebnis im Brain verarbeitet](evidence-0.5.1/04-cdb-im-brain.png)
5. [Lokales Ergebnis im Brain verarbeitet](evidence-0.5.1/05-lokal-im-brain.png)

Keine Anwendungscodeänderung für diesen Test erforderlich. Deshalb kein erneuter Dienstneustart oder Deployment. Der Bericht ergänzt die zuvor bestandenen 53 Python- und 6 JavaScript-Tests; diese wurden für die reine Dokumentationsänderung nicht erneut ausgeführt.
