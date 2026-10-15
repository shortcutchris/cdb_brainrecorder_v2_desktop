# Lokale Kontrollen des Speicheranstiegs

15. Oktober 2026. Ausschließlich synthetische lokale Vorschau auf dem Mac mit
Chrome 155, keine Pi-Aufnahmen, kein Mikrofon und keine Cloud-Gespräche. Die
Frontend-Dateien entsprechen 0.5.55; der Vorschau-Backendprozess meldet 0.5.52.
Der echte Pi läuft weiterhin unverändert mit Chromium 142. Das ist kein
Hardware-Abnahmetest und keine Bestätigung eines behobenen Speicherverlusts.

## Vergleichsbedingungen

1. **Normale Oberfläche, 30 Minuten:** der zuvor dokumentierte
   [natürliche Lauf](../natural-idle-mac/summary.json).
2. **Ansichtsaktualisierung angehalten, 30 Minuten:** nach dem Laden wird nur
   `renderState` durch einen zählenden Platzhalter ersetzt. Statusabfragen,
   sonstige Timer und CSS laufen weiter. Die Oberfläche ist dadurch eingefroren
   und wäre als Produkt nicht benutzbar.
3. **Statische Seite, acht Minuten:** kein App-Code, keine App-Statusabfragen.
   Die Seite hat zehn DOM-Objekte und keine Ereignisbehandler. Nur hier erfolgt
   eine erzwungene Speicherbereinigung vor Beginn des Messfensters.
4. **Ansichtsaktualisierung und Anfrage-Zeitlimits abgeschaltet, zehn Minuten:**
   wie Fall 2, zusätzlich liefert `AbortSignal.timeout` nur `undefined` zurück.
   Der Zähler bestätigt 2.605 Aufrufe dieses Diagnose-Platzhalters. Dies ist
   ausdrücklich keine sichere produktive Änderung: Zeitlimits gehören weiter
   zum Schutz gegen hängende Verbindungen.

Die Browser werden etwa einmal pro Minute über dieselben CDP-Abfragen gemessen.
Der separate Playwright-Treiber ist nicht in der Browser-RSS-Summe enthalten.
Die OS-Vergleiche beginnen für **alle** Fälle erst mit der ersten Stichprobe
nach zwei Minuten. Grund: Eine frühe Probe des vierten Falls enthält noch
Objekte der vorherigen Seite; nach 74 Sekunden sind wieder 29 Dokumente und
2.421 DOM-Objekte vorhanden. Die vollständigen Rohdaten einschließlich dieses
Anlaufs bleiben erhalten. Die tatsächlichen Zeitgrenzen stehen im Bericht.

## Beobachtung

| Fall | Beobachtungsfenster | OS-Vergleich nach Aufwärmphase | Änderung Browser-RSS |
| --- | --- | --- | --- |
| Normale Oberfläche | 30 Minuten | 27,53 Minuten | +40,08 MiB |
| Ansichtsaktualisierung angehalten | 30 Minuten | 27,74 Minuten | +42,86 MiB |
| Statische Seite | 8 Minuten | 5,78 Minuten | +1,31 MiB |
| Zusätzlich Zeitlimits abgeschaltet | 10 Minuten | 7,75 Minuten | +12,41 MiB |

In den beiden eingefrorenen App-Ansichten bleiben DOM-Objekte und
Ereignisbehandler nach dem Anlauf bei 2.421 bzw. 297. Trotzdem steigt der
Prozessspeicher weiter. Die regelmäßigen `renderState`-Schreibvorgänge allein
erklären den lokalen Befund damit nicht. Auch das Abschalten von
`AbortSignal.timeout` beseitigt den Anstieg in diesem kurzen Versuch nicht.
**Es gibt keinen Grund, daraus eine Entfernung der produktiven Zeitlimits
abzuleiten.** Die statische Seite zeigt einen deutlich kleineren Anstieg,
aber weder exakt null Verbrauch noch einen Langzeitnachweis.

Die Zeitfenster sind unterschiedlich lang und teilweise überlappend auf
demselben Mac; absolute RSS-Werte sind kein kontrollierter Effektvergleich.
RSS kann gemeinsam genutzte Seiten mehrfach zählen. Die Ergebnisse beweisen
weder eine allgemeine Browser-Speicherlücke noch deren Ursache auf dem Pi.
Als nächste Eingrenzung bietet sich ein lokaler Lauf ohne angeschlossenen
Browser-Debugger und ohne Playwright-Routing an, bevor produktiver Code auf
Basis dieser Instrumentierung verändert wird.

## Eigenverbrauch der Instrumentierung

Das verwendete Routing ruft `route.fetch()` auf und gibt seine `APIResponse`
nicht ausdrücklich frei. Laut [Playwright-Dokumentation](https://playwright.dev/docs/api/class-apiresponse#api-response-dispose)
bleiben solche Antwortkörper bis zur Freigabe oder bis zum Schließen des
Kontexts gespeichert. Das ist ein bekannter Einfluss auf den **separaten
Testtreiber**, kein Nachweis für die Ursache des Pi-Renderer-Verbrauchs.
Die laufenden Bedingungen wurden während dieser Vergleichsserie nicht
geändert. Bei künftigen Routing-Tests sind Antwortobjekte nach abgeschlossener
Weitergabe freizugeben oder das Routing als Instrumentierung zu vermeiden.

## Nachweise und Abschluss

[Reproduzierbare Auswertung mit Rohdaten-Prüfsummen](comparison.json).
`python3 compare.py` berechnet sie aus den Dateien in diesem Verzeichnis und
dem benachbarten `natural-idle-mac` neu. Die Auswertung verlangt abgeschlossene
Messfenster, geordnete Stichproben und dokumentierte Browser-Schließung; sie
setzt niemals das Gesamtziel auf abgeschlossen.

Die Unterordner enthalten Rohdaten, Versuchsbeschreibung, verwendete
Browser-Proben und Sampler sowie den bestätigten Prozessabschluss. Die
archivierten Sampler dokumentieren die damaligen PIDs und temporären Pfade;
neue Läufe brauchen eigene Browser-Sitzungen und neue Ausgabeverzeichnisse.
Die nachträglichen GC-Proben der beiden App-Kontrollen liegen außerhalb ihrer
natürlichen Messfenster. Alle dafür gestarteten Testbrowser sind geschlossen.

Nur Diagnose und Dokumentation: kein Laufzeit-, Firmware-, Konto- oder
Image-Einfluss, keine neue App-Auslieferung. Die echte 24-Stunden-Beobachtung
und die akustische Langzeitabnahme bleiben offen.
