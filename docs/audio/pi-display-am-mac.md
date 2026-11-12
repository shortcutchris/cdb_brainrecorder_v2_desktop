# Den Pi-Touchscreen am Mac bedienen

Öffne am eingerichteten Mac den Schreibtisch-Starter **Recorder Studio – Pi-Display**. TigerVNC zeigt denselben Bildschirm wie das Gehäuse. Klicke mit der Maus auf eine Schaltfläche, wie du sie am Gerät antippen würdest. Tastatureingaben gehen an das aktive Fenster auf dem Pi. Mikrofonaufnahme und Testwiedergabe erfolgen weiterhin am Pi. Für die Hörprüfung der Soundbar muss jemand in Hörweite sein.

Das Schließen des TigerVNC-Fensters beendet die Freigabe für diese Sitzung. Zum erneuten Verbinden den Starter wieder öffnen.

## Einen weiteren Mac einrichten

1. Über den üblichen SSH-Zugang mit geprüftem Hostschlüssel am Pi anmelden. Der Benutzer muss der laufenden grafischen Sitzung gehören. Auf dem getesteten Raspberry Pi OS läuft labwc mit Wayland und installiertem `wayvnc`.
2. **TigerVNC Viewer** am Mac installieren, mit Homebrew über `brew install --cask tigervnc`.
3. Im Recorder-Studio-Repository `scripts/view_pi_display_macos.sh benutzer@pi-host` ausführen. Übliche SSH-Optionen für Hostalias, Schlüssel oder Proxy vor dem Ziel angeben. Das Skript verwendet den vorhandenen SSH-Schlüssel. Falls der lokale Port 15971 belegt ist, kann die Variable `CDB_DISPLAY_PORT` einen anderen freien Port vorgeben.
4. Zum Prüfen im Viewer **Einstellungen → Audio → Mikrofon** öffnen. Eine Testaufnahme beginnt erst beim Antippen des Testknopfs. Das Fenster zeigt das physische Display in seiner bestehenden Auflösung. Die Zwischenablage wird nicht übertragen.

Der Viewer verbindet sich über einen nur am Mac erreichbaren Port. SSH leitet diese Verbindung an einen privaten Unix-Socket des angemeldeten Pi-Benutzers weiter. Der Zugriff auf den Pi läuft über die SSH-Anmeldung. Für diesen Viewer ist kein zusätzliches VNC-Passwort nötig. Das Hilfsskript läuft auf dem Mac und gehört nicht zum App-Update oder SD-Image. Der Pi benötigt dafür keinen dauerhaft aktivierten VNC-Dienst.

Am 12. November 2026 am Gehäuse-Pi geprüft: TigerVNC auf dem Mac war mit der lokalen Sitzung auf `DSI-1` bei 1280 × 720 Pixeln verbunden.
