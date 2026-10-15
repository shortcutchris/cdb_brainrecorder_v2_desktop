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
Der unten dokumentierte spätere Lauf ohne Browser-Debugger und Playwright-Routing
ergänzt diese Eingrenzung; er wird wegen eines transienten Hilfsprozesses nicht
als streng gleichbleibende Prozessgruppe akzeptiert.

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
## Zusätzlicher Vergleich ohne Browser-Debugger: abgeschlossen mit Einschränkung

Ein weiterer lokaler Kontrolllauf verwendet natives Headless-Chrome ohne
Playwright, CDP oder Remote-Debugging. Ein reiner Leseproxy vor der synthetischen
Vorschau liefert die Wake-Bereitschaft; die Messung liest ausschließlich
Prozess-RSS von außen. API-Zähler belegen laufende Abfragen, aber weder sichtbare
Bedienbarkeit noch Spracherkennung. Der produktive Pi bleibt unverändert.

Die Beobachtung ist nach **1.800,072 Sekunden** mit 31 Stichproben abgeschlossen.
Browser und Proxy sind bestätigt beendet; keine Statusabfrage meldete einen Fehler.
Die strenge Auswertung mit `scripts/summarize_unattached_browser.py <Messordner>` prüft vollständige Dauer,
Messlücken, weiterlaufende Statusabfragen, konsistente RSS-Summen, gleichbleibende
aktive Prozesse nach zwei Minuten Aufwärmzeit und bestätigten Prozessabschluss.
Ein Null-RSS-Zombie bleibt in den Rohdaten, zählt aber nicht als aktiver Renderer.
PID-Startkennungen wurden in diesem lokalen Versuch nicht erfasst; das wird als
Grenze ausgewiesen. Die Chrome-Startparameter und der HTTP-Proxy unterscheiden
sich von den früheren Messungen; dies ist kein exakt kontrollierter A/B-Vergleich.

Neun gezielte Tests schützen die Auswertung unter anderem vor verkürzten Läufen,
Messlücken, gestoppten Abfragen, fremden Prozessen, Rendererwechseln und fehlendem
Aufräumen. Sie bestätigen die Auswertung, nicht die Stabilität der Applikation.
Aufruf: `python3 -m unittest tests.test_unattached_browser_summary -v`.

Die Auswertung lehnt den strengen Prozessgruppenvergleich **zu Recht ab**:
bei Sekunde 180 erscheint einmalig Hilfsprozess 46417 mit **133,53 MiB RSS**,
ab Sekunde 240 ist er nicht mehr vorhanden. Sein genauer Zweck wurde nicht
ermittelt. Die ursprüngliche Zwei-Minuten-Grenze bleibt bestehen; die Ablehnung
wird nicht durch einen nachträglich verlegten Beginn verdeckt.

Die [ergänzende rein beschreibende Auswertung](unattached/description.json)
prüft zunächst, dass genau diese Ablehnung reproduziert wird. Sie zeigt für die
sieben durchgehend vorhandenen Prozesse zwischen Sekunde 120 und 1.800:
Browser-RSS an den beiden Endpunkten **1.062,91 → 1.071,09 MiB**, der am stärksten
wachsende Renderer **+5,78 MiB**. Die gesamte Prozessgruppe hat wegen des temporären
Helfers eine Spitze von **1.197,17 MiB**. In den letzten zehn Minuten liegen die
Stichproben zwischen **1.070,31 und 1.071,67 MiB**; das beweist kein dauerhaftes
Plateau und erst recht keine entsprechende Verbesserung auf dem Pi.

Die kleinere lokale Zunahme gegenüber den früher instrumentierten Läufen ist
ein Hinweis, diese Messmethoden auseinanderzuhalten. Andere Chrome-Startparameter,
der lokale Proxy und die kurz überlappende CPU-Profilierung verhindern einen
isolierten Kausalnachweis. Kein produktiver Fix wird daraus abgeleitet.
`python3 unattached/describe.py` reproduziert den beschreibenden Bericht samt
Prüfsummen. Rohdaten, historischer Sampler, Abschluss und Bereinigung liegen
im selben Unterordner. Private Chrome-Logs und das temporäre Profil sind nicht
Teil des Repositories; das eigene Testprofil wurde nach Prozessende entfernt.

Keine App-/Runtime-Änderung und kein Einfluss auf das Kunden-Image. Kein Neustart,
keine Audioaktivierung und keine neue Pi-Auslieferung für diese Diagnose.
