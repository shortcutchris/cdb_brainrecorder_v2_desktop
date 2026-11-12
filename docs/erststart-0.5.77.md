# Recorder Studio einrichten

Bei einem neuen Factory-Profil startet der Assistent beim ersten Einschalten. Der Pi speichert den zuletzt geöffneten Einrichtungsschritt. Auf eingerichteten Geräten öffnet **Einstellungen → Recorder-Einrichtung → Einrichtungsassistent öffnen** denselben Ablauf. **Geräteverwaltung → WLAN & Einrichtung** öffnet weiterhin nur die Netzwerkeinstellungen.

1. **Netzwerk prüfen.** Bei verbundenem Ethernet oder WLAN kannst du gleich weitergehen. Ohne Verbindung sucht der Assistent nach WLANs. Wähle dein Netz, gib den Schlüssel ein und warte auf die Bestätigung. Ein Netzwerkkabel ermöglicht auch den Einstieg ohne WLAN. Der Assistent zeigt den erkannten Internetstatus separat an. Ohne Internet kannst du Downloads und Anmeldung später nachholen.
2. **Gerät koppeln.** Gib den Verwaltungscode deiner Organisation ein oder wähle „Vorerst ohne Geräteverwaltung einrichten“. Der Code verbindet das Gerät mit dem Geräteportal.
3. **Lokale Modelle laden.** Whisper Medium transkribiert, Qwen3 4B Instruct fasst zusammen. Der Assistent zeigt die Downloadgröße und erkennt installierte Modelle. Jeder Download beginnt mit einem eigenen Tastendruck. Bei Ollama zeigt der Balken den aktuellen Modellabschnitt. Warte auf den Abschluss, bevor du das zweite Modell lädst. Test und Auswahl anderer Modelle findest du unter **KI & Modelle**. Überspringen und erneutes Öffnen behalten die bisherigen Modelleinstellungen bei.
4. **Persönlich beim Brain anmelden.** Prüfe die angezeigte Umgebung. Öffne die Microsoft-Anmeldung per QR-Code am Handy und gib den angezeigten Gerätecode ein. Der Pi zeigt die Bestätigung im Assistenten an. Ein aktiver Anmeldeversuch lässt sich abbrechen. Für den lokalen Betrieb kannst du den Schritt überspringen.
5. **Recorder-Einrichtung öffnen.** Prüfe die angezeigten Voraussetzungen, starte bei Bedarf den fünfsekündigen Mikrofontest und höre das Ergebnis an. Sind alle Pflichtpunkte bereit, tippe auf **Einrichtung abschließen**. Der Übergang vom Assistenten zu dieser Checkliste erteilt für sich genommen keine Aufnahmefreigabe.

## Audit des Gehäuse-Pi am 12. November 2026

Beobachtet auf Recorder Studio 0.5.76, Commit `4d92dce4`. Die unten beschriebene neue Assistentenversion wurde mit getrenntem Profil getestet. Betriebsdaten, Gerätekopplungen und bestehende WLAN-Verbindungen des Pi wurden beim Audit nicht verändert.

| Bereich | Befund und offener Schritt |
| --- | --- |
| Quellstand | Vor Beginn des Audits waren alle 14 sichtbaren Remote-Featurebranches in der Historie von `main`; kein offener PR. Der USB-Timer kam über #16 in den damaligen Gerätebranch und über #18 auf `main`. |
| Aufnahme und Audio | Alle fünf Softwareprüfungen waren erfüllt. Die Aufnahme blieb bis zum ausdrücklichen Abschluss der Recorder-Einrichtung gesperrt. Das USB-Array und die 188A-Soundbar wurden erkannt. Für die Soundbar liegt die frühere Hörbestätigung vor. |
| ReSpeaker-Lichtring | Die App meldete einen Steuerungsfehler. PyUSB war installiert, dem Recorder-Benutzer fehlte der Schreibzugriff auf das passende USB-Gerät `2886:001a`. Für die Inbetriebnahme udev-Regel und Gruppenzugehörigkeit prüfen und anschließend die Statusfarben testen. [ReSpeaker](respeaker.md) |
| USB-Timerdisplay | Begleitdienst geladen, aktiviert und aktiv. Die Timer-API lieferte HTTP 200. Kein USB-Gerät mit der erwarteten Produktkennung „CDB Timer Display“ sichtbar. Anzeige, Touch und Wiederanstecken bleiben am passenden Modul zu prüfen. [Hardwareabnahme](lcd-display/FIRST-START.md) |
| Ansagen und Countdown | Der Code ist integriert. Im aktuellen Recorder-Profil fehlt der Ordner für das deutsche Ansagenpaket. Feste Sprachansagen und gesprochener Countdown benötigen das geprüfte Paket und die gewünschte Aktivierung. [Ansagen einrichten](local-announcements/README.md) |
| Lokale Modelle | Für Whisper Medium und Qwen3 4B Instruct lagen erfolgreiche lokale Modellergebnisse vor. Qwen benötigte 25,4 Sekunden für den kurzen synthetischen Zusammenfassungstest. |
| Netzwerk und Brain | Ethernet und WLAN waren verbunden. Das persönliche Brain-Konto war angemeldet. Die separate Geräteverwaltung war unkonfiguriert. Der privilegierte WLAN-Einrichtungsdienst und sein Socket fehlten auf diesem Gerät. |
| Optionale Bedienung | NFC und Rufwort waren aus, die Handy-Fernbedienung ungepaart. Bluetooth meldete, dass es beim Öffnen geprüft wird. Für diese Eingaben sowie Live-Gespräche wurde beim Audit kein physischer Ende-zu-Ende-Test durchgeführt. |

## Bestandsupdate und Kundenimage

Das signierte App-Update kann die versionierten Studio- und Servicedateien übernehmen. Die neue gemeinsame Fortschrittsanzeige liegt in `studio/model-download.js`. Ein bestehendes Profil erhält durch das Update keinen erzwungenen Erststart.

Das Kundenimage-Rezept enthält den privilegierten Netzwerkdienst. Auf einem älteren Gerät ohne diesen Dienst liest der Assistent den Verbindungsstatus über NetworkManager und weist auf den fehlenden Dienst für WLAN-Änderungen hin. Die Einrichtung des Dienstes gehört auf solchen Geräten in die Systemwartung. Der Assistent installiert weder Treiber noch Firmware. Modelle, Konten und Ansagenpakete sind gerätespezifisch. Ein physischer Erststart mit neuer SD-Karte und echter WLAN-Eingabe steht für 0.5.77 aus.

### Nachprüfung am Gehäuse-Pi am 12.11.2026

Der im Audit fehlende WLAN-Dienst wurde bei freiem Recorder nachinstalliert.
Der Pi nutzt die Unit und den NetworkManager-Adapter des Kundenimages.
Der Gerätebenutzer gehört zur Gruppe `cdb-network`. Für die bereits laufende
Sitzung bekam er Zugriff auf den Dienstsocket. Recorder und Pi liefen dabei weiter.

Auf dem eingebauten Display (1280 × 720) wurde im Netzwerk-Assistenten ein
ausgestrahltes WLAN ausgewählt. Der Dialog zeigte das Passwortfeld. Zurück führte
zur WLAN-Liste. Der Test rief ausschließlich Status und Suche am Netzwerkdienst
auf. Bestehende aktive Verbindungen, gespeicherte Profil-IDs, Einrichtungsstand
und Recorder-Konfiguration stimmten vor und nach dem Test überein. Die Verbindung
mit einem neuen WLAN über „Verbinden“ gehört zum Test auf einer separaten Karte.
