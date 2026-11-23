# Raummodus: Anmeldung, NFC und Offline-Bedienung

Stand: 23.11.2026, untersucht an Recorder Studio 0.5.89. **Bedienkonzept, noch nicht implementiert oder auf den Pi ausgerollt.**

Verbindliche Nutzerentscheidung: Im gemeinsam genutzten Raummodus ist eine Anmeldung erforderlich. Gastaufnahmen bleiben zunächst ausgeschaltet. Ein Talk-/Meeting-Aufsteller wählt eine Aktion; seine Kennung ist kein Nachweis einer Benutzeridentität.

## Aktueller Stand

- `StudioApp.nfc_start()` meldet bei Talk ohne Konto „Für Talk zuerst beim Brain anmelden.“ Es öffnet keinen geführten Anmeldeablauf.
- NFC-Meeting verwendet den bestehenden Aufnahmestart. Bei gewählter Brain-Verarbeitung ist ein gespeichertes Konto nötig. Bei rein lokaler Verarbeitung ist eine Anmeldung bisher keine grundsätzliche Voraussetzung.
- Nach einem gesperrten NFC-Start muss der Aufsteller entfernt und erneut aufgelegt werden. Ein liegen gebliebener Aufsteller löst keinen späteren Start aus.
- Der Kontodialog bietet bereits QR-Code, Microsoft-Eingabecode und Abmelden. Kontowechsel während Aufnahme/Pause oder Live-Gespräch sind gesperrt.
- Die lokale Bibliothek, Suche und Meetingdateien sind gerätebezogen. Cloud-Verarbeitungsaufträge sind bereits an Konto und Firmenumgebung gebunden; diese Bindung ersetzt keine Zugriffstrennung der lokalen Bibliothek.
- 13 vorhandene NFC- und Anmeldesperren-Tests wurden bei der Untersuchung erfolgreich ausgeführt. Dies ist keine neue Abnahme eines physischen NFC-Lesers.

## Vorgeschlagener Ablauf am Gerät

### Niemand angemeldet

Die Startseite zeigt „Mit Brain anmelden“, Talk und Meeting als Einstiege sowie den Verbindungsstatus. Persönliche Aufnahmen, Titel, Wissensbereiche und Gesprächsverläufe sind nicht sichtbar. Das Betätigen eines Einstiegs öffnet die dazu passende Anmeldung; es startet noch kein Mikrofon.

### Talk oder Meeting auflegen

1. Bekannten Aufsteller erkennen und groß „Talk erkannt“ bzw. „Meeting erkannt“ anzeigen.
2. Ohne Konto den vorhandenen QR-Anmeldedialog öffnen: „Melde dich an, um dein Gespräch/deine Aufnahme zu starten. Lass den Aufsteller liegen.“
3. Nach erfolgreicher Anmeldung Name und Firmenumgebung zeigen. Bei Talk die gültige Wissensauswahl des Kontos laden; wenn keine Auswahl vorliegt, direkt zur Auswahl führen.
4. Mit „Gespräch starten“ bzw. „Aufnahme starten“ ausdrücklich fortsetzen. Während einer möglicherweise längeren Anmeldung beginnt keine Aufnahme automatisch.
5. Die gestartete Aktivität übernimmt der bestehende Recorder-/Live-Dienst. Aufsteller abnehmen beendet wie bisher nach bestätigter Abwesenheit nur die von diesem Aufsteller gestartete Aktivität.

Ist schon jemand angemeldet, zeigt der Einstieg vor dem Start „Weiter als [Name]“ und „Anderes Konto“. So ist erkennbar, unter welchem Konto die neue Sitzung läuft. Ein NFC-Aufsteller kann kein anderes Benutzerkonto übernehmen.

Die Startabsicht besitzt eine eindeutige Kennung und einen begrenzten Gültigkeitszeitraum. Abbrechen, Abnehmen, Kontowechsel, Geräte-Neustart und ein veralteter Leserzustand verwerfen sie. Eine verspätete Anmeldung oder wiederkehrende Internetverbindung startet keine Aufnahme. Ein dadurch angelegter Anmeldeversuch wird beim Abbrechen invalidiert; ein unabhängig begonnener Kontodialog darf nicht versehentlich übernommen werden.

### Sitzung beenden und Gerät weitergeben

- „Fertig & abmelden“ ist vom normalen Betrieb aus direkt erreichbar.
- Läuft noch eine Aufnahme oder ein Gespräch, erklärt die Bestätigung konkret „Aufnahme stoppen und abmelden“ bzw. „Gespräch beenden und abmelden“. Erst nach erfolgreichem Beenden und Sichern wird abgemeldet.
- Nur den Aufsteller abzunehmen meldet nicht sofort ab: Ergebnisse und nächste Schritte bleiben für die aktuelle Person erreichbar.
- Nach dem Abmelden wird wieder die neutrale Startseite gezeigt. Verläufe, Entwürfe, Wissensauswahl und gekoppelte persönliche Anzeigen werden aus der sichtbaren Sitzung entfernt; Aufnahmen werden nicht gelöscht.
- Vorschlag: konfigurierbare automatische Abmeldung nach Inaktivität mit sichtbarer Vorwarnung. Keine automatische Abmeldung während Aufnahme, Pause oder aktivem Gespräch. Die genaue Frist ist noch festzulegen.

## Fehlendes Internet

| Zustand | Verhalten im Raummodus |
| --- | --- |
| Kein Konto und keine Verbindung | Anmeldung ist nicht möglich. WLAN-Einstieg und „Erneut prüfen“ anbieten; keine Gastaufnahme und kein Talk. |
| Bereits bestehende bestätigte Sitzung, Internet fällt aus | Konto bleibt zugeordnet. Meeting kann bei erfüllten lokalen Aufnahmevoraussetzungen weiterlaufen bzw. starten. Keine neue Identität aus einer NFC-Kennung ableiten. |
| Aufnahme läuft, Internet fällt aus | Lokal weiter aufnehmen. Deutlich „Aufnahme läuft · lokal gespeichert“ anzeigen; keinen Fehler über die laufende Aufnahme suggerieren. |
| Meeting beendet, Brain nicht erreichbar | „Aufnahme gespeichert · wartet auf Brain“. Wahlweise explizit lokal verarbeiten, wenn beide benötigten lokalen Modelle betriebsbereit sind. Keine stille Änderung der gespeicherten Verarbeitungsvorgabe. |
| Talk ohne erreichbaren Brain-Dienst | Erklären, dass das Gespräch eine Verbindung benötigt; WLAN/erneut prüfen anbieten. Offline-Transkription bedeutet keine Offline-Verfügbarkeit des Brain-Gesprächs. |
| Während der Wartezeit abgemeldet | Aufnahme und Auftrag behalten ihre ursprüngliche Kontozuordnung. Lokale Verarbeitung kann unabhängig laufen. Weitere authentifizierte Cloud-Schritte warten auf dasselbe Konto. Ein bereits angenommener Serverauftrag kann dort weiterlaufen; neue lokale API-Zugriffe benötigen wieder eine passende Anmeldung. |

„Sitzung abgelaufen“, „kein Netzwerk“, „Brain nicht erreichbar“, „Modell fehlt“ und „Mikrofon fehlt“ benötigen unterschiedliche, konkrete nächste Schritte. Eine neue Anmeldung benötigt Internet; das bloße Wiederherstellen eines alten Benutzernamens darf keine neue Raum-Sitzung eröffnen.

## Voraussetzung: Trennung der Daten nach Konto

Vor Freigabe des Raummodus müssen lokale Aufnahmen, Texte, Aufgaben, Exporte, Audioabrufe, Suche, Warteschlange, Übertragungen und Browserentwürfe dem jeweiligen Konto/Firmenkontext zugeordnet und auf dem Server geprüft werden. Nur Zeilen in der Oberfläche auszublenden reicht dafür nicht aus.

Bestehende Aufnahmen ohne eindeutige Zuordnung werden erhalten und nicht automatisch dem nächsten angemeldeten Benutzer zugeschlagen. Eine administrative Zuordnung bzw. ein ausdrücklich freigegebener Altbestand ist separat zu entwerfen. Abmelden muss persönliche Bildschirmkopplungen und Sitzungsdaten berücksichtigen. Geräteverwaltung und Netzwerkeinrichtung benötigen einen definierten Betreiberzugang; eine Administrations-PIN ersetzt keine Firmenanmeldung und berechtigt nicht automatisch zu persönlichen Meetinginhalten.

Der neue Modus wird bewusst als Geräteoption eingeführt. Das bestehende persönliche Gerät wird durch ein Update nicht ungefragt auf Raumbetrieb umgestellt.

## Reihenfolge der Umsetzung und Abnahme

1. Kontozuordnung, Zugriffsschutz und Umgang mit vorhandenen Aufnahmen festlegen und implementieren; bei bestehenden Geräten und leerem Erststart prüfen.
2. Gemeinsamen Ablauf für Touch und NFC bauen: Anmeldung, gewünschte Aktion fortsetzen, Abbruch und eindeutige Statusanzeige.
3. Verständliche Offline-Zustände, gespeicherte Auftragsbindung und geführten Wiedereinstieg nach Anmeldung ergänzen.
4. Sitzung beenden, Betreiberzugang und automatische Abmeldung ergänzen; 1280 × 720 und 1024 × 600 mit Touch prüfen.
5. Mit echtem NFC-Leser vor Ort abnehmen: Talk/Meeting, unbekannter Tag, langsame/abgebrochene Anmeldung, Tagwechsel, Abnehmen vor Loginabschluss, USB-Ausfall, Netzwerkverlust, Kontowechsel, ausstehende Verarbeitung und Neustart mit aufgelegtem Tag.

Die Umsetzung benötigt ein eigenes Release einschließlich Datenmigration und Rollback-Bewertung. App-Update und neues SD-Image müssen dieselben Regeln und Werkseinstellungen enthalten. Dieses Konzept ändert keine laufende Pi-Konfiguration und erzeugt keine Druck- oder Image-Dateien.
