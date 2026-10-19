# Aufnahme stoppt nach wenigen Sekunden

19.10.2026: Die drei jüngsten Aufnahmeprotokolle auf Chris’ Pi melden übereinstimmend `arecord: main:850: audio open error: Device or resource busy`. Der Dienst selbst läuft weiter. Die konfigurierte ReSpeaker-Quelle ist über PipeWire verfügbar; der Hardware-Capture-Knoten ist vom Audiodienst geöffnet. Der Wake-Listener verwendet bereits die exakt auf die ALSA-Karte abgebildete PipeWire-Quelle. Die normale Aufnahme verwendete dagegen weiterhin direkt `arecord`.

StudioApp übergibt jetzt standardmäßig dieselbe vorhandene `native_capture_command`-Funktion an die gemeinsame Python-Engine. Aufnahme und Mikrofontest verwenden damit die exakt konfigurierte Quelle ohne Wechsel auf ein anderes Standardmikrofon. Nicht abgebildete ALSA-Geräte behalten den bisherigen expliziten Fallback. Injizierte Testquellen bleiben erhalten. Wake-Sperren und Einstellungen werden nicht verändert.

13 gezielte Tests bestanden: Zuordnung in StudioApp und Mikrofontest, injizierte Quelle, exakte Kartenauflösung, Ausschluss von Monitorquellen und mehrdeutigen Quellen sowie Audiofreigabe. Ein erster breiter Lauf gegen die alte lokale Engine 0.2.6 hatte einen unabhängigen Fehler (fehlende Recorder.control-Methode); die aktuelle Anwendung pinnt bereits 0.2.7. Der anschließende breite Lauf mit dem aktuellen Engine-Quellstand bestand vollständig: 76 Tests.

Noch nicht auf dem laufenden Pi installiert; keine neue Raumaufnahme gestartet, kein Dienst neu gestartet und keine Benutzerkonfiguration verändert. Der echte Daueraufnahme-Nachtest steht nach Installation aus.

Image-Auswirkung: reine Änderung an der bereits erlaubten Datei web_server.py. Bestehende Geräte benötigen ein App-Update; neue Images übernehmen die Datei aus dem versionierten App-Stand. Keine zusätzlichen Pakete, Dienste, Factory-Änderungen oder Datenmigrationen. Ein neues SD-Image wurde nicht gebaut oder gebootet.
