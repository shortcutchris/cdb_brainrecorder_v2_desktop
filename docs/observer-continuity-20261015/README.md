# Durchgehende Ruhezeit korrekt beobachten

15.10.2026. Drei neue Regressionen schlugen im bisherigen Beobachter fehl:
ein einzelner Abfragefehler, ein gewechselter Backend-/Wake-Kontext und eine
lange unbeobachtete Lücke konnten die frühere Ruhezeit bis zum nächsten Ruf
weitertragen. Der alte Zähler allein ist deshalb kein belastbarer Acht-Stunden-
Nachweis. Es gab im aktuellen Lauf bislang keinen als erfolgreich gewerteten
Langzeitaufruf; frühere Zeitreihen bleiben historische Beobachtungen.

Die Korrektur setzt die Ruhezeit bei diesen Unterbrechungen zurück. Mehr als
fünf Sekunden zwischen erfolgreichen Abfragen oder ein rückwärts laufender
Zeitstempel unterbrechen den Nachweis. Bereits der erste Abfragefehler wird
als technisches `observation_gap` ohne Antwortinhalt protokolliert. Lücken
während eines Wake-Starts markieren auch dessen Latenzmessung als unvollständig.
Die Auswertung lässt solche Starts und alte Ruhezeitzähler nicht als erfüllten
Acht-Stunden-Test gelten. Die bisherige Prüfung der allgemeinen Messabdeckung
bleibt separat erhalten.

**33 Tests lokal und auf dem Pi bestanden**, einschließlich fünf neuer
Regressionen. [Pi-Protokoll](pi-tests.txt). Die Prüfungen verwenden simulierte
Zustände; sie öffnen kein Mikrofon und starten keine Cloud-Sitzung. Der normale
Latenztest liefert nun regelmäßig simulierte Beobachtungen statt eines Sprungs
über eine unbeobachtete Stunde.

## Auslieferung und Image

Nur der separat installierte, rein lesende Beobachter und seine Offline-
Auswertung ändern sich. Keine App-Version, Runtime-Abhängigkeit, Firmware,
Audioeinstellung oder App-/Browser-Neustart. Der Beobachter ist kein Bestandteil
des Kunden-Images; für das bestehende App-Paket und neue Kunden-Images entsteht
keine Änderung. Vorlauf erhalten und die 24h-Beobachtung mit dem korrigierten
Werkzeug neu beginnen; diese zusätzlichen Minuten ersetzen keine echte Standzeit.
Installationsbeleg und neue Messzeiten werden nach der Prüfung ergänzt.
