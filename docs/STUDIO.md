# Recorder Studio 0.5.9

## 0.5.10 – Einheitliche Touchansichten und dauerhafte Modellnachweise

Aktives Modell und Teststatus bleiben klar getrennt. Ergebnisse bleiben pro Modell gespeichert; die übernommenen Pi-Nachweise werden gegen Modell und Laufzeit geprüft. Header, Fußleisten, Auswahlfelder und Such-/Seitennavigation sind vereinheitlicht. Bibliothek und Queue zeigen vollständige Seiten. Siehe [Audit und Screenshots](stable-models-0.5.10/README.md).


Die HTML-Oberfläche übernimmt die ausgewählte zweite Studio-Variante. Das bestehende Python-Backend verarbeitet weiterhin Aufnahmen und lokale Modelle. `web_server.py` verwendet den vorhandenen `LocalController`, die ursprüngliche `data/sessions.db`, bestehende QSettings-Prompts und die fest versionierte gemeinsame Python-Engine 0.2.6. Es gibt eine Aufnahmeinstanz und einen FIFO-Verarbeiter.

## Start auf dem Pi

Nach Sicherung und Beenden der bisherigen Anwendung:

```sh
./scripts/install-studio.sh
./kiosk.sh
```

Der Benutzerdienst `cdb-recorder-studio.service` startet das Python-Backend; der Desktop-Autostart startet Chromium im Kiosk. Die Oberfläche ist auf dem Pi unter `http://127.0.0.1:8088/` erreichbar. Der Server bindet ausschließlich an Loopback und prüft Host, Origin und CSRF. Chromium verwendet ein eigenes lokales Profil, ohne Schlüsselbundanmeldung. Schrift und Symbole werden lokal ausgeliefert. Das Mikrofon wird am Pi aufgenommen; der Browser erhält keine Mikrofonberechtigung. Für Fernzugriff ist ein SSH-Tunnel erforderlich.

Das Installationsskript ändert nur Anwendungsdienst und Starter; es installiert keine Systempakete oder Modelle. `run.sh` bleibt als Starter der bisherigen Python/Qt-Oberfläche erhalten. Sie kann wegen der gemeinsamen exklusiven Datensperre nicht gleichzeitig mit dem Studio laufen.

## Bedienung und Daten

„Recorder“ zeigt ohne laufende Aufnahme eine Bereitschaftsansicht mit Standardbereich. Frühere Meetings werden dort nicht automatisch ausgewählt. Während einer Aufnahme führt „Recorder“ immer zu deren aktuellen Notizen zurück. Nach dem Stoppen bleibt die gerade beendete Aufnahme zur Kontrolle sichtbar; beim nächsten Wechsel zurück zu Recorder erscheint wieder die Bereitschaftsansicht. Eine neue Aufnahme ist unabhängig von der Hintergrundverarbeitung möglich.

„Bibliothek“ merkt sich innerhalb der geöffneten App ihre eigene Aufnahme und den ausgewählten Texttab. „Alle Aufnahmen“ öffnet die Liste zur erneuten Auswahl. Ein Browser-Neustart beginnt wieder auf Recorder. Einstellungen öffnen rechts; Hauptansichten werden ausschließlich über die linke Navigation gewechselt. Das Aufnahme-Widget erscheint ausschließlich im Recorder. Bibliothek und Einstellungen nutzen die gesamte Fläche rechts von der Navigation. Während einer Aufnahme sind beide Bereiche gesperrt; Notizen, Bildschirmtastatur und Stoppen bleiben verfügbar. Meetingaktionen, Transkript-/Zusammenfassungstabs und Wiedergaberegler sind währenddessen ebenfalls gesperrt. Die Warteschlange hat eine eigene rechte Ansicht; ihr Menüpunkt ist bis zum Stoppen gesperrt. Anzahl und Verarbeitungsanimation bleiben am Menü-Icon erkennbar. Bereits laufende Verarbeitung geht weiter; nach dem Stoppen sind Navigation und Ansichten sofort wieder zugänglich. Die HTTP-Schnittstelle erlaubt während einer Aufnahme nur Stoppen und das Speichern der Notizen dieser Aufnahme.

Der Aufnahmebutton startet oder beendet eine Aufnahme unabhängig vom rechts ausgewählten Meeting. Transkription und Zusammenfassung laufen nacheinander in der bestehenden Warteschlange; weitere Aufnahmen sind dabei möglich. Notizen lassen sich parallel bearbeiten. Texte werden verzögert automatisch gespeichert. Bei einem Speicherfehler bleibt die Navigation möglich und der Entwurf lokal erhalten. Ein Konflikt mit einer neueren Fassung verhindert das Überschreiben; ein lokaler Entwurf bleibt erhalten. Während der KI-Verarbeitung sind deren Ergebnisfelder geschützt.

Bibliothek, Suche, Umbenennen, Markdown-Export, Wiedergabe, erneute Transkription, Fehlerwiederholung, vorhandene und eigene Prompts sowie Mikrofon- und Modelleinstellungen sind angebunden. Die integrierte Touch-Tastatur steht in der Seitenleiste und in Dialogköpfen bereit; sie unterstützt Umlaute, Großbuchstaben, Zahlen, Sonderzeichen und Zeilenumbrüche.

Ein Mikrofon muss gefunden, getestet und die Einrichtung abgeschlossen sein, bevor eine echte Aufnahme startet. Bestehende Modelle und Auswahlen werden übernommen. Die direkten Einzeltests unter KI & Modelle verwenden ausschließlich künstliche Sprache bzw. einen festen Beispieltext. Sie laufen unabhängig von der jeweils anderen Modellart, nur bei leerer Verarbeitung und ohne aktive Aufnahme. Während eines Tests sind neue Aufnahmen, Modellwechsel und weitere Tests gesperrt. Die Tests erscheinen nicht als persönliches Meeting. Die konservative Pi-Vorprüfung sperrt ihn bei angeforderter Kühlung ohne Lüfter-Tachosignal, ab 65 °C oder unter 4 GiB verfügbarem RAM.

## Isolierte Funktionsvorschau

```sh
venv-local-ai/bin/python scripts/studio_preview.py /tmp/recorder-studio-preview --port 8094
```

Die Vorschau verwendet eine eigene dauerhafte Datenablage, künstliches Audio und einen austauschbaren Testprozessor. Aufnahme, Warteschlange, Speicherung und HTTP-Anbindung sind echt; die Vorschau misst keine Modellqualität. Sie greift nicht auf persönliche Pi-Meetings zu.

## Rückkehr zur bisherigen Oberfläche

Studio-Dienst beenden und deaktivieren, den eigenen Kiosk schließen und die zuvor gesicherten Desktop-/Autostart-Dateien zurückkopieren. Danach `./run.sh` starten. Die Datenbank bleibt dieselbe; aktuelle Bearbeitungen bleiben erhalten. Eine ältere Datenbanksicherung nur nach ausdrücklicher Entscheidung wiederherstellen, weil sonst neuere Änderungen verloren gingen.

Der Installationslauf vom 11.10.2026 verwendet die Sicherung `/home/chris/recorder-backups/before-studio-0.4.0/`: konsistente Sitzungs- und Queue-Datenbanken, QSettings, Starter, bisheriger Quelltext und SHA-256-Prüfsummen der 17 Audioaufnahmen. Die Aufnahmen selbst werden bei der Installation nicht geändert.

`AudioRecorderApp.clean.conf` enthält den geprüften Einstellungenstand nach Entfernung eindeutig eigener Test-Prompts. Die ursprünglichen und zwischenzeitlichen Dateien bleiben zur Nachvollziehbarkeit ebenfalls gesichert. Vorschau und Tests verwenden ausdrücklich eigene QSettings-Dateien; eine Änderung des globalen Qt-Standardformats allein isoliert den Konstruktor mit Organisationsnamen nicht.

## Auditkorrekturen 0.4.1

Die vom Server gelieferten Aktionsregeln gelten auch unabhängig von der Oberfläche:

| Zustand | Erlaubt | Wartet / gesperrt |
| --- | --- | --- |
| Normale KI-Verarbeitung / Queue | Neue Aufnahme, Notizen, Lesen, Konfiguration für neue Aufträge | Downloads, Modelltest; Löschen/Neuverarbeitung des beschäftigten Meetings |
| Aufnahme | Stop auch im Dialogkopf, Notizen, normale KI-Queue | Mikrofontest, Konfiguration, Modellinstallation/-test, Einrichtung abschließen |
| Mikrofontest | Lesen und Notizen, normale KI-Queue | Aufnahme und weitere Audio-/Modelloperationen |
| Modelldownload / Modelltest | Lesen, lokale Entwürfe, Prompts | Neue Aufnahme, Konfiguration, konkurrierende Modelloperationen und neue KI-Aufträge |
| Zu wenig Speicher | Lesen, Notizen, laufende Aufnahme sicher stoppen | Neue Aufnahme / Mikrofontest / Modelltest |
| Verbindung unterbrochen / veraltet | Gelesene Texte und lokale Entwürfe bearbeiten, lokal exportieren | Serveraktionen bis frischer Zustand vorliegt |

Threadzahl, Whisper-Programm, Modellwahl und Prompt werden pro Auftrag festgehalten. Ein aktiver technischer Modelltest behält seine Identität über einen Dienstneustart. HTTP-Aktionen verwenden dieselbe Lockreihenfolge wie die Statusabfrage; paralleles Polling und Stoppen wird getestet.

„Entwurf lokal sichern“ zeigt alle aktuell bearbeiteten Textfelder zum Kopieren oder als Markdown-Datei, ohne vorheriges Speichern. „Erneut speichern“ wiederholt die optimistisch geprüfte Speicherung. „Aktuelles Feld vergleichen“ zeigt lokale und gespeicherte Fassung; erst die ausdrückliche Auswahl übernimmt eine Fassung. Eine zwischenzeitliche weitere Änderung wird erneut als Konflikt abgefangen. Lokale Browserdaten bleiben im gleichen Kioskprofil erhalten; Löschen des Browserprofils entfernt lokale Entwürfe.

Eine neue Verarbeitung bewahrt bisherige Ergebnisse, bis neue Ergebnisse vorliegen. Beim Löschen bleibt Audio erhalten, wenn eine andere Sitzung dieselbe Datei verwendet. Wiedergabe wird beim Aufnahmestart pausiert; während Aufnahme erfordert die Wiedergabe einen Kopfhörerhinweis. Die Tastatur wählt sichtbare Textfelder; die Ansicht passt sich bei geöffneter Warteschlange und bei 1024×600 mit Tastatur an.

Die Abnahme nutzt ausschließlich isolierte synthetische Sitzungen und kontrollierte Fehlerzustände. Echte Mikrofonqualität und Modellleistung werden dadurch nicht nachgewiesen. Keine Firmware-, Lüfter- oder Betriebssystemänderungen gehören zu diesem Update.

## Modellkatalog 0.4.2

Die Dropdowns wählen einen Kandidaten zur Ansicht; sie ändern keine aktive Modellwahl. Quelle, Lizenz, Downloadgröße, Installation, Kompatibilität, Gerätetest und Aktivierung sind getrennt sichtbar. Neue Kandidaten benötigen einen erfolgreichen technischen Test vor der ausdrücklichen Aktivierung. Der Test verwendet einen eigenen Auftrags-Snapshot; aktive Modelle und vorhandene Aufträge bleiben erhalten. Ein geänderter Modelldigest oder eine geänderte Ollama-Version macht den Testnachweis ungültig.

Whisper medium, large-v3-turbo und large-v3 bleiben mehrsprachige whisper.cpp-Modelle. Qwen3.5 4B Q4_K_M ist ein ungeprüfter zusätzlicher Textkandidat mit ausdrücklich benanntem Hugging-Face-GGUF. Thinking wird über `think:false` der Runtime abgeschaltet; `/nothink` wird nicht als Ersatz verwendet. Architektur, Quantisierung und Thinking-Vorlage müssen passen; unerwartetes Thinking lässt den echten Test scheitern. Quellen, technische Grenzen und spätere Kandidaten: [kanonische Modelldokumentation](https://github.com/shortcutchris/raspberry_pi_meeting_recorder/blob/main/docs/modelle.md).

## Touch-Dialoge 0.4.3

Dialograhmen und Kopf bleiben fest. In den Einstellungen bleiben Audio/Modelle/Prompts und die Hauptaktion sichtbar; nur der Inhalt des ausgewählten Bereichs scrollt. Bibliothekssuche ist ebenfalls fest. Meetingdetails, Export, Wiedergabehinweis und Konfliktvergleich nutzen denselben Aufbau. Schließen und Aufnahme-Stopp bleiben im Kopf erreichbar.

Touchfelder sind mindestens 56 Pixel hoch; die vierzeilige Bildschirmtastatur verwendet eigene 44-Pixel-Mindesthöhen, damit Tasten nicht überlappen. Bei geöffneter Tastatur schrumpft der Dialog oberhalb der Tastatur und das fokussierte Eingabefeld wird in den sichtbaren Inhaltsbereich gescrollt. Prompt löschen befindet sich bewusst im Inhalt, Speichern bleibt unten. Änderungen an Aufnahme-/Queue-/Modellsperren waren nicht erforderlich.

Geprüft am 12.10.2026 mit isolierter synthetischer Bibliothek und bestehendem Python-Backend auf dem Pi: 1280×720 und 1024×600, Modelle lang gescrollt, Bibliothek mit 28 Einträgen, Prompt-Eingabe mit Tastatur, Meetingdetails/Export, laufende Aufnahme mit gesperrter Modellwahl und Stopp im Dialogkopf. 29 vorhandene Native-/Studio-Tests bestanden. [Screenshots und Prüfdetails](touch-dialogs/README.md). Keine echten Meetings oder Mikrofonaufnahmen für diese Prüfung.

[CAD, Gehäusevorschauen und Einkaufsliste im gemeinsamen Raspberry-Pi-Repository](https://github.com/shortcutchris/raspberry_pi_meeting_recorder/tree/main/hardware/enclosure).

## Farbthemes 0.4.4

Unter Einstellungen → Design stehen Blau · Hell, Petrol · Hell, Mitternacht und Graphit zur Auswahl. Die Auswahl gilt sofort für Recorder, Bibliothek, Dialoge, Warteschlange und Bildschirmtastatur. Sie bleibt im lokalen Browserprofil über Neuladen und Neustart erhalten; andere Browserprofile wählen unabhängig. Bei nicht verfügbarem Browserspeicher bleibt die Auswahl nur für die Sitzung erhalten und die Oberfläche zeigt das ausdrücklich an. Aufnahme und Queue werden durch Theme-Wechsel nicht verändert; Design bleibt während der Verarbeitung bedienbar. Aufnahme- und Fehlerfarben bleiben unabhängig vom Theme erkennbar.

Geprüft: alle vier Optionen, genau eine aktive Auswahl, dunkles Theme nach Neuladen wiederhergestellt, Dialograhmen ohne äußeren Scrollbereich. Screenshots: [Theme-Auswahl](touch-dialogs/06-themes-midnight.jpg), [Recorder in Graphit](touch-dialogs/07-theme-graphite-recorder.jpg).

## Eigene Themes 0.4.5

Einstellungen → Design erlaubt eigene Themes anzulegen, das ausgewählte Theme zu duplizieren und eigene Themes zu bearbeiten oder nach einer Rückfrage zu löschen. Standardthemes sind geschützt. Name sowie Hintergrund, Flächen, Aufnahmebereich, Text und Akzentfarbe lassen sich mit Live-Vorschau ändern. Speichern übernimmt und aktiviert das Theme; Abbrechen, Dialog schließen oder Bereich wechseln verwirft die Vorschau. Nach Löschen des aktiven Themes wird Blau · Hell aktiviert. Bis zu 100 eigene Themes bleiben im gleichen lokalen Browserprofil erhalten. Browserdaten löschen entfernt auch eigene Themes.

Der Editor bleibt in einer festen, lesbaren Farbpalette. Speichern erfordert einen Namen und mindestens 4,5:1 Kontrast zwischen Text und den drei Hauptflächen. Text und Symbole auf Akzentflächen erhalten automatisch Schwarz oder Weiß. Touch-Farbfelder öffnen den Farbwähler des Browsers. Die Tastatur schließt beim Speichern, Abbrechen und Bereichswechsel.

In der isolierten Pi-Vorschau geprüft: Anlegen mit geänderter Farbe, Speichern und Wiederherstellung nach Neuladen, Bearbeiten, zu geringer Kontrast sperrt Speichern, Abbrechen verwirft Änderungen, Duplizieren, Löschen mit Rückfrage sowie Schutz der Standardthemes.

## Touch-Navigation 0.4.6

Die Oberfläche verwendet keine sichtbaren Scrollbars. Bibliothek, Einstellungen, Dialoginhalte, lange Notizen/Transkripte/Zusammenfassungen und Warteschlange erhalten bei Überlauf feste Hoch/Runter-Buttons (mindestens 56 Pixel). Jeder Schritt bewegt ungefähr 80 Prozent des sichtbaren Inhalts, damit Zeilen beim Blättern überlappen. Anfang/Ende deaktiviert den entsprechenden Button. Wischen ist zusätzlich möglich. Der Dialograhmen, Schließen, Aufnahme-Stopp und Hauptaktionen bleiben fest. Lange Textfelder besitzen bei Bedarf eigene Blätterbuttons.

Mikrofon-, Modell- und Prompt-Dropdowns sind durch touchgerechte Auswahldialoge mit großen Optionsbuttons, Seitenanzeige und Zurück/Weiter ersetzt. Die bestehenden Select-Elemente und Change-Handler bleiben intern erhalten; Sperren und Aktivierung werden nicht umgangen. Die Auswahl eines Modellkandidaten aktiviert ihn weiterhin nicht automatisch. Während einer Aufnahme bleibt der Stopp auch im Auswahlfenster verfügbar.

Eine neue Aufnahme wird anhand ihrer unveränderlichen Job-ID direkt ausgewählt, auch wenn eine Statusabfrage bereits läuft oder die Aufnahme kurz darauf endet. Die Notizen öffnen sich für das neue Meeting. Bestehende Entwürfe durchlaufen die bisherige Sicherung. Nach dieser einmaligen Auswahl kann der Benutzer wieder frei andere Meetings öffnen, ohne dass das Polling ihn zurücksetzt.

Bei 1024×600 und geöffneter Tastatur wird der erklärende Einstellungsbanner ausgeblendet, um Eingabefeld, Blätterbuttons und Speichern erreichbar zu halten. Die Sperrlogik der eigentlichen Aktionen bleibt aktiv.

Prüfung am 12.10.2026: 29 Native-/Studio-Tests bestanden; Browserprüfung mit isolierten synthetischen Aufnahmen: automatische Auswahl, weitere Aufnahme während Verarbeitung, Queue, lange Notizen mit Blätterbuttons, Bibliothek mit mehr als 28 Einträgen, vollständiger Modelleinstellungsbereich per Buttons, Kandidatenauswahl, Tastatureingabe und fester Dialograhmen bei 1024×600 sowie 1280×720. Computed scrollbar-width überall in diesen Bereichen: none.

Screenshots: [Bibliothek](touch-dialogs/09-library-touch-buttons.jpg), [neue Aufnahme ausgewählt](touch-dialogs/10-new-recording-selected.jpg), [Modellauswahl](touch-dialogs/11-model-touch-picker.jpg).

Dieses Update verändert nur die statischen Frontend-Dateien. Python-Backend bleibt 0.4.5; ein Backend-Neustart ist für die Auslieferung nicht erforderlich und eine laufende Verarbeitung kann weiterlaufen.

### Schwebende Warteschlange

Die Warteschlange öffnet als Panel über der Anwendung, oberhalb der Statusleiste. Aufnahmebereich und Meetingansicht behalten ihre Größe und Position. Ein großer Schließen-Button und der Button in der Statusleiste klappen das Panel zu. Es gibt keine blockierende Hintergrundabdeckung: Aufnahme und Notizen bleiben bedienbar. Lange Warteschlangen besitzen innerhalb des Panels Hoch/Runter-Buttons.

## Zusammenfassung über Azure OpenAI

Unter **Einstellungen → Zusammenfassung → Verarbeitung** zwischen „Auf diesem Gerät · offline“ und „Azure OpenAI · Firmenkonto“ wählen. Für Azure OpenAI zuerst unter Verbindung mit Microsoft anmelden. Das bestehende Firmenkonto genügt; die App benötigt keinen persönlichen OpenAI-Schlüssel. Die Einzelmodelle verwaltet das Unternehmen zentral über CDB. Die Transkription bleibt unabhängig wählbar. Bei Azure-Verarbeitung werden Texte übertragen; die Originalaufnahme bleibt auf dem Pi. Lokale Modellinstallation und Aktivierung sind nur bei lokaler Zusammenfassung sichtbar. Eingereihte Aufträge behalten ihre bei Start gespeicherte Verarbeitung.

Lange Zusammenfassungen werden abschnittsweise erstellt und zusammengeführt. Der CDB-Zugang verwendet Server-Keepalives, damit das Gateway längere Antworten nicht wegen ausbleibender Daten beendet. Nur vollständige Antworten werden übernommen; abgeschnittene Antworten werden einmal mit größerem Ausgabebudget erneut angefordert. Die Länge der Teilantworten wird geprüft und bei Bedarf durch eine erneute Verdichtung reduziert. Texte werden dabei nicht abgeschnitten. So passen die Ergebnisse in das nächste Zusammenführungsfenster. Fehler bleiben sichtbar und blockieren nachfolgende Aufträge nicht.

In der Bibliothek führt die große Taste „Zur Aufnahmeliste“ zurück zur Suche und Aufnahmeliste. Die Positionsanzeige zeigt die Detailansicht an; dort gibt es keine zweite konkurrierende Leiste letzter Aufnahmen. Während einer Aufnahme sind Bibliothek und Einstellungen weiterhin gesperrt.


## Einstellungen und belegte Aufgaben ab 0.5.8

Einstellungen öffnen eine Übersicht aus acht Kacheln. Auf jeder Unterseite führt **Alle Einstellungen** zurück zur Übersicht; eine zweite seitliche Navigation entfällt. Die äußeren App-Icons bleiben sichtbar. Das Mikrofon-Symbol im Recorder öffnet Audio direkt. Während der Aufnahme bleiben Einstellungen und Bibliothek gesperrt.

Die Detailseiten teilen sich Schriftgrößen, Abstände und kompakte Aktionen. Unter Transkription werden lokale Modellfelder nur bei lokaler Verarbeitung gezeigt. Gerätetest → Erweiterte Programmeinstellungen enthält den Whisper-Pfad. Prompts zeigen lange Arbeitsaufträge über direkt anwählbare Textseiten. Ein ungespeicherter Theme-Entwurf wird beim Zurückgehen verworfen. **Einrichtung speichern** erscheint nur, solange die Einrichtung noch offen ist.

Bei Standardvorlagen erfolgt die Zusammenfassung in belegten Abschnitten. Aufgaben, Namen und Fristen müssen wörtlich im selben Satz stehen. Unklare Namensfragmente bleiben als unklar markiert; Vorschläge, Fragen und nicht bestätigte Aufträge werden nicht als Aufgaben übernommen. Ein abschließender deterministischer Schritt führt die Belege zusammen, ohne neue Aufgaben zu formulieren. Eigene Prompts bleiben frei und nutzen weiterhin die bisherige generative Verarbeitung. Die Belegprüfung kann weder Spracherkennungsfehler korrigieren noch vollständige Aufgabenerkennung garantieren. Vor der Brain-Übertragung prüfen.

Aktuelle Testzahlen, Screenshots und Prüfgrenzen: [0.5.8-Prüfbericht](task-quality-0.5.8/README.md).

Die Warteschlange öffnet über das Listen-Icon links als eigene rechte Ansicht. Eine dauerhafte Status-/Queue-Leiste unten entfällt. Dort sind laufender Schritt, wartende Aufträge und Fehler sichtbar. Während der Aufnahme bleibt die Navigation dorthin gesperrt; nach Stoppen ist sie wieder frei.

Hauptansichten besitzen keine zusätzliche Schließen- oder Recorder-Zurück-Taste. Der Rückweg „Alle Einstellungen“ bleibt ausschließlich auf Einstellungs-Unterseiten; „Zur Aufnahmeliste“ ausschließlich im Bibliotheksdetail. Die Tastatur ist ohne erreichbares editierbares Textfeld deaktiviert.


## Brain-Konto und KI & Modelle 0.5.9

Einstellungen → Brain-Konto enthält Microsoft-Anmeldung, Konto und Standardbereich. Der Standardbereich wird nur hier verwaltet; pro Meeting ist weiterhin ein anderes Ziel möglich. „Übertragungen“ zeigt den Verlauf, „KI-Verarbeitung einrichten“ führt zur Modellübersicht. Anmeldung aktiviert keine Online-Verarbeitung.

Einstellungen → KI & Modelle zeigt die **aktiven** Modelle für Transkription und Zusammenfassung. Die jeweilige Unterseite führt über „KI & Modelle“ zurück. Brain-Übertragungen führen über „Brain-Konto“ zurück. Die Übersicht behält sechs große Kacheln.

1. Transkription oder Zusammenfassung öffnen.
2. „Auf dem Pi“ oder „Über Brain“ wählen. Dies ist zunächst nur eine Auswahl.
3. Lokal: Modell auswählen, bei Bedarf herunterladen.
4. „Modell testen“ startet ausschließlich den gewählten Verarbeitungsschritt. Lokal erfolgen Laufzeit-/Kühlungsprüfungen; Brain benötigt die Microsoft-Anmeldung. Der Online-Test überträgt nur ein festes künstliches Beispiel.
5. Ergebnis und Laufzeit erscheinen auf derselben Seite. „Test erfolgreich“ bestätigt ein nichtleeres Modellresultat, nicht dessen inhaltliche Fehlerfreiheit.
6. „Für neue Aufnahmen verwenden“ übernimmt die Auswahl. Bereits eingereihte Aufträge behalten ihre Konfiguration. Ein Test allein aktiviert nichts.

Direkte Tests werden unter `model-checks/` dauerhaft gespeichert; ein bei Neustart unterbrochener Test wird als fehlgeschlagen angezeigt und muss wiederholt werden. Lokale Freigaben sind an den Modell-Fingerprint gebunden. Brain-Aktivierung benötigt einen bestandenen Test desselben Verarbeitungsschritts und desselben Firmenkontos/Servers. Die letzte Online-Prüfung wird durch einen neuen Test ersetzt. Brain verwaltet das konkrete Online-Modell zentral; der Zugang bietet keine freie GPT-Modellliste.

Gerät & Diagnose enthält die erweiterten Programmpfade. Aufnahmemodelle werden dort nicht mehr getestet oder ausgewählt.
