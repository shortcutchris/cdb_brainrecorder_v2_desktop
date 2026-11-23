# NFC-Abnehmen und Statuszeile · 0.5.98

23.11.2026. Chris wünscht einen NFC-Hinweis außerhalb der Aufnahme-Seitenleiste
und getrennte Optionen für automatisches Beenden von Talk und Meeting.
Zusätzlich ist die [Timeranzeige im Raummodus korrigiert](timer-display-0.5.98.md).
Die [Idee einer persönlichen NFC-Anmeldung](../cdb-integration/deferred-nfc-login.md)
ist dokumentiert, nicht implementiert.

## Bedienung

Einstellungen → Audio → NFC-Aufsteller enthält pro Modus zwei Schalter:
Direktstart und Beenden beim Abnehmen. Direktstart bleibt bei frischen Geräten
zunächst aus; Beenden beim Abnehmen bleibt zur Kompatibilität zunächst ein.
Die bereits bewusst gespeicherte Direktstart-Auswahl wird erhalten.

Bei eingeschaltetem Beenden stoppt eine stabil erkannte Abwesenheit von 1,5 Sekunden
nur die eigene NFC-Aktivität. Bei Talk wird das native Audio unmittelbar geschlossen
und anschließend die zugehörige Backend-Sitzung beendet. Ausgeschaltet bleibt der
Modus aktiv und wird am Bildschirm beendet. Ein anderer Aufsteller kann ihn nicht
ersetzen. Leserfehler gelten weiterhin nicht als Abnehmen.

Änderungen erfordern ein freies Gerät und gegebenenfalls die Betreiber-PIN. Sie
werden pro Modus gespeichert. Fehler beim Speichern setzen den Zustand zurück.
Der Hinweis erscheint nur für die aktive NFC-Aktivität in der vorhandenen
Statuszeile: bei Meeting unter den Notizen, bei Talk über den Gesprächsbuttons.

## Prüfung

- 106 Python-Tests bestanden: NFC-Lesen und Besitz, Konfigurationsspeicherung,
  Standardwerte bei Installation/Upgrade, ungültige Eingaben, Schreibfehler,
  Sperren bei laufenden Aktivitäten, Raumregeln, LCD-Export und Image-Export.
- Die Talk-Kette NFC-Abnehmen → StudioApp → LiveConversation ist mit künstlichem
  Audio und einem simulierten Backend geprüft: Audio geschlossen und Close-Aufruf
  für genau die eigene Sitzung. Kein echtes Gespräch ausgelöst.
- 152 JavaScript-Tests bestanden.
- Echter Chromium bei 1024 × 600 und 1280 × 720: beide neuen Schalter betätigt,
  gespeicherte Werte geprüft; alle vier Schalter bleiben groß und erreichbar.
- Simuliertes NFC startete den tatsächlichen Aufnahmeprozess mit künstlichem PCM.
  Nach Abnehmen bei ausgeschalteter Option blieb die Aufnahme aktiv, auch pausiert.
  Anschließend am Bildschirm gestoppt. Keine Mikrofonaufnahme.
- Aufnahmetaste, Dauer und Pause/Stumm behalten beim Ein-/Ausblenden des Hinweises
  exakt ihre Position. Bildschirmtastatur und Pause bei 1024 × 600 geprüft.
  Talk-Statuszeile bei beiden Größen mit simuliertem Browserstatus geprüft.
- [Einstellungen](removal-settings-098-1024.png),
  [Aufnahmeanzeige](recording-status-098-1024.png),
  [Pause mit Tastatur](recording-keyboard-098-1024.png).

## Auslieferung

Lokale Prüfungen abgeschlossen. Signiertes Pi-Update und sauberes Image-Baupaket
werden aus diesem Commit erzeugt; der tatsächliche Auslieferungsnachweis wird
nach Installation ergänzt. Keine Aufnahme und kein reales Voice-Gespräch werden
für die Prüfung am Benutzergerät gestartet.

## Bestehendes Gerät und neue SD-Karte

Reines App-Update, keine neuen Pakete, Dienste oder Laufzeitänderungen.
Das optionale Objekt `stop_on_remove` in der privaten `nfc-tokens.json` speichert
boolesche Werte je Modus. Fehlende oder ungültige Werte erhalten das bisherige
Beenden; nur explizites `false` schaltet es aus. Initiales Laden schreibt keine
Datei um. Tags, Direktstart und übrige Konfiguration bleiben erhalten.
Alle App-Dateien einschließlich lokaler Hilfe sind bereits über bestehende
Update-/Image-Positivlisten abgedeckt. Private Daten und Zuordnungen gehen nicht
ins saubere Baupaket ein. Ein Baupaket ist kein gebautes oder bootgeprüftes Image.
