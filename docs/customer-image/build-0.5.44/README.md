# Tatsächlich gebautes SD-Image · 0.5.44

**Ergebnis:** SD-Image am 14. Oktober 2026 erzeugt und offline geprüft.
Bereit für den Test auf einer zweiten Karte; **noch nicht auf einem echten Pi
gebootet und keine Serienfreigabe**. Chris' laufende Pi-Konfiguration wurde
nicht verändert, kein Update installiert und kein Neustart ausgelöst.
Nur die bestehende Displayrotation wurde lesend abgefragt.

## Dateien

Lokale Ausgabe im Repository-Arbeitsordner:

`dist/customer-image-0.5.44-sd/cdb-brain-0.5.44-pi5.img.xz`

- Komprimiert: **1.714.927.908 Byte** (1,71 GB / 1,60 GiB).
- Entpackt: **6.752.829.440 Byte** (6,75 GB / 6,29 GiB).
- Quellstand: `60a041852484124ae44eaa692ff17447243b4b61`.
- pi-gen: `d346cd53562b3c6b4f94c9155175f814258c456d`.
- SHA256 `.img.xz`:
  `26da50d4f8858a3acb20ccb51d728aa1e90d24985e3f9b80ea8a919fb20b1f92`.
- SHA256 entpacktes Image:
  `1e31e3720a2367130e028c67938f37b4ae6e8feb8a7eaa4d6ec4c8c4c4ef3ce6`.

Das große Image liegt bewusst außerhalb der Git-Historie unter `dist/`.
Versioniert sind Bauanleitung, Programme, Architektur, Input-Manifest und
Prüfergebnisse. Das Image muss separat gesichert/verteilt werden; ein Git-Klon
enthält die Anleitung zum erneuten Bau, nicht diese Binärdatei.

[Manifest der Build-Inputs](build-manifest.json) ·
[Abnahme als JSON](acceptance.json) · [Prüfsumme](SHA256SUMS) ·
[OS-Pakete](os-packages.txt) · [Python-Pakete](python-packages.txt) ·
[Offlineprüfung](offline-audit.txt)

Das `status`-Feld im Input-Manifest bezeichnet den Zustand bei Erstellung des
Baupakets. Der tatsächliche Ergebnisstatus steht in `acceptance.json`.

## Build und Korrekturen

Dedizierte ARM64-Docker-Umgebung auf dem Mac, aus frischem Raspberry Pi OS
Trixie. Der erste Erprobungslauf deckte den fehlenden Python-Interpreter im
pi-gen-Buildcontainer auf; außerdem wurden die CPU-Zielarchitektur von Whisper,
Schreibrechte des neuen Profils und der explizite Wayland-Start korrigiert.
Der endgültige Lauf verwendete erneut eine frische OS-Basis. Die ergänzte
Factory-Initialisierung für das DSI-Querformat und die Quellmetadaten wurden
vor dem Export aus dem sauberen Commit `60a0418` übernommen. **Alle 132
bereitgestellten App-/Factory-Inputs wurden anschließend gegen dessen Build-Manifest
geprüft**, statt den Zwischenstand des Erprobungslaufs auszuliefern.

Whisper ist mit `-march=armv8.2-a+dotprod`, deaktivierter Host-CPU-Erkennung
und drei Build-Threads erstellt. Audio-/Bluetooth-, Pulse-Kompatibilitäts- und
Wayland-Abhängigkeiten sind explizit installiert. Der Desktop wartet auf die
Factory-Initialisierung. Ein frisches Touch-Display-2-Profil verwendet 90 Grad
Rotation an DSI-1 beziehungsweise DSI-2; vorhandene Profile bleiben bestehen.

## Nachweise

- 258 Python-Tests bestanden, abschließender Lauf 61,394 Sekunden in der
  isolierten ARM64-Image-Runtime. Für historische Qt-Tests wurden zusätzliche
  Testquellen nur in den wegwerfbaren Prüfbaum kopiert, nicht ins SD-Image.
- 100 JavaScript-Tests bestanden. Die neuen Build-/Audit-Skripte sind syntaktisch
  geprüft; Exporttests prüfen unter anderem private Schlüssel, vorhandene
  Zielordner und uncommittete Quellen.
- Zwei Aufnahme-Synchronisationstests hatten beim gleichzeitigen, alle CPUs
  belegenden Komprimieren ihre Drei-Sekunden-Grenze überschritten. Nach Ende
  dieser Last bestanden alle Tests unverändert. Ein Belastungstest auf dem
  echten Pi ist dadurch nicht ersetzt.
- Reale Factory-Initialisierung in einer getrennten chroot-Testkopie mit
  synthetischer Board-Seriennummer. Benutzer `cdb` kann den Kioskordner anlegen
  und das Displayprofil verwalten; Wiederholung überschreibt das Profil nicht.
  HTTP-Erststart zeigt `required=true`, Schritt `welcome`, Verwaltung unkonfiguriert.
- `pip check`: keine beschädigten oder fehlenden Paketanforderungen.
- Endgültiges Image ausschließlich über schreibgeschützte Loop-Datei geprüft:
  FAT32 und ext4 fehlerfrei, Pi-5-Kernel und Device Tree vorhanden, App-/Netzwerk-
  /Erststart-Dienste eingerichtet, SSH aus. Root-Dateisystem ohne vorkopierte
  Kundenprofile, Schlüssel oder gemeinsame Maschinenidentität.
- Alle 118 App-Dateien **im endgültigen Image** stimmen per SHA256 mit dem
  Quellmanifest überein. Vollständiges Dekodieren des XZ-Exports bestätigt
  Stream-Integrität und exakt den Hash des zuvor geprüften Roh-Images.

## Jetzt die zweite Karte testen

1. Raspberry Pi Imager öffnen, **eigenes Image** wählen und die `.img.xz` laden.
2. Die **zweite SD-Karte** auswählen (mindestens 32 GB empfohlen). Vorhandene
   Imager-Anpassungen für Benutzer, SSH und WLAN überspringen.
3. Schreiben und Verifizieren abwarten. Den laufenden Pi erst für den tatsächlichen
   Kartentausch sauber herunterfahren und stromlos machen. Bisherige Karte
   beschriften und unangetastet aufbewahren.
4. Neue Karte starten: Querformat, Touch und Willkommens-Assistent prüfen.
5. WLAN/LAN, **neue** Gerätekopplung, Mikrofon, Lautsprecher, Brain-Anmeldung und
   Modelle einrichten. Keine bestehende Geräteidentität kopieren.
6. [Vollständige Hardwareabnahme](../../first-start-0.5.44/README.md#erstes-separates-image-testen)
   durchführen. Lokale Modellgewichte sind nicht im Image enthalten.

[Wie die Systeme zusammenspielen](../../architecture/README.md) ·
[Verbindlicher Ablauf für künftige Images](../README.md)
