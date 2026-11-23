# NFC-Anmeldung bei Lesepausen · 0.5.96

Stand: 23.11.2026. Chris meldet, dass der nach Auflegen geöffnete Anmeldedialog
nach wenigen Sekunden verschwindet. Im Code verwirft `RoomMode.reconcile` den
Startwunsch schon bei einer einzelnen fehlenden/veralteten Leserantwort; die
Oberfläche schließt daraufhin beide Dialoge. Erneutes Auflegen konnte außerdem
den gleichen Startwunsch ersetzen und dessen offenen Anmeldeversuch abbrechen.

## Korrektur

Die vorhandene Fünf-Minuten-Frist bleibt bestehen. Fehlende Präsenz und
Leserfehler unterbrechen die Anmeldung nicht. Dasselbe Tag erzeugt innerhalb
dieser Frist keinen neuen Startwunsch. Ein abweichender Tag, ausgeschaltetes NFC,
ausdrücklicher Abbruch, Kontowechsel oder Fristablauf verwerfen ihn weiterhin.
Vor jedem bestätigten Start prüft der Server erneut dieselbe Tagkennung und
aktuelle Leserantwort. Die Oberfläche sperrt die Starttaste bis dahin und zeigt
einen Hinweis. Es beginnt weder bei Auflegen noch bei Anmeldung eine Aufnahme.
Die bestehende 1,5-Sekunden-Abnahme für das Beenden einer bereits gestarteten
NFC-Aktivität bleibt unverändert.

## Prüfstand

- 49 Python-Tests für Raummodus, NFC-Reader/-Zustandsautomat und Image-Export;
  zusätzlich 8 Aktivitätsprüfungen bestanden.
- 152 JavaScript-Tests bestanden.
- Neue Regressionen: Lesefehler/Abwesenheit während offenem Login, gleiche
  Tagkennung nach Wiederauflegen ohne neuen Login/Fristverlängerung, bestätigter
  Start nur bei Präsenz, Abbruch bei Austausch/Deaktivierung/Ablauf/Abbrechen.
- Echter Chromium-Browser, künstlicher NFC-Leser und Microsoft-Testtransport:
  QR-Dialog bleibt bei Leserfehler und zusätzlich 90 Sekunden versetzter
  Vorbereitungsuhr offen. Anmeldung abgeschlossen, Start bei fehlendem Tag
  gesperrt und bei Wiederauflage desselben Tags freigegeben; kein Audiostart.
  1280 × 720 und 1024 × 600 geprüft. [Anzeige ohne Tag](login-missing-tag-1024.png).
- Signiertes Paket auf dem ungenutzten Pi installiert; Studio und Kiosk laufen
  mit 0.5.96. 150 ausgelieferte Dateien verifiziert, Aufnahmen, Einstellungen,
  Raummodus und beide NFC-Zuordnungen unverändert.
  [Installationsnachweis](096-deployment.json).
- Image-Baupaket aus Commit `d6b5305` vorbereitet und alle 157 Quelldateien gegen
  das Manifest geprüft. Kein SD-Image gebaut oder auf neuer Karte gebootet.

## Auslieferung und SD-Image

Reines Code-Update aus vorhandenen freigegebenen App-Dateien. Keine neuen
Systempakete, Datenformate, Tags oder Geräteeinstellungen. Vorhandene
NFC-Zuordnungen und Aufnahmen bleiben erhalten. Neue Image-Baupakete übernehmen
denselben Code aus sauberem Git-Stand. Ein Baupaket ist kein gebautes oder auf
einer neuen SD-Karte gebootetes Image.

## Separate Live-Beobachtung

Vor der Korrektur lieferte der Pi über 30 Sekunden in 31 Statusabfragen konstant
„Kein NFC-Leser erkannt“, ohne aktiven Startwunsch, Konto oder Aufnahme. Beide
Tags waren zugeordnet und NFC eingeschaltet. Das Rocketek-USB-Gerät und beide
CCID-Schnittstellen waren im System sichtbar; PC/SC-Dienst und Socket aktiv.
Damit ist ein zusätzlicher Fehler der Leser-Erkennung zu prüfen; diese Messung
belegt kein Flattern und rekonstruiert nicht den früheren konkreten Abbruch.
Die zusätzliche PC/SC-Abfrage im normalen Benutzerdienstkontext erkannte ebenfalls
null Leser. Das Treiberprotokoll zeigte `LIBUSB_ERROR_TIMEOUT` und anschließend
fehlgeschlagene Initialisierung beider Slots. Ein Ab-/Anstecken des Lesers wurde
Chris vorgeschlagen und von ihm ausgeführt. Danach meldet der Pi wieder
„Bereit für Talk oder Meeting“ mit korrekt leerem Lesefeld. Keine pauschalen
Berechtigungsänderungen vorgenommen. Chris hat anschließend den Meeting-
Aufsteller aufgelegt: In 13 Abfragen über 60 Sekunden blieben Tagpräsenz,
Meeting-Vorbereitung und offener Anmeldevorgang stabil; keine Audioaufnahme.
[Bereinigte Statusmessung](096-reconnect-check.json). Chris bestätigt anschließend ausdrücklich: „Anmeldung klappt, Dialog bleibt
offen“. Damit ist der persönliche Anmeldeablauf am realen Gerät durch den
Benutzer bestätigt. Die automatische Prüfung hat keine echte Anmeldung oder
Audio gestartet; eine vollständige Talk-/Meeting-Audioabnahme ist davon getrennt.
