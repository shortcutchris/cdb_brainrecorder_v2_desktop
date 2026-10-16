# Ereignisströme an genau ein Live-Gespräch binden

Installiertes Release: **0.5.57**, signierte Sequenz **14**, auf Basis von 0.5.56.

Stand 16. Oktober 2026: **geprüft und auf dem Pi installiert**. Die vorherige
0.5.56-Beobachtung blieb während der lokalen Codeprüfung unberührt und wurde
erst nach dem kontrollierten Update archiviert. Seit 02:15:15 Uhr läuft eine
neue versionsreine Beobachtung. Keine behauptete Langzeitabnahme.

## Reproduzierter Fehler

Der HTTP-Ereignisleser prüfte bei jeder Zeile nur, ob irgendein Live-Gespräch
aktiv war. Wenn ein alter Serverstream nach dem Ende weiter Keepalives lieferte
und inzwischen ein neues Gespräch lief, las der alte Reader weiter. Die bereits
vorhandene Generation-Prüfung der Ereignisverarbeitung verhinderte zwar das
Übernehmen alter Chatereignisse, beendete aber den alten HTTP-Leser nicht.
Alte Verbindungen konnten dadurch die Lebenszeit des neuen Gesprächs übernehmen.

Der [gezielte Test vor der Korrektur](reproduction-before.txt) las nach einem
Gesprächswechsel fünf statt höchstens zwei synthetische Zeilen. Die zweite
Zeile ist der erste Leseabschluss, an dem der Wechsel festgestellt werden kann.
Das ist ein lokaler Fehlernachweis mit synthetischer HTTP-Antwort, **kein Beleg**,
dass der reale CDB-Server dieses Verhalten bereits gezeigt hat. Es erklärt auch
nicht die getrennt beobachtete Chromium-CPU-Last.

## Korrektur und Grenzen

Der Standardleser erhält die Generation seines aufrufenden Gesprächs. Er prüft
Generation, Serverhandle, Kontobindung, Kontogeneration und aktiven Zustand vor
der Anmeldungserneuerung, nach deren Rückkehr, nach dem Öffnen der Antwort und
bei jeder empfangenen Zeile. Obsolete Reader verlassen den Antwortkontext und
schließen ihre Verbindung. Ein erneut verwendeter Serverhandle genügt nicht,
um einen alten Reader gültig zu machen.

Die aktuelle Sitzung darf während `closing` weiterhin ihre letzten
Transkriptteile empfangen. Erst die tatsächliche Freigabe beziehungsweise ein
Gesprächs-/Kontowechsel macht ihren Reader ungültig. Die bestehende Prüfung vor
dem Übernehmen von Ereignissen bleibt zusätzlich erhalten. Die injizierbare
Testtransport-Schnittstelle behält ihre bisherigen drei Argumente.

Ein bereits blockierender Socket-Lesevorgang wird hier **nicht gewaltsam
unterbrochen**. Die Prüfung greift nach seiner Rückkehr; der vorhandene
35-Sekunden-Socket-Timeout bleibt unverändert. Das ist kein absolutes
35-Sekunden-Gesamtzeitlimit für eine langsam eintreffende, unvollständige Zeile.
Keine Behauptung, sämtliche Netzwerkabbruchfälle damit gelöst zu haben.

## Prüfung

Neun neue Regressionstests prüfen alte Keepalives bei wiederverwendetem Handle,
bereits obsolete Reader, verspätete Token-Erneuerung, verspätetes Öffnen,
Kontowechsel, gültige Transkripte, letzte Transkriptteile beim Beenden, die
Generation-Weitergabe und **100 aufeinanderfolgende Gesprächswechsel mit
eigenen Reader-Threads**. Jeder dieser Threads wird beendet und jede zugehörige
Antwort geschlossen; der jeweils neue Gesprächszustand bleibt aktiv.

[60 Live-Tests](live-tests.txt), einschließlich der neun neuen Fälle, bestehen
lokal. [13 Wake-/Fehler-Stresstests](wake-stress-tests.txt) bestehen ebenfalls.
Die künstlichen Wechsel sind weder 100 reale Cloud-Gespräche noch akustische
Wake-Tests. Keine echten Zugangsdaten, Lautsprecher, Mikrofone oder Netzwerkaufrufe.
Die [vollständige Python-Suite](python-tests.txt) besteht ebenfalls:
**371 Tests**, Exitcode 0, lokal mit Python 3.14.7 und Qt offscreen. Die oben
genannten Teilmengen sind darin enthalten, keine zusätzlichen unabhängigen
Tests. Der bekannte Qt-/GC-Hinweis über ein beim Prozessende nicht bereinigtes
Objekt erscheint weiterhin; er ist kein Pi-Ressourcenmesswert.
[Prüfsummen und Prüfstatus](validation.json).

Alle [neun neuen Tests auf dem Pi](pi-tests.txt) bestehen auch mit Python
3.13.5, einschließlich der 100 Reader-Wechsel. Sie liefen in einem getrennten
temporären Quellordner mit künstlichem Transport, ohne App-Neustart oder Zugriff
auf produktive Aufnahmen/Konten. [Quell- und Testprüfsummen](pi-provenance.json)
entsprechen dem lokal geprüften Code. Nach dem Versionssprung bestehen die
[51 Studio-Tests](studio-0.5.57-tests.txt) erneut auf dem Mac; sie sind eine
Teilmenge der vollständigen Suite.

## Auslieferung und Image

Die geänderten Laufzeitdateien sind `services/live_conversation.py` und der
Versionswert in `web_server.py`, beide bereits in der App-Positivliste.
Keine neue Abhängigkeit, kein
geändertes Datenformat, keine Mikrofon-/Modellkonfiguration. Ein signiertes
App-Paket kann die Korrektur auf kompatible bestehende Geräte übertragen; ein
neuer Kunden-Image-Build übernimmt den freigegebenen Quellstand automatisch.
Das bestehende SD-Image wird dadurch nicht neu gebaut oder geändert.

Vor einer Auslieferung: Tests abschließen, neue Release-Version festlegen,
Paket signieren und gegen den derzeit installierten Stand prüfen. Die atomare
Wartungssperre muss erfolgreich sein; keine aktive Aufnahme oder Unterhaltung
abbrechen. Danach Einstellungen und Runtime nachprüfen und den versionsreinen
Beobachtungszeitraum gesondert dokumentieren. Ein Quellcommit allein ist keine
Auslieferung. Das übergeordnete Stabilitätsziel bleibt offen.

## Bestätigte Installation und neuer Dauerlauf

[Signierte Auslieferung](deployment.json), Quellcommit
`37e2a6c184ece4b5211563321fbef624d2cce8f0`, Release-ID
`09a3a71bf99603cc4b43664c4f20148eb86a1aa81217ce2d7bef4060f657137e`.
Signatur, unveränderte Runtime und exakte Paketdifferenz geprüft: nur
`services/live_conversation.py` und `web_server.py`. Die atomare Wartungssperre
war erfolgreich. Die zuvor erfassten Konfigurationsprüfsummen stimmen nach dem
Update überein; Okay KAI bleibt ausgewählt. Kein Browser-/Pi-Neustart, keine
neue Modell-, Audio- oder Firmwarekonfiguration. Der Backend-Neustart gehört
zum App-Update.

[18 Stichproben](installation-check.json) über etwa 36 Sekunden bestätigen
API-/ausgelieferte HTML-Version 0.5.57, genau einen unveränderten hörbereiten
Wake-Kindprozess und passende installierte Quellprüfsummen. Das
[echte Display](display-after.png) zeigt die freie Startseite und Bereitschaft
für Okay KAI. Es belegt keine erfolgreiche Erkennung oder intern ausgeführte
JavaScript-Version; kein akustischer Test wurde gestartet.

Der [neue Messplan](observation-plan.json) reicht von **16.10.2026, 02:15:15**
bis **17.10.2026, 02:15:15 Europe/Berlin**. Beobachter **1488318** wurde als
aktiver Prozess geprüft. Der Beobachtercode und seine Ruhezeitevidenz Revision 2
bleiben unverändert; keine automatische Reparatur. Die bestehende Nachprüfung
läuft alle 15 Minuten, höchstens bis 17.10.2026, 03:45:15 Uhr; unveränderte
Zwischenstände bleiben ohne Benachrichtigung. Bei belegter Acht-Stunden-Ruhe
soll tagsüber einmal um einen natürlichen Ruf gebeten werden, sofern er fehlt.

Die [0.5.56-Teilmessung](previous-partial-observation.json) umfasst rund
22 Minuten und 88 Ressourcenstichproben einschließlich des kontrollierten
Versionswechsels. Sie liegt auf dem Pi unter
`baseline-056-before-live-event-scope-fix`. Der Schlüsselbund-Eingriff und die
zusätzlichen Diagnoseintervalle bleiben markiert. Kein Langzeit-Wake, kein
24-Stunden-Erfolg; alte und neue Zeitfenster werden nicht zusammengezählt.
Die Auswertung endet am aufgezeichneten Ablösezeitpunkt, nicht an späterer
Wanduhrzeit. Die verbleibende Chromium-Last und die akustische Langzeitabnahme
sind weiterhin offen.
