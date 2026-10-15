# SVG-Neuladungen im tatsächlichen Pi-Chromium eingrenzen

16. Oktober 2026. Diagnose im eigenen stummen Headless-Browser auf dem Pi,
Chromium **142.0.7444.59**. Produktiver Browser und App 0.5.55 bleiben unverändert.
Diese Kurzprobe erklärt einen reproduzierbaren Mechanismus, **nicht bereits die
vollständige Ursache oder Behebung des produktiven Langzeitwachstums**.

## Kontrollierter Vergleich

Eine minimale Seite lädt das originale `studio/assets/play.svg`. Zwei getrennte,
frische Browserprofile führen je 500 Timeraufrufe aus. Die Originalvariante setzt
jedes Mal dieselbe Bildquelle; die Gegenvariante prüft vor der Zuweisung, ob sie
bereits gesetzt ist. Gleiche SVG-Prüfsumme, Browserflags und Ressourcenlimits.
Keine Aufnahme, keine Cloud-Verbindung, keine Schreibzugriffe auf die App.

| Messwert | Wiederholte Zuweisung | Unveränderte Quelle überspringen |
| --- | ---: | ---: |
| Ausgeführte Timeraufrufe | 500 | 500 |
| Stressphase | 8,402 s | 4,000 s |
| SVG-HTTP-Antworten im gesamten Lauf | 417 | 1 |
| `load`-Ereignisse am Ende der Stressphase | 362 | 1 |
| Interne Dokumentobjekte nach 5 s Ruhe | 828 | 4 |
| Blink-/Embedder-Heap nach 5 s Ruhe | 34,52 MiB | 1,19 MiB |
| Browser-Task-Zeit in diesen 5 s | 0,135474 s | 0,003211 s |

Die 500 Zuweisungen entsprechen **nicht** 500 vollständig geladenen Bildern:
Browseranfragen und Ladeereignisse werden zusammengefasst beziehungsweise
überholt. `Cache-Control: no-store` entspricht der tatsächlich gelesenen
Produktionsantwort des Symbols. Der frühere Mac-Vorschautest ohne neue
Netzwerkanfragen ist deshalb kein Beleg für fehlenden Netzwerktransfer am Pi.

Erst in einer **separaten letzten Phase** wird ausschließlich im Diagnosebrowser
explizite Speicherbereinigung ausgelöst. Danach sinken die internen Dokumente
in beiden Varianten auf zwei; die Task-Zeit liegt bei jeweils etwa 0,0032 s je
fünf Sekunden. Das zeigt zurückgehaltene, bereinigbare Objekte in dieser Probe.
Es beweist weder einen dauerhaften Leak noch, wann der Produktivbrowser von
selbst bereinigen würde. Eine solche Bereinigung wurde produktiv nicht ausgelöst.
Der größte wachsende Prozess behält nach der Bereinigung einen Teil seines
RSS-Zuwachses; Objektzahl, Heap und RSS dürfen nicht gleichgesetzt werden.

## Fehlversuch und Grenzen

Der erste Lauf mit 2.500 Zuweisungen erreicht das 40-Sekunden-Limit, nachdem
1.044 SVG-Antworten bedient wurden. Er ist **fehlgeschlagen**, kein Test-Pass.
Sein Runner, Fehlerbericht und die vollständige Bereinigung bleiben unter
[failed-2500](failed-2500/failure.json) erhalten. Die zweite Revision begrenzt
beide Varianten gleich auf 500 Aufrufe und speichert Zwischenstände dauerhaft.
Sie ersetzt oder widerlegt den fehlgeschlagenen größeren Test nicht.

Die tatsächliche Startseite läuft mit ungefähr einer Zustandsabfrage pro
Sekunde. Der beschleunigte Mini-Test läuft nominal alle acht Millisekunden,
unter `CPUQuota=50%`, mit deaktivierter GPU und aktiviertem DevTools-Zugang.
Auch der native Display-Browser und dessen Grafikpfad sind damit nicht abgebildet.
Die Profile laufen nacheinander, nicht gleichzeitig. Der Prozessbestand enthält
in der Originalvariante einen vorübergehenden Hilfsprozess; aus einer Summe aller
RSS-Werte wird hier kein strenger Stabilitätsnachweis abgeleitet. Die Auswertung
vergleicht CPU-Zähler nur bei gleicher PID **und** gleicher OS-Startkennung.

Beide Testbrowser samt Server und Aktivitätswächter sind nachweislich beendet,
die temporären Browserprofile gelöscht. Alle Aktivitätsprüfungen meldeten Leerlauf.
Die Tests überlappen den Dauerlauf etwa **01:12:54–01:13:44** (Fehlversuch),
**01:16:45–01:17:14** (Original) und **01:17:21–01:17:45** (Guard), Europe/Berlin.
Diese Intervalle sind zusätzliche Systemlast, keine unbeeinflusste Baseline.
Verbindliche Zeitstempel stehen in den JSON-Dateien.

## Nachweis und nächster Schritt

[Maschinelle Zusammenfassung](summary.json), [reproduzierbare Auswertung](summarize.py),
[Originalmessung](original/profile.json), [Gegenmessung](guarded/profile.json).
Die historischen Runner sind jeweils beigefügt; sie setzen die dokumentierte
Pi-Version und Pfade voraus. Die Auswertung prüft vollständige Iterationen,
Version, Aktivitätswächter und Bereinigung, behauptet aber keine Gesamt-Abnahme.

Als Nächstes wird der schon in `d80f558` korrigierte `renderProbePlayer` mit der
vollständigen Oberfläche und dem normalen Polling derselben Pi-Browserversion
verglichen. Kein weiterer Laufzeitcode geändert, keine App-Auslieferung und kein
neues SD-Image durch diese Diagnose. Die Korrektur bleibt zunächst nur im
Quellstand; die 24-Stunden- und akustische Langzeitabnahme bleiben offen.

Der anschließende [Fünf-Minuten-App-Vergleich](../app-icon-probe/README.md)
ist als Vergleich der App-Korrektur **ungültig**: Neben fehlenden Nebenabfragen
verwendete sein experimenteller Guard einen falschen Symbolpfad. Die Rohwerte
bleiben zur Fehleranalyse erhalten. Die hiervon unabhängige minimale SVG-Probe
oben nutzt dagegen in beiden Varianten korrekt `/icon.svg`.
