# Geräteverwaltung – erste Ausbaustufe (Studio 0.5.43)

Stand: 14. Oktober 2026. Diese Stufe verwaltet **eine Organisation pro Installation**. Sie ist unabhängig vom persönlichen Brain-Konto. Aufnahmen, Gesprächsinhalte, Knowledge Areas, CDB-Sitzungen und Audio werden nicht an die Verwaltung übertragen.

## Bedienung

Die Zentrale ist unter **https://cdblab.de/devices/** erreichbar. Der Verwaltungsschlüssel wird nur im Browser-Arbeitsspeicher gehalten. Er liegt auf Chris' Mac außerhalb des Repositorys in `~/.config/cdb-fleet/admin`. Nicht per Chat versenden. Abmelden entfernt ihn aus der Oberfläche. Microsoft-SSO, individuelle Administratoren und Rollen sind **noch nicht Teil dieser Stufe**; der Schlüssel berechtigt zu allen Geräten dieser Installation.

1. Gerätenamen eingeben und **Kopplungscode erstellen** wählen.
2. Am Pi: **Einstellungen → Gerät & Verwaltung**, zwölfstelligen Code eingeben, **Gerät koppeln**.
3. Innerhalb von 30 Sekunden erscheinen Verbindung, Version, Aktivität und technische Werte.
4. **Diagnose** aktualisiert den technischen Status; **App neu starten** startet nur Studio; **Pi neu starten** fordert einen geordneten Systemneustart an.
5. Unter **Verfügbare App-Version** ein veröffentlichtes signiertes Paket auswählen und **App aktualisieren** wählen.

Ein Auftrag wird nach spätestens zehn Minuten ungültig. Beschäftigte Geräte stellen ihn zurück; er muss ausdrücklich neu gestartet werden. Es gibt keine später überraschend ausgeführte Neustartschlange. Bei fehlendem App-Zustand wird ein Neustart ebenfalls nicht blind erzwungen.

Kopplungscodes gelten zehn Minuten und einmalig. Die darauf folgende Geräteberechtigung ist separat widerrufbar. **Kopplung entfernen** sperrt weitere Meldungen und offene Aufträge. Für eine erneute Kopplung muss ein Administrator die lokale Datei `management/credential.json` bei gestopptem Agent entfernen und den Agent wieder starten. Beim Wechsel der SD-Karte in einen anderen Pi wird anhand der Hardwarekennung gesperrt, statt die alte Identität still zu übernehmen. Dies verhindert versehentliche Klone, ist aber keine Hardware-Attestierung gegen einen kompromittierten Pi.

## Bausteine und Grenzen

- `fleet/server.py`: eigenständige HTTP-Anwendung, SQLite-Geräteregister, Einladungen, Auftragszustände und Audit-Einträge. Ein Verwaltungsschlüssel pro Installation; keine Remote-Shell.
- `fleet/agent.py`: eigener systemd-Benutzerdienst, ausgehende HTTPS-Verbindung alle 30 Sekunden. Läuft auch bei ausgefallener Recorder-App. Keine eingehend geöffneten Pi-Ports nötig.
- `services/device_management.py`: privater lokaler Kontrollkanal mit separatem Token und gemeinsamer App-Sperre.
- `fleet/releases.py`: Ed25519-signierte, unveränderliche Programmversionen, atomarer Versionslink und persistentes Transaktionsjournal.
- Portal und Pi nutzen ausschließlich feste Aktionen. Es gibt weder einen frei eingebbaren Befehl noch eine vom Server frei wählbare Download-Adresse.

Inventar enthält Version, Aktivität, App-Erreichbarkeit, freien Speicher, Temperatur, RAM und den gemeldeten Aktivierungswort-Zustand. „Wartet auf Hey Brain“ beschreibt den Detektorzustand und **beweist keine erfolgreiche Spracherkennung**. Nach 100 Sekunden ohne Meldung gilt ein Gerät als offline. Rohprotokolle, Kontonamen und Geräte-Audiomitschnitte werden nicht übertragen. Das Portal ist keine Sammlung vollständiger Systemlogs.

Die Sperre wird unter denselben Locks gesetzt wie Aufnahme und Gespräch. Sie verhindert neue Mutationen und Wake-Starts. Neustart/Update werden bei Aufnahme, Live-Gespräch, Tests, Installation, Bluetooth-Aktion, ausstehender Verarbeitung/Übertragung, Wiedergabe oder aktivem Timer/Erinnerung abgewiesen. Alle geplanten Erinnerungen blockieren in dieser konservativen ersten Stufe; Wartungsfenster sind später zu ergänzen.

## Sichere App-Updates

Ein Paket enthält Code und Oberfläche, **keine** Aufnahmen, Konfiguration, Sitzungsdatenbanken, Modelle, Firmware oder Python-Pakete. Die Python-Laufzeit wird über Version und installierte Pakete gebunden. Abweichende Architektur, Runtime, Ausgangsversion, abgelaufenes Paket oder nicht steigende Freigabesequenz werden abgewiesen. Signatur, Archivhash und jeder Dateihash werden geprüft; Pfadtraversal, Symlinks und unerlaubte Dateien sind gesperrt. Kein Release-Installationsskript wird ausgeführt.

Ablauf: Paket laden → prüfen → freie App atomar reservieren → neue Version separat schreiben → Journal sichern → Versionslink wechseln → App starten → lokale Bereitschaft/Version prüfen → Freigabesequenz dauerhaft bestätigen → Wartung aufheben. Fehler führen zur vorherigen Version zurück. Ein abgebrochener Agent liest das Journal beim Start und stellt die alte Version wieder her. Bestätigte Updates werden nicht wegen eines nachträglichen Journal-Löschfehlers zurückgerollt. Eine offene Transaktion hält die App auch über die normale Wartungsfrist hinaus gesperrt.

Die Startprüfung belegt Serverstart, Versionsantwort und erreichbaren App-Zustand. Sie ersetzt keinen vollständigen akustischen Test oder Cloud-Sprachtest. Es wurde kein physischer Stromausfall während SD-Schreibzugriffen provoziert; Wiederanlaufzustände werden gezielt in Tests erzeugt. Die vorherige Version bleibt erhalten; keine automatische Bereinigung in dieser Stufe.

**Schema-Regel:** Pakete müssen `schema: unchanged` deklarieren und dürfen keine inkompatiblen Datenmigrationen enthalten. Der Freigabeverantwortliche muss dies im Code-Review prüfen; eine Signatur analysiert keine Python-Semantik. OS-, Firmware-, Modell- und Abhängigkeitsupdates benötigen einen separaten Ablauf. Die unabhängige Agent-Version wird ebenfalls nicht durch ein normales App-Paket ersetzt.

## Mender- und Serverentscheidung

Mender bietet Application Update Modules, Signaturprüfung und Rollback-Lebenszyklen. Es bleibt eine sinnvolle nächste Integrationsstufe für größere Flotten und Betriebssystemupdates. Die offizielle Docker-Compose-Installation ist als **Evaluation** beschrieben; die Produktionsanleitung führt zu Kubernetes. Ein zusätzliches Mender-System wurde deshalb nicht ungeprüft auf den gemeinsam genutzten Host gesetzt. Die aktuelle Lösung verwendet **keinen Mender-Client**. Die schmale App-Updatefunktion ist eigenständig und sollte vor größerem Flottenbetrieb gegen einen standardisierten Mender-Betrieb neu bewertet werden.

Primärquellen, geprüft am 14.10.2026:
- [Mender: Docker-Compose-Evaluation](https://docs.mender.io/server-installation/evaluation-with-docker-compose)
- [Mender: eigenes Update Module](https://docs.mender.io/artifact-creation/create-a-custom-update-module)
- [Mender: Signieren und Prüfen](https://docs.mender.io/artifact-creation/sign-and-verify)
- [Mender: Anpassung des Updateprozesses](https://docs.mender.io/overview/customize-the-update-process)
- [Mender: Serverinstallation](https://docs.mender.io/server-installation/overview)

Host `coolify-test`, Tailscale `100.117.50.28`, ARM64, 8 GB RAM. Bei Prüfung ca. 4,9 GB RAM verfügbar und 27 GB Disk frei. **Kein Coolify-Controller vorhanden**, auch kein gestoppter Container. Bestehender Docker-Compose-/Nginx-Betrieb wurde verwendet. Die neue Compose-Datei ist später in Coolify übernehmbar, aber derzeit kein Coolify-Projekt.

## Betrieb und Release

Server: `/opt/cdb-fleet`, Compose in `deploy/fleet/`, Loopback-Port 8460, Netzwerkalias `cdb-fleet` im bestehenden Netzwerk `coolify`. Nginx leitet ausschließlich `/devices/` an diesen Dienst. Bestehende Routen und Tailscale-Funnel bleiben erhalten. Daten und Admin-Schlüssel liegen außerhalb des Images. Container ohne Root, read-only-Dateisystem, begrenzte CPU/RAM, keine Linux-Capabilities. TLS endet am bestehenden Nginx.

Pi:
- Agentcode: `~/.local/share/cdb-recorder-agent/fleet/`.
- Agentdienst: `cdb-recorder-agent.service`.
- Programmversionen: `~/.local/share/cdb-recorder-app/releases/`, aktiver Link `current`.
- Private Geräteparameter: `~/.local/share/cdb-recorder-local/management/` (0600-Dateien).
- Daten und Python-venv bleiben in ihren bisherigen Verzeichnissen.
- Originale Startkonfiguration im datierten `~/backups/fleet-bootstrap-*`.

`python scripts/install-fleet.py --help` beschreibt den einmaligen Übergang. Nur auf einem freien Pi mit bereits getesteter Kandidatenquelle ausführen. Vorhandene Installationen werden nicht überschrieben. Der Installationsschritt ist administrativ; normale Updates laufen anschließend durch den atomaren App-Wartungskanal.

Signierschlüssel: `~/.config/cdb-fleet/release-private.pem` auf dem Mac; **nie auf Server oder Pi kopieren**. Der Pi erhält ausschließlich den öffentlichen Schlüssel. Schlüssel separat sicher sichern; Verlust erfordert kontrollierte Neuverteilung eines Vertrauensschlüssels.

Ein freigegebenes Release wird aus den in Git erfassten, zugelassenen Quelldateien erzeugt:

```sh
python scripts/fleet_release.py --key /privater/pfad/release-private.pem \
  --version VERSION --from-version VORVERSION --sequence FORTLAUFENDE_ZAHL \
  --runtime LAUFZEIT_HASH --out /privater/releaseordner
```

Nur sauberen, getesteten Commit signieren. Der Befehl gibt die Release-ID aus. Die JSON-Datei danach nach `/opt/cdb-fleet/deploy/fleet/data/releases/` kopieren (lesbar für Container-UID 10001). Sie erscheint im Portal. Keine privaten Schlüssel, Brain-Sitzungen oder Admin-Codes in Git. Ein Update-Paket darf kein älteres Ausgangsrelease still überschreiben.

SQLite-Sicherung mit der SQLite-Backup-API erstellen; nicht während Schreibzugriffen lediglich die Datei kopieren. Backup von Register, Freigabepaketen und privaten Serverparametern aufbewahren. `commands` und `audit` enthalten keine Gesprächsinhalte, wachsen aber derzeit ohne automatische Aufbewahrungsfrist.

### Wiederherstellung

Bei Updatefehler: zuerst Portalstatus und `accepted.json` prüfen. Agent führt Rückkehr automatisch durch. Bei erfolgloser Rückkehr bleibt das Journal erhalten. Nicht manuell löschen, solange die aktive Version unklar ist.

Bei fehlerhaftem einmaligen Bootstrap: ursprünglichen `cdb-recorder-studio.service` aus dem datierten Backup zurückkopieren, Agent stoppen, systemd neu laden und Studio starten. Die ursprünglichen Quelldateien, Modelle, Daten und venv sind unverändert vorhanden. Bei fehlender Kioskansicht das vorhandene `kiosk.sh` erneut starten; ein historischer temporärer systemd-Kioskname ist kein dauerhafter Dienst.

## Testnachweis

Der abschließende Stand und reale Verwaltungsaktionen stehen in [acceptance.json](acceptance.json). Automatische Tests decken HTTP-Authentifizierung/Origin, Einmalcode/Ablauf, Widerruf, Hardwarewechsel, Datenfilter, Auftragszuordnung, doppelte Zustellung, Ablauf, Wartung, Signatur/Archivhash, Pfade, Architektur/Runtime/Schema, Rollback und unterbrochene Transaktionen ab.
