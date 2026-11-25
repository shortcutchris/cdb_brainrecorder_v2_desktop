# Version 1 – Endabnahme

Stand: **25. November 2026 · Kandidat 1.0.0-rc1**. Noch keine endgültige V1-Freigabe.
Quellstand: `01d81078794942dc5255e4ab221b9e8c59a02502`.
[Bereinigte Ergebnisse](results-2026-11-24.json) · [Sichtprüfung](views-2026-11-24.md) · [SD-Image](../customer-image/build-1.0.0-rc1/README.md).

**Fortsetzung am echten Pi:** [Bedien- und Hardwareprüfung vom 25.11.](hardware-2026-11-25.md)
mit 25 zusätzlichen Bildschirmnachweisen. Aufnahme, Pause, Stummschaltung,
Timeralarm, Bibliothek, Außentipp-Abbruch und Offline-Verarbeitung bestanden.
Der kleine native Kalender bleibt offen. Die fehlende ReSpeaker-LED-Zugriffsregel
ist nach der Administratorinstallation auf dem Pi technisch nachgeprüft und behoben.
App-Paket und SD-Image wurden dabei nicht ersetzt.

## Bestanden

- **797 Python- und 171 JavaScript-Tests**; zusätzlich serieller PTY-Integrationstest.
  Native LCD-Protokoll- und Timeransicht-Tests mit Address-/UndefinedBehavior-Sanitizer.
- **Update am vorhandenen Pi von 0.5.105 auf 1.0.0-rc1**: Signatur und 158
  Paketdateien geprüft. App, Kiosk und LCD-Dienst danach aktiv. Anmeldung,
  Einstellungen, Aufnahmeninventar, NFC-Zuordnungen und Raummodus erhalten.
  Wartung beendet; kein Neustart und keine Änderung der Bootkonfiguration.
- **Echtes Zusatzdisplay**: Uhr → ein großer Countdown → zwei Timer → Alarm →
  wieder Uhr. 115 von 115 gesendeten Zuständen bestätigt; alle Wechsel vom
  Benutzer am Display bestätigt. Nur drei eigene Testtimer erzeugt, beendet und
  quittiert. Danach keine sichtbaren Timer und Begleitdienst wieder aktiv.
- **Neues SD-Image gebaut und offline geprüft**: FAT/ext4, 165 Quelldateien,
  Bootdateien, Dienste, Modelle und Kundendatenfreiheit. Komprimiertes Archiv
  fehlerfrei. ARM64-Runtime und leere Profilinitialisierung zusätzlich ohne
  Netzwerk ausgeführt; LCD-Pythonlaufzeit importierbar.
- Hauptansichten, Einstellungen und relevante Dialoge in einer isolierten
  UI-Prüfkopie dokumentiert. Aufnahme-/Pausen-/Talk-Sperren, große
  Entscheidungsflächen, Außentipp-Abbruch und Bildschirmtastatur geprüft.

## Während der Abnahme korrigiert

Auf dem vorhandenen Pi fehlte die ReSpeaker-USB-Zugriffsregel. Nach Installation
der bereits versionierten Regel ist der Geräteknoten für die Gruppe `audio` mit
Modus `0660` zugänglich. Ein kurzer Mikrofontest bestätigt die LED-Steuerzustände
`idle → recording → idle`, ohne Fehler und ohne Neustart. Im Factory-Image ist
diese Regel bereits enthalten; kein neues Image für diese Gerätereparatur nötig.

Das bisherige Image lieferte LCD-Code, aber keinen aktivierten Begleitdienst und
keine serielle Laufzeit. Die Factory-Einrichtung enthält jetzt beides, pyserial
3.5, die Gruppe `dialout` und einen aktivierten PC/SC-Socket.

Das ausdrücklich gewählte Profil `--pcie-usb-board` übernimmt für frische Images
PCIe, 100 ms Reset-Verzögerung und Gen 1. Widersprüchliche vorhandene Bootprofile
werden abgelehnt. Das ist **kein Nachweis**, dass der sporadische VIA-Ausfall
behoben wurde. App-Updates verändern diese OS-Komponenten nicht.

Der Remote-Control-Testaufbau bildet nun die USB-Wiederherstellung des echten
Studios ab und prüft zusätzlich, dass währenddessen kein Gespräch startet.

## Noch offene Freigabepunkte

1. **Zweite SD-Karte booten**: Karte ab 32 GB ist laut Benutzer vorhanden.
   Erststart, WLAN, Displayausrichtung, Audiogeräte, Offline-Transkription und
   Zusammenfassung sowie Neustart mit erhaltener Einrichtung prüfen.
2. **Touch-Kalender**: Die direkte Kiosk-Prüfung wurde am 25.11.
   fortgesetzt. Die Kalender-/Uhrzeitfelder des Browsers sind für unsere großen
   Touchziele zu klein. Die separat festgestellte LED-Freigabe ist inzwischen behoben.
3. **NFC-Hardware**: Seit 25.11. ist der Rocketek wieder angeschlossen und bereit;
   beide Zuordnungen und Direktstart-/Abnehmen-Einstellungen sind vorhanden.
   Talk/Meeting-Aufstellen und Abnehmen wurden noch nicht erneut physisch abgenommen.
4. **USB-Langzeitstabilität**: Frühere Belastungstests mit Timeralarmen bestanden
   und wurden hörbar bestätigt. Der vorherige VIA-Controller-Ausfall mit
   USB-Zeitüberschreitungen ist trotzdem nicht abschließend erklärt.
5. **Externe Funktionen**: Kein neuer vollständiger Cloud-Talk-, Brain-Upload-,
   Handy-Kopplungs- oder Aktivierungswort-Hardwaretest in diesem Durchlauf.
   Automatisierte Tests und synthetische UI-Zustände ersetzen diese nicht.

Das aktuelle Geräteprofil enthält kein aktiviertes Sprachansagen-Paket. Das ist
getrennt von den vorhandenen Timer-, Start- und Abschiedsklängen zu behandeln.
Neustart wurde zusätzlich am echten Pi bis zur Bestätigung kontrolliert und per
Außentipp abgebrochen. Ein echter Stromzyklus war in diesem Durchlauf nicht Teil
eines gesteuerten Tests.

## Nachweise und Datenschutz

Screenshots mit synthetischem Prüfkonto und Rohprotokolle liegen außerhalb Git im
Arbeitsordner `output/v1-acceptance-20261124/`; die Galerie heißt `index.html`.
Image, signiertes App-Paket und Bauprotokolle liegen lokal unter
`/Users/chris/Developer/cdb-images/1.0.0-rc1-20261124/`.
Keine Kundenanmeldung, Aufnahmen, WLAN-Schlüssel oder privaten Signierschlüssel
wurden in das Image übernommen. Die vorhandene SD-Karte wurde nicht beschrieben.
