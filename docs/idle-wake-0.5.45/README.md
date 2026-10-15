# Bereitschaft nach längerer Standzeit · 0.5.45

15. Oktober 2026. Gemeldet: mehrfaches „Hey Brain“ reagiert spät, Erkennungshinweis
bleibt stehen und die Gesprächs-Waveform fehlt.

## Befund und Korrektur

Der produktive Pi (16 GB, 0.5.43) war knapp 24 Stunden gestartet. Rund 10 GB RAM
waren verfügbar. Der Kiosk-Renderer belegte etwa 4,3 GB. Eine zehnsekündige
Leerlaufmessung ergab 143,8 % eines CPU-Kerns und +13,59 MB RSS. Eine frisch
geöffnete Oberfläche am gleichen Backend zeigte diesen Zustand nicht.
Die genaue Ursache der langfristigen Chromium-Speicherentwicklung ist damit
noch nicht isoliert; ein kurzer Nachtest beweist keine Dauerstabilität.

Im Code bestätigt: Wake-Start erneuerte über `reserve → _binding → session`
ein abgelaufenes Microsoft-Token innerhalb der Live- und App-Steuerungssperren.
Zusätzlich wartete der öffentliche Kontostatus auf dieselbe Netzwerksperre.
Ein langsamer Refresh konnte somit Statuspolls und Pegelanzeigen verzögern.
Wake reserviert jetzt sofort anhand der bereits gespeicherten Kontobindung.
Die erste authentifizierte Anfrage im Hintergrund prüft/erneuert weiterhin das
Token und bestätigt die Bereiche, bevor eine Cloud-Sitzung eröffnet wird.
Der Kontostatus liest nur den atomar gespeicherten Stand. Keine Berechtigung
wird durch diese Anzeigeprüfung ersetzt oder umgangen.

Die Erkannt-Meldung läuft zusätzlich im Browser nach spätestens acht Sekunden ab.
Derselbe Erkennungszähler kann sie durch verspätete Statusantworten nicht erneut
verlängern. Sobald das Gespräch läuft bzw. beendet ist, verschwindet sie.
Die Waveform bleibt an echte Python-Pegel gebunden. Unveränderte Icons werden
nicht jedes Mal neu angefordert; der schnelle Pegelpoll schreibt unveränderte
Button-Sperren nicht wieder in den DOM. Technische Startphasen werden ohne
Kontodaten, Tokens oder Gesprächsinhalte protokolliert.

## Hilfe direkt am Gerät

**Einstellungen → Gerät & Verwaltung:**

- **Oberfläche neu laden** sichert offene Entwürfe und lädt die Webseite neu.
  Während Aufnahme/Gespräch gesperrt; beendet kein Gespräch im Hintergrund.
- **Pi neu starten** zeigt zunächst eine Erklärung. Erst der zweite Tipp auf
  **Jetzt neu starten** fordert den geordneten Neustart an.

Der Server prüft CSRF, Bestätigung und dieselbe Wartungssperre wie die
Geräteverwaltung. Aufnahme, Pause, Gespräch, Verarbeitung, Tests, Übertragung,
Wiedergabe sowie geplante/fällige Timer verhindern den Neustart. Eine abgewiesene
Aktion wird nicht später automatisch ausgeführt. Die vorhandene eng begrenzte
Neustartberechtigung wird geprüft, nicht erweitert. Der kurze Wartungsmarker
gilt nur für dieselbe Linux-Bootkennung und blockiert den nächsten Start nicht.
Der eigentliche Hardware-Neustart wurde für diesen Test nicht ausgelöst.

## Prüfungen

264 Python-Tests auf dem Pi bestanden, in getrennten Testdaten. 104 JavaScript-
Tests bestanden. Neue Regressionen prüfen hängenden Token-Refresh bei weiterhin
lesbarem Status, sofortige Wake-Reservierung und Ablehnung einer zweiten
Reservierung, selbständig ablaufendes Erkennungsfeedback, Neustartbestätigung,
Aktivitätssperren, Bootwechsel und fehlerhafte Neustartvorbereitung.

Echte Vosk-Erkennung, native WebRTC-Verbindung und CDB-Staging wurden mit
künstlicher Sprache und ausschließlich `staging_playground` geprüft. Das echte
Mikrofon und der Lautsprecher werden dabei nicht verwendet; die produktive
Anmeldung und Einstellungen werden nicht verändert. In der ersten Serie kamen
3/3 kurze Hallo-Begrüßungen nach 5,21–6,19 Sekunden ab Beginn des Aktivierungsworts,
mit jeweils genau einer Erkennung sowie positiven Eingangs- und Ausgangspegeln.
Die erste Runde erneuerte absichtlich ein abgelaufenes Token in einer privaten
Testkopie. Die sofortige Reservierung dauerte 0,10–0,12 ms.

Der Ende-Befehl bestand in dieser Serie nur 2/3 Mal. Eine Wiederholung mit längerem
Abstand zur Begrüßung zeigte als konkreten ASR-Fehler „Ich beenden“. Diese Form
wird absichtlich nicht zu einem allgemeinen Abschaltbefehl erweitert.
Die zweite Serie hatte erneut 3/3 Erkennungen, Begrüßungen und beide Pegel,
aber nur 1/3 korrekte Ende-Transkriptionen. Der weitere Fehltext lautete
„Sprich mit den“. Die Begrüßungszeiten lagen dort bei 5,35–15,93 Sekunden;
Cloud-Latenz bleibt variabel. [Zweite Serie](repeated-synthetic-cycles.json). Die Serie
ist deshalb kein vollständiger 3/3-Ende-Nachweis. Sie ersetzt weder einen
akustischen Test im Raum noch einen Test nach weiteren 24 Stunden.

## App-Update und Kunden-Image

Code und Oberfläche liegen vollständig in bereits freigegebenen Release-Pfaden.
Keine neuen Python-Abhängigkeiten, Modelle, Firmware oder Datenmigrationen.
Bestehende Konfiguration und Aufnahmen bleiben erhalten. Ein neues Kunden-Image
übernimmt diese Dateien automatisch aus dem jeweiligen committed Quellstand;
die bestehende enge sudo-Regel ist bereits Bestandteil der Factory-Installation.
Das fertig gebaute SD-Image 0.5.44 bleibt unverändert und enthält diese Korrekturen
noch nicht. Es wurde in diesem Auftrag kein neues SD-Image gebaut.

## Auslieferung

Signiertes App-Paket aus Commit `089ac94`, Sequenz 2, auf dem produktiven Pi
installiert. Version 0.5.45 und unveränderte Konfigurationsdateien nachgewiesen
([Deployment](deployment.json)). Kein Hardware-Neustart. Der alte Chromium-
Prozess blieb auch nach dem automatischen Seitenreload auffällig; deshalb wurde
nur der Kiosk-Browser geordnet beendet und mit demselben Profil neu gestartet.
Die Diagnose des langfristigen Browserzustands bleibt eine offene Nachprüfung.

Nach dem Browser-Neustart: 20 Sekunden Messung mit zwei Renderern, 245 MB
Renderer-RSS und 13,7 % eines CPU-Kerns. Der anschließende echte Nutzeraufruf
wurde als sofortig bestätigt. Die technische Stichprobe zeigte genau eine
Erkennung, abgelaufenes Erkannt-Feedback, positive Ein-/Ausgangspegel und
fortlaufende Audioframes. Im Log wurde das Gespräch per `voice_command` beendet.
Dies ist weiterhin kein Langzeitnachweis.

Die jetzt aktive [24-Stunden-Beobachtung und der Watchdog-Entwurf](watchdog.md)
sowie das [verbindliche Stabilitätsziel](stability-goal.md) beschreiben die
weitere Abnahme. Automatische Neustarts sind dabei noch nicht eingeschaltet.
