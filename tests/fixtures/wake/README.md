# Synthetische Wake-Teststimmen

Am 15.10.2026 auf ausdrücklichen Nutzerauftrag über ElevenLabs erzeugt.
Stimme Vincent – Factual (`ABvMrd8urrMUl3V6UZ3Y`), Modell
`eleven_multilingual_v2`, Sprache Deutsch, MP3 44,1 kHz/128 kbit/s.

- `hey-brain-vincent.mp3`: „Hey Brain.“, Geschwindigkeit 1, Stabilität 0,6.
- `hey-brain-vincent-slow.mp3`: „Hey, Brain.“, Geschwindigkeit 0,75, Stabilität 0,65.
- `end-vincent.mp3`: „Gespräch beenden.“, Geschwindigkeit 1, Stabilität 0,6.

Keine Aufnahmen von Personen oder Raumgesprächen. Akustischer Wiedergabetest
mit zwei Sekunden Stille vor und einer Sekunde danach, 16 kHz Mono PCM-WAV.
Die App pausiert Wake absichtlich bei eigener Wiedergabe: Für einen isolierten
Raumtest `scripts/check_wake_acoustic.py` unter atomarer Wartung verwenden.
Ein echter produktiver Wake-Test braucht eine davon unabhängige menschliche
Stimme oder externe Schallquelle. Nicht unangekündigt hörbar abspielen.
