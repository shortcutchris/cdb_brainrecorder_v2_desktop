# Okay Nabu wiederherstellen · 0.5.59

16.10.2026. Nutzerwunsch: von Hey KAI zurück zum ursprünglichen Nabu-Rufwort.
Die genaue Phrase lautet **Okay Nabu**, nicht Nabu allein. Dies ist ein eigenes
microWakeWord-Modell, keine neue Vosk-Grammatik und keine umbenannte Kai-Erkennung.

## Umsetzung und Schutz

`services/wake_detectors.py` wählt anhand der gespeicherten Phrase genau eine
Engine. Nabu nutzt `MicroWakeWord.from_builtin(Model.OKAY_NABU)` mit unveränderten
Herstellerparametern. Die 50-ms-Audioblöcke werden vollständig in fünf 10-ms-Stücken
verarbeitet; ein Treffer überspringt keine verbleibenden Features. Die bestehende
Kindprozesssteuerung beendet den Listener nach der ersten Meldung und verwirft
doppelte Meldungen. Kein zweites Mikrofon, kein Browser-Mikrofon, keine stille
Rückfalloption auf Vosk. Der Modellstart erfolgt im Kindprozess außerhalb der
Aufnahme-Sperre. Nabu erzeugt keine Text-/Wortkonfidenzdiagnose, nur angenommene
Treffer und technische Audiopegel. Fehlende Engine blockiert die Freigabe.

Die Audioreservierung, Aufnahme-/Pausen-/Gesprächssperren, zeitliche Begrenzung,
Kontobindung und Rückkehr nach Gesprächsende bleiben erhalten. In Einstellungen
steht „Okay Nabu“ als eigene Auswahl. Gespeicherte Brain-/KAI-Auswahlen werden
nicht automatisch migriert. Auf Chris' Pi wird Nabu nach geprüftem Update
bewusst über die App-API gewählt; kein Zurücksetzen des Kontos oder der Aufnahmen.

## Tests

- 43 fokussierte lokale Tests bestanden, einschließlich neuer Nabu-Frameprüfung,
  fehlender Runtime, Engine-Auswahl, Persistenz, bestehender Konten, Sperren und
  Image-Export-Positivliste.
- Dateitest auf dem echten Pi: 3/3 offizielle Okay-Nabu-Dateien erkannt, 0/9
  fremde Rufwortdateien angenommen. 100/100 erneuerte Erkennungszyklen bestanden.
- Zehn beschleunigte Audiominuten digitale Stille ohne Aktivierung; folgender
  Referenzruf erkannt. Rund 2,85 CPU-Sekunden, maximal 38.496 KiB Prozess-RSS
  im Gesamttest. Kein Mikrofonzugriff, kein Lautsprecher, kein Cloud-Gespräch.
- Diese Referenzen und Wiederholungen sind kein realer Raum-, Stimmen-, Rausch-
  oder Acht-Stunden-Test. Ob der erste natürliche Ruf zuverlässig reagiert,
  bleibt mit dem Benutzer zu prüfen. Nabu wird nicht pauschal als bestes Wort bewertet.
- Pi-Gesamtlauf: 386 Tests, 383 bestanden; drei Fehler wegen fehlendem altem
  Qt-UI-Ordner im isolierten Testpaket. Nach Ergänzung des unveränderten Ordners
  alle zehn nativen Tests bestanden, einschließlich der drei zuvor blockierten.
  Somit alle 386 unterschiedlichen Tests erfolgreich geprüft; kein behaupteter
  fehlerfreier erster Gesamtlauf. Der bekannte abgefangene Latin-1-Ausgabefehler
  des Qt-Übersetzers bleibt im Nachtestprotokoll sichtbar.
- 111 JavaScript-Tests bestanden. [Erster Pi-Lauf](python-tests-pi-first.txt),
  [korrigierter nativer Nachtest](native-tests-pi.txt),
  [lokale fokussierte Tests](focused-tests-mac.txt), [JavaScript](js-tests.txt).

[Dateimesswerte](model-benchmark-pi.json). Reproduktion:
`PYTHONPATH=. python scripts/check_wake_nabu.py --references PFAD_ZU_UPSTREAM/tests --output AUSGABE.json`.
Upstream-Fixtures stammen aus Commit `333da550c54b95192af472cfe37d98dab2f2086e`
des [offiziellen Python-Projekts](https://github.com/OHF-Voice/pymicro-wakeword).
Referenzdateien werden nicht in das Kundenpaket kopiert; ihre SHA256 stehen im Bericht.

## Bestehender Pi und neue Images

Auf diesem Pi sind `pymicro-wakeword==2.5.0` und `pymicro-features==2.0.2` aus
der ursprünglichen Nabu-Installation bereits vorhanden. Die Runtime wird nicht
neu installiert oder verändert; Paketfingerprint wird vor dem signierten
Code-Update gegen den Verwaltungsagenten geprüft. Andere Geräte ohne diese
Pakete brauchen zuerst eine qualifizierte Runtime-Installation; das App-Paket
führt keine Paketinstallation aus und behauptet keine solche Kompatibilität.

`requirements-wake.txt` enthält beide Pins zusätzlich zu Vosk. Der Kunden-Image-
Export übernimmt diese Datei und die neue Engine-Datei; die Factory-Installation
installiert nun ausdrücklich diese Anforderungen. Das neue optionale Nabu-Modell
ist im Runtime-Paket enthalten. Unverändert: keine Konten, Aufzeichnungen,
WLAN-/SSH-/Signierschlüssel im Image; neuer Kunde beginnt ohne Wake-Freigabe.
Das bestehende SD-Image 0.5.44 wird nicht verändert. Ein Export ist kein neu
gebautes oder gebootetes Image. Die neue Factory-Runtime muss beim nächsten
vollständigen Image-Build und Hardwaretest erneut qualifiziert werden.

Der vorherige KAI-Lauf darf nach dem Engine-/Versionswechsel nicht als
abgeschlossener 24h-Nabu-Nachweis gelten. Er wird als Teilmessung erhalten.
Automatische Reparaturen bleiben ausgeschaltet; das langfristige Stabilitätsziel
wird durch diesen Wortwechsel nicht als abgeschlossen markiert.
