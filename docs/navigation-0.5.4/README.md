# Recorder-Navigation 0.5.4

## Verhalten

- Recorder ohne laufende Aufnahme: Bereitschaftsansicht mit Standardbereich; keine automatische Auswahl eines früheren Meetings.
- Recorder während einer Aufnahme: aktuelle Aufnahme und Notizen. Die Bibliotheksauswahl bleibt separat erhalten.
- Neue Aufnahme aus Bibliothek oder Einstellungen: Recorder zeigt automatisch die neue Aufnahme.
- Stoppen (auch aus Einstellungen): gerade beendete Aufnahme bleibt zur Kontrolle sichtbar. Hintergrundverarbeitung und Start einer weiteren Aufnahme bleiben möglich.
- Nach dem Wechsel zu Einstellungen/Bibliothek führt Recorder ohne aktive Aufnahme wieder zur Bereitschaftsansicht.
- Bibliothek merkt sich Aufnahme und Texttab innerhalb der geöffneten App. „Alle Aufnahmen“ öffnet die Liste; nach Browser-Neustart beginnt die App auf Recorder.
- Schließen von Bibliothek/Einstellungen führt zurück zu Recorder. Notizen werden vor dem Wechsel gespeichert; die vorhandene lokale Entwurfswiederherstellung bleibt bestehen.

## Verifiziert am 12. Oktober 2026

Auf Raspberry Pi 5, 16 GB, Browser bei 1280 × 720:

1. Isolierte Testinstanz mit künstlicher Audioquelle und Testprozessor; keine persönlichen Aufnahmen und kein CDB-Upload für diesen Navigationstest.
2. Bibliothek → Produktplanung Q4 → Zusammenfassung → Recorder: Bereitschaftsansicht. Zurück zur Bibliothek: gleiche Aufnahme und gleicher Tab.
3. Neue Aufnahme aus Bibliothek: automatisch aktuelle Notizen im Recorder. Notiz eingegeben, zu Bibliothek und Einstellungen gewechselt, zu Recorder zurück: Notiz erhalten, Aufnahme und Timer laufen weiter.
4. Mikrofonwahl/-test und Einrichtung während Aufnahme gesperrt; große Stopptaste erreichbar.
5. Aufnahme direkt aus Einstellungen beendet: automatisch gerade beendete Aufnahme mit gespeicherter Notiz sichtbar, Hintergrundverarbeitung gestartet.
6. Einstellungen geöffnet/geschlossen: Bereitschaftsansicht, Verarbeitung läuft weiter. „Alle Aufnahmen“ öffnet die Liste korrekt.
7. 55 Python-Tests auf dem Pi bestanden; zehn JavaScript-Tests bestanden, davon vier neue Navigationstests.
8. Produktive Instanz erst bei leerer Queue und ohne Aufnahme aktualisiert. Backup der vier Deploymentdateien unter `/home/chris/backups/recorder-before-0.5.4`.
9. Python-Dienst und Kiosk neu gestartet; API meldet 0.5.4. Die vier produktiven Dateien stimmen per SHA256 mit dem lokalen Stand überein. 22 produktive Meetings unverändert. Standardbereich Staging Playground erhalten.

Die Screenshots 01–06 stammen aus dem isolierten Testbetrieb auf dem Pi mit künstlichen Daten. Screenshot 07 zeigt die produktive Startansicht nach Deployment. Kein physischer Touch-/Mikrofontest durchgeführt. Modellqualität und CDB-End-to-End-Verarbeitung sind im vorherigen [CDB-Gesamttest](../cdb-live-0.5.3/README.md) dokumentiert.

## Screenshots

- [Bereitschaft im Testbetrieb](01-ready.jpg)
- [Bibliotheksdetail](02-library-detail.jpg)
- [Neue Aufnahme](03-recording.jpg)
- [Bibliothek während Aufnahme](04-library-recording.jpg)
- [Einstellungen während Aufnahme](05-settings-recording.jpg)
- [Gerade beendete Aufnahme](06-after-stop.jpg)
- [Produktive Startansicht](07-production-ready.jpg)
