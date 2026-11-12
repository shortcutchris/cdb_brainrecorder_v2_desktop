# Abschluss der Pi-Beobachtung vom 16.–17. Oktober 2026

Ausgewertet am 19. Oktober 2026 nach wiederhergestelltem Tailscale-Zugang.
**Messung abgeschlossen; Ergebnis `needs_review`, Gesamtziel weiterhin offen.**
Dies ist ein historischer Testbericht, keine Aussage über den heutigen App-Zustand.

## Quellen und Verfahren

Originalplan: 16.10.2026, 12:31:15 bis 17.10.2026, 12:31:15 Europe/Berlin
(`start_epoch=1792146675.5296578`, `end_epoch=1792233075.5296578`).
Die vier technischen Dateien wurden unverändert und ausschließlich lesend über
Mac Studio vom Pi übernommen. Private Kopien liegen unter
`~/.local/share/cdb-stability-evidence-20261015/final-readonly-20261019T102202Z`.
Keine Audio-, Konto- oder Gesprächsinhalte wurden gelesen.

`scripts/summarize_pi_stability.py` wurde einmal auf diesen lokalen Kopien ausgeführt.
[Auswertung und SHA256 der Quellen](summary.json). Das Feld
`last_sample_age_seconds` bezieht sich auf die Auswertung am 19. Oktober.
Der aktuelle Dienstzustand ist `inactive/dead`, `MainPID=0`, `Result=success`;
das Abschlussereignis stammt vom 17.10. um 12:31:16. Der Beobachter hat seinen
begrenzten Lauf regulär beendet. Es wurde kein neuer Lauf gestartet.

## Messwerte und Einordnung

- 5.761 gültige Messpunkte, keine ungültigen Zeilen; 86.391,912 Sekunden bzw.
  **99,9906 %** Abdeckung nach Vereinigung der 15-Sekunden-Messintervalle.
  Der größte rechnerische Rest zwischen diesen Intervallen beträgt 0,011 Sekunden.
  Das ersetzt nicht die Ereignisprüfung: Am 16.10. um 13:31:53 wurde ein
  Abfragefehler aufgezeichnet. Dieser unterbricht den Bereitschaftsnachweis,
  obwohl er zwischen den groberen Ressourcenmessungen liegt.
- Keine aufgezeichneten Ressourcenwarnungen, kein Wechsel der Browsergeneration.
  Zwei Backendwechsel passen zu den bekannten Updates auf 0.5.60 und 0.5.61.
  Zwei Beobachterstarts passen zum ursprünglichen Start und zur bekannten
  Nabu-Zuordnungskorrektur um 12:55:35. Keine zusätzlichen Wechsel aufgezeichnet.
- Versionsfolge 0.5.59 / 0.5.60 / 0.5.61. Phrase zunächst `unknown` wegen der
  bekannten Beobachter-Zuordnung, danach `okay-nabu`; der Vorlauf bleibt erhalten.
  Dieser Datensatz ist **keine ungestörte 24-Stunden-Abnahme einer Version**.
- Browser-CPU im als `idle` gemeldeten Zustand: Median 29,0 %, p95 30,46 % eines
  Kerns, Maximum 96,59 %. Diese Statistik enthält bekannte Laborlast und ist
  keine reine Ruhemessung. Die bekannte Browser-Grundlast bleibt ungelöst.
- Browser-RSS: Median 1.379,89 MB, Maximum 1.388,67 MB. Stundenmediane steigen
  zunächst von etwa 1.308 auf 1.314 MB; im Zusammenhang mit der abendlichen
  Aktivität folgt ein höheres Plateau. Die letzten 14 Stundenmediane liegen bei
  1.380,45–1.381,91 MB. Kein fortlaufender nächtlicher Anstieg in diesem Datensatz;
  die Ursache des Sprungs ist damit nicht abschließend erklärt. Summiertes RSS
  kann gemeinsam genutzte Seiten mehrfach zählen.
- API-Antwortzeit bei `idle`: Median 4,83 ms, p95 97,6 ms, Maximum 113,27 ms.
- Zwei Wake-Ereignisse am 16.10. um 22:11:19 und 22:11:33: Verbindung nach
  3 bzw. 2 Sekunden, erste Ausgabe nach 4 bzw. 5 Sekunden. Vorherige belegte
  Ruhezeit nur 22 bzw. 1 Sekunde. Kein aufgezeichneter Wake-Fehler in diesen
  beiden Versuchen; die tatsächliche Erst-Ruf-Erkennung ist nicht belegt.

Die Rückkehr nach dem letzten Gespräch ist um 22:11:47 protokolliert.
Von 22:11:53 bis zum 17.10. um 12:31:13 liegen 3.438 aufeinanderfolgende
Messpunkte mit `idle`, `listening`, aktivem `okay-nabu` und Version 0.5.61 vor:
**14 Stunden 19 Minuten 20 Sekunden technische Bereitschaftsevidenz**.
Der größte Messpunktabstand beträgt 15,007292 Sekunden. In diesem Abschnitt
sind keine Fehler-, Neustart- oder Kontextwechselereignisse aufgezeichnet.
Es handelt sich um Abtastung, nicht um einen lückenlosen akustischen Nachweis.
Danach fehlt ein echter Ruf: **null qualifizierte Aktivierungen nach acht Stunden**.
Die zeitweilige Nichterreichbarkeit des Macs hat diese auf dem Pi fortlaufende
Messreihe nicht unterbrochen; für die Zeit nach Messende gibt es hier keine Daten.

Bekannte Raumtests, CPU-Dateitests, Wartungen und Updates am 16. Oktober bleiben
Kontextwechsel und zählen nicht als unbeeinflusste Ruhezeit. Details stehen im
[Forschungsbericht](../wake-word-research/2026-10-16/README.md) und in den
[Beobachter-Nachweisen](../observer-nabu-20261016/README.md). Die zusätzliche
abendliche Gesprächsaktivität ist technisch sichtbar; ihr Startweg und eine
natürliche Erst-Ruf-/Sprachende-Abnahme sind aus diesen Daten nicht bestimmbar.

## Prüfung der vollständigen Abnahmematrix

| Kriterium | Ergebnis und verbleibende Grenze |
| --- | --- |
| 24 Stunden, mindestens 99 % Abdeckung | Abdeckung erfüllt; Versionswechsel, Wartung, Beobachterkorrektur und Abfragefehler verhindern eine ungestörte Gesamtabnahme. |
| Keine ungeklärten Neustarts / dauerhaften Ressourcenwarnungen | Keine Warnungen, bekannte Wechsel zugeordnet; RSS-Plateau beobachtet, Ursache des früheren Sprungs nicht abschließend geklärt. |
| Echter Wake nach mindestens acht Stunden | Fehlt trotz langer technischer Bereitschaft am Ende. |
| Mindestens 100 lokale Zustands-/Konkurrenzzyklen, sichere Audioreservierung | Frühere isolierte Testnachweise vorhanden, etwa 100/100 Nabu-Zyklen; keine erneute vollständige Prüfung des installierten Gesamtstands durch diese Messung. |
| Fehlerfälle für Anmeldung, Cloud, Audio, Detektor und Status | Frühere Regressionen vorhanden; dieser passive Lauf prüft nicht die komplette Fehlerinjektionsmatrix. |
| Akustik getrennt von Cloud, echte Erst-Ruf-Qualität | Offen: bekannte natürliche KAI-Fehler und Nabu-Raum-Aussetzer/Fehlstart bleiben bestehen. Kleine synthetische Serien und Kandidatenmodelle ersetzen die Abnahme nicht. |
| Reservierung unter 100 ms / API normalerweise unter 200 ms / Cloud typisch unter 5 s | API-Werte günstig, zwei Cloud-Verbindungen in 2–3 s; Reservierungsgrenze hier nicht neu gemessen und Stichprobe keine Zuverlässigkeitsgarantie. |
| Rückkehr, echte UI-Pegel, Sprachende, Schutz laufender Aufnahmen | Technische Rückkehr nach beiden Wakes sichtbar; UI, hörbares Ergebnis, korrektes Sprachende und Aufnahme-Schutz nicht vollständig durch Telemetrie belegt. Älterer Schlüsselbund-Dialog nicht als behoben bestätigt. |

Die vollständigen Kriterien stehen im [Arbeitsziel](../idle-wake-0.5.45/stability-goal.md).
Das Gesamtziel bleibt offen. Insbesondere wird weder `needs_review` noch die
reguläre Dienstbeendigung als Produktabnahme ausgegeben. Keine Kandidaten wurden
aktiviert, keine Kopplung oder Remote-Ende-zu-Ende-Abnahme vorgenommen.

Nur Dokumentation: keine Änderung an App, Konfiguration, Dienst oder SD-Image;
kein Einfluss auf Updates bestehender Geräte oder Neuinstallation.
