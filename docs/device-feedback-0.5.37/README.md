# Gerätefeedback · 0.5.37

## Aktivierungswort

Die vorherige Erkennung verlangte, dass der gesamte vom Decoder abgeschlossene
Audioabschnitt ausschließlich „hey brain“ enthält. Vorangehende Sprache und
unmittelbar wiederholtes „Hey Brain Hey Brain“ konnten deshalb verworfen werden.
Jetzt wird das benachbarte Wortpaar mit unveränderten Konfidenz- und Dauerschwellen
im abgeschlossenen Wortstrom gesucht. Ähnlich klingende Alternativen bleiben im
Decoder. Das ist eine konkrete Verbesserung; ohne Aufnahme der tatsächlichen
Fehlversuche ist die Ursache beim Benutzer nicht abschließend bewiesen.

`recognized_for` bleibt acht Sekunden sichtbar, auch wenn die Audioübergabe den
Detector bereits anhält. Ein kleiner Speicher-Endpunkt liefert die Bestätigung
alle 300 ms, ohne die langsame vollständige Statusabfrage oder Gerätesuche.
Polling pausiert in unsichtbaren Tabs, bei Aufnahme und nach Gesprächsverbindung.
Die Meldung hat eine feste Position und verschiebt kein Inhaltselement. Sie
unterscheidet Verbindungsaufbau und Sprechbereitschaft. Reduzierte Bewegung wird
respektiert. Kein eigener Bestätigungston stört die Mikrofonübergabe.

Pi-Wake-Korpus: 8 positive Fälle (einschließlich Kontext und Wiederholung),
20 Gegenbeispiele und 60 Sekunden Stille bestanden. 85,39 Sekunden Material,
2,295 CPU-Sekunden (~2,69 % eines Kerns). [Messung](wake-test.json).
Synthetische Proben belegen keine Erkennungsquote für die reale Raumakustik.

## Timer

- Countdown und Titel oben rechts in allen Ansichten, zusätzlich im Timersymbol.
  Der früheste Termin steht vorne; weitere aktive Einträge sind mit +N erkennbar.
- Fälliger Eintrag hat Vorrang und bietet „Alarm stoppen“ sowie „+5 Min.“.
- Alarmdatei: 15 Zyklen aus drei Sekunden Ton und einer Sekunde Pause = 60 Sekunden.
  Die Vorschau bleibt bei drei Sekunden. „Lautlos“ bleibt lautlos.
- Ende oder Abbruch beendet den Pi-Abspielprozess. Bestätigung/Snooze über die
  Gerätewerkzeuge werden ebenfalls vom Hintergrundlauf erkannt und stoppen ihn.
- Aufnahme, Gespräch und Wiedergabe bleiben geschützt; ausstehende Alarme werden
  erst bei freiem Audio abgespielt. Ein quittierter Alarm wird nicht erneut gespielt.
- Nach automatischem Tonende bleibt der fällige Eintrag sichtbar. Der Ton wird
  nicht endlos wiederholt und nicht nach einem Neustart erneut gestartet.

Echter Pi-Abspieltest mit `paplay` auf einem isolierten virtuellen Ausgang:
Ton läuft nach sechs Sekunden weiter; Oberflächenaktion und Geräteauftrag
`acknowledge_alarm` stoppen ihn; automatisches Ende nach **60,66 Sekunden**
einschließlich Hintergrund-Abfrageintervall. [Protokoll](alarm-test.json).
Kein Raumton aufgezeichnet; kein Testalarm über den echten Marshall ausgegeben.

Oberflächenbilder sind aus der isolierten Pi-Testinstanz bei 1280 × 720 Pixeln:
[Countdown](../../output/playwright/device-feedback-0.5.37/01-countdown.png),
[Alarm](../../output/playwright/device-feedback-0.5.37/02-alarm.png).

Abschlussprüfung: 202 Python-Tests und 96 JavaScript-Tests bestanden. Ein eigener
HTTP-Test hält die Controller-Sperre fest und prüft, dass die Erkennungsbestätigung
trotzdem innerhalb einer Sekunde abrufbar bleibt.
