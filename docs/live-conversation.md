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

## Status, Waveform und Suchton ab 0.5.23

Über dem Verlauf bleibt eine feste Statusfläche. Sie unterscheidet Zuhören, Vorbereitung der Antwort, hörbare Antwortdaten, Brain-Suche, Websuche, Stumm und Verbindungsunterbrechung. Die Chatfläche und Fußleiste behalten ihre Position beim Zustandswechsel.

Die 16 Balken bilden die Lautstärke aufeinanderfolgender echter PCM-Blöcke ab, kein zufälliges Equalizer-Muster. Bei Antwortaudio zeigen sie den Ausgang, sonst den Mikrofoneingang nach der Stummschaltung. Veraltete Messwerte werden nach 300 ms auf null gesetzt. Bluetooth- und Wiedergabepuffer können den tatsächlich hörbaren Ton etwas gegenüber dieser Messung verzögern. Es werden keine Rohdaten für die Anzeige gespeichert oder an den Browser übertragen.

**Suchton an/aus** schaltet einen leisen, wiederholten Glockenklang am
gewählten Pi-Lautsprecher. Ab **0.5.25** beendet eine kurze bestätigte Brain- oder
Websuche die bereits gestartete Phrase nicht abrupt: Sie spielt mindestens
1,6 Sekunden und blendet anschließend in 180 ms aus. Neue Suchaufrufe innerhalb
von 450 ms verwenden denselben Player. Parallel laufende Suchen werden nicht
übereinander abgespielt.

Beginnt Voice One zu sprechen, wird der Suchklang zusätzlich auf 20 % seiner
Lautstärke abgesenkt und die kurze Phrase beendet. Danach bleibt er während der
Antwort stumm; bei weiterlaufender Suche kann er nach der Antwort fortsetzen.
Eigene Sprache hat Vorrang und unterbricht auch eine noch nicht fertige Phrase
mit kurzer Ausblendung. Ohne Antwortaudio erkennt die vorhandene Pegelanalyse
die Unterbrechung; während Antwortaudio werden bestätigte Nutzer-Transkriptereignisse
verwendet, damit das Lautsprecherecho nicht erneut den Loop abbricht. Diese
Unterscheidung hängt dann von der Erkennungslatenz des Anbieters ab.

Abschalten, Gesprächsende und Verbindungsabbruch beenden den Klang auch vor Ende
der Mindestphrase. Der Schalter bleibt auf dem Pi gespeichert und kann während
des Gesprächs nur vom steuernden Browser verändert werden. Bluetooth kann beim
hörbaren Stoppen eine zusätzliche Verzögerung verursachen. Mikrofon und Hauptantwort
werden durch den Suchklang nicht stummgeschaltet. Der Loop zeigt Aktivität an,
keinen prozentualen Fortschritt.

Die WAV-Datei wird einmal vorgeladen; es gibt keine laufende Klangerzeugung und
keinen Cloud-Abruf. Nur kleine 20-ms-Blöcke werden weitergereicht, damit keine
mehrsekündige Tonschleife nachläuft.

Damit der Lautsprecherklang nicht selbst die Sprachpause auslöst, berücksichtigt
die Pausensteuerung die bekannten Frequenzen des Loops. Das verändert weder die
übertragenen Mikrofondaten noch die echte Pegelanzeige. Es ist eine Erkennung
dieses speziellen Suchklangs, keine allgemeine Echo-Unterdrückung. Die Raumlautstärke
bleibt unverändert; der Suchklang selbst wird leiser als die Hörprobe abgespielt.

Brain-Suchen stammen aus den authentifizierten SSE-`search`-Ereignissen. Websuchen erkennt der Pi aus den tatsächlichen `response.web_search_call.*`-/`web_search_call`-Ereignissen des **nur gelesenen** WebRTC-Datenkanals. Reines Nachdenken oder Delegation lösen keine Suchanzeige aus. Suchargumente, URLs, Werkzeugergebnisse und Providertexte werden nicht für dieses Feedback veröffentlicht. Wiederholte Ereignisse lösen keine mehrfachen Töne aus; alte Sitzungen und unvollständige Vorgänge bleiben zeitlich und mengenmäßig begrenzt.

Die Anzeige fragt ausschließlich während einer sichtbaren aktiven Unterhaltung zehnmal pro Sekunde eine kleine lokale Statusantwort ab. Die vollständige App und der Verlauf behalten ihren bisherigen Aktualisierungstakt. Animationen ändern nur Größe/Deckkraft, respektieren reduzierte Bewegung und benötigen keine zusätzliche Audioberechtigung.

## Corporate-Digital-Brain-Theme

Unter **Einstellungen → Design → Seite 2** steht das Standardtheme **Corporate Digital Brain**. Farben nach `git_reps_v4/cdb_design_system/tokens/colors.css`: Navy `#000e22`/`#04162b`, Weiß, Orange `#ffaa3a` und Slate-Neutrals. Bestehende Touch-Typografie und Abmessungen bleiben erhalten. Das Theme kann wie die anderen Standardthemes dupliziert werden. Die Auswahl wird pro Browser/Kiosk gespeichert; eine Auswahl am entfernten Rechner ändert daher nicht automatisch den Touchdisplay-Browser.

[Abnahme, Messwerte und Screenshots 0.5.23](live-feedback-0.5.23/README.md).

## Gesprächsdarstellung ab 0.5.25

Eigene Beiträge stehen in kleinen, rechtsbündigen Blasen. Antworten von Voice One
stehen links als offener Text ohne Kartenrahmen. Neue Transkriptfragmente ergänzen
den vorhandenen Beitrag; nur der neue Text wird kurz eingeblendet. Es gibt keine
künstliche Schreibsimulation. Reduzierte Bewegung wird berücksichtigt.

Header, Status/Waveform, Verlaufsschaltflächen und die untere Bedienleiste bleiben
an festen Positionen. Die Seitenaufteilung misst den tatsächlich gerenderten Text
mit aktueller Schrift und Fenstergröße. Lange Antworten bleiben vollständig über
die nummerierten Seiten erreichbar, ohne sichtbare Scrollleisten. Wer eine ältere
Seite auswählt, bleibt dort auch bei neuen Antworten. **Zum Live-Gespräch** schaltet
wieder auf die jeweils neueste Seite. Nach Gesprächsende werden die anderen
Ansichten wieder freigegeben.

[Prüfungen und Screenshots 0.5.25](live-conversation-0.5.25/README.md).

## Suchanimation ab 0.5.26

Unten rechts im Gespräch ist ein fester Platz für die Suchaktivität reserviert.
Vier kleine bewegte Balken mit **Suchton läuft** erscheinen erst, wenn Python
Audioblöcke an den Suchton-Player weitergibt. Nach Suchende bleibt **Suchton klingt
aus** sichtbar, solange die kurze Phrase noch läuft. Das Symbol ist ein
Aktivitätsindikator, keine zweite Waveform oder Fortschrittsanzeige.

Bei laufender Suche ohne Ton erscheint ein kleiner Suchkreis mit **Suche · Ton
pausiert** bzw. **Suche · Ton aus**. Wenn weder gesucht noch ein Suchton ausgegeben
wird, bleibt der reservierte Platz unsichtbar. Header, Textfläche, Seitennavigation
und Bedienleiste verschieben sich dadurch nicht. Reduzierte Bewegung stellt die
Symbole statisch dar. Die Animation nutzt nur CSS-Transformationen und den bereits
vorhandenen Statusabruf; keine zusätzlichen Browser-Timer oder Cloud-Anfragen.

Die Rückmeldung bestätigt die Ausgabe an den Pi-Audioplayer, nicht die akustische
Hörbarkeit im Raum. Bluetooth kann den tatsächlichen Klang geringfügig verzögern.
Bei Gesprächsende, veralteter Audioaktivität oder Verbindungsfehler verschwindet
die Tonanimation. [Prüfungen und Vorschauen](live-search-indicator-0.5.26/README.md).
