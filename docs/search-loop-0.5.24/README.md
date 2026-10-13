# Such-Loop 0.5.24

Variante 1 aus der [Klangstudie](../search-sound-study/README.md) ersetzt den
einmaligen 120-ms-Ton. Eine vorgeladene 3-Sekunden-WAV läuft am gewählten
Pi-Lautsprecher, solange bestätigte Brain- oder Web-Suchen aktiv sind.

- Ein Player für alle parallelen Suchen; keine übereinanderliegenden Loops.
- Pause bei Mikrofon- oder Antwortsprache; Fortsetzen nach 600 ms Ruhe.
- Stopp bei letzter fertiger/fehlgeschlagener Suche, Sound aus und Sitzungsende.
- Verwaiste Suchereignisse verfallen nach 65 Sekunden.
- Sound-Schalter bleibt gespeichert; Einschalten während einer Suche funktioniert.
- Wiedergabe in getakteten 20-ms-Blöcken mit begrenztem Puffer.
- Abgeschlossene Audioprozesse werden aus der Verwaltung entfernt.
- Brain-Ereignisse werden für Anzeige und Audio gespiegelt, aber nur einmal gezählt.

## Akustische Prüfung am Pi

Der erste Hardwaretest zeigte Selbstunterbrechungen: Das ReSpeaker hörte die
Marshall-Wiedergabe und die bisherige reine Pegelschwelle wertete sie als Sprache.
Eine vorübergehend getestete PipeWire-Echokompensation löste das bei dieser
Bluetooth-Verbindung nicht ausreichend; das Testmodul wurde wieder entfernt.
Es wurde keine dauerhafte PipeWire-Konfiguration angelegt; die explizit ausgewählten
Ein- und Ausgabegeräte der App bleiben unverändert.

Die endgültige Lösung spielt den Loop 12 dB leiser als die Quelldatei ab
(Spitzenpegel ca. −36 dBFS, Hörprobe nochmals 10 dB lauter als die Quelldatei).
Die Pausensteuerung betrachtet zusätzlich die Energie außerhalb der sechs
bekannten Glockenfrequenzen (±65 Hz): 80-ms-Hann-Fenster, 20-ms-Schritte,
zwei aufeinanderfolgende Blöcke oberhalb der Restpegelschwelle. Die Erkennung
läuft während der Wiedergabe und 800 ms Nachlauf. Es wird **kein Mikrofon-PCM
gefiltert, verworfen oder wegen des Suchtons stummgeschaltet**. Dies ist eine
klangspezifische Unterscheidung, keine allgemeine Spracherkennung oder AEC.

`hardware.json`: echter ReSpeaker-Eingang und Marshall-Ausgang am Pi, vorhandene
Lautstärke 82 % unverändert. 7,2 Sekunden / 360 Blöcke ohne Selbstunterbrechung,
ein Player. Mikrofon- und Antwortunterbrechungen wurden mit definierten PCM-Pegeln
in die jeweiligen Detektoren eingespeist: Pause und Wiederaufnahme bestanden.
Parallele Suchen, Schalter, Suchende und vollständiges Freigeben der Audioprozesse
ebenfalls bestanden. Kein Raumton gespeichert oder in die Cloud gesendet.
Dies ersetzt keinen subjektiven Hörtest bzw. Sprechtest durch eine Person im Raum.

`performance.json`: 10.000 Analyseblöcke entsprechen 200 Sekunden Eingangsaudio.
Auf dem Pi benötigten sie 0,8754 CPU-Sekunden, ca. 0,44 % eines Kerns. Das ist
nur die Analyse, kein Gesamtbenchmark der App. Synthetische deutsche Sprache
blieb trotz aktivem Suchklang-Detektor erkennbar (792 von 903 Sprachdateiblöcken).

## Automatische Prüfung

152 Python-Tests auf dem Pi und 62 JavaScript-Tests bestanden. Neue Prüfungen
decken Wiederholung über die Loop-Grenze, parallele und wiederholte Ereignisse,
beide Sprachrichtungen, Abschalten, Wiederaufnahme, Ablauf verwaister Suchen,
optionalen Player-Ausfall, PCM-Format, stille Loop-Grenzen sowie Klang-plus-Sprache
ab. Bestehende Sperren und Aufnahmeabläufe bleiben Bestandteil der Gesamtsuite.

## Quellen zur Einordnung

- [PipeWire Echo Cancel](https://docs.pipewire.org/page_module_echo_cancel.html):
  beschreibt den Referenzsignal- und Mikrofonpfad der getesteten allgemeinen AEC.
- [WebRTC-VAD Python-Schnittstelle](https://github.com/wiseman/py-webrtcvad):
  alternative Spracherkennung recherchiert; keine neue VAD-Abhängigkeit installiert.

Die produktive Umsetzung nutzt das bereits vorhandene NumPy und eine eigene,
gezielt auf diese Audiodatei abgestimmte Analyse.

## CDB-Integration

`cdb-integration.json`: synthetische deutsche Anfrage auf dem Pi, isolierte
Testinstanz, CDB staging_playground. Echte Brain-Suche und zwei bestätigte
Websuchaufrufe wurden erkannt. 193 Loop-Blöcke wurden ausgegeben; die Suche
endete mit nur den beiden normalen Audioprozessen. Sound-Schalter, Mikrofonstumm,
Aufnahme-/Einstellungssperren während des Gesprächs und Entsperren nach Ende
bestanden. Raum-Mikrofon und Lautsprecher wurden für diesen Cloudtest durch
synthetischen Eingang und einen stillen Prüfausgang ersetzt. Der gesonderte
Hardwaretest oben prüft die tatsächlichen Geräte.

Beim ersten Durchlauf war der Suchton in der vorhandenen Testinstanz ausgeschaltet;
die Prüfung bemerkte korrekt die fehlende Wiedergabe. Der abschließende Lauf
aktivierte die Einstellung ausdrücklich. Produktive Einstellungen blieben dabei
unverändert.

## Produktiv aufgespielt

Version **0.5.24**, Laufzeit-Commit `787a930`, auf dem Pi aktiviert. Backend und
Touchdisplay-Kiosk laufen. Alle fünf ausgelieferten Dateien wurden per SHA256
gegen den Git-Commit geprüft. 22 vorhandene Aufnahmen, Gerätekonfiguration,
Modellanbieter, Standardbereich und Anmeldung sind erhalten geblieben.
`deployment.json` enthält den überprüften Stand. Vorheriger Stand gesichert unter
`/home/chris/backups/recorder-before-0.5.24`. Die isolierte Testinstanz wurde beendet
und ihre temporäre Anmeldedatei entfernt.
