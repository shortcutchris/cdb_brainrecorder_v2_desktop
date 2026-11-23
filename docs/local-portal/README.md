# cdbPiOS – Hilfe und Fernbedienung im lokalen Netz

Stand: 23.11.2026, App **0.5.94**. Umsetzung im Repository; aktuelle
Auslieferungsabnahme siehe [Prüfprotokoll](acceptance-0.5.94.md).
Die [Anmeldeidee ohne Abtippen](../cdb-integration/deferred-qr-login.md)
bleibt zurückgestellt.

## Benutzen

1. Am Pi **Einstellungen → Hilfe & Fernzugriff** öffnen. Dort stehen die
   individuelle Adresse, alternative IP-Adressen und ein QR-Code.
2. Handy, Tablet oder Laptop mit demselben erreichbaren Netz verbinden und die
   Adresse öffnen: `http://<Gerätename>.local:8091/`. Gastnetze können den Zugriff
   sperren. Bei fehlender Namensauflösung die angezeigte IP verwenden.
3. Hilfe, Suche, Bilder und die komplette Verkabelungs-PDF sind ohne Anmeldung
   und Internet verfügbar. „Hilfe auf diesem Pi lesen“ öffnet dieselben Inhalte
   lokal mit Bildschirmtastatur. „Zurück zum Recorder“ kehrt zur Bedienung zurück.
4. Für Steuerung am Pi **Fernbedienung einschalten**. Im Browser **Status &
   Fernbedienung → Verschlüsselten Zugang öffnen** wählen.
5. Das geräteeigene Zertifikat zuerst vergleichen (unten). Danach am Pi beim
   Brain anmelden, im Browser einen Namen und Kopplungscode anfordern. Den
   sechsstelligen Code innerhalb von zwei Minuten am Pi eingeben und bestätigen.
6. Große Tasten steuern Meeting-Aufnahme, Pause, Fortsetzen, Stummschaltung und
   Stoppen sowie Talk-Start, Ende und Stummschaltung. Talk verwendet die zuvor
   auf dem Pi ausgewählten Wissensbereiche. Ton kommt weiterhin ausschließlich
   vom Mikrofon und Lautsprecher des Pi.

Abmeldung/Kontowechsel, Neustart, „Browser entkoppeln“ oder Ausschalten der
Fernbedienung widerrufen Freigaben. Nach zwei Stunden endet eine Freigabe auch
bei offenem Browser; nach zehn Minuten ohne Browserkontakt ebenfalls. Eine
unterbrochene Verbindung **stoppt keine Aufnahme**. Browserabfragen verlängern
nicht die Anmelde-Ruhefrist am Pi. Eine echte Bedienaktion zählt als Aktivität.
Keine Gastaufnahme und kein Herunterfahren/Neustarten über dieses Bedienpanel.

## Zertifikat einmal richtig prüfen

Die Steuerung verwendet HTTPS auf **8443**, mit einem ausschließlich auf diesem
Pi erzeugten Zertifikat. Deshalb kennt der Browser dessen Aussteller beim
allerersten Besuch nicht. Unter **Zertifikat dieses Pi vergleichen** zeigt der
Pi den SHA-256-Fingerabdruck. Im Zertifikatsdialog des Browsers denselben
Fingerabdruck prüfen und nur dieses konkrete Zertifikat zulassen. Keine globale
Abschaltung der Zertifikatsprüfung oder Browsersicherheit vornehmen.

Die öffentliche HTTP-Hilfe ist keine Vertrauensquelle für den Fingerabdruck;
der Vergleich erfolgt direkt am Pi. In verwalteten Firmennetzen sollte die IT
das gerätespezifische Zertifikat vertrauenswürdig hinterlegen. Kann der Browser
keine geprüfte Ausnahme zulassen, bleibt die Hilfe nutzbar; die Fernbedienung
wird nicht auf unverschlüsseltes HTTP zurückgestuft.

Hostname bevorzugen. Die bei der ersten Aktivierung bekannten IP-Adressen sind
zusätzlich im Zertifikat enthalten. Nach einem Netzwechsel kann sich eine IP
ändern; dann den Hostnamen verwenden. Die Adresse im Pi-Menü wird beim App-Start
ermittelt. Keine Router-Portfreigabe und kein öffentlicher Internetzugang nötig.

## Hilfeinhalte und Pflege

16 Themen: Einstieg, Verkabelung, Anmeldung, Talk, Meeting, Verarbeitung,
Bibliothek, NFC, Audio, automatische Abmeldung, Netz/Umstellen, Fernbedienung,
Zertifikat, Fehlerhilfe, Betreiber und Quellen. Texte und Zeichnungen liegen in
`studio/help/`; keine Webfonts oder externen Skripte. Suche arbeitet lokal.
Alle Hilfethemen lassen sich auch über den Browser drucken.

Die originale **Verkabelungsanleitung R2 vom 27.10.2026** wurde bytegleich aus
`pi-studio-files-public/docs/pi-studio/reviews/2026-10-27-wiring` übernommen.
Dateiname und SHA-256 stehen in `studio/help/downloads.json`. Das Portal prüft
sie beim Dekodieren und liefert sie als `verkabelung-r2.pdf` aus. Die historische
Anleitung kennzeichnet offene Kabeltests weiterhin als offen; der spätere
Soundbar-Stand vom 12.11. ist im Audioartikel gesondert erläutert. Keine
automatische Änderung der funktionierenden PCIe-/Audio-/GPIO-Konfiguration.

Bei Funktionsänderungen Artikel, Suchbegriffe, Quellen/Stand, Anleitung und
Tests im selben Release aktualisieren. Aktuelle Geräte-/Benutzerdaten gehören
nicht in die öffentliche Hilfe. Das separate Pi Studio bleibt die CAD- und
Druckdateianwendung.

## Umsetzung und Grenzen

- Kiosk/API bleiben ausschließlich auf `127.0.0.1:8088`. Die bisherige lesende
  Bildschirmfreigabe 8090 und der CDB-Steuerkanal sind eigenständige Funktionen.
- `services/local_portal.py`: begrenzte HTTP-Hilfe und optionaler TLS-Listener.
  Nur private IPv4-Absender und passende lokale Hosts; keine Durchleitung der
  Kiosk-API, Bibliothek, Audiodateien, Transkripte, Accountnamen oder Tokens.
- Cookies `Secure`, `HttpOnly`, `SameSite=Strict`, `__Host-`-Präfix;
  schreibende Anfragen zusätzlich exakte Origin, CSRF und begrenztes JSON.
  Strenge Ressourcenrichtlinie, kein Einbetten, keine Browser-Audiofreigabe.
- Kopplung und Befehle unter gemeinsamem Studio-Steuerlock. Bindung an Konto,
  Anmeldegeneration und Raumsitzung. Start erhält nach eventuell langsamer
  Mikrofonfreigabe nochmals Ablauf-/Kontoprüfung.
- Zustandsgebundene Tickets gelten 15 Sekunden nach Serveruhr. Auch ein lokales
  Pause/Weiter oder Stumm/An mit gleichem Endzustand macht alte Aufträge ungültig.
  Ein alter Stop-Auftrag darf keine inzwischen neue Aufnahme beenden.
- Auftragskennung und Ergebnis werden vor Ausführung im Arbeitsspeicher
  vermerkt. Duplikate führen nichts erneut aus, veränderte Duplikate scheitern.
  Nach Neustart sind alle Sitzungen widerrufen. Der Browser wiederholt einen
  unklaren Auftrag nie automatisch, sondern fragt den tatsächlichen Status ab.
- Aufnahmebefehle laufen auf dem bestehenden langlebigen Aufnahme-Thread;
  das Ende einer HTTP-Anfrage beendet nicht den Audioprozess.
- Rate-Limits, maximal acht Freigaben/Anfragen, maximal 20 parallele Verbindungen,
  begrenzte Requestgrößen und Verbindungs-Timeouts. Keine allgemeine Shell,
  Dateiverwaltung, Fernwartung oder Desktopfreigabe.
- Zertifikat und privater Schlüssel unter `local-portal/` im Datenverzeichnis;
  Zugriffsrechte 0600. Einstellungen werden gespeichert, Sitzungen/Codes nicht.
  Bei TLS-Startfehlern bleibt die lokale Gerätebedienung verfügbar.

## Update und frisches Image

App-Dateien einschließlich Offline-PDF sind von den **bestehenden** Release-
und Image-Positivlisten abgedeckt. Die PDF liegt als JSON-Nutzlast vor, da der
bereits installierte Update-Prüfer keine freien PDF-Dateien zulässt. Kein
Austausch des Prüfers oder nachträgliches Aufweichen seiner Regeln nötig.
Die vorhandene `cryptography`-Abhängigkeit der Audio-Laufzeit genügt. QR-Code:
vendorte MIT-Bibliothek Nayuki; genaue Herkunft in `services/vendor/README.md`.

Bei frischer Installation startet nur die öffentliche Hilfe. Steuerung bleibt
bis zur bewussten Aktivierung aus. Jedes Gerät erzeugt seinen eigenen Schlüssel;
Kundenprofile, Schlüssel und Sitzungen sind keine Build-Eingaben.
Ein geprüftes Baupaket ist **kein gebautes oder hardwaregetestetes SD-Image**.
