# Live-Gespräch mit CDB Voice One

## Bedienung

In der linken Navigation **Live-Gespräch** öffnen. Nach der bestehenden Microsoft-/Brain-Anmeldung werden die persönlich verfügbaren Knowledge Areas geladen. Ein bis acht Bereiche auswählen; der Standardbereich ist vorausgewählt. Die Auswahl gilt nur für das Gespräch und ändert das Übertragungsziel des Recorders nicht.

**Mikrofon freigeben** fordert die Browserberechtigung an. Erst nach Bestätigung wird die Geräteauswahl aktiv. Bereits freigegebene Geräte werden beim Öffnen ohne erneuten Mikrofonstart geladen; **Geräte aktualisieren** liest sie erneut ein. Während einer offenen Berechtigungsabfrage bleibt die Auswahlansicht sichtbar und **Abbrechen** gibt die Reservierung frei. Fehler bleiben mit einer konkreten Anleitung im Bildschirm sichtbar. Ein erkanntes ReSpeaker wird ausgewählt; bei anderen Mikrofonen ist eine ausdrückliche Auswahl nötig. **Gespräch starten** verbindet anschließend CDB Voice One. Der Verlauf zeigt die tatsächlich vom Brain empfangenen Transkriptfragmente mit „Du“ und „Voice One“. Längere Verläufe haben direkt anwählbare Seiten.

**Mikro stumm** deaktiviert den sendenden Audio-Track. **Gespräch beenden** stoppt Mikrofon und Lautsprecher sofort und schließt die Brain-Sitzung. **Neues Gespräch** beginnt einen leeren Verlauf; abgeschlossene lokale Verlaufsdateien bleiben erhalten. Nach einem Neustart wird beim Öffnen die letzte abgeschlossene Unterhaltung desselben Brain-Kontos geladen.

Die Audioverbindung verwendet **Mikrofon und Lautsprecher des Browsers**: auf dem Touchdisplay den Pi, bei Fernzugriff den eigenen Computer. Die Audioauswahl für Recorder-Aufnahmen ist davon unabhängig. Es gibt keine automatische Übernahme des Pi-Mikrofons durch einen entfernten Browser und keine automatische Aufnahme des Raums. Der Browser braucht einen sicheren Kontext, beispielsweise die lokale Kiosk-Adresse `http://localhost:8088` beziehungsweise eine localhost-Weiterleitung. Eine unverschlüsselte LAN-IP genügt für Browser-Mikrofonzugriff nicht.

## Zustände und Ressourcen

- Eine Audioreservierung erfolgt **vor** der Browser-Berechtigungsabfrage. Eine zweite Aufnahme, ein zweites Gespräch, Mikrofontest und Änderungen an Audio-/Kontoeinstellungen sind währenddessen gesperrt.
- Während eines Gesprächs bleibt die Live-Ansicht geöffnet; Recorder, Bibliothek, Einstellungen und Warteschlangenansicht sind gesperrt. Bereits laufende Hintergrundverarbeitung kann weiterlaufen.
- Spät erteilte Mikrofonberechtigungen nach Abbruch werden sofort wieder freigegeben; sie öffnen keine neue Gesprächssitzung.
- Fehlgeschlagener Start, verlorene Browser-Verbindung, Tab im Hintergrund, Abmeldung und Ablauf der maximalen Gesprächszeit schließen die Sitzung. Die Browser-Reservierung läuft ohne Verlängerung nach 25 Sekunden ab.
- Abbruch während des entfernten Sitzungsstarts bleibt gesperrt, bis die möglicherweise verspätet angelegte Brain-Sitzung wieder geschlossen ist.
- Die App sendet keine Steuerbefehle über den WebRTC-Datenkanal. Mitschriften stammen ausschließlich aus dem authentifizierten Brain-Ereignisstrom.

## Anbindung und Sicherheit

Referenz: `cdb-knowledge-mobile/src/services/liveApi.ts`, `liveWebRtcTransport.ts` sowie `docs/LIVE-CONTRACT.md` (gelesen am 13.10.2026). API-Basis `/api/v1/tqs/voice-live`: capabilities, sessions, heartbeat, close und SSE events. Das bestehende Microsoft-Token bleibt im Python-Backend. Es wird weder an Browser noch an Azure weitergereicht. Azure-Zugang und Modellrouting verwaltet der CDB-Dienst.

Die Knowledge-Area-Rechte werden vor jedem Start frisch abgefragt und zusätzlich vom CDB-Backend geprüft. Bereichswechsel während einer Sitzung sind nicht erlaubt. Die Sitzung bleibt an Server, Benutzer und Mandant gebunden. Lokale JSON-Verläufe unter `<data-root>/live/` haben Dateirechte 0600 und enthalten keine Tokens, SDP-Antworten oder Rohaufnahmen. Beim Kontowechsel blendet die App fremde Verläufe sofort aus.

Am 13.10.2026 meldete der vorhandene Staging-Zugang: Live aktiviert, maximal acht Bereiche, 20 Minuten Gespräch, Herzschlag alle 15 Sekunden, Sprachen Deutsch/Englisch und Unterstützung für Chat-Bindung. Diese Version speichert den Verlauf lokal; eine Zuordnung zu einem bestehenden CDB-Chat wurde nicht eingebaut. Die Freigabe hängt von der jeweiligen Brain-Umgebung ab.

## Prüfungen

Automatisierte Tests prüfen gültige Bereiche, Besitzer der Reservierung, doppelte Starts, fehlgeschlagene Verbindungen, Abbruch während eines verzögerten Starts, Ablauf der Browser-Reservierung, Kontowechsel, lokale Wiederherstellung sowie verspätete Browser-Mikrofonfreigaben. Reale Browser-, ReSpeaker- und CDB-Abnahme wird im Release-/Testprotokoll separat dokumentiert; bestandene Mock-Tests sind kein Nachweis eines echten Sprachgesprächs.

## Mikrofonfreigabe 0.5.19

Das Platzhalterfeld bedeutet keine Gerätebelegung. Am 13.10.2026 war das ReSpeaker auf dem Pi als PipeWire-Eingang vorhanden, beide PCM-Geräte waren frei, Recorder und Live-Service im Ruhezustand. Die konkrete Browserfreigabe am Touchdisplay war noch nicht bestätigt. Der neue Ablauf trennt fehlende Berechtigung, fehlendes Gerät und nicht lesbares/belegtes Mikrofon. Bestehende Browser-Wiedergabe und Mikrofon-Testplayer werden vor der Freigabe und dem Gesprächsstart pausiert. 60 JavaScript-Tests bestanden, inklusive Abbruch während der Freigabe, persistenter Fehlermeldung, vorhandener Berechtigung und Wiedergabestopp.

Browservertrag: [MDN getUserMedia](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia), [MDN enumerateDevices](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/enumerateDevices). Keine automatische Änderung von Browserberechtigungen oder globalen Chromium-Sicherheitseinstellungen.
