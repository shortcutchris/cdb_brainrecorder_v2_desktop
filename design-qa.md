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

Die Python-Prüfungen umfassen 10 bestehende native Tests und 8 HTTP-Studio-Tests. Die HTTP-Prüfungen decken bestehende Sitzungszuordnung, Konfliktschutz, Notizspeicherung bei gesperrten KI-Feldern, Prompt-Verwaltung, Audio-Range/Export, Host/Origin/CSRF, ausschließliche Loopback-Bindung, exklusive Backend-Sperre, Doppelstartschutz, Audiodatenerhalt beim Beenden/Neustart und ausdrücklich isolierte Einstellungen ab. Die abschließenden Ergebnisse stehen im Installationsbericht.

Die Sicherungsprüfung vor der Installation fand echte Test-Promptänderungen: Qt verwendet beim Konstruktor mit Organisation/Anwendungsname weiter die nativen Einstellungen, obwohl das globale Standardformat geändert wurde. Tests und Vorschau erhalten jetzt ausdrücklich eine eigene QSettings-Datei. Drei eindeutig anhand Testname und Testtext identifizierte Artefakte auf dem Pi und fünf auf dem Mac wurden nach zusätzlicher Sicherung entfernt; alle anderen Einstellungen blieben erhalten. Der ursprüngliche Pi-Stand aus der Sicherung vor 0.3.0 enthielt keine eigenen Prompts. Zusätzlich prüft ein Regressionstest, dass der Testadapter keinen nativen Einstellungen-Konstruktor aufruft. Das Studio verwendet im Produktivbetrieb bewusst weiterhin die ursprünglichen Einstellungen.

Interaktiver Browser-Test: Aufnahme/Stop, neue Aufnahme während Transkription und während Zusammenfassung, unverändert ausgewähltes Meeting, Warteschlange, Wiedergabe mit fortschreitender Position, Registerwechsel, Notizen nach Neuladen, eigener Prompt, Bibliothek/Suche und integrierte Tastatur. Zusätzlich wurde dieselbe Oberfläche über einen SSH-Tunnel mit dem Python-Testbackend auf dem Pi verbunden und drei Meetings durch die echte FIFO-Warteschlange geführt. Testprozessor und künstliche Audioquelle sind ausdrücklich isoliert; hieraus wird keine Modell- oder Mikrofonqualität abgeleitet.

Der reale Pi hat derzeit kein gefundenes Aufnahmemikrofon. Die Einrichtung bleibt entsprechend offen. Die bekannte Lüftermeldung 0 U/min begrenzt belastbare Modelltests, nicht diese UI-Abnahme. Keine zusätzlichen schweren Modelltests wurden für die Gestaltung ausgelöst.


## Auditnachprüfung Studio 0.4.1 — 11.10.2026

Ausgewählte Studio-Variante 2 bleibt erhalten. Aktuelle Nachprüfung mit echten Browseraufnahmen bei 1280×720 und 1024×600: Dialog-Stop, beschäftigte Meetingaktionen, Download-/Test-/Konfigurationsregeln, Notizen während KI und Aufnahme, Speicherfehler, lokaler Export, Konfliktvergleich, Wiederherstellung in frisch geladener Seite, Offline/Wiederverbindung, Warteschlange, Einrichtung, Prompts und Tastatur. Fehlerhinweise verdecken die Entwurfsaktionen nicht mehr. Die Tastatur überspringt verborgene Felder und Regler. Die offene Queue reduziert die übrige Ansicht, ohne den Aufnahmestopp zu verdecken.

Die nummerierte Galerie und der Abnahmebericht liegen im lokalen Aufgabenordner `outputs/studio-audit/`. Alle Galerieinhalte sind synthetisch; persönliche produktive Meetingansichten werden nur privat geprüft. Keine vollständige WCAG-Zertifizierung; physischer Fingertest und echte Mikrofonaufnahme bleiben Hardwareprüfungen.

## Variante 3 – Gesprächswissen, 0.5.27 (13.10.2026)

Ausgewählte Referenz: `exec-bc63cad5-f186-4178-8329-f134fab2170c.png`, 1672 × 941.
Implementierung: `output/playwright/live-0.5.27/01-auswahl.jpg`, 1280 × 720,
gleicher Vorstartzustand mit Projekt Atlas, Teamwissen und Workshop-Notizen gewählt.
Beide Bilder gemeinsam betrachtet, Abmessungen proportional auf 1280 × 720
verglichen. Aktive Ansicht zusätzlich anhand `04-gespraech-gesperrt.jpg` geprüft.

| Prüfung | Ergebnis |
|---|---|
| Struktur | Schmale Navigation, fester Header, Statuszeile, Chat links, feste 320-px-Wissensleiste rechts, Footer: bestanden |
| Typografie/Spacing | Lokale Inter, 16-px-Zeilen, 20-px-Seitentitel, 48-px-Touchziele, 24-px-Inhaltsrand: bestanden |
| Assets/Farben | Vorhandene Phosphor-SVGs und vier offizielle Ergänzungen; Themefilter im dunklen CDB-Theme nachgebessert |
| Auswahl/Seiten | Vier Zeilen am Zielbildschirm, Suche und Nummernseiten. Ausgewählte Checkboxen und gesperrte Übersicht unterscheidbar |
| Stabilität | Footer x88/y612/h80 vor/während Gespräch gleich; Seitenleiste x936/y200/w320/h372; kein Dokumentüberlauf |
| Tastatur/kleine Größe | 1280 × 720 und 1024 × 600 geprüft; anfänglich abgeschnittene Zeile bei kleiner Tastaturansicht behoben |
| Status | Keine offenen P0/P1/P2-Layoutprobleme in den geprüften Zuständen |

Bewusste Unterschiede zur hellen Referenz: bestehendes auswählbares CDB-Theme
(Navy/Orange) statt erzwungenem Blau; tatsächliche Pi-Audiogeräte bleiben sichtbar;
Aktualisieren als zusätzlicher Iconbutton; vorhandene harmonisierte 208-px-
Footerbuttons; keine dekorative Mikrofonillustration in der Statusleiste.
Texte und Zeilenumbrüche wurden auf das reale Display angepasst. Die festen Leisten
folgen dem übrigen Produkt. Synthetische Bilder sind im Abnahmebericht gekennzeichnet.
