# Verbindungsfehler sauber abschließen · 0.5.50

15. Oktober 2026. [Stabilitätsziel](../idle-wake-0.5.45/stability-goal.md),
[vorherige Decoder-Korrektur und Sprachtests](../wake-stability-0.5.49/README.md).

## Reproduzierte Randfälle

Beim Nachweis der Netzwerk-Ausfälle fanden sich zwei Fehler in der Rückmeldung:
Nach ausgeschöpften Ereignisstrom-Wiederholungen wurde die gesetzte Fehlermeldung
beim Freigeben durch einen normalen Ende-Zustand ersetzt. Ein verspäteter
Audiofehler konnte außerdem noch während eines gewollten Schließens eine
Fehlermeldung setzen. [Beide neuen Regressionstests scheiterten vorher](faults-before.txt).

Die endgültige Freigabe bewahrt jetzt eine bereits gesetzte lokale Fehlermeldung,
auch wenn die Bestätigung des Cloud-Schließens zuerst eintrifft. Ein fehlgeschlagener
Heartbeat erhält ebenfalls einen verständlichen lokalen Hinweis; Anbieterdetails
werden nicht ausgegeben. Audio- und erschöpfte Netzwerk-Rückmeldungen dürfen
einen bereits gewollten Abbruch nicht nachträglich zum Fehler machen. Alle
Rückmeldungen bleiben an ihre Sitzungsgeneration gebunden. Beim nächsten Start
wird die alte Fehlermeldung zurückgesetzt.

Das ändert weder Retry-Anzahl noch Netzwerk-Timeouts und behauptet keine sofortige
Cloud-Freigabe bei unbekanntem Serverzustand. Lokales Audio wird vor Freigabe der
Reservierung geschlossen. Nach Abschluss können die normalen Aktivitätsregeln
Wake-Bereitschaft und einen neuen Start wieder zulassen.

## Nachweise

- [292 Python-Tests bestanden](python-tests.txt). Die fünf zusätzlichen Fälle
  prüfen neun ausgeschöpfte Netzwerkversuche mit begrenzter Wartefolge,
  sichtbaren Fehler nach Freigabe, erneute Reservierung, späten Audiofehler
  während Abbruch, Heartbeat-Timeout, Cloud-Schließbestätigung vor lokalem
  Abschluss und Abbruch während der letzten Wiederholungswartezeit. Die
  Netzwerkfehler werden isoliert injiziert; das produktive WLAN wurde nicht
  getrennt. Qt-/DBus-Warnungen im Log sind keine fehlgeschlagenen Tests.
- [Eine weitere native CDB-Runde](native-cycle.json) mit synthetischem
  „Gespräch beenden“ bestanden: Aktivierung nach 2,45 Sekunden ab kaltem
  Quellenstart, Hallo-Begrüßung nach 6,18 Sekunden, Reservierung 0,10 ms,
  beide Audiopegel vorhanden und normaler Ende-Grund `voice_command`.
  Nichtstumme PCM-Blöcke unverändert durch den lokalen Puffer weitergegeben.
  Vorher absichtlich abgelaufener Token in privater Testkopie, anschließend
  kontrolliertes Schließen. Nur `staging_playground`, keine Raummikrofone oder
  Lautsprecher. Der normale Abschluss bleibt erfolgreich und wird nicht als
  Fehler markiert.
- Wake-Decoder, Oberfläche, Aufnahmeformat und Audioreservierung ändern sich
  gegenüber 0.5.49 nicht. Dessen Sprach-, Parallelitäts- und Auslieferungsnachweise
  bleiben dafür relevant. Historische nicht vollständig erkannte Cloud-Sätze
  bleiben dokumentiert; keine Garantie für jedes natürliche Sprachsignal.

## Auslieferung und Kunden-Image

Produktiv ändern sich `services/live_conversation.py` und die App-Version.
Keine neuen Pakete, Modelle, Berechtigungen, Firmware, Datenformate oder
Kundeneinstellungen. Bestehende Geräte erhalten ein signiertes Code-Paket unter
atomarer Wartungssperre. Ein zukünftiger Image-Build übernimmt die Dateien über
die vorhandene Positivliste; das vorhandene Image 0.5.44 wird nicht verändert.
Die temporäre Beobachtung wird nicht automatisch Teil eines Kunden-Images.

Nach erfolgreicher Installation sind API-/HTML-Version, Einstellungen,
Touchbildschirm und Wake-Bereitschaft zu prüfen. Der 24-Stunden-Lauf wird für
diesen abschließenden Code-Stand neu begonnen. Kein automatischer Browser-,
Backend- oder Pi-Neustart wird aktiviert. Echte Langzeitabnahme bleibt offen.
