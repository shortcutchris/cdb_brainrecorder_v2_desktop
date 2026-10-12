# Einstellungen 0.5.12

## Aufbau

Alle Einstellungsdetails verwenden bei 1280 × 720 einen 80 px hohen Header, einen 532 px hohen Inhaltsbereich und eine 80 px hohe Aktionsleiste. Darunter bleibt die bestehende 28-px-Statuszone. Innenabstand 24 px, Spaltenabstand 20 px, Abstand zusammengehöriger Felder 12 px. Touchbuttons sind 56 px hoch. Hauptaktion rechts (240 px), Nebenaktion daneben (180 px), Dienstprogramme links. Verfügbare Aktionen verändern die Positionen der übrigen Buttons nicht.

Brain zeigt Benutzer und Server getrennt vom Standardbereich. Breadcrumbs erlauben den direkten Rückweg zur Übersicht und zur übergeordneten Seite. Aufnahme-Sperren gelten auch für diese Navigation. Modellwechsel reserviert den Platz für lokale Auswahlfelder, damit Testergebnis und Aktionen nicht springen.

Lange Inhalte behalten ihre nummerierten Seiten (Vorlagen, Testergebnisse, Themeauswahl, Übertragungen). Bei der Bildschirmtastatur wird nur der relevante Eingabebereich gezeigt; die Aktionsleiste bleibt darüber erreichbar.

## Prüfung

- 78 Python-Tests auf dem Pi bestanden.
- 37 JavaScript-Tests bestanden, einschließlich Breadcrumb-Rückwegen, Aufnahmesperre und Kontozuständen.
- Browserprüfung bei 1280 × 720: alle Einstellungsseiten, Modellprovider lokal/Brain, Themeeditor, Vorlagenseite 1/2, Tastatur, Diagnose geöffnet/geschlossen, Übertragungen leer und Anmeldung ausstehend.
- Kein Überlauf des äußeren Inhaltsbereichs in den geprüften Zuständen; gleiche Fußleistenposition (y=612, Höhe=80), Buttons y=624, Höhe=56. Bei Tastatur entsprechend y=392/404. Messwerte in `layout-metrics.json`.
- Keine Browserfehler in der geprüften Vorschau.
- Isolierte Vorschau auf dem Pi mit separater Datenablage. `14-brain-pending.png` zeigt ausdrücklich simulierte Anmeldedaten (DEMO 1234), keinen echten Anmeldecode. Modelltesttexte stammen aus gespeicherten Nachweisen; keine erneute Qualitätsmessung oder Cloudübertragung für dieses Layoutupdate.

## Screenshots

| Ansicht | Nachweis |
|---|---|
| Übersicht | [00-overview.png](00-overview.png) |
| Brain-Konto | [01-brain.png](01-brain.png) |
| KI & Modelle | [02-models.png](02-models.png) |
| Transkription lokal / Brain | [03-transcription.png](03-transcription.png), [04-transcription-cloud.png](04-transcription-cloud.png) |
| Vorlagen Seite 1 / 2 | [05-prompts.png](05-prompts.png), [05b-prompts-page2.png](05b-prompts-page2.png) |
| Bildschirmtastatur | [06-prompts-keyboard.png](06-prompts-keyboard.png) |
| Design / Editor | [07-design.png](07-design.png), [08-theme-editor.png](08-theme-editor.png) |
| Diagnose | [09-diagnosis.png](09-diagnosis.png), [10-diagnosis-advanced.png](10-diagnosis-advanced.png) |
| Audio | [11-audio.png](11-audio.png) |
| Übertragungen | [12-transfers.png](12-transfers.png) |
| Zusammenfassung | [13-summary.png](13-summary.png) |
| Anmeldung ausstehend | [14-brain-pending.png](14-brain-pending.png) |

## Produktiver Pi

Version 0.5.12 auf den produktiven Pi gespielt. Vor dem Neustart waren Aufnahme und Warteschlange inaktiv. Sicherung unter `/home/chris/backups/recorder-before-0.5.12`. Backend und Kiosk aktiv. Alle sechs ausgelieferten Dateien per SHA256 gegen den lokalen Stand verglichen (`deployment.json`). 22 Aufnahmen, Konfiguration, Provider, Brain-Anmeldung und Zielbereich unverändert.

Produktive Ansichten: [Brain-Konto](15-production-brain.png), [Übertragungen mit drei Inhaltsseiten](16-production-transfers.png), [Modellseite mit Breadcrumb](17-production-model.png). Auch die Seitentasten der Übertragungen sind auf y=624 / Höhe=56 ausgerichtet.
