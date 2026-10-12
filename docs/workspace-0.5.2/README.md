# Studio 0.5.2 – Arbeitsansichten und sinnvolle Aufgaben

Bibliothek und Einstellungen teilen sich als nichtmodale Ansichten die rechte Arbeitsspalte mit dem Meetinginhalt. Die große Aufnahme-/Stopptaste, Navigation und Queue bleiben erreichbar. Schließen oder „Recorder“ führt zum Meeting zurück; Auswahl in der Bibliothek öffnet das gewählte Meeting. Auswahl- und Bestätigungsdialoge bleiben für einzelne Aktionen bestehen.

Letzte Aufnahmen besitzen Platz für drei Titelzeilen und Datum. Längere Titel enden mit Auslassung; der volle Titel steht im Meeting. Auch dessen Überschrift ist auf zwei Zeilen begrenzt, damit die Inhaltsfläche erhalten bleibt.

Textaktionen erscheinen nur unter Zusammenfassung. Die Standardauswahl umfasst „Meetingprotokoll“ und „Aufgaben & nächste Schritte“; allgemeines Übersetzen und Umformatieren entfallen. Eigene gespeicherte Prompts bleiben erhalten. Bei automatischer Zusammenfassung verwenden lokale und CDB-Verarbeitung denselben neuen Meetingauftrag. Bereits gespeicherte Ergebnisse werden nicht automatisch neu berechnet.

Aufgaben erfordern eine belegte Handlung mit erkennbarem Ziel. Zuständigkeit und Termin werden nur aus dem Text übernommen; fehlende Angaben bleiben als „nicht genannt“ erkennbar. Wochentage werden nicht in erfundene Kalenderdaten umgerechnet. Vorschläge, offene Freigaben und fehlende Angaben erzeugen keine neuen Aufgaben. Diese Modellanweisungen reduzieren Fehlinterpretationen; sie garantieren keine fehlerfreien KI-Ergebnisse.

## Prüfung

55 Python-Tests auf dem Pi in separatem QA-Verzeichnis bestanden; darunter neue Prüfungen der meetingbezogenen Auswahl, Erhalt eigener Prompts und Übergabe des automatischen Arbeitsauftrags an den lokalen Backendpfad ohne Überschreiben eigener Aufträge. 6 JavaScript-Tests bestanden. JavaScript-Syntax und `git diff --check` geprüft.

Browserprüfung der isolierten Vorschau mit synthetischen Daten bei 1280 × 720 und 1024 × 600: rechte Ansichten nicht `:modal`, links erreichbare Aufnahme, direkte Navigation, dreizeiliger Titel mit sichtbarem Datum, alle acht Einstellungsseiten ohne vertikalen Inhaltsüberlauf bei den getesteten Zuständen. Designverwaltung bei 1024 × 600 nachgebessert; Tastatureingabe stellt das aktive Feld frei. Nicht alle Konto-, Fehler- und Downloadzustände wurden neu simuliert.

- [Einstellungen](01-settings.png)
- [Bibliothek](02-library.png)
- [Dreizeiliger Aufnahmetitel](03-recent.png)
- [Tastatur bei 1024 × 600](04-keyboard-1024.png)

## Präzisierte Navigation in 0.5.3

„Recorder“ ist eine Ansicht, kein Startbefehl. Nur die große Taste startet beziehungsweise stoppt. Bei laufender Aufnahme öffnet „Recorder“ deren Notizen, sonst bleibt das zuletzt gewählte Meeting samt Inhalt erhalten. Ein neuer Aufnahmestart wechselt aus Bibliothek/Einstellungen direkt zu den zugehörigen Notizen. Dieses Verhalten wurde mit der synthetischen Aufnahmequelle geprüft, einschließlich Wechsel zu einem älteren Meeting und Rückkehr zur laufenden Aufnahme. Ohne fertige Audiodatei zeigt der Player keine alte Dauer mehr.

Ein echter lokaler Modelltest mit Qwen3 4B zeigte trotz der ersten Regeln unzulässig abgeleitete Aufgaben aus Budget und offener Freigabe. Die Vorlage wurde daraufhin konkreter formuliert: reine Informationen bleiben Informationen, angekündigte Termine sind getrennt, offene Freigaben keine Beauftragung. Aufgaben werden als kurze Zeilen ausgegeben. [Aufnahme und Navigation](05-recording-navigation.png).

## Produktive Prüfung 0.5.3

Nach leerer Queue und ohne laufende Aufnahme auf den Pi übertragen; Backend und Kiosk aktiv. Backups: `/home/chris/studio-backups/before-workspace-0.5.2-20261012/application.tar.gz` und `/home/chris/studio-backups/before-workspace-0.5.3-20261012/application.tar.gz`. Microsoft-Sitzung, Standard `staging_playground`, lokale Provider und bestehende Aufnahmen erhalten. Die produktive angemeldete Verbindungsseite bei 1280 × 720 geprüft: Inhalt passt in die rechte Ansicht, keine Modalität.

Lokaler echter Modelltest, Sitzung 33: vorhandenes synthetisches Transkript der Sitzung 32 wiederverwendet, ergänzt um einen ausdrücklich unverbindlichen Mikrofonbestellvorschlag. Kein weiterer ASR-Test, keine neue Mikrofonaufnahme und kein CDB-Versand. Erster Auftrag `aa5e53f829684255af91606ae1b75e41` benötigte 153,1 s und leitete falsche Aufgaben aus Budget/Freigabestatus ab; deshalb verworfen und Vorlage überarbeitet. Zweiter Auftrag `399420dd93ee468ab56a838008bf22a2` mit der überarbeiteten Aufgabenvorlage: abgeschlossen nach 62,0 s, Qwen3 4B Instruct. Ergebnis:

> Aufgaben:
> Frau Meier: erstellt bis Mittwoch die Checkliste.
> Herr Fischer: prüft am Donnerstag das Mikrofon.
>
> Termine:
> Der nächste Test findet am Freitag um 11 Uhr statt.
>
> Offene Punkte:
> Eine Bestellung ist noch nicht freigegeben.

Damit in dieser Probe keine erfundene Budget-/Freigabeaufgabe und keine Aufgabe aus dem Vorschlag. Keine allgemeine Garantie für beliebige Transkripte. Der überarbeitete Auftrag wird ebenfalls an CDB übergeben; ein erneuter Live-CDB-Modelllauf war in dieser Änderung nicht enthalten.

Zusätzlich manuell geprüft: „Öffnen“ in der Queue führt auch aus Einstellungen in die Meetingansicht, einschließlich bereits ausgewähltem Meeting. Vorschauaufnahmen verwenden ausschließlich die synthetische Testquelle. Gesamte Prüfung weiterhin 55 Python- und 6 JavaScript-Tests bestanden.

Transkript und Zusammenfassung nutzen eine Leseansicht: Die Kartenleiste wird ausgeblendet, Titel und Abstände werden kompakter. Bei Notizen erscheint die Leiste wieder. Bibliothek bleibt jederzeit erreichbar. Ohne laufende Aufnahme bewahrt „Recorder“ das zuletzt ausgewählte Meeting und den geöffneten Inhalt; dies ebenfalls im Browser geprüft.

Abschluss: produktiver Code `4cba2dd`, Studio 0.5.3, Backend und Kiosk aktiv. Frontend-Dateihashes lokal/Pi identisch. Queue nach Aufgabenprobe leer. [Produktives Aufgaben-Ergebnis](06-pi-task-result.png) und [produktive Einstellungsansicht](07-pi-settings.png), jeweils 1280 × 720 über den Pi-Tunnel.
