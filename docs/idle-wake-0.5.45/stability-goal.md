# Arbeitsziel: belastbare Hey-Brain-Bereitschaft

Expliziter Nutzerauftrag vom 15. Oktober 2026: nicht bei einem guten Einzeltest
aufhören, sondern lange Standzeit, Doppelnennungen und Störungen systematisch
prüfen und Fehler beheben. Das Codex-Ziel bleibt bis zur Abnahme aktiv.

## Abnahmeplan

- **24 Stunden echte Standzeit:** der produktive Pi sammelt ab 15.10.2026,
  16:14:14 Europe/Berlin bis 16.10.2026, 16:14:14 technische Messwerte. Erwartet
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

- 0.5.45 auf dem Pi; realer Nutzer bestätigt sofortige Aktivierung. Ein reales
  Gespräch endete laut technischem Log per `voice_command`.
- Standalone-Messdienst aktiv, begrenzt auf 24 Stunden und niedrige Ressourcen.
  Kurzer Pi-Test bestätigt echte Prozesszuordnung und automatische Beendigung.
- Elf gezielte Monitoring-Tests bestanden. Frühere 264 Python-/104 JS-Tests
  betreffen den Stand 0.5.45; sie ersetzen den neuen Stresstest nicht.
- Langzeit-, akustische Langzeit- und neue Stressabnahme: **offen**.

App und vorhandenes SD-Image werden durch diese Diagnose nicht neu gebaut.
Jede folgende Laufzeitänderung bekommt ihre eigene App-/Image-Einflussbewertung.
