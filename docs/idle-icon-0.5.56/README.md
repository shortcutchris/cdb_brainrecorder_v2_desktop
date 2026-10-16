# Unverändertes Testplayer-Symbol erhalten · 0.5.56

Am 16. Oktober 2026 als signiertes App-Update auf dem Pi installiert.

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
kein Pi-Messwert. Nach dem Versionssprung auf 0.5.56 bestehen die 51 Studio-Tests erneut
(Teilmenge der Python-Suite, keine zusätzlichen 51 unabhängigen Tests).
Weitere acht Diagnosetests verhindern die Freigabe falscher Quellstände,
defekter Bilder und unvollständiger Messungen. Die tatsächliche Prüfung von
API-/HTML-Version auf dem Pi ist nachfolgend belegt.

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

## Installation und neuer Beobachtungszeitraum

[Signierte Auslieferung](deployment.json), Sequenz **13**, Quellcommit
`db932ea4bdcd9cc3a4d60d1350c5b69163e1db83`, Release
`3c6efacbd2ecfc93d3a1d5f8ae221ddf0917be43cc3e272a0f39a7557129636c`.
Signatur, Runtime und exakter Paketunterschied wurden vorab geprüft: nur
`studio/microphone.js` und `web_server.py`. Die vorhandene Wartungssperre war
erfolgreich; Konfigurationsprüfsummen vor und nach dem Austausch stimmen überein.

[18 Geräte-Stichproben](installation-check.json) bestätigen API-/HTML-Version
0.5.56 und durchgehend genau einen unveränderten Wake-Prozess in Bereitschaft.
Installierte Dateihashes entsprechen dem getesteten Quellstand. Okay KAI bleibt
gewählt. Das ist kein akustischer Erkennungstest. Kein Testton, keine künstliche
Unterhaltung, kein Browser- oder Pi-Neustart und keine neue Audio-/Modellkonfiguration.
Der kontrollierte Backend-Neustart gehört zum signierten Update.

Der [neue 24-Stunden-Messplan](observation-plan.json) läuft von **16.10.2026, 01:53:18**
bis **17.10.2026, 01:53:18 Europe/Berlin**. Beobachterprozess **1469691**
wurde aktiv geprüft; unveränderte Evidenzrevision 2 und ausschließlich lesender
Betrieb. Automatische Browser-/Backend-/Pi-Reparatur bleibt ausgeschaltet.

Die [vorherige Teilmessung](previous-partial-observation.json) enthält rund
**3,53 Stunden** einschließlich des kontrollierten Versionswechsels, 847 gültige
Ressourcenstichproben und keinen qualifizierten Langzeit-Wake. Sie liegt auf dem
Pi unter `baseline-055-before-icon-resource-fix`. Die Auswertung endet am dort
aufgezeichneten Ablösezeitpunkt; spätere Zeit ohne laufenden alten Beobachter
wird nicht als künstliche zusätzliche Lücke ausgegeben. Rohdatei-Prüfsummen sind
beigefügt. Versionswechsel, Backend-Neustart und unterbrochene Ruhezeitevidenz
bleiben ausdrücklich prüfpflichtig; **kein bestandener 24-Stunden-Test**.

Der kurzfristige Ressourcenvergleich begründet diesen gezielten Fix. Ob der
produktive Browser damit dauerhaft stabil bleibt und ein echter Ruf nach
mindestens acht Stunden Pause zuverlässig aktiviert, ist weiterhin offen.

Die [anschließende Prüfung des echten Displays](display-check/README.md)
fand einen nativen Schlüsselbund-Dialog über der ansonsten bereiten App.
Er wurde ohne Neustart geschlossen. Dieser manuelle Eingriff und die noch
ungeklärte Herkunft müssen in die Langzeitbewertung eingehen; reine API-Werte
belegen keinen störungsfreien UI-Betrieb.
