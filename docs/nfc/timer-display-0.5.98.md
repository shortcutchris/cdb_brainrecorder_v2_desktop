# USB-Timerdisplay im gemeinsamen Raummodus · 0.5.98

23.11.2026. Das angeschlossene Zusatzdisplay zeigt „Timer Display · Pi Recorder“,
aber keine auf dem Pi gestarteten Timer.

## Ursache und Änderung

Der lesende Endpunkt `/api/lcd/timers` hat im Raummodus pauschal eine leere Liste
ausgeliefert. Seit Anmeldung der Standard ist, betraf das auch angemeldete Nutzer.
Ein zusätzlicher Einschalter am Display ist nicht erforderlich.

Der Endpunkt verwendet jetzt dieselbe Kontozuordnung wie die Timeransicht des Pi:
nur Timer und Erinnerungen des aktuell angemeldeten Kontos, bei Abmeldung keine.
Der Filter läuft vor Zählung und Begrenzung auf 16 Einträge. Fremde Einträge können
eigene daher weder verdrängen noch über die Gesamtzahl sichtbar werden.
Kontowechsel und Abfrage sind mit derselben Gerätesperre synchronisiert.

Auf dem öffentlich sichtbaren Zusatzdisplay stehen im Raummodus nur die
allgemeinen Bezeichnungen „Timer“ beziehungsweise „Erinnerung“. Persönliche
Titel bleiben am angemeldeten Pi. Restzeit, Status, Sortierung, Seiten- und
Einzelansicht bleiben im bestehenden USB-Protokoll unverändert. Keine neue
Firmware, Portwahl oder Freigabe pro Timer erforderlich.

## Prüfung

- Pi rein lesend geprüft: Zusatzdienst aktiviert und aktiv, ein Gerät mit der
  USB-Kennung `303a:4001`, Produkt `CDB Timer Display`; Dienst hält `/dev/ttyACM0`
  offen. API antwortet HTTP 200. Vor Änderung leerer Timerexport bestätigt.
- 38 LCD-/Raumtests bestanden, darunter acht fokussierte Prüfungen: Eigentümer und Firmenwechsel, Abmeldung,
  allgemeiner Titel, positive Restzeit, Status, mehr als 16 fremde Timer,
  Begrenzung, Protokollbindung, Authentifizierung und lesender Zugriff.
- Kein Timer am Benutzergerät angelegt, keine Audioausgabe gestartet, kein
  USB-Port zusätzlich geöffnet und keine Firmware geflasht. Sichtbare Abnahme
  mit einem vom Benutzer gestarteten Timer nach App-Update bleibt erforderlich.

## Auslieferung

Mit Recorder 0.5.98 auf dem Pi installiert; kein Firmwarewechsel nötig.
[Installationsnachweis](098-deployment.json). Der Endpunkt liefert nach dem
App-Neustart ohne Anmeldung korrekt keine Timer. Die sichtbare Prüfung eines
neu gestarteten Timers nach Anmeldung wurde beim Benutzer angefragt.

## App-Update und Kundenimage

Vorhandene versionierte App-Dateien, keine neuen Pakete oder Konfigurationswerte.
Der bereits laufende Zusatzdienst erhält die korrigierten Daten vom aktualisierten
Recorder-Endpunkt; sein Protokoll und seine Firmware bleiben kompatibel.
Die bestehenden Freigabelisten übernehmen die Änderung auch in saubere
Image-Baupakete. Dieser Fix ist kein gebautes oder hardwaregeprüftes SD-Image.
