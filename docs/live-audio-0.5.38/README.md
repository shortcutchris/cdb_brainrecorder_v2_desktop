# Live-Audio · 0.5.38

## Ursachen und Verhalten

Der Alarm verwendete bisher `wake_reason()`. Diese Sperre schützt den lokalen
Aktivierungswort-Detektor vor Aufnahme, Gespräch und Wiedergabe. Für Alarme war
sie zu weit gefasst: Ein Gespräch konnte den Ton beliebig lange verzögern.
Die neue abgeleitete `alarm_allowed`-Regel erlaubt das Mischen mit Live-Audio
und Medienwiedergabe. Aufnahme, Mikrofon-/Lautsprechertest, Bluetooth-Einrichtung,
Modelltest und Installation bleiben geschützt. Der Alarm besitzt weiterhin
einen eigenen Abspielprozess am ausgewählten Pi-Ausgang. Gesprächsende und
Alarmbestätigung beenden nur ihren jeweiligen Audiopfad.

Der konkret gemeldete Befehl „Okay, beende das Gespräch“ passte nicht zur früheren
Wortreihenfolge „Gespräch beenden“. Der Parser akzeptiert jetzt eine begrenzte
Gruppe natürlicher, vollständiger Aufforderungen, einschließlich „Beende bitte
das Gespräch“, „Unterhaltung beenden“, „Ende“ und „Das war’s“. Dies ist kein
zusätzlicher KI-Aufruf. Die bestehende Ruhefrist von 1,5 Sekunden, Kontobindung,
Mute-Sperre und Ablehnung von Fragen, Zitaten und Verneinungen bleiben erhalten.
Ein als Nutzersprache zurückkommendes „Ich beende das Gespräch jetzt“ passt
bewusst nicht. Voraussetzung bleibt eine korrekt erkannte Nutzertranskription;
die Prüfung belegt keine allgemeine Erkennungsquote unter Raumhall/Lautsprecherecho.

Ein 360-ms-Doppelton wird lokal erzeugt und erst beim tatsächlichen
WebRTC-Zustand `connected` abgespielt, nicht beim Startknopf oder SDP-Austausch.
Einmal pro Sitzung, auch bei wiederholten Verbindungsereignissen. Der optionale
Ton hat einen separat aufgeräumten Prozess; Fehler beenden nicht das Gespräch.
Der Suchton-Schalter verändert diesen Bereitschaftston nicht.

## Prüfung auf dem Raspberry Pi

210 Python-Tests und 98 JavaScript-Tests bestanden. Gezielte Fälle umfassen:

- Beide Wortreihenfolgen und natürliche Varianten; Fragen, Verneinungen,
  Assistenten-Echos, unvollständige Befehle, stummes Mikro und Kontowechsel.
- Alarm während Live, kein erneutes Abspielen desselben Alarms,
  Alarmbestätigung ohne Gesprächsende und Zurückstellung bei Aufnahme.
- Bereitschaftston erst nach Verbindung, nur einmal, Fehlerisolierung und
  Prozessbereinigung bei Abbruch.
- Alarmanzeige und beide Alarmaktionen bleiben während Live verfügbar;
  „Ton nach der Aufnahme“ erscheint nur für noch ausstehende Alarme.

Die Integration verwendet echtes CDB-Staging/WebRTC mit `staging_playground`,
synthetischer deutscher Sprache und einem isolierten PipeWire-Ausgang.
Es werden keine Raumaufnahmen oder Produktionstimer verwendet. Die erfolgreiche
Wiedergabe am virtuellen Ausgang belegt den Audiopfad, nicht die subjektive
Lautstärke im Raum. Reproduktionsskript: [acceptance_pi.py](acceptance_pi.py).
Es benötigt die bestehende Pi-Testkopie und Staging-Anmeldung; Sitzungsdateien
bleiben nur im privaten Testverzeichnis auf dem Pi und gehören nicht ins Git.

Erster Durchlauf: [acceptance-first.json](acceptance-first.json). Zwei gleichzeitige
Audioströme am selben Ausgang, eingehende Live-Frames steigen während des Alarms
von 395 auf 549. Alarmbestätigung lässt Live weiterlaufen. Die Frage nach dem
Beenden schließt nicht; „Okay, beende das Gespräch“ schließt mit `voice_command`.
Alle nativen Audio-Kindprozesse sind danach beendet; Aufnahme/Einstellungen frei.

Oberflächenprüfung bei 1280 × 720 Pixeln:
[Alarm während Live](../../output/playwright/live-audio-0.5.38/02-alarm-during-live.png).
Fester Alarmbereich oben rechts mit sichtbaren Aktionen; Gespräch und
Bedienleiste behalten ihre Position. Das Bild zeigt die isolierte Testinstanz.

Zweiter Durchlauf: [acceptance-alarm-end.json](acceptance-alarm-end.json).
Zusätzlich wird „Okay, beende das Gespräch“ bei einem erneut laufenden Alarm
gesprochen. Live endet und gibt alle eigenen Audioprozesse frei, während der
Alarm weiterläuft. Erst dessen separate Bestätigung stoppt den Ton. Danach
sind Aufnahme und Einstellungen wieder freigegeben.
