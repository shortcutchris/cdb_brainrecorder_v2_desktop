# CDB-Verbindung und Touchseiten · Studio 0.5.0

Stand 12.10.2026. Python-Backend und HTML-Kiosk bleiben eine Anwendung mit einer Aufnahme-/Verarbeitungsqueue. Die gemeinsame lokale Engine bleibt unverändert auf 0.2.6 gepinnt.

## Bedienung

1. Einstellungen → Verbindung → Microsoft anmelden. Die angezeigte Microsoft-Adresse auf dem Handy oder Rechner öffnen und den Gerätecode eingeben. Nach bestätigter Anmeldung zeigt der Pi den CDB-Kontonamen. Abmelden/Abbrechen beendet die lokale Sitzung beziehungsweise die laufende Anmeldung.
2. Transkription und Zusammenfassung unabhängig auf „Auf diesem Gerät“ oder „Über CDB“ stellen. CDB benötigt eine gültige Firmenanmeldung und überträgt Audio beziehungsweise Text. Lokale Modelle und öffentliche Modelldownloads brauchen keine Firmenanmeldung. Kein automatischer Wechsel zwischen lokal und CDB.
3. Knowledge Areas → Bereiche laden → Zielbereich wählen. Das bestätigte Ziel bleibt kontogebunden gespeichert. Eine sichtbare Area ist noch kein garantiertes Schreibrecht.
4. Meetingaktionen → Ins Brain übertragen. Gesendet werden ein eingefrorener Markdown-Text mit Zusammenfassung, vollständigem Transkript und Notizen sowie Titel und festem Ziel. Der Original-Audioversand zur Archivierung gehört nicht zu diesem Text-Ingest. Eine für CDB-Transkription übertragene Audiodatei ist ein eigener Serverbestand.
5. Unter Knowledge Areas die Übertragung verfolgen: eingereiht → übertragen → angenommen → CDB verarbeitet. „Angenommen“ wird nicht als fertiges Wissensdokument ausgegeben. Antwortverlust nach einem Schreibaufruf bleibt „Empfang unklar“; kein blinder automatischer Neuversand.

Einstellungen besitzen acht direkt anwählbare Aufgabenseiten ohne Scroll-Pfeile. Modellinstallation/-aktivierung ist bei der jeweiligen Modellseite, der technische lokale Modelltest auf einer eigenen Seite. Beim Eingeben mit Bildschirmtastatur wird das aktive Feld freigestellt. Eigene Themes und Übertragungen besitzen direkte Seitennummern. Die übrigen vorhandenen Leser-/Listenpfeile außerhalb der Einstellungen bleiben unverändert.

## Technische Grenzen und Verträge

Referenz: `git_reps_v5/cdb-knowledge-mobile`, insbesondere `ssoProtocol.ts`, `connection.ts`, `serverTranscription.ts`, `remoteSummary.ts`, `brainSend.ts`, `drive.ts` und die zugehörigen Domain-Parser.

- Öffentlicher Microsoft-Client, Device Authorization Grant, delegierter CDB-Scope `access_as_user` plus `offline_access`. Kein Clientsecret. Voreinstellung: vorhandene CDB-Knowledge-Mobile-Client-ID; deren erlaubte Public-Client-Flows und Firmenrichtlinien müssen die Geräteanmeldung erlauben. Die öffentliche ID kann administrativ in der privaten CDB-Konfiguration geändert werden; kein selbsttätiges Ändern der Entra-Registrierung.
- Microsoft liefert derzeit `https://login.microsoft.com/device`; zusätzlich ist die dokumentierte `https://microsoft.com/devicelogin` erlaubt. Andere Verifikationsziele werden verworfen. Tokenantwort und CDB-Identität werden vor Speicherung geprüft. Refresh prüft unveränderten Benutzer/Mandanten.
- Serverauswahl ist auf `https://staging.cdbos.de` (Standard) und `https://cdbos.de` begrenzt. Produktion wurde nicht live geprüft. Netzwerkaufrufe folgen keinen Redirects und ignorieren Proxy-Umgebungsvariablen.
- Zugangsdaten nur serverseitig unter `<Datenablage>/cdb/session.json` (0600, Verzeichnis 0700). Dies ist **Dateizugriffsschutz, keine Verschlüsselung der SD-Karte** und kein Linux-Schlüsselbund. API und Frontend erhalten keine Access-/Refresh-Tokens. Anmeldecodes sind kurzlebig und werden nicht in Git/Screenshots archiviert.
- Provider und Konto werden beim Erstellen jedes neuen Verarbeitungsjobs in `cdb-request.json` festgeschrieben. Bestehende Jobs ohne diese Datei bleiben lokal. Modelltests bleiben lokal. Die Aufnahme ist weiterhin unabhängig vom FIFO-Verarbeitungsworker.
- CDB-ASR komprimiert eine Kopie des Originals mit ffmpeg zu Opus (32 kbit/s), streamt sie in begrenzten Blöcken als Multipart und speichert Recording-/Job-ID. Original bleibt unverändert. Größenlimit 95 MiB für die komprimierte Kopie. Ein bestätigter Serverjob wird nach Neustart gepollt. Unklarer Audioupload wird über seinen eindeutigen Dateinamen abgeglichen; ohne eindeutigen Fund kein erneuter Upload.
- CDB-Zusammenfassung verwendet den vorhandenen abschnittsweisen Worker mit `/api/v1/tqs/agent/structure-text`. Abgeschnittene/leere Antworten gelten als Fehler. Die bekannten Zeichenbudget-/Teilcheckpoint-Grenzen der gemeinsamen Engine sind dadurch noch nicht behoben.
- Text-Ingest: frische Area-Prüfung, eingefrorene Account-/Server-/Area-/Mandantenbindung, `origin: ai_generated`, `auto_verify_tl1: false`. Publikations-DB mit Payload-Fingerprint verhindert Doppeltippen desselben unveränderten Inhalts/Ziels. Dies ist keine serverseitige Idempotenzgarantie. Nach unklarem Versand manuell im CDB prüfen.
- Netzwerk-/Anmeldefehler bei noch nicht gesendeten Textaufträgen beziehungsweise bestätigten Statusabfragen lassen den Auftrag erhalten. Neue ASR-/Summary-Versuche bleiben nach Fehler über die bestehende Wiederholen-Aktion steuerbar. Es gibt keinen stillen Cloud-/Lokal-Fallback.
- Die Knowledge-Areas-Seite zeigt die letzten 30 Übertragungen. Kein vollständiger Drive-Browser und kein bidirektionaler Sync. Originalarchivierung samt verknüpften Texten ist eine spätere Erweiterung.

## Nachweise

Automatische Tests: CDB-Adapter mit synthetischem Transport (Anmeldung, Refresh/Kontowechsel, lokale Defaults, Konto-/Zielbindung, Dateirechte, wiederaufgenommene ASR, bestätigte Publikation, falsche IDs, Antwortverlust, Deduplizierung); bestehende Native-/Studio-Tests einschließlich CSRF-/Origin-Schutz und Anmeldungsvoraussetzungen.

Browser: alle acht Grundseiten bei 1024 × 600 ohne angeschnittene Bedienelemente oder vertikalen Inhaltsüberlauf geprüft; Verbindung zusätzlich bei 1280 × 720. Bildschirmtastatur bei 1024 × 600 geprüft. Screenshots zeigen ausschließlich eine isolierte synthetische Bibliothek, keinen abgeschlossenen Live-Login.

Live: Firmenlogin, acht aktive Knowledge Areas, CDB-ASR und CDB-Summary sowie synthetischer End-to-End-Ingest in `staging_playground` bestätigt, einschließlich Wissensgraph und Vektorisierung. Siehe [Live-Test mit Zeiten und Qualitätsbefund](live-test-2026-10-12.md). **Noch offen:** weitere Firmenrichtlinien, Langaufnahmen und physischer Touchtest durch Chris. Keine produktiven Meetingtexte testweise hochgeladen.

[Microsoft Device Flow](https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-device-code)

## Auslieferung 12.10.2026

- Code: `8401583` auf `main`, zuvor `50707b7`; beide gepusht. 50/50 Python-Tests auf dem Pi mit UTF-8 und Qt-Offscreen bestanden. JavaScript-Syntax und Git-Whitespace geprüft.
- Studio 0.5.0 produktiv unter Pi-Loopback 8088 gestartet. Backend und Kiosk aktiv; Kiosk nach Auslieferung neu gestartet. Datei-Hashes von Backend, CDB-Adapter, HTML und CDB-JavaScript stimmen lokal und auf dem Pi überein.
- Nachprüfung: 18 bestehende Sitzungen vorhanden, aktueller Testjob weiterhin `completed`, keine aktive Aufnahme, kein neuer Verarbeitungsauftrag. Provider bleiben zunächst lokal; kein Firmenkonto automatisch angemeldet.
- Vorheriger Stand einschließlich SQLite-Backups gesichert unter `/home/chris/studio-backups/before-cdb-0.5.0-20261012-143055/`. Rückweg: Studio im Leerlauf stoppen, `application.tar.gz` in das Anwendungsverzeichnis zurückspielen, Studio und Kiosk starten. Datenbanken nur bei einem begründeten Datenproblem und nach gesonderter Prüfung restaurieren; die neue Integration verändert die vorhandenen Sitzungs-/Queue-Schemata nicht.
- Produktive neue Verbindungseinstellungen im Browser geprüft; physisches Pi-Display per Screenshot geprüft. Microsoft-Anmeldung und ein synthetischer CDB-End-to-End-Lauf stehen weiterhin aus. Für den nächsten Test: auf dem Pi Einstellungen → Verbindung → Mit Microsoft anmelden; anschließend nur `staging_playground` für synthetische Übertragungen verwenden.

### Live-Anmeldung: Clientkennung korrigiert (12.10.2026)

Nach Microsoft-Anmeldung scheiterte die CDB-Kontoprüfung: Cloudflare antwortete auf Pythons Standard-User-Agent mit HTTP 403, `text/plain`, `error code: 1010`. Eine identische nicht authentifizierte Anfrage mit `CDB-Recorder/0.5.0` erreicht den Dienst und erhält erwartungsgemäß HTTP 401 JSON. JSON-Anfragen und gestreamte Audiouploads senden nun diese explizite App-Kennung. Keine Cloudflare-Regeln oder Berechtigungen geändert. Zwei Regressionstests prüfen die Kennung in beiden Transportwegen; vollständige Pi-Suite: 52 Tests bestanden. Adapter auf dem Pi gesichert und im Leerlauf aktualisiert; Backend neu gestartet. Erneute Anmeldung erforderlich, weil vor erfolgreicher CDB-Identitätsprüfung keine Sitzung gespeichert wird.

Synthetische End-to-End-Probe nach erneuter Anmeldung erfolgreich: 23,346 Sekunden künstliche deutsche Sprache, ohne Kundeninhalt, mit überprüfbaren Aufgaben, Budget und offenem Bestellentscheid. [Nachweis und Qualitätsgrenze](live-test-2026-10-12.md).

## Studio 0.5.1: Anmeldung → Standardbereich → Übertragung

Die mobile App (`src/features/ConnectionPanel.tsx`, `src/services/connection.ts`) dient als Ablaufreferenz: Anmeldung, verfügbare Bereiche laden, explizite Auswahl als Standard für „Ins Brain“, späterer Wechsel. Im Pi-Frontend werden Bereiche nach bestätigter Anmeldung beziehungsweise beim Laden einer angemeldeten Sitzung automatisch geladen. Unter **Einstellungen → Verbindung** steht der Standard direkt unter dem Konto. Derselbe gespeicherte Standard lässt sich unter Knowledge Areas ändern. Es wird kein erster Bereich automatisch gewählt und keine Aufnahme automatisch übertragen.

Am Meeting öffnet **Meetingaktionen → Ins Brain übertragen …** ein eigenes Touchfenster: Der Standard ist vorbelegt; ein anderes Ziel gilt nur für dieses Meeting und verändert den Standard nicht. Erst **Jetzt übertragen** reiht den Textauftrag ein. Bereits eingereihte Publikationen behalten ihr eingefrorenes Ziel, auch bei einem späteren Standardwechsel.

Standard ist dauerhaft und an Benutzer, Mandant und CDB-Umgebung gebunden. Veraltete Bereichsantworten werden nach Kontowechsel/Abmeldung verworfen. Fehlende oder entfernte Bereiche zeigen eine Aufforderung zur Auswahl; Ladefehler lassen sich über „Bereiche aktualisieren“ erneut prüfen. Doppeltippen während des Versands sendet nur eine Anfrage; der bestehende Backend-Fingerprint verhindert zusätzlich doppelte Publikationen desselben Inhalts/Ziels.

Nachweise: 53 Python-Tests auf dem Pi und 6 JavaScript-Tests (`node --test tests/js/cdb-flow.test.cjs`) bestanden. Browserprüfung mit isoliertem Demo-Konto bei 1024 × 600: automatisches Laden, Standard speichern, nach Neuladen erhalten, abweichendes Meetingziel ohne Standardänderung; Verbindungsseite und Übertragungsfenster ohne Inhaltsüberlauf/Scrollpfeile. Screenshots `06-standardbereich.png` und `07-meetingziel.png` sind synthetische Vorschauen. Für diese UI-Prüfung keine zusätzliche echte Übertragung ausgeführt und kein Standard für Chris vorgewählt. Der echte CDB-End-to-End-Nachweis der vorherigen Version steht im verlinkten Live-Testbericht.

Auslieferung 0.5.1: Code-Commit `00a82cf` auf `main` gepusht; im Leerlauf auf den Pi übertragen. Vorversion unter `/home/chris/studio-backups/before-cdb-flow-0.5.1-20261012/application.tar.gz` gesichert. Backend und Kiosk nach Neustart aktiv. Versionsprüfung 0.5.1, 19 Sitzungen erhalten, Microsoft-Sitzung erhalten, bereits vom Nutzer gewählter Standard `staging_playground` erhalten. Backend-/Frontend-Hashes lokal und auf dem Pi identisch. Produktiven Verbindungsbildschirm mit automatisch geladenem Standard im Browser bestätigt. Keine weitere echte Publikation ausgelöst.

## Produktiver Vergleichstest 0.5.1

Der vollständige neue Ablauf wurde anschließend mit derselben synthetischen Audiodatei lokal und über CDB getestet, jeweils einschließlich bestätigter Übertragung in den bestehenden Standardbereich `staging_playground`. [Zeiten, Qualität, Quittungen und Screenshots](live-test-0.5.1-2026-10-12.md).
