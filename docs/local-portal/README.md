# Vorschlag: cdbPiOS Hilfe und Fernbedienung im lokalen Netz

Stand: 23.11.2026. Anlass: Nutzer wünscht eine vollständige Hilfe direkt auf
dem Pi und erwägt die Bedienung des Pi über einen Browser im gleichen Netz.
**Konzept zur Besprechung; noch keine neue Weboberfläche oder Fernsteuerung
implementiert, kein Netzwerkzugang am Gerät verändert.**

Die [Anmeldeidee ohne Abtippen](../cdb-integration/deferred-qr-login.md)
bleibt ausdrücklich zurückgestellt.

## Was der aktuelle Code bereits kann

| Bestand | Beleg und Grenze |
| --- | --- |
| Python-Webserver mit Kiosk-Oberfläche | `web_server.py`: `StudioServer` erlaubt ausschließlich `127.0.0.1`; Standardport 8088. Kein frei erreichbares LAN-Bedienpanel. |
| Optionaler Browser-Empfänger | `services/remote_display.py`, `studio/receiver/`: Port 8090, nach Einschalten und Kopplung aktuelles Gespräch nur lesend; HTTP im vertrauten LAN. Keine Steuerrechte. |
| Interne Fernsteuerungslogik | `services/remote_control.py`, `services/remote_control_transport.py`: CDB-Kanal für persönliche Mobile-Steuerung. Letzter dokumentierter Verbundstand hat offene Server-/Mobile-Abnahme; kein Nachweis aktueller Verfügbarkeit durch diese Prüfung. |
| Geräteverwaltung | Diagnose, signierte Updates und feste Wartungsaktionen über einen separaten Verwaltungsdienst; keine allgemeine persönliche Fernbedienung. |

Architektur und Grenzen: [Übersicht](../architecture/README.md),
[Mobile-Implementierung](../remote-control/IMPLEMENTATION-63.md).

## Vorgeschlagener Einstieg

Am Pi erscheint **Hilfe & Fernzugriff** mit der tatsächlichen Geräteadresse
und einem QR-Code. Nach Öffnen auf Laptop, Tablet oder Handy gibt es drei
klar benannte Bereiche: **Hilfe**, **Gerätestatus**, **Fernbedienung**.

Die Adresse verwendet den individuellen Gerätenamen; eine aktuelle IP-Adresse
dient als Alternative, falls die Namensauflösung im Netz nicht funktioniert.
Hostname, Port und HTTPS-Zugang sind vor Umsetzung festzulegen und zu testen.
Es gibt noch keinen neuen aufrufbaren Hilfe-Link.

Die Hilfe liegt vollständig auf dem Gerät: Texte, Bilder, Suche und nötige
Schriften benötigen kein Internet. Pi und Browser müssen dasselbe erreichbare
lokale Netz nutzen; ein getrenntes Gast-WLAN kann den Zugang verhindern.
Die Hilfeseiten passen sich auch kleinen Handybildschirmen an. Das eigentliche
Pi-Bedienpanel bleibt für 1280 × 720 und 1024 × 600 mit Touch ausgelegt.

## Inhalt der vollständigen Hilfe

- Erste Schritte: Aufbau, Verkabelung, Stromversorgung, Einschalten, Netzwerk,
  Brain-Anmeldung und Gerätezuordnung. Hardware-Anleitungen aus den jeweiligen
  Projekten übernehmen und gegen den tatsächlichen Aufbau prüfen.
- Talk: Wissen auswählen, Gespräch beginnen/beenden, Mikrofon stummschalten,
  Aktivierungswort und Bedeutung der Statusanzeigen.
- Meeting: Aufnahme beginnen, pausieren, stoppen, Notizen sichern;
  lokale bzw. CDB-Verarbeitung, Warteschlange, Transkript und Zusammenfassung.
- Geteiltes Gerät: Anmeldung erforderlich, NFC-Verhalten, Abschluss/Abmeldung,
  Ruhefrist und optionale Raumgeräuscherkennung ohne Speicherung.
- Alltag: Lautsprecher und Mikrofon, WLAN-Wechsel, sauber herunterfahren,
  Umstellen, Start-/Abschiedsklang sowie Bedeutung der lokalen/offline Funktionen.
- Hilfe bei Problemen: kein Ton, keine Aufnahme, Anmeldung fehlgeschlagen,
  Verarbeitung wartet, Netzwerk nicht erreichbar; verständliche erste Schritte.
- Betreiberbereich: Diagnose, Version, Aktualisierung, Gerätekopplung,
  Berechtigungen und Rücknahme einer Browser-Freigabe.

Versionsstand sichtbar machen; Hilfe mit jeder Funktionsänderung aktualisieren
und zusammen mit der passenden App-Version ausliefern. Generische Hilfe kann
ohne Brain-Anmeldung lesbar sein; sie enthält keine persönlichen Gerätedaten,
Aufnahmen, Kontonamen oder Zugangsdaten.

## Fernbedienung als zweiter Schritt

Der Browser stellt eine Kopplungsanfrage. Am Pi wird das konkrete Gerät mit
einem kurzlebigen Code bestätigt. Eine Browser-Freigabe ist getrennt von der
Brain-Anmeldung und erlaubt keine Gastaufnahme. Sie gilt nur für die aktuelle
berechtigte Pi-Sitzung; Abmeldung, Kontowechsel, Widerruf und Neustart machen
sie ungültig. Bereits lesend gekoppelte Empfänger erhalten keine Steuerrechte.

Erster vorgeschlagener Umfang: tatsächlichen Aufnahme-/Gesprächsstatus sehen,
Aufnahme starten/pausieren/stoppen, Gespräch starten/beenden und stummschalten.
Mikrofon und Lautsprecher bleiben am Pi; kein Audio vom Browser und kein
automatischer Zugriff auf die Aufnahmebibliothek. Warteschlangenstatus nur
kontogebunden und ohne fremde Titel oder Inhalte anzeigen.

Pi-Touch und Browser bedienen dieselben Python-Aktionen. Die vorhandenen
Kontoprüfungen und Aktivitätssperren gelten auch dort. Ein ausdrückliches
Stoppen beendet nur die zugehörige aktuelle Sitzung. Doppelklicks, verspätete
Aufträge und parallele Bedienung dürfen keine zweite Aufnahme erzeugen oder
eine inzwischen andere Sitzung beenden. Erfolg erst nach Bestätigung des Pi.

Bei Verbindungsabbruch läuft eine bestehende Aufnahme am Pi weiter; der Browser
kennzeichnet seinen Status als veraltet und holt ihn nach Wiederverbindung neu.
Eine offen gelassene Browserseite oder ihr Heartbeat hält die Anmeldung nicht
künstlich offen. Die bestehenden Regeln für laufende Meetings bleiben erhalten.

Wartung, Neustart und Herunterfahren wären ein gesonderter Betreiberbereich
mit eigener Freigabe und Bestätigung. Die vorhandenen Sperren bei laufenden
Arbeiten bleiben wirksam. Kein beliebiger Desktop- oder Shell-Zugang.

## Technische Leitplanken für die Umsetzung

- Den Kiosk-Dienst auf 8088 nicht einfach für alle Netzwerkschnittstellen öffnen
  und nicht seine komplette API oder `/api/state` an das LAN durchreichen.
- Eigenen begrenzten Zugang für Hilfe und gekoppelte Befehle entwerfen. Bestehende
  Aktionslogik wiederverwenden; keine zweite Aufnahme-Engine und keine ungeprüften
  angeblich bereits authentifizierten Aufträge an die interne Steuerung übergeben.
- Für schreibenden Zugriff vor Freigabe einen funktionierenden verschlüsselten
  Zugang einschließlich Zertifikats-/Vertrauensmodell festlegen. Die bestehende
  HTTP-Anzeige allein ist dafür nicht ausreichend. Offline-Nutzung und Zugriff
  vom Handy müssen damit vereinbar sein; kein stillschweigender Cloud-Zwang.
- Eigene zeitlich begrenzte Browser-Sitzungen mit Widerruf, begrenzten
  Kopplungsversuchen sowie Herkunfts-, Host- und CSRF-Prüfungen. Keine Tokens in
  URLs, Logs oder Hilfedateien. Keine Router-Portfreigabe ins öffentliche Internet.

## Sinnvolle Reihenfolge und Abnahme

1. Hilfeportal mit bebilderten Abläufen, lokaler Suche, Adresse/QR am Pi und
   eindeutiger App-Version. Keine Steuer-API in dieser ersten Stufe öffnen.
2. Geschützten Status und gekoppelte Fernbedienung nach abgestimmtem Umfang
   ergänzen; optional später Betreiberfunktionen.
3. Offline-Hilfe, mehrere Geräte im Netz, unbekannten/abgelaufenen Browser,
   Konto-/Umgebungswechsel, parallele Pi-/Browser-Aktionen, Verbindungsabbruch
   und Wiederverbindung prüfen. Laufende Aufnahme darf nicht verloren gehen.

Dieses Konzept ändert keine App-Datei, Freigabe oder SD-Image-Konfiguration.
Bei Umsetzung müssen Hilfe-Assets in die App-/Image-Positivliste, bestehende
Geräte und frische Images denselben Umfang erhalten und neue Netzwerk-/HTTPS-
Einrichtung gegebenenfalls als eigene Systemmigration getestet werden.
Hilfedaten sind versioniert; persönliche Kopplungen gehören nie ins Image.
