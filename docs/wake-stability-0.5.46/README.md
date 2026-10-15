# Wake-Stabilität · 0.5.46

**Nachtrag 0.5.48:** Die zusätzliche Prüfung des echten Touchbildschirms zeigte
eine Reload-Schleife nach dem Update: Das HTML enthielt weiterhin die feste
Versionsnummer 0.5.45. Dies war beim ersten Auslieferungstest übersehen worden.
Die API war erreichbar, während die Oberfläche fortlaufend neu lud. Ein
HTTP-Healthcheck allein reicht daher als Abnahme ausdrücklich nicht.

Das HTML erhält seine Versionsnummer jetzt direkt vom laufenden Backend.
Zusätzlich erlaubt die Oberfläche höchstens einen automatischen Reload pro
Zielversion und Tab, auch bei weiterhin veraltetem HTML. Vor dem Reload werden
Entwürfe gespeichert und der Aufnahme-/Gesprächs-/Wartungszustand erneut geprüft.
Ist der Tab-Speicher gesperrt, erfolgt kein automatischer Reload. Neue Tests
prüfen die dynamische HTML-Version und Länge, wiederholt veraltetes HTML,
Aufnahmestart während Entwurfsicherung und blockierten Tab-Speicher.
107 JS-Tests bestanden; die Hardware-Abnahme und der Langzeitlauf werden erneut
mit dem tatsächlich angezeigten Stand geprüft. Keine Änderung an Abhängigkeiten,
Kundendaten oder Factory-Diensten; neue Images übernehmen die drei App-Dateien.

**Nachtrag 0.5.47:** Beim echten signierten Update blieb das Arbeitsverzeichnis
des Diensts im ursprünglichen Checkout. `python -m services.wake_word` startete
daher einen alten Detektor ohne Fortschrittsmeldungen. Der neue Elternprozess
erkannte den fehlenden Fortschritt korrekt, startete aber wieder denselben alten
Code. Die Installation von 0.5.46 bestand damit die Wake-Abnahme nicht.

0.5.47 startet den Unterprozess ausdrücklich im unveränderlichen Release-Ordner
des laufenden Elternmoduls. Das behebt gleichzeitig den Fall eines frischen
Images ohne passenden Modulpfad im Standard-Arbeitsverzeichnis. Ein zusätzlicher
Regressionstest startet aus einem absichtlich fremden Verzeichnis. Keine
Änderung am Systemdienst oder seinen Kundeneinstellungen notwendig. Die
24-Stunden-Abnahme beginnt erst mit diesem korrigierten Installationsstand neu.

15. Oktober 2026. Folge des ausdrücklich gesetzten
[Stabilitätsziels](../idle-wake-0.5.45/stability-goal.md). Dies ist ein geprüfter
Zwischenstand, noch keine abgeschlossene 24-Stunden-Abnahme.

## Vier reproduzierte Fehlerfälle

Die neuen isolierten Fehlertests schlugen auf 0.5.45 in vier Fällen fehl:

1. Ein noch lebender, aber beim Start hängender Detektor blieb unbegrenzt aktiv.
2. Eine unvollständige Statuszeile des Kindprozesses ließ `readline()` unter
   den App-/Aufnahmesperren warten.
3. Ein blockierter Cloud-Heartbeat hielt die lokale Prüfung des sprachlichen
   Ende-Befehls auf.
4. Ein verspäteter Heartbeat-Fehler aus einer bereits beendeten Sitzung konnte
   ein inzwischen neu gestartetes Gespräch beenden.

Diese Fehler wurden durch kontrollierte Störungen reproduziert. Nicht alle
vier sind als Ursache des ursprünglichen Nutzerberichts nachgewiesen.

## Korrekturen und Schutz

Der Detektor meldet alle zwei Sekunden, dass weiterhin Audioblöcke verarbeitet
werden. Ohne Startbereitschaft innerhalb 30 Sekunden oder ohne Fortschritt
während 15 Sekunden beendet die App ausschließlich ihren eigenen
Wake-Detektor mitsamt dessen Aufnahme-Unterprozess. Nach zehn Sekunden folgt
ein neuer Versuch, **nur wenn die normalen Aktivitätssperren weiterhin frei sind**.
Eine laufende oder pausierte Aufnahme sowie ein Gespräch verhindern diesen Start.
Das ist keine Browser-/Backend-/Pi-Neustartfunktion.

Das Statusrohr wird in begrenzten verfügbaren Blöcken gelesen. Teilzeilen
werden gepuffert, ohne auf ein Zeilenende zu warten; Puffergröße ist begrenzt.
Nach einer Aktivierung wird der alte Prozess freigegeben und weiterer Inhalt
verworfen. Zwei Erkennungen aus demselben Audiostream starten kein zweites Gespräch.

Der Cloud-Heartbeat arbeitet nun außerhalb der lokalen Ende-/Zeitlimitprüfung.
Pro Sitzung ist höchstens ein Heartbeat gleichzeitig unterwegs. Späte
Fehlermeldungen dürfen nur die passende Sitzungsgeneration beenden; das gilt
auch für native Audiofehler und erschöpfte Ereignisstrom-Wiederholungen.
Die normalen Cloud-Timeouts bleiben bestehen. Ein langsamer Cloud-Close kann
weiterhin die vollständige Freigabe verzögern; keine unbelegte Sofortfreigabe
bei unbekanntem Serverzustand.

## Nachweise

- [282 Python-Tests](python-tests.txt) auf dem Pi, isolierte Testdaten. Darunter
  100 Runden mit acht konkurrierenden Reservierungsversuchen (je genau ein
  Besitzer), 100 Doppelnennungen und Fehlertests zu den vier Punkten oben.
  Die Reservierungstests sind keine 100 echten Cloud-Gespräche.
- [104 JavaScript-Tests](javascript-tests.txt) bestanden.
- [Akustischer Testkorpus](acoustic-corpus.json): 28/28 synthetische Beispiele
  über den echten Vosk-Erkenner korrekt, acht positive und zwanzig negative Fälle.
  60 Sekunden synthetische Stille ohne Auslösung. 85,39 Sekunden Sprachkorpus
  benötigten 2,364 Sekunden Inferenz-CPU; kein Feldtest für Fehlaktivierungen
  durch Fernsehen, Raumhall oder fremde Stimmen.
- Der 24-Stunden-Messdienst bleibt separat aktiv. Browserlast, Speicherwachstum
  und echte Aufrufe nach langer Pause werden nicht aus kurzen Unit-Tests abgeleitet.

Fünf isolierte [native CDB-Runden](native-cycles.json) auf dem Pi: 5/5 Aktivierungen,
je genau eine Reservierung, 5/5 Hallo-Begrüßungen und positive Eingangs-/Ausgangspegel.
Zwei Runden enthalten doppelt gesprochenes „Hey Brain“. Die Reservierung dauerte
0,08–0,10 ms, die lokale Erkennung 2,37–3,23 Sekunden ab Beginn der künstlichen
Quelle, die Begrüßung 5,23–8,27 Sekunden ab Quellenstart. Erste Runde mit bewusst
abgelaufenem Token in der privaten Testkopie. Kein echtes Raummikrofon oder
Lautsprecher wurde verwendet.

**Sprachliches Beenden: 4/5, noch nicht vollständig bestanden.** In Runde 2
lieferte die Cloud nur „Beende bitte das“ als Nutzertranskript. Dieser unvollständige
Satz wird nicht als sicherer Abschaltbefehl akzeptiert. Nach dem Testzeitlimit
wurde die Testsession kontrolliert per API geschlossen; die nächsten drei
Runden waren erfolgreich. Das Stabilitätsziel bleibt auch wegen dieses offenen
ASR-/Ende-Falls aktiv. Die Erkennungsgrammatik wird nicht auf beliebige Satzanfänge
aufgeweicht, um eine bessere Erfolgsquote vorzutäuschen.

Reproduktion über `scripts/check_native_wake_cycles.py --end-audio DATEI
--output /tmp/ERGEBNIS.json`: synthetische deutsche Audiodatei mit „Beende bitte
das Gespräch“, maximal fünf Runden; benötigt die vorhandene Staging-Anmeldung,
native Runtime, `espeak-ng`, `ffmpeg` und das konfigurierte Wake-Modell. Bei diesem
Lauf stammte der Ende-Satz aus der macOS-Stimme Anna. Die private Testkopie wird
anschließend entfernt. Dieses Skript startet echte Cloud-Sitzungen und ist kein
automatischer nächtlicher Produktions-Stresstest.

Die Gesamttests geben eine bestehende Qt-GC-Ressourcenwarnung beim Prozessende
aus; der Testlauf selbst meldet keine fehlgeschlagenen Tests. Die Änderung
führt keine Qt- oder Abhängigkeitsaktualisierung durch.

### Weitere Abnahme bis 0.5.48

[285 vollständige Python-Tests](python-tests-047.txt) mit den 0.5.47-Korrekturen
bestanden. Danach 48 Studio-Tests inklusive dynamischer Versionsauslieferung
und 107 JS-Tests für 0.5.48 bestanden. [Signiertes Deployment](deployment-048.json)
bestätigt Version 0.5.48 und unveränderte Einstellungen. Der komplette Pi wurde
nicht neu gestartet. Der nach der Reload-Schleife festgefahrene Browser wurde
einmal geordnet mit demselben Profil neu gestartet, unter der bestehenden
atomaren Wartungssperre; das Backend blieb dabei aktiv.

![Echter Pi-Bildschirm nach Wiederherstellung](pi-home-048.png)

Der installierte Detektor blieb in einer [44-Sekunden-Stichprobe](installed-wake-047.json)
mit derselben PID im richtigen Release-Ordner und im Zustand `listening`.
Das belegt die Beseitigung der 15-Sekunden-Neustartschleife, keinen Langzeitlauf.

Der [lange kontinuierliche Test](continuous-before.json) verwendet einen einzigen
Detektor für 1.000 synthetische Segmente, insgesamt 3.332,41 Sekunden Audiomaterial.
999/1.000 Segmente korrekt, keine falsche Aktivierung unter 500 Negativbeispielen,
eine überhörte Aktivierung unter 500 Positivbeispielen (Zyklus 725). Der Test gilt
als **nicht vollständig bestanden**. Er läuft schneller als Echtzeit und ersetzt
keine echte 55-Minuten-Standzeit. In der Produktion wird der Detektor nach einer
erfolgreichen Aktivierung beendet; der Test hält ihn absichtlich auch danach offen.

RSS stieg zunächst von etwa 157 MB auf 197 MB, blieb danach bis Zyklus 1.000
nahezu konstant. Die anfängliche Hochrechnung eines unbegrenzten Wachstums hat
sich damit nicht bestätigt. Vosk 0.3.45 bereinigt seine Feature-Pipeline periodisch
([Originalcode, CleanUp](https://github.com/alphacep/vosk-api/blob/v0.3.45/src/recognizer.cc#L136)).
Ob die eine verpasste Aktivierung genau an einer Bereinigungsgrenze liegt, ist
eine Hypothese, kein nachgewiesener Fehlergrund.

Ein [isolierter Vergleich mit häufigerer Neuinitialisierung](continuous-experiment-not-shipped.json)
senkte den Speicherstand auf etwa 178 MB, hatte aber ebenfalls einen Fehlversuch
(Zyklus 545). Diese experimentelle Änderung wird **nicht ausgeliefert**. Der
Produktionsdetektor und seine Konfidenzschwellen bleiben unverändert.

Ein separater [730-Segment-Diagnoselauf](missed-activation-diagnosis.json)
reproduzierte den Fehler wieder in Zyklus 725. Der Decoder lieferte dort
`[unk] rain` statt `hey brain`. Es war somit keine hängen gebliebene App-Sperre
oder lediglich eine zu streng gefilterte korrekte Phrase. Ein Absenken der
Konfidenzschwelle behebt diesen Befund nicht. Der konkrete Zusammenhang mit der
internen Pipeline-Bereinigung bleibt weiter zu prüfen; eine automatische
Aktivierung auf „rain“ wird ausdrücklich nicht ergänzt.

## Bestehende Geräte und Kunden-Image

Nur App-Code in bereits zugelassenen `services/`-Dateien und Versionsstand
ändern sich. Keine neuen Pakete, Modelle, Firmware, Einstellungen oder
Datenmigrationen. Die neue Fortschrittsmeldung gehört zum internen Protokoll
zwischen Eltern- und Kindprozess und wird gemeinsam im App-Paket ausgeliefert.

Ein frisches Kunden-Image aus diesem Quellstand übernimmt den Code automatisch.
Das bereits gebaute SD-Image 0.5.44 bleibt unverändert. Der separate temporäre
24-Stunden-Beobachter wird weiterhin nicht automatisch in Kunden-Images oder
App-Updates aktiviert. Kein neuer Browser-Watchdog und kein automatischer
Pi-Neustart werden mit diesem Stand eingeschaltet.
