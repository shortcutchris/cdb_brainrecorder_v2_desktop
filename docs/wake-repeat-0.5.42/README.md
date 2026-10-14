# Fünf Gespräche hintereinander · 0.5.42

14. Oktober 2026. Raspberry Pi 5, gleiche laufende App-Instanz über alle fünf Durchläufe.

## Befunde vor der Korrektur

- Die Session bestätigte `session.instructions.appended`, blieb jedoch über 65 Sekunden ohne Begrüßung. [Nachweis](before-greeting.json). Eine weitere erste Probe war ebenfalls am Begrüßungs-Timeout gescheitert; erst die instrumentierte Wiederholung belegte das bestätigte, aber stumme Verhalten.
- „Gespräch beenden“ wurde als „Gespr�che beenden“ transkribiert. Der Agent kündigte das Ende an, die lokale enge Wortprüfung schloss aber nicht. [Nachweis](before-end.json).

## Korrektur

Bestätigte Vorbereitungsanweisung plus einmaliger expliziter Sprechauftrag mit `session.commentary.append`, wie im vorhandenen Voice-One-Client für vorbereitete Antworten. Eigene Ereignis-ID je Schritt; nur passende Bestätigung erlaubt den Folgeschritt. Kein Retry bei unklarem ACK, keine Wiederholung beim Reconnect. „Hallo“ bleibt erstes Wort. Das Modell kann die Satzzeichen natürlich gestalten.

Die lokale Ende-Prüfung erkennt zusätzlich den beobachteten Plural und ausschließlich innerhalb des Wortes Gespräch/Gespräche `ae` bzw. ein einzelnes Ersatzzeichen. Keine allgemeine unscharfe Erkennung, keine Änderung des gespeicherten Transkripts. Fragen, Verneinungen, Zitate und Assistentenstimmen bleiben ausgeschlossen.

## Methode und Ergebnis

Echtes lokales Vosk-Modell, tatsächlicher Detector-Unterprozess, native WebRTC-Verbindung und reale CDB-Staging-Sitzungen mit `staging_playground`. Espeak liefert synthetisches „Hey Brain“ an den Detector und synthetisches „Gespräch beenden“ an den Audioeingang. Keine direkte Auslösung von Start/Ende in der Testserie, kein Neustart der App zwischen Gesprächen. Wiederanlauf mit frischem Detector-Prozess und Freigabe der Bedienung geprüft.

Die Tests laufen in isoliertem Datenverzeichnis auf dem Pi. Mikrofoninput und Lautsprecherausgabe sind synthetisch bzw. stumm abgenommen. Dies prüft den vollständigen Softwareablauf, nicht Reichweite, Raumecho oder individuelle Aussprache am realen Mikrofon.

| Runde | Hey Brain erkannt | Erstes Begrüßungswort | Ende per Sprache | Wieder bereit nach Schließen |
|---|---:|---:|---:|---:|
| 1 | 1.81 s | 10.73 s | 4.62 s | 0.72 s |
| 2 | 1.75 s | 5.66 s | 4.12 s | 0.82 s |
| 3 | 1.70 s | 9.93 s | 4.62 s | 0.72 s |
| 4 | 1.81 s | 10.38 s | 5.03 s | 0.72 s |
| 5 | 1.75 s | 11.02 s | 4.62 s | 0.72 s |

Erkennung und erstes Begrüßungswort zählen ab Beginn des eingespeisten Aktivierungsworts. Ende zählt ab Beginn des eingespeisten Ende-Befehls und enthält dessen Sprechdauer. Die letzte Spalte zählt erst nach vollständigem Schließen. Keine allgemeine Latenzgarantie: Cloud- und Netzwerkzeiten variieren.

**5/5 bestanden**: jeweils eine kurze Hallo-Begrüßung, `voice_command`, keine zurückgebliebenen Live-Audioprozesse, Recorder und Einstellungen freigegeben, lokaler Detector wieder `listening`. [Vollständige Messung](after-five-cycles.json).

Automatische Regression: passende und veraltete ACKs, Reihenfolge des Sprechauftrags, kein zweiter Start bei Reconnect, Abbruch, Mute-Erhaltung sowie negative und beschädigte/plurale Ende-Äußerungen.

**223 Python-Tests und 99 JavaScript-Tests bestanden.**

## Nachprüfung am realen Gerät: Erkennung reagiert nicht

Am 14. Oktober 2026 meldete Chris nach dem Deployment, dass „Hey Brain“ am
realen Mikrofon nicht mehr reagierte. Gleichzeitig zeigte die Oberfläche
„Einrichtung abschließen“. Die vorherigen fünf synthetischen Durchläufe ersetzen
keinen akustischen Praxistest und schließen diesen Fehler nicht aus.

### Beobachteter Zustand

- Studio 0.5.42 aktiv, keine Aufnahme und kein laufendes Live-Gespräch.
- Aktivierungswort eingeschaltet; Status `listening`, aber noch null Erkennungen.
  Detector und dessen `parec`-Unterprozess liefen.
- ReSpeaker XVF3800 als USB-Audiogerät vorhanden, konfigurierte Quelle aktiv.
  Weder PipeWire noch die Hardware-Mute-Abfrage meldeten Stummschaltung.
- Eine dreisekündige Pegelmessung bestätigte Eingangssignal: maximaler RMS 0,03486,
  Peak 0,07916, normiert auf 1. Keine Audiodatei gespeichert oder zur Cloud übertragen.
- `setup_complete` war `false`, obwohl alle fünf bestehenden Einrichtungsprüfungen
  bestanden waren. Das blockierte den Recorder; die Live-Freigabe war bereits erlaubt.

### Durchgeführte Maßnahmen und Ergebnis

1. Den aktuellen Einrichtungsstatus über `GET /api/setup` geprüft. Erst nach
   `ready: true` den normalen Abschluss über `POST /api/setup/complete` gespeichert.
   Danach `setup_complete: true` und Recorder freigegeben. Keine Prüfungen umgangen.
2. Nur den lokalen Detector mit `POST /api/wake`, Body
   `{"action":"test-stop"}`, neu gestartet. Dieser bestehende Endpunkt beendet den
   Detector-Unterprozess; bei weiter eingeschaltetem Aktivierungswort startet die
   normale Hintergrundsteuerung ihn anschließend neu. Die gespeicherte Freigabe
   und Bereichsauswahl bleiben erhalten. Aufruf nur im zuvor geprüften Leerlauf;
   mutierende Anfragen benötigen wie üblich den aktuellen CSRF-Header.
3. Erneut `listening` bestätigt. Chris sprach anschließend direkt am Pi „Hey Brain“
   und bestätigte: „Ja, startet wieder“. Die App meldete eine Erkennung und wechselte
   von `connecting` zu `speaking`, ohne Live-Fehlermeldung.

**Kein Neustart des Pi, kein USB-Abziehen und kein Firmwarewechsel nötig.**
Der fehlende Einrichtungsabschluss war ein separater gespeicherter Zustand und
nicht die Ursache der ausgebliebenen Aktivierung.

Die genaue Ursache des nicht reagierenden Detectors ist noch nicht belegt.
Der erfolgreiche gezielte Neustart ist eine bestätigte Wiederherstellung,
kein Nachweis einer dauerhaften Fehlerbehebung. Es wurde hierfür kein neuer
Laufzeitcode geändert; Version 0.5.42 bleibt bestehen.

### Bei erneutem Auftreten

Zuerst Aufnahme/Gespräch und sonstige Audio-Belegung prüfen, dann Wake-Status,
Erkennungszähler, USB-Gerät, gewählte Quelle und beide Mute-Zustände festhalten.
`listening` allein beweist nicht, dass eine reale Äußerung erkannt wird.
Erst im Leerlauf den Detector gezielt neu starten und den akustischen Test am
Gerät wiederholen. Wenn das nicht hilft, Signalweg und Decoder gezielt untersuchen,
bevor ein kompletter Hardware-Neustart versucht wird. Einrichtung nur abschließen,
wenn die tatsächlichen Einrichtungsprüfungen weiterhin erfolgreich sind.
