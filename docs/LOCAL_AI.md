# Native lokale KI · Raspberry Pi 5 / 8 GB

Die bestehende PySide6-App bleibt das native Produkt. Session-Datenbank, IDs, Aufnahmen, Notizen und QSettings-Prompts bleiben erhalten. Neue nullable SQLite-Spalten ergänzen Queue-ID, Zusammenfassung, Fehler und Messwerte. API-Schlüssel sind für den lokalen Betrieb weder nötig noch verwendet. Ein eventuell früher gespeicherter Schlüssel wird nicht ausgelesen oder gelöscht.

## Gemeinsame Komponente

Das Repository `shortcutchris/raspberry_pi_meeting_recorder` enthält die einzige Implementierung für Queue, ALSA-Aufnahme, Wiederanlauf, whisper.cpp, Ollama, Speicherüberwachung, Modellinstallation und Mikrofonprobe. `vendor/README.md` dokumentiert den konsumierten Quellcommit und die SHA-256 des unveränderten Wheels. Die native App braucht keinen HTTP-Webserver. Die vorhandene Web-App bleibt separat lauffähig. Änderungen an der Engine erfolgen ausschließlich im Quellrepository; danach Wheel und Pin gemeinsam aktualisieren.

Native Brücke: `services/local_controller.py` mappt feste Queue-IDs auf Session-IDs. Qt-Signale und Hintergrundaufgaben in `ui/tasks.py` halten langsame Vorgänge aus dem GUI-Thread heraus. Neuverarbeitung erhält einen eigenen Job mit Modell-/Prompt-Snapshot. Die frühere UI-Auswahl beeinflusst nie die Ergebniszuordnung.

## Einmalige Installation

Debian 13 arm64 / Python 3.13.5 wurde am Zielgerät geprüft. `scripts/install-native.sh` legt `venv-local-ai` an und installiert die gepinnten nativen Abhängigkeiten samt beiliegendem Engine-Wheel. Systempython und bisherige `venv` bleiben erhalten. `run.sh` startet die neue Umgebung.

whisper.cpp: v1.8.2 unter `/opt/meeting-recorder/whisper.cpp`, mit CMake Release, ARM-CPU, Ziel `whisper-cli`, drei Build-Threads. Ollama: v0.40.3, offizielles ARM64-Archiv gegen die Release-SHA-256 geprüft; nur CPU-Binärdateien/Libraries installiert, CUDA-Bibliotheken auf dem Pi nicht benötigt. Lokaler systemd-Dienst auf `127.0.0.1:11434`, Cloud aus, ein geladenes Modell/eine Anfrage, Kontext 4096, keep-alive 0. Keine OS-Major-Aktualisierung; gezielt benötigte ALSA/FFmpeg/Build/Sprachsynthese-/Tastaturpakete aktualisieren/installieren.

Modelle werden nur ausdrücklich ausgewählt und heruntergeladen. Empfohlener Stand: Whisper medium mehrsprachig, unquantisiert, und Ollama Qwen3 4B Instruct Q4_K_M (`qwen3:4b-instruct`). Das generische `qwen3:4b` ist aktuell ein Denkmodell; im realen Test wurde sein Ausgabelimit erreicht. Es bleibt als ausdrücklich langsamerer Vergleich auswählbar. Keine `.en`-Variante für Deutsch. large-v3-turbo und weitere Modelle sind Vergleichskandidaten in Dropdowns. 8B ist bei 8 GB kein unkritischer Standard. Gewichte liegen außerhalb Git unter `~/.local/share/cdb-recorder-local/models` und `/var/lib/ollama/models`.

## Native Oberfläche 0.3.0 · Variante A

Die Meetingliste erhält etwa 30 % Breite. Der rechte Bereich enthält eine dominante, mittig beschriftete Aufnahmefläche mit mindestens 72 Pixeln Höhe. Laufzeit und Pegel bleiben darüber sichtbar; Mikrofon- und Modelleinstellungen öffnen ausschließlich über das Zahnrad in einem eigenen Dialog. Ein 650-ms-Schutz verhindert unbeabsichtigtes Start/Stop durch Doppeltippen; laufende Hintergrundaufgaben sperren die Aktion zusätzlich.

Notizen, Transkript und Zusammenfassung belegen Inhaltsreiter mit flexibler Höhe. Metadaten/Titel liegen unter „Details“. Notizen bleiben während Verarbeitung editierbar, KI-Texte sind bis Abschluss schreibgeschützt. Änderungen werden nach 350 ms sowie vor Reiter-/Meetingwechsel und beim normalen Schließen synchron gespeichert. Bei Schreibfehlern bleiben Entwürfe geladen; der Meetingwechsel wird abgebrochen. Polling erneuert nur tatsächlich geänderte Ergebnisse, ohne unveränderten Text, Cursor oder Scrollposition zurückzusetzen. Abgeschlossene Modellartefakte überschreiben anschließend keine Benutzerkorrekturen, auch leere Texte bleiben erhalten.

Die feste Statuszeile zeigt Phase, verstrichene Zeit, wartende Anzahl, Fehler und parallele Aufnahme. Das Tätigkeitssymbol wechselt vier Frames. „Warteschlange anzeigen“ öffnet eine separat scrollende Inline-Liste mit maximal 156 Pixeln Höhe. Unter 700 Pixeln Fensterhöhe wird sie auf 66 Pixel reduziert, damit Aufnahme und Editor erreichbar bleiben. Die Queue-Aktion „Wiederholen“ behält Job-/Modell-/Prompt-Snapshot; „Neu verarbeiten“ im Inhaltsreiter erstellt einen neuen Auftrag mit dem aktuell gewählten Prompt. Seltene Player-Aktionen stehen im Menü „⋯“; Wiedergabe, Pause und Stop bleiben direkt erreichbar. Löschen bleibt bestätigt und für aktive Aufträge gesperrt.

## Bedienung

Die vertraute Hauptansicht mit Aufnahmen links und Recorder/Player/Notizen rechts bleibt erhalten. Keine Web-Oberfläche und keine neue Seitennavigation ersetzen sie.

1. Zahnrad → **Audio und lokale Modelle** → Audio: Hardware-Mikrofon wählen, fünf Sekunden aufnehmen, Pegel ansehen und Probe anhören. Ohne Mikrofon bleibt „Einrichtung abschließen“ gesperrt.
2. Modelle: Whisper und Zusammenfassungsmodell in Dropdowns wählen; fehlende Gewichte ausdrücklich herunterladen. Fortschritt, Fehler, Lizenz und Speicherprüfung sind sichtbar. „Beide Modelle mit Testaufnahme prüfen“ erzeugt künstliche deutsche Sprache, verarbeitet sie wirklich und zeigt Messwerte. Das ist kein Qualitätsbenchmark eines Meetingraums.
3. Bereit: Voraussetzungen prüfen und Einrichtung abschließen. Lokale Auswahl wird sofort gespeichert; Abbrechen verwirft sie nicht. Allgemeine Sprache/Prompts bleiben im bisherigen Einstellungsbereich.
4. Aufnahme: ein Start/Stop-Button, keine Aufnahme-Pause. Stop finalisiert Audio im Hintergrund und reiht den Job atomar hinten ein. Die gespeicherte Einreihungszeit bestimmt FIFO, nicht der Aufnahmebeginn. Ein Worker verarbeitet je Meeting zuerst ASR und danach Zusammenfassung. Neue Aufnahme bleibt in beiden Phasen möglich.
5. In der festen Statuszeile: bewegter Aktivitätsindikator, aktueller Schritt, verstrichene Zeit, Anzahl und Reihenfolge wartender Aufnahmen. Keine erfundenen Prozentwerte oder ETA. Die Anzeige läuft auf einem Qt-Timer; Engine/SQLite/Netzwerk/Finalisierung laufen in Hintergrundaufgaben.
6. Meeting auswählen → Inhaltsreiter Notizen/Transkript/Zusammenfassung. Die bisherige Prompt-Auswahl steuert „Verarbeiten“. Texte können nach Abschluss korrigiert und automatisch gespeichert oder als Markdown/Text exportiert werden. CSV-Export, Player, Notizen und Suche bleiben verfügbar.
7. Bei Fehlern: Statuszeile und Warteschlange zeigen Fehler; „Wiederholen“ in der Warteschlange nutzt denselben Job und stellt ihn hinten an. „Neu verarbeiten“ im Inhaltsreiter verwendet die aktuelle Modell-/Prompt-Auswahl. Andere Jobs werden durch Fehler nicht blockiert.
8. Alte `pending`-Einträge ohne dauerhafte Job-ID werden als unterbrochen markiert, mit einer Wiederholen-Aktion. Inhalte bleiben erhalten; bestehende Meetings werden nicht automatisch neu verarbeitet.

Prompts verwalten: Einstellungen → Allgemein und Prompts. Bestehende benutzerdefinierte Prompts bleiben erhalten; Standardprompts können durch einen neuen eigenen Prompt ergänzt werden. Ausgabe/Textverarbeitung bleibt über den gewählten Arbeitsauftrag steuerbar.

Wiedergabe liest 2048 Frames pro Callback, statt die gesamte Datei beim Auswählen einzulesen. Aufnahme schreibt 16-kHz-Mono-PCM direkt auf SD, synchronisiert regelmäßig und finalisiert WAV blockweise im Hintergrund. 115,2 MB Audio/Stunde; vorübergehend doppelter Audioplatz beim Abschluss. Speicherreserve und sechs Stunden Höchstdauer schützen den Abschluss. Keine automatische Löschung. Bei bewusster Löschung wird der Queue-Job verborgen, damit die Session nicht wieder erscheint; bisherige Audit-Artefakte bleiben erhalten. Laufende Jobs sind gegen Löschen geschützt.

## Daten und Sicherung

Alte Datenbank: `data/sessions.db` im vorhandenen Projekt. Alte Audio-Pfade werden beibehalten. Neue Queue/Audio: `~/.local/share/cdb-recorder-local`. `CDB_SESSION_DB` und `CDB_LOCAL_DATA` erlauben isolierte Testdaten; nicht zwischen Produktiv- und Testablage mischen. Native App und Web-Dienst nutzen denselben exklusiven Lock je Queue-Ablage und können sie nicht gleichzeitig verarbeiten. Normalerweise verwenden sie getrennte Ablagen.

Vor Aktualisierung: keine aktive Aufnahme, App geordnet schließen, SQLite über Backup-API sichern, Projekt (ohne große Runtime) sowie `~/.config/AudioSessions` sichern. Am Zielgerät liegt der Ausgangsstand unter `~/recorder-backups/pre-local-ai-20261011`. Sicherungen enthalten persönliche Daten und bleiben mit privaten Rechten auf dem Pi. Keine Aufnahmen/Transkripte/Schlüssel/Modelle in Git oder Dropbox synchronisieren.

## Rollback

Neue App zuerst schließen; eine aktive Aufnahme vorher sicher beenden. Alten Quellstand aus Git `83d9631` in einer separaten Ablage wiederherstellen und mit der unveränderten alten `venv` starten. Bei notwendigem Datenrollback die konsistente `sessions-consistent.db` aus der Sicherung in eine separate Test-/Rollbackablage kopieren; aktuelle Datenbank und neue Aufnahmen vorher sichern. Neue nullable Spalten sind abwärtskompatibel und allein kein Grund, neue Meetings zu verwerfen. Alte Prompts/QSettings wurden nicht ersetzt. Neue Engine-Daten und Modelle bleiben separat erhalten. Bei Bedarf Ollama mit `sudo systemctl stop ollama` entladen; nicht ungeprüft Modellablagen löschen.

## Grenzen und Abnahme

Ausführungsgeschwindigkeit und Erkennungsqualität müssen mit deutschen Raumaufnahmen gemessen werden. Langsame SD, thermische Drosselung oder knapper RAM dürfen nicht durch dauerhaften Swap kaschiert werden. 4096 Kontexttokens, abschnittsweise Zusammenfassung und Modell-Entladung begrenzen Speicher; gemessene Spitzen sind keine Obergrenze für andere Meetings. RSS-Messungen unter Linux werden gesampelt; aggregierter Ollama-RSS kann gemeinsame Seiten mehrfach zählen.

Ein physisch fehlendes Mikrofon verhindert die vollständige Audio-Einrichtung. Synthetische Prozess-/Sprachtests ersetzen keinen USB-/Raum-/Lautsprechertest. Physischer Stromverlust ist kein automatischer Softwaretest; dafür existieren Prozessabbruch-/Recovery-Tests.

## Installation der System-Runtimes reproduzieren

Nur auf einem unbenutzten Zielgerät bzw. nach sicherem Schließen der App ausführen. Die Basispakete und Python-Umgebung installiert `scripts/install-native.sh`; das lokale Wheel wird zuvor gegen `vendor/SHA256SUMS` geprüft.

```bash
sudo git clone --depth 1 --branch v1.8.2 https://github.com/ggml-org/whisper.cpp /opt/meeting-recorder/whisper.cpp
sudo cmake -S /opt/meeting-recorder/whisper.cpp -B /opt/meeting-recorder/whisper.cpp/build -DCMAKE_BUILD_TYPE=Release
sudo cmake --build /opt/meeting-recorder/whisper.cpp/build --target whisper-cli -j3
```

Geprüfter Whisper-Quellcommit: `4979e04f5dcaccb36057e059bbaed8a2f5288315`.

Ollama v0.40.3: offizielles ARM64-Archiv `https://github.com/ollama/ollama/releases/download/v0.40.3/ollama-linux-arm64.tar.zst`, SHA-256 `5754700747a93ea14db88888f08072386d2da6fbf7dd75be19a684348b9f28b8`. Vor Installation vollständiges Archiv prüfen. `bin/ollama` nach `/usr/bin/ollama`, die CPU-Dateien direkt unter `lib/ollama/` nach `/usr/lib/ollama/` installieren; CUDA-Unterverzeichnisse werden am Pi nicht gebraucht. Am geprüften Zielgerät wurden diese CPU-Dateien aus dem verifizierten Archiv extrahiert und übertragen. Nutzer `ollama`, private Modellablage `/var/lib/ollama/models`, systemd-Service:

```ini
[Unit]
Description=Ollama local CPU inference for CDB Recorder
After=network.target
[Service]
ExecStart=/usr/bin/ollama serve
User=ollama
Group=ollama
Environment=OLLAMA_HOST=127.0.0.1:11434
Environment=OLLAMA_MODELS=/var/lib/ollama/models
Environment=OLLAMA_NO_CLOUD=1
Environment=OLLAMA_NUM_PARALLEL=1
Environment=OLLAMA_MAX_LOADED_MODELS=1
Environment=OLLAMA_CONTEXT_LENGTH=4096
Environment=OLLAMA_KEEP_ALIVE=0
Restart=on-failure
UMask=0077
NoNewPrivileges=true
[Install]
WantedBy=multi-user.target
```

Desktop-Verknüpfung und Autostart des geprüften Pi verweisen bereits auf `run.sh` im bestehenden Projekt; dieses startet `venv-local-ai`. Die alte `venv` bleibt für Rollback unverändert. Kein GitHub-Token liegt auf dem Pi.

## Prüfbefehle

```bash
LANG=C.UTF-8 LC_ALL=C.UTF-8 PYTHONIOENCODING=utf-8 QT_QPA_PLATFORM=offscreen venv-local-ai/bin/python -m unittest discover -s tests -v
# Nur ausdrücklich; benutzt ausschließlich getrennte Testdaten und synthetisches Audio:
venv-local-ai/bin/python scripts/native_acceptance.py /home/chris/local-ai-staging/qt-acceptance
```

45 gemeinsame Engine-/Web-/Recovery-/Setup-Tests und 8 native Qt-/Migrations-/Mapping-/Player-/Aktivitätsprüfungen. Linux-Parent-Death-Test läuft auf dem echten Pi; auf macOS wird genau dieser Linux-Test übersprungen. Das Qt-Abnahmeskript bedient Start/Stop, nimmt während ASR und während Summary erneut auf und wartet auf FIFO-Verarbeitung aller drei Jobs. Synthetische Prozesszuführung ersetzt ausdrücklich kein echtes Mikrofon. Linux-Kinder erhalten einen Parent-Death-Signal-Wrapper, sodass nach einem App-Absturz kein verwaister Recorder weiter aufzeichnet.

Der direkte Hugging-Face-Download wurde im Zielnetz zunächst zurückgesetzt. Die ersten Whisper-Gewichte wurden deshalb am Mac aus der offiziellen Quelle heruntergeladen, gegen SHA-256 geprüft und anschließend über LAN auf den Pi übertragen. SHA-256 medium: `6c14d5adee5f86394037b4e4e8b59f1673b6cee10e3cf0b11bbdbee79c156208`. Weitere Downloads sind explizit in der UI möglich; Netzwerkfehler werden dauerhaft angezeigt und benötigen einen erneuten Versuch.

## UI-Abnahme Variante A

`scripts/layout_acceptance.py NEUER_TESTORDNER` startet eine ausdrücklich isolierte Qt-Abnahme mit künstlicher PCM-Quelle und kontrollierter Test-Inferenz. Sie prüft Start/Stop, Doppeltippen, neue Aufnahme während ASR und Zusammenfassung, unabhängige Meetingauswahl, Queue ein/aus, Inhaltsreiter, Details, Fehler und Wiederholen. Keine persönliche Datenbank und kein reales Mikrofon werden dabei benutzt. Die realen Modelle wurden in der vorhergehenden Engine-Abnahme geprüft; der UI-Test lädt sie wegen des stillstehenden Lüfters nicht erneut.

Die 10 nativen Tests ergänzen insbesondere Speicherung bei Auswahl-/Reiterwechsel, Cursor/Scrollschutz, fehlgeschlagene Speicherung, Erhalt korrigierter KI-Texte über Poll/Neustart und Touch-Geometrie bei 1280×720 und 1024×600. Die Engine bleibt unverändert 0.2.3.

### Lautsprecher am Pi (ab Studio 0.5.16)

Unter **Einstellungen → Audio → Lautsprecher** einen vorhandenen Pi-Ausgang wählen, Lautstärke mit −/+ ändern und **Testton am Pi** starten. Der Test spielt links und rechts je einen kurzen Ton direkt am Gerät. Ohne angeschlossenen Ausgang bleibt er gesperrt; „Dummy Output“ zählt nicht als Lautsprecher. Änderungen werden direkt übernommen. Während einer Aufnahme stehen diese Einstellungen nicht zur Verfügung.

Die Audioausgabe verwendet die vorhandene PipeWire/PulseAudio-Benutzersitzung mit `pactl` und `paplay` (Paket `pulseaudio-utils`). Der Studio-Dienst muss unter demselben Benutzer wie die Audiositzung laufen. Kein Root-Dienst und keine neue Netzwerkfreigabe erforderlich. Aufnahmen im Browser nutzen weiterhin den Ausgang des jeweiligen Browsergeräts; der Testton läuft auch beim Fernzugriff immer auf dem Pi. Gerätauswahl liegt unter dem Studio-Datenordner in `speaker.json`; Systemroute, Lautstärke und Stummschaltung verwaltet die Audiositzung.
