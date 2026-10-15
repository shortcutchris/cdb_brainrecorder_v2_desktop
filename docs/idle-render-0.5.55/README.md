# Leerlauf-Aktualisierungen reduzieren · 0.5.55

15. Oktober 2026. Die schnelle Wake-Abfrage schrieb auch bei unverändertem
Zustand Titel, Detailtext, LED-Zustand und Sichtbarkeit erneut in den DOM.
Die Touch-Navigation setzte zusätzlich bei jeder Prüfung dieselbe
Seitenbeschriftung. Diese Schreibvorgänge lösten unnötige Beobachteraufrufe
und Stilprüfungen aus.

Die beiden Module schreiben diese Werte jetzt nur bei einer Änderung. Abfrage-
und Erkennungstakt bleiben gleich. Die lokale Ablaufzeit des Erkennungshinweises,
Schutz vor alten Statusmeldungen und Rücksetzung bei neuer Backend-Instanz bleiben
erhalten. Audio-, Mikrofon-, Konten- und Modellkonfiguration werden nicht geändert.

## Nachweis und Grenzen

Der [lokale Vergleich](../audio-release-0.5.54/idle-render-comparison.json) zeigt
in 30 Sekunden 33 statt 509 DOM-Beobachteraufrufe sowie 66 statt 266
Stil-Neuberechnungen. Ein wiederholter Kandidatenlauf bestätigt dieselben Zähler.
Diese Werte stammen vom instrumentierten Mac-Browser, nicht vom Pi. Sie belegen
vermeidbare Oberflächenarbeit, aber noch nicht die Ursache seines Speicheranstiegs.

Die [isolierte Vergleichsprüfung](../audio-release-0.5.54/check-idle-render-candidate.cjs)
führt 100 Zyklen mit insgesamt 1.400 Zustandsprüfungen durch: schneller
Erkennungshinweis, veraltete Vollabfrage, Verbindungsaufbau, Zuhören, Denken,
Sprechen, Schließen, Aufnahme, lokaler Test, Ablauf und neue Backend-Instanz.
Die sichtbaren Werte entsprechen jeweils dem unveränderten Stand. Zusätzlich
wird geprüft, dass der übernommene Quelltext genau dem gemessenen Kandidaten
entspricht. Die Vorversion wird dafür aus dem festen Commit `14f9dc5` gelesen.
Das ist ein VM-Test ohne Audiohardware, keine Serie echter Gespräche.

Alle **110 JavaScript-Tests auf dem Mac** bestehen, darunter neue Regressionen
für 100 unveränderte Wake-Abfragen ohne erneute Feedback-Schreibvorgänge und
unveränderte Pager-Beschriftungen mit weiterhin korrektem Beschriftungswechsel.
Die vollständige Python-Suite besteht mit **340 Tests auf dem Mac**.
[Testprotokolle: JavaScript](js-tests-mac.txt), [Python](python-tests-mac.txt),
[Zustandsvergleich](transitions.json). Die bekannte Qt-/GC-Aufräumwarnung
erscheint weiterhin; sie wird nicht als fehlgeschlagener Test ausgegeben.
Auf dem Pi ist kein Node-Testprogramm installiert; dafür wurde keine neue
Systemabhängigkeit eingerichtet.

## Bestehendes Gerät und Kunden-Image

Geändert werden `studio/device-status.js`, `studio/touch.js` und die App-Version
in `web_server.py`. Alle drei Dateien sind bereits Teil der App-Positivliste.
Keine neue Runtime, Bibliothek, Firmware, Datenmigration oder Modelle. Ein neues
SD-Image aus diesem Commit übernimmt die Dateien automatisch; das vorhandene
Image 0.5.44 wird dadurch nicht ersetzt.

Die Auslieferung erfolgt ausschließlich über das signierte App-Update mit
atomarer Wartungssperre. Aktive Aufnahmen oder Gespräche werden nicht beendet.
Der bisherige 0.5.54-Teilzeitraum muss erhalten bleiben und darf nicht mit einer
neuen Version als durchgehender 24-Stunden-Lauf zusammengerechnet werden.
Installation, Gerätestichproben und neuer Messplan werden nach ihrer tatsächlichen
Prüfung ergänzt. Bis dahin ist dieses Dokument kein Auslieferungsnachweis.
