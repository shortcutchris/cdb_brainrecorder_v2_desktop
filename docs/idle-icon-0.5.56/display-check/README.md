# Echtes Touchdisplay: störender Schlüsselbund-Dialog

16. Oktober 2026, etwa 02:00–02:01 Europe/Berlin. Der laufende Beobachter
1469691 wurde als aktiver Prozess bestätigt. Seine Backend-Messwerte meldeten
Leerlauf, Wake-Bereitschaft und keine Warnung. Der [Display-Screenshot vor dem
Eingriff](before.png) zeigte dennoch einen nativen „Unlock Keyring“-Dialog
über der Startseite. Damit ist API-Bereitschaft allein kein Beleg für eine
unverdeckte, bedienbare Oberfläche.

Der Dialogprozess `/usr/libexec/gcr-prompter`, PID 1375127, lief laut Prozessliste
seit 00:25:15. Das belegt nicht, seit wann das Fenster sichtbar war oder welche
Anwendung es ursprünglich angefordert hatte. Der produktive Chromium-Aufruf und
die zuletzt verwendeten SVG-/App-Diagnose-Runner enthalten bereits
`--password-store=basic`; die Ursache ist damit noch nicht geklärt. Kein pauschales
Abschalten oder Löschen des Schlüsselbunds und keine Änderung der Passwortablage.

Nach Prüfung des ausführbaren Prozesspfads wurde ausschließlich dieser
Dialogprozess mit SIGTERM beendet. Keine Passworteingabe, kein Audiozugriff,
kein Neustart von Browser, Backend oder Beobachter. Der [Screenshot danach](after.png)
zeigt die unverdeckte Startseite mit „Bereit für Okay KAI“. Browser 805908,
Backend 1468084 und Beobachter 1469691 blieben erhalten. Die
[Nachprüfung](check.json) bestätigt weiter laufende Audioerfassung und
`listening`; sie belegt keine tatsächliche Rufworterkennung.

Die laufende Messung wird nicht zurückgesetzt. Dieser manuelle Eingriff muss
bei ihrer Abschlussbewertung berücksichtigt werden; ein störungsfreier
unbeaufsichtigter UI-Betrieb ist für diesen Abschnitt **nicht nachgewiesen**.
Der sichtbare Screen verrät außerdem nicht die aktuell im Browser ausgeführte
JavaScript-Version. Installierte Dateihashes und API-/HTML-Version aus der
Installationsprüfung bleiben davon getrennte Nachweise. Der produktive Browser
hat keinen offenen DevTools-Port; es wurde kein Neustart zur Instrumentierung
erzwungen. Die verbleibende Last von etwa 30 % eines CPU-Kerns bleibt offen.

Nur Diagnose und Dokumentation: keine neuen App-Dateien oder Abhängigkeiten,
keine Auslieferung, keine Änderungen am Kunden-Image. Der Screenshot enthält
keine eingegebenen Zugangsdaten. Die ursprünglichen Messdateien bleiben unverändert.
