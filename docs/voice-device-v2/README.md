# Pi-Gerätebedienung im Gespräch

Stand: 25.11.2026. Erweiterung für ein angemeldetes, laufendes Talk-/Voice-One-Gespräch.
Die Funktionen müssen im Pi und im zentralen Voice-Dienst vorhanden sein. Eine
neue Sitzung handelt `device_tools_v2` aus; ein älterer Server liefert weiterhin
nur Timer/Erinnerungen. Keine lokale Offline-Spracherkennung für diese Befehle.

| Beispiel | Verhalten |
|---|---|
| „Mach lauter / leiser.“ | +10 / −10 Prozentpunkte am ausgewählten Pi-Ausgang, auf 0–100 begrenzt. |
| „Stelle die Lautstärke auf 40 Prozent.“ | Absoluter Wert; positiver Wert hebt die Lautsprecher-Stummschaltung auf. |
| „Schalte den Lautsprecher stumm / wieder ein.“ | Ändert nur die Wiedergabe. Mikrofon bleibt unverändert. Bei 0 % zusätzlich eine positive Lautstärke anfordern. |
| „Wie laut bist du eingestellt?“ | Aktuelle Lautstärke und Stummschaltung vom Gerät lesen. |
| „Bin ich angemeldet? Welche Module sind verbunden?“ | Kontoanmeldung ohne Namen; ausgewähltes Mikrofon und Lautsprecher, NFC-Zustand/Zuordnung, ReSpeaker-LED-Zugriff, USB-Zusatzdisplay. |
| „Wie viel Speicher ist frei? Arbeiten wir lokal?“ | Freie Bytes und konfigurierte Verarbeitung für Transkription/Zusammenfassung. Kein Versprechen, dass Modelle vollständig funktionieren. |

Die Auskunft ist eine **Momentaufnahme**, kein automatischer Funktionstest.
„Display erkannt“ belegt keine sichtbare Anzeige; „Mikrofon erkannt“ keine
akustische Qualität. Fehler eines Moduls ergeben „unbekannt“, statt alle anderen
Ergebnisse zu verwerfen. Keine Testaufnahme, USB-Neuinitialisierung oder Ausgabe
eines Testtons durch die Statusabfrage. Kein pauschales „alles funktioniert“.
Stumm oder 0 % bedeutet, dass auch die gesprochene Bestätigung nicht hörbar ist;
am Bildschirm oder mit einer erneuten positiven Lautstärke lässt sich das ändern.

## Grenzen und Wiederholungen

Die grundlegenden Werkzeuge: `set_device_volume`, `adjust_device_volume`,
`set_device_mute`, `get_device_status`. Die geführten Ergänzungen stehen unten. Kein beliebiger Befehl, Dateipfad,
Ausgangswechsel, Mikrofonwechsel, Neustart oder Abmelden. Die Lautstärke ist eine
normale Gesprächsbedienung; die übrigen Einstellungs-/Betreibersperren bleiben.
Ein laufender Testton/Alarm blockiert Änderungen wie bisher.

Die bestehende Sitzung bindet Aufträge an Konto, Mandant und Session-Schlüssel.
Nach Gesprächsende/Kontowechsel werden keine weiteren Aktionen ausgeführt. Ein
stummer Gesprächspartner ist kein abgemeldeter Nutzer. Ohne Anmeldung entsteht
kein Voice-Gespräch; diese Funktion umgeht den Raummodus nicht.

`voice-device.sqlite3` speichert einen unbestätigten Beleg **vor** genau einem
Hardwareversuch. Erst nach Rücklesen folgt Erfolg. Ein Absturz zwischen beidem
bleibt unbestätigt; erneute Zustellung erhöht die Lautstärke niemals nochmals.
Gleiche ID mit verändertem Auftrag wird abgelehnt. Belege sind sitzungsgebunden,
enthalten keine Gesprächsinhalte und werden nach sieben Tagen bei weiteren
Aufträgen bereinigt. Es gibt keine Wiederholungsgarantie über neue Sitzungen.

## Auslieferung / Image

App-Update: neue Python-Datei unter `services/` und Hilfe unter `studio/help/`
liegen in der vorhandenen Positivliste. Keine neue Runtime, Root-Rechte,
Systemdienste oder Bootänderungen. SQLite wird leer beim ersten Appstart erstellt.
Die vorhandenen Audiovorgaben bleiben erhalten.

Frische SD-Karte: dieselben versionierten Dateien werden vom Image-Bau übernommen;
keine Live-Datenbank oder Anmeldung kopieren. Das bereits gebaute **1.0.0-rc1-Image
enthält diese Änderung noch nicht**. Ein neuer Bau samt SD-Bootabnahme bleibt Teil
der V1-Freigabe. Das ist keine nachträgliche Freigabe des bisherigen Images.

TQS muss v2 ausliefern, bevor diese Befehle im Gespräch auftauchen. BFF-Polling und
Quittungsroute bleiben unverändert. Alte v1-Pi-Sitzungen und normale/Portal-Clients
bekommen die neuen Werkzeuge nicht. Keine Änderungen an Azure-Modellen nötig.

## Erweiterte Befehle (ebenfalls rc2)

| Beispiel | Verhalten |
|---|---|
| „Zeig den Timer groß.“ | Öffnet den gewünschten sichtbaren Timer am Pi und wählt ihn für das USB-Display. Bei mehreren Timern fragt der Agent nach. |
| „Zeig die Uhr / Zurück zur Uhr.“ | Große Uhr am Pi und Uhrdarstellung am USB-Display. Timer laufen weiter, fällige Alarme haben Vorrang. |
| „Ist das Gerät bereit fürs Meeting?“ | Anmeldung, Mikrofon, Speicher, Einrichtung, Lautsprechereinstellung und Hardware-Mute als technische Momentaufnahme; kein Start einer Aufnahme. |
| „Zeige die Hilfe zur Verkabelung.“ | Lokale Anleitung direkt im Dialog. Talk bleibt verbunden; Hilfe lässt sich wieder schließen. |
| „Prüfe den Lautsprecher.“ | Große Auswahl: im Gespräch bleiben oder Gespräch beenden. Danach Testton ausdrücklich starten und „Ja, gehört“ / „Nein, nicht gehört“ wählen. |
| „Für den Umzug vorbereiten.“ | Gespräch gezielt am Display beenden, laufende Vorgänge abschließen, dann separate Ausschaltbestätigung. Kein Herunterfahren durch den Sprachauftrag. |

Zusätzliche Werkzeuge: `show_device_timer`, `show_device_clock`,
`check_meeting_readiness`, `open_device_help`, `prepare_speaker_test`,
`prepare_device_move`. Jede Eingabe ist begrenzt; Hilfe erlaubt ausschließlich
bekannte lokale Themen. Der Auftrag bestätigt zunächst nur „Ansicht angefordert“,
keine beobachtete Anzeige. Offene Anmelde-/Speicherdialoge werden nicht verdeckt.
Unangezeigte Ansichtsaufträge verfallen nach zwei Minuten, geöffnete nach zehn.
Kontowechsel/Abmeldung widerrufen sie. Die LCD-Auswahl gilt bis zum nächsten
Anzeigebefehl, zur Abmeldung oder höchstens eine Stunde; Alarme bleiben vorrangig.

Hörtest und Umzugsvorbereitung laufen nach einem ausdrücklich am Display
beendeten Gespräch weiter. Eine alte Bestätigung kann niemals ein später
gestartetes Gespräch beenden. Testtöne behalten die Betreiber- und Aktivitätssperren.
Nur die tatsächliche Person kann den Hörtest bestätigen; eine andere oder
unvollständige Testausgabe wird nicht als Bestätigung angenommen.

Ansichten und temporäre Auswahl sind nur im Arbeitsspeicher, keine zusätzlichen
Kundendaten im Image. Die neue UI verwendet große Entscheidungskacheln und einen
festen Schließen-Button bei längeren Anleitungen. App-Update und Clean-Image
enthalten `services/voice_actions.py` und `studio/voice-actions.{js,css}` automatisch.
Keine neue Firmware für das USB-Display nötig: bestehende Uhr-/Einzeltimeransichten
verwenden die gefilterte, weiterhin nur lesbare Projektion.

## Prüfung am 25.11.2026

- 168 Pi-Tests gemeinsam bestanden: Audio, persistente Auftragsbelege, Status-Datenschutz,
  geführte Geräteabläufe, Gesprächs-/Kontoende, Timer/LCD, Studio-HTTP sowie Update/Image.
- 171 bestehende JavaScript-Prüfungen bestanden.
- TQS: 37 erweiterte Gerätewerkzeug-Tests bestanden; zusätzlich wurden vor der
  Erweiterung 214 Tests zu Gerätevertrag, Live, Reconnect und Portal-Keys geprüft.
- Ansichten bei 1024×600 (hell) und 1280×720 (CDB) geprüft. Entscheidungskacheln
  148 px hoch, feste Schließen-Aktion mindestens 56 px. Längere Hilfe bleibt
  scrollbar und behält ihre Leseposition beim Statusabruf. Keine verdeckten Aktionen.
- [Lautsprechertest, 1024×600](screenshots/speaker-1024.png),
  [Umzugsvorbereitung, 1280×720](screenshots/move-1280.png),
  [Verkabelungshilfe, 1024×600](screenshots/help-1024.png).
  Diese Ansichten stammen aus einer isolierten UI-Vorschau, nicht vom physischen Pi.
- Am echten Pi: ausgewählten Lautsprecher um einen Prozentpunkt reduziert,
  zurückgelesen, denselben Auftrag wiederholt (keine zweite Änderung), danach
  ursprüngliche Lautstärke und Mute-Zustand wiederhergestellt. Isolierter Executor;
  keine Aufnahme, kein Ausgangswechsel und kein Neustart.

Zum Zeitpunkt dieses Implementierungscommits läuft der Pi weiterhin mit 1.0.0-rc1.
Die vollständige App-Version 1.0.0-rc2 enthält alle oben beschriebenen Befehle.
Rollout und gesprochene Endabnahme folgen nach erfolgreicher Server-CI.
Kein neues SD-Image gebaut; ein sauberer Image-Bausatz ist keine Bootabnahme.

Rollout: [TQS #2915](https://github.com/BIK-GmbH/cdb_tqs/pull/2915),
[Nutzerhinweis webOS #2187](https://github.com/BIK-GmbH/cdb_webos/pull/2187).
Ziel ist die am Pi konfigurierte Umgebung `staging.cdbos.de`.
