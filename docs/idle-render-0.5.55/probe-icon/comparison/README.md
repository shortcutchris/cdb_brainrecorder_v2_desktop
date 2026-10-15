# Abgeschlossener lokaler 30-Minuten-Vergleich

16. Oktober 2026, etwa **00:39:49–01:10:06 Europe/Berlin**. Zwei getrennte
Chrome-155-Prozesse mit jeweils eigenem Profil, ohne CDP/Playwright und ohne
Audio. Die Startzeiten liegen 17,74 Sekunden auseinander. Beide laufen danach
auf demselben Mac. 87 exportierte Frontend-Dateien sind während der Messung
unveränderlich; nur `microphone.js` unterscheidet sich zwischen den Quellständen
3de5f94 (Original) und d80f558 (Guard). Die API liefert synthetische Vorschau-
Daten, kein produktives Brain-Konto. Ein passiver Fehler-Listener ist in beiden
Testseiten identisch enthalten; es wurde kein Browser-Fehler erfasst.

Beide Läufe erreichen **1.800 reale Sekunden**, jeweils 31 Stichproben,
fortlaufende State-/Wake-Abfragen und keine Proxyfehler. Beide Browser und
Proxy-Threads sind beendet; temporäre Profile sind entfernt. Die Beobachtung
auf dem Pi wurde weder neu gestartet noch durch eine App-Auslieferung verändert.

## Resultat und Grenzen

| Deskriptive Messung, ab 120 Sekunden | Original | Guard |
| --- | ---: | ---: |
| RSS zu Beginn | 1.063,78 MiB | 1.067,48 MiB |
| RSS am Ende | 1.081,06 MiB | 1.083,91 MiB |
| Differenz | +17,28 MiB | +16,42 MiB |
| Größter Zuwachs eines durchgehenden Renderer-Prozesses | +6,14 MiB | +5,45 MiB |
| Zwischenzeitlicher Gesamt-Spitzenwert | 1.198,09 MiB | 1.201,12 MiB |

**Kein belastbarer Speichervorteil und kein Pi-Fix nachgewiesen.** In beiden
180-Sekunden-Proben erscheint ein zusätzlicher Hilfsprozess mit rund 133,5 MiB,
der danach wieder verschwindet. Seine genaue Aufgabe konnte nicht mehr
festgestellt werden. Der strenge Vergleich unveränderter Prozessgruppen wird
für **beide** Läufe deshalb abgewiesen. Dieser Fehlschlag bleibt erhalten;
Anlaufgrenze oder Rohdaten werden nicht nachträglich verschoben.

Die Tabelle beschreibt lediglich Endpunkte. Die ergänzenden Einzelprozesswerte
verwenden nur PIDs, die in jeder Probe nach der festgelegten Anlaufphase vorhanden
sind; Prozessnamen und vom Betriebssystem gemeldete Startzeiten werden geprüft.
Auch diese Zusatzbeschreibung ersetzt den gescheiterten Prozessgruppenvergleich
nicht. RSS kann gemeinsam genutzte Seiten mehrfach enthalten. Ein einzelner
paralleler Versuch auf einem Mac liefert weder eine kausale Effektgröße noch
eine Aussage zur Pi-Version Chromium 142. Offline-Symbolauswertung lief während
des Fensters zusätzlich auf demselben Mac; der Host war nicht exklusiv reserviert.

Die [kurze UI-Messung](../README.md) bestätigt weiterhin, dass der Guard
wiederholte Quellenzuweisungen und `load`-Ereignisse vermeidet. Ein daraus
abgeleiteter langfristiger Speicher-Fix wäre aber nicht durch diese Daten gedeckt.
Die [native Pi-Stichprobe](../../native-perf/README.md) ist deshalb für den
nächsten gezielten Eingrenzungsschritt maßgeblich.

## Vollständigkeit und Reproduktion

- [Original: Beschreibung](original/description.json), [Rohmessungen](original/process-memory.jsonl), [Bereinigung](original/cleanup.json).
- [Guard: Beschreibung](guarded/description.json), [Rohmessungen](guarded/process-memory.jsonl), [Bereinigung](guarded/cleanup.json).
- `python3 describe.py original` beziehungsweise `python3 describe.py guarded`
  reproduziert zuerst die strenge Zurückweisung und erstellt erst danach die
  ausdrücklich beschreibende Ergänzung. Andere Fehler werden nicht übergangen.
- Beide Verzeichnisse enthalten Plan, Quellenprüfsummen, Sampler, Abschluss und
  Proxyzähler. Die zugehörigen vollständigen Browser-Logs bleiben außerhalb Git.
- `failed-startup` enthält beide ersten, sauber beendeten Fehlversuche: Die
  geforderten Wake-Abfragen begannen nicht. Der genaue Startfehler blieb
  ungeklärt; er wird nicht als App-Fehler oder bestandener Test dargestellt.
- `startup-pilot` enthält den getrennten, erfolgreichen Zehn-Sekunden-Aufbaucheck
  mit passivem Fehler-Listener. Der folgende Vergleich wurde mit diesem Aufbau
  und gestaffelten Starts vollständig neu gemessen. Auch das beweist nicht die
  Ursache der vorherigen Startfehler.

Keine Laufzeitänderung, keine neue Auslieferung, kein Image-Einfluss durch diesen
Bericht. Das produktive 0.5.55 und die gesamte Stabilitätsabnahme bleiben offen.
