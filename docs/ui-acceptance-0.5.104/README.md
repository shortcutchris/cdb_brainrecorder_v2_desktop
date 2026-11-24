# Recorder Studio 0.5.104 – Bedienprüfung am 24.11.2026

Geprüft wurde die bereits installierte Version 0.5.104. Bei dieser Prüfung wurde
kein neues Release installiert. Die Ergebnisse ergänzen den
[Installationsnachweis](../update-session-0.5.104/README.md).

## Bedienung und Screenshots

Der physische Pi-Kiosk wurde über privaten Bildschirmzugriff beobachtet und mit
Tastatur bedient. Ergänzende Klickprüfungen liefen gegen dieselbe echte Pi-App
über einen privaten lokalen Tunnel im Browser mit 1280 × 720 Pixeln. Diese
Browserprüfungen verwendeten keine Fixture. Koordinatenklicks über VNC sind wegen
der Displayrotation unzuverlässig und wurden nicht als Fingertest gewertet.

| Prüfung | Ergebnis und Nachweisart |
| --- | --- |
| Konto öffnen/schließen | Pi-Kiosk dargestellt; Außentipp im verbundenen Browser schließt den Dialog und erhält die Anmeldung. |
| Abmeldebestätigung | Große Aktionskacheln am Pi sichtbar; Außentipp im Browser verwirft die Bestätigung, ohne abzumelden. |
| Timer – Zeit | Große Plus-/Minus- und Vorgabetasten, zwei Formularseiten und fester Startbereich am Pi sichtbar. Kein Scrollen nötig. |
| Timer – Titel und Klang | Im verbundenen Browser Titel und Klang geändert; Wechsel zwischen beiden Seiten erhält die Eingaben. |
| Bildschirmtastatur | Titel, Tastatur und Startbereich im verbundenen Browser gleichzeitig erreichbar und sichtbar. |
| Verlauf | Fünf erledigte Einträge auf zwei Seiten (3 + 2); beide Seiten im verbundenen Browser geprüft. |
| Laufender Timer | Ein Timer „Bedientest“ mit einer Minute gestartet. Großansicht und Außentipp zum Minimieren im Browser geprüft. Countdown am tatsächlichen Pi beobachtet. |
| Kopfzeile | Der minimierte Timer überdeckt den Kontoknopf am tatsächlichen Pi nicht. |
| Timerende | Alarm öffnet sich am tatsächlichen Pi groß. Bestätigung dort per Tastatur ausgeführt; Eintrag danach erledigt. |
| Alarmton | Fehlgeschlagen. Fehlerhinweis im Alarmdialog sichtbar. Kein erfolgreicher Hörtest. Siehe USB-Befund. |

Der abschließende Zustand nach dem Bedientest: keine Aufnahme, kein laufendes
Gespräch, kein laufender Timer und kein unbestätigter Alarm. Die Anmeldung blieb
erhalten. Der klar bezeichnete erledigte Testtimer bleibt im Verlauf.

Die Screenshots liegen im privaten Arbeitsartefakt `output/pi-ui-test-2026-11-24`.
Die Galerie unterscheidet Pi-Kiosk-Aufnahmen (CDB-Design) und ergänzende
Browseraufnahmen (helles Design). Identifizierende Kontoansichten wurden nicht
zusätzlich in dieses Git-Repository kopiert.

## Beobachtete Grenzen

Kein erneuter physischer Fingertest, kein neuer 1024 × 600-Hardwaretest und keine
erneute vollständige Prüfung sämtlicher Aufnahme-/Talk-Zustände. Die vorhandenen
[0.5.103-Prüfungen](../ui-audit-0.5.103/README.md) bleiben dafür separat ausgewiesen.

Zu Beginn zeigte eine offene Kioskansicht fälschlich eine fehlende Verbindung,
während die Statusschnittstelle erreichbar war. Neuladen behob die Anzeige und
erhielt die Anmeldung. Eine zuvor gelöschte, noch ausgewählte Sitzung ist als
Ursache plausibel: ein Fehler beim Nachladen der Sitzung kann derzeit in den
allgemeinen Verbindungsfehlerpfad fallen. Dies ist ein offener Befund, kein in
dieser Prüfung behobener Fehler.

## USB-Soundbar: gesicherter Befund

Zwei zusätzliche Prüfungen untersuchten USB/PCIe sowie die Audio-Ansteuerung.

- 09:40:21 MEZ: Lautsprecher-Test angefordert.
- 09:40:26: externer VIA VL805/806-Controller `0001:01:00.0` meldet
  `xHCI host controller not responding, assume dead` und `HC died; cleaning up`.
- Dabei verschwinden der externe Hub und die USB-Soundbar „188A“ (`0020:0b21`).
  Die Soundbar fehlt anschließend bereits in USB-/ALSA-Erkennung, nicht nur in
  der Anwendung. NFC und reSpeaker an einem anderen Controller bleiben verfügbar.
- Nur der aktuelle Boot ist im Journal enthalten. Zusätzlich dokumentiert die
  [bestehende Soundbar-Anleitung](../audio/soundbar.md) einen gleichartigen Ausfall
  vom 23.11., 18:58:35 Uhr. Der dort verlinkte Hardware-Leitfaden hält einen
  weiteren vom 12.11., 13:54 Uhr fest. Das Problem ist damit wiederholt
  dokumentiert; eine vollständige Häufigkeitsstatistik ist nicht möglich.
- Keine protokollierte Unterspannung oder Überstrommeldung; `throttled=0x0`.
  Das schließt ein Problem der separaten Boardversorgung oder Verkabelung nicht aus.
- PipeWire und WirePlumber laufen seit 09:23 durch, ohne Dienstneustart.
- 13:26:17 wurde über die Lautsprechereinstellungen ausdrücklich der reSpeaker
  gewählt. Dies war kein automatisches Umschalten der App. Die Existenz seines
  Audioausgangs bedeutet nicht, dass die interne USB-Soundbar verfügbar ist.

Der Bedientest-Alarm scheiterte vor dieser Auswahländerung. Sein konkreter
Ausgabefehler wird derzeit nicht dauerhaft gespeichert; `sound=failed` allein
beweist den damaligen ausgewählten Ausgang nicht. Der Controllerverlust ist
unabhängig davon sicher belegt.

Der Nutzer korrigierte die zunächst gemeldete Umsteckbestätigung: Das Gehäuse ist
verschraubt; ein direkter Anschluss der Soundbar am Pi wurde nicht durchgeführt.
Ein A/B-Test von Soundbar gegen Erweiterungsboard steht daher aus.

Die gerätespezifische Treiber-Neubindung wurde als Wiederanlauf geprüft: betroffen
wären nur Bus 1/2 am VIA-Controller, nicht die separaten Pi-Controller mit Display,
NFC und reSpeaker. Nach erneuter Aktivitätsprüfung wurde der eng begrenzte Aufruf
versucht. `sudo -n` brach vor Ausführung wegen fehlender Passwortbestätigung ab.
Es wurde **kein Controller zurückgesetzt**, keine Treiberschnittstelle beschrieben
und kein Pi-/App-/Audiodienst neu gestartet. Die Soundbar blieb nicht verfügbar;
weitere Töne und ein angeblich bestandener Hörtest wurden nicht behauptet.

Ein geordneter Pi-Neustart ist ein bereits erprobter vorläufiger Wiederanlauf,
kein Nachweis für eine dauerhafte Behebung. Die vollständige Prüfung der
Boardversorgung/FPC-Verbindung sowie ein direkter Vergleichsanschluss bleiben offen.

## Image-Auswirkung

Nur Prüfdokumentation, keine Änderung am Programm, Installationspaket oder
Kunden-Image. Kein neues Image gebaut oder als hardwaregeprüft bezeichnet.
