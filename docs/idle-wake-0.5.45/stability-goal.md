# Arbeitsziel: belastbare Hey-Brain-Bereitschaft

Expliziter Nutzerauftrag vom 15. Oktober 2026: nicht bei einem guten Einzeltest
aufhören, sondern lange Standzeit, Doppelnennungen und Störungen systematisch
prüfen und Fehler beheben. Das Codex-Ziel bleibt bis zur Abnahme aktiv.

## Abnahmeplan

- **24 Stunden echte Standzeit:** der produktive Pi sammelt im aktuellen Lauf ab
  15.10.2026, 18:21:33 Europe/Berlin bis 16.10.2026, 18:21:33 technische Messwerte.
  Vorläufe 0.5.45–0.5.51 wurden nach Korrekturen bzw. Diagnose-Erweiterung archiviert und zählen nicht als
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
- Aktuelle Langzeitabnahme ab **17:24:13 am 15.10.: offen**. Sämtliche künstlichen
  Belastungstests sind beendet. Der beschleunigte Acht-Stunden-Stille-Vorlauf
  bestand; er ersetzt keinen echten Aufruf nach acht Stunden Ruhe.
  Kein automatischer Browser-/Backend-/Pi-Neustart. Weitere Änderungen nur bei
  neuen Fehlernachweisen; der aktuelle Stand bleibt für die Beobachtung erhalten.

0.5.50 wurde als signiertes App-Paket ausgeliefert. Das vorhandene SD-Image
0.5.44 bleibt unverändert; ein zukünftiger Image-Build übernimmt den neuen
App-Code über die bestehende Positivliste. Jede folgende Laufzeitänderung
bekommt ihre eigene App-/Image-Einflussbewertung.
