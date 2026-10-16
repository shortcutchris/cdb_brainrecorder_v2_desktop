# Verbleibende Last: passive Anfragen und Seitenwechsel

16. Oktober 2026. Zwei getrennte Diagnosen, keine neue App-Auslieferung.

## Passive Prüfung am laufenden Gerät

Von 02:02:40 bis etwa 02:03:25 Europe/Berlin zählte ein auf 45 Sekunden
begrenzter IPv4-Loopback-Empfänger ausschließlich feste GET-Pfadkategorien
zum App-Port 8088. Header, Cookies, Inhalte und unbekannte Pfade wurden nicht
gespeichert oder ausgegeben. Der einzige eigene HTTP-Aufruf war `/favicon.ico`
als Funktionskontrolle: genau einmal erfasst, Status 204. Keine verlorenen
Pakete laut Socket-Zähler. Sechs Parser-Selbstprüfungen bestanden.

[Ergebnis](passive-counts.json): 90 Zustandsabfragen, 345 Wake-Statusabfragen,
65 sonstige GETs und die eine Kontrollanfrage. **Keine Anfrage nach Play-/Pause-
SVG, HTML-Dokument oder Mikrofon-Skript** in diesem Fenster. Der
[Zähler](passive-counter.py) nimmt keine Prozesszuordnung oder TCP-Reassemblierung
vor; die Zahlen enthalten auch Beobachter und möglicherweise Browserzugriffe
über den lokalen Tunnel. Sie sind keine reine Kiosk-Pollingrate. IPv6 und
geteilte HTTP-Anfragezeilen werden nicht erfasst.

Das spricht gegen fortlaufende Play-Symbol-Netzwerkanfragen als Erklärung der
aktuellen Last. Es ist weder ein direkter Beweis des ausgeführten JavaScript-
Quellstands noch ein Beleg für fehlende interne Browserarbeit. Der Produktions-
Browser wurde nicht neu geladen oder neu gestartet.

## Isolierter Lebenszyklus im selben Testbrowser

Ein eigener stummer Headless-Chromium **142.0.7444.59** führte zuerst 500
unbedingte SVG-Quellenzuweisungen aus. Anschließend navigierte derselbe Browser
auf eine neue Seite mit bedingter Zuweisung und führte dort weitere 500
Durchläufe aus. Keine explizite Garbage Collection, kein Audio und keine
Cloud-Anmeldung. Die minimale SVG-Seite ist keine vollständige App.

| Phase | Dokumentobjekte am Ende | Browser-Task-Zeit in ungefähr 5 s |
| --- | ---: | ---: |
| Vor Belastung | 8 | 0,0058 s |
| Nach unbedingten Bildzuweisungen | 862 | 0,1228 s |
| Erste fünf Sekunden nach Navigation | 431 | 0,4694 s |
| Nach 500 bedingten Durchläufen | 2 | 0,0053 s |
| Spätere Ruheprobe | 2 | 0,0053 s |

Nach Navigation waren zunächst noch Objekte erhalten; danach wurden sie in
dieser Probe ohne expliziten GC-Befehl freigegeben. Der kurz höhere Wert nach
Navigation umfasst den Seitenwechsel und mögliche Aufräumarbeit. Er ist keine
Leerlauf-Dauerlast. Diese Probe widerlegt eine pauschale Behauptung, ein
Browser-Prozessneustart sei immer nötig. Sie erklärt **nicht**, warum der
produktive Browser weiterhin ungefähr 30 % eines CPU-Kerns benötigt. Es wurde
deshalb kein Neustart zur künstlichen Bereinigung des Dauerlaufs ausgeführt.

[Rohmessung](profile.json), [Zusammenfassung und Prüfsummen](summary.json),
[historischer Runner](runner.py), [Bereinigung](cleanup.json).
Beide 500er-Phasen abgeschlossen, 34 Aktivitätsprüfungen ausschließlich idle,
keine protokollierten Testfehler. Testbrowser, lokaler Server und Prüfschleife
sind beendet; kein zugehöriger Prozess blieb übrig, temporäres Profil entfernt.
Systemd meldet `inactive`, `MainPID=0`, `Result=success`.

Der Diagnosezeitraum **02:04:33–02:05:41 Europe/Berlin** überlappt den Dauerlauf.
Die eigene Unit hatte `CPUQuota=50%`, `MemoryMax=512M`, `Nice=15` und eine
Laufzeitgrenze von 150 Sekunden. Zusätzliche Systemlast muss bei der Auswertung
berücksichtigt werden; dies ist keine unbeeinflusste Leerlauf-Baseline.
Der [produktive Beobachter danach](production-after.json) läuft weiter unter
PID 1469691. Der zuvor geschlossene Schlüsselbund-Dialog trat während dieser
Prüfung nicht erneut auf; seine ursprüngliche Ursache bleibt offen.

Nur Diagnoseartefakte und Dokumentation. Kein App-/Runtime-/Image-Unterschied,
kein Zurücksetzen der Beobachtung, kein Langzeit- oder akustischer Test-Pass.
