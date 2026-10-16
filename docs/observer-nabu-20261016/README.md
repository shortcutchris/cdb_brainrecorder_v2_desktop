# Nabu-Zuordnung im Messdienst und WAV-Raumtest

16. Oktober 2026. Begrenzter Nutzerauftrag: Zuordnung korrigieren, selbst mit
WAV-Dateien testen, dokumentieren und pushen. Das übergeordnete Stabilitätsziel
bleibt pausiert; kein unbegrenzter Stressbetrieb und keine automatische Reparatur.

## Korrektur und Installation

Die App 0.5.59 meldete korrekt `okay-nabu`. Die unabhängige Positivliste in
`scripts/observe_pi_stability.py` enthielt Nabu nicht und speicherte `unknown`.
Nabu ist jetzt ergänzt. Ein Regressionstest gleicht alle App-Rufwörter mit dem
separat installierbaren Beobachter ab; unbekannte Werte bleiben datensparsam
`unknown`. Weitere Tests prüfen Nabu-Ereignis/echte gemessene Ruhezeit und
verhindern, dass historische unknown-Werte oder ein Neustart verdeckt werden.

- 44 lokale Tests: Überwachung, Auswertung und Nabu-Adapter.
- 37 Überwachungs-/Auswertungstests auf dem Pi bestanden.
- Nur Messdienst am **16.10., 12:55:35 Europe/Berlin** neu gestartet,
  PID 1882621 → 1894368. App-PID 1882091 und Browsergeneration unverändert.
- Installierter SHA256 entspricht dem korrigierten Quelltext; neuer Status
  enthält `okay-nabu`. [Installationsnachweis](installation.json).
- Die erste Prüfung nach zwei Sekunden las noch den alten Status und schlug
  fehl. Eine spätere frische Probe bestätigte den Start; kein zweiter Neustart.

Originalplan **16.10. 12:31:15 bis 17.10. 12:31:15 Europe/Berlin** bleibt
bytegleich. Frühere technische Dateien und alter Beobachter liegen privat auf
dem Pi unter `before-nabu-observer-fix-20261016`. Rohdaten wurden nicht umbenannt,
umgeschrieben oder rückwirkend als Nabu klassifiziert. Der laufende Datensatz
enthält den unknown-Vorlauf und den angekündigten Beobachter-Neustart. Er bleibt
für Ressourcen-/Teilauswertung nutzbar, ist aber kein ununterbrochener,
fehlerfrei zugeordneter 24h-Nabu-Nachweis. Ruhezeit beginnt nach Unterbrechungen
neu. [Zwischenauswertung](partial-summary.json): `pending`, Review-Punkte
bleiben sichtbar. Ein vollständig sauberer 24h-Lauf ist weiterhin offen.

## WAV-Inferenz direkt auf dem Pi

Mit dem tatsächlich installierten Adapter und den unveränderten offiziellen
Referenzen (Upstream `333da550c54b95192af472cfe37d98dab2f2086e`):

- 3/3 Nabu-Dateien erkannt, 0/9 Fehlstarts bei anderen Rufwörtern.
- 100/100 erneuerte Erkennungszyklen erfolgreich.
- Zehn Minuten beschleunigte digitale Stille ohne Treffer; folgender Ruf erkannt.

[Dateitest](wav-regression-pi.json) enthält Dateihashes, Runtime-Versionen und
CPU-Messung. Kein echtes zehnminütiges Warten und kein akustischer Nachweis.

## Echter Lautsprecher → Raum → ReSpeaker-Test

Der Nutzer bestätigte, dass der Mac Studio in Hörweite steht. Vier begrenzte
WAV-Wiedergaben liefen am **16.10. ca. 12:56:30–12:57:09 Europe/Berlin**:
drei unterschiedliche Nabu-Referenzen, anschließend ein Alexa-Gegenbeispiel.

`scripts/play_wake_wav_macos.swift` wählt explizit `BuiltInSpeakerDevice` über
AVAudioPlayer.currentDevice. Die sonst eingestellten externen Kopfhörer bleiben
Systemstandard. Wiedergabe mit originaler Dateirate, Player-Lautstärke 0,65;
kein beschleunigtes Roh-PCM. Alle vier Player-Prozesse endeten erfolgreich.

`scripts/check_wake_acoustic.py --phrase okay-nabu --external-playback`
reserviert auf dem Pi die bestehende atomare Wartungssperre, öffnet die exakt
konfigurierte Mikrofonquelle mit 16 kHz/16 Bit/Mono und verwendet den installierten
Nabu-Adapter. Nach je drei Sekunden Ruhe meldet es eine JSON-Wiedergabeaufforderung.
Der steuernde Rechner spielt darauf die identische WAV per SSH auf dem Studio.
Externe Wiedergabe muss getrennt quittiert werden: das Pi-Tool behauptet keinen
lokalen Player-Erfolg (`playback_exit: null`). Es speichert weder Raum-Audio
noch erkannte Gesprächsinhalte. Maximal vier Dateien bis je acht Sekunden;
der Test war zusätzlich durch einen 90-Sekunden-Prozess-Timeout begrenzt.

**Ergebnis: 0/3 positive Nabu-Dateien erkannt, 0/1 negativer Fehlstart.**
[Gemeinsamer Player-/Mikrofonbericht](acoustic-studio-pi.json) enthält Zeitpunkte,
Hashes, Pegel und Entscheidungen. Während der positiven Dateien wurden
Spitzenpegel von −9,8 / −14,3 / −25,2 dBFS gemessen. Pegel beweisen nicht, dass
die gewünschte Sprache am Mikrofon hinreichend verständlich ankam. Der genaue
Einfluss von Lautsprecher, Entfernung, Raum, ReSpeaker-Verarbeitung und
Modellschwelle ist damit noch nicht isoliert. Keine Erfolgsbehauptung aus dem
bestandenen digitalen Dateitest; Schwellen und Firmware wurden nicht geändert.

Die Wartung wurde im finally-Pfad freigegeben; danach App wieder `listening`,
Live `ended`, kein Testplayer oder zusätzlicher Capture-Prozess verblieben.
Es wurde absichtlich kein Cloud-Gespräch gestartet. Dieser isolierte Raumtest
prüft nicht Begrüßung, Sprach-Endebefehl oder Wake nach acht Stunden. Seine
Wartungsphase unterbricht den durchgehenden Bereitschaftsnachweis.

Für eine Wiederholung: Swift-Helfer auf dem Studio kompilieren, dort zunächst
ohne Argument den Ausgang prüfen, dann mit WAV-Pfad spielen. Pi-Test über den
freigegebenen SSH-Proxy starten und dessen `play_clip`-Signale mit den passenden
Dateien beantworten. Beide Seiten protokollieren; nie aus allein erfolgreicher
Wiedergabe eine Erkennung ableiten. Die Dateien bleiben im privaten Testbereich.

## App, Kunden-Image und Automation

Keine App-Version, Modellinstallation, Konfiguration, Firmware oder SD-Karte
geändert. Die Hilfsskripte gehören nicht zum signierten App-/Factory-Payload;
kein App-Release oder Image-Neubau erforderlich. Nur der eigenständige Messdienst
wurde ausgetauscht. Die Beobachtungsautomation kennt jetzt die Korrektur,
Unterbrechung und den fehlgeschlagenen Raumtest. Sie bleibt rein lesend und
darf diese bekannten Ergebnisse nicht wiederholt als neue Störung melden.
