# Fünf-Minuten-App-Vergleich: Signal vorhanden, Testaufbau unvollständig

16. Oktober 2026, etwa **01:18:08–01:28:30 Europe/Berlin**. Zwei nacheinander
laufende, getrennte Pi-Chromium-142-Profile laden eine schreibgeschützte
Momentaufnahme der vollständigen App. Nur die ausgelieferte Zeile für das
Play-Symbol unterscheidet sich in der Gegenprobe: identische Quellenzuweisungen
werden durch den vorhandenen `setIcon`-Helfer übersprungen. Dies entspricht der
Quellkorrektur `d80f558`; produktiv bleibt Version 0.5.55 unverändert.

**Keine vollständige App-Abnahme:** In beiden Vorschauen fehlten
`/api/cdb/areas` und `/api/microphone/audio`. Der lokale Testserver antwortete
404, statt die entsprechenden Antworten der App abzubilden. Die fehlende
frühere Mikrofon-Testdatei beeinflusst auch den Player-Fehlerzustand. Alle
Fehler bleiben in den Rohberichten erhalten; `complete_fixture` ist ausdrücklich
`false`. Die folgenden Werte sind eine eingeschränkte Ressourcenbeobachtung.

## Beobachtung bei normalem Abfragetakt

Beide Läufe umfassen je 300 Sekunden mit elf Messpunkten. Die Startseite blieb
sichtbar und online; Zustands- und Wake-Abfragen liefen durchgehend. Je Lauf
300 zusätzliche Zustandsabfragen, 1.000 zusätzliche Wake-Abfragen. Beide
Momentaufnahmen enthielten gleich viele Einträge: 22 Aufnahmen, sieben Aufträge,
keine Live-Nachrichten. Keine Wiedergabe oder Aufnahme gestartet.

| Messwert | Original | Mit Symbol-Guard |
| --- | ---: | ---: |
| SVG-Antworten für `play.svg`, Ende | 336 | 2 |
| Interne Dokumente, Sekunde 60 → 300 | 77 → 114 | 50 → 50 |
| RSS des aktiven Renderers, Sekunde 60 → 300 | +9,16 MiB | +1,03 MiB |
| CPU dieses Renderers, Sekunde 60–300, ein Kern | 3,32 % | 2,39 % |
| Blink-/Embedder-Heap am Ende | 11,09 MiB | 6,69 MiB |

Die ersten 60 Sekunden werden für diese beschreibenden Differenzen getrennt,
bleiben jedoch vollständig in den Rohdaten enthalten. Keine nachträgliche
Änderung eines Abnahmelimits. Der Guard-Lauf zeigt zwischenzeitlich höhere
Objektzahlen und danach eine natürliche Reduktion; er erzeugt weiterhin
kurzlebige Objekte. Es wurde **keine** Speicherbereinigung erzwungen. Die
Momentaufnahme am Ende ist deshalb weder ein langfristiges Plateau noch eine
allgemeine Einsparquote. Zwei einzelne, kurze Läufe liefern keine statistische
Streuung und keinen Beleg für zuverlässige Aktivierung nach langer Pause.

Der Prozessbestand ist in beiden Läufen nicht durchgehend identisch. Die
angegebenen Renderer haben jedoch jeweils dieselbe PID und OS-Startkennung
über alle elf Messpunkte; ihr Typ wurde während der Laufzeit separat aus
`/proc` ermittelt und mit der Startkennung abgeglichen. Gesamtsummen für eine
wechselnde Prozessgruppe werden nicht als Stabilitätsabnahme ausgegeben.

## Schutz und Grenzen

Eigene stumme Headless-Profile, CPU-Limit 50 % eines Kerns, keine GPU, keine
Schreibweiterleitung. Statusdaten blieben im RAM des Vorschau-Servers; die
Berichte speichern nur technische Messwerte und Anzahl der Einträge.
Aktivitätswächter: alle Prüfungen Leerlauf; beim Beginn von Aufnahme oder
Gespräch wäre ausschließlich der Diagnosebrowser beendet worden. Beide
Browser, Server und Wächter sind geschlossen; temporäre Profile entfernt.
Der native Display-Browser wurde weder ersetzt noch neu gestartet.

DevTools-Messung, Headless-Grafik und eingefrorene Statusdaten unterscheiden sich
vom normalen Touchbetrieb. Die zusätzliche Last überlappt den Langzeitmonitor;
dieses Intervall ist Diagnose und keine unbeeinflusste Leerlauf-Baseline.

[Auswertung](summary.json), [Auswertungsskript](summarize.py),
[Original](original/profile.json), [Gegenprobe](guarded/profile.json),
[Prozesszuordnung](identify-processes.py). Die Skripte und jeweiligen
Bereinigungsnachweise sind beigefügt. Die Auswertung setzt die beschriebenen
fünf Minuten voraus und erklärt die Gesamt-Stabilität niemals für bestanden.

## Weiterer Schritt und Auslieferung

Der Testserver wurde anschließend um die zwei fehlenden GET-Antworten ergänzt.
Diese werden einmalig ausschließlich in RAM gehalten, einschließlich des
originalen Antwortstatus; weder Aufnahmeinhalt noch Bereichsnamen werden in
Messdateien übernommen. Ein neuer Originalvergleich ist gestartet; Ergebnisse
werden erst nach Prüfung aller Antworten und der Bereinigung bewertet.

Keine weitere App-Änderung, keine produktive Auslieferung und kein SD-Image durch
diesen Bericht. Die vorhandene Symbol-Korrektur bleibt im Quellstand. Die
24-Stunden-Beobachtung, der tatsächliche Wake nach mindestens acht Stunden Pause
und die Gesamt-Ressourcenabnahme sind weiterhin offen.
