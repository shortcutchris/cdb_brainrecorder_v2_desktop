# Version 1 – Endabnahme

Stand: 24. November 2026. **Abnahme läuft; noch keine endgültige Freigabe.**
Kandidat: `1.0.0-rc1`. Bestehendes Gehäuse-Gerät: `0.5.105` vor Beginn der Abnahme.

## Vorgehen

1. Vollständige Python-/JavaScript-Regression und LCD-Protokolltests.
2. Alle Hauptansichten, Einstellungen und Dialoge mit synthetischem Konto bei
   1280×720 und 1024×600 prüfen; Tastatur, große Aktionen, Statuswechsel und
   gegenseitige Aktionssperren erfassen. Eine solche Prüfung ist keine
   Hardware- oder Cloudabnahme.
3. Tatsächlicher Pi: Aufnahme, Pause, lokale Verarbeitung, Timer/Alarme,
   Audiogeräte, NFC, Konto/Raummodus, Neustart und Zusatzdisplay prüfen.
4. Sauberes, signiertes App-Paket und frisches Offline-Image aus dem
   festgehaltenen Quellcommit erstellen. Keine Kundendaten, Konten oder
   Geräteschlüssel aus dem laufenden Gerät kopieren.
5. Export offline prüfen. Danach Erststart mit der vom Benutzer bestätigten
   zweiten SD-Karte (mindestens 32 GB). Die bisherige Installation bleibt erhalten.

## Bisherige Befunde und Korrekturen

- Das Image lieferte den LCD-Code, aber keinen aktivierten Begleitdienst und
  keine serielle Laufzeit. Factory-Einrichtung ergänzt; normale App-Updates
  installieren keine OS-Komponenten.
- PC/SC wird im Image ausdrücklich über seinen Socket aktiviert.
- Opt-in-Profil für die vorhandene PCIe-USB-Platine ergänzt: PCIe aktiv,
  Reset-Verzögerung 100 ms, Gen 1. Ausschließlich in frischem Factory-Root;
  widersprüchliche vorhandene Profile werden abgelehnt.
- Fernbedienungs-Tests erhielten die im echten Studio vorhandene
  USB-Wiederherstellungsinstanz. Sie prüfen jetzt zusätzlich, dass diese
  Wartungsaktion einen Gesprächsstart blockiert.

## Offene Freigabepunkte

- Sporadischer Ausfall des VIA-USB-Controllers ist weiterhin nicht abschließend
  erklärt. Zwei vorherige Timer-Belastungsläufe bestanden und wurden vom Nutzer
  hörbar bestätigt; ein USB-Neubinden hatte den ausgefallenen Controller nicht
  wiederhergestellt, ein Neustart schon. Nicht als dauerhaft behoben behandeln.
- Aktuelles Geräteprofil enthält kein aktiviertes Sprachansagen-Paket. Diesen
  Zustand von normalen Alarm- und Startklängen unterscheiden.
- Image-Build, Offlineprüfung, echter Erststart und aktuelle Sicht-/Funktions-
  abnahme werden nach ihrer Durchführung mit Nachweisen ergänzt.

Private Bilder und Rohprotokolle bleiben außerhalb Git unter dem Arbeitsordner
`output/v1-acceptance-20261124/`; hier werden nur bereinigte Ergebnisse abgelegt.
