# Prüfung 0.5.94 – 23.11.2026

## Lokaler Stand

- Python-Regression: 233 Prüfungen bestanden (Portal, Studio, Raummodus,
  Raumaktivität, Aktionssperren, Display, CDB-Fernsteuerung, Geräteklänge).
- Zusätzliche HTTPS-Aufnahme-/Parallelbedienungs-/Ablauf- und Imageprüfungen:
  82 Prüfungen bestanden; die Suite enthält erneut Studio-Basisprüfungen.
- JavaScript: 152 Prüfungen bestanden.
- Synthetischer Audioprozess schreibt nach Ende der Start-HTTP-Anfrage weiter.
  Pause/Fortsetzen/Stumm/An, Browser-Entkopplung ohne Aufnahmestopp und lokaler
  Abschluss getestet. Kein echter Raumton für diese Prüfung aufgenommen.
- Zwei gleichzeitige Browser starten nur einmal; abgelaufene Aufträge nach
  Mikrofonfreigabe starten nicht. Konto-/Sitzungswechsel und Wartung sperren.
- TLS-Verifikation mit dem eigenen Zertifikat als gezieltem Vertrauensanker
  bestanden. Browser-Vorschau nutzt ausschließlich isolierte Testdaten.
- Hilfe und Kopplungsansicht bei 1024×600 mit Bildschirmtastatur geprüft;
  1280×720 sowie Smartphone-Hilfe 390×844 ebenfalls geprüft. Kopplung,
  Start, Pause und bestätigter Stop über den Browser am synthetischen Gerät
  durchlaufen. Stabile Tasten behalten beim Statuspolling ihren Fokus.
- Abschließende gezielte Portal-/Image-Suite: 20 Prüfungen bestanden.
- Screenshots unter `output/playwright/local-portal-094/` (nur Testdaten).

## Auslieferung abgeschlossen

Am 23.11.2026 um 17:44 MEZ auf dem Recorder-Pi installiert: **0.5.94**,
Quellcommit `a624e61a324f34daff7041121621fe6185d3e989`. 150 Dateien des signierten
Pakets verifiziert. Vorheriger Stand 0.5.93 als Rückfall erhalten. Beim Update
keine Aufnahme und keine persönliche Anmeldung aktiv. Konfiguration,
Raumregeln und Aufnahmen unverändert; Wartungssperre anschließend freigegeben.
Studio und physischer Kiosk neu gestartet und aktiv. Bildschirmaufnahme zeigt
die korrekte Startseite im vorhandenen dunklen Theme.

LAN-Hilfe, Bilder, lokale Suche und vollständige PDF mit passender SHA-256
geprüft. HTTPS-Fernbedienung anschließend über die normale lokale Aktion
aktiviert. Zertifikat mit gezieltem Vertrauensanker für aktuelle LAN-IP und
`raspberrypi.local` erfolgreich geprüft. Ohne Brain-Anmeldung wird die
Kopplung zurückgewiesen; private API-/Bibliotheksrouten fehlen am HTTP-Portal.
Keine Browserfreigabe oder Testidentität auf dem produktiven Gerät angelegt.

Drei zusätzliche Tests auf dem Pi selbst bestanden: Aufnahme über HTTPS mit
künstlicher PCM-Quelle überlebt das Ende der HTTP-Anfrage, zwei Browser starten
nur einmal, private geräteeigene Schlüssel und strenge TLS-Prüfung funktionieren.
Diese Tests liefen in temporären Datenverzeichnissen auf eigenen Loopbackports,
mit eigener Testanmeldung; kein Raumton und keine produktive Aufnahme verändert.
Die persönliche Kopplung mit Chris' echtem Konto ist noch durchzuführen.

Das saubere Image-Baupaket aus demselben Commit enthält 157 Quelldateien,
einschließlich Hilfe/QR/PDF. Alle Dateihashes geprüft, keine privaten
Portaldateien übernommen. Offline-Modelle in der Baukonfiguration aktiviert.
**Kein neues SD-Image gebaut oder auf Hardware gebootet.**

Belege: [Deployment](deployment-0.5.94.json),
[Netzwerk und Pi-Prüfung](network-acceptance-0.5.94.json),
[Image-Baupaket](image-kit-0.5.94.json).

## Parallelprüfung NFC

Rocketek am USB vorhanden (`2ce3:9567`, Debian-Treiberkennung Alcor Link AK9567).
`python3-pyscard`, `pcscd` und `libccid` fehlen. Das installierte
`scripts/install-nfc.sh` stimmt mit upstream `main` Commit
`72da8b8865088b97815f102370d8b7578987197a` überein;
SHA-256 `84c5bd1a5e16e2beef04bacaec1174206f64fee8417aa864474768eeed91fe28`.
Installation versucht, jedoch von sudo wegen fehlender Passworteingabe abgelehnt.
Nutzerbefehl auf dem betreuenden Mac vorbereitet und Nutzer informiert.
**Installation und PC/SC-Erkennung noch nicht bestätigt.** Danach „Leser prüfen“
testen und bei zwei logischen CCID-Slots den kontaktlosen Leser gezielt prüfen.
Das Portal-Update installiert keine OS-NFC-Pakete und aktiviert keine Tags.

Nachtrag 23.11.2026: Installation anschließend vom Nutzer bestätigt. Die
Doppelschnittstelle des Rocketek wurde mit 0.5.95 korrigiert; Leser und
aufgelegter Tag erfolgreich geprüft. [Aktueller NFC-Stand](../nfc/acceptance-0.5.95.md).
