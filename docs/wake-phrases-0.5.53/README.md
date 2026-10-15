# 0.5.53 – Rufwörter zum Vergleichen

Unter **Einstellungen → Audio → Aktivierungswort** stehen „Hey Brain“,
„Hey KAI · Test“ und „Okay KAI · Test“ zur Wahl. KAI wird wie der Name Kai
und nicht als einzelne Buchstaben gesprochen. Vor einem Wechsel Erkennung
und lokalen Test ausschalten. Die Wahl wird sofort gespeichert. Aufnahme,
pausierte Aufnahme, Gespräch und Wartung sperren den Wechsel auch in der API.

**Erkennung testen** hört für 30 Sekunden lokal zu und zeigt die Zahl der
Erkennungen; es startet kein Cloud-Gespräch. Für den normalen Betrieb mit
gewähltem Brain-Konto und Wissen **Aktivierungswort einschalten** wählen.
Status auf der Startseite, Bereitschaft und Erkennungshinweis nennen das
gewählte Wort. „Gespräch beenden“ bleibt unverändert.

## Bestehende Installation und neues Image

Alte Konfigurationen ohne `phrase` verwenden weiterhin Hey Brain; der bestehende
Ein-/Aus-Zustand und die Kontobindung bleiben erhalten. Eine unbekannte gespeicherte
Phrase wird sicher ausgeschaltet. Neue Profile starten ausgeschaltet mit Hey Brain.
Abmelden hebt wie bisher die Aktivierung auf, behält aber die Rufwortauswahl.
Es gibt keine neue Runtime, Abhängigkeit, Firmware oder Modellinstallation.
Die App-Dateien liegen in der bestehenden Positivliste. Künftige saubere SD-Images
übernehmen sie; das bereits gebaute Image 0.5.44 wird nicht ersetzt. Teststimmen
und Testskripte sind keine App-Paketdateien.

## Erkennung und Schutz

Nur das ausgewählte Profil aktiviert. Konkurrierende ähnliche Phrasen bleiben
in der Grammatik, Konfidenzen 0,8/0,9 und Dauerprüfung bleiben unverändert.
„OK“ wird nicht zusätzlich zu „Okay“ in dieselbe Grammatik aufgenommen: dieselbe
Aussprache teilte im Vorversuch die Wortkonfidenz auf etwa 0,5 auf. Kein neues
Modell wird trainiert; Kai und Okay sind im vorhandenen Modellwortschatz enthalten.
Der Kindprozess erhält die ausgewählte Profil-ID ausdrücklich. Test-/Profilwechsel
erneuern den Feedback-Zähler-Kontext, damit alte Erkennungshinweise nicht wieder
erscheinen. Es entsteht kein zweiter Mikrofonbesitzer.

## Prüfungen und Grenzen

- **320 Python-Tests auf dem Pi bestanden**, einschließlich HTTP-Sperren,
  Einstellungen-Migration, ausgewähltem Kindprozessprofil und Doppelnennungen.
  [Vollständiges Protokoll](python-tests-pi.txt). Der Lauf meldete anschließend
  einen vorhandenen GC-Hinweis sowie eine Locale-Warnung des Übersetzungsladers.
- **108 JavaScript-Tests bestanden**, inklusive Auswahl, Speicherung und Sperren.
  [Protokoll](javascript-tests.txt). Touch-Auswahl in der laufenden lokalen
  Vorschau bei 1280 × 720 geöffnet und Okay KAI ausgewählt; feste Leisten erhalten.
- Zusätzlich 28 Beobachter-/Auswertungstests lokal bestanden. Der Beobachter
  erfasst die Phrase, setzt die Ruhezeit bei deren Wechsel zurück und kennzeichnet
  gemischte Rufwörter als prüfpflichtigen Lauf.
- Ein zusätzlicher vollständiger Mac-Lauf hatte einen reproduzierbaren
  `PermissionError` beim Beenden eines Suchton-Testprozesses. Er wird nicht als
  bestanden gezählt; der Linux/Pi-Lauf desselben App-Codes bestand. Kein neuer
  Mac-Shutdown-Fix gehört zu dieser Auslieferung. [Mac-Protokoll](python-tests-mac.txt).

### Dateien durch den echten Pi-Decoder

[108 Dateifälle](pi-file-comparison.json), Vosk 0.3.45 auf dem Pi, ein künstlicher
Sprecher, Einzel-/Doppelruf und Faktoren 1/0,3/0,03. Kein Lautsprecher und kein
Mikrofon in diesem Test. 107/108 Erwartungen erfüllt:

| Profil | Positive Varianten erkannt | Fehlaktivierungen bei Gegenbeispielen |
| --- | --- | --- |
| Hey Brain | 6/6 | 0/30 |
| Hey KAI | 5/6 | 0/30 |
| Okay KAI | 6/6 | 0/30 |

Der übersehene Hey-KAI-Einzelruf war auf 3 % Amplitude abgesenkt. Keine breite
Qualitätsquote: Pegel-/Wiederholungsvarianten derselben Stimme sind keine
unabhängigen Nutzerstimmen. Der Mac-Vorversuch mit Vosk 0.3.44 zeigte denselben
Fehlschlag; maßgeblich ist der verlinkte Pi-Lauf.

**Nachprüfung der Zählung:** Die ursprünglichen 107/108 prüfen lediglich,
ob mindestens eine Aktivierung stattfand. Für zwei getrennte Dateirufe reicht
das nicht als Nachweis beider Erkennungen. Die [strengere Auswertung derselben
unveränderten Rohdaten](pi-file-count-review.json) erfüllt **105/108** genaue
Zählerwartungen: Bei 3 % Amplitude wurden ein einzelner Hey-KAI-Ruf sowie
je einer von zwei Hey-KAI- bzw. Okay-KAI-Rufen übersehen. Alle Negativbeispiele
bleiben ohne Aktivierung. Das ist keine neue Aufnahme oder weitere unabhängige
Messung. Der Testbericht enthält jetzt sowohl Anwesenheits- als auch exakte
Zählprüfung; drei Regressionstests schützen vor übersehenen und zusätzlichen
Erkennungen. Die gewünschte Sperre mehrfacher Cloud-Starts ist davon getrennt:
zwei erkannte Rufe dürfen während eines Gesprächs weiterhin keinen zweiten
Audioeigentümer erzeugen. Diese Änderung betrifft nur Testwerkzeuge und Doku;
App-Paket, Image-Runtime und laufende Pi-Baseline bleiben unverändert.

### Lautsprecher → Raum → ReSpeaker

Je ein angekündigter synthetischer Ruf unter atomarer Wartungsreservierung:
[Hey KAI](hey-kai-acoustic.json) **0/1**, [Okay KAI](okay-kai-acoustic.json) **0/1**,
[Hey Brain als Kontrolle](hey-brain-acoustic.json) **1/1**. Capture wurde jeweils
beendet und die Wartung freigegeben. Diese Versuche liefen mit dem neuen
Decoder aus einem isolierten Testordner, während die produktive App noch 0.5.52
war. Keine Änderung an Mikrofon-, Lautsprecher- oder Firmwareeinstellungen.

**Die neuen Rufwörter sind daher Testvarianten, keine nachgewiesene Verbesserung.**
Eine natürliche Stimme vor dem Pi muss separat geprüft werden. Die eigene
Pi-Wiedergabe unterdrückt den produktiven Wake-Pfad bewusst; der isolierte
Raumtest belegt keinen normalen Live-Start oder gesprochenen Ende-Befehl.

## Langzeitmessung

Der Nutzerauftrag für neue Rufwörter löste den bisherigen Lauf nach etwa
67 Minuten ab. [Erhaltener Zwischenstand 0.5.52](../wake-stability-0.5.52/partial-observation.json).
Kein abgeschlossener 24-Stunden- oder echter Acht-Stunden-Ruhetest. Die neue
Beobachtung muss App-Version und Rufwort berücksichtigen; ein Wechsel während
des Laufs gilt nicht stillschweigend als Abnahme einer einzelnen Phrase.

## Installation und aktueller Teststand

0.5.53 aus Commit `eda03c3296990982a6a2f0166ab828bcd047ecc5` wurde als
signiertes App-Update (Sequenz 10) auf dem Pi installiert.
[Installationsnachweis](deployment.json): die geprüften Einstellungen blieben
während der Installation erhalten. Anschließend wurde für den ausdrücklich
gewünschten Rufwortvergleich bewusst **Okay KAI** ausgewählt und aktiviert.
Audioauswahl, Kontobindung und Wissensbereiche wurden dabei nicht geändert.

Die neue rein lesende Beobachtung läuft laut `plan.json` vom **15.10.2026,
19:38:35 Uhr bis 16.10.2026, 19:38:35 Uhr (Europe/Berlin)**. Der erste Status
meldet Version 0.5.53, Phrase `okay-kai`, Zustand `listening` und keine Warnungen.
Das beweist noch keinen akustischen Erfolg. Ein natürlicher Ruf „Okay Kai“ und
anschließend „Gespräch beenden“ wurde beim Nutzer angefragt; eine bestätigte
Antwort liegt zum Dokumentationszeitpunkt noch nicht vor. Die bestehende
15-Minuten-Nachprüfung wurde auf diesen Lauf umgestellt; sie greift nicht
automatisch in Aufnahmen, Gespräche oder Dienste ein.

Vorschauen der produktiven Pi-App im Browser:

![Startseite mit aktivem Okay KAI](pi-home-browser.jpg)
![Aktivierungswort-Einstellungen](pi-wake-settings-browser.jpg)
