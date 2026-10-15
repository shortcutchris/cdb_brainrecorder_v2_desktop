# Quellengeprüfter Vergleich auf dem Pi

16. Oktober 2026, **01:39:42–01:50:05 Europe/Berlin**. Zwei getrennte,
nacheinander gestartete Headless-Chromium-142-Profile, je 300 Sekunden und elf
Messpunkte. Sie laden schreibgeschützte Momentaufnahmen der tatsächlichen App
0.5.55; die Gegenprobe verwendet ausschließlich für `microphone.js` die echte
Korrektur aus Commit `d80f558` (SHA256 `9de014063923156499f4b294ad16b7402664785f24cd2d25307716ce7fc71276`).
Alle anderen untersuchten Quellhashes und Browserflags stimmen überein.

## Warum dieser Vergleich gültig ist

Der Runner liest die tatsächliche committed Kandidatendatei, prüft vor dem
Start deren exakten Ein-Zeilen-Unterschied zum installierten Original und
protokolliert den bedienten Hash. Jeder Messpunkt bestätigt zusätzlich die
vollständige Symboladresse `/assets/play.svg`, erfolgreiche Bilddekodierung,
sichtbare Startseite, laufende Abfragen und keine JavaScript-Fehler.
Die zwei Nebenabfragen für Wissensbereiche und frühere Testdatei sind vorhanden.
Antwortinhalte bleiben ausschließlich im RAM; Berichte speichern keine
Aufnahmeinhalte, Bereichsnamen oder Kontotokens.

Die vorhandene produktive Schrift-404 wird auf beiden Seiten unverändert
abgebildet und explizit protokolliert. `/favicon.ico` liefert wie produktiv 204.
Dies ist keine Behauptung vollständiger Asset-Gesundheit. Alle unerwarteten
HTTP-/Skriptfehler bleiben Abbruchgründe. Die fehlgeschlagenen Vorläufe werden
[nicht als Erfolge umgedeutet](../../idle-render-0.5.55/app-icon-probe/README.md).

## Beschreibende Kurzzeitwerte

| Messwert | Installiertes Original | Tatsächlicher Kandidat |
| --- | ---: | ---: |
| Erfolgreiche Antworten für `play.svg`, Ende | 337 | 2 |
| Interne Dokumente, Sekunde 60 → 300 | 85 → 116 | 48 → 48 |
| Aktiver Renderer-RSS, Sekunde 60 → 300 | +10,30 MiB | +3,08 MiB |
| Aktiver Renderer-CPU, Sekunde 60–300, ein Kern | 3,49 % | 2,46 % |
| Blink-/Embedder-Heap am Ende | 10,62 MiB | 5,50 MiB |

Die ersten 60 Sekunden bleiben in den Rohdaten; sie werden bei den angegebenen
Differenzen als Anlauf getrennt. Der Kandidat zeigt weiterhin temporäre
Objektzunahme und natürliche Bereinigung. Kein erzwungenes GC. Ein geringerer
Zuwachs in vier Minuten ist **kein** bewiesenes dauerhaftes Plateau oder ein
allgemeiner prozentualer Leistungsgewinn. Kein akustischer Wake-/Cloud-Test.

Die gesamten Prozessgruppen wechseln während beider Läufe durch Hilfsprozesse.
Die angegebenen Renderer behalten über alle elf Messpunkte PID und OS-
Startkennung; ihr Typ wurde während der Laufzeit separat geprüft. Es wird keine
strenge Gesamtgruppen-Stabilität aus wechselnden RSS-Summen behauptet.
Headless-Grafik, DevTools und eingefrorene Statusdaten begrenzen die Übertragung
auf den echten Kiosk. CPU-Limit 50 % eines Kerns, eigene stumme Profile, keine
Schreibweiterleitung und Aktivitätsabbruch bei belegtem Gerät. Alle Wächter-
Prüfungen meldeten Leerlauf. Beide Browser, Server und Wächter sind geschlossen;
Profile gelöscht. Die zusätzliche Last überlappt den alten Produktionsmonitor
und ist keine unbeeinflusste Leerlauf-Baseline.

[Auswertung](summary.json), [reproduzierbares Skript](summarize.py),
[Original](original/profile.json), [Kandidat](guarded/profile.json).
Je Ordner: tatsächlicher Runner/Kandidat, Prozesszuordnung, Bereinigung und
Validierung. `scripts/validate_icon_probe.py` weist unter anderem falschen
Quellhash, defekte Bilder, unvollständige Messungen, stockende Abfragen und
ersetzte Browser zurück. Acht Regressionstests bestehen. `probe_valid: true`
bezeichnet ausschließlich diese Vergleichsmessung; `overall_goal_complete`
bleibt ausdrücklich false. Die neue produktive 24h-/Acht-Stunden-Abnahme folgt
separat nach der signierten Installation.
