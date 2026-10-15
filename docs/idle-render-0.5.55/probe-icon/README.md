# Vermeidbare Bild-Neuladung im versteckten Mikrofon-Player

16. Oktober 2026. Korrektur im Quellstand, **noch nicht auf dem Pi ausgeliefert**.
Die laufende 24-Stunden-Beobachtung verwendet weiterhin unveränderte Version
0.5.55 aus Commit 7868716.

`renderProbePlayer` setzt bisher bei jeder Zustandsabfrage erneut die Quelle des
Play-/Pause-Symbols. Der Aufruf erfolgt auch auf der Startseite bei geschlossenem
Audio-Bereich. Der vorhandene `setIcon`-Helfer verhindert nun identische
Zuweisungen. Ein tatsächlicher Wechsel zwischen Play und Pause wird weiterhin
sofort angezeigt. Keine Änderung an Aufnahme, Medienfreigabe oder Wake-Logik.

## Beobachteter Unterschied

Ein getrennter lokaler Browser lädt die synthetische Vorschau auf Port 8099.
Ausgangscode aus Commit 3de5f94, anschließend genau diese Ein-Zeilen-Korrektur
über eine Antwortüberschreibung, jeweils nach erneutem Laden und 1,5 Sekunden
Anlauf. Gemessen wurden je 12 Sekunden bei laufenden Zustandsabfragen:

| Beobachtung am Play-Symbol | Vorher | Mit Guard |
| --- | ---: | ---: |
| Änderungen am `src`-Attribut | 13 | 0 |
| `load`-Ereignisse | 13 | 0 |
| Beobachtete Netzwerkanfragen auf play.svg | 0 | 0 |

Damit ist das wiederholte Laden aus dem Browsercache belegt, **kein wiederholter
Netzwerktransfer**. Das beweist noch keine Ursache oder Behebung des langfristigen
Pi-Speicheranstiegs. Der Messbrowser wurde danach geschlossen; kein Audio,
kein Zugriff auf produktive Aufnahmen und keine Änderung des Pi-Browsers.
[Messwerte](comparison.json), [historisches Prüfszenario](audit.js).
Das Prüfszenario setzt den angegebenen Ausgangscommit voraus; mit bereits
korrigiertem Quellstand ist dessen Original-Code-Prüfung absichtlich nicht erfüllt.

Der Regressionstest verwendet den echten `setIcon`-Helfer und simuliert 1.000
identische Aktualisierungen sowie die Wechsel Pause/Play. Vor der Korrektur
scheitert er mit 1.000 statt einer Quellenzuweisung; danach bestehen alle
**111 JavaScript-Tests**, einschließlich der bestehenden Wiedergabe-, Fehler-,
Aufnahme- und Verbindungsverlust-Prüfungen. `git diff --check` besteht.

## Auslieferung und Image

Die korrigierte Datei `studio/microphone.js` ist bereits Teil der App-Allowlist.
Bestehende Geräte erhalten sie mit dem nächsten signierten App-Update; neue
Kunden-Images übernehmen sie beim Build aus diesem Quellstand. Es gibt keine
Datenmigration, neue Abhängigkeit oder Änderung an Kundenkonfigurationen. Ein
neues Image oder eine neue App-Version wurde hierfür noch nicht gebaut. Die
kontrollierte Pi-Abnahme des Kandidaten folgt nach Abschluss des aktuellen
Beobachtungsfensters; dessen Laufzeit wird für diesen lokalen Nachweis nicht
zurückgesetzt. Die gesamte Stabilitätsabnahme bleibt offen.

Der anschließende 30-Minuten-Vergleich verwendet exportierte, unveränderliche
Quellstände (3de5f94 und d80f558). Von 87 Frontend-Dateien unterscheidet sich nur
`microphone.js`. Die Messung erfasst nun zusätzlich den vom Betriebssystem
angegebenen Prozessstart. Die Auswertung verwirft wiederverwendete PIDs mit
abweichender Startkennung und nur teilweise vorhandene Kennungen; historische
Messungen ohne dieses Feld bleiben ausdrücklich auf PID-Prüfung beschränkt.
Zwölf Auswertertests bestehen, einschließlich abgebrochener Messungen,
Polling-Stillstand, wechselnder Prozesse und fehlender Bereinigung. Dies ändert
nur die Diagnoseauswertung, nicht die App oder ein Kunden-Image. Ein Ergebnis
des längeren Vergleichs liegt zu diesem Dokumentationsstand noch nicht vor.
