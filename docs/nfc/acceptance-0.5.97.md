# Konfigurierbarer NFC-Direktstart · 0.5.97

23.11.2026. Chris wünscht nach erfolgreicher Anmeldung sofortigen Start durch
Meeting- und Talk-Aufsteller und anschließend eine Einstellung dafür.

## Verhalten

- Zwei getrennte Optionen unter Einstellungen → Audio → NFC-Aufsteller.
  Standard bei frischer Installation und Upgrade: ausgeschaltet.
- Eingeschaltet + bereits angemeldet + keine offene Vorbereitung: eine gültige
  neue Auflage startet die vorhandene Aufnahme bzw. das native Voice-Gespräch.
  Talk verwendet die kontogebundene gespeicherte Wissensauswahl.
- Ohne Anmeldung: Login und Vorbereitung. Anmeldung allein startet weiterhin
  kein Audio. Auch Wiedererkennung während einer offenen Vorbereitung startet
  nicht automatisch. Bestätigen oder Abbrechen, dann bewusst neu auflegen.
- Zwei Sekunden leeres Lesefeld nach Abbrechen, manuellem Stoppen oder einer
  Einstellungsänderung. Intern bleiben die vorhandenen 1,5 Sekunden bestätigte
  Abwesenheit und 0,5 Sekunden bestätigte Präsenz maßgeblich.
- Keine Doppelstarts bei gehaltenem Tag, kein Moduswechsel während Aufnahme,
  Pause oder Gespräch. Abnehmen beendet nur die eigene NFC-Aktivität.
- Fehlgeschlagener Direktstart öffnet die Vorbereitung mit dem konkreten Hinweis;
  nach Behebung ausdrücklich starten. Kein automatischer Wiederholungsversuch.

## Nachweise

- 65 Python-Prüfungen bestanden: Leser, NFC, Raum-/Aktivitätsregeln, Image-Export.
  Neue Prüfungen decken beide direkten Startpfade, alte Bestätigung, Login,
  Abbrechen und erneutes Aufstellen, Doppelstarts, belegte Geräte, Betreiberrechte,
  Speichern pro Modus, fehlgeschlagenes Speichern und Upgrade-Standard ab.
- 152 JavaScript-Prüfungen bestanden.
- Chromium-Browser: Beide Schalter einzeln eingeschaltet, Zustand über die API
  und gespeicherte Einstellungen verifiziert. Eine neue simulierte Auflage
  startete über den tatsächlichen Aufnahmeprozess ausschließlich künstliches PCM;
  keine Vorbereitung offen, genau die NFC-Aufnahme als Besitzer zugeordnet.
  Aufnahme anschließend gestoppt. [Einstellungen 1024 × 600](direct-start-1024.png).
- Einstellungen im echten Browser bei 1024 × 600 und 1280 × 720 geprüft:
  beide Schalter sichtbar, 56 Pixel hoch und nach Speichern aktiv.
- Signierte 0.5.97 aus `cc2c7a2` auf dem freien Pi installiert, 150 Dateien
  verifiziert, Kiosk neu gestartet. Aufnahmebestand, bestehende Einstellungen
  und Tag-Zuordnungen erhalten. Die persönliche Anmeldung endet wie vorgesehen
  beim App-Neustart; Chris wurde vorher darauf hingewiesen.
  [Installation](097-deployment.json).
- Auf ausdrücklichen Wunsch beide Direktstart-Optionen über die normale API
  eingeschaltet. Gespeicherte Werte und unveränderte Tags geprüft; Leser bereit,
  kein Audio aktiv. [Geräteeinstellung](097-configuration.json).
- Neues Image-Baupaket vorbereitet, 157 Quell-Hashes verifiziert. Kein neues
  SD-Image gebaut oder gebootet.
- Kein echtes Mikrofon oder Voice-Backend für diese Prüfung verwendet. Der
  persönliche Direktstart von Talk/Meeting vor Ort bleibt separat zu erproben.

## Update und neue SD-Karte

Reines App-Update, keine Laufzeit- oder OS-Änderung. Die bestehende private Datei
`nfc-tokens.json` erhält beim bewussten Speichern lediglich das optionale Objekt
`direct_start` mit getrennten booleschen Werten für Talk und Meeting. Fehlende
oder ungültige Werte werden als ausgeschaltet behandelt. Tags bleiben erhalten.
Bei fehlgeschlagenem Speichern wird der Zustand im Speicher zurückgesetzt.
Alle App-Dateien sind bereits durch die bestehenden Update-/Image-Positivlisten
abgedeckt. Private Tags, Einstellungen und Konten werden nicht ins Baupaket
exportiert. Ein vorbereitetes Baupaket ist kein gebautes oder hardwaregeprüftes
SD-Image.
