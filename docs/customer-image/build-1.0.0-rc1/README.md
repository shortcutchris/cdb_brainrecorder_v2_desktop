# Recorder Studio 1.0.0-rc1 · Pi-5-Image

**Gebaut und offline geprüft am 24.11.2026. Hardware-Erststart noch offen.**

| Merkmal | Wert |
| --- | --- |
| Datei | `cdb-brain-1.0.0-rc1-pi5-offline.img.xz` |
| Komprimiert / entpackt | 5.551.114.068 / 11.651.776.512 Byte |
| SHA-256 komprimiert | `9f6ab2ea29ac449bc196b216c6ae0bd1d145e935418523bc4b6db81340977436` |
| SHA-256 entpackt | `4a7c1a04c2737b64a02677f9e5c89a9b1b3fa9629dbc2a7762de0684516d3560` |
| Quellcommit | `01d81078794942dc5255e4ab221b9e8c59a02502` |
| pi-gen | `d346cd53562b3c6b4f94c9155175f814258c456d` |
| Öffentlicher Update-Prüfschlüssel SHA-256 | `8ea3e5260389013e2f21973c3a029ba82842e03e720aa9398daa66e27dbe4590` |
| Profile | Offline-Modelle, PCIe-USB-Platine / Gen 1, DE |

Enthalten sind der Kiosk, cdbPiOS-Startbild, Erststart-Assistent, lokale Hilfe,
Whisper Medium, Qwen3 4B Instruct, NFC/PCSC, USB-Wiederherstellung und LCD-
Begleitdienst. Die Firmware auf dem Zusatzdisplay wird nicht durch das SD-Image
aktualisiert. Konten, WLAN und persönliche Gerätekopplung entstehen erst am Gerät.

## Nachweise

- Archivintegrität, FAT/ext4 und Bootdateien bestanden.
- Alle 165 Quelldateien und festgelegten Modellgewichte geprüft; Kundendaten-Audit sauber.
- App-Runtime mit PySide6, aiortc, cryptography, numpy und dbus-next importiert;
  LCD-Runtime mit pyserial 3.5 importiert. Alles im ARM64-Container ohne Netzwerk.
- Leeres Kundenprofil mit tatsächlicher Image-Initialisierung erzeugt:
  Erststart erforderlich, keine persönliche Sitzung, vorinstalliertes Whisper vorhanden.
- Die tatsächliche SD-Hardware, lokale Modellinferenz auf der neuen Karte und
  die Dienste nach einem vollständigen Boot sind noch zu prüfen.

## Auf die zweite Karte schreiben

1. Raspberry Pi Imager öffnen und **eigenes Image** wählen.
2. Obige `.img.xz` direkt auswählen; Entpacken ist nicht nötig.
3. Ausschließlich die **zweite SD-Karte ab 32 GB** als Ziel auswählen.
4. Keine gespeicherten Imager-Anpassungen für Benutzer, SSH oder WLAN übernehmen.
5. Schreiben und Verifizieren abwarten. Die bisherige Karte aufbewahren.
6. Den ausgeschalteten Pi mit der neuen Karte starten. Erststart, Anschlüsse,
   Kiosk, Timerdisplay, Ton, Aufnahme und lokale Verarbeitung prüfen.

Die Karte ist ein Testkandidat. [Offene Freigabepunkte und Gesamtprüfung](../../acceptance-v1/README.md).

Der lokale Buildordner enthält außerdem `SHA256SUMS`, `acceptance-results.json`,
`offline-audit.log`, `runtime-smoke.log`, signiertes App-Update und pi-gen-Paketlisten.
Diese großen beziehungsweise privaten Dateien werden nicht ins Git-Repository kopiert.
