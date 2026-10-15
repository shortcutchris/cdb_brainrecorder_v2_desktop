# Hey Brain · Decoderzustand zwischen Sprachabschnitten

15. Oktober 2026. Folge des [Stabilitätsziels](../idle-wake-0.5.45/stability-goal.md).
Die 24-Stunden- und echte Acht-Stunden-Ruheabnahme sind weiterhin offen.

## Fehler und Änderung

Der bisherige Detektor überhörte im reproduzierbaren 1.000-Segment-Test den
Aufruf Nummer 725: Vosk lieferte `[unk] rain`. Die App war nicht blockiert.
Eine Erneuerung nur alle fünf Audiominuten beseitigte den Fehler nicht.
[Unveränderte Vorher-Nachweise](../wake-stability-0.5.46/README.md).

0.5.49 erneuert den Decoder nach jedem abgeschlossenen **nichtleeren**
Sprachsegment. Das akustische Modell bleibt geladen. Unvollständige Segmente
werden weiter verarbeitet; leere Ergebnisse während Stille lösen keine
Neuanlage aus. Grammatik, Mindestkonfidenzen und Audioreservierung bleiben gleich.
Damit wird der Fehler im bekannten Korpus beseitigt. Eine Garantie fehlerfreier
Spracherkennung in beliebigem Raum oder bei jedem Sprecher folgt daraus nicht.

Die alternative Erneuerung auch nach leeren Segmenten bestand ebenfalls, baut
aber bei Stille unnötig neue Decoder. Sie bleibt nur als Diagnoseoption in
`python -m scripts.check_wake_stream --endpoint-refresh-experiment` erhalten.

## Prüfung auf dem Pi

- [287 Python-Tests](python-tests.txt) bestanden, einschließlich konkurrierender
  Reservierungen, Doppelnennung, langsamer Cloud-Heartbeats, später Fehler und
  eines neuen Tests für geteilte Wörter, abgeschlossene Hintergrundsprache und
  Stille ohne wiederholtes Modellladen. Keine zusätzlichen JS-Änderungen.
- [28 synthetische Sprachfälle](acoustic-corpus.json) bestanden: verschiedene
  Stimmen, wiederholte Aktivierung und ähnlich klingende Negativbeispiele.
- [1.000 kontinuierliche Abschnitte](continuous-after.json): 500 positive und
  500 negative Fälle korrekt; kein Fehlalarm und kein überhörter Aufruf. Die
  Datei enthält den SHA256 des tatsächlich geprüften Detektor-Quelltexts.
  RSS 156,44 → 157,97 MB statt zuvor ungefähr 197 MB. 197,70 CPU-Sekunden für
  3.332,41 Audiosekunden, also etwa 5,93 % eines Kerns bei Echtzeitdurchsatz.
- [Eine Stunde periodischer Hintergrundsprache](background-after.json):
  keine Aktivierung vor dem Zielwort; anschließendes „Hey Brain“ nach 1,65
  Audiosekunden erkannt, RSS am Ende 159,69 MB. [Vorher](background-before.json)
  und [Alternative mit Erneuerung aller Segmente](background-all-endpoints.json)
  sind ebenfalls abgelegt. Diese Läufe verwenden synthetische Audiozeit und
  ersetzen keine reale Standzeit.
- [Zwei native CDB-Gespräche](native-cycles.json) bestanden, einschließlich
  Token-Erneuerung, Doppelnennung, Hallo-Begrüßung, Eingangs-/Ausgangspegel und
  sprachlichem Beenden. Die Prüfsummen der nichtstummen PCM-Blöcke stimmen am
  Ein-/Ausgang des lokalen Audiopuffers jeweils überein. Keine echten Mikrofone
  oder Lautsprecher geöffnet; nur synthetische Daten in `staging_playground`.

Die nativen Runden liefen neben mehreren CPU-Laborprozessen. Kalter Detektorstart
bis Aktivierung dauerte 4,67/5,29 Sekunden; Reservierung 0,32/0,34 ms;
Begrüßung ab künstlichem Quellenstart 10,97/9,14 Sekunden. Das ist ausdrücklich
**kein Leerlauf-Latenzwert**. CPU-Zeiten verschiedener früherer Läufe unter
unterschiedlicher Nebenlast sind kein sauberer Energie- oder Geschwindigkeits-
Vergleich. Belegt sind der gemessene Speicherbedarf und die Ergebnisse innerhalb
der jeweiligen Testbedingungen. Der Pi meldete bei einer Laststichprobe keine
Drosselung (`throttled=0x0`).

Der ältere unvollständige Cloud-Ende-Satz bleibt im Bericht sichtbar. Drei
vorherige und diese zwei instrumentierten Wiederholungen bestanden, beweisen
aber keine Ursache für den nicht instrumentierten Fehlversuch. Unvollständige
Satzanfänge lösen weiterhin kein Abschalten aus.

## Auslieferung und Image-Einfluss

Nur `services/wake_phrase.py` und die App-Version ändern sich produktiv. Keine
neuen Pakete, Modelle, Firmware, Datenformate oder Kundeneinstellungen. Bestehende
Geräte erhalten den Code über das signierte App-Paket unter atomarer
Wartungsreservierung. Ein zukünftiges Kunden-Image übernimmt ihn automatisch
aus der vorhandenen App-Positivliste. Das bereits gebaute Image 0.5.44 wird durch
dieses Commit nicht verändert; Laborprogramme werden nicht mitaktiviert.

Vor der produktiven Langzeitabnahme sind Paketinstallation, unveränderte
Einstellungen, API-/HTML-Version, laufender Detektor im aktiven Release und der
echte Touchbildschirm erneut zu prüfen. Die bisherige Beobachtung bleibt als
Vorläufer erhalten. Kein automatischer Browser-, Backend- oder Pi-Neustart
wird eingeschaltet.
