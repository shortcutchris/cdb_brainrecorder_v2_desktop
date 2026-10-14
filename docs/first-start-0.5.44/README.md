# Erststart und Kunden-Image · 0.5.44

Stand: 14. Oktober 2026. Erststart-Funktion implementiert; Kunden-Image **als Baupaket vorbereitet, noch kein gebootetes oder freigegebenes SD-Image**. Die bestehende Installation auf Chris' Pi wurde nicht aktualisiert, neu gekoppelt oder umkonfiguriert. Tests laufen in `/tmp/cdb-onboarding-044-code` mit getrennten Daten.

## Bedienung

Ein neues Factory-Profil öffnet automatisch den lokalen Erststart-Assistenten. Er benötigt zum Anzeigen keine Internetverbindung. Eine bestehende Installation erhält keinen automatischen Erststart: Nur `first-start.json` mit `required: true` aktiviert ihn.

1. Willkommen → Einrichtung starten.
2. Netzwerk: WLAN-Liste mit drei Einträgen je Seite und Seitenbuttons; LAN-Status; WPA2/WPA3-Personal. Ein Netzwerk antippen oder „Anderes WLAN eingeben“ wählen.
3. WLAN-Schlüssel: separate Seite mit maskierter Eingabe, optionaler Anzeige, Bildschirmtastatur, verstecktem WLAN und Sicherheitswahl. „Verbinden“ bleibt im festen rechten Fußbereich. Nach erfolgreicher Aktivierung geht es zurück zur Netzwerkliste. Auch ein WLAN ohne Internet ist eine gültige lokale Verbindung; Internetstatus wird separat dargestellt.
4. Gerät koppeln: Ein Administrator erzeugt unter https://cdblab.de/devices/ einen einmaligen, zehn Minuten gültigen Code. Code am Gerät eingeben und Bestätigung abwarten. Wiederholtes Absenden während laufender Kopplung wird abgewiesen. Gerät und Verwaltungsserver werden angezeigt; der Geräteschlüssel gelangt nicht in den Browser.
5. Audio: Übergang zur bestehenden Mikrofoneinrichtung. Mikrofon, Lautsprecher, persönliches Brain-Konto und Modelle werden dort eingerichtet. Der Erststart markiert niemals ungeprüft ein Mikrofon als einsatzbereit.

Ohne Internet/Verwaltung kann der Benutzer ausdrücklich „Vorerst ohne Geräteverwaltung einrichten“ wählen. Diese Entscheidung und der Schritt werden gespeichert. Die spätere Kopplung bleibt in Einstellungen → Gerät & Verwaltung möglich. Dort öffnet „WLAN & Einrichtung“ die Netzwerkeinrichtung; bestehende Aufnahmen und Einstellungen bleiben erhalten.

Die Firmen-Gerätekopplung verwendet **die vorhandenen Verwaltungscodes**, noch kein neues Microsoft-SSO/QR-Claim-Verfahren. Persönliche Microsoft-Anmeldung für Brain-Funktionen und Geräteverwaltung sind getrennt. Für eine spätere Firmen-SSO-Anbindung müssen Tenant-/Rollenprüfung und Freigabe zur Gerätezuordnung ergänzt werden.

## Netzwerkdienst und Sperren

`deploy/customer-image/network_service.py` ist ein eigener root-eigener Systemdienst. Die App bleibt ein normaler Benutzerprozess. Er bietet ausschließlich Status, Scan und Verbindung über einen lokalen Unix-Socket an. Socket und Verzeichnis erlauben nur root und der Gruppe `cdb-network` Zugriff. Es gibt keine beliebigen Befehle, Dateipfade oder Shell-Ausführung aus Clientwerten.

WLAN-Schlüssel werden ausschließlich in einem root-lesbaren NetworkManager-Profil gespeichert (0600). Sie erscheinen weder in Prozessargumenten noch in App-Status, Browser-Speicher, Fehlerantworten oder der Geräte-Telemetrie. Profilname und UUID werden vom Dienst erzeugt. SSID und Schlüssel werden vor dem Schreiben validiert bzw. für das Keyfile escaped.

Ein neues Profil wird zunächst ohne Autoconnect aktiviert. Erst nach erfolgreicher Aktivierung wird es dauerhaft automatisch verbunden. Ein Journal merkt vorherige Verbindung und Kandidat. Bei einem Fehler oder Dienstneustart wird nur der Kandidat entfernt und die vorherige Verbindung wieder aktiviert. Bestehende Profile werden nicht überschrieben. Ein echter Stromausfall und ein falscher Schlüssel müssen vor Image-Freigabe zusätzlich auf einem separaten Testgerät geprüft werden; die automatischen Tests simulieren diese Pfade.

Aufnahme, Gespräch, Modelldownload/-test, Verarbeitung, Übertragung und aktive Timer verhindern Netzwerkaktionen. Während einer Netzwerkoperation gelten die gemeinsamen App-Sperren; das Aktivierungswort pausiert. Ein neuer Scan/Verbindungsauftrag ist erst nach Abschluss möglich. HTTP-Aktionen benötigen den bestehenden CSRF-Schutz; Studio hört weiterhin ausschließlich auf Loopback.

Unterstützt: WPA2/WPA3-Personal, gespeicherte/versteckte SSID, Ethernet. Nicht Teil dieser Version: 802.1X, Zertifikatsverwaltung, offene WLANs, Captive-Portal-Browser, WLAN-Hotspot, Passwortänderung bereits gespeicherter Profile als Verwaltungsfunktion. Solche Netze dürfen nicht als erfolgreich eingerichtet ausgegeben werden. Country/Regulatory Domain wird im Image-Bauparameter festgelegt, in der ersten Variante DE; keine automatische Standortannahme.

## Sauberes Kunden-Baupaket erzeugen

Auf einem sauberen Checkout mit Python und `cryptography`:

```sh
python scripts/prepare_customer_image.py \
  --output /sicherer/neuer/pfad/cdb-customer-image-0.5.44 \
  --public-key /sicherer/pfad/release-public.pem \
  --server https://cdblab.de/devices \
  --country DE
```

Der öffentliche Ed25519-Schlüssel muss zum Release-Signierschlüssel der Verwaltung passen. Ein privater Schlüssel wird abgewiesen. Der Ausgabeordner muss neu sein; das Werkzeug überschreibt keine Installation und liest keine SD-Karte aus.

Das Paket enthält eine eigene pi-gen-Stage, Konfiguration, Buildskript, root-eigenen Netzwerkdienst, Erststart-Initialisierung, Kiosk-/App-/Agent-Units, ReSpeaker-LED-Regel und öffentliche Update-Prüfung. App-Code kommt aus einer Positivliste versionierter Dateien. Keine Aufnahmen, Sitzungsdatenbanken, Browserprofile, WLAN-Schlüssel, Microsoft-Sitzungen, Geräteschlüssel, Tailscale-Zugänge oder privaten SSH-/Signierschlüssel werden übernommen.

- pi-gen ARM64-Pin: `d346cd53562b3c6b4f94c9155175f814258c456d`, Debian Trixie.
- Standardkonto `cdb`, gesperrtes Passwort; SSH abgeschaltet; kein pauschales sudo. Einzig der vorhandene kontrollierte Neustartbefehl wird erlaubt.
- Root-eigene Einmalmarkierung unter `/var/lib/cdb-factory` verhindert erneute privilegierte Initialisierung eines später benutzerbeschreibbaren Home-Verzeichnisses. Ein unterbrochener **System-Bootstrap** verlangt Image-Recovery; ein unterbrochener **Benutzer-Assistent** wird normal fortgesetzt. Gerätespezifische Hostnamen und neues Profil beim ersten Start; systemd erzeugt eine eigene machine-id. Kein vorkopierter Verwaltungs-Token. Keine gemeinsamen SSH-Hostschlüssel.
- Python-Pakete entsprechend den Repository-Pins; `cryptography 50.0.2`, optionales Wake-Runtimepaket `vosk 0.3.45` zusätzlich. Paketstände werden im Image protokolliert.
- Whisper-/Ollama-Runtimes gemäß den bereits dokumentierten Pins in `docs/LOCAL_AI.md`; Ollama-Archiv wird per SHA256 geprüft und CPU-Libraries ausgewählt. Modellgewichte werden nicht mitgeliefert und müssen später bewusst installiert werden. Wake-Modellinstallation bleibt gesondert nötig.
- Updates verwenden die vorhandene signierte App-Update-Architektur. Root-Netzwerkdienst und Betriebssystem werden damit nicht ausgetauscht.

Das Buildskript verlangt einen **dedizierten ARM64-Linux-Baurechner** mit pi-gen-Abhängigkeiten und ausreichend freiem Speicher. Nicht auf dem laufenden Kunden-/Test-Pi und nicht auf dem gemeinsam genutzten Coolify-Server ausführen. Dort wird `build.sh` im Baupaket gestartet; es erstellt ein neues Dateisystem. Der chroot-Installationsschritt verweigert die Ausführung ohne temporären Image-Baumarker.

`manifest.json` dokumentiert Quellcommit, Hash jedes App-Inputs und öffentlichen Prüfschlüssel. Das ist ein nachvollziehbarer Build, **noch kein bitweise reproduzierbares Image**: Paketquellen/indirekte Python-Abhängigkeiten sind nicht vollständig über Snapshot und Hash-Lock eingefroren. Vor Serienauslieferung sind ein qualifizierter Image-Build und eingefrorene Paketartefakte erforderlich.

Nach dem Image-Installationsschritt läuft die lesende Prüfung `scripts/audit_customer_rootfs.py`. Sie weist vorhandene WLAN-/SSH-/App-Sitzungsdaten, aktive gemeinsame Kontopasswörter und machine-id zurück. Nach dem endgültigen pi-gen-Export den Audit auf dem offline gemounteten Root-Dateisystem erneut ausführen; Image-SHA256 und Paketlisten mit der Freigabe ablegen. Dieser Check ersetzt keinen vollständigen Geheimnis- oder Boot-Test.

## Durchgeführte Tests

- 258 Python-Tests im separaten Verzeichnis auf dem Raspberry Pi, erfolgreich. Enthält 11 Erststart-/Netzwerk-/Socket-/Kopplungstests und 3 Factory-Export-/Audit-/Initialisierungstests.
- 100 JavaScript-Tests (einschließlich Theme-Initialisierung ohne Einstellungseditor), erfolgreich; Syntaxprüfung der neuen Skripte.
- Netzwerkstatus am echten Pi lesend geprüft: LAN und WLAN verbunden, NetworkManager meldet Internetzugang. Keine Verbindung getrennt, keine Profile geschrieben.
- GLib-Keyfile-Parser auf dem Pi: synthetischer Schlüssel mit Leerzeichen und Backslash exakt wiederhergestellt.
- Browserprüfung 1280 × 720: Willkommen, WLAN-Seitenwechsel, Schlüssel-Eingabe mit Touch-Tastatur, gesperrte Aktionen während Verbindung, Testkopplung, Übergang zur Audioeinrichtung. Daten und Kopplung im UI-Test sind ausdrücklich synthetisch. Die Produktions-Gerätekopplung bleibt unangetastet.
- Screenshots: `welcome.png`, `network.png`, `wifi-key.png`, `paired.png`, `audio.png`.

Nicht durchgeführt: neues SD-Image bauen/flashen/booten, realen WLAN-Schlüssel wechseln, tatsächlichen Stromausfall auslösen, WPA3-/Enterprise-Hardwareabnahme. Für diese Abnahme eine **zweite SD-Karte** verwenden; aktuelle SD-Karte unangetastet aufbewahren. Erst nach diesen Prüfungen ist das Paket ein freigegebenes Kunden-Image.

## Erstes separates Image testen

1. Image auf eine zweite SD-Karte schreiben. Aktuelle Karte sicher verwahren.
2. Ohne LAN starten: Assistent muss offline erscheinen; SSID wählen, falschen und danach richtigen Schlüssel prüfen.
3. Neustart während Einrichtung/Verbindungsversuch; korrektes Wiederaufnehmen und Rückkehr zum alten Netz prüfen.
4. Mit LAN wiederholen; ausgeschalteter Verwaltungsserver darf lokale Oberfläche nicht blockieren.
5. Neuen Verwaltungs-Testcode erzeugen, einmalig koppeln; abgelaufenen und bereits verwendeten Code ablehnen. Keine bestehende Geräteidentität wiederverwenden.
6. Mikrofon und Lautsprecher physisch testen; Brain-Anmeldung/Modellinstallation und eine synthetische Aufnahme prüfen.
7. Geräte-Neustart und signiertes App-Update samt Rollback auf dem frischen Image abnehmen; Image-SHA256 und Protokoll dokumentieren.

## Quellen

- [Raspberry Pi Konfiguration / NetworkManager](https://www.raspberrypi.com/documentation/computers/configuration.html)
- [NetworkManager-Keyfile, Schutz und Format](https://networkmanager.dev/docs/api/latest/nm-settings-keyfile.html)
- [nmcli](https://networkmanager.dev/docs/api/latest/nmcli.html)
- [Gepinnte pi-gen-Bauanleitung](https://github.com/RPi-Distro/pi-gen/blob/d346cd53562b3c6b4f94c9155175f814258c456d/README.md)
