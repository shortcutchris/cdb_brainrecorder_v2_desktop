# Live-Gespräch mit CDB Voice One

## Bedienung ab 0.5.20

In der Navigation **Live-Gespräch** öffnen. Nach der bestehenden Microsoft-/Brain-Anmeldung werden die persönlich verfügbaren Knowledge Areas geladen. Ein bis acht Bereiche auswählen; der Standardbereich ist vorausgewählt. Diese Auswahl verändert das Übertragungsziel des Recorders nicht.

Unter **Audio am Raspberry Pi** stehen das eingerichtete Mikrofon und der gewählte Lautsprecher. **Audioeinstellungen** führt zu den vorhandenen Mikrofon- und Lautsprecherseiten. Ein fehlendes Mikrofon oder ein stummgeschalteter Ausgang sperrt den Gesprächsstart mit einem Hinweis. Nach Änderungen zurückkehren und bei Bedarf **Aktualisieren** wählen.

**Gespräch starten** verbindet CDB Voice One. Python liest das Pi-Mikrofon und spielt die Antworten über den Pi-Lautsprecher ab. Der Browser steuert ausschließlich die Oberfläche: Es gibt keine zusätzliche Mikrofonfreigabe, keinen zweiten Geräteschalter und keine Audioübertragung über den Browser. Das gilt auch bei Fernzugriff: **Gesprochen und gehört wird am Pi**, nicht am entfernten Computer. Die Browser-Mikrofonschnittstelle ist für diese App gesperrt.

**Mikro stumm** ersetzt ausgehende Audioblöcke durch Stille. Beim Wiedereinschalten werden während der Stummschaltung gepufferte Blöcke verworfen. **Gespräch beenden** beendet Pi-Audio und die Brain-Sitzung. **Neues Gespräch** öffnet wieder die Bereichsauswahl. Der Verlauf zeigt ausschließlich empfangene Transkriptfragmente mit „Du“ und „Voice One“; längere Verläufe haben direkt anwählbare Seiten. Die letzte abgeschlossene Unterhaltung desselben Brain-Kontos wird beim erneuten Öffnen wiederhergestellt.

## Zustände und Ressourcen

- Vor dem Audiozugriff wird das Gerät für das Gespräch reserviert. Aufnahme und Live-Gespräch schließen sich aus, auch bei gleichzeitigem Zugriff aus mehreren Browsern.
- Während des Gesprächs sind Recorder, Bibliothek, Einstellungen, Warteschlangenansicht und Gerätekonfiguration gesperrt. Bereits laufende Hintergrundverarbeitung darf weiterlaufen.
- Abbruch während des Verbindungsaufbaus, fehlende Geräte, Verbindungsfehler, Abmeldung und Zeitlimits schließen die Sitzung und geben die Audioprozesse frei. Während der vollständigen Freigabe bleibt der Zustand „Gespräch wird beendet“ gesperrt.
- Der steuernde Browser verlängert seine Reservierung alle fünf Sekunden. Bleibt er länger als 25 Sekunden aus, endet das Gespräch. Ein bloßer Wechsel des sichtbaren Tabs löst keinen absichtlichen Abbruch aus; pausiert der Browser Hintergrundtimer zu lange, greift trotzdem dieses Zeitlimit.
- Ein anderer Browser kann das laufende Gespräch beenden, aber nicht die Stummschaltung des Eigentümers ändern.
- Der ReSpeaker-Ring zeigt das aktive Gespräch blau und App-Stumm rot blinkend. Die physische Stummtaste behält Vorrang. Nach Ende wird die normale Geräteanzeige wiederhergestellt.

## Technischer Audioweg

`services/live_audio.py` verwaltet WebRTC mit `aiortc`, PCM-Eingang mit 16 kHz und Wiedergabe mit 24 kHz. Das konfigurierte Pi-Mikrofon und der konfigurierte PipeWire-Ausgang werden explizit adressiert; es gibt keinen stillen Wechsel auf ein anderes Gerät. ALSA-Geräte werden anhand Kartenkennung und Gerätenummer der exakt passenden PipeWire-Quelle zugeordnet (`parec`), damit Aufnahme und Wiedergabe auf derselben USB-Soundkarte gleichzeitig funktionieren. Ohne passende Quelle bleibt nur das ausdrücklich gewählte ALSA-Gerät als Alternative; mehrdeutige Zuordnungen brechen ab. Der Eingabepuffer umfasst maximal vier Blöcke à 20 ms. Rohaufnahmen werden nicht auf Platte gespeichert.

Audio-Kindprozesse gehören dem Backend, werden bei dessen Ende beendet und bei normalem Gesprächsende abgewartet. Erst danach wird die Aufnahme wieder freigegeben. Die App sendet keine Steuerbefehle über den WebRTC-Datenkanal; Mitschriften stammen ausschließlich aus dem authentifizierten Brain-Ereignisstrom.

Installation: zusätzlich zu den bisherigen Audio-Werkzeugen wird `aiortc==1.15.0` aus `requirements.txt` benötigt. Referenz: [aiortc API](https://aiortc.readthedocs.io/en/latest/api.html).

## Brain-Anbindung und Verläufe

Referenz ist `cdb-knowledge-mobile/src/services/liveApi.ts`, `liveWebRtcTransport.ts` und `docs/LIVE-CONTRACT.md` (13.10.2026). API-Basis `/api/v1/tqs/voice-live`: capabilities, sessions, heartbeat, close und SSE events. Das bestehende Microsoft-Token bleibt im Python-Backend und wird für die autorisierten CDB-Anfragen verwendet. Zugang zum Modell und Modellrouting verwaltet CDB.

Knowledge-Area-Rechte werden vor jedem Start frisch abgefragt und zusätzlich von CDB geprüft. Bereichswechsel während eines Gesprächs sind gesperrt. Die Sitzung ist an Server, Benutzer und Mandant gebunden. Lokale JSON-Verläufe unter `<data-root>/live/` haben Rechte 0600 und enthalten keine Tokens, SDP-Antworten oder Rohaufnahmen. Beim Kontowechsel verschwinden fremde Verläufe aus der Ansicht.

Staging meldete am 13.10.2026 maximal acht Bereiche, 20 Minuten Gespräch und einen CDB-Herzschlag alle 15 Sekunden. Diese Version speichert den Verlauf lokal; eine Zuordnung zu einem bestehenden CDB-Chat wurde nicht eingebaut. Die Freigabe hängt von der jeweiligen Brain-Umgebung ab.

## Prüfungen und Versionswechsel

[Abnahme 0.5.20](native-live-0.5.20/README.md): echte CDB-Sitzung mit synthetischer Sprache, Pi-Audioprozesse, Stumm/Weiter, gegenseitige Sperren, Abbruch und Freigabe sowie UI-Nachweise. Automatisierte Tests unterscheiden künstliche Quellen und echte Hardware; eine empfangene Audioantwort allein bestätigt nicht, dass ein physisch angeschlossener Lautsprecher hörbar ist.

0.5.18 und 0.5.19 verwendeten noch Browser-Audio. Deren Mikrofonfreigabe und separate Geräteauswahl wurden mit 0.5.20 entfernt. Nach dem Update lädt der Kiosk die neue Oberfläche neu; vorhandene Browserberechtigungen werden nicht mehr genutzt.
