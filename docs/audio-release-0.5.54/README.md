# Audiofreigabe erst nach bestätigtem Beenden · 0.5.54

15. Oktober 2026. Im isolierten Fehleraudit von `fddfb50` wurden zwei
Sicherheitslücken reproduziert: Nach einem abgewiesenen Prozesssignal verlor
WakeWord die Referenz auf den noch laufenden Detektor. Nach einem Fehler beim
Schließen des nativen Live-Audios gab LiveConversation die Reservierung frei
und verwarf das Audioobjekt. Die Prüfwerte `wake_tracks_unreleased_child`,
`live_blocks_second_owner_after_close_failure` und
`live_tracks_unreleased_audio` waren jeweils `false`.

Das sind gezielt injizierte Fehler, kein Nachweis ihrer Ursache bei den früheren
natürlichen Wake-Aussetzern. Es wurden weder ein produktiver Prozess beschädigt
noch Raumaufnahmen erzeugt.

## Korrektur

- Der Wake-Prozess bleibt bis zum bestätigten Ende im Besitz der App. Bei
  fehlgeschlagenem Signal oder Timeout wird die Freigabe nach zehn Sekunden
  erneut versucht. Bis dahin werden weder Erkennungen übernommen noch neue
  Detektoren gestartet. Die normale Aufnahmesperre bleibt erhalten.
- Ein zweiter Fehler beim Aufräumen beendet die Bereitschaftsschleife nicht.
  Der Benutzer erhält einen lokalen Hinweis statt interner Fehlerdetails.
- Live bleibt bei fehlgeschlagener Audiofreigabe im gesperrten Zustand
  `closing`. Audioobjekt, Sitzungsgeneration und Reservierung bleiben erhalten;
  erst eine erfolgreiche Wiederholung gibt sie frei. Die Prüfung läuft im
  vorhandenen lokalen Überwachungsthread mit fünf Sekunden Wiederholabstand.
- Native Audio unterscheidet jetzt „Stopp angefordert“ von „Ressourcen
  vollständig geschlossen“. Die Eingabe wird sofort stummgeschaltet. Bei einem
  fehlgeschlagenen Aufräumen bleibt die Ereignisschleife für den nächsten Versuch
  verfügbar. Ein gesetztes Stopp-Flag allein zählt nicht mehr als Freigabe.

Bei einer dauerhaft nicht behebbaren Betriebssystemstörung bleibt das Gerät
sichtbar gesperrt. Ein zweiter Audiobesitzer wird nicht als Ausweg gestartet.
Diese Korrektur aktiviert keinen Browser-, Backend- oder Pi-Neustart und keinen
automatischen Wartungs-Watchdog.

## Prüfung und Grenzen

Die neuen Regressionen in `tests/test_audio_release.py` prüfen verweigerte
Signale, Timeout auch nach SIGKILL, einen echten ausschließlich vom Test
gestarteten stillen Kindprozess, verhinderte zweite Reservierung, erneute
Freigabe und eine Cloud-Schließbestätigung vor dem lokalen Abschluss.
`test_studio.py` prüft zusätzlich, dass wiederholte Freigabefehler die
Bereitschaftsschleife nicht beenden. Alle Profile und Dienste sind isoliert;
keine produktiven Zugangsdaten, Mikrofone oder Lautsprecher werden verwendet.

Die vollständigen Testläufe bestehen mit jeweils **338 Tests**: [Mac](python-tests-mac.txt)
und [Pi](python-tests-pi.txt). Die Pi-Prüfung läuft aus einem separaten
Testverzeichnis; die produktive App bleibt währenddessen unverändert. Die
anschließende sichere Auslieferung wird separat belegt.
Eine echte dauerhafte Kernelblockade wird nicht erzeugt. Die Tests belegen
die lokale Reservierungslogik, keine fehlerfreie Hardware unter allen Bedingungen.

## App-Update und Kunden-Image

Geändert werden die vorhandenen Dateien `services/wake_word.py`,
`services/live_audio.py`, `services/live_conversation.py` und `web_server.py`.
Keine neue Abhängigkeit, Firmware, Berechtigung, Datenmigration, Audioauswahl
oder Modellkonfiguration. Alle Laufzeitdateien gehören bereits zur App-
Positivliste. Ein neues Kunden-Image übernimmt sie aus dem ausgewählten Commit;
das vorhandene Image 0.5.44 bleibt unverändert. Testdateien und Berichte sind
keine zusätzlichen Produktdienste.

Die laufende Beobachtung von 0.5.53 wird nicht als Prüfung von 0.5.54 ausgegeben.
Nach einer bestätigten Auslieferung ist für die neue Version eine eigene
24-Stunden-Beobachtung nötig; der bisherige Teilbericht bleibt erhalten.
