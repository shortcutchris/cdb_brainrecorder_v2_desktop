# Unverändertes Testplayer-Symbol erhalten · 0.5.56

Freigabekandidat vom 16. Oktober 2026. **Noch nicht installiert.**

Auch auf der Startseite wurde das Play-Symbol des versteckten Mikrofon-Testplayers
bei jeder Zustandsabfrage erneut zugewiesen. Der vorhandene `setIcon`-Helfer
überspringt jetzt identische Quellen. Wechsel zwischen Play und Pause bleiben
sofort sichtbar. Keine Änderung an Erkennungstakt, Audio, Konten oder Modellen.

Die Quellkorrektur stammt aus `d80f558`. Der [minimale Pi-Vergleich](../idle-render-0.5.55/svg-reproduction/README.md)
belegt zusätzliche interne Dokumentobjekte und CPU-Verwaltungsarbeit durch
wiederholte SVG-Ladevorgänge. Der [erste App-Vergleich](../idle-render-0.5.55/app-icon-probe/README.md)
hatte zwei fehlende Nebenabfragen sowie einen falschen Symbolpfad im Testcode
und ist als Kandidatenvergleich ungültig. Die korrigierte Diagnose übernimmt
die echte committed Datei und prüft Quelle, geladenes Symbol und Browserfehler;
der [gültige Pi-Vergleich](pi-comparison/README.md) ist abgeschlossen.
Die Dokumentzahl bleibt beim Kandidaten konstant; der Renderer wächst im
beschriebenen Kurzfenster geringer und benötigt weniger CPU-Zeit. Keine Behauptung, damit bereits
alle Ressourcenprobleme oder die akustische Langzeitbereitschaft gelöst zu haben.

## Prüfungen

111 JavaScript-Tests und 354 Python-Tests bestehen auf dem Mac für den
unveränderten Funktionsstand vor dem Versionssprung. Der Symbol-Regressionstest
prüft 1.000 identische Darstellungen sowie Play-/Pause-Wechsel. Die bestehenden
Tests prüfen Aufnahme-/Verbindungsverlust-Sperren und Fehlerwiederholung.
Die Python-Suite meldet weiterhin die bekannte Qt-/GC-Aufräumwarnung; sie ist
kein Pi-Messwert. Weitere 51 Studio-Tests bestehen nach dem Versionssprung auf 0.5.56.
Weitere acht Diagnosetests verhindern die Freigabe falscher Quellstände,
defekter Bilder und unvollständiger Messungen. Die tatsächliche Prüfung von
API-/HTML-Version auf dem Pi steht noch aus.

## Bestehendes Gerät und Kunden-Image

Gegenüber 0.5.55 ändern sich im App-Paket ausschließlich `studio/microphone.js`
und der Versionswert in `web_server.py`. Beide sind bereits in der bestehenden
Positivliste enthalten. Keine Datenmigration, neue Bibliothek, Firmware oder
Modelländerung. Bestehende Geräte erhalten das signierte Code-Paket; ein neuer
Kunden-Image-Build übernimmt denselben Quellstand automatisch. Das vorhandene
SD-Image 0.5.44 bleibt unverändert; kein neues Image wurde für diesen Fix gebaut.

Eine Auslieferung darf nur über die vorhandene atomare Wartungssperre erfolgen.
Aufnahme, Gespräch und sonstige belegte Ressourcen werden nicht abgebrochen.
Nach erfolgreicher Installation werden Konfigurationsprüfsummen, API-/HTML-
Version und die einzelne Wake-Instanz geprüft. Der bisherige 0.5.55-Zeitraum
bleibt als Teilmessung erhalten; er darf nicht mit einer neuen Version zu einem
bestandenen 24-Stunden-Lauf zusammengezählt werden. Die Gesamt-Abnahme bleibt offen.
