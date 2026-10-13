# Mira: Sender und Empfänger – Codeprüfung

Stand der ursprünglichen Untersuchung: 13.10.2026. Die Textanzeige mit Kopplung
und Heartbeat ist inzwischen in [Studio 0.5.30](display-0.5.30/README.md) umgesetzt.
Die folgenden Abschnitte dokumentieren den untersuchten Mira-Prototyp und die
weiterführenden Ideen, insbesondere noch offene Bild-/Toolcall-Unterstützung.

## Gefundene Implementierung

Der passende lokale Prototyp liegt unter
`/Users/chris/Dropbox/git_reps_v4/mira/desktop_mira/src/mira_desktop/`.
Der Ordner `mira_live_communicator` ist hier leer. Im Desktop-Prototyp wurde keine
eigene Git-Metadatenstruktur gefunden.

| Quelle | Vorhandene Funktion |
| --- | --- |
| `remote/display.py`, `RemoteDisplayServer` | Browseranzeige, sechsstelliger Code, HTTP-Endpunkte und Ereignispuffer |
| `ui/dialogs.py`, `RemoteDisplayDialog` | Codeeingabe und Verbindungsanzeige |
| `ui/main_window.py` | Display starten/koppeln, Transkripte, Suchquellen und Bilder veröffentlichen |
| `storage/settings_store.py` | Display aktivieren, Host und Port; Standardkonfiguration 0.0.0.0:8765 |

Mira hostet selbst eine Webseite. Der Browser zeigt den Code, der innerhalb von
Mira bestätigt wird. Danach veröffentlicht Mira Text, Webquellen, Bilder und
Systemhinweise. Der Browser fragt `/status` und `/events` alle 900 ms ab und lädt
Bilder über `/image/<id>`. Das entspricht dem beschriebenen sichtbaren Ablauf;
ein separater Vermittlungsserver ist in diesem Code nicht enthalten.

Ein synthetischer Test ausschließlich auf localhost bestätigte Codeprüfung,
Transkript-/Quellen-/Bildereignisse und Bildauslieferung. Der Test bestätigte
auch die Begrenzung auf 200 Ereignisse im Speicher. Keine echten Gesprächsdaten
oder externen Empfänger wurden dafür verwendet.

## Grenzen des Prototyps

- Regelmäßige Abfrage ist vorhanden, aber kein Heartbeat mit Ablaufzeit oder
  Empfangsbestätigung. „Gekoppelt“ bleibt auch nach Trennung des Browsers gesetzt.
- Der Code schaltet global die Veröffentlichung frei. Die Lese-Endpunkte
  verlangen kein empfängerspezifisches Token; `/status` liefert den Code selbst.
  Vor einer produktiven Wiederverwendung muss die Kopplung abgesichert werden.
- Nur die letzten 200 Ereignisse werden gehalten. Es gibt keinen Import des
  vollständigen vorhandenen Chatverlaufs und keine Trennung nach Brain-Konto.
- Im ungepaarten Browserzweig wird der nächste Abruf doppelt geplant. Das muss
  korrigiert werden, damit nicht immer mehr Abfrageschleifen entstehen.

Der Android-Zweig `mira/assets/FaceVoiceMvp` enthält zusätzlich
`display/AgentDisplayItem.kt` für Transkript, Websuche, Bild und Systemhinweis.
`docs/TABLET_AGENT_DISPLAY_IDEATION.md` beschreibt eine weitere DisplayManager-
Idee. Für die Code-Kopplung ist jedoch der Desktop-Code der passende Fund.

## Übertragung auf den Recorder

1. **Pi als Sender:** Python besitzt Konto, Sitzung und Audiozustand. Es liefert
   strukturierte Text-, Quellen- und Bildereignisse. Aufnahme und Gespräch
   bleiben gegenseitig gesperrt.
2. **Browser als Empfänger:** eigenständige Anzeige auf PC, Tablet oder Bildschirm,
   zunächst nur lesend. Der dort angezeigte kurzlebige Code wird am Pi eingegeben.
   Die Kopplung erzeugt ein eigenes Empfängertoken; Microsoft-Zugangsdaten bleiben
   ausschließlich auf dem Pi. Kopplungsversuche werden begrenzt.
3. **Verbindung sichtbar:** Vorschlag: Heartbeat alle fünf Sekunden, nach 15
   Sekunden ohne Antwort „Verbindung verloren“. Wiederverbindung lädt einen
   sitzungsgebundenen Verlauf und danach nur neue Ereignisse mit Sequenznummern.
4. **Vollständiger Verlauf:** gespeicherte Nachrichten seitenweise nachladen,
   zusätzlich laufende Antwort ergänzen. Kein 200-Ereignis-Limit als Archiv.
   Konto-/Sitzungswechsel und Entkoppeln dürfen keine fremden Inhalte stehenlassen.
5. **Modellgesteuerte Inhalte:** zuerst Chat spiegeln, dann Quellen-/Bildkarten;
   anschließend explizite Anzeigeaktionen wie `display.show`, `display.update`
   und `display.clear`. Externe Links und Bilder müssen geprüft gerendert werden.

Der Recorder hört in `services/live_audio.py` derzeit auf dem Datenkanal
`oai-events` auf Suchaktivität. Das ist noch keine Schnittstelle für beliebige
Display-Toolcalls und liefert dort keine vollständigen Suchresultate. Für vom
Sprachmodell ausgelöste Bild-/Inhaltskarten muss CDB Voice One die strukturierten
Ereignisse bzw. Toolergebnisse bereitstellen. Das ist vor der Umsetzung mit dem
CDB-Protokoll abzugleichen; es lässt sich nicht allein durch einen UI-Schalter
aktivieren.

Empfehlung: Ereignistypen und Darstellungsansatz aus Mira übernehmen, die
Verbindung aber mit echter Kopplung, Heartbeat und sitzungsgebundenem Verlauf
aufbauen. Der Empfänger benötigt kein Mikrofon und steuert keine Aufnahme.
