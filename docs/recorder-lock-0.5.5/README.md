# Recorder exklusiv während Aufnahme — Studio 0.5.5

Aufnahme-Widget nur im Recorder. Bibliothek, ausgewählte Bibliotheksinhalte und Einstellungen nutzen die gesamte Breite rechts von der Navigation.

Während einer Aufnahme: Bibliothek/Einstellungen, Mikrofonzugang, Meetingaktionen, Transkript-/Zusammenfassungstabs, Wiedergabe und Regler gesperrt. Notizen, Tastatur und Stoppen bleiben verfügbar. Queue darf angezeigt werden; ihre Öffnen-/Wiederholen-Aktionen sind gesperrt. Bereits laufende Verarbeitung geht weiter. Nach Stoppen sind Navigation und Ansichten wieder frei. Neue Aufnahme während Verarbeitung weiterhin möglich.

Auch Python sperrt Änderungen während Aufnahme: Nur `/api/record/stop` und Speichern ausschließlich des Feldes `notes` der laufenden Aufnahme erlaubt. Andere Meetingtexte, Titel, Prompts, Standardbereich, CDB-Anmeldung/-Versand, Einstellungen, Modellaktionen, Wiederholung und Löschen sind gesperrt. Vor Start werden noch offene Textänderungen gespeichert. Vorhandene lokale Entwürfe bleiben geschützt.

## Prüfung am 12. Oktober 2026

- Separater Dienst auf dem tatsächlichen Pi 5 mit künstlicher Audioquelle und Testprozessor, eigene Datenbank; keine Kundenaufnahmen/CDB-Uploads für diesen UI-Test.
- 1280 × 720: Bibliothek und Einstellungen ohne Capture-Widget; Einstellungen und Footer jeweils 1192 px breit, Navigation 88 px. Kein impliziter leerer Gridbereich.
- Aufnahme gestartet: Navigation, Tabs, Mikrofon, Meetingaktionen und Wiedergaberegler sichtbar deaktiviert. Aktuelle Notiz gespeichert und nach Stoppen erhalten.
- Nach Stoppen Einstellungen wieder erreichbar, während Hintergrundverarbeitung läuft.
- Weitere Aufnahme gestartet, während vorherige Aufnahme verarbeitet wird. Queue zeigt Aufnahme + laufende Zusammenfassung + wartenden Auftrag; Öffnen gesperrt. Nach Stoppen sind Queue-Aktionen wieder verfügbar.
- 55 Python-Tests auf dem Pi bestanden, einschließlich erweiterter HTTP-Prüfung der Aufnahmesperre für aktuelle Notizen, fremde Notizen, Titel, Einstellungen, Standardbereich, Logout, Prompts, Retry und Delete.
- 11 JavaScript-Tests bestanden, einschließlich Navigationssperre während Aufnahme.
- Kein Test der physischen Fingerbedienung oder Mikrofonqualität; Modellqualität siehe vorherigen CDB-Gesamttest.

## Screenshots

01/02: volle Bibliotheks-/Einstellungsfläche im isolierten Testbetrieb.
03: Aufnahme mit gesperrten Bereichen und gespeicherter Notiz.
04: Einstellungen nach Stoppen während Verarbeitung wieder zugänglich.
05: Queue verarbeitet weiter bei neuer Aufnahme.
06: produktive Recorder-Startansicht nach Deployment.

Produktiv auf dem Pi installiert: vier Anwendungsdateien per SHA256 identisch mit dem lokalen Stand, API-Version 0.5.5, 22 Meetings unverändert, bestehender Standardbereich erhalten. Python-Dienst und Kiosk neu gestartet. Rückkehrstand: `/home/chris/backups/recorder-before-0.5.5`. Screenshot 07 zeigt die produktiven Einstellungen ohne Aufnahme-Widget.
