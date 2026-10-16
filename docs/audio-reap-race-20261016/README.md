# Bestätigter Audioabschluss statt sporadischem Cleanup-Fehler

16. Oktober 2026. Korrekturkandidat auf Basis `1d35d02`; noch nicht produktiv
installiert. Die laufende Pi-App bleibt 0.5.60 mit unveränderter Nabu-Erkennung.

## Fehler und Korrektur

Der vollständige Mac-Testlauf der Mobile-Fernbedienung hatte den bereits zuvor
bekannten Fehler in `test_followup_tool_inside_grace_keeps_one_player` beim
Beenden des Suchtons erneut gezeigt. Eine isolierte Wiederholung mit echten,
stummen Python-Kindprozessen lieferte bei 12 Durchläufen zweimal `EPERM` auf
`killpg(SIGTERM)`; unmittelbar danach meldete `getpgid` jeweils `ESRCH`.
Der Prozess war bereits verschwunden, während die asyncio-Abschlussmeldung
noch ausstand. Die zwölf Tests waren formal grün, enthielten aber zwei nicht
abgeholte Task-Exceptions. Ein grüner Testzähler allein war hier unzureichend.

Der Signalweg wartet bei verweigertem Signal jetzt maximal 0,5 Sekunden auf
den tatsächlichen Abschluss. Nur ein bestätigter Returncode macht diesen
Fehler unschädlich. Ein lebender oder nicht bestätigter Kindprozess bleibt
registriert; Cleanup schlägt weiterhin fehl und kann wiederholt werden.
Der abschließende Kill-/Reap-Versuch läuft auf derselben asyncio-Schleife.
Es wird weder ein Berechtigungsfehler pauschal verschluckt noch die Audiosperre
aufgrund des bloßen `closed`-Flags freigegeben.

## Nachweise

- Neuer deterministischer Test gegen unveränderten Basiscode: beide Varianten
  (normaler Abschluss und abschließender Kill-Pfad) schlagen erwartungsgemäß fehl.
- Kandidat: 10 gezielte Freigabetests bestanden. Enthalten sind 100 konkurrierende
  Close-/Retry-Zyklen, nicht beendete Prozesse, fehlgeschlagene Wake-Freigabe,
  Live-Reservierung und ein echter lebender Kindprozess mit verweigertem Signal.
- [Vollständiger Mac-Lauf](python-tests-mac.txt): **415 Tests bestanden** in
  72,922 Sekunden. Verbleibende Deprecation-/Qt-/ResourceWarnings sind im Log
  sichtbar; kein behaupteter warnungsfreier Lauf.
- [Zwölf erneute Suchton-Abschlüsse](repeat-search-close-mac.txt): 12 bestanden,
  zweimal derselbe reale EPERM/ESRCH-Fall, **keine** unbehandelte Task-Exception.
- [Isoliert auf dem echten Pi](python-tests-pi.txt): **10 Tests bestanden** in
  2,214 Sekunden. Nur lokale temporäre Testdateien und stumme Kindprozesse,
  keine Mikrofonöffnung, Lautsprecherwiedergabe, Cloud-Sitzung oder App-Neustart.
  Vorhandene Runtime verwendet; keine Paketinstallation. Kein vollständiger
  Pi-Gesamtlauf und keine akustische Abnahme durch diese Prüfung.

Reproduktion lokal:

```sh
QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests -p test_audio_release.py -q
QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests -q
```

## Laufende Beobachtung getrennt bewerten

[Technischer Zwischenstand](observation-interim.json), 16.10.2026 15:22:43
Europe/Berlin: 2,86 Stunden des ursprünglichen Plans erfasst, 687 gültige
Stichproben, 99,99 % Abdeckung der bis dahin verstrichenen Zeit. Messdienst
PID1894368 tatsächlich aktiv. Browser-CPU im Leerlauf Median 28,2 %, p95 30,26 %
eines Kerns; stündliche RSS-Mediane 1308,17 / 1307,34 / 1308,61 MB. Kein wachsender
Trend in diesem kurzen Ausschnitt und keine aktiven Ressourcenwarnungen.

Kein echter Wake beobachtet. Historische unbekannte Phrase, Messdienst-Neustart,
App-Wechsel und angekündigte Labortests bleiben erhalten. Das ist **keine**
ungestörte 24h-Abnahme und kein Nachweis eines natürlichen Erst-Rufs nach acht
Stunden. Der Plan endet unverändert am 17.10. um 12:31:15 Europe/Berlin.
Die Rohdateien bleiben privat; der Bericht enthält technische Messwerte und
Hashes. Der hier beschriebene spätere kurze Pi-Prozesstest ist zusätzliche
Laborlast und darf nicht als reine passive Ressourcenmessung ausgegeben werden.

## Auslieferung und Image

Noch kein App-Update, kein Versionswechsel, keine Änderung am Produktivprofil.
Der geänderte Code liegt in der bereits erlaubten Datei `services/live_audio.py`
und wird bei einem späteren signierten App-Paket sowie einem neuen Image-Export
übernommen. Keine neue Abhängigkeit, kein Datenformat und keine Factory-Änderung.
Ein neuer Image-Build oder Hardware-Boot wurde nicht durchgeführt. Der Kandidat
wird getrennt zur Prüfung gepusht; das Stabilitätsziel bleibt offen. Kein
automatischer Watchdog und keine Änderung an Modell oder Erkennungsschwelle.
