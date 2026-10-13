# Suchklang: wiederholbarer Loop statt Einzelsignal

Stand: 13. Oktober 2026. **Hörproben und Integrationsentwurf**, noch keine Änderung
am produktiven Suchton von Version 0.5.23.

## Recherche und Auswahl

Kurze abstrakte UI-Klänge werden als Earcons bezeichnet. Sie können Aktionen und
Zustände signalisieren; ihre Bedeutung ist jedoch nicht von selbst eindeutig.
NN/g empfiehlt, ihren Kontext und ergänzende visuelle bzw. sprachliche Hinweise
zu berücksichtigen. Deshalb bleibt im Recorder die feste Anzeige „Websuche läuft“
bzw. „Brain wird durchsucht“ bestehen.

Quelle: [NN/g: Audio Signifiers for Voice Interaction](https://www.nngroup.com/articles/audio-signifiers-voice-interaction/).

Für die gewünschte wiederholte „Jing“-Figur kommen verschiedene Klangrichtungen
infrage. Dies ist unsere gestalterische Einordnung, keine Rangliste aus der Quelle:

| Richtung | Charakter | Einschätzung für unseren Recorder |
| --- | --- | --- |
| Weiche Glocken / Mallet-Earcon | Helle, kurze Noten mit sanftem Anschlag | Trifft das gewünschte „Jing-jing“; erste Empfehlung |
| Warme Plucks | Etwas tiefer, runder, weniger metallisch | Zurückhaltende Alternative für längere Suchen |
| Digitaler Puls | Wiederkehrender kurzer Synthesizerton | Klar, kann bei häufiger Wiederholung wie ein Warnsignal wirken |
| Ambient-Fläche | Durchgehender schwebender Klang | Weniger klarer Suchrhythmus, nimmt dauerhaft akustischen Raum ein |

Auch KI-generierte Soundeffekte sind möglich: ElevenLabs dokumentiert eine
Loop-Option zur Erzeugung nahtlos wiederholbarer Klänge.
Quelle: [ElevenLabs Sound Effects](https://elevenlabs.io/docs/eleven-creative/playground/sound-effects).
Für diese beiden Entwürfe verwenden wir eine eigene, reproduzierbare Synthese;
es wurden keine fremden Audio-Samples und keine kostenpflichtige API verwendet.

## Dateien und Hörvergleich

- `soft-bells-preview.wav`: vier Wiederholungen, 12 Sekunden, helle Glocken.
- `warm-plucks-preview.wav`: vier Wiederholungen, 12 Sekunden, wärmere Alternative.
- `*-loop.wav`: jeweilige unveränderte 3-Sekunden-Schleife für spätere Integration.
- `validation.json`: technische Pegel- und Formatprüfung.

Die Hörproben sind **10 dB lauter** als die vorgesehenen Hintergrunddateien,
damit man den Charakter auf dem Rechner vergleichen kann. Die Lautheit im Raum
muss anschließend mit der Marshall-Box und der gewählten Lautstärke abgestimmt
werden. Noch kein akustischer Praxistest auf dem Pi für diese neuen Dateien.

Vier Noten bei 0,08 / 0,43 / 0,78 / 1,13 Sekunden, danach Ausklang und Pause.
Sanfte Ein- und Ausblendungen, exakte Stille an beiden Dateigrenzen, keine
Übersteuerung. 24 kHz, 16 Bit, Mono; ein Loop benötigt 144.044 Bytes inklusive
WAV-Header. Das lässt sich vorladen und wiederholen, ohne laufende Synthese oder
Cloud-Zugriff. Reale Wiedergabelast wurde für diese Entwürfe noch nicht gemessen.

Erzeugen: `python3 scripts/generate_search_sounds.py`.

## Vorgesehenes Laufzeitverhalten

1. Nur bestätigte Brain-/Web-Suchereignisse starten den Loop.
2. Parallele Suchen teilen sich genau einen Klang; kein Übereinanderlegen.
3. Beim letzten abgeschlossenen oder fehlgeschlagenen Suchvorgang ausblenden.
4. Sprachwiedergabe hat Vorrang. Bei eigener Sprache ebenfalls unterbrechen;
   nach einer kurzen Ruhephase nur fortsetzen, solange wirklich gesucht wird.
5. Suchton ausschalten, Gespräch beenden und Verbindungsabbruch stoppen den Klang.
6. Kein fester Suchfortschritt wird durch den Rhythmus behauptet.

Vor Integration besonders prüfen: Das ReSpeaker darf den Lautsprecher-Loop nicht
als neue Sprache an CDB senden oder dadurch fortlaufend die Wiedergabe sperren.
Echo-Unterdrückung und Sprechunterbrechung daher mit dem echten ReSpeaker/Marshall-
Aufbau testen. Die Aufnahme des Benutzers darf dafür nicht pauschal stummgeschaltet
werden. Außerdem Ende, Abbruch, parallele Suchaufrufe und Sound-Schalter prüfen.
