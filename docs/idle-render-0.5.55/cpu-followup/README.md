# Rechenzeit: echter Pi und getrennte lokale Diagnose

16. Oktober 2026, Europe/Berlin. Keine App-Änderung, kein Audio und kein Neustart
des Pi. Diese kurzen Proben ersetzen weder den Dauerlauf noch eine Latenzabnahme.

## Echter Pi, zehn Sekunden

Eine reine Leseprobe von `/proc/806009/task/*/stat` vergleicht CPU-Zähler über
10,002 Sekunden. Der Renderer behält seine Startkennung 8935764; im Fenster
startet oder endet kein Thread. Der Hauptthread verwendet **2,78 CPU-Sekunden**
(27,79 % eines Kerns), der Compositor **0,03 Sekunden**, der vordere Threadpool
**0,04 Sekunden**. [Vollständige Thread-Stichprobe](pi-thread-sample.json).

Das lokalisiert die Rechenzeit im Renderer-Hauptthread, unterscheidet dort aber
nicht JavaScript, Layout, Speicherbereinigung oder andere native Aufgaben.
Vom produktiven Pi-Renderer gibt es keinen aufgezeichneten CPU-Stack und keine
daraus abgeleitete Behauptung, welche Funktion die Last verursacht.

## Synthetische Mac-Vorschau, zweimal 15 Sekunden

Getrennter Chrome 155 bei 1280 × 720, aktuelle Frontend-Dateien und Vorschau-
Backend 0.5.52. Ein lokaler Wake-Status ist gesetzt; kein echtes Brain-Konto,
Raumaudio oder Cloud-Gespräch wird verwendet. Playwright-Routing gibt die
Antwortobjekte nach der Weitergabe ausdrücklich frei. Der DevTools-Profiler
verändert die Instrumentierung und ist daher vom debuggerfreien Speichertest
getrennt. Beide laufen während dieses kurzen Fensters auf demselben Mac.

| Messfenster | Hauptthread-Aufgabenzeit | JavaScript-Zeit | Layout / Stil |
| --- | --- | --- | --- |
| Normale Oberfläche, 15,038 s | 0,1852 s | 0,0437 s | 0,0027 / 0,0017 s |
| `renderState` angehalten, 15,014 s | 0,1156 s | 0,0382 s | 0 / 0 s |

Das Anhalten ist ausschließlich eine Diagnose und macht die Oberfläche als
Produkt unbrauchbar. Die Funktion wurde nach dem Fenster wiederhergestellt;
anschließend wurde die eigene Playwright-Sitzung geschlossen. Die CLI bestätigte
den Abschluss und ihr Prozess 51172 war danach nicht mehr vorhanden. Der
separate debuggerfreie Browser 44123 wurde nicht verändert.

Die normale lokale Vorschau zeigt in dieser Probe keine vergleichbare starke
Auslastung. Unterschiedliche Hardware, Browser-Version, Datenbestand und
Instrumentierung verhindern einen direkten Prozentvergleich mit dem Pi.
Auch eine vereinzelte langsamere Aufgabe könnte zwischen kurzen Proben fehlen.
Keine neue produktive Optimierung wird allein aus diesen Werten abgeleitet.

[Rohprofil](mac-profile.json), [verwendeter Browser-Code](profile-local.js),
[Kennzahlen und Prüfsummen](summary.json). Die Zeitanteile stammen aus
`Performance.getMetrics`; die CPU-Samples bleiben zusätzlich vollständig
erhalten. Keine erzwungene Speicherbereinigung. Kein Laufzeit- oder Image-Einfluss.


## Getrennte Diagnose auf dem Pi

Am 16. Oktober zwischen etwa **00:25 und 00:32 Uhr Europe/Berlin** wurden sechs
kurze, getrennte Diagnosebrowser gestartet. Fünf scheiterten beim Aufbau der
Testumgebung, der sechste lieferte zwei 15-Sekunden-Profile. Alle sechs sind
nachweislich beendet, ihre temporären Browserprofile entfernt. Der produktive
Kiosk und die Aufnahme-/Wake-Dienste wurden nicht neu gestartet.

Die Testinstanz nutzt dieselbe Chromium-Version **142.0.7444.59** und Frontend-
Dateien wie der Pi, aber einen eigenen Headless-Prozess ohne GPU, einen festen
Zustand im Arbeitsspeicher und eine CPU-Grenze von 50 % eines Kerns. Der Snapshot
enthält 22 Aufnahme- und sieben Auftragsdatensätze, keinen Live-Verlauf. Private
Inhalte wurden nicht ins Repository übernommen. Zwei unvollständige Fixtures
(`/api/cdb/areas` und `/api/microphone/audio`) lieferten Fehler; es wurde kein
Raumaudio geladen oder abgespielt. 20 begleitende Aktivitätsprüfungen meldeten
Leerlauf. Diese Einschränkungen verhindern eine vollständige Nachbildung.

| Messfenster | Hauptthread-Aufgabenzeit | JavaScript-Zeit | Layout / Stil |
| --- | --- | --- | --- |
| Normale Oberfläche, etwa 15 s | 0,5099 s | 0,0468 s | 0,0583 / 0,0117 s |
| `renderState` angehalten, etwa 15 s | 0,1983 s | 0,0336 s | 0 / 0 s |

Auch dieser kurze frische Prozess reproduziert die steigende Last des alten
produktiven Renderers nicht. Er begründet weder eine Laufzeitänderung noch eine
bestandene Stabilitätsabnahme. Die fünf Fehlversuche sind Fehler des
Diagnoseaufbaus. Mit `--password-store=basic` startete die isolierte Navigation;
eine solche Option wurde am produktiven Prozess bei der Nachprüfung **nicht**
gefunden. Die zwischenzeitliche Aussage, dass der Kiosk sie bereits verwendet,
war nicht belegt. Die genaue interne Ursache der Startblockade bleibt offen.

[Messwerte, Quellenprüfsumme, Zeitpunkte und Bereinigung aller sechs Versuche](pi-isolated-summary.json).
Das private vollständige Rohprofil liegt außerhalb Git am dort angegebenen Pfad.
Die Tests liefen im gleichen Beobachtungszeitraum: Der Beobachter zählt nur die
produktive Browser-Prozessgruppe, globale Temperatur und freier Arbeitsspeicher
können trotzdem durch die Diagnose beeinflusst sein. Diese Intervalle sind daher
**keine unbeeinflusste System-Leerlaufmessung**. Kein App- oder Image-Einfluss,
keine neue Auslieferung. Ressourcenwachstum und echte Langzeit-Erkennung bleiben
ungelöste Abnahmepunkte.
