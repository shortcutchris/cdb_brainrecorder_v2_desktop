# NFC-Aufsteller · Recorder 0.5.71

Umsetzungskandidat vom 26.10.2026, Basis 0.5.70. Noch nicht auf dem Pi installiert
und noch nicht mit einem echten NFC-Leser/Tag abgenommen. Die vorhandene
Pi-Konfiguration und Mira-Quellen wurden nicht geändert.

## Bedienung

Einstellungen → Audio → NFC-Aufsteller. NFC ist nach sauberer Installation aus.
„Leser prüfen“ aktiviert eine zweiminütige Einrichtungssitzung. Einen Tag auflegen,
Talk zuordnen, abnehmen; zweiten Tag auflegen, Meeting zuordnen. Danach beide
abnehmen, NFC einschalten, 1,5 Sekunden leeres Lesefeld abwarten.

- Talk nutzt das aktuelle Brain-Konto und die zuvor gespeicherten Wissensbereiche.
- Meeting verwendet den bestehenden Record-Start und Record-Stop mit Speicherung
  und normaler nachgelagerter Verarbeitung. Kein zweiter Audio-Recorder.
- Ein stabiler Tag startet einmal. 1,5 Sekunden bestätigte Abwesenheit stoppen
  ausschließlich die eigene Aufnahme-ID bzw. Live-Lease.
- Manuelles Stoppen, Neustart mit gehaltenem Tag, unbekannte Tags und blockierter
  Start lösen keine automatischen Wiederholungen aus. Erst abnehmen und neu auflegen.
- Ein Reader-/USB-Fehler ist keine Abwesenheit. Die Aufnahme bleibt erhalten;
  Bildschirmbedienung bleibt möglich. Ein anderer Tag wechselt nicht abrupt.
- Wake Word behält seine Einstellung; die gemeinsamen Gerätesperren koordinieren
  NFC, Bildschirm, Wake Word und Fernsteuerung.

Die Tagkennung wird bereits im Readerprozess mit SHA-256 verarbeitet. Nur lokale
Hashes und Moduszuordnung liegen in `nfc-tokens.json` (0600); weder rohe UID noch
Hashes erscheinen im öffentlichen Status. Das ist eine Moduswahl, kein sicherer
Identitätsnachweis. Keine API-Schlüssel auf Tags schreiben.

## Reader und Installation

PC/SC/CCID, genau ein Leser. UID-Abfrage `FF CA 00 00 00`; dies ist nicht bei jedem
PC/SC-Leser bzw. Tag unterstützt. ACR122U aus Mira ist ein zu prüfender Kandidat,
keine zugesagte Raspberry-Pi-Abnahme. Hardwaredaten: Pi-Studio-Projekt
`pi-recorder-accessories`, Version `pi-recorder-accessories-v0.1`.

Bestehendes Gerät: reguläres signiertes Code-Update separat einspielen. Die drei
Debian-Pakete sind eine **zusätzliche, optionale Laufzeitänderung**; der Code-Updater
führt keine Paketinstallation aus. In einem Wartungsfenster ohne laufende Aufnahme:

```sh
sudo bash scripts/install-nfc.sh
```

Installiert `python3-pyscard`, `pcscd`, `libccid` und aktiviert `pcscd.socket`.
Der Worker läuft isoliert über `/usr/bin/python3 -I`, deshalb muss die App-venv
keine Systempakete importieren. Vor Ort prüfen, dass der normale App-Benutzer den
PC/SC-Dienst erreichen kann; keine pauschalen Berechtigungsaufweichungen hinzufügen.
Das Script aktiviert keine Tags und startet den Recorder nicht neu.

Neue SD-Karte: `prepare_customer_image.py` enthält die Pakete im sauberen pi-gen-
Rezept. NFC-Service-/UI-Dateien sind von der bestehenden Code-Allowlist abgedeckt;
Nutzerzuordnungen werden weder exportiert noch überschrieben. Kein SD-Abbild wurde
gebaut oder gebootet. Fehlende optionale Laufzeit verhindert nur NFC, nicht den Appstart.

Rücknahme: NFC in der App ausschalten; laufende Aufnahme/Gespräch manuell beenden.
Bei Bedarf reguläres Code-Rollback auf 0.5.70. Die lokale Zuordnung darf bleiben;
die alte Version liest sie nicht. PC/SC nicht entfernen, wenn ein anderer Dienst
den Leser benötigt. Keine Kundenaufnahmen oder Einstellungen löschen.

## Technische Grenzen und Abnahme

Native PC/SC-Aufrufe laufen in einem separaten Prozess; veraltete Antworten werden
nach zwei Sekunden als Fehler behandelt. Ein hängender Worker wird nach vier
Sekunden neu gestartet. Keine USB-Aufrufe im Audio-Control-Thread. Zwei Sekunden
veraltete Präsenz sind keine sichere Aussage über Wegnehmen.

Tests: Zustandsübergänge, stabile Abwesenheit, USB-Ausfall, Wiederanstecken,
manuelles Stoppen, Sitzungsbesitz, ununterstützte UID-APDU, getrennte Tagzuordnung,
Speicherfehler, Standard aus, Factory-Allowlist und bisherige Wake-/Audio-/Remote-
Kontrolle. Browserprüfung der neuen Seite mit nicht installierter Reader-Laufzeit.
125 gezielte Tests mit dem exakt festgelegten Engine-Wheel 0.2.7 bestanden.
Eine zunächst ältere lokale Testinstallation wurde für den Prüflauf isoliert
ersetzt; der Produktcode benötigte dafür keine Änderung.
Simulationen sind keine echte Audio-/RF-/USB-Abnahme.

Vor Freigabe: echte Leserbezeichnung, USB-ID und Tagtyp protokollieren; offen und
im gedruckten Gehäuse testen; Talk/Meeting jeweils zehnmal, Dauerauflage zehn
Minuten, USB-Ausfall während Testaufnahme, Neustart mit Tag, parallelen Wake-Start
und manuelles Stoppen prüfen. Audio-Datei und Verarbeitung kontrollieren.

Grundlagen: [pyscard-Dokumentation](https://pyscard.sourceforge.io/user-guide.html),
[ACS ACR122U](https://www.acs.com.hk/en/products/3/acr122u-usb-nfc-reader/).
Mira-Code diente als Referenz; seine plattformspezifische ctypes-Bindung wurde
nicht kopiert. Der ACR122U ist beim Hersteller abgekündigt; vor Neubeschaffung
eine aktuelle Variante separat prüfen.
