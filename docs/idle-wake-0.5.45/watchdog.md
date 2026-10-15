# 24-Stunden-Beobachtung und sicherer Watchdog

15. Oktober 2026. Erste Stufe ist **nur Beobachtung**. Kein automatischer
Browser-/App-/Pi-Neustart ist aktiviert. Der Messdienst hat keinerlei Steuerpfad,
öffnet kein Mikrofon und startet keine künstlichen Gespräche im Raum.

## Aktive Beobachtung

`scripts/observe_pi_stability.py` läuft als separater Benutzerdienst auf dem Pi,
auch wenn der steuernde Mac schläft. Er verwendet ausschließlich lesende lokale
HTTP-Aufrufe und `/proc`-/Temperaturwerte. Kein Zugriff auf Aufnahmen oder
Gesprächsinhalte. Die beiden schnellen Status-Endpunkte enthalten weder Texte
noch Konten/Knowledge Areas. Der Verwaltungsschlüssel wird nur im Arbeitsspeicher
für den lokalen Health-Aufruf verwendet und niemals protokolliert.

- Alle 15 Sekunden: CPU und RSS des Kiosk-Prozessbaums (anderes Browserprofil
  ausgeschlossen), separat Renderer-RSS, freier RAM, Temperatur, Zustand und
  Antwortzeit des Python-Diensts.
- Etwa jede Sekunde: Aktivierungszähler und Gesprächszustand; Ereignisse nur bei
  Änderungen. Bei echten Nutzeraufrufen: vorausgehende Bereitschaftsdauer,
  beobachtete Zeit ab Erkennung bis zur Verbindung und zur ersten Audioausgabe.
- Eine unveränderliche Start-/Endzeit beendet die Erfassung nach 24 Stunden.
  Neustart des Messdiensts verlängert diese Frist nicht. Unterbrechungen werden
  als Lücken dokumentiert; kein vorgetäuschter vollständiger Dauerlauf.
- JSONL-Daten und atomarer Status lokal im privaten Beobachtungsordner, mit
  Dateirechten 0600; keine Gesprächstexte, Audiodateien oder Tokens. Wenige MB
  pro Tag, reguläre Status-/Messwertschreibvorgänge nur alle 15 Sekunden.
- Ein Codex-Heartbeat prüft die Daten alle 15 Minuten, meldet neue Auffälligkeiten
  und erstellt nach Ablauf den Abschluss. Bei unverändertem Zustand bleibt er
  still. Die Benachrichtigung setzt einen erreichbaren Codex-Host und Pi voraus;
  die Messung selbst ist davon unabhängig.

**Grenzen:** CPU 100 % entspricht einem ausgelasteten Kern. RSS summiert auch
gemeinsam genutzte Speicherseiten; kein exakter exklusiver RAM-Verbrauch.
Erkennungs-/Verbindungszeiten sind Poll-Beobachtungen, normalerweise mit ungefähr
einer Sekunde Auflösung, bei API-Ausfällen gröber. Wir messen nicht den Zeitpunkt,
an dem ein Mensch zu sprechen beginnt. Ohne einen echten Aufruf nach längerer
Pause ist diese Wake-Latenz nicht geprüft. Audiopegel können Stille nicht von
einer kaputten Visualisierung unterscheiden; die Messung beweist nicht, dass der
Browser die Waveform tatsächlich zeichnet. Ein zukünftiger UI-Heartbeat ist
dafür zusätzlich notwendig.

## Vorläufige Warnschwellen

Diese Werte sind Beobachtungskriterien, noch keine Neustartfreigaben:

| Signal | Warnung |
| --- | --- |
| Browser-CPU | Mindestens 80 % eines Kerns während etwa fünf Minuten durchgehendem App-Leerlauf |
| Browser-RSS | Mindestens 1,5 GB während etwa fünf Minuten (gesamter Kiosk-Prozessbaum) |
| Speichertrend | Mindestens 256 MB Zunahme über 30 Minuten in derselben Browsergeneration |
| Browser fehlt | Etwa fünf Minuten ohne Kiosk-Prozess |
| System | Weniger als 512 MB verfügbarer RAM oder mindestens 80 °C über etwa fünf Minuten |
| Lokale Status-API | Drei fehlgeschlagene Abfragen in Folge |
| Wake-Verbindung | 15 Sekunden nach beobachteter Erkennung noch nicht verbunden |
| Erkennung | Drei Fehlerzustandswechsel binnen fünf Minuten oder etwa zwei Minuten im Lade-/Fehlerzustand bei freiem Gerät |

Während Aufnahme/Pause/Gespräch wird eine erhöhte CPU-Last nicht als
Leerlaufproblem gewertet. Speicher-/Erreichbarkeitswarnungen bleiben sichtbar.
Eine Warnung und ihre Erholung werden jeweils einmal je Zustandswechsel erfasst.
Im aktuellen Code gibt es selbst bei kritischen Werten **keine Gegenmaßnahme**.

## Nächste Stufe: kontrollierte Browser-Reparatur

1. **Messung bestätigen:** Langzeitwerte auswerten, normal aktive Phasen abgrenzen,
   Schwellen kalibrieren. Browser-Heartbeat muss Frame-/Statusaktualisierung
   nachweisen; eine erfolgreiche Python-Antwort allein beweist keine gesunde UI.
2. **Wartung atomar reservieren:** Unter derselben App-Sperre wie Aufnahme- und
   Gesprächsstart sämtliche Ressourcen prüfen. Kein bloßes „GET idle, dann kill“:
   Zwischen diesen Schritten könnte eine Aufnahme beginnen. Die bestehende
   `DeviceManagement.prepare`-Grenze ist die Grundlage, noch kein automatischer
   Watchdog. Reservierung sperrt neue Aufnahmen, Live-Starts und Wake-Starts bis
   zum Ende der Wartung.
3. **Bei Unsicherheit nichts beenden:** Aufnahme inklusive Pause, laufendes oder
   verbindendes Gespräch, Queue-Verarbeitung, Übertragung, Tests, Downloads,
   Wiedergabe, Geräteeinrichtung, Timer/Alarm und fremde Wartung blockieren. Auch
   ein nicht erreichbares Backend gilt als gesperrt. Zuerst zusätzlich offene
   Oberflächenentwürfe sichern/bestätigen. Keine Datenverluste als Preis einer
   Reparatur akzeptieren.
4. **Nur den Kiosk reparieren:** Geordnet den exakt identifizierten Browser mit
   festem Profil beenden und neu starten. Python-Backend, Aufnahmeprozesse und
   Pi bleiben laufen. Nach Start API **und** UI-Heartbeat prüfen, dann Wartung
   freigeben. Nie ein generisches `pkill chromium`, nie ein automatischer
   Pi-Neustart bei unbekanntem Aufnahmezustand.
5. **Schleifen verhindern:** Höchstens ein Versuch pro Stunde, maximal zwei pro
   Tag, nach erfolglosem Versuch nur melden. Reservierung mit Bootkennung und
   Ablaufzeit; Wiederanlauf darf keine dauerhafte Sperre hinterlassen. Sichtbarer
   Hinweis und nachvollziehbares Protokoll. Diese Aktionsstufe separat testen:
   konkurrierender Aufnahmestart, pausierte Aufnahme, Netzfehler, hängende API,
   Browser-PID-Wechsel, fehlgeschlagener Start und Neustart während Wartung.

## Installation, Ende und Image-Einfluss

Die temporäre Messung liegt außerhalb des signierten App-Verzeichnisses unter
`~/.local/share/cdb-stability-20261015/`, der Dienst heißt
`cdb-stability-observer.service`. `plan.json` hält die genaue Frist fest;
`status.json` den aktuellen Zustand, `events.jsonl` die Warnungen und
Wake-Ereignisse, `metrics.jsonl` die Messreihe. Er läuft als `chris` mit niedriger
Priorität, maximal 5 % eines CPU-Kerns und 64 MB RAM. Der Dienst ist für
Wiederanlauf aktiviert, endet aber immer zur ursprünglichen Frist. Nach der
Abnahme deaktivieren; Daten vor manueller Bereinigung sichern.

Auf dem Kunden-Image und in signierten App-Updates ist dieser Versuch **nicht
automatisch aktiv**. Das Hilfsskript unter `scripts/` gehört nicht zur App-
Positivliste. Kein neues Image, keine neue App-Version, keine Änderungen an
Pi-Konfiguration, Modellen oder Aufnahmeformaten erforderlich. Eine dauerhafte
Watchdog-Auslieferung braucht ausdrücklich die Factory-Dienstinstallation und
eine Migration für vorhandene Geräte sowie die oben beschriebenen Tests.

Die Tests prüfen Warnhysterese, Aufnahmelast, Speichertrend, PID-Wiederverwendung,
Profiltrennung, Statusausfälle und Wake-Messung. Aufnahme/Pause werden in diesen
Tests nur als Zustände simuliert; keine produktive Aufnahme wird für den
Messdienst verändert. Das ist noch kein Test eines automatisch eingreifenden
Watchdogs.

Nachtrag: 13 Monitoring-Tests bestanden. Der erste Messlauf wurde für 0.5.47
abgebrochen und unter `baseline-045-046` bewahrt; der nächste unter `baseline-047`
nach dem UI-Update auf 0.5.48. Beide sind bewusst **keine** bestandenen
24-Stunden-Läufe. Die verbindliche aktuelle Frist steht in `run/plan.json`.
Die Oberfläche wird zusätzlich per echtem Display-Screenshot geprüft; der
Messdienst kann weiterhin keine gerenderte Waveform bestätigen.

Weitere Vorläufe `baseline-048` und `baseline-049` wurden nach gezielten
Decoder-/Fehlerrückmeldungs-Korrekturen ebenfalls archiviert. Aktuell läuft
0.5.50; verbindliche Frist und [Abnahmestand](../wake-stability-0.5.50/README.md)
bleiben vom ursprünglichen Versuchsdatum getrennt. Alle Laborlasten sind beendet.

## Reproduzierbare Abschlussauswertung

`python3 scripts/summarize_pi_stability.py /pfad/zur/lokalen/messkopie`
liest ausschließlich `plan.json`, `status.json`, `metrics.jsonl` und
`events.jsonl`. Der Aufruf gehört auf den Auswertungsrechner; weder der
produktive Messdienst noch seine Startzeit werden verändert. Während der
Messung ist das Ergebnis ein Zwischenstand. Nach Ende eine vollständige Kopie
auswerten, damit gleichzeitig geschriebene Dateien nicht irrtümlich als
Messfehler gelten.

Die Abdeckung vereinigt Zeitfenster von höchstens 15 Sekunden je gültigem
Messwert. Doppelte Zeilen füllen keine Lücken; fehlende Browser-/Health-Daten
zählen nicht als gültige Messung. Abdeckung der bereits verstrichenen Zeit und
Abdeckung der gesamten geplanten 24 Stunden stehen getrennt im Bericht.
Neustarts, Versionswechsel, rückwärts laufende Zeitstempel und auch inzwischen
behobene Warnungen bleiben prüfpflichtig. CPU und Health-Latenz werden im
Leerlauf ausgewertet; stündliche RSS-Mediane ermöglichen eine getrennte
Bewertung des Speicherverlaufs.

Ein langer Wake-Nachweis benötigt zusammengehörige Erkennungs-, Verbindungs-
und Audioausgabe-Ereignisse nach mindestens acht Stunden beobachteter Ruhe
innerhalb dieses Laufs, Verbindung unter 15 Sekunden und keinen erfassten
Fehlschlag. Bloße Stille oder ein synthetischer Audiotest ersetzt ihn nicht.
Vor dem tatsächlichen Ende samt passendem Abschlussmarker lautet der Status
`pending`. Danach sind Messprobleme `needs_review`; auch `ready_for_review`
ist ausdrücklich **keine automatische Gesamtabnahme**. Speichertrend, echte
UI-/Audiofunktion und die vollständige Abnahmematrix bleiben zu bewerten.

Zwölf zusätzliche Tests prüfen vollständige und unvollständige Zeitfenster,
Duplikate, Ausfälle, Neustarts, Warnungen, Zeitrücksprünge, fehlende bzw. falsch
zugeordnete Wake-Ausgabe, Abschlussmarker, Leerlaufstatistik und beschädigte
JSONL-Zeilen. Validierung mit dem echten kurzen Zwischenstand: korrekt
`pending`, keine vorweggenommene 24-Stunden-Abnahme. Das Auswertungsskript
ändert keine App-Dateien, benötigt keine Auslieferung und hat keinen Einfluss
auf bestehende Geräte oder Kunden-Images.
