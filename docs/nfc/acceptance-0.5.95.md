# Rocketek-Nachprüfung · 23.11.2026

Nutzer bestätigt die Installation des geprüften NFC-Skripts. Pakete und
PC/SC-Socket verifiziert. „Leser prüfen“ auf App 0.5.94 ausgeführt; die
Fehlermeldung über fehlende Unterstützung ist behoben. Stattdessen meldet die
App zwei Leser. Nur ein physisches USB-Gerät vorhanden, mit zwei CCID-Interfaces.
Kontaktloser Slot durch PC/SC-Namen und USB-iInterface bestätigt.

Die Auswahlkorrektur in 0.5.95 ist lokal mit 55 Prüfungen getestet. Kein Konto,
Tag oder Audioauftrag geändert. Quellcodeänderung benötigt keine neue
Laufzeit oder zusätzlichen OS-Dienst. Bestehende App-Updates und saubere
Image-Baupakete übernehmen den Reader automatisch über ihre Positivlisten.

## Auf Pi installiert und live bestätigt

Version **0.5.95**, Quellcommit `a5d3ccf60ea622843058487eef7591913c5f39fe`,
am 23.11.2026 um 17:56 MEZ im Leerlauf installiert. Alle 150 signierten Dateien
verifiziert; Aufnahmen, Einstellungen, Raummodus und aktiviertes Hilfeportal
unverändert erhalten. Studio und Kiosk neu gestartet. Sieben zusätzliche
Reader-Tests mit dem System-Python auf dem Pi bestanden.

„Leser prüfen“ anschließend über genau dieselbe App-Aktion wie der Button
aufgerufen. Drei Abfragen bei 1,1 / 2,2 / 3,3 Sekunden meldeten:

> Tag erkannt. Talk oder Meeting zuordnen.

`can_enroll=true`, `state=present`. Der aufgelegte Tag wird also tatsächlich
über die kontaktlose Schnittstelle erkannt. Talk und Meeting sind beide noch
nicht zugeordnet; NFC bleibt ausgeschaltet. Keine Kartenkennung/Hashes in
Belegen gespeichert, keine Zuordnung vorgenommen und kein Modus gestartet.

Als Nächstes die beiden unterschiedlichen Aufsteller als Talk und Meeting
anlernen und den gewünschten Ablauf im Raummodus testen. Die aktuelle Prüfung
bestätigt Lesererkennung und Tag-Erkennung, noch keinen kompletten Gesprächs-
oder Meeting-Durchlauf und keine Dauer-/Gehäuseabnahme.

Sauberes Image-Baupaket aus demselben Commit erzeugt und alle 157 Quellhashes
geprüft. Aktualisierter NFC-Reader enthalten; bereits vorhandene Factory-
Pakete unverändert. Kein neues SD-Image gebaut oder gebootet.

Belege: [Deployment](095-deployment.json), [Leser-/Tag-Prüfung](095-reader-check.json).
