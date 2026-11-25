# Gesprächsergebnisse im Chat und Brain · 1.0.0-rc5

Stand 25.11.2026. Interview und Brainstorming erzeugen strukturierte Texte:
Ziel, Fragen, Erkenntnisse, Ideen, bestätigte Entscheidungen und nächste Schritte.
Die Karte im Talk-Verlauf zeigt vorhandene Bereiche und ihren Ergebnisstand.
Nur tatsächlich gefüllte Bereiche zählen; angekündigte Ergebnisse zählen nicht.
Es gibt hier keine Bild-, PDF-, Präsentations- oder Tabellen-Dateierzeugung.
Freies Talk ohne gewähltes Gesprächsformat führt keine solche Ergebnisablage.

## Am Pi bedienen

1. **Ergebnisse ansehen** in der Chat-Karte oder **Ergebnis & Format →
   Ergebnisse auswählen** antippen. Bei regulärem Gesprächsende öffnet sich die
   Auswahl direkt, sofern die Talk-Seite sichtbar und kein anderer Dialog offen ist.
2. Über **Lesen** den vollständigen Text prüfen. **Text bearbeiten** öffnet den
   bisherigen Editor; Änderungen übernehmen und die Auswahl neu öffnen.
3. Gewünschte Kacheln an- oder abwählen. Anfangs sind alle gefüllten Bereiche
   ausgewählt; Anzahl und Markierung sind sichtbar. Vier Kacheln je Seite.
   Die Seitennavigation bleibt unten direkt über den großen Abschlussaktionen,
   auch auf kürzeren Seiten. Dasselbe gilt für die Wissensbereich-Auswahl.
4. **Ziel wählen**. Ein einziger für dieses Gespräch gewählter Wissensbereich wird
   vorausgewählt, sofern noch verfügbar. Bei mehreren Gesprächsbereichen gibt es
   keine Vorauswahl. Ansonsten kann der bereits bestätigte allgemeine Zielbereich
   vorausgewählt werden. Immer ist genau ein Ziel sichtbar zu bestätigen.
5. **N Ergebnisse speichern** überträgt die Auswahl als getrennte Textdokumente.
   Titel: Gesprächstitel plus Bereich. Chat, Ton und abgewählte Inhalte werden
   nicht angehängt. Eine abgewählte Zielbeschreibung bleibt ebenfalls ausgeschlossen.
   KI-Texte werden nicht automatisch als fachlich geprüft markiert.
6. Der Beleg zeigt **Wartet auf Übertragung**, **Wird übertragen**, **Im Brain
   empfangen · wird verarbeitet** und erst nach positiver Verarbeitung **Im Brain
   gespeichert**. Schließen ist nach der Vormerkung erlaubt. Den Stand später über
   **Brain-Status** in der Ergebnisauswahl öffnen.

Composer bleibt eine separate Funktion: ausdrücklicher Auftrag oder **In Composer
speichern** erzeugt beziehungsweise ergänzt das eigene Board. Brain-Speicherung
legt kein Composer-Board an und umgekehrt.

## Schutz vor Verwechslung und Datenverlust

- Speicherziel und Anmeldung werden vor dem Vormerken frisch geprüft. Arbeitsstand,
  Account, Server und Mandant müssen zusammenpassen. Kontowechsel schließt die
  Ergebnisanzeige; persönliche Texte werden nicht an den nächsten Benutzer gereicht.
- Ein geänderter Ergebnisstand wird abgewiesen und muss erneut geprüft werden.
  Der bestätigte Snapshot bleibt unveränderlich, auch wenn später weiterbearbeitet wird.
- Gleicher Inhalt im selben Ziel wird für dieses Gespräch nicht doppelt übertragen,
  auch nicht nach Phasenwechsel oder Umbenennung des Zielbereichs. Geänderter Text
  wird als neues Dokument gespeichert; vorhandene Brain-Dokumente werden nicht
  überschrieben. Ein anderes Gespräch besitzt eigene Ergebnisse.
- Unbestätigter Empfang wird nicht als Erfolg angezeigt. Nach unsicherem Versand
  gibt es keinen blinden erneuten Upload; Hinweis und Brain prüfen. Bei fehlendem
  Internet bleiben lokale Texte erhalten. Nach Abmeldung wartet die bestehende
  Warteschlange auf das passende Konto.
- Lesen bleibt während Talk möglich; Brain-Speicherung setzt Gesprächs- und
  Aufnahmeende voraus. Die API prüft diese Grenze erneut.
- Das Modell erhält keinen neuen Brain-Schreibbefehl. Die Auswahl am Display ist
  die Freigabe. Ein Gesprächsende allein lädt nichts hoch.

## Umsetzung und Installation

`Workshops.save_brain` erzeugt den geprüften Snapshot. `CdbService.enqueue_artifacts`
legt alle gewählten Dokumente gemeinsam in einer SQLite-Transaktion der vorhandenen
`publications`-Tabelle an. Fingerprints berücksichtigen Konto, Ziel-ID, Gespräch,
Bereich, Titel und Inhalt. Der vorhandene Worker verwendet Document-Ingest und
Verarbeitungsbelege. Kein zusätzlicher Server oder Cloud-Deploy erforderlich.
Die sichtbaren Belege enthalten Ziel und ursprüngliche Revision.

Bestandsupdate: keine Migration, neuen Pakete oder Systemdienste. Aufnahmen,
Anmeldung, Timer, NFC- und Geräteeinstellungen bleiben erhalten. Clean Install:
neue JS-/CSS-Dateien sind versioniert und über bestehende Positivlisten exportiert;
private SQLite-Dateien, Zugangsdaten und Aufnahmen sind ausgeschlossen.
Ein Quell-/Image-Baupaket ist kein neu gebautes oder bootgeprüftes SD-Image.

## Prüfung und Grenzen

- 60 gezielte Python-Prüfungen zu Ergebnisablage, Brain-Übertragung und Kundenimage
  bestanden: Auswahl, Revisionskonflikt, Kontowechsel, leere/ungültige Bereiche,
  Transaktion, Doppelaufruf, umbenanntes Ziel und unklarer Empfang.
- 123 bestehende Studio-/Live-/Geräteaktions-Prüfungen sowie 171 JavaScript-Prüfungen
  bestanden. Der API-Test prüft auch CSRF und die Sperre während Talk.
- Isolierte Touch-Vorschau bei 1024×600 und 1280×720, hell und CDB: Chat-Karte,
  Auswahlseiten, vollständiges Lesen, Zielsuche, Bildschirmtastatur, feste Aktionen,
  Übertragungsstatus und Außentipp. Simuliertes Gesprächsende öffnet die Auswahl
  ohne Upload. Fehlende Bereichsliste zeigt einen bedienbaren Fehlerzustand;
  erneutes Laden funktioniert. Bei mehreren Gesprächsbereichen keine Vorauswahl.
- Echter Brain-Test vom Recorder-Pi in `staging_playground`: zwei gewählte Texte als
  getrennte Dokumente verarbeitet, Ziel und Text anschließend zurückgelesen.
  Abgewählter Inhalt blieb ausgeschlossen; erneuter Speicheraufruf lieferte dieselben
  Belege. Isolierte Testablage; temporäre Anmeldung danach entfernt.
  [Sanitisierter Nachweis](brain-acceptance.json).

Die isolierte Vorschau ist keine vollständige manuelle Touch- oder Sprachabnahme.
Echte Spracherzeugung der strukturierten Inhalte wurde bereits für rc4 geprüft;
hier wird daraus kein neuer Sprachtest abgeleitet. Installation und tatsächlicher
Pi-Bildschirm werden separat dokumentiert.

Ansichten der isolierten Vorschau: [Chat 1024×600](screenshots/assets-chat-cdb-1024.png),
[Chat 1280×720](screenshots/assets-chat-cdb-1280.png),
[Auswahl hell](screenshots/assets-selection-1024.png),
[zweite Ergebnisseite](screenshots/assets-page2-cdb-1280.png),
[zweite Zielseite](screenshots/assets-target-cdb-1280.png),
[Tastatur](screenshots/assets-keyboard-1024.png),
[Verarbeitungsbelege](screenshots/assets-saved-1024.png),
[Verbindungsfehler](screenshots/assets-error-1024.png).
Die Seitennavigation blieb beim Wechsel von Seite 1 auf 2 an derselben Höhe:
Ergebnisse y=428 bei 1024×600, Ziele y=521 bei 1280×720.

## Auslieferung am 25.11.2026

Um **15:38 Uhr MEZ** wurde rc5 aus Commit `c8039178` als signiertes Update
mit Sequenz 110 installiert. Alle 167 Paketdateien wurden verifiziert. Die App
und der Kiosk laufen, Anmeldung und bisherige Ruhefrist wurden übernommen.
Aufnahmen, Einstellungen, NFC-Zuordnungen und Raumregeln blieben erhalten. Der
Pi wurde nicht neu gestartet. Zusatzdisplay erkannt; sein Begleitdienst läuft.
[Installationsbeleg](deployment-rc5.json).

Der echte Pi-Bildschirm wurde anschließend geprüft: 1280×720, CDB-Design,
Startseite und angemeldetes Konto sichtbar. Der persönliche Screenshot wird
nicht ins Repository übernommen. Das ist ein Start-/Anzeigecheck; die neuen
Auswahldialoge wurden in der isolierten Touch-Vorschau geprüft, nicht als
vollständige manuelle Hardware-Touch-Abnahme ausgewiesen.

Ein sauberes Image-Baupaket aus demselben Commit wurde exportiert: 174 Quelldateien,
beide neue Touch-Assets enthalten, keine private Ergebnisdatenbank.
[Exportnachweis](image-kit-rc5.json). Kein neues SD-Image gebaut.
