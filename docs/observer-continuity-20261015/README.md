# Durchgehende Ruhezeit korrekt beobachten

**Aktueller Lauf:** Der jeweils verbindliche Messplan steht im
[Stabilitätsziel](../idle-wake-0.5.45/stability-goal.md) und auf dem Pi in `run/plan.json`.
Die hier beschriebenen früheren Läufe sind als Teilberichte archiviert.
Der Beobachter selbst und Revision 2 bleiben unverändert.

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
[Installationsbeleg](deployment.json): App-Prozess und Browsergeneration vor
und nach der Umstellung identisch; produktiv weiterhin 0.5.53 mit Okay KAI.
Der korrigierte Beobachter stammt aus `2b24da5`, Revision der Ruhezeitevidenz 2.
Der neue Lauf reicht vom **15.10.2026, 20:01:48 Uhr bis 16.10.2026,
20:01:48 Uhr Europe/Berlin**; `plan.json` bleibt maßgeblich. Die vorherigen
rund 23 Minuten sind unter `baseline-053-pre-continuity` erhalten und als
abgelöst gekennzeichnet. [Teilbericht](previous-partial-observation.json),
kein bestandener 24h-Lauf. Keine automatische Reparaturfunktion aktiviert.

Die bestehende automatische Nachprüfung bleibt alle 15 Minuten aktiv und ist
bis **16.10.2026, 21:00 Uhr Europe/Berlin** begrenzt. Damit liegt auch nach dem
verschobenen Messende noch Zeit für die Abschlussauswertung. Die frühere feste
Anzahl von 101 Wiederholungen wurde durch dieses ausdrückliche Enddatum ersetzt,
damit ihre ursprüngliche Startzeit den Folgecheck nicht vorzeitig abschneidet.
Nach erfolgter Auswertung soll die Automation bereits vor diesem Limit pausieren;
unveränderte Zwischenstände bleiben ohne Benachrichtigung. Das Ablaufdatum der
Automation ist kein Nachweis eines bestandenen Tests.

## Browser-Leerlauf: eingegrenzter Prüfpunkt

Die Sichtprüfung des Codes zeigt: Die schnelle Live-Audioabfrage in
`studio/live.js` kehrt bei geschlossenem View, verborgenem Dokument oder
inaktivem Gespräch vor der Netzabfrage zurück. Der feste Wake-Statuspoll in
`studio/device-status.js` schreibt hingegen auch unveränderte Titel, Hinweise
und `hidden`-Werte. Eine isolierte Ausführung desselben Codes im bestehenden
JavaScript-Testharness bestätigt bei 60 identischen Idle-Antworten 120 Text-
und 120 `hidden`-Zuweisungen. [Messprotokoll](idle-status-write-probe.json).

Diese beschleunigte Prüfung zählt Zuweisungen an simulierte Elemente, keine
echten Browser-Layouts, keine CPU-Ersparnis und keinen Speicherverlust. Die
globale Mutation-Beobachtung in `studio/touch.js` macht unnötige Aktualisierungen
zu einem sinnvollen Kandidaten für eine spätere Browser-Profilierung. Sie
beweist nicht die Ursache des bislang leichten RSS-Anstiegs. Keine Änderung
am App-Code oder am Pi nur aufgrund dieser Vermutung; zunächst die längerfristige
Speicherkurve und mögliche Warnungen des laufenden Tests abwarten.
