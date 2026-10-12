# Audit der Web-Navigation

12.10.2026, aktuelle Browser-Oberfläche bei 1280 × 720. Grundlage sind die während dieses Arbeitslaufs aufgenommenen Screens, die echte synthetische Aufnahme und die automatischen Zustandsprüfungen.

Die Hauptursache war eine vermischte Navigation: Die linke Leiste wechselte Hauptansichten, während die Seitenköpfe dieselben Ansichten wie wegklickbare Dialoge behandelten. Das erzeugte konkurrierende Rückwege. Die Korrektur folgt einer einzigen Regel: **Hauptansichten wechseln links; Unterseiten führen zu ihrer Übersicht zurück; echte Aktionsdialoge dürfen geschlossen werden.**

| Schritt | Befund | Korrektur / Prüfstand |
|---|---|---|
| 1. Recorder → Aufnahme | Aufnahme muss sichtbar bleiben; andere Arbeitsbereiche dürfen die Sitzung nicht verändern. | Record/Stop bleibt im Recorder. Bibliothek, Einstellungen und Queue während Aufnahme gesperrt; Notizen und Tastatur erreichbar. Nach Stoppen sofort frei. |
| 2. Bibliothek → Detail → Liste | X im Kopf der Bibliothek führte irreführend zum Recorder; Detail-Rückweg ist dagegen sinnvoll. | X entfernt. Nur Detail → „Zur Aufnahmeliste“ bleibt. Auswahl und Texttab bleiben beim Wechsel erhalten. |
| 3. Einstellungen → Übersicht | X und „Zum Recorder“ duplizierten die Hauptnavigation; Keyboard hatte hier kein Eingabefeld. | Beide redundanten Aktionen entfernt. Tastatur ohne editierbares Feld deaktiviert. „Audio einrichten“ nur bei offener Einrichtung. |
| 4. Übersicht → alle acht Unterseiten | Zweite Seitennavigation und überbreite Fußaktionen störten die Hierarchie. | Seitennavigation entfernt; „Alle Einstellungen“ bleibt als echter Rückweg. Einzelne Seiten geöffnet, fotografiert und auf Inhaltsüberlauf geprüft. |
| 5. Warteschlange | Eigene Hauptansicht, aber zusätzlicher Recorder-Rückweg und ursprünglich eine Dauerleiste/Overlay. | Normale rechte Ansicht, keine Fußleiste, kein Overlay, kein Rückweg im Kopf. Hauptnavigation links. Anzahl/Animation am Icon; Status und Fehler in der Ansicht. |
| 6. Aktionsdialoge / Texteingabe | Tastatur-Erweiterung setzte überall einen Dialogkopf voraus; leere Tastaturen waren möglich. | Echte Dialoge behalten Schließen und bei Texteingabe ihre Tastaturaktion. Workspace-Köpfe erhalten keine duplizierte Tastaturaktion. Leere Tastatur öffnet nicht; Navigation schließt sie. |

Weitere Korrekturen: CDB-Statusmeldungen auf Deutsch, Prozentwerte ausschließlich vom gemeldeten Fortschritt; lokale Modellfelder bei Online-Verarbeitung ausgeblendet; lange Prompttexte mit Textseiten; ungespeicherter Theme-Entwurf beim Rückweg verworfen; gefährliche Meetingaktion im Fuß links getrennt von „Titel speichern“.

## Nachweise

- [Aufnahmesperren](final-recording.jpg)
- [Bibliothek](final-library.jpg)
- [Einstellungen](26-final-overview.jpg)
- [Design-Unterseite](final-design.jpg)
- [Warteschlange](25-queue-view.jpg)
- [Alle acht Seiten, Messungen](layout-checks.json)

## Grenzen

Das ist ein Audit der tatsächlich erreichbaren Touch-Oberfläche und ihrer Navigation, kein allgemeiner Konformitätsnachweis. Physische Treffgenauigkeit, Screenreader-Verhalten und weitere Browser wurden nicht umfassend geprüft. Native Farbauswahl und Browser-Downloads folgen dem Browser. Browser-Zurück/Vorwärts ist aktuell kein eigener Navigationspfad für diese App-Ansichten; ein Neuladen startet im Recorder. Erzwungene Netzwerk-/Kontofehler werden durch gezielte Tests geprüft, nicht durch Abmelden der produktiven Sitzung. Lange variable Inhalte werden über bestehende Inhalts-/Textseiten bedient; nicht jeder mögliche individuelle Inhalt wurde vermessen.
