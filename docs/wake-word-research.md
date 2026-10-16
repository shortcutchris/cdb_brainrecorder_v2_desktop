# Aktualisierung 16.10.2026

[Vertiefte Recherche mit aktuellen Modellkarten und Pi-Vergleich](wake-word-research/2026-10-16/README.md). Die folgenden Abschnitte sind der ältere Recherchestand; insbesondere sind ESPHome-v2-Nabu und das installierte mehrsprachige Nabu unterschiedliche Gewichte.

# Lokales Aktivierungswort für CDB Voice One

Stand: 13. Oktober 2026. Entscheidungsvorlage aus Primärquellen und Prüfung des vorhandenen Codes; noch keine Implementierung und kein Mikrofon- oder Leistungstest auf dem Pi.

## Verbindliche Produktvorgabe

Der Nutzer hat bestätigt: eigener Ein-/Ausschalter in den Einstellungen, standardmäßig aus. Auslösen ausschließlich ohne laufende Aufnahme (einschließlich Pause) und ohne laufendes oder startendes Live-Gespräch. Diese Regeln sind im Python-Backend atomar durchzusetzen, nicht nur durch ausgeblendete Buttons.

## Empfehlung

Der Raspberry Pi 5 mit 16 GB kann voraussichtlich problemlos einen kleinen lokalen Wake-Word-Detektor zusätzlich betreiben. Entscheidend sind die Zuverlässigkeit im Raum, der Wechsel des Mikrofonbesitzers und die Verbindung zum Brain. Mehr RAM allein verbessert die Erkennung nicht.

Für den ersten Prototyp empfehle ich **microWakeWord über `pymicro-wakeword`, zunächst mit einem vorhandenen Modell wie „Okay Nabu“**. Das Aktivierungswort bleibt lokal. Erst nach einer gültigen Erkennung und erfolgreicher Zustandsprüfung startet das vorhandene CDB-Voice-One-Gespräch mit den gemerkten Knowledge Areas. Die Funktion ist ausdrücklich einschaltbar, standardmäßig aus. Ein eigenes „Hey Brain“ oder „Hey Mira“ ist eine zweite Ausbaustufe mit eigenem Training und Raumtest, keine bloße Texteinstellung.

Die Empfehlung ist eine technische Ableitung, keine bereits gemessene Freigabe. Die Trennung zwischen lokalem Erkennungswort und dem anschließend online laufenden Gespräch muss in der Oberfläche sichtbar bleiben.

## Geeignete Engines

| Lösung | Befund aus Primärquellen | Einschätzung für dieses Gerät |
|---|---|---|
| microWakeWord | Framework Apache-2.0; Modelle für kleine Geräte; eigenes Training möglich, laut Projekt aber anspruchsvoll. [Framework](https://github.com/OHF-Voice/micro-wake-word), [Modell-Lizenz](https://github.com/esphome/micro-wake-word-models/blob/main/LICENSE). | Bevorzugter freier MVP. Erst unverändertes, versioniertes Modell messen, dann eigenen Namen trainieren. |
| Python microWakeWord | Python-API für 16-kHz-Mono-PCM, 16 Bit; aktuelles PyPI-Paket 2.5.0 mit ARM64-Wheel und Python ≥3.9. [API](https://github.com/OHF-Voice/pymicro-wakeword), [Paket](https://pypi.org/project/pymicro-wakeword/). | Passt zur vorhandenen Python-Audiokette. Runtime und Modell separat pinnen; kein TensorFlow-Training auf dem produktiven Pi. |
| openWakeWord | Code Apache-2.0, mitgelieferte Modelle ausdrücklich CC BY-NC-SA 4.0. Unterstützt offiziell derzeit englische Modelle; 16-kHz-PCM und 80-ms-Schritte, VAD und optionale Speex-Rauschunterdrückung. [Projekt samt Lizenzhinweis](https://github.com/dscripka/openWakeWord). | Gute Vergleichsengine, aber vor Auslieferung eines kommerziellen CDB-Geräts die Modellrechte klären; Code-Lizenz allein genügt nicht. Nicht erste Wahl für ein fertiges deutsches Markenwort. |
| Picovoice Porcupine | Eigene Aktivierungswörter, Deutsch und Raspberry-Pi-Ziel werden in der Modell-API unterstützt; AccessKey erforderlich. [Modell-API](https://picovoice.ai/docs/model-api/porcupine/). SDK-Code offen, Modelle und Inferenzengine proprietär; Hersteller nennt derzeit Enterprise-Testzugang und keine eigenen Privatnutzer-Tarife. [Hersteller-FAQ](https://picovoice.ai/docs/faq/general/). | Alternative, wenn ein deutsches Wunschwort schnell wichtig ist und ein kommerzieller Anbieter akzeptiert wird. Preis und Nutzungsrecht vor Festlegung konkret anfragen; kein kostenloses Dauerangebot unterstellen. |

Die Sprache des Aktivierungsworts und die spätere Gesprächssprache sind unabhängig: „Okay Nabu“ kann ein deutschsprachiges Brain-Gespräch starten. Das untersuchte [Okay-Nabu-v2-Manifest](https://github.com/esphome/micro-wake-word-models/blob/main/models/v2/okay_nabu.json) nennt allerdings `trained_languages: ["en"]`; daraus folgt keine Garantie für deutsche Aussprache. Varianten müssen mit realen Nutzern geprüft werden. Die Home-Assistant-Entwickler berichten über verbesserte Akzentabdeckung durch zusätzliche Sprachaufnahmen; das ist kein Nachweis für jede beliebige Modell-Datei. [Entwicklerbericht](https://community.home-assistant.io/t/help-us-make-voice-better-in-under-a-minute/786333).

Ein passendes Referenzprojekt ist [OHF Linux-Voice-Assistant](https://github.com/OHF-Voice/linux-voice-assistant): lokale Wake Words, ARM64, PulseAudio, Gesprächsstart und Timer. Es bezeichnet sich als experimentell. Wir sollten dessen Audio-/Lebenszyklusideen prüfen, aber weder Home Assistant noch dessen gesamtes Satellitenprotokoll für CDB voraussetzen.

## Belastbarkeit der Hardware-Aussagen

Es gibt **noch keine Messung von CPU, RSS, Latenz oder Fehlaktivierungen auf unserem Pi**. Auch die Zeit bis zur ersten CDB-Antwort wurde für Wake-Starts nicht gemessen.

- openWakeWord nennt als Projektangabe 15–20 gleichzeitige Modelle in Echtzeit auf einem einzelnen Pi-3-Kern. Das stützt die grundsätzliche Machbarkeit, ist aber kein Benchmark unserer Konfiguration. [Primärquelle](https://github.com/dscripka/openWakeWord).
- Linux-Voice-Assistant nennt 1 GHz CPU und mindestens 512 MB Speicher für sein anderes Gesamtprodukt. Daraus darf man nicht dessen RAM-Bedarf für unsere Anwendung übernehmen. [Anforderungen](https://github.com/OHF-Voice/linux-voice-assistant#requirements).
- Im Okay-Nabu-Manifest stehen 26.080 Bytes Tensor-Arena. Das ist ein Modellparameter für die eingebettete Runtime, **nicht** der gesamte Python-Prozessspeicher. [Manifest](https://github.com/esphome/micro-wake-word-models/blob/main/models/v2/okay_nabu.json).
- Ein älteres [ARM64-Paketproblem, Issue #13](https://github.com/OHF-Voice/pymicro-wakeword/issues/13), meldet eine falsch eingepackte x86-Bibliothek. Die aktuelle Version wurde deshalb zusätzlich statisch geprüft: Das veröffentlichte `pymicro_wakeword-2.5.0-py3-none-manylinux_2_35_aarch64.whl` enthält eine ELF-Bibliothek mit `e_machine=183` (AArch64). SHA256: `6c75b77c936efd19b8c35a094cb7e3fdbd4ebcd0f63635a0851ce591990829f2`. Die Datei wurde nur im Arbeitsspeicher entpackt; kein Paket wurde installiert oder ausgeführt. Das bestätigt die Architektur, nicht die Laufzeitfunktion. Das Wheel setzt glibc ≥2.35 voraus. [Release-Dateien](https://pypi.org/project/pymicro-wakeword/#files).

Whisper dauerhaft für die Erkennung eines einzigen Wortes laufen zu lassen ist hier kein sinnvoller erster Ansatz: Wir brauchen einen kleinen Klassifikator, während die vorhandene Transkriptionswarteschlange ihre Rechenzeit behalten soll.

## ReSpeaker, Marshall und Echo

Das XVF3800 besitzt DSP-Funktionen einschließlich AEC. AEC benötigt das Referenzsignal der Lautsprecherausgabe. Seeed erklärt diesen Zusammenhang ausdrücklich; XMOS dokumentiert den Referenzpfad. [Seeed-Erklärung](https://www.seeedstudio.com/blog/2025/09/25/how-respeaker-enables-clear-voice-pickup-even-in-noise-a-technical-explainer/), [XMOS-Handbuch](https://www.xmos.com/documentation/XM-014888-PC/pdf/xvf3800_user_guide_v3.2.1.pdf).

**Ableitung für unseren Aufbau:** `NativeLiveAudio` spielt auf dem konfigurierten PipeWire-Sink ab. Bei der Marshall-Box per Bluetooth ist damit keine AEC-Referenz zum ReSpeaker nachgewiesen. Dass das Mikrofon Hardware-AEC unterstützt, genügt hier nicht. Bluetooth-Verzögerung und Raumhall sind zusätzliche Testbedingungen. Es braucht keine weitere Firmware nur für ein softwareseitiges Wake Word.

Der MVP setzt die Erkennung während eigener Wiedergabe aus: Live-Antwort, Suchjingle, Testton, Erinnerungsalarm und abgespielte Aufnahmen. Danach eine messbar angepasste kurze Nachlaufzeit; als erster Testwert eine Sekunde, nicht als universell richtiger Wert. Während eines laufenden Live-Gesprächs ist Wake-Erkennung ohnehin aus. Echtes „Dazwischenrufen“ wird dadurch nicht versprochen. Eine spätere dauerhaft aktive Unterbrechungsfunktion braucht eine separat geprüfte AEC-Kette mit tatsächlichem Ausgabereferenzsignal.

VAD allein löst Lautsprecherecho nicht: abgespielte Sprache ist ebenfalls Sprache. Auch das Aktivierungswort im Fernseher kann erkannt werden. Wake Word ist keine Sprecheridentifikation und kein Ersatz für eine Kontoanmeldung.

## Einbindung in den vorhandenen Code

Geprüft wurden `services/live_audio.py`, `services/live_conversation.py`, `services/app_activity.py` sowie die aufrufenden Stellen in `web_server.py`.

Bereits vorhanden:

- `native_capture_command()` wählt die konfigurierte Quelle statt eines zufälligen Standardgeräts; Pulse-Monitorquellen werden ausgeschlossen. Native Live-Audioaufnahme verwendet 16-kHz-Mono-PCM.
- `StudioApp.control_lock` serialisiert Aufnahme und Live-Reservierung. `AppActivity` leitet Sperren aus echten Dienstzuständen ab; auch pausierte Aufnahmen halten das Mikrofon belegt.
- `LiveConversation.reserve()` bindet Konto, Mandant und Server, erzeugt eine Besitzer-Lease und reserviert das Gespräch. `_start()` prüft CDB-Freigabe und erlaubte Areas erneut.
- Gemerkte Areas sind bereits pro Bindung gespeichert. Eine bewusst leere Auswahl muss leer bleiben; ein Wake-Start darf nicht heimlich irgendeinen Bereich nehmen.
- Der aktuelle Browser-Besitzer muss `pulse()` senden; die lokale Frist beträgt 25 Sekunden. Davon getrennt existiert ein CDB-Session-Heartbeat. Kontoänderung und Maximaldauer beenden die Sitzung.

Notwendige Erweiterungen:

1. Ein `WakeWordService` mit eigener begrenzter Audioqueue, konfigurierbarer Engine und sauberem Stop/Join. Kein Audio in Logdateien; Modell und Audioruntime bleiben getrennt.
2. **Ein zentraler Mikrofonbesitzer.** Für den MVP darf der Wake-Dienst die Quelle nur im Bereitschaftszustand öffnen. Aufnahme, Tests und Live-Start stoppen ihn zuerst und warten auf die Freigabe. Diese Übergabe muss unter derselben Reservierungslogik stattfinden; erst danach startet `NativeLiveAudio`. Bei Fehler geschlossen bleiben statt zwei Leser zu starten. Ein späterer gemeinsamer Capture-Broker ist möglich, aber nicht nötig für den ersten Schritt.
3. `wake_armed` darf `AppActivity.occupied` nicht einfach dauerhaft wahr machen: Sonst sperrt Bereitschaft alle regulären Aktionen. Stattdessen ist Wake-Bereitschaft **verdrängbar**, `wake_starting` dagegen eine atomare Reservierung. Ein Klick und ein Wake-Ereignis zur gleichen Zeit dürfen genau einen Gewinner haben.
4. Ein expliziter Session-Besitzertyp `browser` / `device`. Ein Wake-Start wird vom Backend betreut und läuft nicht nach 25 Sekunden wegen fehlender Browser-Pulse aus. Die bestehende Browser-Sicherheitslogik nicht global entfernen. Ein Geräte-Watchdog, Inaktivitätsende und CDB-Heartbeat bleiben erforderlich; kein heimlicher Endlos-Pulse als Umgehung.
5. Das Touchdisplay muss ein vom Gerät gestartetes Gespräch sicher übernehmen/stoppen können, ohne dass der externe Receiver Steuerrechte oder die interne Besitzer-Lease erhält. Ein reiner Receiver bleibt Anzeige.
6. Vor jedem Start aktuelle Bindung, Anmeldung, Audioquelle/-ausgabe, CDB-Capability und gespeicherte Auswahl prüfen. Logout oder Kontowechsel deaktiviert Bereitschaft; Aktivierung muss im neu gewählten Konto bewusst wieder freigegeben werden.
7. Wiedergabezustand aus allen Ausgabepfaden an den Wake-Dienst liefern. Aktuell deckt `AppActivity` Tests und Live ab, aber eine allgemeine Browser-/Bibliothekswiedergabe nicht vollständig. Nur die Live-Waveform zu prüfen reicht nicht.

## Vorgeschlagener Ablauf und Oberfläche

| Zustand | Mikrofon / Verhalten | Anzeige |
|---|---|---|
| Aus | Wake-Capture geschlossen | „Aktivierungswort aus“ |
| Bereit | Nur lokale Wake-Erkennung, keine Cloud-Audioübertragung | Kleine feste Statusfläche „Bereit für …“; ausgewählte Areas sichtbar |
| Unterbrochen | Aufnahme, Test, Wiedergabe, Bluetooth-Wechsel oder fehlende Anmeldung | Verständlicher Grund, kein rotierender Dauerfehler |
| Erkannt / verbindet | Erkennung sperren, Besitzerwechsel, Konto/Areas erneut prüfen | Kurzer Bestätigungston; feste Verbindungsanzeige und Abbrechen |
| Gespräch | Ausschließlich vorhandener Live-Audiopfad | Bestehende Chatansicht, Stumm- und Ende-Taste |
| Ende / Nachlauf | Audioressourcen schließen; Nachhall abwarten | Danach wieder Bereit, sofern weiterhin freigegeben |

Bedienung in „Gespräch → Aktivierungswort“: Ein/Aus, Wortauswahl, Empfindlichkeit in drei verständlichen Stufen, Testmodus und klare Angabe „Das Wort wird lokal erkannt. Das Gespräch verwendet dein Brain-Konto.“ Keine Zahlenflut im Alltag. Testmodus zeigt Erkennungen an, startet aber noch keine Cloud-Sitzung. Konfiguration und Status stehen an festen Positionen; kein zusätzliches Modal nötig.

Der erste Gesprächsbefehl folgt nach dem Bereitschaftston. So verliert eine einfache Übergabe keinen Satzanfang während des Verbindungsaufbaus. Ein Vorlaufpuffer, der Sprache von vor der Aktivierung nachträglich an die Cloud sendet, gehört ausdrücklich nicht in den MVP.

## Datenschutz und Fehlerverhalten als Produktanforderungen

Im Bereitschaftsmodus nur einen kurzen RAM-Puffer verwenden, fortlaufend überschreiben und weder speichern noch senden. Bereitschaft ist opt-in; Hardware-Mute und App-Mute haben Vorrang, auch nach Neustart. Ein sichtbarer Unterschied zwischen lokalem Warten und Cloud-Gespräch ist erforderlich. Keine Stimme als automatische Identitätsprüfung behandeln.

Nach einem Neustart darf eine zuvor aktive Aufnahme oder Live-Sitzung nicht automatisch wieder in die Cloud verbinden. Persistiert werden nur Freigabe/Modell/Empfindlichkeit und die vorhandene kontogebundene Bereichsauswahl. Fehlende Rechte, leere Auswahl, entfernte Geräte oder Netzfehler ergeben einen erklärten, ruhigen Fehlerzustand mit Rückkehr zur zulässigen Bereitschaft. Fehler dürfen keine neue Aufnahme erzeugen oder die Queue löschen.

## Abnahmeplan vor Freigabe

Zielwerte sind **Produktvorschläge, keine bisherigen Ergebnisse**:

1. Installation in isolierter Testumgebung auf ARM64: Import, richtiges Modell, echte Audioframes, stabile Laufzeit; keine Änderung der Produktionsumgebung während laufender Aufnahme.
2. Mindestens 100 Aktivierungen mit mehreren Personen, deutscher Aussprache, unterschiedlichen Abständen und Lüfter-/Raumgeräuschen. Trefferquote und p50/p95 vom Wortende bis zur lokalen Erkennung sowie bis zum CDB-Hörbereit separat messen. Als erstes Ziel ≥95 % erfolgreiche lokale Aktivierungen unter den definierten Testbedingungen.
3. Mindestens ein Arbeitstag negativer Audiofälle: Gespräche ohne Wort, ähnlich klingende Wörter, TV, Musik, eigene Antworten/Jingle, Alarm. Für den ersten Raumtest Ziel höchstens eine unbeabsichtigte Aktivierung pro acht Stunden. Ein einzelner Tag ist keine statistische Garantie; deshalb über mehrere Tage nachmessen.
4. CPU pro Kern, RSS, Temperatur, Audioaussetzer und Queue-Verlangsamung im Leerlauf sowie während lokaler Transkription messen. Erkennung muss ohne wachsenden Rückstau arbeiten; CPU-Prozentwerte erst danach veröffentlichen.
5. Konflikte gezielt testen: Wake + Record im selben Moment, pausierte Aufnahme, Mikro-/Lautsprechertest, Bibliotheksplayer, Modelltest, Gerätewechsel, Mute, Konto-/Area-Wechsel, abgelaufene Anmeldung, CDB-Abbruch, Browser geschlossen und Backend-Neustart.
6. Nachweis: Im Bereitschaftsmodus fließt kein Mikrofon-Audio zur Cloud; nach Stopp bleiben keine Aufnahmeprozesse übrig. Kein späteres Nachsenden gepufferter Sprache.

**Nächster sinnvoller Schritt:** ein lokal begrenzter Testmodus mit microWakeWord, dann gemessene Freigabe des automatischen Voice-One-Starts. Ein eigenes Markenwort und „während der Antwort unterbrechen“ erst nach erfolgreicher Grundabnahme.
