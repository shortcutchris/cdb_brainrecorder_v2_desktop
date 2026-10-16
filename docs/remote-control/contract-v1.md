# Mobile Pi-Fernbedienung: Vertrag v1

Stand 16.10.2026. Gemeinsamer Implementierungsvertrag für
[cdb-knowledge-mobile#63](https://github.com/BIK-GmbH/cdb-knowledge-mobile/issues/63),
Pi und CDB-Server. **Entwurf zur Implementierung, keine bereits verfügbare API.**
Dieser Vertrag ersetzt abweichende Transport-, Signatur- und Controller-Lease-
Annahmen im früheren Recherchevorschlag. Bluetooth bleibt außerhalb dieses Schritts.

## Verantwortungen und Identität

Das Handy ist eine Fernbedienung. Nur der Pi besitzt Mikrofon, Lautsprecher,
Audioreservierung und CDB-Live-Sitzung. Die bestehenden Pi-Grenzen bleiben:
120 Sekunden Inaktivität, höchstens 1200 Sekunden Gesprächsdauer. Handy-
Hintergrund, App-Sperre, Verbindungsverlust und Entkopplung stoppen oder verlängern
kein laufendes Gespräch. Es gibt **keine Controller-Lease** und keinen Handy-
Heartbeat für die Live-Sitzung. Lokales Ende und die Pi-Zeitgrenzen bleiben wirksam.

Bindung überall: `{environment, user_id, client_id}`. `environment` ist der
kanonische HTTPS-Origin der ausdrücklich gewählten CDB-Umgebung, ohne Pfad oder
abschließenden Slash. Der Server bestimmt Person und Mandant aus dem geprüften
persönlichen Entra-Access-Token; diese Werte werden niemals aus dem Request-Body
als Autorisierung übernommen. Ein Umgebungs-/Kontowechsel verwirft alte Antworten
und Steuerrechte auf beiden Clients. Keine automatische Wiederkopplung.

Controller-Routen verlangen persönlichen JWT, passenden delegierten API-Scope,
aktives Benutzerkonto und aktuellen Mandanten. API-Keys, Portalbesucher, Teilnehmer
und ID-Tokens reichen nicht. Die bestehende `require_live_auth`-Dependency darf
nicht unverändert übernommen werden: sie erlaubt inzwischen Portal-API-Keys.

Der Pi registriert eine **eigene Control-Geräteidentität** mit seiner bestehenden
persönlichen CDB-Anmeldung. Seine zufällige Gerätecredential berechtigt nur zu
seinem Control-Kanal, Status, Pairing-Bestätigung und Quittungen. Sie erteilt weder
Brain-Zugriff noch Controller-Rechte oder Fleet-Wartungsrechte. Eine Fleet-ID ist
allenfalls Inventarmetadatum und keinerlei Autorisierung.

Erster Transport: ausschließlich ausgehendes HTTPS zum gewählten CDB-Origin,
gültige Zertifikatsprüfung, keine credentialführenden Cross-Origin-Redirects.
Authentifizierung immer im Authorization-Header, niemals URL/Query/Logs. Kein
Drittanbieter-Relay. TLS und dedizierte Gerätecredential authentifizieren den
Serverkanal; zusätzliche Auftragssignaturen und neue Factory-Vertrauensschlüssel
sind in v1 nicht erforderlich. Der Pi-Domainadapter akzeptiert ausschließlich
vom verifizierten Kanal übergebene Grants und Aufträge, keine frei erreichbare
lokale HTTP-Funktion, die einen angeblich verifizierten Grant entgegennimmt.

## Konventionen

Public BFF-Basis: `/api/v1/tqs/device-control`; TQS-Basis:
`/api/v1/device-control`. Alle folgenden Pfade sind relativ dazu. JSON nutzt
snake_case. IDs sind UUID-Strings, `process_epoch` ein neuer UUID-String je
Pi-Prozessstart, Revisionen nichtnegative Integer. Zeiten sind Unix-Sekunden in
UTC. Keine Audio-, Transkript-, Prompt-, Token- oder Chatinhalte im Vertrag.
Unbekannte Felder in mutationsrelevanten Requests werden abgewiesen.

Fehler: HTTP-Status plus `{code: string, message: string}` ohne Interna.
401 `access_token_required`/`device_auth_required`, 403 `account_inactive`/
`binding_mismatch`/`grant_revoked`, 404 `not_found`/`device_control_disabled`,
409 `pairing_in_use`/`command_conflict`/`stale_state`/`device_busy`,
410 `pairing_expired`/`command_expired`, 429 `rate_limited`,
503 `device_offline`/`device_control_unavailable`. Fremde Objekt-IDs ergeben 404,
ohne deren Existenz offenzulegen. Fehlende Capability oder bloßes 404 darf auf
alten Servern als nicht unterstützt erscheinen, niemals als Steuerfreigabe.

## Controller-Routen (persönlicher JWT)

| Methode und Pfad | Request / Antwort |
| --- | --- |
| `GET /capabilities` | `{device_control_v1: boolean, protocol_version: 1}`; standardmäßig false |
| `GET /devices` | `{devices: Device[]}`; ausschließlich eigene aktive Kopplungen |
| `POST /pairings/claim` | `{code, controller_id, claim_request_id}` → 202 `Pairing` |
| `GET /pairings/{pairing_id}` | eigene `Pairing`, sonst 404 |
| `POST /pairings/{pairing_id}/revoke` | leerer Body → 204; idempotent, auch pending abbrechbar |
| `GET /devices/{device_id}/status` | `DeviceStatus` für eigene aktive Kopplung |
| `POST /devices/{device_id}/commands` | `Command` → 202 `CommandResult`, oder gespeichertes Ergebnis desselben Auftrags |
| `GET /commands/{command_id}` | eigenes `CommandResult`, sonst 404 |

`controller_id` ist eine zufällige App-Installations-ID, kein Sicherheitsgeheimnis.
Der Server bindet sie an Person/Mandant und die aktive Kopplung; sie ersetzt keinen
JWT. V1 erlaubt je Gerät genau eine aktive oder bestätigungsbereite Kopplung.
Ein anderer Controller muss zuerst explizit entkoppeln; kein stilles Übernehmen.

`Pairing`:

```json
{"pairing_id":"uuid","device_id":"uuid","device_name":"Besprechungsraum",
 "controller_id":"uuid","state":"pending_confirmation","expires_at":1792150000,
 "binding":{"environment":"https://staging.cdbos.de","user_id":"uuid","client_id":"uuid"}}
```

`state`: `pending_confirmation | active | rejected | expired | revoked`.
Bei `active` ist `pairing_id` zugleich `grant_id`; `expires_at` ist dann der
Grant-Ablauf, maximal 30 Tage nach lokaler Bestätigung. Pending verfällt spätestens
mit dem Pairing-Code. Abgelaufene Grants erfordern neue ausdrückliche Kopplung.
Ein Claim verbraucht den Code atomar; gleiche `claim_request_id` derselben Person
mit identischem Body liefert dasselbe Ergebnis. Abweichender Body ergibt 409.
Wiederholung reaktiviert niemals einen widerrufenen oder abgelaufenen Grant.

`Device`: `{device_id, device_name, grant_id, controller_id, binding, expires_at}`.
Der Geräte-/Statuszugriff prüft Konto, Mandant, Umgebung und Grant frisch.
Nach Widerruf keine neuen Aufträge oder Statusdaten; bereits laufende Gespräche
laufen lokal weiter. Nicht ausgeführte Aufträge werden verworfen. Bereits vor
dem Widerruf ausgeführte Aktionen werden nicht rückgängig gemacht.

## Geräteanmeldung und ausgehender Pi-Kanal

Diese Routen sind ebenfalls neu zu implementieren. Die erste benötigt persönlichen
JWT, alle übrigen ausschließlich die dedizierte Gerätecredential:

| Methode und Pfad | Vertrag |
| --- | --- |
| `POST /devices/register` | JWT; `{device_id, device_name, credential_hash}` → `DeviceRegistration` |
| `POST /device/pairings` | Geräteauth, lokale Benutzeraktion; `{}` → `{code, expires_at}` |
| `POST /device/pairings/{pairing_id}/confirm` | Geräteauth und ausdrückliche lokale Bestätigung; `{approved: boolean}` → `Pairing` |
| `POST /device/poll` | Geräteauth; `{process_epoch, timeout_seconds: 20}` → `DevicePoll` |
| `POST /device/status` | Geräteauth; `PiStatus` → 204 |
| `POST /device/commands/{command_id}/receipt` | Geräteauth; `{status, code?, snapshot}` → 204 |
| `POST /device/revoke` | Geräteauth; `{}` → 204, Gerätecredential und alle Grants widerrufen |

Pi erzeugt `device_id` und eine Credential aus mindestens 32 kryptografisch
zufälligen Bytes lokal. Registrierung übermittelt nur ihren SHA256-Hexdigest
`credential_hash` (64 Zeichen); spätere Geräteanfragen übermitteln das rohe
Geheimnis als Bearer. Der Server speichert nur den Hash, prüft konstantzeitig und
bindet Registrierung an die JWT-Identität. Wiederholte Registrierung desselben
Geräts/Hashes derselben Person ist idempotent; andere Bindung/anderer Hash ergibt
409 und rotiert nichts still. `DeviceRegistration` ist `{device_id, binding}`.
Gerätecredential ist bis Widerruf gültig, wird aber nur bei weiterhin aktivem
Konto und unverändertem Mandanten akzeptiert. Kein Token wird aus dem Server auf
den Pi delegiert, der Pi verwendet für Voice Live weiterhin seine eigene SSO-Sitzung.

Pairing-Code: acht Zeichen aus `ABCDEFGHJKLMNPQRSTUVWXYZ23456789`, fünf Minuten
gültig, zufällig, serverseitig nur gehasht, eine Verwendung. Höchstens fünf
Claimversuche pro Minute und 20 pro Stunde je authentifizierter Person; zusätzliche
IP-Begrenzung empfohlen. Der Pi zeigt nach Claim den bestätigungsbereiten
Controller; die lokale Zustimmung ist zwingend. Der Controller sieht `active`
erst nach dieser Bestätigung. Kein Code und kein Geheimnis in normalen Logs.

`DevicePoll`:

```json
{"protocol_version":1,"binding":{"environment":"https://staging.cdbos.de","user_id":"uuid","client_id":"uuid"},
 "grants_revision":3,"grants":[{"grant_id":"uuid","controller_id":"uuid","expires_at":1792150000}],
 "pending_pairings":[],"commands":[]}
```

`pending_pairings` enthält `Pairing`-Objekte. Je Poll höchstens 32 Commands;
`timeout_seconds` 0 bis 20 ist eine maximale Wartezeit, sofortige Antwort ist
erlaubt. Clients warten zwischen kurzen Polls. `grants` ist der vollständige aktuelle
aktive Snapshot; höhere `grants_revision` ersetzt ihn, entfernte Grants sind
lokal widerrufen. Aufträge dürfen nur mit dem mitgelieferten aktuellen Grant und
passender Bindung ausgeführt werden. Der Server prüft vor jeder Auslieferung
erneut Konto, Grant und Ablauf. Der Transport verarbeitet Antworten seriell,
verwirft Antworten alter Account-/Prozessgenerationen und reicht keine gepufferten
Aufträge nach einem Reconnect ungeprüft weiter. Ein Widerruf kann eine bereits
ausgelieferte, gleichzeitig ausgeführte Aktion nicht rückwirkend verhindern;
danach gelieferte Pollantworten enthalten weder Grant noch Auftrag. Kein Anspruch
auf atomare verteilte Rücknahme bereits laufender Audioaktionen.

Der Pi meldet Status bei Änderung und spätestens alle zehn Sekunden. Ein
erfolgreicher authentifizierter Poll/Status aktualisiert `last_seen_at`.
Nach 30 Sekunden ohne Kontakt gilt das Gerät serverseitig als offline. Ein
Online-Status ist keine Controller-Lease. V1 braucht keinen Controller-SSE-Stream:
das Handy fragt Status während sichtbarer Fernbedienung ab (etwa alle zwei
Sekunden) und pausiert diese Abfragen im Hintergrund.

## Status, Generation und Aufträge

`PiStatus`:

```json
{"device_id":"uuid","process_epoch":"uuid","generation":4,"revision":12,
 "state":"active","busy":false,"muted":false,
 "areas":[{"id":"uuid","name":"Wissensbereich"}],"allowed_actions":["end","set_muted"]}
```

`state`: `idle | connecting | active | closing | error`.
`busy` zeigt eine belegte Ressource, die Remote-Start verbietet, insbesondere
Aufnahme **und Pause**, Wartung, Wiedergabe oder unvollständiges Audio-Cleanup.
`areas` sind IDs und sichtbare Namen der tatsächlich am Pi bestätigten Bereiche
der aktiven Sitzung, sonst die gespeicherte kontogebundene Pi-Auswahl. M1 zeigt
diese Auswahl auf dem Handy nur lesend an; Start verwendet genau diese Auswahl.
`allowed_actions` ist ein Hinweis für die UI, keine Autorisierung.
`DeviceStatus` ergänzt `{binding, grant_id, online, last_seen_at, snapshot: PiStatus}`.
Vor dem ersten Pi-Snapshot ist `snapshot: null`; das Handy erlaubt dann keine Aktion.

`generation` erhöht sich vor Beginn jeder neuen Live-Sitzung, auch lokaler
Starts; ein fehlgeschlagener Start darf die verbrauchte Generation nicht erneut
verwenden. Bei Prozessneustart wird die `process_epoch` neu, der Generationszähler
darf wieder bei null beginnen. `revision` erhöht sich bei jeder materiellen
Statusänderung, nicht bei unverändertem Poll. Der Server akzeptiert innerhalb
derselben Epoch keine fallenden Revisionen. Eine neue Epoch verwirft alle alten
ausstehenden Aufträge. Ein später Status aus einer alten Epoch darf den aktuellen
Status nicht ersetzen (Poll legt aktuelle Epoch fest; status allein wechselt sie nicht).

```json
{"command_id":"uuid","grant_id":"uuid","controller_id":"uuid",
 "action":"start","process_epoch":"uuid","expected_generation":4,
 "expected_revision":12,"expires_at":1792150000}
```

Alle Aktionen tragen dieselben Basisfelder. `start` und `end` tragen keine
weiteren Parameter; `set_muted` trägt genau `muted: boolean`. Keine Toggle-Aktion.
Start verwendet gespeicherte Pi-Sprache und kontogebundene Pi-Wissensauswahl
(1 bis 8 eindeutige IDs). M1 erlaubt keine Auswahl-/Sprachmutation vom Handy.
Die Auswahl gehört zum materialisierten Status und seiner Revision: ändert sie
sich nach Anzeige am Handy, schlägt CAS fehl. Pi und bestehender Live-Server
prüfen die Auswahl ohne stilles Erweitern oder Reduzieren. End/Mute dürfen eine
aktive Sitzung desselben gebundenen Pi-Kontos steuern, auch wenn sie lokal
gestartet wurde; Epoch und Generation müssen exakt stimmen. Aufnahme und Pause
sind niemals eine solche Live-Sitzung.

`expires_at` liegt höchstens 15 Sekunden nach Annahme am Broker; der Client setzt
es entsprechend der aktuellen UTC-Zeit. Abgelaufene Aufträge werden nicht
ausgeführt. Unsichere Pi-Uhr: Start/Unmute ablehnen (`clock_untrusted`), lokale
Bedienung bleibt möglich. Der Broker lehnt Offline-Geräte ab und setzt keine
unbegrenzte Warteschlange fort. CAS: Epoch, Generation und Revision müssen am Pi
passen; andernfalls `stale_state`, aktueller Snapshot und erneutes Anzeigen.
Kein automatisches Wiederholen einer Start-/Unmute-Aktion mit neuer ID.

Der Broker ergänzt `device_id` und `binding` aus autorisierten Datensätzen, nicht
aus dem Controller-Body. Die Pi-Domain erhält diesen Envelope plus verifizierten
Grant. `commands` im Poll enthält die Command-Basisfelder plus `device_id`,
`binding` und `grant: {grant_id, controller_id, expires_at}`. Der Pi-Transport
bindet diesen Grant zusätzlich an seine aktuelle lokale `account_generation`;
der Broker erfindet diese lokale Generation nicht. Prüfung/Reihenfolge: Bindung/Grant/Ablauf, gespeicherte Auftrags-ID,
identischer Body, dann Epoch/Generation/Revision, dann vorhandene Audioreservierung.
Eine identische Wiederholung liefert die gespeicherte Quittung statt Audio erneut
zu öffnen; gleiche ID mit anderem Body ergibt `command_conflict`.

`CommandResult`:

```json
{"command_id":"uuid","device_id":"uuid","status":"accepted","code":null,"snapshot":null}
```

`status`: `accepted | applied | rejected | expired | unknown`. Nach Ablauf der
Ausführungsfrist sind nie gelieferte Aufträge `expired`, gelieferte Aufträge ohne
Quittung `unknown`. Verspätete dauerhafte Quittungen desselben Prozesses und
weiterhin gültigen Grants dürfen `unknown` auflösen. Eine historische Quittung
darf den neueren Gerätestatus nicht zurücksetzen.
202/`accepted` bestätigt nur Aufnahme durch den Broker. Erst die Pi-Quittung
`applied` bestätigt die lokale technische Zustandsänderung, nicht semantischen
Erfolg eines gesprochenen Auftrags. Der Pi quittiert erst nach seiner jeweiligen
realen Aktionsgrenze (Start reserviert/Connecting, Ende bestätigt/Idle, Mute gesetzt).
Start/Connecting ist keine Behauptung einer verbundenen Cloud-Sitzung; der
bestätigte Status zeigt später `active` oder `error`.

Pi speichert ID, Body-Fingerprint und Ausführungs-/Quittungszustand vor dem
Seiteneffekt dauerhaft und beendet den Journaleintrag nach Bestätigung. Nach
Prozessabbruch ist ein nicht abschließend quittierter Auftrag `unknown`, wird
niemals automatisch erneut ausgeführt und verlangt Statusabgleich. Ein
unbestätigtes Ende darf Cleanup nicht freigeben. Broker und Pi halten Ergebnisse
mindestens 24 Stunden; alte terminale Einträge können danach entfernt werden,
weil Ablaufzeit und Epoch/Generation eine erneute Ausführung verhindern.
Widerruf ist stärker als Idempotenz: nach Widerruf keine erneute Mutation.

## Implementierungs- und Abnahmestufen

Erste Stufe: reine Domainports, Fake-Broker/Fake-Audio, synthetische Identitäten,
Capability aus. Kein nachgebautes Modell als alleiniger Beleg: Pi-Tests prüfen
den echten Studio-/Live-Adapter mit injizierten Ports. Danach echter Broker mit
Auth-/Tenant-/Replay-/Race-Tests und expliziter BFF-Weiterleitung. Erst danach
gesonderte Staging-Abnahme und Hardwareprüfung. Kein Release/OTA/Production durch
diesen Vertrag autorisiert.

Pflichtfälle: falsche Identität/Umgebung; Portal-/API-Key; Code-Replay und Ablauf;
lokale Ablehnung; Grant-Widerruf; neue Epoch und verspätete Statusmeldung;
gleichzeitiger Record-/Wake-/Remote-Start; Pause; duplicate start; conflicting ID;
Mute-Reordering; End aus alter Generation; Accountwechsel; verlorene Quittung;
Prozessabbruch an Aktionsgrenzen; App-Hintergrund beendet/verändert keinen Pi-Timer;
kein Audio-/Transkriptinhalt oder Credential in Status/Logs; frischer ungepaarter
Erststart und Upgrade eines Profils ohne Control-State.

## Image-Auswirkung

Dieses Dokument hat keine Runtime-/Image-Auswirkung. Künftiger App-Code benötigt
Aufnahme in die bestehende Positivliste und Prüfung vorhandener sowie frischer
Profile. Neue Control-ID, Credential, Grants und Journal entstehen ausschließlich
auf dem Zielgerät und gehören nicht ins SD-Image. Dieser Vertrag benötigt keine
Fleet-Identitätsmigration, keinen zusätzlichen Root-Dienst und keine neuen
Signaturschlüssel im Kunden-Image. Datenmigration, Runtime-Abhängigkeiten und
Hardwareabnahme müssen an der tatsächlichen Implementierung erneut geprüft werden.
