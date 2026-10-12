# Studio 0.5.2 – Arbeitsansichten und sinnvolle Aufgaben

Bibliothek und Einstellungen teilen sich als nichtmodale Ansichten die rechte Arbeitsspalte mit dem Meetinginhalt. Die große Aufnahme-/Stopptaste, Navigation und Queue bleiben erreichbar. Schließen oder „Aufnahme“ führt zum Meeting zurück; Auswahl in der Bibliothek öffnet das gewählte Meeting. Auswahl- und Bestätigungsdialoge bleiben für einzelne Aktionen bestehen.

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
