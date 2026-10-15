# Ungültiger App-Kandidatenvergleich: Rohdaten zur Fehleranalyse

16. Oktober 2026, etwa **01:18:08–01:28:30 Europe/Berlin**. Zwei getrennte
Pi-Chromium-142-Profile liefen je fünf Minuten. **Die Gegenprobe entspricht
nicht der committed App-Korrektur und darf deren Wirkung nicht belegen.**
Der produktive Browser und die App blieben unverändert bei 0.5.55.

## Nachträglich erkannter Fehler im Testaufbau

Der Testcode übergab dem `setIcon`-Helfer `play` statt der vollständigen Adresse
`/assets/play.svg`. Der Helfer erwartet eine Adresse. Die Gegenprobe stellte
somit ein fehlendes Bild statt des richtigen Symbols ein. Der Testserver
protokollierte fehlende statische Dateien bisher nicht als Fehler. Die
Prüfsumme der tatsächlich bedienten Datei weicht von der Korrektur `d80f558` ab:

- Tatsächlicher Kandidat im Repository: `9de014063923156499f4b294ad16b7402664785f24cd2d25307716ce7fc71276`.
- Die experimentelle Quellen-Prüfsumme steht unverändert in `summary.json`.
- `candidate_matches_repository` ist für die Gegenprobe **false**;
  `valid_app_candidate_comparison` ist ausdrücklich **false**.

Zusätzlich fehlten in beiden Vorschauen `/api/cdb/areas` und
`/api/microphone/audio`: Der Testserver antwortete 404. Diese Fehler wurden
bereits beim ersten Bericht offengelegt; sie waren jedoch nicht die einzigen
Probleme. Die erste Interpretation eines Kandidatenvorteils wird hiermit
zurückgenommen. Auch die danach gestartete zweite Diagnose-Revision war vom
falschen Symbolpfad betroffen und wird nicht als bestandener Vergleich gewertet.

## Erhaltene Beobachtungen, keine Freigabe-Evidenz

Die Startseite blieb sichtbar und online; Zustands- und Wake-Abfragen liefen.
Je Lauf 300 zusätzliche Zustandsabfragen und 1.000 zusätzliche Wake-Abfragen.
Beide Momentaufnahmen enthielten 22 Aufnahmen, sieben Aufträge und keine
Live-Nachrichten. Keine Wiedergabe oder Aufnahme gestartet.

| Messwert | Original | Fehlerhafter Testcode |
| --- | ---: | ---: |
| Erfolgreiche Antworten für `play.svg`, Ende | 336 | 2 |
| Interne Dokumente, Sekunde 60 → 300 | 77 → 114 | 50 → 50 |
| RSS des aktiven Renderers, Sekunde 60 → 300 | +9,16 MiB | +1,03 MiB |
| CPU dieses Renderers, Sekunde 60–300, ein Kern | 3,32 % | 2,39 % |

Diese Werte erklären, weshalb der Fehler zunächst plausibel wirkte. Sie sind
kein gültiger Vergleich der vorgesehenen Korrektur. Die vollständigen elf
Messpunkte bleiben erhalten. Keine erzwungene Speicherbereinigung. Der
Prozessbestand wechselt in beiden Läufen; die angegebenen Renderer behalten
jeweils PID und OS-Startkennung. Keine pauschale Stabilitätsaussage aus RSS-Summen.

Beide Browser, Server und Wächter sind geschlossen; temporäre Profile entfernt.
Alle Aktivitätsprüfungen meldeten Leerlauf. Die zusätzliche Diagnose-Last
überlappt den Langzeitmonitor und ist keine unbeeinflusste Leerlauf-Baseline.
Statusdaten blieben im RAM; Berichte enthalten technische Werte und Anzahlen,
keine Aufnahmeinhalte, Bereichsnamen oder Kontotokens.

[Historische Auswertung](summary.json), [Auswertungsskript](summarize.py),
[Original](original/profile.json), [fehlerhafte Gegenprobe](guarded/profile.json),
[Prozesszuordnung](identify-processes.py). Runner und Bereinigung sind beigefügt.
Die unabhängig durchgeführte [minimale SVG-Probe](../svg-reproduction/README.md)
verwendet in beiden Varianten korrekt `/icon.svg`; ihr Befund bleibt bestehen.

## Korrigierter Prüfweg

Revision 3 kopiert die **tatsächliche committed `microphone.js`** in den
isolierten Server. Vor dem Start prüft sie den exakten Ein-Zeilen-Unterschied
zum installierten Original und die SHA256. Jeder Messpunkt prüft zusätzlich
`src`, erfolgreiche Bilddekodierung sowie JavaScript-/HTTP-Fehler. Die zwei
Nebenabfragen werden ausschließlich in RAM mit echtem Antwortstatus gehalten.
Erst ein so geprüfter Vergleich kann eine App-Freigabe unterstützen.

Keine produktive App-Auslieferung und kein neues SD-Image durch diese Diagnose.
Die Langzeit- und akustische Abnahme bleiben offen.
