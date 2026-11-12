# Bestätigte deutsche Ansagen: Modell, Stimme und Arbeitsweise

Stand und Nutzerabnahme: **21. Oktober 2026**, Pi-Version **0.5.67**, signierte
Sequenz **24**, Quellcommit `a517be09b27c25f9a72dee8c35365f1153ddcd46`.

Nach Veröffentlichung und Geräteprüfung der Verbindungsansage bestätigte Chris:
> Okay, läuft perfekt […] Stimme, alles läuft perfekt.

Damit ist die persönliche Hörabnahme der aktuellen Stimme und des erlebten
Ansagenablaufs festgehalten. Bereits nach den Offline-/Timer-Ansagen hatte er
bestätigt: „Der Sound hört sich sehr gut an.“ Diese Kombination aus Stimme,
Sprachpaket und Wiedergabeablauf ist die bestätigte Referenz für weitere feste
Ansagen. Vorhandene, abgenommene Clips bei Erweiterungen beibehalten.

## Verwendetes Modell und Stimme

| Eigenschaft | Bestätigte Implementierung |
| --- | --- |
| Text-zu-Sprache-Modell | `gradium/phonon-40m-de` |
| Modelldatei | `model.q8.gguf`, Quantisierung Q8 |
| Stimme | `voice='default'`, mitgelieferte `default-voice.safetensors` |
| Sprache / Textaufbereitung | `lang='de'`, `rewrites='all'` |
| Erzeugungsbibliothek | `ptts==0.4.0` |
| Erzeugung | CPU, ein Thread, Seed 42, auf dem Mac |
| Ausgabeformat | WAV, Mono, PCM16, 24 kHz |
| Produktionsbetrieb auf dem Pi | Vorgefertigte Dateien über den bestehenden Lautsprecherausgang |

Die Standardstimme wurde verwendet; keine eigene Stimme trainiert oder geklont.
Die Modell- und Stimmdateien wurden nach Hugging-Face-Freigabe lokal bereitgestellt.
Die Parameter stehen im Werkzeug `scripts/prepare_announcements.py`.
Die konkreten freigegebenen Audiodateien sind durch ihre SHA-256-Prüfsummen im
[Vier-Clip-Manifest](connecting-pack-manifest.json) eindeutig dokumentiert.

## So haben wir gearbeitet

1. Lokale deutsche Synthese mit Phonon erprobt, danach begrenzte CPU-Versuche
   auf dem Pi durchgeführt. Diese Versuche begründeten keine Freigabe für
   dauerhafte Synthese parallel zur Aufnahme oder Rufworterkennung.
2. Feste Texte auf dem Mac vorberechnet und WAV-Format, Text, Länge und
   Prüfsummen geprüft. Der Pi benötigt für die produktiven Ansagen weder das
   Phonon-Modell noch eine zusätzliche KI-Laufzeit.
3. Zuerst Offline-, Timer- und Erinnerungsansagen mit PR #13 / 0.5.66 eingeführt;
   anschließend „Ich verbinde dich.“ mit PR #14 / 0.5.67 ergänzt. Die drei
   vorhandenen Clips blieben beim zweiten Schritt bytegleich.
4. Signierte App-Updates und Paketwechsel nur bei freiem Gerät unter der
   Wartungssperre durchgeführt. Einstellungen erhalten, altes Paket gesichert,
   Ansagen erst ohne laufende Aufnahme oder Unterhaltung aktiviert.
5. Automatisierte Schutzprüfungen, begrenzte echte Geräteprüfungen und danach
   persönliche Hörabnahme durch den Nutzer durchgeführt. Technische Nachweise
   und Hörurteil werden getrennt dokumentiert.

Aktiv sind Offline-/Fehlerhinweis, Timer-/Erinnerungsansagen und Verbindungsansage.
Für „Ich verbinde dich.“ dauert der Clip 1,68 Sekunden. Darauf folgen zwei Sekunden
Nachhallpause; erst danach öffnet sich das Gesprächsmikrofon. Die Rufworterkennung
ist während der Ausgabe ausgesetzt und kehrt nach dem beendeten Vorgang zurück.
Bestehende Aufnahme, Pause oder Unterhaltung werden für eine Ansage nicht beendet.

Die lokale Stimme dient diesen festen Ansagen. Die eigentliche Voice-One-
Unterhaltung einschließlich Cloud-Begrüßung nutzt weiterhin ihren bestehenden
Sprachdienst. Es wurde keine dynamische Phonon-Synthese in das Gespräch eingebaut.

## Nachweise und Umfang der Abnahme

- [Installation, Bedienung und Schutzregeln](README.md)
- [Verbindungsablauf und produktive Geräteprüfung](connecting.md)
- [Automatisierte Prüfung und Nutzerabnahme](connecting-validation.json)
- [Texte, Dauer und Prüfsummen aller vier Clips](connecting-pack-manifest.json)

Das Nutzerurteil bestätigt die erlebte Stimme und Funktion. Es ersetzt keine
systematische Echo-/Raummessung, natürliche Rufwort-Langzeitprüfung oder zusätzliche
Geräteprüfung unter Aufnahme/Pause. Diese Grenzen der technischen Prüfung bleiben
bestehen. Keine Änderung an Laufzeit, Konfiguration oder SD-Image durch diesen
Dokumentationsnachtrag; kein neuer Pi-Test und keine erneute Audiowiedergabe nötig.
