# Bluetooth-Audio am Raspberry Pi

Ab Recorder Studio 0.5.21: **Einstellungen → Audio → Bluetooth**.

## Lautsprecher koppeln

1. Lautsprecher einschalten und in Reichweite des Pi stellen. Falls er automatisch mit einem Handy verbindet, dort zunächst trennen.
2. Am Lautsprecher den Kopplungsmodus aktivieren. Bei Marshall hängt die genaue Taste und Haltezeit vom Modell ab; die Bluetooth-Anzeige signalisiert die Suche. Modellbezeichnung und Herstellerhandbuch sind maßgeblich.
3. Im Recorder gegebenenfalls **Bluetooth einschalten**, dann **Geräte suchen**. Die Suche endet spätestens nach 60 Sekunden oder durch **Abbrechen**. Gefundene und gespeicherte Geräte erscheinen auf direkt anwählbaren Seiten.
4. Das gewünschte Gerät auswählen und **Koppeln** drücken. Falls ein Code erscheint, mit dem Gerät vergleichen und bestätigen. Angeforderte PIN eingeben; über das Tastatursymbol ist die Touch-Tastatur verfügbar. Niemals einen nicht passenden Code bestätigen.
5. Warten, bis beim Gerät **Audio bereit** steht. **Als Lautsprecher** wählt genau dieses Gerät und öffnet die Lautsprechereinstellungen. Lautstärke setzen und **Testton am Pi** abspielen. Der Button ist erst aktiv, wenn der Pi einen echten Audioausgang dieses Geräts erkannt hat; er fällt nicht auf einen anderen Lautsprecher zurück.

**Status ab 0.5.22:** „Gekoppelt · nicht verbunden“ bedeutet nur gespeicherte Kopplung. „Verbunden · Audio fehlt“ bedeutet eine Bluetooth-Verbindung ohne verfügbaren Audioein- oder -ausgang. Erst „Audio bereit“ erlaubt die passende Audioauswahl. Ein reiner Lautsprecher aktiviert den Mikrofon-Shortcut nicht.

Für spätere Verbindungen genügt bei einem gespeicherten Gerät **Verbinden**. **Trennen** behält die Kopplung. **Kopplung entfernen** verlangt eine zusätzliche Bestätigung auf derselben Seite und erfordert danach erneutes Koppeln. Neu erfolgreich gekoppelte Geräte werden für die Wiederverbindung als vertrauenswürdig gespeichert.

## Mikrofon oder Freisprecheinrichtung

Ein Gerät kann nur als Mikrofon dienen, wenn es ein entsprechendes Audioprofil bereitstellt. Eine reine Musikbox stellt nicht automatisch einen Eingang bereit.

Beim verbundenen Gerät zeigt **Audiomodus** die tatsächlich vom Pi angebotenen Profile:

- **Musik**: hochwertige Lautsprecherwiedergabe (A2DP).
- **Gespräch**: Mikrofon und Lautsprecher gleichzeitig (HFP/HSP), abhängig vom Gerät mit geringerer Klangqualität.

Nach einem Profilwechsel **Mikrofon** öffnen, Geräte aktualisieren, das Bluetooth-Mikrofon auswählen und eine Testaufnahme machen. Unter **Lautsprecher** den passenden Ausgang auswählen. Das Live-Gespräch übernimmt diese vorhandenen Einstellungen. Ein Profilwechsel kann die verfügbaren Ein- und Ausgänge verändern; deshalb werden sie ausdrücklich gewählt.

## Bedienung und Grenzen

Während Aufnahme, Live-Gespräch oder Audiotest sind Bluetooth-Änderungen gesperrt. Während Suche, Kopplung und Verbindungswechsel sind neue Aufnahmen und Gespräche ebenfalls gesperrt. **Abbrechen** beendet die eigene Suche oder Kopplung; erst nach der Bereinigung wird freigegeben. Die Hintergrundverarbeitung vorhandener Meetings läuft weiter.

Die App sucht und koppelt vom Pi aus. Sie macht den Pi nicht dauerhaft öffentlich sichtbar und übernimmt nicht die systemweite Standardrolle für fremde Kopplungsanfragen. PIN- und Codebestätigungen sind an die gerade ausgewählte Kopplung gebunden, verfallen nach 60 Sekunden und werden nicht protokolliert.

Bei fehlendem Gerät: Einschalten, Kopplungsmodus neu aktivieren, Handyverbindung trennen und erneut suchen. Bei vorhandenem Lautsprecher, aber fehlendem Mikrofon: angebotene Audiomodi prüfen. Bluetooth-Reichweite und Funkstörungen können Gesprächsqualität beeinflussen; der Gerätetest bleibt entscheidend.

## Technik und Quellen

BlueZ über dessen System-D-Bus; eigener Agent mit `KeyboardDisplay`, keine automatische Bestätigung fremder Geräte. Abhängigkeit `dbus-next==0.2.3`. Audioausgabe und Profilwahl laufen über PipeWire/PulseAudio, Aufnahme über die vorhandene `pulse:`-Geräteunterstützung. Auf dem Pi waren BlueZ 5.82, PipeWire 1.4.2 und `libspa-0.2-bluetooth` bereits installiert. Es wurden keine globalen Bluetooth- oder WirePlumber-Regeln geändert.

- [BlueZ Agent API](https://bluez.readthedocs.io/en/latest/agent-api/)
- [BlueZ Device API](https://bluez.readthedocs.io/en/latest/device-api/)
- [WirePlumber Bluetooth-Konfiguration](https://pipewire.pages.freedesktop.org/wireplumber/daemon/configuration/bluetooth.html)
- [WirePlumber Audioprofil-Einstellungen](https://pipewire.pages.freedesktop.org/wireplumber/daemon/configuration/settings.html)

[Abnahme und Screenshots](bluetooth-0.5.21/README.md).

## Marshall EMBERTON II

Bei unserem Praxistest war die Kopplung gespeichert, der Audio-Verbindungsaufbau wurde aber abgebrochen. Nach erneutem Kopplungsmodus und Wiederverbinden erschien die Box als A2DP-Ausgang; beide Testtöne bei 25 % wurden vom Benutzer gehört. Die Kopplung musste dafür nicht gelöscht werden, zusätzliche Treiber waren nicht nötig. Ob zuvor eine andere Geräteverbindung die Ursache war, ist nicht belegt.

Bei erneutem Auftreten: mögliche Handyverbindung trennen, Bluetooth-Taste halten, bis die Anzeige langsam rot pulsiert, dann am Pi **Verbinden** wählen. Erst falls das nicht hilft, die Kopplung entfernen und neu koppeln. [Offizielle Anleitung für EMBERTON II](https://www.marshall.com/de/en/support/speakers/support-for-emberton-ii/how-to-connect-or-pair).
