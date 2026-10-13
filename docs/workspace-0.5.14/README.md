# Recorder und Bibliothek – 0.5.14

## Änderungen

- Bibliothek und Queue: 80-px-Fußleiste plus separater 28-px-Abschluss, entsprechend Einstellungen. Der bisherige zusätzliche Innenabstand innerhalb der farbigen Leiste entfällt.
- Aufnahmedetail und laufende Aufnahme: eigene feste Fußleiste, gemeinsame Seitenwahl und Textaktionen. Die Speicheranzeige beansprucht unten 28 px. Lange Texte ändern die Leistenposition nicht.
- Zusammenfassungsvorlage oberhalb des Textes, nur im entsprechenden Tab sichtbar. Neu zusammenfassen und Exportieren jeweils 208 × 56 px. Gleiche Breiten für Inhaltstabs und Rückweg zur Bibliotheksliste.
- Recorder: Mikrofoneinstellungen in einer festen unteren Leiste mit 208 × 56 px. Aufnahme/Stopp behält seine große runde Touchfläche; bei Bildschirmtastatur bleibt Stoppen erreichbar.
- Fehler-/Entwurfaktionen erscheinen oberhalb der Fußleiste und verschieben deren Position nicht.

## Validierung

78 Python- und 37 JavaScript-Tests bestanden. JavaScript-Syntax und Git-Diff geprüft. Browserprüfung bei 1280 × 720, in Graphit und Blau/Hell, auf isolierter Pi-Vorschau mit eigener Bibliothek. Gemessene Fußleisten: y=612, Höhe=80, Abschluss y=692–720; bei Tastatur y=392, Abschluss bis y=500. Siehe `measurements.json`.

Geprüft: synthetische Aufnahme starten/stoppen (94 Sekunden), gesperrte Navigation währenddessen, Notizen schreiben und speichern, 30 Textzeilen bis zur letzten Seite erreichen, Bildschirmtastatur, Navigation danach freigegeben, Zusammenfassungstab, Bibliotheksseitenwechsel und Suche, Queue. Der Testverarbeiter liefert feste Beispieltexte; dies ist ein UI-/Aufnahmetest, keine Modellqualitätsprüfung und keine Brain-Übertragung. Ein erster Vorschau-Audiogenerator lieferte keine Audiodaten; für den erfolgreichen Test wurde der bereits in den Funktionstests verwendete PCM-Generator genutzt. Der Fehlereintrag ist ausschließlich in der isolierten Vorschau und dient im Queue-Screenshot als Fehlerzustand.

## Screenshots

- [Aufnahme](01-recording.png), [Tastatur](02-keyboard.png)
- [Recorder Notizen](03-recorder-notes.png), [Recorder Zusammenfassung](04-recorder-summary.png)
- [Bibliotheksliste hell](05-library-light.png), [Seite 2](06-library-page2.png)
- [Aufnahmedetail hell](07-detail-light.png), [Queue](08-queue.png)
