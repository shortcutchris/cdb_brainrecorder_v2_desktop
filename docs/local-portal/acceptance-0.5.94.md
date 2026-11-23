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

## Auslieferung

Noch nicht abgeschlossen. Vor Freigabe signiertes App-Paket und sauberes
Image-Baupaket erzeugen, im Leerlauf installieren, Daten-/Konfigurationserhalt
und erreichbare LAN-Hilfe prüfen. Persönliche Kopplung am echten Pi benötigt
die Anmeldung des Benutzers; eine synthetische Anmeldung gehört nicht aufs Gerät.
