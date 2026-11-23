# Raummodus: Anmeldung, NFC und Offline-Bedienung

Stand: 23.11.2026 · Recorder Studio 0.5.90. Implementiert; Installationsnachweis folgt separat in diesem Ordner. Gastaufnahmen sind im Raummodus ausgeschaltet. Der persönliche Betriebsmodus bleibt der Werksstandard.

## Einmalig einrichten

1. Mikrofon, Lautsprecher, Verarbeitungsmodelle und Netzwerk wie bisher einrichten.
2. Einstellungen → Gerät & Verwaltung → **Raummodus & Betreiber** öffnen.
3. „Gemeinsam genutztes Raumgerät“ aktivieren, eine Betreiber-PIN mit 6–12 Ziffern setzen und die Abmeldefrist wählen (Standard 5 Minuten, 2–60 Minuten möglich).
4. **Speichern & abmelden** tippen. Die bisherige Brain-Sitzung wird beendet. Aufnahmen werden nicht gelöscht.
5. Einstellungen sind danach mit der Betreiber-PIN für fünf Minuten entsperrbar. Eine PIN berechtigt nicht zum Lesen fremder Meetings. Bei Abmeldung verfällt auch die Betreiberfreigabe.

Die PIN wird lokal mit zufälligem Salt und scrypt gespeichert. Nach fünf falschen Versuchen folgt eine Minute Wartezeit. Eine vergessene PIN erfordert betreute Wiederherstellung am Gerät; es gibt keinen allgemeinen Standardcode. Dies schützt die Bedienoberfläche und API, nicht gegen einen Administrator mit Zugriff auf Betriebssystem und Datenträger.

## Am Gerät arbeiten

- **Meeting aufzeichnen** oder **Mit dem Brain sprechen** antippen. Ein bekannter NFC-Aufsteller führt zum selben Ablauf.
- Ohne Anmeldung öffnet sich der bestehende Microsoft-Dialog mit QR-Code und Eingabecode. Dafür ist Internet nötig. Ein Aufsteller wählt ausschließlich den Modus und ist kein Ausweis.
- Nach Anmeldung zeigt die Vorbereitung Name und Brain-Umgebung. **Aufnahme starten** beziehungsweise **Gespräch starten** schaltet das Mikrofon ausdrücklich ein. Bei Talk zuerst Gesprächswissen auswählen, falls noch keines gespeichert ist.
- **Anderes Konto** meldet ab. Danach die gewünschte Aktion mit dem anderen Konto erneut wählen.
- Bei NFC den Aufsteller während der Anmeldung liegen lassen. Abnehmen, Wechsel, veraltete Leserantwort, Abbruch oder fünf Minuten Wartezeit verwerfen den Startwunsch. Eine spätere Anmeldung startet nie automatisch.
- Nach einem bestätigten NFC-Start beendet das Abnehmen wie bisher nur die zugehörige Aktivität (1,5 Sekunden bestätigte Abwesenheit). Ein USB-/Leserausfall beendet keine laufende Aufnahme. Im Zweifel am Display stoppen.
- **Fertig & abmelden** ist neben dem Konto erreichbar, auch während Aufnahme/Gespräch. Der Dialog nennt die laufende Aktivität. Erst erfolgreich stoppen/sichern beziehungsweise Audio freigeben, dann abmelden. Bei Fehlschlag bleibt das Konto angemeldet.
- Nach Inaktivität gibt es 30 Sekunden Vorwarnung und **Angemeldet bleiben**. Aufnahme, Pause und aktive Gespräche verhindern die automatische Abmeldung. Statusabfragen des Browsers verlängern die Sitzung nicht.

Ein Neustart des Raumgeräts stellt keine alte persönliche Anmeldung wieder her. Das Anmeldekonto muss erneut bestätigt werden.

## Wenn die Verbindung fehlt

| Situation | Verhalten |
| --- | --- |
| Noch niemand angemeldet | Kein Aufnahmestart. Internet wiederherstellen, ggf. Betreiber → WLAN & Einrichtung, dann erneut anmelden. |
| Bestätigte Sitzung verliert Internet | Meeting kann lokal aufgenommen werden; laufende Aufnahme bleibt bestehen. |
| Aufnahme gespeichert, Brain nicht erreichbar oder Anmeldung abgelaufen | Warteschlange: „Aufnahme gespeichert · wartet auf Brain“ mit konkretem Grund. **Erneut prüfen** startet den bestehenden Wiederanlauf. |
| Lokale Modelle verfügbar | **Lokal verarbeiten** verlangt eine eigene Bestätigung. Nur installierte, getestete und ausgewählte lokale Modelle werden akzeptiert. Die neue Verarbeitung wird der ursprünglichen Aufnahme und ihrem Konto zugeordnet. |
| Abmeldung während Hintergrundverarbeitung | Lokale Verarbeitung darf weiterlaufen. Cloud-Schritte prüfen stets das gespeicherte ursprüngliche Konto; keine Übernahme durch den nächsten Benutzer. |
| Talk offline | Keine lokale Talk-Ersatzfunktion. Verbindung/Anmeldung prüfen und Gespräch erneut ausdrücklich starten. |

Es gibt keine automatische Umstellung der KI-Anbieter und keine automatische erneute Audioübertragung. Unklar quittierte Uploads behalten die vorhandene Abgleichlogik; ein bereits angenommener Serverauftrag kann dort weiterlaufen. Die lokale Warteschlange verwendet technisch weiterhin den wiederholbaren Zustand `failed` für unterbrochene Cloud-Schritte; `brain-wait.json` unterscheidet das Warten vom eigentlichen Verarbeitungsfehler.

## Kontotrennung und Altbestand

Neue Raumjobs erhalten vor dem Start eine private `room-owner.json` mit Server, Benutzer und Firmenkennung. Liste, Suche, Details, Änderungen, Löschen, Wiederholen, Neuverarbeitung, Audio, Peaks und Exporte prüfen dieselbe Zuordnung. Dies gilt auch für die geerbten `/api/meetings/*`-Routen. Eigentümermarkierungen bleiben auch nach dem Ausschalten des Raummodus wirksam.

Bestehende Aufnahmen ohne solche Zuordnung bleiben unverändert. Im Raummodus sind sie verborgen; sie werden niemals dem nächsten angemeldeten Benutzer zugeschlagen. Eine nachträgliche administrative Eigentümerzuweisung ist nicht Teil dieses Releases. Der bisherige persönliche Modus zeigt weiterhin den persönlichen Altbestand.

Brain-Übertragungen werden nach ihrer vorhandenen Kontobindung gefiltert. Wartende Übertragungen eines abgemeldeten Kontos blockieren nicht die Übertragungen des aktuell angemeldeten Kontos. Timer erhalten ebenfalls eine Eigentümerbindung. Der öffentlich sichtbare LCD-Timer-Begleiter bekommt im Raummodus zunächst keine persönlichen Timer. Eigene Promptvorlagen liegen dort getrennt pro Konto. Browserentwürfe des Raummodus bleiben nur im Sitzungsspeicher und werden bei Abmeldung entfernt. Gespeicherte Aufnahmen bleiben erhalten.

Abmelden widerruft persönliche Bildschirmkopplungen und lokale Fernsteuerungsfreigaben. Der sichtbare Gesprächsverlauf wird geleert; bei einer späteren Anmeldung desselben Kontos kann dessen gespeicherter Verlauf wiederhergestellt werden. Allgemeine Geräteeinstellungen und Modelle bleiben bestehen.

## Installation, Datenformat und Rückkehr

- Keine neuen Laufzeitpakete und keine Änderung der bestehenden SQLite-Tabellenschemata.
- Ergänzende private Dateien: `room-mode.json`, `meetings/<id>/room-owner.json`, `meetings/<id>/brain-wait.json`, `room-prompts/<Kontoschlüssel>.ini`. Timerbindung liegt im bereits vorhandenen JSON-Payload.
- `services/room_mode.py`, `studio/room.js`, `studio/room.css` und die angepassten vorhandenen Dateien sind durch die bestehenden App-/Image-Freigabelisten abgedeckt. Runtime-Dateien, PIN, Konten und Meetings gelangen nicht ins Release oder Factory-Image.
- Beim Update bleibt der Raummodus ausgeschaltet, sofern er nicht schon ausdrücklich eingerichtet wurde. Das aktuelle Pi-Profil und der gesamte Altbestand werden erhalten.
- Code-Rollback ist während der Installation zulässig, solange noch keine Raumdaten erzeugt wurden. **Nach Nutzung des Raummodus nicht auf eine Version vor 0.5.90 zurückgehen:** Ältere Software kennt die Eigentümermarkierungen nicht. Eine Wiederherstellung muss eine Version mit denselben Zugriffsprüfungen verwenden oder bei gesperrtem Zugriff administrativ erfolgen. Das Löschen der Modus-Konfiguration ersetzt diese Prüfung nicht.
- Ein exportiertes Image-Baupaket ist kein gebautes oder auf Hardware gestartetes SD-Image.

## Abnahme

Automatisiert geprüft: frischer persönlicher Start, bewusstes Einschalten mit PIN, Erhalt des Altbestands, Konten-/Firmentrennung aller Dateipfade und Mutationen, Neustart, veraltete/abgenommene NFC-Absicht, Startbestätigung, fehlgeschlagener Stopp, Leerlauffrist inklusive Pause/Live, PIN-Sperre, Timer-/Publikationsfilter und Brain-Wartezustand. Insgesamt bestanden 194 Python-Tests und 140 JavaScript-Tests einschließlich der bestehenden Aufnahme-, NFC-, Geräte-, Cloud- und Fernsteuerungsprüfungen.

Browserprüfung mit synthetischem Konto und synthetischer Audioquelle: 1280×720 und 1024×600; Startbestätigung, Aufnahme, Stoppen & Abmelden, neutraler Bildschirm und Betreiber-PIN mit Bildschirmtastatur. Die Microsoft-Anmeldung wird dabei nicht als echte Kontoabnahme ausgegeben.

Noch vor Ort zu prüfen: echter NFC-Leser mit Talk/Meeting-Aufstellern, Microsoft-Anmeldung durch den Nutzer, tatsächlicher Netzwerkausfall und Talk mit echtem Mikrofon/Lautsprecher. Dafür keine bestehende persönliche Aufnahme oder Konfiguration ungefragt verändern.

[Startbestätigung 1280×720](room-confirm-1280.png) · [Startbestätigung 1024×600](room-confirm-1024.png) · [PIN mit Tastatur 1024×600](room-pin-1024.png)
