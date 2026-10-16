# Arbeitsziel: belastbare Hey-Brain-Bereitschaft

Expliziter Nutzerauftrag vom 15. Oktober 2026: nicht bei einem guten Einzeltest
aufhören, sondern lange Standzeit, Doppelnennungen und Störungen systematisch
prüfen und Fehler beheben. Das Codex-Ziel bleibt bis zur Abnahme aktiv.

## Abnahmeplan

- **24 Stunden echte Standzeit:** der produktive Pi sammelt im aktuellen Lauf ab
  16.10.2026, 08:34:20 Europe/Berlin bis 17.10.2026, 08:34:20 technische Messwerte
  für 0.5.58 mit Hey KAI. `plan.json` des Messdienstes bleibt maßgeblich.
  Vorläufe 0.5.45–0.5.52 wurden nach Korrekturen, Diagnose-Erweiterung oder dem
  ausdrücklichen Auftrag für neue Rufwörter archiviert und zählen nicht als
  bestandene Dauerläufe. Erwartet
  mindestens 99 % Messabdeckung, keine ungeklärten Neustarts, keine dauerhafte
  CPU-/Speicherwarnung und kein ungeklärter wachsender Speichertrend. Fehlende
  Abdeckung oder Reparaturen verlangen einen neuen Lauf mit dem korrigierten Stand.
- **Realer Wake nach Pause:** wenigstens ein echter Aufruf nach mindestens acht
  Stunden ohne Gespräch. Keine absichtliche nächtliche Lautsprecheraktivierung.
  Fehlt der Aufruf, bleibt der akustische Langzeitnachweis offen. Der Nutzer kann
  das Gerät normal verwenden; wir manipulieren weder Mikrofon noch Live-Gespräch.
- **Lokale Zustands-Stresstests:** mindestens 100 wiederholte Zyklen, doppelte und
  konkurrierende Aktivierungen, Abbruch während Start/Schließen, stale Events und
  Reservierung gegen Aufnahme/Pause. Kein zweiter Eigentümer und kein hängen
  bleibender Zustand. Alle Testressourcen müssen am Ende geschlossen sein.
- **Fehlerinjektion:** langsame/fehlgeschlagene Anmeldung, Cloud-Timeout,
  Audiofehler, abgestürzter oder stummer Detektor, unterbrochene Statusabfrage.
  Kontrollierte Fehlermeldung und erneuter Start möglich, keine unendliche
  Wartephase. Ein echter Netzfehler darf nicht als erfolgreiche Verbindung gelten.
- **Akustik und Cloud getrennt:** synthetische Wake-Phrasen einschließlich
  Doppelnennung und ähnlich klingender Negativbeispiele über den echten lokalen
  Detektor; native CDB-Testgespräche nur isoliert mit `staging_playground`,
  künstlichem Eingang und stummer Testausgabe. Kleine Serien statt unbeschränkter
  kostenpflichtiger Dauergespräche. Pro Test genaue Grenzen dokumentieren.
- **Bedienbarkeit/Latenz:** lokale Reservierung ohne Netzabhängigkeit; im
  Regressionstest unter 100 ms. API im ruhigen Gerät normalerweise unter 200 ms;
  p95 nach Messung auswerten. Bei gesunder Cloud Verbindung nach beobachteter
  Erkennung typischerweise innerhalb fünf Sekunden, spätestens nach 15 Sekunden
  Warnung und anschließend begrenzter Fehlerweg. Cloud-Verzögerungen separat
  ausweisen, nicht durch Grenzwertverschiebung als Erfolg umdeuten.
- **Rückkehr:** nach jedem beendeten oder fehlgeschlagenen Versuch erneute lokale
  Wake-Bereitschaft; erkannter Hinweis verschwindet, echte Pegel laufen. Keine
  Aufnahmeunterbrechung. Ein Fehler im synthetischen Ende-Transkript zählt als
  fehlgeschlagener Sprachtest, auch wenn man per API sauber schließen kann.

Diese Kriterien sind ein nachvollziehbares Arbeitsziel, keine Zusicherung einer
fehlerfreien Spracherkennung in jeder Umgebung. Änderungen an Kriterien müssen
mit Messgrund erklärt werden; Fehlversuche und Einschränkungen bleiben im Bericht.

## Vorgehen und Schutz

Erst getrennte Tests und Codeprüfung, dann gezielte Korrekturen samt Regressionen.
Keine künstliche Flut auf dem produktiven Mikrofon. CPU-intensive Laborläufe
zeitlich begrenzen und die Messreihe entsprechend markieren. Produktivdaten,
Brain-Konto, Wissensauswahl, Timer und Aufnahmen bleiben erhalten. Vor Auslieferung
die vorhandene atomare Wartungssperre verwenden, bei belegtem Gerät warten.

Der [Watchdog-Entwurf](watchdog.md) sieht zunächst ausschließlich Beobachtung vor.
Eine automatische Reparatur erfordert zusätzlich atomare Reservierung,
Entwurfsicherung, UI-Heartbeat und bestätigte Schutztests. Hohe Last allein darf
niemals einen Pi-/Backend-Neustart während einer Aufnahme auslösen.

## Fortschritt

- **0.5.58 installiert, Hey KAI bewusst ausgewählt:** Niedrige Konfidenz für
  „Kai“ am realen ReSpeaker nachgewiesen; nur Hey KAI auf 0,80/0,50 kalibriert.
  Zwei isolierte natürliche Rufe angenommen, 12/12 synthetische positive Fälle
  und 0/68 negative Fälle; drei Stimmen sind keine allgemeine Zuverlässigkeits-
  oder Langzeitabnahme. 379 Pi-Tests und 51 Studio-Tests bestehen; der Mac-
  Gesamtlauf behält einen dokumentierten Suchton-Cleanup-Fehler. Signiertes
  Update, erhaltene Einstellungen, bewusste Auswahl über App-API, 18 stabile
  Nachproben und echtes Display geprüft. Neuer Beobachterprozess 1767736 aktiv.
  Der alte 6,32-Stunden-Lauf bleibt mit Eingriffen erhalten. Produktiver Ruf,
  Begrüßung/Ende und echter Wake nach acht Stunden bleiben zu bestätigen.
  [Nachweise und Grenzen](../wake-kai-0.5.58/README.md).

- **Natürlicher Okay-KAI-Ruf am 16.10. fehlgeschlagen:** Der Benutzer meldete
  „Keine Reaktion“. Zwei Kandidaten wurden vom lokalen Detektor verworfen;
  laufender Audioeingang und gute passive Ressourcenwerte widerlegen diesen
  Fehler nicht. Die genaue Ablehnungsursache ist noch offen. Ein isoliertes,
  textfreies Diagnosewerkzeug ist vorbereitet; der Sprachtest wartet auf die
  Bereitschaft des Benutzers. Die Beobachtungsautomation kennt diesen Befund
  und darf daraus keinen bestandenen akustischen Langzeitnachweis ableiten.
  [Evidenz und Testverfahren](../wake-phrases-0.5.53/README.md#natürlicher-kai-test-fehlgeschlagen--16-oktober-2026).

- **0.5.57 installiert:** alte Live-Ereignisleser bleiben an ihre Gesprächs- und
  Kontogeneration gebunden. Der Keepalive-Fehler ist isoliert reproduziert;
  371 lokale Python-Tests, neun gezielte Pi-Tests mit 100 Reader-Wechseln und
  51 Studio-Tests nach Versionssprung bestanden. Signierte Sequenz 14, erhaltene
  Konfigurationsprüfsummen und 18 Startup-Stichproben geprüft. Die vorherige
  0.5.56-Teilmessung umfasst etwa 22 Minuten, keinen Langzeitnachweis und bleibt
  mit UI-Eingriff/Diagnoseintervallen archiviert. [Belege](../live-event-scope/README.md).
  Neuer Beobachterprozess 1488318 aktiv. Kein Browser-Neustart und keine
  automatische Reparatur; verbleibende Browserlast und natürlicher KAI-Wake
  nach mindestens acht Stunden bleiben offen.

- 0.5.45: realer Nutzer bestätigt sofortige Aktivierung. Ein reales
  Gespräch endete laut technischem Log per `voice_command`.
- Standalone-Messdienst aktiv, begrenzt auf 24 Stunden und niedrige Ressourcen.
  Kurzer Pi-Test bestätigt echte Prozesszuordnung und automatische Beendigung.
- Inzwischen 0.5.48 produktiv; fünf weitere Fehlerfälle behoben (Detektorfortschritt,
  Teilzeile, Cloud-Heartbeat, späte Fehler, Kindprozess-Pfad), außerdem die bei
  der Installation entdeckte UI-Reload-Schleife beseitigt und am Display geprüft.
- 285 vollständige Python-Tests auf 0.5.47; nach der UI-Korrektur weitere 48
  Studio-Tests und 107 JS-Tests bestanden. 13 Monitoring-Tests bestanden.
- 100 konkurrierende Reservierungsrunden und 100 Doppelnennungen ohne doppelte
  Audioreservierung; 28/28 synthetische Sprachfälle korrekt. In fünf nativen
  CDB-Runden 5/5 Aktivierungen/Begrüßungen, aber nur 4/5 Ende-Befehle vollständig
  transkribiert. Im erweiterten kontinuierlichen 1.000-Segment-Test ein
  Erkennungsfehler; Speicherplateau statt ungebremstem Wachstum. Der experimentelle
  Reset verbessert die Erkennung nicht und wurde nicht übernommen.
- Historischer Befund vor 0.5.49: Langzeit- und akustische Langzeitabnahme sowie
  beide Sprachfehler offen. [Details und Rohmesswerte](../wake-stability-0.5.46/README.md).
- Weitere Eingrenzung: drei zusätzliche native Runden bestanden; eine
  Audio-Prüfsumme bestätigt jeweils die vollständige lokale Weitergabe des
  synthetischen Ende-Satzes. Der alte Fehlversuch bleibt dokumentiert.
  Ein isolierter Decoder-Vergleich nach abgeschlossenen Segmenten bestand
  1.000/1.000 Fälle und den separaten 28-Fälle-Korpus bei geringerem RAM-Bedarf.
  Ressourcen bei Stille und längere Hintergrundsprache werden noch verglichen;
  die experimentelle Variante ist nicht produktiv installiert.

- **0.5.49 installiert:** Erneuerung nach nichtleeren abgeschlossenen
  Sprachsegmenten, keine wiederholte Neuanlage bei Stille. 287 Python-Tests,
  1.000/1.000 kontinuierliche Abschnitte, 28 Sprachfälle, eine Stunde synthetische
  Hintergrundsprache und zwei weitere native CDB-Runden bestanden. Insgesamt
  fünf instrumentierte CDB-Folgerunden erfolgreich; der alte unvollständige
  Cloud-Satz bleibt als nicht abschließend erklärter Fehlversuch dokumentiert.
  Der reproduzierbare Decoder-Aussetzer ist im identischen langen Korpus
  beseitigt. Signierte Installation, erhaltene Einstellungen, API-/HTML-Version,
  tatsächlicher Detektor-Quelltext und Touchbildschirm geprüft.
  [Nachweise](../wake-stability-0.5.49/README.md).
- **0.5.50 installiert:** Fehler bleiben beim Freigeben sichtbar, verspätete
  Rückmeldungen verfälschen keinen gewollten Abbruch. 292 Python-Tests und eine
  weitere instrumentierte native Runde mit „Gespräch beenden“ bestanden.
  Einstellungen, API-/HTML-Version, Startphase und echte Oberfläche geprüft.
  [Nachweise und offene Abnahmepunkte](../wake-stability-0.5.50/README.md).
- Historischer 0.5.50-Lauf ab **17:24:13 am 15.10.: inzwischen abgelöst**. Sämtliche künstlichen
  Belastungstests sind beendet. Der beschleunigte Acht-Stunden-Stille-Vorlauf
  bestand; er ersetzt keinen echten Aufruf nach acht Stunden Ruhe.
  Kein automatischer Browser-/Backend-/Pi-Neustart. Weitere Änderungen nur bei
  neuen Fehlernachweisen; der aktuelle Stand bleibt für die Beobachtung erhalten.

0.5.50 wurde als signiertes App-Paket ausgeliefert. Das vorhandene SD-Image
0.5.44 bleibt unverändert; ein zukünftiger Image-Build übernimmt den neuen
App-Code über die bestehende Positivliste. Jede folgende Laufzeitänderung
bekommt ihre eigene App-/Image-Einflussbewertung.

- **0.5.52 installiert:** Nach der Diagnose in 0.5.51 wurde ein reproduzierbarer
  Erkennungsfehler bei sehr leisem Grundrauschen korrigiert. 315 Python-Tests und
  28 Sprachfälle bestanden; Rauschvergleich 8/12 statt 6/12, vier extreme
  Kombinationen weiterhin nicht erkannt. Die tatsächliche Ursache der früheren
  Nutzer-Aussetzer bleibt damit nicht rückwirkend bewiesen. Aktuelle Auslieferung,
  Grenzen und der neue unveränderliche Lauf vom 15.10. 18:21:33 bis 16.10.
  18:21:33 sind im [0.5.52-Bericht](../wake-stability-0.5.52/README.md) dokumentiert.
  Langzeitabnahme und echter Wake nach acht Stunden sind weiterhin offen.

- **0.5.53 installiert:** Hey KAI und Okay KAI sind als Testvarianten auswählbar;
  aktuell hört der Pi auf Okay KAI. [Prüfbericht](../wake-phrases-0.5.53/README.md)
  mit 320 bestandenen Python-Tests auf dem Pi, 108 JS-Tests und den Grenzen der
  Akustikprüfung. Der Dateikorpus erfüllt 107/108 Anwesenheitsprüfungen, aber nur
  105/108 genaue Erkennungszählungen. Die neue Raumwiedergabe erkannte beide
  KAI-Varianten noch nicht; ein natürlicher Nutzertest steht aus. Die neue
  24h-Messung darf diese offenen Erkennungsprobleme nicht als gelöst darstellen.
  Der Beobachter erfasst die Phrase und übernimmt Ruhezeiten nicht über einen
  Rufwortwechsel hinweg. Der frühere 0.5.52-Lauf ist nach etwa 67 Minuten abgelöst.

- **Beobachterkorrektur bei unveränderter App 0.5.53:** Abfragefehler,
  unbeobachtete Lücken und Prozesswechsel unterbrechen jetzt den Nachweis
  durchgehender Ruhe. 33 Tests lokal und auf dem Pi bestanden; App und Browser
  wurden nicht neu gestartet. Die vorherige 23-Minuten-Beobachtung bleibt
  erhalten, der korrigierte Lauf beginnt am 15.10. um 20:01:48.
  [Fehlernachweis, Installation und Grenzen](../observer-continuity-20261015/README.md).

- **0.5.54 installiert:** Die zusätzliche Fehlerprüfung zeigte einen Verlust
  der Audioreservierung bei fehlgeschlagenem Prozess-/Audioabschluss. Besitzer
  bleiben jetzt bis zum bestätigten Ende erhalten; kontrollierte Wiederholungen
  geben erst danach frei. Je 338 Tests auf Mac und Pi bestanden, signiertes
  Update unter Wartungssperre und Quelltext-Hashes geprüft. Der frühere Lauf
  von etwa 55 Minuten liegt unter `baseline-053-before-audio-release-fix`.
  Neuer Lauf ab 15.10., 20:56:47; keine Änderung am Rufwort, Modell oder den
  Erkennungsschwellen. [Nachweise und offene Punkte](../audio-release-0.5.54/README.md).

- **0.5.55 installiert:** Im lokalen Browservergleich nachgewiesene redundante
  DOM-Schreibvorgänge für Wake-Anzeigen und Pager-Beschriftungen entfernt.
  340 Python-Tests, 110 JS-Tests und 1.400 synthetische Zustandsvergleiche auf
  dem Mac bestanden. Signiertes Update, erhaltene Einstellungen, Quelltext-Hashes,
  18 Startstichproben und echtes Display geprüft. Der rund 85-minütige Vorlauf
  bleibt unter `baseline-054-before-idle-render-fix` erhalten. Neuer Lauf ab
  15.10., 22:21:44; noch keine behauptete Pi-Speicherverbesserung oder vollständige
  Langzeitabnahme. [Nachweise](../idle-render-0.5.55/README.md).

- **0.5.56 installiert:** Identische SVG-Quellen des versteckten Testplayers
  werden nicht mehr neu zugewiesen. Der quellengeprüfte Pi-Kurzvergleich zeigt
  konstante interne Dokumentzahl und geringeren Renderer-Zuwachs; ungültige
  Vorläufe mit fehlerhaftem Diagnosecode bleiben ausdrücklich verworfen.
  354 Python-/111 JS-Tests, erneute 51 Studio-Tests nach Versionssprung und acht
  neue Diagnosevalidierungen bestanden. Signiertes Paket Sequenz 13,
  Konfigurationshashes und 18 Bereitschaftsstichproben bestätigt. Der bisherige
  0.5.55-Lauf ist nach rund 3,53 Stunden einschließlich Updateübergang archiviert.
  Neuer echter 24h-Lauf gestartet, kein Browser-/Pi-Neustart und kein akustischer
  Test. Die Langzeit-/Acht-Stunden-Abnahme bleibt offen.
  [Nachweise](../idle-icon-0.5.56/README.md).
