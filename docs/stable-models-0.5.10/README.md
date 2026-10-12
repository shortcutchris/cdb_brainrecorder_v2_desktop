# Recorder 0.5.10 – konsistente Modellprüfung und Touchansichten

Geprüft am 12.10.2026 auf dem Raspberry Pi, Weboberfläche im Browser mit 1280 × 720 Pixeln. Die nummerierten Screenshots zeigen die isolierte Pi-Testinstanz mit künstlichen Daten. Produktionsnachweise werden separat ergänzt.

## Behobene Ursachen

- Der frühere technische Whisper-Test war in der isolierten Testablage erfolgreich; im produktiven `model-validations.json` fehlte der Nachweis. Nachweise werden nur bei exakt identischer Modell- **und** Laufzeitkennung übernommen. Ungeprüfte Modelle erhalten keinen grünen Status.
- Erfolgreiche Einzeltests werden pro Verarbeitung, Anbieter, Modell und Brain-Kontobindung dauerhaft gespeichert. Ein späterer Test verdrängt ältere Ergebnisse nicht. Lokale Ergebnisvorschauen werden bei geänderter Modell-/Laufzeitkennung verworfen; Aktivierung bleibt durch den aktuellen Katalognachweis geschützt.
- Aktives Modell und Prüfauswahl bleiben getrennt. „Aktiv · Gerätetest bestanden“ bedeutet technische Funktionsfähigkeit, keine Garantie für fehlerfreie Erkennung.
- Modellseiten reservieren Platz für Auswahl, Status, Ergebnis und Aktionen. Keine aufklappenden Testergebnisse mehr. Lange Ergebnisse und Fehlermeldungen haben Seiten.
- Einheitlicher 80-Pixel-Header, 24-Pixel-Seitenabstand, 220-Pixel-Zurückfläche und 56-Pixel-Bedienelemente bei der Zielauflösung. Fußleisten behalten ihre Höhe; Statuszeilen und Audio-Rückmeldung erhalten feste Bereiche.
- Bibliothek und Warteschlange haben vollständige Listenseiten statt angeschnittener, per Pfeil verschobener Zeilen. Auswahlfenster besitzen dieselbe Suche und direkt anwählbare Seitennummern. Textbereiche verwenden ebenfalls Seitennummern.
- Die Bildschirmtastatur adressiert das oberste Auswahlfenster und schließt mit diesem zuverlässig. Der Picker reduziert seine Einträge pro Seite auf den verfügbaren Platz.

## Audit und Nachprüfung

| Schritt | Ansicht / Screenshot | Ergebnis |
|---|---|---|
| 1 | [Einstellungen](01-settings.png) | Übersicht klar, gemeinsamer Header; letzte Detailkorrekturen vereinheitlichen zusätzlich Zurückbreite und Inhaltsabstand. |
| 2 | [Audio](02-audio.png) | Aktionen in fester Fußleiste; keine Überläufe. Testinstanz verwendet synthetische Quelle, keinen Mikrofontest. |
| 3 | [Brain-Konto](03-brain.png) | Umgebung bleibt als Kontext sichtbar und ist bei Anmeldung gesperrt. Fester Platz für Konto-/Zielstatus. |
| 4 | [Übertragungen](04-transfers.png) | Rückweg zum Konto; keine Übertragung ausgelöst. |
| 5 | [Vorlagen](05-prompts.png) | Direkte Textseiten, gleiche Eingabehöhen; Fußleistenhöhe anschließend auf 80 Pixel vereinheitlicht. |
| 6 | [Design](06-design.png) und [Editor](07-theme-editor.png) | Vorschau/Abbruch geprüft; Änderungen nicht gespeichert. |
| 7 | [Diagnose](08-diagnostics.png) | Erweiterter Bereich geprüft; reservierte Rückmeldung. Kein Programmpfad geändert. |
| 8 | [Bibliothek](09-library.png), [Seite 4](20-library-page4.png) | 16 künstliche Einträge; direkte letzte Seite, Suche setzt korrekt auf Seite 1 zurück. |
| 9 | [Aufnahmedetail](10-meeting.png) | Gleiche obere Grundlinie, klarer Rückweg, Textseiten. |
| 10 | [Meetingaktionen](11-meeting-actions.png), [Übertragung](12-transfer-dialog.png) | Sekundäre Dialoge mit festen Kopf-/Fußbereichen. Kein Versand oder Löschen. |
| 11 | [Auswahl vorher](13-picker-before.png), [Auswahl nachher](19-picker.png) | Pfeile durch Seitennummern ersetzt; Filter und Seitenwechsel getestet. |
| 12 | [Tastatur](21-picker-keyboard.png) | Toucheingabe im Picker funktioniert; Schließen entfernt auch Tastatur. |
| 13 | [Recorder bereit](15-recorder.png), [Aufnahme](22-recording.png) | Große Aufnahmetaste; Bibliothek/Einstellungen/Queue gesperrt während Aufnahme, nach Stop wieder bedienbar. |
| 14 | [Queue leer](14-queue.png), [Verarbeitung](23-queue-working.png) | Reale synthetische Aufnahme in Queue, Aktivitätsanzeige und feste Fußleiste. |
| 15 | [Whisper](16-whisper-passed.png), [Brain-Auswahl](17-brain-model.png), [Zusammenfassung](18-summary.png) | Aktiv-/Teststatus korrekt; lokaler/Brain-Wechsel verändert keine Position von Modellkopf, Auswahl, Ergebnis oder Aktionen. |

Einige Auditbilder dokumentieren den Zwischenstand vor den letzten gemeinsamen Abstandsregeln; `production-*` zeigt den ausgelieferten Stand. `geometry.json` enthält die während der Prüfung gemessenen Bereiche.

## Tests und Grenzen

- 78 Python-Tests auf dem Pi, 29 JavaScript-Tests lokal.
- Neuer Regressionstest: erfolgreiche Prüfungen überleben andere Tests und Neustart; Brain-Aktivierung bleibt kontogebunden.
- UI-Regressionen: Auswahl ist nicht Aktivierung; geänderte Fingerprints verlieren alte Ergebnisvorschauen; Ergebnisbereich bleibt sichtbar.
- Erneuter echter Whisper-medium-Test: **116,3 s** für das künstliche Beispiel. Ergebnis: „Anerstellt, bis Donnerstag eine Aufgabenliste. Die Kosten sind noch ungeklärt.“ Der Name wurde falsch erkannt.
- Erneuter echter Qwen3-4B-Instruct-Test: **24,1 s**. Genannte Aufgabe und offener Kostenpunkt korrekt, ohne weitere Aufgabe.
- Nach Qwen-Test bleibt das Whisper-Ergebnis sichtbar. Modell-/Laufzeitidentitäten stimmen mit den produktiven Dateien überein.
- Keine neuen Brain-Uploads und keine produktiven Meetings verändert. Kein neuer Stundentest in diesem UI-Audit. Die Aufnahme zum Prüfen der Aufnahmesperren enthält nur synthetisches Audio.
- Die Prüfung ist keine vollständige WCAG-Zertifizierung und ersetzt keinen Finger-Test am physischen Touchdisplay. Schwerpunkt: Zielauflösung, Bedienbarkeit, dynamische Zustände, Navigation und sichtbare Überläufe.
