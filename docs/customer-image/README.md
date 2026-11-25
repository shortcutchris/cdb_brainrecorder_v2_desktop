# SD-Images bauen, testen und weiterentwickeln

**1.0.0-rc4, geführte Formate:** Die vorhandene Positivliste übernimmt
`services/workshops.py` und `studio/workshops.*`. SQLite ist bereits vorhanden;
keine Runtime-, Root- oder Factory-Erweiterung. `workshops.sqlite3` wird erst beim
Start leer angelegt und darf nie aus einem benutzten Pi ins Image gelangen.
Ein Bestandsupdate ergänzt die separate Ablage, ohne vorhandene Datenbanken zu
migrieren. Das rc1-SD-Image enthält diese Funktion noch nicht.

**1.0.0-rc2, Gerätebefehle im Gespräch:** `services/voice_device.py` und die
aktualisierte Talk-Hilfe werden mit den vorhandenen Positivlisten exportiert;
keine neue OS-/Runtime-Komponente. Die Belegdatenbank entsteht leer auf dem
Gerät und gehört nicht ins Image. Das gebaute rc1-Image enthält dies noch nicht.
[Details und Rollout-Abhängigkeit vom Voice-Dienst](../voice-device-v2/README.md).

**1.0.0-rc1, Endabnahme:** Das Factory-Image richtet jetzt auch den USB-LCD-
Begleitdienst mit eigener, auf pyserial 3.5 fixierter Laufzeit, `dialout` und
aktiviertem PC/SC-Socket ein. `--pcie-usb-board` übernimmt ausdrücklich das auf
dem Gehäuse-Pi verwendete Gen-1-Profil; generische Images bleiben unverändert.
Das ist kein Nachweis einer Behebung des sporadischen USB-Controller-Ausfalls.
Bestehende Geräte behalten ihre Einrichtung; ein App-Update ändert diese
OS-Dienste und Bootparameter nicht. [Endabnahme](../acceptance-v1/README.md).

**0.5.105:** Der USB-Audio-Helfer wird explizit im Factoryteil eingerichtet,
mit genau zwei freigegebenen Root-Kommandos. Bestehende Geräte benötigen den
einmaligen Administrator-Installer; App-Updates erweitern keine Systemrechte.
Das Diagnosewerkzeug bleibt separat. Kein neues SD-Image gebaut.
[Details](../audio/usb-recovery-0.5.105.md).

**0.5.104:** Die Update-Sitzungsübergabe wird als normales App-Modul aus der
bestehenden Allowlist mitgeliefert. Frische Images enthalten keine Sitzungsdaten
oder Übergaben; Anmeldung ist erforderlich. Keine Runtime- oder OS-Änderung.
[Details und Abnahme](../update-session-0.5.104/README.md).

**cdbPiOS-Startbildschirm:** Neue Baupakete enthalten das eigene Boot-/Abschaltbild
mit expliziter Plymouth-Installation und nativer Touch-Display-2-Ausrichtung.
Das ist eine OS-Ergänzung zum App-Stand 0.5.93, kein durch App-Updates ausgeführtes
Installationsskript. Im Image 1.0.0-rc1 enthalten; dessen Hardware-Erststart ist noch offen. [Paket, Tests und bestehende Geräte](../boot-brand/README.md).

Bei der Hardwareabnahme eines neuen Pi mit interner Soundbar den [Links-rechts-Hörtest in Recorder Studio](../audio/soundbar.md) durchführen.

Das Kunden-Image wird aus **Quellcode und Bauanleitung** erstellt. Es ist kein
Abbild eines benutzten Pi. Der laufende Pi und seine SD-Karte werden zum Bauen
nicht benötigt und bleiben unangetastet.

**Aktueller Testkandidat:** [SD-Image 1.0.0-rc1 mit Offline-Modellen und Zusatzdisplay](build-1.0.0-rc1/README.md). [Früherer Build 0.5.77](build-0.5.77/README.md).

[Systemübersicht und Architektur](../architecture/README.md) ·
[Erststart-Assistent ab 0.5.77](../erststart-0.5.77.md) · [Erststart im Image 0.5.44](../first-start-0.5.44/README.md)

## Hilfeportal ab App 0.5.94

Die versionierten Dateien unter `services/local_portal.py`, `services/vendor/`, `studio/help/` und `studio/local-portal.*` werden über die bestehenden Positivlisten sowohl ins App-Update als auch ins Image-Baupaket übernommen. Die Verkabelungs-PDF liegt integritätsgeprüft in einem JSON-Asset, damit auch der bereits installierte Update-Prüfer die neue Anleitung akzeptiert. Keine Erweiterung seiner Dateityp-Freigabe nötig. Die bestehende `cryptography`-Laufzeit wird weiterverwendet.

Frische Geräte starten nur die allgemeine Hilfe auf Port 8091; persönliche Fernbedienung bleibt ausgeschaltet. Der private TLS-Schlüssel entsteht erst beim Einschalten auf dem jeweiligen Pi. Keine Zertifikate, Schlüssel oder Kopplungen werden aus einem benutzten Gerät übernommen. [Details und Prüfstand](../local-portal/README.md).

## Was jede Weiterentwicklung berücksichtigen muss

Diese Regel gilt für alle künftigen Änderungen und ist zusätzlich in
`AGENTS.md` festgehalten: **App-Update und frische Image-Installation gemeinsam
bewerten und den Image-Einfluss im Release dokumentieren.**

| Änderung | Bestehendes Gerät | Nächstes SD-Image |
| --- | --- | --- |
| Python-App, HTML, CSS, JS, Töne, Icons | Signiertes App-Paket, sofern Runtime/Schema kompatibel | Versionierte Dateien aus der Positivliste werden übernommen |
| Neue Datei oder neues Asset | Datei und Freigabe-Positivliste prüfen | `git add`, Image-Manifest auf Vollständigkeit prüfen |
| Python-Paket oder native Bibliothek | Kein normales Code-Update; eigene Migration qualifizieren | Anforderungen/Pins und Runtime-Installation anpassen |
| Root-Dienst, Bluetooth, Audio, WLAN, Kiosk, OS | Kontrollierte Systemwartung oder neues Image | Factory-Stage, Dienste und Erststart prüfen |
| Datenformat | Migration und Rückkehr ausdrücklich qualifizieren | Leeren Erststart und vorhandene Daten getrennt testen |
| TQS-/CDB-Tool oder API-Vertrag | Server und Pi auf Kompatibilität prüfen | Unterstützte Serverfähigkeiten prüfen; Server ist nicht Teil des Images |

Ein Commit erzeugt **noch nicht automatisch** ein neues SD-Image. Der Build muss
für die freizugebende Version bewusst gestartet werden. Es gibt derzeit keine
CI, die jedes Commit als mehrere Gigabyte großes Image veröffentlicht.

## Wiederholbarer Build

Voraussetzungen: eigener ARM64-Linux-Builder oder Apple-Silicon-Mac mit laufendem
ARM64-Docker, Git, Python 3 und `cryptography` für den Paketexport. Docker baut
in seiner Linux-VM mit den von pi-gen benötigten privilegierten Mount-/Loop-
Funktionen. Mindestens 40 GB freien Arbeitsbereich vorsehen; praktisch 60 GB
oder mehr für Image, Zwischenstufen und Export. Nicht auf dem aktiven Pi oder
dem gemeinsam genutzten Infrastrukturserver bauen.

1. Änderungen testen, Versionsstand und Image-Einfluss dokumentieren, committen.
2. Neues Baupaket aus dem sauberen Commit erstellen. Der Export weist geänderte
   versionierte Dateien zurück. Nicht versionierte Dateien sind keine Inputs.
3. Paket in einen neuen lokalen Arbeitsordner außerhalb von Dropbox kopieren.
4. Build starten; Logs bleiben im Arbeitsordner. App- und Build-Inputs werden
   gegen das Manifest geprüft, bevor pi-gen geklont wird.
5. Fertiges Image offline prüfen, Prüfsumme und bereinigtes Build-Protokoll ablegen.
6. Image auf einer **zweiten Karte** booten und die Hardwareabnahme dokumentieren.

```sh
python3 scripts/prepare_customer_image.py \
  --output /neuer/pfad/brain-kit \
  --public-key /sicherer/pfad/release-public.pem \
  --server https://cdblab.de/devices --country DE --offline-models
cd /neuer/pfad/brain-kit
./build.sh --docker
# Auf einem vorbereiteten dedizierten ARM64-Linux-Host alternativ: ./build.sh
```

Ausgabe: `pi-gen/deploy/*.img.xz` und Build-Logs. pi-gen ist auf den im Manifest
angegebenen Commit festgelegt. `build.sh` verweigert einen bereits vorhandenen
pi-gen-Ordner; erneute saubere Builds bekommen einen neuen Arbeitsordner.
Ein Docker-Build-Container bleibt für Diagnose/Offlineprüfung erhalten und kann
nach Sicherung der Artefakte gezielt entfernt werden. Keine globale Docker-
Bereinigung ausführen: andere Projekte können dieselbe Engine benutzen.

Whisper wird ausdrücklich für `armv8.2-a+dotprod` gebaut (Pi 5 / Cortex-A76),
**nicht** für die vom Mac-Buildhost erkannten CPU-Erweiterungen. Damit gelangen
keine Apple-spezifischen Befehlsanforderungen in die Pi-Binärdateien. Das Image
ist für Pi 5 qualifiziert; andere Pi-Generationen brauchen eigene Prüfung.
Audio-/Bluetooth- und Wayland-Pakete sind explizite Image-Abhängigkeiten.
Das frische Profil dreht Touch Display 2 an DSI-1/DSI-2 um 90 Grad ins Querformat;
HDMI und vorhandene Displayprofile werden nicht umgeschrieben.

## Was im Image steckt

Raspberry Pi OS Trixie ARM64, Wayland-Desktop mit Kiosk, Python-Runtime, Recorder,
separater Verwaltungsagent, root-eigener WLAN-Dienst, Erststart-Assistent,
Whisper- und Ollama-Programme sowie der öffentliche Update-Prüfschlüssel.
Keine persönlichen Daten, WLAN-Schlüssel, Brain-Sitzungen, gekoppelte Bluetooth-
Geräte, Verwaltungs-Identitäten oder privaten SSH-/Signierschlüssel.
Mit `--offline-models` enthält die Karte **Whisper Medium (mehrsprachig)** und
**Qwen3 4B Instruct (Q4_K_M)**. Die zwei Modelle belegen zusammen rund 4,03 GB.
Der Builder lädt die festgelegten Gewichte aus den öffentlichen Modellquellen,
prüft SHA-256 und legt die Lizenztexte unter `/usr/share/doc/cdb-models` ab.
Die Offlineprüfung kontrolliert die Gewichte und Ollama-Layer im fertigen Image.
Ohne diesen Schalter bleibt der bisherige Download im Assistenten verfügbar.
[Whisper-Gewichte](https://huggingface.co/ggerganov/whisper.cpp) ·
[Qwen-Paket](https://ollama.com/library/qwen3:4b-instruct).

Beim ersten Start erkennt der Assistent eine bestehende LAN-Verbindung.
Für WLAN auf **WLAN suchen**, auf den Netznamen und erst nach Eingabe des
Schlüssels auf **Verbinden** tippen. Bis dahin bleibt die bisherige Verbindung
bestehen. Der Image-Bau aktiviert `cdb-network.service` und berechtigt den
Gerätebenutzer für die lokale WLAN-Schnittstelle. Auf einer Karte mit
vorinstallierten Modellen sollen beide Modellkarten **Installiert** anzeigen.
Zum Gerätetest auf einer zweiten Karte den ersten Start ohne Internet durchführen
und mit einem synthetischen Audioclip Transkription und Zusammenfassung prüfen.
Die persönliche Brain-Anmeldung kann später online erfolgen.

Die ReSpeaker-USB-Firmware befindet sich auf dem Mikrofon selbst; ein SD-Image
flasht sie nicht automatisch erneut. Siehe [Mikrofondokumentation](../respeaker.md).

Die root-eigene Erstinitialisierung erstellt nur ein neues Kundenprofil.
Nachher arbeitet die App als Benutzer `cdb`; dessen Passwort ist gesperrt,
SSH ist ausgeschaltet. Der Desktop startet erst nach erfolgreicher Initialisierung.
Der Kunde benötigt keine Terminal-Anmeldung für den Assistenten. Ein abgebrochener
System-Bootstrap erfordert Recovery; die normale WLAN-/Kontoeinrichtung ist fortsetzbar.

## Prüfen und auf die zweite Karte schreiben

Zu jeder Auslieferung gehören Dateiname, Dateigröße, SHA256, Quellcommit,
pi-gen-Commit, öffentliche Schlüssel-Prüfsumme, OS-/Python-Paketlisten und
Teststatus. **Gebaut**, **offline geprüft** und **auf Hardware gebootet** sind
verschiedene Zustände. Ein noch nicht gebootetes Image ist ein Testkandidat.

Das Image vor Weitergabe entpacken beziehungsweise schreibgeschützt über eine
Loop-Datei einhängen. Auf dem endgültigen Root-Dateisystem
`scripts/audit_customer_rootfs.py ROOTFS` ausführen. `scripts/verify_customer_image.sh DATEI.img` führt diese Offlineprüfung einschließlich
Dateisystemkontrolle im isolierten Linux-Builder aus. Es akzeptiert nur reguläre
Image-Dateien, keine physischen Blockgeräte. Bootpartition, Pi-5-Kernel,
Dateisysteme, Dienste und Laufzeitprogramme zusätzlich prüfen. `xz -t` prüft
den komprimierten Export; `shasum -a 256 DATEI.img.xz` liefert die Prüfsumme.

Mit Raspberry Pi Imager **eigenes Image auswählen**, die `.img.xz` wählen und
nur die zweite SD-Karte als Ziel auswählen. Vorhandene Imager-Anpassungen für
Benutzer, SSH und WLAN nicht übernehmen; diese Einrichtung erledigt unser
Assistent. Schreiben und Verifizieren abwarten. Erst danach den Test-Pi sauber
herunterfahren, stromlos machen und die Karten wechseln. Die bisherige Karte
unverändert und beschriftet aufbewahren. Für den ersten Test mindestens 32 GB,
für Aufzeichnungen und lokale Modelle eher 64/128 GB einplanen.

Die Hardwareabnahme prüft: Offline-Willkommen, LAN/WLAN mit falschem und richtigem
Schlüssel, Neustart während Einrichtung, eindeutige Geräteidentität, Kopplung,
Audio/LEDs/Bluetooth, Modellinstallation, synthetische Aufnahme, Queue, CDB,
Timer/Wake sowie signiertes App-Update und Rückkehr. Ohne diese Prüfung keine
Serienfreigabe. Online-Tests nur mit freigegebenen synthetischen Daten durchführen.

## Reproduzierbarkeit und Pflege

Der Build ist durch Quellcommit, Datei-Hashes und Paketlisten nachvollziehbar.
Debian-/Raspberry-Pi-Paketquellen und indirekte Python-Pakete sind noch nicht
vollständig über unveränderliche Snapshots/Hashes eingefroren. Ein späterer
Build desselben App-Commits kann deshalb neuere Systempakete enthalten und ist
nicht zwingend bitidentisch. Vor Serienauslieferung Paketquellen einfrieren,
Lizenz-/Quellcodepflichten prüfen und das komplette Image erneut qualifizieren.
Die privaten Signierschlüssel bleiben ausschließlich außerhalb des Repositorys.

Quellen: [pi-gen](https://github.com/RPi-Distro/pi-gen),
[Pi-5-Prozessor](https://www.raspberrypi.com/documentation/computers/processors.html).

## Optionale lokale Ansagen

Die neue Ansagensteuerung verwendet die bestehenden App-Positivlisten, ohne Runtime- oder Schemawechsel. Frische Images und Updates aktivieren keine Sprache automatisch. Modell, Sprachpaket und `announcements.json` gehören nicht in den Quell-Export. Ein optionales Paket wird separat geprüft und installiert. [Paketformat, Bestandsgeräte und Abnahme](../local-announcements/README.md).
