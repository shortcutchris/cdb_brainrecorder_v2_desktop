# Anmeldung, NFC und automatische Abmeldung

Stand: 23.11.2026 · Recorder Studio 0.5.92. Anmeldung und Kontotrennung sind der Standard. Es gibt keine auswählbare persönliche Betriebsart und keine Gastaufnahme. Der vorherige Installationsnachweis 0.5.90 bleibt in [deployment.json](deployment.json) erhalten; der neue Nachweis steht in [deployment-0.5.91.json](deployment-0.5.91.json).

## Einmalig einrichten

1. Mikrofon, Lautsprecher, Verarbeitungsmodelle und Netzwerk wie bisher einrichten. Technische Tests mit künstlicher Sprache sind auch vor einer persönlichen Anmeldung möglich; sie werden keinem Benutzer zugeschlagen und erscheinen nicht in der persönlichen Bibliothek.
2. Einstellungen → Gerät & Verwaltung → **Anmeldung & Geräteschutz** öffnen.
3. Eine Betreiber-PIN mit 6–12 Ziffern setzen und die Ruhefrist wählen (Standard 15 Minuten, 2–60 Minuten möglich). Bis zur PIN-Einrichtung sind die Geräteeinstellungen noch offen; die persönliche Anmeldung für Aufnahmen ist bereits erforderlich.
4. Optional **Raumgeräusche berücksichtigen** aktivieren. Das Mikrofon bleibt dann bei angemeldeter, ungenutzter Sitzung aktiv. Der Dialog erklärt die lokale Pegelauswertung und die mögliche Verlängerung durch Geräusche.
5. **Speichern** tippen. Die persönliche Anmeldung bleibt erhalten; die Geräteeinstellungen sind danach gesperrt und mit PIN für fünf Minuten entsperrbar. Eine PIN berechtigt nicht zum Lesen fremder Meetings.

Die PIN wird lokal mit zufälligem Salt und scrypt gespeichert. Nach fünf falschen Versuchen folgt eine Minute Wartezeit. Eine vergessene PIN erfordert betreute Wiederherstellung am Gerät; es gibt keinen allgemeinen Standardcode. Dies schützt die Bedienoberfläche und API, nicht gegen einen Administrator mit Zugriff auf Betriebssystem und Datenträger. Beschädigte Konfigurationen sperren die Einrichtung statt den Schutz zu öffnen.

## Am Gerät arbeiten

- **Meeting aufzeichnen** oder **Mit dem Brain sprechen** antippen. Ein bekannter NFC-Aufsteller führt zum selben Ablauf.
- Optional ab 0.5.97: In **Audio → NFC-Aufsteller** Direktstart getrennt für Talk
  und Meeting einschalten. Ein bereits angemeldeter Benutzer startet dann durch
  erneutes Aufstellen unmittelbar, solange keine Vorbereitung offen ist. Ohne
  Anmeldung sowie bei offener Vorbereitung bleibt die Bildschirmbestätigung
  erhalten. Ein bereits aufliegender Aufsteller startet bei Anmeldung nicht
  nachträglich. Nach Abbrechen mindestens zwei Sekunden abnehmen und neu auflegen.
- Ohne Anmeldung öffnet sich der bestehende Microsoft-Dialog mit QR-Code und Eingabecode. Dafür ist Internet nötig. Ein Aufsteller wählt ausschließlich den Modus und ist kein Ausweis.
- Nach Anmeldung zeigt die Vorbereitung Name und Brain-Umgebung. **Aufnahme starten** beziehungsweise **Gespräch starten** startet die Aufnahme beziehungsweise die Audioübertragung für das Gespräch ausdrücklich. Eine eingeschaltete lokale Geräuscherkennung speichert bis dahin weiterhin keinen Ton. Bei Talk zuerst Gesprächswissen auswählen, falls noch keines gespeichert ist.
- **Anderes Konto** öffnet dieselbe Speicher- und Abmeldebestätigung wie der Kontodialog. Danach die gewünschte Aktion mit dem anderen Konto erneut wählen.
- Bei NFC bleibt die Vorbereitung seit 0.5.96 bis zu fünf Minuten offen, auch bei
  kurz abgenommenem Aufsteller oder unterbrochener Leserantwort. Zum Start muss
  derselbe Aufsteller wieder erkannt werden. Erneutes Auflegen setzt weder den
  Anmeldeversuch noch die Frist zurück. Wechsel zu einem anderen Tag, NFC
  ausschalten, Abbruch oder fünf Minuten Wartezeit verwerfen den Startwunsch.
  Eine spätere Anmeldung startet nie automatisch.
- Nach einem NFC-Start beendet das Abnehmen nur die zugehörige Aktivität, wenn „Beenden beim Abnehmen“ für diesen Modus eingeschaltet ist (Standard ein, 1,5 Sekunden bestätigte Abwesenheit). Seit 0.5.98 kann diese Option für Talk und Meeting getrennt ausgeschaltet werden; dann am Bildschirm beenden. Ein USB-/Leserausfall beendet keine laufende Aufnahme. Im Zweifel am Display stoppen.
- **Fertig & abmelden** ist neben dem Konto erreichbar. Seit 0.5.92 ist die Taste während Aufnahme, Pause, Gespräch und laufenden Geräteänderungen gesperrt. Zuerst **Aufnahme stoppen** beziehungsweise **Gespräch beenden**. Anschließend bietet der Abschlussdialog **Angemeldet bleiben** und **Speichern & abmelden**. Alle Abmeldeeinstiege sichern die Notizen; bei einem Fehler bleibt das Konto angemeldet und der lokale Entwurf erhalten. Eine veraltete Bestätigung stoppt niemals eine neue Aufnahme. Die explizite Abmeldekachel in der Ruhefristwarnung braucht keine zweite Bestätigung, sichert aber ebenfalls zuerst den Entwurf.

- Während Aufnahme, Aufnahmepause, Gespräch (einschließlich Verbindungsaufbau und Beenden) und Wiedergabe wird nie wegen Inaktivität abgemeldet. Nach deren Ende beginnt die vollständige Ruhefrist neu. Standardmäßig sind es 15 Minuten; während der letzten Minute erscheint **Angemeldet bleiben**. Berührung oder Tastatureingabe startet die Frist neu. Reine Statusabfragen verlängern sie nicht; Hintergrundverarbeitung allein hält ein verlassenes Konto nicht offen.

Ein Neustart des Geräts stellt keine alte persönliche Anmeldung wieder her. Das Anmeldekonto muss erneut bestätigt werden.

## Zusätzliche Geräuscherkennung

Nach ausdrücklichem Einschalten und nur bei angemeldeter Sitzung nutzt der Pi den bestehenden lokalen Mikrofonprozess. Ist das Aktivierungswort eingeschaltet, teilen sich beide Erkennungen denselben Audiostrom. Ohne Aktivierungswort wird kein Sprachmodell geladen: Es werden ausschließlich wechselnde Lautstärkepegel ausgewertet. Der Prozess hält jeweils einen 50-ms-PCM-Block kurz im Arbeitsspeicher und speichert für den Vergleich höchstens 100 skalare Pegelwerte. Keine Audiodatei, kein Transkript und keine Übertragung an Brain oder einen anderen Dienst.

Gleichmäßiges Lüfterrauschen bildet den Grundpegel. Mindestens drei erhöhte Blöcke (150 ms) lösen einen Aktivitätshinweis aus, höchstens alle fünf Sekunden. Ein einzelner erhöhter 50-ms-Block genügt nicht. Erkannte Aktivität startet die Ruhefrist neu. Die Empfindlichkeit ist zunächst fest; der echte Raum muss noch auf passende Reaktion geprüft werden. Musik, wechselnde Geräusche oder Stimmen nebenan können die Anmeldung verlängern; stille Personen können unbemerkt bleiben. Daher bleibt die Vorwarnung mit manueller Verlängerung erhalten.

Die Kontotaste zeigt **Mikrofon: Geräuschpegel**, die Startseite zusätzlich den vollständigen Hinweis. Während Aufnahme, Gespräch, Wiedergabe, Tests und Gerätewartung hat die jeweilige Nutzung Vorrang. Vor einem neuen Audiozugriff wird der Beobachter bestätigt beendet; fehlgeschlagene Freigabe blockiert den Start statt einen zweiten Mikrofonprozess zu öffnen. Bei Abmeldung wird auch die Beobachtung beendet. Neue Geräte starten mit ausgeschalteter Geräuscherkennung; für den aktuellen Pi wurde das Einschalten am 23.11.2026 ausdrücklich beauftragt.

Bei fehlendem Mikrofon oder ausbleibenden Messwerten läuft die normale Ruhefrist weiter. Die Erkennung verlängert die Sitzung nur anhand tatsächlich eingegangener Aktivitätshinweise. Kein vorgetäuschtes Offenhalten bei Fehlern.

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

Neue Raumjobs erhalten vor dem Start eine private `room-owner.json` mit Server, Benutzer und Firmenkennung. Liste, Suche, Details, Änderungen, Löschen, Wiederholen, Neuverarbeitung, Audio, Peaks und Exporte prüfen dieselbe Zuordnung. Dies gilt auch für die geerbten `/api/meetings/*`-Routen. Eigentümermarkierungen bleiben dauerhaft wirksam; auch ein alter API-Aufruf kann die Anmeldung nicht ausschalten.

Bestehende Aufnahmen ohne solche Zuordnung bleiben unverändert. In der Benutzeransicht sind sie verborgen; sie werden niemals dem nächsten angemeldeten Benutzer zugeschlagen. Eine nachträgliche administrative Eigentümerzuweisung ist nicht Teil dieses Releases. Der Altbestand bleibt auf dem Datenträger für eine spätere betreute Zuordnung erhalten.

Brain-Übertragungen werden nach ihrer vorhandenen Kontobindung gefiltert. Wartende Übertragungen eines abgemeldeten Kontos blockieren nicht die Übertragungen des aktuell angemeldeten Kontos. Timer erhalten ebenfalls eine Eigentümerbindung. Der öffentlich sichtbare LCD-Timer-Begleiter bekommt im Raummodus zunächst keine persönlichen Timer. Eigene Promptvorlagen liegen dort getrennt pro Konto. Browserentwürfe des Raummodus bleiben nur im Sitzungsspeicher und werden bei Abmeldung entfernt. Gespeicherte Aufnahmen bleiben erhalten.

Abmelden widerruft persönliche Bildschirmkopplungen und lokale Fernsteuerungsfreigaben. Der sichtbare Gesprächsverlauf wird geleert; bei einer späteren Anmeldung desselben Kontos kann dessen gespeicherter Verlauf wiederhergestellt werden. Allgemeine Geräteeinstellungen und Modelle bleiben bestehen.

## Installation, Datenformat und Rückkehr

- Keine neuen Laufzeitpakete und keine Änderung der bestehenden SQLite-Tabellenschemata.
- Ergänzende private Dateien: `room-mode.json`, `meetings/<id>/room-owner.json`, `meetings/<id>/brain-wait.json`, `room-prompts/<Kontoschlüssel>.ini`. Timerbindung liegt im bereits vorhandenen JSON-Payload.
- `services/room_mode.py`, `services/room_activity.py`, `studio/room.js`, `studio/room.css` und die angepassten vorhandenen Dateien sind durch die bestehenden App-/Image-Freigabelisten abgedeckt. Runtime-Dateien, PIN, Konten und Meetings gelangen nicht ins Release oder Factory-Image.
- Beim Update wird die Anmeldung zum Standard; eine vorherige persönliche Anmeldung wird beim Neustart beendet. Audio-/Modell-/Netzwerkeinstellungen und Aufnahmen bleiben erhalten. Bereits eingerichtete PINs und ausdrücklich gesetzte Fristen bleiben bestehen. Bisher ausgeschalteter Modus beziehungsweise frische Installation erhalten 15 Minuten Ruhefrist. `room-mode.json` wird additiv auf Richtlinienversion 2 normalisiert.
- Code-Rollback ist während der Installation zulässig, solange noch keine Raumdaten erzeugt wurden. **Nach Nutzung des Raummodus nicht auf eine Version vor 0.5.90 zurückgehen:** Ältere Software kennt die Eigentümermarkierungen nicht. Eine Wiederherstellung muss eine Version mit denselben Zugriffsprüfungen verwenden oder bei gesperrtem Zugriff administrativ erfolgen. Das Löschen der Modus-Konfiguration ersetzt diese Prüfung nicht.
- Ein exportiertes Image-Baupaket ist kein gebautes oder auf Hardware gestartetes SD-Image.

## Abnahme 0.5.91

301 Python- und 141 JavaScript-Tests bestanden. Automatisierte Prüfung umfasst den frischen Standardbetrieb und Upgrade vom ausgeschalteten Modus, PIN-Erhalt, Ablehnung eines alten Deaktivierungsaufrufs, Kontentrennung, stundenlange Aufnahme/Pause/Gespräch, volle neue Ruhefrist nach Ende, Wiedergabe, Vorwarnung und Verlängerung, technische Einrichtung ohne persönliches Konto sowie Mikrofonfreigabe. Die Geräuscherkennung wird mit künstlichem PCM, Stille, gleichmäßigem Rauschen, Einzelimpuls und wechselnden Pegeln getestet. Zusätzlich läuft der echte Erkennungsprozess mit künstlicher Audioquelle, ohne Sprachmodell oder Mikrofonzugriff des Entwicklungsrechners.

Browserprüfung: 1280×720 und 1024×600, Einstellungen, PIN mit Tastatur, Geräuschhinweis und Abmeldevorwarnung. Abschlussdialog in hellem und CDB-Theme geprüft: Zurück lässt die Aufnahme weiterlaufen, Speichern beendet die künstliche Aufnahme und meldet ab. Eine spätere Löschbestätigung erhält wieder ihre Warnfarbe und keine alten Kontohinweise. Künstliches Konto und künstliche Audioquelle; kein behaupteter echter Microsoft-Login.

Installation: Signiertes Paket aus Commit `8901052`, 136 verifizierte App-Dateien. Am physischen Pi laufen Studio und Kiosk mit 0.5.91; die Anzeige wurde neu geladen. Aufnahmebestand und Audio-/Modell-/Netzwerkeinstellungen unverändert. Anmeldung ist Standard, Raumgeräusche aktiviert, Ruhefrist 15 Minuten. Eine Betreiber-PIN wurde nicht vorgegeben und muss vom Nutzer gesetzt werden.

Ein achtsekündiger Test des neuen Pegelprozesses mit dem tatsächlichen Pi-Mikrofon lieferte Bereitschaft, drei Fortschrittsmeldungen und einen Aktivitätshinweis. Danach war der Prozess beendet und die Wartungssperre freigegeben. Es wurden ausschließlich diese Ereignisse ausgewertet, kein Ton gespeichert oder übertragen. Dies prüft den Mikrofonpfad, nicht die Zuverlässigkeit der Anwesenheitserkennung. [Bereinigter Messnachweis](microphone-smoke-0.5.91.json) · [Geräteeinstellungen am Pi](pi-policy-0.5.91.png).

Das saubere Image-Baupaket wurde mit 143 Dateien vorbereitet; kein SD-Image gebaut oder auf einer neuen Karte gestartet.

Noch vor Ort zu prüfen: Empfindlichkeit im tatsächlichen Meetingraum, echter NFC-Leser mit Talk/Meeting-Aufstellern, Microsoft-Anmeldung durch den Nutzer, tatsächlicher Netzwerkausfall und Talk mit echtem Mikrofon/Lautsprecher. Die automatische Abmeldung allein ist kein Anwesenheitsnachweis.

[Prüfnachweis 0.5.90](acceptance.json) · [Startbestätigung 1280×720](room-confirm-1280.png) · [Startbestätigung 1024×600](room-confirm-1024.png) · [PIN mit Tastatur 1024×600](room-pin-1024.png)

[Prüfnachweis 0.5.91](acceptance-0.5.91.json) · [Speichern 1024×600](room-save-1024.png) · [Speichern 1280×720](room-save-1280.png) · [Abschluss im CDB-Design](room-finish-cdb-1024.png) · [Abmeldevorwarnung](room-idle-warning-1024.png) · [Einstellungen mit Tastatur](room-standard-pin-1024.png)

Die aktuelle Aktionsprüfung und Touch-Dialoge sind unter [Abnahme 0.5.92](../touch-decisions-0.5.92/README.md) dokumentiert. Die Abnahme 0.5.91 oben beschreibt den damaligen, inzwischen ersetzten kombinierten Stoppen-/Abmeldeablauf.
