# Design-QA — Recorder Studio, Variante 2

Datum: 11.10.2026. Ergebnis: **passed**. Keine offenen P0-, P1- oder P2-Designabweichungen im geprüften Umfang.

## Referenz und Vergleich

Referenz ist das ausdrücklich gewählte zweite ImageGen-Bild `exec-7098b889-e275-49b9-88be-ee57587a758e.png` (1672 × 941). Vergleichszustand: Teamrunde ausgewählt, Notizen geöffnet, Aufnahme bereit, eine Transkription aktiv und zwei Aufgaben wartend. Referenz auf 1280 × 720 normalisiert; Umsetzung auf dem echten Pi mit Chromium/Wayland in 1280 × 720 aufgenommen. Der kombinierte Vergleich und Ausschnitte wurden tatsächlich geöffnet und beurteilt.

Nachweise im lokalen Abnahmeordner: `studio-comparison-pi-final.jpg`, `studio-compare-pi-capture.jpg`, `studio-compare-pi-notes.jpg`, `studio-pi-queue.png`. Links im abschließenden Abnahmebericht führen zu den Dateien.

## Korrekturen und Ergebnis

| Fläche | Befund und Korrektur | Ergebnis |
| --- | --- | --- |
| Hauptproportionen | 88-px-Navigation, 324-px-Aufnahmebereich, rechter Editor und 72-px-Fußleiste wie normalisierte Referenz | bestanden |
| Aufnahmeknopf | 174 × 174 px, heller Ring, weißer Kern; klarer blauer Verlauf statt flacher Farbe; vertikale Abstände korrigiert | bestanden |
| Symbole | Inaktive Symbole blaugrau statt schwarz, aktive Symbole blau; lokale Phosphor-Dateien | bestanden |
| Notizen | Vier Zeilen vollständig sichtbar, Zeilenabstand ca. 35 px; überzählige Leerzeilen ausschließlich in der Testvorlage entfernt | bestanden |
| Titel, Player, Register | Vertikale Abweichung verringert; aktive Lautstärke blau dargestellt; lokale Inter-Schrift | bestanden |
| Status | Tatsächliche aktive Phase, Laufzeit und Anzahl wartender Aufgaben; Vergleich mit derselben Phase | bestanden |
| Kleineres Display | 1024 × 600 ohne Dokumentüberlauf; Aufnahmeknopf 136 × 136 px, Editor 177,5 px hoch, Fußleiste vollständig sichtbar | bestanden |
| Touch-Tastatur | Integrierte Tastatur im Hauptfenster und Suchdialog, Editor bleibt sichtbar; Umlaute, Zeilenumbruch und Zifferneingabe funktional geprüft | bestanden |

Die Mac-In-App-Browseraufnahme gab Blau sichtbar stumpfer wieder. Maßgeblich für die Farbe ist die tatsächlich geprüfte Pi-Bildschirmaufnahme; dort entspricht der Verlauf dem Ziel. `studio-pi-main-before-final.png` zeigt den Hauptbildschirm **ohne** Tastatur und ist kein Tastaturnachweis. Die integrierte Tastatur ist durch `studio-touch-keyboard.jpg` und `studio-library-keyboard.jpg` aus dem interaktiven Browser-Test dokumentiert; ein physischer Fingertest auf dem Pi wird nicht behauptet.

Bewusste funktionale Unterschiede zur statischen Vorlage: Die Anzeige übernimmt echte Uhrzeiten und Speicherzustände, erfindet kein integriertes Mikrofon, zeigt tatsächliche Audiomesswerte und kennzeichnet die isolierte Testbibliothek. Der reale Fortschrittszähler wurde nicht auf die erfundenen 02:14 der Vorlage gesetzt. Die zusätzliche Tastatur-Schaltfläche ermöglicht die Touchbedienung. Kleinere Unterschiede bei Glyphen und Schatten sind P3.

## Funktions-QA

17 Python-Tests auf dem Pi bestanden (10 bestehende native Tests, 7 HTTP-Studio-Tests), erneut unter explizitem UTF-8 ohne vorherigen Codierungsfehler. Auf dem Mac bestanden dieselben bestehenden Tests und die neuen Studio-Tests. Die HTTP-Prüfungen umfassen bestehende Sitzungszuordnung, Konfliktschutz, Notizspeicherung bei gesperrten KI-Feldern, Prompt-Verwaltung, Audio-Range/Export, Host/Origin/CSRF, ausschließliche Loopback-Bindung, exklusive Backend-Sperre, Doppelstartschutz und Audiodatenerhalt beim Beenden/Neustart.

Interaktiver Browser-Test: Aufnahme/Stop, neue Aufnahme während Transkription und während Zusammenfassung, unverändert ausgewähltes Meeting, Warteschlange, Wiedergabe mit fortschreitender Position, Registerwechsel, Notizen nach Neuladen, eigener Prompt, Bibliothek/Suche und integrierte Tastatur. Zusätzlich wurde dieselbe Oberfläche über einen SSH-Tunnel mit dem Python-Testbackend auf dem Pi verbunden und drei Meetings durch die echte FIFO-Warteschlange geführt. Testprozessor und künstliche Audioquelle sind ausdrücklich isoliert; hieraus wird keine Modell- oder Mikrofonqualität abgeleitet.

Der reale Pi hat derzeit kein gefundenes Aufnahmemikrofon. Die Einrichtung bleibt entsprechend offen. Die bekannte Lüftermeldung 0 U/min begrenzt belastbare Modelltests, nicht diese UI-Abnahme. Keine zusätzlichen schweren Modelltests wurden für die Gestaltung ausgelöst.
