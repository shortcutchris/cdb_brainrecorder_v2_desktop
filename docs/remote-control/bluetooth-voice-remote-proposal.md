# Bluetooth-Fernbedienung für CDB Voice One

Stand: 16. Oktober 2026 · Codebasis Recorder 0.5.60 · **Entwurf, nicht implementiert oder am Pi abgenommen.**

**Priorität nach Nutzerentscheidung: zurückgestellt. Zuerst wird die CDB-Mobile-App als Software-Fernbedienung umgesetzt.**

Späterer Vorschlag: Eine ausdrücklich gekoppelte BLE-HID-Fernbedienung steuert den
vorhandenen Python-Gesprächsdienst. Der erste Meilenstein umfasst zwei getrennte
Tasten für **Gespräch starten** und **Gespräch beenden**. Eine dritte Taste kann
anschließend **Mikrofon stumm/ein** schalten. Gedrückthalten zum Sprechen folgt
frühestens nach einer eigenen Audio- und Ausfallprüfung.

Die Fernbedienung überträgt Tasten, kein Mikrofon-Audio. ReSpeaker bleibt Eingang,
Marshall bleibt der eingerichtete Ausgang. Touch-Bedienung, Statusanzeige und
Bereitschaftston bleiben maßgeblich. Das bestehende Starten einer Cloud-Sitzung
wird durch einen Knopf nicht schneller; man wartet weiterhin auf „Hört zu“.

## Belegte Ausgangslage im Repository

Gelesen wurden `AGENTS.md`, `README.md`, `docs/architecture/README.md` und
`docs/customer-image/README.md`. Das Architekturwort „Remote Controller“ meint
bisher unter anderem Geräteverwaltung und den **nur lesenden** LAN-Bildschirm;
dieser Entwurf fügt eine lokale Eingabe hinzu und erweitert keinen LAN-Zugriff.

| Vorhandener Baustein | Befund und Konsequenz |
| --- | --- |
| `services/bluetooth_audio.py`, `public_devices()` | Zeigt auch Nicht-Audiogeräte. Eine angezeigte Fernbedienung ist noch kein Beleg für funktionierende Steuerung. |
| `BluetoothAudio._main()`, `ask()`, `make_agent()` | BlueZ-Systembus, eigener `KeyboardDisplay`-Agent, expliziter Zielbezug, Bestätigung und Zeitlimits. Kein globaler Standardagent. Diese Grenzen erhalten. |
| `make_agent().AuthorizeService()` | Erlaubt bisher nur Audio-/AVRCP-UUIDs. Bei angeforderter Service-Autorisierung wird HID abgewiesen. Deshalb ist „einfach koppeln“ kein nachgewiesener vollständiger HID-Pfad. |
| `BluetoothAudio._operate()` | `Pair` → `Trusted=True` → `Connect`; Erfolgstext setzt Audio voraus. HID benötigt eigene Klassifikation und „Fernbedienung verbunden“, keine Suche nach PipeWire-Audioports. |
| `web_server.py`, `StudioApp.action()` | Reihenfolge `control_lock` → `controller.lock` → `engine.recorder.lock`. Alle Fernbedienungsaktionen müssen dieselbe Reservierung und Sperrreihenfolge benutzen. |
| `StudioApp.wake_start()` | Geeignete Vorlage: Bereitschaft prüfen, gespeicherte kontogebundene Bereiche laden, `reserve(owner_kind='device', cached_binding=...)`, `start_native()`, bei Fehler `end()`. Die Methode verlangt ausdrücklich aktiviertes Wake; daher **nicht unverändert für die Fernbedienung aufrufen**. |
| `services/app_activity.py` | Leitet Sperren aus tatsächlichem Zustand ab: Aufnahme/Pause, Tests, Bluetooth-Einrichtung, Wartung und Live sind abgesichert. Keine zweite unabhängige Zustandsmaschine für Audio bauen. |
| `services/live_conversation.py` | Eigentümer-Lease und Generation verhindern fremde/veraltete Eingriffe. `end(generation=...)` ist bereits vorhanden. `mute()` verlangt eine aktuelle Lease. |
| `LiveConversation.reserve()`, `_transcript()`, `_watch()` | Gerät besitzt anfangs 120 Sekunden Frist; Transkripte verlängern sie, insgesamt maximal 1.200 Sekunden. Ein Remote-Listener darf diese Grenzen nicht durch künstliche Browser-Pulses umgehen. |
| `services/live_audio.py`, `PcmGate` | Stummschaltung leert den Puffer und verwirft alte Audio-Epochen. `reserve()` setzt zunächst `muted=False`; `start_native()` erzeugt Audio später. Für PTT muss ein anfänglich geschlossenes Gate ausdrücklich vor dem Capture gelten. |
| `studio/live.js`, `studio/assistant-tools.js` | Bereits Unterstützung für gerätegestartete Gespräche; Live-Ansicht öffnet automatisch, Touch-Mute funktioniert bei `owner_kind='device'`. |
| `config/udev/70-cdb-respeaker.rules` | Berechtigt nur das ReSpeaker-USB-Gerät. Daraus folgt keine Berechtigung zum Lesen von `/dev/input/event*`. |

Diese Untersuchung hat keine Bluetooth-Verbindung verändert, keine Aufnahme
geöffnet und keine Mikrofon-/Audio-Tests gestartet.

## Hardwarewege und belastbare Grenzen

### 1. Kaufbare BLE-HID-Fernbedienung: erster Integrationsversuch

Ein Presenter oder eine kleine HID-Tastenfernbedienung kann vom Linux-Inputsystem
als Tastengerät geliefert werden. Für einen Prototyp genügt ein Gerät mit zwei
unterscheidbaren Tasten und ohne notwendige Hersteller-Cloud. Vor einem Kauf
oder einer Produktfreigabe müssen **genau Modell, Revision und BLE-Modus** geprüft
werden; „Bluetooth“ allein beschreibt weder HID noch nutzbare Tastencodes.

Konkreter Prüfkandidat ist der **Logitech R500s**: Der Hersteller dokumentiert
BLE und USB-Empfänger; seine Konfigurationssoftware unterstützt Windows/macOS.
Daraus folgt keine bestätigte Pi-Kompatibilität. Die R500-Anleitung beschreibt
Vor/Zurück und einen separaten Laser; der Laser ist **keine zugesicherte dritte
HID-Taste**. Lange Tastendrücke beziehungsweise deren Zusatzfunktionen dürfen
nicht ohne Messung vorausgesetzt werden. Für Start/Ende reichen zwei nachgewiesene
Codes. Falls nur mit USB-Empfänger zuverlässig, ist das eine separate
Fallback-Variante, kein bestandener BLE-Test.
[Produktdaten](https://www.logitech.com/en-us/shop/p/r500s-laser-presentation-remote),
[Herstelleranleitung R500](https://support.logi.com/hc/en-150/articles/360023459813-Getting-Started-R500).

Für drei Funktionen bevorzugen wir später drei tatsächlich unabhängige Tasten.
Eine Ein-Tasten-Fernbedienung mit Kurz-/Doppel-/Langdruck ist möglich, aber für
den ersten Touch-orientierten Ablauf unnötig schwer erklärbar. Smartphone-
Kameraauslöser und Medienknöpfe sind unbestätigte Kandidaten: häufig fehlen
verlässliche Hold/Release-Signale; Lautstärke-/Medientasten können gleichzeitig
den Desktop oder Lautsprecher bedienen.

**Flic nicht mit Standard-HID gleichsetzen.** Das offizielle Linux-HCI-SDK nutzt
einen eigenen Daemon mit direktem Controllerzugriff und nennt mögliche
Interferenzen mit BlueZ. Es ist damit kein naheliegender erster Weg auf dem
bereits für Marshall verwendeten Adapter. Ein separater Adapter oder Hub würde
eine andere Integration und zusätzliche Betriebsprüfung bedeuten.
[Offizielles Flic Linux SDK](https://github.com/50ButtonsEach/fliclib-linux-hci).

### 2. Eigene ESP32-Fernbedienung: klare Produkttasten, mehr Entwicklung

Espressif stellt ein offizielles `esp_hid_device`-Beispiel für Bluetooth Classic
und BLE sowie HID-Report- und Batterie-APIs bereit. Ein passend unterstütztes
ESP32-Board mit drei beschrifteten Tasten kann deshalb denselben Pi-HID-Empfänger
bedienen. Zielchip und ESP-IDF-Version vor Beginn festschreiben; nicht jeder
ESP32-Typ unterstützt dieselben Bluetooth-Transporte.
[ESP-IDF HID Device API und Beispielverweis](https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-reference/bluetooth/esp_hidd.html).

Vorgeschlagenes Geräteverhalten: eigene feste HID-Codes, Down/Up für jede Taste,
Entprellung, nur auf physischen Langdruck zeitlich begrenzt koppelbar,
persistenter Bond, ausdrückliches Zurücksetzen, sauberer Wiederanlauf nach
Batteriewechsel. Beispielsweise F13/F14/F15 statt Lautstärke/Power verwenden;
die tatsächliche Linux-Abbildung und Freiheit von Desktop-Shortcuts prüfen.

Vorteil: klare Tasten Start/Ende/Stumm und kontrollierbare Release-Ereignisse.
Aufwand: Gehäuse, Stromversorgung/Laden, Sleep/Reconnect, Firmwarepflege und
Produkt-/Funkzulassung. Ein Entwicklungsboard ist noch keine fertige
Batterie-Fernbedienung. Eine lokale LED kann „verbunden“ anzeigen; „Mikro wirklich
stumm“ darf sie nur nach bestätigtem Pi-Status melden. Dafür wären später
Output-Reports oder ein gesonderter Rückkanal nötig.

## Geplante Integration

```text
Fernbedienung → BlueZ/Bond → Linux HID/evdev
                            ↓ nur zugewiesenes Gerät
                   RemoteInput (ohne Audiozugriff)
                            ↓ normalisierte Aktion
                   StudioApp unter vorhandenen Locks
                            ↓
                   LiveConversation / NativeLiveAudio
                            ↓
                   bestehender Touch-Status / ReSpeaker-LED
```

### Paarung, Identität und Rechte

1. Unter **Einstellungen → Fernbedienungen → Bluetooth-Fernbedienung**: „Verbinden“, anschließend
   Geräteauswahl und die bereits vorhandene Kopplungsbestätigung. Derselbe
   BlueZ-Manager bleibt zuständig; keine zweite konkurrierende Agent-Instanz.
2. HID-Klassifikation ergänzen, für BLE insbesondere HID-Service `0x1812`, bei
   späterer Classic-Unterstützung `0x1124`. Audio- und HID-Berechtigungen getrennt
   behandeln. `AuthorizeService` nur für den ausdrücklich gewählten Vorgang und
   die vorgesehenen Dienste erweitern; kein allgemeines Akzeptieren fremder UUIDs.
3. Nach Bindung ein eigener Schritt „Tasten prüfen“: Start-/Ende-Taste drücken;
   der Test zeigt lediglich „Erkannt“, löst noch kein Gespräch aus. Mapping erst
   danach aktivieren. Initialzustand neuer und aktualisierter Profile: deaktiviert.
4. Gerätezuordnung verbindet BlueZ-Identität/Bond, Linux-Bluetooth-Bustyp,
   überprüfte Input-Eigenschaften und beobachtete Event-Nodes. Weder Anzeigename
   noch VID/PID noch eine feste Nummer wie `event7` allein reichen. Zufällige
   BLE-Adressen und mehrere Input-Nodes eines Geräts bei Reconnect berücksichtigen.
5. Nur das zugewiesene Gerät lesen; normale Tastatur, Touchscreen und Marshall-
   Medienereignisse dürfen keine Gesprächsaktionen auslösen. Kein allgemeiner
   Tastaturmitschnitt. Für produktiv unterstützte Modelle gezielte udev-Rechte
   an eine eigene Gruppe, z. B. `cdb-remote`, vergeben. Nicht pauschal alle
   Input-Geräte für den App-Benutzer öffnen und die App nicht als root starten.
6. Vor Umsetzung die tatsächlichen sysfs-/udev-Attribute des gewählten Geräts
   ermitteln. Eine genaue Regel kann erst danach qualifiziert werden. Eine
   laufzeitgeprüfte Bond-Zuordnung bleibt zusätzlich nötig; ein Herstellername
   ist keine Authentifizierung. Falls gezielte Rechte über alle unterstützten
   Geräte nicht abbildbar sind, separaten eng begrenzten Input-Broker entwerfen.

BlueZ unterscheidet Paarung und `Trusted`; `Connect()` kann mehrere unterstützte
Profile verbinden. App-Zuweisung ist daher eine zusätzliche Berechtigung über
den Bluetooth-Bond hinaus. Geräte ohne Code/Display verwenden gegebenenfalls
Just Works: Bestätigung am Touchscreen schützt nicht nachträglich kryptografisch
vor einem aktiven Angreifer während dieser Paarung. Dafür den physischen
Kopplungsmodus kurz halten; einen Bond niemals nur anhand des Namens übernehmen.
[BlueZ Device API](https://raw.githubusercontent.com/bluez/bluez/master/doc/org.bluez.Device.rst),
[BlueZ Agent API](https://raw.githubusercontent.com/bluez/bluez/master/doc/org.bluez.Agent.rst),
[Bluetooth SIG Sicherheitsleitfaden](https://www.bluetooth.com/download/bluetooth-security-and-privacy-best-practices-guide/).

Input-Rechte müssen für den tatsächlich laufenden Benutzerdienst funktionieren,
auch nach Boot, Ab-/Anmelden und Reconnect. Automatische Sitzungs-ACLs nicht
voraussetzen; systemd behandelt bestimmte Input-Klassen gezielt.
[systemd uaccess-Regeln](https://cgit.freedesktop.org/systemd/systemd/tree/src/login/70-uaccess.rules).

### Interner Vertrag und Zustandswechsel

Neue Module als Vorschlag: `services/remote_input.py` für Linux-Ereignisse und
`services/remote_control.py` für Zuordnung, Entprellung und begrenzte Warteschlange.
Unter Linux bietet sich `python-evdev` an; Version/ARM64-Wheel und Einbindung in
die isolierte Runtime müssen vor Festlegung geprüft werden. Die folgenden
Signaturen sind Entwurf, keine heute verfügbaren API-Endpunkte:

```python
StudioApp.remote_command(action, device_id, connection_epoch,
                         event_id, received_at, expected_generation)
# action: start | end | set_muted
# set_muted zusätzlich mit streng booleschem muted-Wert
```

Der Listener gibt ausschließlich feste Aktionen weiter, keine Shellbefehle,
URLs oder frei konfigurierbaren Tastaturmakros. Backend-Zustand entscheidet.
Jede Warteschlangennachricht trägt Verbindungsepoche, lokale laufende Ereignis-ID,
monotone Empfangszeit und die beim Empfang aktuelle Gesprächsgeneration.
Doppelte/zu alte Nachrichten sowie alte Verbindungsepochen verwerfen. Eine
physische Taste erzeugt pro Down/Up-Zyklus höchstens eine Aktion. `EV_KEY=2`
ist Repeat und löst kein weiteres Starten/Schalten aus. Nach `SYN_DROPPED` gemäß
Kernel bis zum nächsten `SYN_REPORT` verwerfen und Zustand neu lesen; erst nach
neutralem Tastenstand wieder scharf schalten.
[Linux Input-Ereignisvertrag](https://www.kernel.org/doc/html/latest/input/event-codes.html).

| Zustand | Start | Ende | Mikro stumm/ein |
| --- | --- | --- | --- |
| idle / ended / error, Ressourcen frei | Konto, lokale Remote-Freigabe, gespeicherte Wissensbereiche, Gerätebereitschaft prüfen; `connecting` reservieren | ohne Wirkung | ohne Wirkung, kein stiller Start |
| connecting | ohne zweite Sitzung | aktuelle Generation abbrechen | zuerst nur „stumm“ erlauben, korrekt vor Capture wirksam machen; Freigabe erst nach Ready |
| listening / thinking / speaking | ohne Wirkung | `closing`, lokale Audiofreigabe wie Touch | aktueller Zustand atomar ändern, vorhandenes `PcmGate` nutzen |
| reconnecting | ohne Wirkung | abbrechen | Stumm erlaubt; kein automatisches Entstummen |
| closing | gesperrt bis echte Freigabe | idempotent | kein Entstummen |
| Aufnahme/Pause, Tests, Einrichtung, Wartung | mit vorhandener Begründung abweisen | beendet keine Aufnahme und keinen Test | verändert weder Aufnahme noch Systemlautsprecher |

Eine Startaktion nutzt einen neuen gemeinsamen Helfer für gerätegestartete
Gespräche. Wake behält seine bisherige Freigabeprüfung; Remote erhält eine eigene
kontogebundene Freigabe. Remote funktioniert auch bei ausgeschaltetem Rufwort.
Beim Kontowechsel wird die Remote-Startfreigabe ungültig, bis sie für das neue
Konto bestätigt wird. Keine Bereiche vom vorherigen Konto übernehmen.

Vor Reservierung Wake kontrolliert suspendieren; danach die vorhandenen
Audio- und Aktivitätssperren nutzen. Nach Ende greift wieder die vorhandene
Wake-Konfiguration. Reservierung ist `owner_kind='device'`, damit kein Browser
als künstlicher Eigentümer pulsieren muss. Vor Freigabe testen, dass die
bestehende Cloud-Validierung auch beim gecachten Binding tatsächlich vor
Audioübertragung erfolgt.

Für Ende die beim Empfang festgehaltene Generation bis zum Aufruf prüfen.
Für Mute unter Live-Lock dieselbe Generation und aktuelle interne Lease prüfen;
keine Lease in HID, Diagnose oder UI senden. Eine Toggle-Taste wird unter
Lock in einen konkreten booleschen Zielwert übersetzt. Physische Bedienung darf
nach ausdrücklicher lokaler Zuweisung auch ein per Touch begonnenes Gespräch
beenden/stummschalten; sie darf dessen Lease-Lebensdauer nicht verändern.

Normale Fernbedienungen schlafen: Bei Verbindungsverlust wird ein laufendes
Gespräch im ersten Meilenstein weiter am Touch bedient, keine alten Eingaben
werden nachgespielt. Die UI meldet „Fernbedienung getrennt“. Wiederverbinden
startet nichts. Dieser Modus ist keine Sicherheits-Stummschaltung.

Öffentliche lokale Einstellungs-API als Vorschlag:
`GET /api/remote/status` und `POST /api/remote/configure` für Zuordnung,
Aktivierung, Tastentest, Entfernen. Gleiche lokale Request-/Origin-Prüfung und
`configure`-Sperre wie die übrigen Einstellungen. Keine neue LAN-Steuer-API,
keine Änderung des Empfängerports 8090 und kein Zugriff aus dem Geräteportal.
Normale Tastenaktionen erfolgen direkt intern.

Für die parallel untersuchte CDB-Mobile-Steuerung denselben internen
Befehlsdienst und dieselben Generation-/Aktivitätssperren verwenden. Der
Bluetooth-Eingang authentifiziert ein lokal zugewiesenes Gerät; ein künftiger
CDB-Steuerbroker muss seine eigene Benutzer-/Geräteautorisierung davor setzen.
Beide dürfen nur feste normalisierte Befehle weiterreichen. `DisplayHub` und
der bisherige Bildschirmempfänger bleiben lesend. Der mobile Broker ist ein
separater Entwurf, keine Voraussetzung für den ersten Bluetooth-Meilenstein.

### Push-to-talk erst als eigener zweiter Funktionsumfang

„Nur senden, solange gedrückt“ ist etwas anderes als ein kurzer Startknopf.
Es benötigt garantierte Down/Up-Ereignisse und einen anfangs geschlossenen
Audioeingang. Der jetzige Startpfad setzt `muted=False`; ein nachgeschobenes
`mute(True)` reicht nicht als Nachweis, dass vorher keine Samples gesendet wurden.

Für PTT ein eigenes Gate-Modell vorsehen:
`effective_muted = user_muted or not ptt_held or startup_blocked or transport_fault`.
Touch-Stumm darf durch PTT-Down nie aufgehoben werden. Das Gate muss bereits bei
Erzeugung des Audiotransports geschlossen sein. Release, Geräteverlust,
Listener-Ausfall, Überlauf, Generation-/Kontowechsel und ein begrenztes
Hold-Timeout schließen es unmittelbar. Nach Störung braucht es einen frischen
Down/Up-Zyklus. Consumer-HID liefert nicht zwingend einen periodischen Hold-
Heartbeat; Verlust wird erst nach Verbindungs-/Watchdog-Erkennung bemerkt.
Eine garantierte kurze Abschaltfrist erfordert entsprechend qualifizierte
Hardware bzw. ein zusätzliches Hold-Lease-Protokoll.

Eine Taste öffnet nicht pro Satz eine neue Cloud-Sitzung. Die Sitzung wird
separat gestartet; gehalten wird erst nach Bereitschaft. Ob Loslassen eine
Modellantwort unmittelbar auslöst, hängt von VAD/Turn-Erkennung des CDB-Vertrags
ab. Ohne geprüften Serververtrag kein Versprechen einer expliziten
„Satz abschicken“-Semantik. Stummschaltung des Eingangs bedeutet außerdem
nicht automatisch Abbruch einer bereits laufenden Assistentenantwort.

## ReSpeaker, Marshall und Funkbetrieb

BLE-HID fügt keine Audioquelle hinzu. Weder das ReSpeaker-Gerät noch Marshall-
Profil, Lautstärke oder Default-Sink werden für die Fernbedienung umgeschaltet.
BlueZ bleibt der gemeinsame Bluetooth-Manager; kein Neustart von `bluetoothd`
oder Adapter-Aus-/Einschalten als allgemeine Reconnect-Maßnahme.

Gleichzeitiger Betrieb ist technisch plausibel, aber in diesem Auftrag nicht
am Gerät belegt. Gemeinsam genutzter Funkadapter, 2,4-GHz-WLAN, Entfernung,
Sleep/Reconnect und laufende Marshall-Ausgabe gehören in die Abnahme. Dauerhafte
Discovery vermeiden; normale HID-Nutzung zählt nicht als „Bluetooth wird
konfiguriert“ und sperrt deshalb kein Gespräch. Nur Paarung/Umkonfiguration
behalten die bestehende exklusive Einrichtungssperre.

## Prüfung und Auslieferung

Erster Meilenstein: genau ein Modell auf einem Testgerät koppeln, dessen
identifizierte Input-Nodes und Down/Up-Codes dokumentieren, erst dann zwei
explizite Aktionen aktivieren. Zunächst Testanzeige ohne Live-/Audiozugriff;
anschließend separat freigegebene Hardwareabnahme. Kein Austausch des
Wake-Modells und keine Änderung der Mikrofonkalibrierung nötig.

Geplante automatisierte Tests mit künstlichen Ereignissen und Fake-Audio:

- Ein Druck startet exakt einmal; Repeat, Bounce, Doppelzustellung und alte
  Queue-Ereignisse starten oder beenden keine spätere Sitzung.
- Start konkurriert mit Wake, Touch, Aufnahme und Wartung: nur eine Reservierung;
  Ende während langsamer Anmeldung/Verbindungsaufbau räumt dieselbe Generation auf.
- Kontowechsel, entfernte Knowledge Areas, fehlende Anmeldung und ungültige
  Bindung verhindern Remote-Start vor Audioübertragung.
- Fremde Tastatur, gleichnamiges Bluetooth-Gerät, Marshall-Medientasten und
  falscher Input-Node lösen nichts aus. Reconnect mit neuer Node-Nummer funktioniert.
- Rechte fehlen, Adapter fehlt, Kopplung abgelehnt/abgebrochen: verständlicher
  Status, keine Rechteausweitung, Touch/Wake bleiben nutzbar.
- HID-Service-Autorisierung gilt nur für das konkrete Ziel; bestehende
  Bluetooth-Audiotests bleiben gültig. Kein Audio-Profilaufruf für reine HID-Geräte.
- Stumm verwirft alte Samples; spätes Release/Mute trifft keine Folgegeneration.
  Für PTT zusätzlich erster Frame stumm, Release-Verlust, Watchdog, Ausfall und
  Touch-Stumm-Priorität. PTT gilt erst nach diesen Nachweisen als implementiert.
- Neues leeres Profil ist deaktiviert; Update bewahrt vorhandene Audio-/Wake-
  Einstellungen; Rollback toleriert neue Remote-Einstellungen. Kein Bond im Image.

Passende bestehende Tests: `tests/test_bluetooth_audio.py`,
`tests/test_app_activity.py`, `tests/test_live_conversation.py`,
`tests/test_live_audio.py`, `tests/test_audio_release.py`,
`tests/test_wake_word.py`, `tests/test_customer_image.py`,
`tests/js/live.test.cjs`. Neue Event- und Controller-Tests benötigen keine
Audiohardware. Hardwareabnahme separat: 100 Betätigungen ohne Doppelaktion,
Sleep/Wake, Batteriewechsel, fünf Reconnects, App-/Pi-Neustart und Koexistenz mit
ReSpeaker + Marshall; Ereignis-zu-Status-Latenz und Cloud-Startzeit getrennt messen.
Das sind geplante Kriterien, keine bereits bestandenen Ergebnisse.

**Image-Auswirkung dieser Dokumentänderung: keine.** Bei Umsetzung werden
`services/`- und `studio/`-Dateien aus `fleet/releases.py` bereits grundsätzlich
zugelassen; neue Dateien trotzdem im Paketmanifest prüfen. Ein neues
`evdev`-Paket, udev-Regeln, Gruppen oder Input-Broker sind Runtime-/Systemänderungen
und kommen **nicht** allein durch das signierte App-Paket auf vorhandene Geräte.
Dafür einen eigenen kontrollierten Migrationsweg und Runtime-Kompatibilität
qualifizieren; auf ungeeigneter Runtime die Funktion deaktiviert halten.

Für frische Images wären mindestens `requirements.txt`,
`scripts/prepare_customer_image.py`, `deploy/customer-image/01-run-chroot.sh`
und die Benutzer-/Gruppeninitialisierung zu prüfen. Der Export kopiert aktuell
nur die ausdrücklich benannte ReSpeaker-Regel: eine neue Remote-Regel muss
explizit mitgenommen und installiert werden. ARM64-Paketverfügbarkeit mit dem
aktuellen `--only-binary=:all:`-Build prüfen. Manifest-/Rootfs-Audit und
`tests/test_customer_image.py` entsprechend erweitern; zweite SD-Karte separat
booten. Dokumentation und In-App-Hilfe müssen die Tastenzuordnung, Startwartezeit,
Stumm-Grenzen und Wiederverbindung erklären. Paarungsdaten, Geräteadressen,
Kundenzuordnung und persönliche Tokens gehören nie ins Factory-Image.
