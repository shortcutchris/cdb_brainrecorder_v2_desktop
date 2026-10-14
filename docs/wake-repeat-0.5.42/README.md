# Fünf Gespräche hintereinander · 0.5.42

14. Oktober 2026. Raspberry Pi 5, gleiche laufende App-Instanz über alle fünf Durchläufe.

## Befunde vor der Korrektur

- Die Session bestätigte `session.instructions.appended`, blieb jedoch über 65 Sekunden ohne Begrüßung. [Nachweis](before-greeting.json). Eine weitere erste Probe war ebenfalls am Begrüßungs-Timeout gescheitert; erst die instrumentierte Wiederholung belegte das bestätigte, aber stumme Verhalten.
- „Gespräch beenden“ wurde als „Gespr�che beenden“ transkribiert. Der Agent kündigte das Ende an, die lokale enge Wortprüfung schloss aber nicht. [Nachweis](before-end.json).

## Korrektur

Bestätigte Vorbereitungsanweisung plus einmaliger expliziter Sprechauftrag mit `session.commentary.append`, wie im vorhandenen Voice-One-Client für vorbereitete Antworten. Eigene Ereignis-ID je Schritt; nur passende Bestätigung erlaubt den Folgeschritt. Kein Retry bei unklarem ACK, keine Wiederholung beim Reconnect. „Hallo“ bleibt erstes Wort. Das Modell kann die Satzzeichen natürlich gestalten.

Die lokale Ende-Prüfung erkennt zusätzlich den beobachteten Plural und ausschließlich innerhalb des Wortes Gespräch/Gespräche `ae` bzw. ein einzelnes Ersatzzeichen. Keine allgemeine unscharfe Erkennung, keine Änderung des gespeicherten Transkripts. Fragen, Verneinungen, Zitate und Assistentenstimmen bleiben ausgeschlossen.

## Methode und Ergebnis

Echtes lokales Vosk-Modell, tatsächlicher Detector-Unterprozess, native WebRTC-Verbindung und reale CDB-Staging-Sitzungen mit `staging_playground`. Espeak liefert synthetisches „Hey Brain“ an den Detector und synthetisches „Gespräch beenden“ an den Audioeingang. Keine direkte Auslösung von Start/Ende in der Testserie, kein Neustart der App zwischen Gesprächen. Wiederanlauf mit frischem Detector-Prozess und Freigabe der Bedienung geprüft.

Die Tests laufen in isoliertem Datenverzeichnis auf dem Pi. Mikrofoninput und Lautsprecherausgabe sind synthetisch bzw. stumm abgenommen. Dies prüft den vollständigen Softwareablauf, nicht Reichweite, Raumecho oder individuelle Aussprache am realen Mikrofon.

| Runde | Hey Brain erkannt | Erstes Begrüßungswort | Ende per Sprache | Wieder bereit nach Schließen |
|---|---:|---:|---:|---:|
| 1 | 1.81 s | 10.73 s | 4.62 s | 0.72 s |
| 2 | 1.75 s | 5.66 s | 4.12 s | 0.82 s |
| 3 | 1.70 s | 9.93 s | 4.62 s | 0.72 s |
| 4 | 1.81 s | 10.38 s | 5.03 s | 0.72 s |
| 5 | 1.75 s | 11.02 s | 4.62 s | 0.72 s |

Erkennung und erstes Begrüßungswort zählen ab Beginn des eingespeisten Aktivierungsworts. Ende zählt ab Beginn des eingespeisten Ende-Befehls und enthält dessen Sprechdauer. Die letzte Spalte zählt erst nach vollständigem Schließen. Keine allgemeine Latenzgarantie: Cloud- und Netzwerkzeiten variieren.

**5/5 bestanden**: jeweils eine kurze Hallo-Begrüßung, `voice_command`, keine zurückgebliebenen Live-Audioprozesse, Recorder und Einstellungen freigegeben, lokaler Detector wieder `listening`. [Vollständige Messung](after-five-cycles.json).

Automatische Regression: passende und veraltete ACKs, Reihenfolge des Sprechauftrags, kein zweiter Start bei Reconnect, Abbruch, Mute-Erhaltung sowie negative und beschädigte/plurale Ende-Äußerungen.

**223 Python-Tests und 99 JavaScript-Tests bestanden.**
