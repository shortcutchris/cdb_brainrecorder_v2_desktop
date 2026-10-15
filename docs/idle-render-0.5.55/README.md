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
Installation, Gerätestichproben und neuer Messplan sind nachfolgend belegt.
Vorläufe liefern keinen Nachweis eines vollständigen 24-Stunden-Tests.

## Auslieferung bestätigt

[Signiertes Update, Sequenz 12](deployment.json) aus Commit
`78687160e4acec9d05d7b144bfdf22e4b04d3c1b` ist auf dem Pi installiert.
Die vorhandene Wartungssperre war erfolgreich; gespeicherte Einstellungen
haben vorher und nachher dieselben Prüfsummen. Die Runtime blieb unverändert.
[18 Startstichproben](installation-check.json) zeigen 0.5.55 in API und HTML,
genau einen unveränderten Wake-Prozess in Bereitschaft und identische Hashes
der drei geänderten Laufzeitdateien auf Pi und getestetem Quellstand.

![Tatsächliches Touchdisplay nach der Installation](pi-home.png)

Die native Displayaufnahme zeigt die Startseite und „Bereit für Okay KAI“.
Das belegt die Anzeige, keinen akustischen Erfolg. Keine Testtöne, keine
künstlichen Gespräche und kein Wechsel von Mikrofon, Rufwort oder Brain-Konto.

Der [neue Messplan](observation-plan.json) läuft vom **15.10.2026, 22:21:44 Uhr
bis 16.10.2026, 22:21:44 Uhr Europe/Berlin**. Der tatsächliche Beobachterprozess
1272509 ist aktiv; ausschließlich lesend und weiterhin Evidenzrevision 2.
Die bestehende 15-Minuten-Nachprüfung wurde auf Version, Fenster und Frist
angepasst. Es wurde keine zweite Überwachungsautomation angelegt.

Der vorherige [0.5.54-Teilbericht](previous-partial-observation.json) umfasst
rund 85 Minuten bis zum Archivieren. Archiv auf dem Pi:
`baseline-054-before-idle-render-fix`. Der enthaltene Versionswechsel und die
Unterbrechung der Ruhezeitevidenz gehören zur kontrollierten Auslieferung;
sie werden nicht als bestandener Dauerlauf gewertet oder aus den Daten entfernt.
Die vollständige neue 24-Stunden-Messung, ein echter Ruf nach acht Stunden Ruhe
und die Einordnung des längerfristigen Speicherverlaufs bleiben offen.

## Erste zehn Minuten auf dem Pi

Der feste Abschnitt **22:21:44 bis 22:31:44 am 15.10.** hat 40 Messwerte und
99,9923 % Abdeckung. Browser-CPU: Median **25,46 % eines Kerns**, p95 26,46 %.
Die letzten 40 ruhenden 0.5.54-Stichproben vor dem Update lagen bei Median
31,83 %, p95 33,06 %. Das ist eine frühe beobachtete Entlastung, kein kontrollierter
Pi-A/B-Versuch: Backend und Oberfläche wurden beim Update neu gestartet bzw.
geladen. Die vollständige Messung bleibt erforderlich.

Lokale Gesundheitsabfrage: Median 6,67 ms, p95 96,41 ms. Der summierte RSS steigt
von 1.162,58 auf 1.173,77 MiB; **ein behobener Speicherverlust oder ein dauerhaftes
Plateau ist damit ausdrücklich nicht belegt**. Kein Wake-Ereignis in diesem
Abschnitt. [Vergleich mit Quellprüfsummen](first-ten-minute-comparison.json).
Die technischen Quelldateien sind zusätzlich außerhalb von Git gesichert.
Für diesen Zwischenbericht wurde weder die Beobachtung zurückgesetzt noch
ein weiterer Eingriff auf dem Pi vorgenommen.
