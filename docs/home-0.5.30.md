# Startseite · 0.5.30

Die App erhält eine eigene Startseite. Das Haus steht als erster Button in der linken Navigation; der bisherige Recorder bleibt ein eigener Bereich.

Sechs große Kacheln öffnen bestehende Bereiche: Aufnehmen, Live-Gespräch, Bibliothek, Warteschlange, Bildschirm und Einstellungen. „Bildschirm“ führt über den Monitor-Button in der linken Navigation zur eigenen Bildschirm-View mit der Code-Kopplung. Die Kacheln starten keine Aufnahme und kein Gespräch automatisch.

Die Seite übernimmt die aktuellen Theme-Farben, den festen Header, die feste 80-Pixel-Fußleiste und den 28-Pixel-Sockel der anderen Views. Im Inhaltsbereich liegen sechs Kacheln in drei Spalten und zwei Zeilen. Kleine Fenster wechseln auf zwei Spalten. Die Seite benötigt bei der Zielauflösung 1280 × 720 keine Scrollbars. Der Footer zeigt die tatsächlich geprüfte Recorder-Bereitschaft aus `currentReadiness()` mit identischem Statuslicht und Text sowie Aufträge in Verarbeitung. Eine früher abgeschlossene Einrichtung allein erzeugt keine grüne Bereitschaft.

## Navigation und Zustände

- Nach dem ersten erfolgreichen Statusabruf wird bei einem unbeschäftigten Gerät die Startseite geöffnet.
- Eine schon laufende Aufnahme bleibt im Recorder, ein laufendes Gespräch öffnet die Live-View.
- Wurde während des Verbindungsaufbaus bereits ausdrücklich navigiert, verändert der erste Statusabruf diese Wahl nicht.
- Spätere Statusabfragen ändern die aktuelle Seite nicht. Ein auf einem anderen Client gestartetes Live-Gespräch ersetzt eine sichtbare Startseite.
- Home und die Kacheln sind während Aufnahme oder Gespräch gesperrt. Die bestehenden Workspace- und Live-Sperren bleiben die maßgeblichen Prüfungen und sichern auch Zustandswechsel zwischen Klick und Navigation ab.
- Das Öffnen von Home speichert einen eventuell offenen Entwurf über den bestehenden Ablauf und beendet die Wiedergabe. Ein Wechsel zur Bibliothek behält deren zuletzt gewählte Aufnahme.
- Reine Hintergrundverarbeitung sperrt die Startseite nicht.

## Integration

Nach den bestehenden Studio-Skripten und Styles laden:

```html
<link rel="stylesheet" href="/home.css">
<script defer src="/home.js"></script>
```

Zusätzlich `studio/assets/house.svg` ausliefern. Das Haus-Icon ist eine einfache projektspezifische SVG-Geometrie ohne externe Abhängigkeit. Der bestehende `#home`-Recorderbutton bleibt unverändert; die neuen IDs sind `#start-open` und `#start-view`.

## Prüfung

`node --test tests/js/home.test.cjs` prüft elf Fälle: Initialroute, Aufnahme- und Live-Wiederaufnahme, direkte Bereichswahl, Entwurfs-/Wiedergabeablauf, Bildschirm-Shortcut, Polling-Stabilität, Navigation vor Verbindungsaufbau, Entsperren nach Aufnahme, Live-Race Live-Start durch einen anderen Client und Übereinstimmung mit der tatsächlichen Recorder-Bereitschaft. Die Browserprüfung bei 1280 × 720 erfolgt im integrierten Gesamtstand vor Auslieferung.
