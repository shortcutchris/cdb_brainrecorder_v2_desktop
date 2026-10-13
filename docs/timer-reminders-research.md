# Entscheidungsvorlage: lokale Timer und Erinnerungen im Raspberry-Pi-Recorder

Stand: 13.10.2026 · Untersuchung, keine Implementierung oder Bereitstellung

## Empfehlung

**Umsetzen als lokale Gerätefunktion mit SQLite, unabhängig von Browser und Voice-One-Sitzung. Sprachsteuerung über eine ausdrücklich erweiterte CDB-Tool-Brücke anschließen.** Touchbedienung und Zeitplanung sind clientseitig möglich; die vollständige Sprachsteuerung im bestehenden Voice-One-Vertrag benötigt TQS- und BFF-Unterstützung. Das Modell interpretiert den Wunsch, aber der Pi validiert, speichert, bestätigt und löst aus.

Als erste Version: einmalige Countdown-Timer und datierte Erinnerungen; Stellen, Anzeigen, Ändern, Löschen, Quittieren und Schlummern. Wiederholungen, Cloud-Synchronisierung und ein ständig lauschendes Aktivierungswort separat behandeln. „Wie Alexa“ beschreibt hier die Bedienung, keine zugesicherte vollständige Alexa-Parität. Der vorhandene Live-Start ist explizit, zeitlich begrenzt und mit Aufnahme gegenseitig gesperrt. Ein Zuruf außerhalb eines Live-Gesprächs würde eine zusätzliche Spracherkennung und Aktivierungslogik benötigen.

**Freigabebedingung für Sprache:** CDB bestätigt einen versionierten Vertrag für lokale Werkzeugausführung, Wiederzustellung und Ergebnisrückgabe. Ohne diesen Vertrag keine Erfolgsmeldung des Modells und kein Behelf durch das Auswerten von Assistententranskripten.

## 1. Befunde aus dem vorhandenen System

Lesend geprüft wurde `/Users/chris/Dropbox/git_reps_v3/cdb_brainrecorder_v2_desktop`, HEAD zum Prüfzeitpunkt `d710b0d90b2f7c6ef623aff5d9a55fec19aa1ac7`. Arbeitsdateien können sich wegen paralleler Arbeit unabhängig davon verändern. Keine Dateien in vorhandenen Repositories wurden geändert, keine Anwendung gestartet und keine authentifizierten Serveraktionen ausgeführt.

| Quelle | Beobachtung | Konsequenz |
|---|---|---|
| `services/live_conversation.py`, `setup`, `_start` | CDB-Capabilities; Start mit SDP, Bereichs-IDs, Sprache, UUID; opaque Session-Handle | Keine Übergabe eigener Tooldefinitionen im derzeitigen Startbody |
| dieselbe Datei, `_frame`, `_read_events`, `_events` | Authentifiziertes SSE; verarbeitet `state`, `transcript`, `search`, `closed`; Wiederverbindung ohne dauerhaften Eventcursor | Neue Toolereignisse und Zustandsabgleich erforderlich; SSE allein liefert keine zuverlässige Auftragswarteschlange |
| `services/live_audio.py`, `_open` | Pi-Mikrofon/Pi-Lautsprecher via Python und WebRTC; `oai-events` ausdrücklich nur lesend | Nicht einfach Steuerbefehle auf dem Datenkanal ergänzen |
| dieselbe Datei, `PcmGate`, `mute` | Mikrofonmute verwirft alte Blöcke und sendet Stille; Ausgabe ist davon getrennt | Mikrofonmute bedeutet nicht Alarmmute |
| dieselbe Datei, Suchton | Eigener Suchklang, Koordinierung mit Sprache und Ausgabemeter | Alarm und Suchklang brauchen gemeinsame Audioentscheidungen |
| `services/app_activity.py` | Abgeleitete Aktivität; Pause zählt weiterhin als Aufnahme; Live reserviert Audio auch bei Aufbau/Abbau | Scheduler darf durch diese Zustände nicht blockieren; Audio muss sie beachten |
| `web_server.py`, `StudioApp.action` | `control_lock` serialisiert Aktionen; Live sperrt fast alle anderen Pfade, Bluetooth ebenfalls | Timer-CRUD und Alarmquittierung gezielt zulassen, sonst sind sie gerade während Live unbedienbar |
| `web_server.py`, Zustand/Schließen | Gemeinsamer Zustand und kontrollierter Service-Lebenszyklus | Lokalen Service hier anbinden; nicht im Browser-Countdown |
| `services/cdb_integration.py` | Token bleibt im Backend; Bindung an Server, Benutzer, Mandant; SQLite-Publikationen | Identitätsgrenzen für Sprachaufträge übernehmen; Timer nicht als CDB-Dokument veröffentlichen |

Zusätzlich gelesen: `docs/live-conversation.md` sowie unter `/Users/chris/Dropbox/git_reps_v5/cdb-knowledge-mobile` die Dateien `docs/LIVE-CONTRACT.md`, `src/services/liveApi.ts` und relevante Teile von `liveWebRtcTransport.ts`. Die Vertragsdatei trägt Stand 06.10.2026 und spätere Ergänzungen. Sie beschreibt Implementierungen und Staging, ersetzt jedoch keinen aktuellen Server-Codeaudit oder Integrationstest.

## 2. Der tatsächliche Voice-One-Toolcall-Vertrag

Voice One verwendet laut lokalem Vertrag **Azure GPT-Live mit Responses-Delegation**, nicht einfach den klassischen OpenAI-Realtime-Werkzeugpfad.

1. Pi sendet an `/api/v1/tqs/voice-live/sessions` ein SDP-Angebot, Bereichs-IDs, Sprache und `client_request_id`.
2. TQS prüft Konto/Bereiche, erstellt Konfiguration und registriert derzeit `search_brain(question)` in `delegation.responses.tools`.
3. TQS besitzt die Sideband-Steuerleitung über den LLM-Proxy. Der Pi besitzt Audio und empfängt UI-Ereignisse über SSE.
4. Fertige Werkzeugaufrufe stehen im äußeren `response.event` mit `delegation_id`, innen `response.output_item.done`, `item.type=function_call`, `call_id`, `name`, `arguments`.
5. Werkzeugergebnis geht als `response.item.create` mit `function_call_output` zurück; anschließend ausdrücklich `response.create`. Der Vertrag beschreibt bereits Deduplizierung beantworteter `call_id`s in TQS.

Die aktuelle Microsoft-Primärquelle bestätigt diesen Ablauf und die Korrelation. Das ist entscheidend: `conversation.item.create` aus dem klassischen Realtime-Beispiel wäre hier die falsche ungeprüfte Übernahme. [Microsoft: GPT-Live-Delegation](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/gpt-live-delegation).

Der CDB-Vertrag enthält **keine** lokale Gerätewerkzeug-Registrierung, kein `tool_request` an den Pi und keinen Tool-Ergebnis-Endpunkt. Vorhandene Ereigniszähler für `response.function_call_arguments.*` belegen Modellaktivität, aber keinen ausführbaren lokalen Werkzeugvertrag. Aus Fragmenten darf keine Mutation ausgelöst werden.

Azure verlangt laut WebRTC-Dokumentation ein vertrauenswürdiges Backend für den Sitzungsaufbau. Bestehende CDB-/Azure-Zugangsdaten gehören weiterhin nicht in den Browser. [Microsoft: GPT-Live über WebRTC](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/gpt-live-webrtc).

### Was wo geändert werden müsste

| Teil | Ohne Serveränderung möglich | Für vollständige Sprache notwendig |
|---|---|---|
| Pi | SQLite, Zeitplanung, Touch-CRUD, lokale Alarme, Audioentscheidungen, Tests | Authentifizierter Empfänger, Validator, persistente Auftragsquittung und Ergebnis-Outbox |
| TQS | Bestehende Suche unverändert nutzen | Timerwerkzeuge registrieren; lokalen Executor adressieren; Zustellung/Ergebnis/Timeout/Kontobindung verwalten; Erfolg erst nach Pi-Commit |
| BFF | Vorhandene Routen | Neue Ergebnis- und Pending-Routen ausdrücklich freigeben; Streaming-Ereignisse transportieren |
| LLM-Proxy | Bestehender transparenter Sideband-Transport dürfte reichen | Anhand tatsächlichem Code prüfen, ob neue Frames/Größen ohne Änderung durchgehen; keine unbelegte Zusage |
| Azure | Vorhandene Funktionsdelegation nutzen | Keine eigene Timer-API nötig; Deployment und Tool-Schema praktisch validieren |

**Alternative direkter Datenkanal:** technisch könnte ein Client Befehle senden; der lokale CDB-Vertrag verbietet dies bewusst und nennt eine Azure-Grenze bei technischen Kanalfreigaben. Ein solcher Umbau hätte zwei konkurrierende Tool-Ausführer und unsaubere Rechte-/Fortsetzungszuständigkeit. Nicht empfehlen.

## 3. Vorgeschlagene CDB-Brücke – neuer Vertrag, noch nicht vorhanden

Versionierte Capability beispielsweise `device_tools_v1`; nur dann sendet der Pi einen zusätzlich vereinbarten Startblock. Ältere Server können unbekannte Felder ablehnen. TQS darf ausschließlich fest definierte Gerätewerkzeuge registrieren, keine vom Client gelieferten beliebigen Funktionen.

Werkzeuge: `create_timer`, `create_reminder`, `list_schedules`, `update_schedule`, `cancel_schedule`; zusätzlich `acknowledge_alarm` und `snooze_alarm`. Ein einheitliches `manage_schedule` mit diskriminierten Operationen wäre ebenfalls möglich; separate Funktionen sind leichter eng zu validieren. Keine Shell-, Dateipfad-, URL- oder freie SQL-Parameter.

Vorgeschlagener Auftragsumschlag:

```json
{
  "version": 1,
  "request_id": "server-generated-stable-id",
  "call_id": "provider-call-id",
  "delegation_id": "provider-delegation-id",
  "device_id": "paired-recorder-id",
  "session_handle": "opaque",
  "issued_at": "2026-10-13T16:00:00Z",
  "expires_at": "2026-10-13T16:00:30Z",
  "tool": "create_timer",
  "arguments": {"duration_seconds": 600, "label": "Tee"}
}
```

Die Kontobindung wird aus authentifizierter Sitzung und serverseitiger Gerätezuordnung abgeleitet, nicht aus frei vom Modell gelieferten Identitäten. TTL 30 Sekunden ist ein vorgeschlagener Startwert, kein bestehendes CDB-Limit. Der Pi liefert `ok`, `needs_clarification`, `conflict`, `rejected` oder `failed` samt tatsächlicher ID, Revision, Fälligkeit und gerenderter deutscher Bestätigung zurück. Ein `ok` darf erst nach erfolgreicher Datenbanktransaktion entstehen. Bestätigung etwa: „Timer Tee läuft, zehn Minuten ab jetzt.“

Transportvorschlag: SSE-Ereignis `device_tool_request`, dazu neue autorisierte Pending-Abfrage und POST-Ergebnisroute unter der Sitzung. Konkrete Pfadnamen mit TQS/BFF abstimmen. SSE benachrichtigt; persistente Pending-Aufträge sind die Wahrheit. Nach Reconnect Pending-Aufträge abgleichen. TQS hält auch bei Instanzwechsel Aufträge/Resultate ausreichend lange und kann ein bereits lokal committed Ergebnis nach Gesprächsende annehmen, ohne erneut auszuführen. Kein öffentlich erreichbarer Pi oder Cloud-Zugriff ins Heimnetz nötig.

### Idempotenz und Rennen

- Pi-Transaktion speichert Auftrags-ID, Hash der kanonischen Argumente, Mutation und vollständiges Ergebnis gemeinsam. Wiederholung gleicher ID/Argumente liefert dasselbe Ergebnis; gleicher Schlüssel mit anderem Inhalt wird abgewiesen.
- Eindeutiger Schlüssel umfasst Server-/Kontobindung, Geräte-ID und stabile Request-ID. TQS muss dieselbe logische Provider-Anfrage auch nach Sideband-Reconnect auf dieselbe ID abbilden.
- Ergebnis-Outbox wiederholt nur die Rückgabe, nicht das Erstellen. Verlorene HTTP-Antwort bedeutet „Status abgleichen“, nicht „neuen Timer anlegen“.
- `update`/`cancel` verlangen ID und `expected_revision`. Touch-Änderung zwischen Modelllesen und Schreiben ergibt `conflict`. „Den Timer“ bei mehreren Treffern ergibt Rückfrage.
- Eine neue Provider-Call-ID mit ähnlichem Text ist nicht automatisch ein Duplikat: zwei gleich lange Timer können gewollt sein. Für einen neuen Call nach unklarem Ergebnis muss das Modell zuerst den Zustand prüfen; eine perfekte semantische Deduplizierung ist nicht zugesichert.
- Konto-, Mandanten-, Serverwechsel und abgelaufene Aufträge verhindern neue Mutationen. Bereits committed lokale Timer bleiben nach festgelegter Gerätepolitik erhalten.
- Nur ausdrückliche Nutzeraufträge dürfen Mutationen auslösen. Brain-Suchergebnisse, zitierte Texte und Transkriptfragmente sind keine Handlungsfreigabe.

## 4. Lokale Persistenz und Zeitplanung

Empfohlen: ein kleiner `ScheduleService` im Python-Backend, separater Worker, SQLite im lokalen Datenverzeichnis. Der Worker lebt unabhängig vom Browser und vom 20-Minuten-Live-Limit. Ein systemd-Service überwacht den Backendprozess und startet ihn neu. Eine eigenständige Scheduler-Daemonisierung lohnt erst, wenn Alarme auch bei bewusst gestoppter Recorder-App erforderlich sind.

Tabellen: `schedules` (UUID, Art, Titel, ursprüngliche Zeitabsicht, UTC-Fälligkeit, IANA-Zone, Erstellzeit, Status, Revision, Identitätsherkunft), `occurrences` (eindeutiges Ereignis, Fälligkeit, fällig/aktiv/quittiert/verpasst, Alarmversuche), `tool_requests` und `result_outbox`. Statusübergänge und Outbox immer in einer Transaktion. SQLite garantiert atomare Transaktionen unter dokumentierten Hardware-/Dateisystemannahmen; das ist keine Garantie gegen defekte SD-Karten. [SQLite: Atomic Commit](https://www.sqlite.org/atomiccommit.html).

Für diesen kleinen Schreibumfang zunächst gewöhnliches SQLite-Journal mit `synchronous=FULL`, begrenzter Busy-Wartezeit und einem Writer verwenden. WAL nur mit gemessenem Bedarf; ebenfalls lokale Platte, keine Datenbank in einem synchronisierten Cloudordner. Migrationen versionieren, Speicherfehler sichtbar machen. Keine Bestätigung bei Schreibfehler oder vollem Datenträger. Datei-/Verzeichnisrechte analog den bestehenden privaten Live-Daten.

Der Worker wartet höchstens bis zum nächsten Termin oder einer Zustandsänderung, prüft Fälligkeiten mindestens etwa jede Sekunde und beansprucht Ereignisse atomar. Uhrzugriffe injizierbar gestalten. Netzwerkaufrufe und Audio niemals unter `control_lock`, Recorder-Lock oder Datenbanktransaktion ausführen. Einheitliche Lockreihenfolge festlegen, damit Live-SSE und Touch keine Deadlocks erzeugen.

### Countdown und Kalenderzeit unterscheiden

**Timer („in zehn Minuten“):** Dauer ab lokalem Commit. Während desselben Boots auf Linux `CLOCK_BOOTTIME` für suspendübergreifende Ablaufzeit bevorzugen; gewöhnliches `monotonic()` läuft auf Linux nicht automatisch durch Suspend weiter. Persistieren: Boot-ID, Start-/Zielwert der Bootuhr, UTC-Ziel, Dauer. NTP- oder manuelle Wanduhrsprünge ändern einen laufenden Countdown nicht. Python dokumentiert die unterschiedlichen Uhren. [Python: time](https://docs.python.org/3/library/time.html).

**Erinnerung („morgen um neun“):** lokales Datum/Uhrzeit, IANA-Zone wie `Europe/Berlin`, aufgelöster UTC-Zeitpunkt und etwaige Mehrdeutigkeitsentscheidung speichern. Countdown-Anzeige leitet sich aus dem Serverzustand ab; ein Browser zählt nur zur Darstellung zwischen Updates weiter.

Nach einem Reboot ist die Bootuhr neu. Dann zählt das persistierte UTC-Ziel einschließlich ausgeschalteter Zeit, sofern die Systemzeit vertrauenswürdig ist. Eine falsche RTC ohne Netz lässt die echte verstrichene Zeit nicht zuverlässig rekonstruieren. Deshalb Uhrstatus anzeigen, Kalenderauslösung bis zur Zeitvalidierung zurückhalten und Timer als „Zeit nach Neustart prüfen“ kennzeichnen. Erst danach Überfälligkeiten bearbeiten. Uhrzeit/NTP-Status und konkrete Pi-RTC-Ausstattung müssen am Zielgerät geprüft werden.

### Neustarts, verpasste Termine und Zustellung

- Vorschlag: bis fünf Minuten verspätet einmal hörbar nachmelden, mit „vor … fällig“; ältere Ereignisse in „Verpasst“ zusammenfassen und sichtbar halten. Keine Alarmflut nach einem Wochenende ohne Strom. Diese Produktregel ist konfigurierbar und kein technischer Standard.
- `active`-Alarm nach Prozessabsturz mit gleicher Occurrence-ID sichtbar wiederaufnehmen; erneutes kurzes Tonsignal nur begrenzt. Dauer und Wiederholungen begrenzen, etwa maximal zwei Minuten mit drei kurzen Signalen, anschließend sichtbare Quittierung offen halten.
- Physisch hörbares Audio und Datenbankcommit können nicht atomar sein. Ziel ist ein einziges logisches Alarmereignis mit tolerierbarer begrenzter Wiederholung, keine behauptete Exactly-once-Hörbarkeit.
- Fälligkeiten während UI-Neuladen, Kontologout oder Internetverlust laufen lokal weiter. Bei fehlendem Lautsprecher bleibt der Alarm aktiv und zeigt „Ton konnte nicht abgespielt werden“; Rückkehr eines Geräts darf keine unbegrenzte Wiedergabe auslösen.
- Ausgeschalteter Pi kann nicht klingeln. Suspend/Wake benötigt passende Hardware und Betriebssystemkonfiguration. systemd `Persistent=` holt Kalenderaktivierungen nach und `WakeSystem=` ist hardwareabhängig; beides ersetzt keine fachliche Nachholregel. Ein systemd-Timer pro Nutzertermin wäre hier unnötig aufwendig. [systemd: timer](https://github.com/systemd/systemd/blob/main/man/systemd.timer.xml).

### Zeitzonen und Sommerzeit

`zoneinfo` mit installierter IANA-Datenbank verwenden, keine festen UTC+1/UTC+2-Annahmen. `fold` unterscheidet doppelte lokale Zeiten; nicht existierende Zeiten zusätzlich per UTC-Roundtrip validieren. [Python: zoneinfo](https://docs.python.org/3/library/zoneinfo.html).

Konkrete Tests für Berlin: 29.03.2026 02:30 existiert nicht; 25.10.2026 02:30 kommt zweimal vor. In beiden Fällen vor Speicherung rückfragen beziehungsweise explizite Auswahl zeigen. Kein stilles Verschieben. Gerätezeitzonenwechsel verschiebt bestehende einmalige Erinnerungen nicht; Anzeige zeigt gegebenenfalls die ursprüngliche Zone. Wiederholungen wären später als lokale Kalenderregel mit eigener Gap-/Fold-Politik zu speichern, nicht als immer wieder 86.400 Sekunden.

## 5. Zeitangaben und Gesprächsverhalten

Das Modell erhält aktuelle Server-/Gerätezeit, Gerätezone, Locale und bestehende relevante IDs. Der Pi löst keine freie Modellprosa ungeprüft in Termine auf. Toolargumente sind strikt typisiert; Grenzen etwa 1 Sekunde bis 7 Tage pro Timer und maximal 100 aktive Einträge zunächst als Produktvorschlag.

| Äußerung | Verhalten |
|---|---|
| „Timer zehn Minuten für Tee“ | Dauer validieren, committen, exakte Bestätigung |
| „Erinnere mich morgen um neun an den Anruf“ | Lokales Datum bestimmen; bei sprachlich unklarem 09/21 Uhr nachfragen |
| „Später“, „nach dem Essen“, „am Abend“ | Rückfrage, kein aktiver Termin |
| „Um acht“ nach acht Uhr | Nicht still auf morgen verschieben; nächsten gemeinten Termin klären |
| „Verlängere den Tee-Timer um fünf Minuten“ | Explizite Semantik: verbleibende Zeit + fünf Minuten; Revision prüfen |
| „Stelle ihn auf fünf Minuten“ | Fünf Minuten ab Änderung; vor Umsetzung bei unklarem Bezug fragen |
| „Lösche den Timer“ bei mehreren | Auswahl nennen, ID auflösen |
| „Lösche alle“ | Umfang zeigen und kurze Bestätigung einholen |

Rückfragen sind kein erfolgreicher Create-Call. Kandidaten können flüchtig gespeichert werden, werden aber weder geplant noch als aktiv dargestellt. Spracherkennungsunsicherheit bei Zeit/Zahl darf nicht mit einem selbstsicheren Ton überspielt werden. Bei Netzwerkabbruch nach Commit zeigt die Touchoberfläche den tatsächlichen Timer; die Sprachausgabe darf einen unklaren Zustand nicht als Fehlschlag mit automatischem Neustart behandeln.

## 6. Audio-Prioritäten und Mute

**Fälligkeit und akustische Wiedergabe trennen.** Jeder Termin wird rechtzeitig sichtbar; Audio erhält eine bewusste, zentral entschiedene Behandlung. Empfohlene sichere V1: Aufnahme nicht automatisch verändern und Live nicht mit ungeprüftem Alarmton überlagern.

| Zustand | Sichtbar | Empfohlenes Audio in V1 |
|---|---|---|
| Idle | Alarmkarte sofort | Kurzer lokaler Ton, begrenzte Wiederholung; optional lokal vorbereitete Ansage später |
| Aufnahme läuft | Banner und Alarmzähler | Standard leise, damit der Ton nicht in der Aufnahme landet; klar „Ton während Aufnahme zurückgestellt“ |
| Aufnahme pausiert | Alarmkarte | Kurzer Ton erst nach Bestätigung, dass wirklich keine Samples gespeichert werden; Pause nicht als frei verfügbar behandeln |
| Live: Aufbau/Abbau | Alarmkarte | Ton kurz zurückstellen bis Zustand stabil; Verzögerung sichtbar |
| Live: zuhören/denken/sprechen | Alarmkarte | Standard visuell und Ton bis Gesprächsende zurückgestellt; kein zweites Sprachsignal ins offene Mikrofon |
| Mikrofon stumm | Alarmkarte | Alarm folgt dem übrigen Modus; Mikrofonmute allein sperrt keinen Lautsprecher |
| Alarmton ausdrücklich aus | Alarmkarte | Kein Ton; Zustand dauerhaft sichtbar |
| Lautsprechertest/Bluetoothwechsel | Alarmkarte | Test unterbrechen bzw. Ausgabe nach erfolgreichem Wechsel neu bewerten; nicht auf falsches Gerät routen |

Das ist eine bewusste Einschränkung gegenüber Alexa: Ein Timer kann während Aufnahme/Live leise fällig werden. Die Oberfläche muss das vorab vermitteln. Wer sofortige akustische Timer in jedem Modus verlangt, benötigt eine zusätzliche Ausbaustufe: gemeinsamer Audiomischer/Arbiter, explizite Live-Unterbrechung mit CDB, Echovermeidung und getestete Mikrofon-Gates. Nur Playback leiser zu machen reicht nicht; der Modellkontext muss zur tatsächlich gehörten Ausgabe passen. Keine automatische Aufnahmeunterbrechung ohne gesonderte Produktentscheidung.

Priorität im Arbiter: Quittieren/Stop und explizite Stummschaltung zuerst; danach Integrität der Aufnahme und Live-Audiositzung; dann freigegebener Alarm; Suchklang zuletzt. Beim Alarm Suchklang stoppen. Separates Setting „Alarmton“ und Lautstärke, getrennt von „Mikro stumm“ und Suchton. Physische Mute-Taste am Gerät prüfen: aus aktueller LED-/Mikrofonlogik lässt sich kein Lautsprecherverhalten ableiten. Lokaler vorinstallierter Ton funktioniert ohne TTS oder Cloud. Automatische Textansagen können private Inhalte offenbaren und sollten optional sein.

## 7. Zugängliche Touchoberfläche

- Eigener Navigationspunkt „Timer & Erinnerungen“ mit aktivem Zähler; nächster Timer kompakt auch auf Aufnahme-/Live-Seite. Kein Zwang zum externen Display.
- Zwei klar erkennbare Listen: aktive Einträge und verpasste/erledigte. Timer zeigen Namen und Restzeit, Erinnerungen absolutes Datum/Uhrzeit. Zone nur dort ergänzen, wo sie relevant oder abweichend ist.
- Große Schaltflächen: „Timer starten“, „Erinnerung erstellen“, „Ändern“, „Löschen“; einfache Dauerpresets und Zeitwahl, keine freie Tastatureingabe als einziger Weg.
- Alarmkarte über allen Ansichten, ohne Stop-/Aufnahmebedienung zu verdecken; „Erledigt“ und „5 Minuten später“. Quittieren stoppt genau die zugehörige Occurrence. Mehrere gleichzeitige Alarme als einzeln adressierbare Liste.
- Zielgröße für Touch mindestens 48 × 48 CSS-Pixel mit Abstand als Produktziel. WCAG 2.2 nennt für AA 24 × 24 CSS-Pixel bzw. Ausnahmen, nicht pauschal 48. Sichtbarer Tastaturfokus, zugängliche Namen, ausreichender Kontrast, Text neben Farbe und Symbol. [W3C: Target Size Minimum](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html).
- Countdown nicht jede Sekunde als Screenreader-Live-Nachricht vorlesen; nur Start, relevante Zustandswechsel und Fälligkeit ankündigen. Alarmbedienung keyboardfähig; Dialogfokus sinnvoll setzen und nach Schließen zurückgeben.
- Touch-CRUD und Quittierung auch während Live/Aufnahme erlauben. Audio-/Gerätewechsel bleiben gesondert gesperrt. Bei gleichzeitigem Ändern in zwei Browsern Konflikt verständlich anzeigen und aktualisieren.
- Systemzeit unsicher, Ton aus, Lautsprecher fehlt, Ton zurückgestellt und Pi offline sind unterscheidbare Zustände. Eine sichtbare Restzeit ist keine Zusicherung eines hörbaren Alarms.

## 8. Identität und lokaler Betrieb

Empfohlen für V1: ausdrücklich **Gerätetimer** auf einem gemeinsam genutzten Recorder. Touch sieht alle Gerätetimer; Sprachzugriff wird nur aus der aktuell autorisierten Pi-Sitzung akzeptiert. Kontowechsel löscht oder beendet gespeicherte Timer nicht automatisch. Diese Gerätepolitik muss im UI erkennbar sein, da Titel für andere Personen sichtbar werden können. Falls persönliche Erinnerungen verlangt sind, vor Umsetzung stattdessen ownergebundene Listen, Sperrbildschirm und eine Regel für unsichtbare fremde Alarme festlegen; beide Modelle nicht vermischen.

Lokale API übernimmt vorhandene Zugriffsschutzmechanismen, verlangt aber deren Prüfung für neue schreibende Routen (Origin/CSRF/Authentifizierung bei Fernzugriff). Keine neuen offen erreichbaren Timer-Endpunkte. Ohne CDB-Anmeldung bleibt lokale Touchbedienung möglich. Keine Aufnahmeauswertung im Hintergrund, keine automatische Erstellung aus Meeting-Zusammenfassungen. Texte begrenzen, HTML escapen, keine Geheimnisse oder Inhalte in technische Auditlogs schreiben.

## 9. Test- und Abnahmeplan

| Ebene | Wesentliche Prüfungen | Abnahmekriterium |
|---|---|---|
| Zeitmodell | Injizierte Uhren; NTP ±1 Stunde; Bootwechsel; Suspend; UTC-/Zonenwechsel; DST Gap/Fold | Countdown folgt Dauer, Kalender folgt aufgelöstem Termin; keine stille DST-Korrektur |
| Persistenz | Absturz vor/nach Commit, vor/nach Ton, vor/nach Ergebnis-POST; voller Datenträger; konkurrierende Worker | Keine verlorene bestätigte Planung; ein logisches Ereignis; Fehler sichtbar |
| Toolvertrag | Schemafehler, bool statt Zahl, unbekanntes Tool, übergroßer Text, fremdes Gerät/Konto, abgelaufener Request | Keine Mutation; strukturierter Fehler |
| Wiederzustellung | Doppeltes SSE, Reconnect ohne Eventcursor, TQS-Instanzwechsel, verlorene Antwort, identische ID mit anderem Payload | Ein Timer je stabilem Auftrag; identische Ergebnisrückgabe |
| Konkurrenz | Touch vs. Sprache Update/Delete/Fire; zwei Browser; Löschen genau zur Fälligkeit | Revisionen und Transaktionsreihenfolge entscheiden nachvollziehbar; kein Geisteralarm |
| Audio | Idle, Aufnahme, Pause, Live in allen Phasen, App-/Hardwaremute, Suchton, Speakerverlust | Keine heimliche Aufnahmeunterbrechung, kein ungeprüfter Alarm im Live-Mikrofon; Stop reagiert sofort |
| UI | Kleine Pi-Auflösung, externe Anzeige, 200 % Zoom, Touch, Tastatur, Screenreader, mehrere Alarme | Bedienung ohne verdeckte Aktionen, keine sekündliche Sprachflut |
| Offline/Restart | Browser geschlossen, Appcrash, Netzwerk aus, Strom weg, Start mit falscher Uhr | Gespeicherte Termine wiederhergestellt; Nachholregel und Unsicherheit sichtbar |
| Echte CDB-Integration | Deutscher Sprachauftrag → Tool → Pi-Commit → Ergebnis → bestätigte Sprache; auch Änderung/Löschen/Rückfrage | Modell nennt nur tatsächlich gespeicherten Zustand; Cloud-Ausfall ändert laufenden Timer nicht |
| Echte Hardware | Hörprüfung am gewählten Pi-Lautsprecher und Aufnahme auf unbeabsichtigte Signaltöne prüfen | Ein empfangener Audiostream allein gilt nicht als Hörnachweis |

Messbare Startziele: sichtbare Fälligkeit und freigegebener Ton im normalen Betrieb innerhalb einer Sekunde; Alarmquittierung beendet Ausgabe innerhalb 300 ms; 24-Stunden-Soak mit mehreren Timern, Reconnects und einem Prozessneustart. Grenzen unter Last messen, nicht ungeprüft versprechen. Langzeitversuche für Erinnerungen durch beschleunigte injizierte Zeit ergänzen, mindestens einen realen Durchlauf behalten.

## 10. Umsetzung in getrennten Schritten

1. **CDB-Vertrag entscheiden:** TQS/BFF bestätigen Capability, Gerätebindung, Request-ID, Pending-Replay, Ergebnisroute, Timeout und Gesprächsende. Ein kleiner isolierter Vertragstest zuerst, keine Änderungen am externen Display.
2. **Lokalen Kern erstellen:** SQLite, Uhrmodell, Worker, API und Touchoberfläche; ausschließlich Gerätetimer, einmalige Ereignisse und sichere Audio-V1. Integration in bestehende Locks gezielt prüfen.
3. **Sprachadapter anschließen:** CDB-Featureflag; Ergebnis-Outbox; Rückfragen; echtes Ende-zu-Ende-Protokoll. Ohne Capability bleibt die Touchfunktion verfügbar.
4. **Hardwareabnahme:** Mute, Pause, Lautsprecherverlust, Reboot und reale Uhrsynchronisierung testen. Erst danach getrennte Deploymentfreigabe.

Nicht seriös geschätzt sind Aufwand und Fertigstellungstermin, solange CDB-Brücke und gewünschtes Audioverhalten während Live/Aufnahme offen sind. Die lokale Planung ist überschaubar; zuverlässig bestätigte verteilte Toolausführung und unterbrechungsfreie Audiointegration sind die eigentlichen Risiken.

## Offene Entscheidungen vor Implementierung

1. Akzeptiert der Nutzer in V1 sichtbar fällige, aber während Live/Aufnahme leise Alarme? Falls nein, Audio-Unterbrechungsvertrag als Pflichtumfang aufnehmen.
2. Gerätetimer oder persönliche Erinnerungen? Empfehlung für dieses Gerät: Gerätetimer mit sichtbarer Kennzeichnung.
3. Fünf-Minuten-Nachholfenster, begrenzte Signale, Standardlautstärke und Schlummerdauer bestätigen.
4. Welches Team erweitert TQS/BFF, und welcher reale Serverstand implementiert den vereinbarten Vertrag?
5. Pi-Modell, RTC, NTP, Suspend und physische Mute-Taste am Zielgerät verifizieren.

**Entscheidung:** Lokalen Kern befürworten; vollständige Voice-One-Steuerung unter Vorbehalt der CDB-Vertragserweiterung. Keine bestehende Clientfunktion kann diesen fehlenden Rückkanal verlässlich ersetzen. Die Parallelentwicklung am externen Display bleibt durch diese reine Untersuchung unberührt.
