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

Nur vier streng begrenzte Werkzeuge: `set_device_volume`, `adjust_device_volume`,
`set_device_mute`, `get_device_status`. Kein beliebiger Befehl, Dateipfad,
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

## Sinnvolle nächste Ausbaustufen

- „Zeig mir den Timer groß“ und „Zurück zur Uhr“: reine Anzeigeaktion am Pi und
  Zusatzdisplay, ohne laufende Timer zu verändern.
- „Prüfe den Lautsprecher“: kurzer angekündigter Testton, danach Rückfrage, ob er
  tatsächlich hörbar war; nur wenn kein Meeting/Gespräch dadurch gestört wird.
- „Ist das Gerät bereit fürs Meeting?“: Anmeldung, Platz, Mikrofon, Mute und
  Ausgabe einzeln prüfen; Aufnahmebeginn bleibt eine eigene bewusste Aktion.
- „Zeige die Hilfe zur Verkabelung“: passende lokale Hilfe öffnen.
- „Für den Umzug vorbereiten“: erst sichere Abschlussübersicht, dann große
  Bestätigung am Display für Abmelden/Herunterfahren. Kein spontaner Strombefehl.

Diese Ausbaustufen sind Ideen, keine bereits verfügbaren Befehle.

## Prüfung am 25.11.2026

- 65 gezielte Pi-Tests: Audio, Auftragsbelege, Status-Datenschutz,
  Gesprächs-/Kontoende, v1/v2-Aushandlung und vorhandene Timer.
- 67 Studio-Integrationstests ohne Fehler.
- 214 TQS-Tests: neuer Vertrag und bestehende Live-/Portal-Key-Szenarien.
- Am echten Pi: ausgewählten Lautsprecher um einen Prozentpunkt reduziert,
  zurückgelesen, denselben Auftrag wiederholt (keine zweite Änderung), danach
  ursprüngliche Lautstärke und Mute-Zustand wiederhergestellt. Keine Aufnahme,
  kein Ausgangswechsel und kein Neustart; isolierte Testinstanz des Executors.

Das laufende Pi-Studio wurde dabei nicht ersetzt (weiter 1.0.0-rc1). Die neue
App-Version 1.0.0-rc2 ist für den gemeinsamen Rollout vorbereitet. Gesprochene
Endabnahme nach TQS-Freigabe und Pi-Update noch offen. Kein neues SD-Image gebaut.
