# Native CPU-Stichprobe am laufenden Pi-Renderer

16. Oktober 2026, etwa **00:56:06–00:56:16 Europe/Berlin**. Der produktive
Renderer 806009 behielt die Startkennung 8935764. Kein Browser-, Backend- oder
Pi-Neustart, keine Audioaktivierung und keine Konfigurationsänderung.

## Beobachtung

Eine begrenzte CPU-Clock-Stichprobe des Renderer-Hauptthreads liefert **143
Samples**, keine verlorenen Samples und keinen Parsingfehler. In 10,244 Sekunden
steigen die Prozesszähler um **3,04 Sekunden Benutzerzeit** und **0,10 Sekunden
Systemzeit**. Alle 21 begleitenden Aktivitätsprüfungen melden Leerlauf.

| Funktion am untersten erfassten Stackframe | Samples |
| --- | ---: |
| `AgentGroupSchedulerImpl::PerformMicrotaskCheckpoint` | 68 |
| `MainThreadSchedulerImpl::UpdateCompositorTaskQueuePriority` | 39 |
| `MainThreadSchedulerImpl::PerformMicrotaskCheckpoint` | 11 |
| Andere | 25 |

Damit liegen **118/143 = 82,5 %** dieser Stichprobe in drei nativen Scheduler-
Funktionen. Das ist keine Aussage, dass JavaScript oder die App unbeteiligt seien:
Die App kann solche Verwaltungsarbeit auslösen. Ebenso beweist eine CPU-Probe
weder den Eigentümer wachsender Speicherbelegungen noch einen Speicherfehler.

Die Funktionsnamen stammen aus dem offiziellen Raspberry-Pi-Debugpaket für
**142.0.7444.59-1~deb13u1+rpt1, arm64**. Die GNU-Build-ID wurde im ELF selbst mit
der laufenden Chromium-Datei abgeglichen:
`7914866d038784fc765399fac27c1c34baa6507f`. Das Paket wurde nur in private
Diagnoseverzeichnisse heruntergeladen und entpackt, **nicht installiert**.
Die ausführbare ELF-Sektion hat einen VMA/File-Offset-Unterschied von 0x10000;
dieser wurde bei der Symbolzuordnung berücksichtigt. Eine unabhängige Prüfung
mit `addr2line` bestätigt die häufigsten Funktionsnamen, meldet aber Fehler in
Zeilennummerntabellen. Daher keine Behauptung genauer Quellzeilen oder
rekonstruierter Inline-Frames.

## Methode und Grenzen

`sample.c` verwendet die vorhandene Linux-Schnittstelle
[`perf_event_open`](https://www.man7.org/linux/man-pages/man2/perf_event_open.2.html):
User-Space-CPU-Clock im Abstand von 20 ms CPU-Zeit, IP/TID/Callchain, ohne Kernel-
Stacks. Nach zehn Sekunden wird das Event deaktiviert und der Ringpuffer erst
danach ausgewertet. Keine Aufzeichnung von Audio, Nachrichten oder Stack-
Inhalten. Der Begleiter beendet ausschließlich den eigenen Sampler, falls das
Gerät beschäftigt wird oder die Laufzeit überschritten wird. Der C-Code wurde
auf dem Pi mit `-Wall -Wextra -Werror` ohne Warnungen kompiliert.

Diese Instrumentierung sowie die anschließende Symbolauswertung überlappen
mit dem Dauerlauf; ihr zusätzlicher Aufwand wurde nicht separat quantifiziert.
Das Intervall ist deshalb ausdrücklich als Diagnose zu behandeln, nicht als
unbeeinflusste Leerlauf-Baseline. Die private Rohprobe bleibt samt Prüfsummen
erhalten. Es handelt sich um **einen Thread und zehn Sekunden**, nicht die
Gesamt-CPU aller Browserprozesse oder einen Langzeitnachweis.

Der versionsgebundene Chromium-Code iteriert in diesen Pfaden über Agenten,
Scheduler beziehungsweise Aufgabenwarteschlangen. Quellen:
[AgentGroupSchedulerImpl, 142.0.7444.59](https://chromium.googlesource.com/chromium/src/+/refs/tags/142.0.7444.59/third_party/blink/renderer/platform/scheduler/main_thread/agent_group_scheduler_impl.cc),
[MainThreadSchedulerImpl, 142.0.7444.59](https://chromium.googlesource.com/chromium/src/+/refs/tags/142.0.7444.59/third_party/blink/renderer/platform/scheduler/main_thread/main_thread_scheduler_impl.cc).
Die Zahl dieser Objekte wurde hier **nicht** gemessen. Ein Zusammenhang mit
wiederholten SVG-Ladevorgängen ist eine zu prüfende Hypothese, kein bestätigter
Chromium-Bug. Der bisherige Mac-Vergleich verwendet Chrome 155 und kann das
Verhalten der Pi-Version 142 nicht ausschließen.

[Zusammenfassung, Symbolherkunft und Prüfsummen](summary.json),
[Sampler](sample.c), [historischer Aufruf mit Prozess- und Aktivitätsschutz](run-sample.py),
[historische Symbolauswertung](symbolize.py). Die Skripte beziehen sich ausdrücklich
auf diese PID, diese Build-ID und private Beweisdateien; keine allgemeine
Anleitung zum ungeprüften Ausführen an einem anderen Prozess.

Nächster Eingrenzungsschritt: eine begrenzte isolierte Reproduktion mit derselben
Pi-Chromium-Version, bei der wiederholte Bild-Ladevorgänge einzeln variiert werden.
Der Produktionsbrowser bleibt dafür unverändert. Keine App-Auslieferung und kein
Image-Einfluss durch diese Diagnose. Die Stabilitätsabnahme bleibt offen.

Ein enger Quellvergleich mit Tag 155.0.8059.41 zeigt für
`AgentGroupSchedulerImpl::PerformMicrotaskCheckpoint` denselben Funktionskörper;
auch die schwache Agentenmenge und die Page-Scheduler-Menge sind in beiden
Headern gleich deklariert. Daraus folgt **kein belegter Browser-Fix** zwischen
diesen Versionen. Andere Teile, Objektlebenszeiten und Plattformbedingungen
wurden damit nicht verglichen; ein Update wird nicht als bereits bewiesene
Lösung dargestellt.
