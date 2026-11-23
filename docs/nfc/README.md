# NFC-Aufsteller · Recorder 0.5.95

Stand 23.11.2026. Die optionale NFC-Laufzeit ist auf dem Recorder-Pi installiert:
`python3-pyscard` 2.2.2-1, `pcscd` 2.3.3-1 und `libccid` 1.6.2-1;
`pcscd.socket` aktiv. Der Rocketek (`2ce3:9567`) ist ein einzelnes USB-Gerät mit
zwei PC/SC-Schnittstellen:

- `Alcor Link AK9567 00 00` (Kontaktkarten)
- `Alcor Link AK9567 [Contactless Card Reader] 01 00` (kontaktlos)

USB-Interface 1 ist ebenfalls ausdrücklich als `Contactless Card Reader`
benannt. Bis 0.5.94 wies die App beide Einträge fälschlich als mehrere Leser ab.
0.5.95 wählt die einzige eindeutig kontaktlos benannte Schnittstelle unabhängig
von der Reihenfolge. Keine Slotnummer geraten und keine PC/SC-/Polkit-Rechte
aufgeweicht. [Auslieferung und Hardwareabnahme](acceptance-0.5.95.md).

## Bedienung

Einstellungen → Audio → NFC-Aufsteller. NFC ist nach sauberer Installation aus.
„Leser prüfen“ aktiviert eine zweiminütige Einrichtungssitzung. Einen Tag auflegen,
Talk zuordnen, abnehmen; zweiten Tag auflegen, Meeting zuordnen. Danach beide
abnehmen, NFC einschalten, 1,5 Sekunden leeres Lesefeld abwarten.

- Talk nutzt das aktuelle Brain-Konto und die zuvor gespeicherten Wissensbereiche.
- Meeting verwendet den bestehenden Record-Start und Record-Stop mit Speicherung
  und normaler nachgelagerter Verarbeitung. Kein zweiter Audio-Recorder.
- Im standardmäßigen Raummodus führt ein Aufsteller zunächst zur Anmeldung und Vorbereitung. Ohne Anmeldung keine Gastaufnahme; Start am Display ausdrücklich bestätigen.
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

PC/SC/CCID: ein einzelner Leser oder genau eine ausdrücklich als „Contactless“ benannte Schnittstelle bei einem Gerät mit mehreren Einträgen. Mehrere kontaktlose oder ausschließlich unklar benannte Einträge bleiben gesperrt. UID-Abfrage `FF CA 00 00 00`; dies ist nicht bei jedem
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
keine Systempakete importieren. Vor Ort prüfen, dass der normale App-Benutzer im App-Dienstkontext den
PC/SC-Dienst erreichen kann; eine SSH-Sitzung kann abweichende Polkit-Rechte haben; keine pauschalen Berechtigungsaufweichungen hinzufügen.
Das Script aktiviert keine Tags und startet den Recorder nicht neu.

Neue SD-Karte: `prepare_customer_image.py` enthält die Pakete im sauberen pi-gen-
Rezept. NFC-Service-/UI-Dateien sind von der bestehenden Code-Allowlist abgedeckt;
Nutzerzuordnungen werden weder exportiert noch überschrieben. Kein SD-Abbild wurde
gebaut oder gebootet. Fehlende optionale Laufzeit verhindert nur NFC, nicht den Appstart.

Rücknahme: NFC in der App ausschalten; laufende Aufnahme/Gespräch manuell beenden.
Bei Bedarf reguläres Code-Rollback auf die zuletzt geprüfte Version. Die lokale Zuordnung bleibt erhalten; 0.5.94 besitzt noch den beschriebenen Rocketek-Auswahlfehler. PC/SC nicht entfernen, wenn ein anderer Dienst
den Leser benötigt. Keine Kundenaufnahmen oder Einstellungen löschen.

## Technische Grenzen und Abnahme

Zusatzprüfung 0.5.95: 55 gezielte Tests bestanden (Reader, NFC-Zustandsautomat,
Raummodus/-aktivität, Kunden-Image). Auswahl bleibt bei Reihenfolgenwechsel
stabil. Kontaktkarten-Schnittstelle wird bei diesem Dual-Reader nicht geöffnet.
Der Worker merkt sich die ausgewählte Schnittstelle; fällt nur diese weg,
wechselt er nicht unbemerkt zum Kontaktkarten-Slot. Keine rohe UID in Logs oder
Diagnosebelegen. Neue Images übernehmen den Code über die bestehende Positivliste;
OS-Pakete stehen bereits im Factory-Rezept. Kein neues SD-Image gebaut.

Frühere Basisabnahme:

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
