# Aufnahme stoppt nach wenigen Sekunden

19.10.2026: Die drei jüngsten Aufnahmeprotokolle auf Chris’ Pi melden übereinstimmend `arecord: main:850: audio open error: Device or resource busy`. Der Dienst selbst läuft weiter. Die konfigurierte ReSpeaker-Quelle ist über PipeWire verfügbar; der Hardware-Capture-Knoten ist vom Audiodienst geöffnet. Der Wake-Listener verwendet bereits die exakt auf die ALSA-Karte abgebildete PipeWire-Quelle. Die normale Aufnahme verwendete dagegen weiterhin direkt `arecord`.

StudioApp übergibt jetzt standardmäßig dieselbe vorhandene `native_capture_command`-Funktion an die gemeinsame Python-Engine. Aufnahme und Mikrofontest verwenden damit die exakt konfigurierte Quelle ohne Wechsel auf ein anderes Standardmikrofon. Nicht abgebildete ALSA-Geräte behalten den bisherigen expliziten Fallback. Injizierte Testquellen bleiben erhalten. Wake-Sperren und Einstellungen werden nicht verändert.

13 gezielte Tests bestanden: Zuordnung in StudioApp und Mikrofontest, injizierte Quelle, exakte Kartenauflösung, Ausschluss von Monitorquellen und mehrdeutigen Quellen sowie Audiofreigabe. Ein erster breiter Lauf gegen die alte lokale Engine 0.2.6 hatte einen unabhängigen Fehler (fehlende Recorder.control-Methode); die aktuelle Anwendung pinnt bereits 0.2.7. Der anschließende breite Lauf mit dem aktuellen Engine-Quellstand bestand vollständig: 76 Tests.

## Installation am Pi

Mit ausdrücklicher Freigabe installiert: **0.5.62**, signierte Sequenz **19**,
Quellcommit `3a3f5e449560a2d9ac4873a6925ac4620724a7ad`. Der laufende Pi enthielt
bereits die Fernbedienungs-Zwischenversion 0.5.61 aus dem anderen Feature-Branch.
Alle 118 Ausgangsdateien wurden gegen diesen Stand geprüft; deshalb basiert die
Auslieferung auf dessen Commit c78384d, mit der Aufnahmekorrektur ergänzt.
Nur `web_server.py` unterscheidet sich im Laufzeitpaket. Keine vorhandene
Fernbedienungsfunktion wurde entfernt. Signatur, unveränderte Runtime,
Wartungsreservierung, atomare Installation und Startprüfung bestanden.
Alle 118 Dateihashes stimmen danach überein. Audio-Konfiguration und gespeicherte
Wake-Freigabe sind identisch; ein privates Datenbank-Backup liegt auf dem Pi.
Die 25 vorherigen Sitzungsdatensätze wurden zusätzlich vollständig verglichen
und sind unverändert. [Installationsnachweis](deployment.json).

Der bereinigte Testaufruf mit korrektem Test-Suchpfad besteht auf dem Mac und
auf dem Pi mit jeweils **133 Tests**. Zwei vorherige Testmodul-Ladefehler im
Aufruf wurden korrigiert, nicht als bestandene Tests gezählt.
[Mac-Protokoll](python-tests-mac.txt) · [Pi-Teststand](pi-tests.json).

Die installierte Nabu-Engine erkennt alle drei positiven Referenzdateien und
verwirft alle neun fremden Rufwortdateien. Dieser Dateitest verwendet weder
Mikrofon noch Lautsprecher und ersetzt keinen gesprochenen Ruf am echten Gerät.
[Referenztest](wake-files.json).

Image-Auswirkung: reine Änderung an der bereits erlaubten Datei web_server.py. Bestehende Geräte benötigen ein App-Update; neue Images übernehmen die Datei aus dem versionierten App-Stand. Keine zusätzlichen Pakete, Dienste, Factory-Änderungen oder Datenmigrationen. Ein neues SD-Image wurde nicht gebaut oder gebootet.


## Echte Aufnahmeprüfung nach Installation

Zwei Starts über die produktiven HTTP-Endpunkte, mit dem echten ReSpeaker und
der installierten Python-Pipeline:

| Versuch | Ziel | WAV-Dauer | Aufnahmefehler |
| --- | ---: | ---: | --- |
| Längere Aufnahme | 180 s | 180,32 s | keine |
| Erneuter Start | 12 s | 12,56 s | keine |

Die Aufnahme blieb jeweils bis zum ausdrücklich angeforderten Stoppen aktiv;
PCM-Zähler und WAV-Länge stimmen mit der verstrichenen Zeit überein. Mono,
16 kHz, beide `recording.log` leer. Während beider Aufnahmen blieb die
Wake-Freigabe eingeschaltet, der Detektor gab jedoch das Mikrofon ab. Nach
jedem Stoppen kehrten Zustand `listening` und ein laufender Capture-Kindprozess
zurück. [Zeitreihe](live-capture.json) · [Bestandsvergleich](data-check.json).

Dies belegt die Behebung des bisherigen Abbruchs nach drei bis vier Sekunden
und den erneuten Start, keinen unbegrenzt langen oder mehrstündigen Betrieb.
Die beiden Testaufnahmen bleiben in der App; sie enthalten keine aus dem
Gerät kopierten oder in Git eingecheckten Audiodaten. Der normale konfigurierte
Verarbeitungsweg der App bleibt erhalten. Der akustische Test mit Chris ist
separat angefragt; Bereitschaft und Referenzdateien werden nicht als Erfolg
eines natürlichen gesprochenen Rufes ausgegeben.

[Image-Exportprüfung](image-export.json): 125 erlaubte Quelldateien, exportierte
web_server.py identisch mit dem installierten Quellstand. Keine neue Runtime,
Factory-Änderung oder Datenmigration; kein neues Image gebaut oder gebootet.
