# CDB-Gesamttest auf dem Pi — 12. Oktober 2026

Studio 0.5.3, produktiver Code `4cba2dd`, Engine 0.2.6. Tatsächlicher Raspberry Pi 5 mit 16 GB; Oberfläche bei 1280 × 720 geprüft. Separater Testdienst auf Loopback 8089, eigene Datenbank und synthetische PCM-Aufnahmequelle. Die Verarbeitung lief über echte CDB-Endpunkte auf staging.cdbos.de. Keine Kundenaufnahmen verwendet; keine Änderung an produktiven Einstellungen oder Meetings. Der Test belegt weder die physische Mikrofonqualität noch die Bedienung mit einem Finger am Display.

## Geprüfter Ablauf

1. Aufnahme A über die große Aufnahmetaste starten: neue Aufnahme wird automatisch mit Notizen ausgewählt.
2. Während der Aufnahme Recorder, Bibliothek und Einstellungen wechseln; alte Referenz öffnen; Recorder kehrt zur laufenden Aufnahme zurück. Stopptaste bleibt erreichbar, Timer läuft weiter, Notizen bleiben erhalten.
3. Mikrofonwahl/-test und Modell-/Providerwechsel sowie Installation/Aktivierung sind während der Aufnahme gesperrt. Übertragung einer laufenden Aufnahme ist gesperrt.
4. A stoppen und sofort B aufnehmen. A transkribiert bei CDB, während B weiter aufnimmt; Warteschlange zeigt beide Zustände. B nach A ebenfalls vollständig verarbeitet.
5. Meetingprotokoll und Vorlage „Aufgaben & nächste Schritte“ mit CDB prüfen. Erkannten Wortfehler im Transkript manuell korrigieren und Aufgaben erneut mit CDB erzeugen.
6. A einmal in den voreingestellten Standardbereich **Staging Playground / staging_playground** übertragen. Receipt und Serverstatus stimmen bei Dokument-/Job-ID überein. Alle sechs Verarbeitungsfelder abgeschlossen: Markdown-Konvertierung, Bereinigung, Chunking, Graph Generation, Knowledge Graph, Vektorisierung. UI zeigt „Im Brain verarbeitet“.

## Zeiten

| Aufnahme | Audiodauer | CDB-Transkription | Erste CDB-Zusammenfassung | Verarbeitung gesamt |
| --- | ---: | ---: | ---: | ---: |
| A | 31,073 s | 7,21 s | 9,69 s | 16,93 s |
| B | 37,573 s | 7,04 s | 8,85 s | 15,90 s |

Die eigentliche synthetische Sprachquelle mit Randstille ist 27,773 s lang; danach liefert die Aufnahmequelle Stille bis zum Stoppen. Die zweite Aufgabenfassung nach manueller Korrektur benötigte 10,67 s. Die abschließende Brain-Verarbeitung dauerte serverseitig ca. 15,49 s. Das sind kurze synthetische Funktionstests, keine belastbare Hochrechnung für eine Stunde oder natürliche Raumaufnahmen. CDB liefert hier die Backend-Bezeichnungen `cdb/transcription-jobs` und `cdb/agent-structure-text`; die konkrete serverinterne Modellversion ist daraus nicht ersichtlich.

## Qualität — bewusst kein uneingeschränktes ASR-Pass

Soll: „Frau Meier **erstellt** bis Mittwoch die **Checkliste**.“

CDB bei A und B: „Frau Meier **stellt** bis Mittwoch die **Chatliste**.“ Die übrigen wesentlichen Angaben wurden richtig erkannt: Herr Fischer, Donnerstag, 400 Euro, fehlende Bestellfreigabe, Freitag 11 Uhr und unbeschlossener Vorschlag. Die Zusammenfassung übernahm den erkannten Wortfehler. Originale sind in `first-passes.json` und Screenshots 06/07 dokumentiert.

Die Aufgabenlogik war bereits vor der Korrektur sinnvoll: zwei ausdrücklich zugewiesene Aufgaben, Termin separat; Budget ist keine Aufgabe, fehlende Freigabe und unbeschlossener Mikrofonvorschlag bleiben offene Punkte. **Vor dem Versand wurde ausschließlich der bekannte Wortfehler manuell korrigiert und die Aufgabenfassung erneut erzeugt.** Das veröffentlichte Ergebnis ist somit geprüft/korrigiert und nicht das unveränderte automatische ASR-Ergebnis.

## Nachweise

- [Aufnahme](01-recorder-recording.jpg)
- [Bibliothek während Aufnahme](02-library-recording.jpg)
- [Gesperrte Audioeinstellungen während Aufnahme](03-settings-recording.jpg)
- [Gesperrter Versand während Aufnahme](04-transfer-locked.jpg)
- [CDB-Verarbeitung A parallel zu Aufnahme B](05-processing-and-recording.jpg)
- [Unkorrigiertes Transkript](06-asr-original.jpg)
- [Aufgaben aus unkorrigiertem Transkript](07-tasks-original.jpg)
- [CDB-Aufgaben nach manueller Transkriptkorrektur](08-tasks-reviewed.jpg)
- [Voreingestelltes Versandziel](09-standard-destination.jpg)
- [Verarbeitung abgeschlossen](10-brain-completed.jpg)
- [Erste Ergebnisse und Messwerte](first-passes.json)
- [Geprüftes Ergebnis](reviewed-result.json)
- [Empfangsbeleg und CDB-Serverstatus](publication-evidence.json)

Temporärer Testdienst wird nach Abschluss beendet und seine kopierte Microsoft-Sitzung entfernt. Produktion bleibt bei ihren vorherigen lokalen Verarbeitungsprofilen und bestehendem Standardbereich. Kein Anwendungscode geändert; kein Deployment oder Versionswechsel erforderlich.
