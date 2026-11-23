# Touch-Entscheidungen und Aktionsprüfung · 0.5.92

23.11.2026 · Recorder Studio, Python-App auf dem Pi. Ziel: 1280 × 720 und 1024 × 600. Pi Studio für 3D-Modelle ist eine andere Anwendung.

Ausgangspunkt ist der [Nutzer-Screenshot](user-reference.png): eine fast leere, hohe Abmeldewarnung mit kleinen Tasten. Die einfachen Entscheidungen verwenden jetzt zwei große Kacheln mit Symbol, klarer Aktion und kurzer Folge. Formulare, Textvergleiche und Wissensauswahl behalten eine kompakte Aktionsleiste. Beide geprüften Themes (Blau/Hell und CDB) nutzen dieselben Größen. Mindesthöhe der Entscheidungskacheln: 164 px bei 600 px Bildschirmhöhe, sonst 196 px.

## Verbindliche Bedienregeln

1. Aufnahme, Pause und Live-Gespräch inklusive Verbindungsaufbau und Beenden sperren Abmelden und Kontowechsel. Erst separat stoppen/beenden, dann abmelden. Auch der Server verweigert eine alte Abmeldebestätigung; sie hat keine Stop-Berechtigung.
2. „Fertig & abmelden“, Kontodialog, Konto-Einstellungen und „Anderes Konto“ verwenden denselben Abschluss. Notizen aller bereits geöffneten Meetings werden vor der Abmeldung gespeichert, auch ein Entwurf aus einer früheren Ansicht. Fehler behalten Anmeldung und Entwurf. „Angemeldet bleiben“ bricht ab.
3. Die ausdrückliche Abmeldekachel der Ruhefristwarnung braucht keinen weiteren Dialog. Sie speichert und prüft ebenfalls erneut. Aufnahme/Pause/Gespräch/Wiedergabe unterbrechen weiter die automatische Abmeldefrist; danach beginnt sie vollständig neu.
4. Wiederholtes Tippen auf eine noch laufende Tastenaktion sendet sie nicht noch einmal. Die aktiven Start-/Stopp-/Stumm-/Pause-Steuerungen behalten ihre eigenen Sperren. Eingabe und Suche verlieren dadurch keine Zeichen oder Folgeanfragen.
5. Neustart und Herunterfahren haben große Bestätigungskacheln, sperren einander und prüfen nach dem Speichern erneut auf Aufnahme, Gespräch, Wiedergabe, Verarbeitung, Übertragung, Timer und Wartung. Kein Neustart/Poweroff wurde bei dieser Abnahme ausgeführt.
6. Fremdgestartetes Live schließt veraltete Modalfenster, stoppt lokale Wiedergabe und zeigt Gesprächsende/Stummschaltung. Reine Statusabfragen dürfen weiterlaufen.
7. Vor großen Entscheidungen verschwindet die Bildschirmtastatur. Die Ruhefrist ist auch mit der lokalen Zahlentastatur editierbar. Laufende Verarbeitung behält das beim Antippen gewählte Meeting und den gewählten Prompt, selbst bei späterem Ansichtswechsel.

## Durchsicht sämtlicher Ansichten und Dialoge

Diese Matrix beschreibt Code-/Zustandsprüfung; sie behauptet keine erneute reale Kopplung aller externen Geräte. Neue oder korrigierte Pfade sind zusätzlich durch automatisierte Tests und die unten genannten Browserabläufe abgesichert.

| Ansicht / Dialog | Erlaubt und gesperrt bei laufender Arbeit |
|---|---|
| Startseite, Talk-/Meeting-Vorbereitung, NFC-Start | Expliziter Start erst nach Anmeldung. Während Startanfrage kein weiterer Start, Kontowechsel oder Abbruch der Vorbereitung. Gerätebeschäftigung sperrt den Start. |
| Recorder, Pause, Stumm, Stop | Notizen und eigene Aufnahmesteuerung verfügbar. Bibliothek, Einstellungen, neue Aufnahme und Abmeldung gesperrt. Pause bleibt eine aktive Aufnahme. |
| Konto, Microsoft-Anmeldung, Anderes Konto | Kontoinformation darf gelesen werden; Abmeldung/Wechsel einschließlich alter Bestätigungen während Capture/Live gesperrt. Abmeldung speichert vor Kontotrennung. |
| Ruhefristwarnung | Zwei große Kacheln; Verlängern setzt volle Frist. Kein automatisches Abmelden bei Capture, Live oder Wiedergabe. |
| Live, Gesprächswissen, Verlauf, Suchton | Gesprächsende/Stumm verfügbar, Auswahl für aktives Gespräch nur lesbar. Audio-/Kontowechsel und Recorder gesperrt. Verbindungsaufbau und Ende gelten als belegt. |
| Bibliothek, Player, Meetingaktionen | Laufende Aufnahme blockiert Wechsel. Titel/Notizen bleiben bei Hintergrundverarbeitung editierbar; KI-Texte und Löschen des verarbeiteten Meetings gesperrt. |
| Notizen, Entwurf sichern/vergleichen, Export | Bestehende Speicher-/Konfliktprüfung bleibt aktiv. Fehlgeschlagenes Speichern blockiert Abmeldung; Entwurf bleibt lokal. Prozessziel vor dem Warten festgehalten. |
| Warteschlange, Wiederholen, Löschen, lokal verarbeiten | Laufende Jobs nicht löschbar. Veraltetes Löschen/Verarbeiten während Capture/Live wird serverseitig verweigert. Wiederholter Tastendruck wird unterdrückt. |
| Übertragen, Zielbereich | Übertragung hält Meeting und Zielbereich fest; wiederholtes Senden gesperrt. Konto-/Meetingbesitz wird serverseitig geprüft. Hintergrundaufträge behalten ihre Zuordnung. |
| Einstellungen, PIN, Ruhefrist, Raumgeräusche | Änderungen erfordern Geräteschutzfreigabe. Gerätekonfiguration während Capture/Live/Test/Wartung gesperrt. Werte vor asynchronem Speichern festgehalten. |
| Mikrofon, Probe, Lautsprecher, Ansagen | Eigene laufende Tests können beendet werden; neue konkurrierende Audiobelegung und Gerätewechsel gesperrt. Aufnahme und Live haben serverseitige Ressourcenprüfung. |
| Bluetooth | Kopplung/Profilwechsel blockieren Capture. Wiederholte Anforderungen gesperrt, Abbruch/Antwort auf eigene Kopplungsfrage bleibt möglich. |
| NFC, Aktivierungswort | Einrichtung nur im freien Zustand; NFC erhält zusätzlich unmittelbare Anfragesperre und gemeinsame Gerätebereitschaft. Abschalten/Beenden eines eigenen Tests bleibt möglich. |
| KI-Modelle, Download, Modelltest, Aktivierung | Installieren/Testen erst ohne konkurrierende Arbeit; keine Aktivierung ungeprüfter Modelle. Bestehende Jobs behalten ihre gewählte Verarbeitung. |
| Vorlagen, Design, eigene Themes | Löschbestätigung bleibt app-eigen. Neue Vorlage nicht durch Doppeltippen doppelt angelegt. Rein lokale Designwahl ändert keine Audio-/Kontodaten. |
| Bildschirmfreigabe, Handy-Fernbedienung | Neue Kopplung/Änderungen nur bei freiem Gerät; Freigaben haben vorhandene Konto-/Anfrageprüfung. Entkoppeln startet keine Aufnahme. |
| Timer, Erinnerung, Alarm | Eigene Anfragen und Revisionen verhindern doppelte Änderung. Alarm quittieren bleibt erreichbar; bei Aufnahme wird Ton zurückgestellt. Aktive Timer sperren Stromaktionen. |
| Geräteverwaltung, WLAN/Ersteinrichtung, Versionswechsel | Wartungs- und Serverprüfungen bleiben aktiv. Neustart/Herunterfahren prüfen nochmals nach Dialog/Speichern. Oberflächenneuladen während Capture/Live gesperrt. |

## Abnahme

- 151 JavaScript-Tests bestanden: wiederholte Tastenaktionen, unverlorene Suchanfragen, ursprüngliches Prozessziel, Abmeldung bei aktiver/pausierter Aufnahme, Live und Startübergang, Beginn einer Aufnahme während Bestätigung/Speichern, Speicher-/Serverfehler ohne Entwurfsverlust, gemeinsame Abmeldewege, Neustart/Shutdown-Rennen, Live-Fernstart und vorhandene UI-Zustände.
- 98 Python-Tests bestanden (`test_room_mode`, `test_studio`, `test_customer_image`, `test_device_shutdown`). Zusätzlich 81 gezielte Tests für Kontowechsel, App-Aktivität, Live, Fernsteuerung, NFC und Raumaktivität; eine Kontowechselprüfung wurde nach der letzten Änderung erneut ausgeführt und ist in beiden Läufen enthalten.
- Browser mit künstlichem Konto und künstlicher Audioquelle: Meeting vorbereiten/starten, Pause/Fortsetzen, gesperrte Abmeldung an beiden Einstiegen, Stoppen, Notizen eingeben, Tastatur, Abschluss abbrechen, Konto-Abschluss bestätigen, erneut anmelden und gespeicherte Notizen wiederfinden. Anfangs wurde beim Prüfen die kompakte Sitzungsliste statt der Detailantwort gelesen; Detailabruf bestätigt den gespeicherten Text.
- Beide Pi-Displaygrößen; Blau/Hell und CDB. Neustart und Herunterfahren nur öffnen und abbrechen. Ruhefristwarnung verlängert die Sitzung. PIN-Freigabe und Ruhefrist mit Tastatur geprüft.
- Kein echter Microsoft-Login, NFC-/Bluetooth-Hardware-Neukopplung oder externes Sprachmodell für diese UI-Abnahme. Diese Grenzen ersetzen keine bestehenden Funktionsnachweise. Kein SD-Image gebaut oder auf neuer Karte gebootet.

[Vorbereitung 1024](prepare-1024.png) · [Konto während Pause](paused-account-1024.png) · [Abschluss 1024](finish-1024.png) · [CDB-Abschluss 1280](finish-cdb-1280.png) · [Neustart 1024](restart-cdb-1024.png) · [Herunterfahren 1280](shutdown-cdb-1280.png) · [Ruhefristwarnung](idle-cdb-1024.png) · [Zahlentastatur](minutes-keyboard-1024.png)

## Auslieferung und neue SD-Karten

Alle Änderungen liegen in bereits zugelassenen App-Dateien und werden automatisch in signierte Aktualisierung und sauberes Image-Baupaket übernommen. Keine neue Abhängigkeit, kein Schemawechsel und keine Änderung der vorhandenen Pi-Einstellungen. Die vorhandene Ruhefrist, PIN und Geräuscherkennung bleiben erhalten. Bild- und Prüfnachweise sind ausschließlich Repository-Dokumentation und werden nicht auf den Pi kopiert.

Installiert am 23.11.2026 um 15:26 Uhr (Berlin) aus Commit `df176c5`: 136 App-Dateien signiert geprüft, Studio und Kiosk aktiv mit 0.5.92. Vorher kein angemeldeter Benutzer und keine aktive Aufnahme/Verarbeitung. Datenbank-/Audiodatei-Inventar, Audio-/Modellkonfiguration und Raumrichtlinie vor/nach Installation unverändert; Wartungssperre freigegeben. Ruhefrist bleibt 15 Minuten, Geräuscherkennung bleibt aktiviert, bisher nicht gesetzte Betreiber-PIN unverändert.

Physisches Display 1280 × 720: Startseite → Einstellungen → Geräteverwaltung → große Abschaltbestätigung → „Eingeschaltet lassen“ → Startseite. Kein Poweroff/Neustart ausgeführt. [Installationsnachweis](deployment.json) · [Dialog am echten Pi](pi-dialog-1280.png) · [Zurück auf der Startseite](pi-home-1280.png).

Ein sauberes Image-Baupaket mit 143 Dateien wurde vorbereitet. Es ist kein gebautes oder hardwaregeprüftes SD-Image.
