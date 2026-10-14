# Gesprächsstart · 0.5.39

Am 14.10.2026 blieb beim Test auf dem Pi eine TCP-Verbindung zu einer
Cloudflare-IPv6-Adresse im Zustand SYN-SENT. Die Standardbibliothek probierte
Adressen nacheinander mit dem hohen HTTP-Lesezeitlimit. Derselbe Gesprächsstart
war nach 100 Sekunden noch nicht bereit. Zusätzlich schwankte DNS zwischen
Millisekunden und rund 5–8 Sekunden. Der erste Verdacht „IPv6 generell kaputt“
war zu grob: Andere IPv6-Verbindungen funktionierten. Speicher und Temperatur
waren unauffällig (kein Throttling).

## Änderung

- Verfügbare IPv6-/IPv4-Adressen werden abwechselnd versucht, neue Versuche nach
  250 ms. TCP-Verbindungsaufbau insgesamt maximal zehn Sekunden (DNS davor).
  Nur Sockets werden parallel geöffnet; HTTP-Aufträge werden niemals wiederholt.
- Nicht gewählte Sockets werden geschlossen. Auch Systeme ohne IPv6-Unterstützung
  fallen auf die nächste Adresse zurück. Lesen behält das bestehende Zeitlimit.
- DNS-Ergebnisse bleiben höchstens 30 Sekunden in einem auf 64 Ziele begrenzten
  Prozesscache. Verbindungsfehler verwerfen den Eintrag. Keine fest codierten IPs,
  keine Änderung des Routers, DNS-Anbieters oder globalen IPv6-Verhaltens.
- HTTPS bleibt bei Standard-TLS, SNI, Hostnamen- und Zertifikatsprüfung, ohne
  Weiterleitungen/Proxy. Der gemeinsame Pfad umfasst Anmeldung, CDB-HTTP,
  Live-Ereignisstrom und Upload.
- Die feste Statusfläche zeigt Startschritt und Gesamtwartezeit. Der Zustand
  „Hört zu“ wartet auf die echte WebRTC-Verbindung. Ein Abbruch in dieser Phase
  endet ohne falsche Fehlermeldung. Audioverhandlung maximal 15 Sekunden.

## Messungen

[Vorher](before.json): erster Start nach 100 Sekunden abgebrochen, kein Audio bereit.
[Nachher](after.json): zwei echte CDB-Staging-Sitzungen mit synthetischem, stummem
Eingang und isolierter Ausgabe: **8,01 / 7,41 Sekunden** ab Start bis Bereitschaft.

[Hardwaretest](hardware.json): **7,53 Sekunden** mit realem ReSpeaker über PipeWire
und Marshall-Ausgang. 360 Mikrofonframes wurden gelesen. Vor Öffnen wurde die
Audiosperre aktiviert, sodass ausschließlich Null-PCM zum Brain ging; kein
Raumton übertragen oder gespeichert. Der vorher laufende Produktions-Wake-Detektor
wurde für die Prüfung über eine begrenzte Wiedergabe-Reservierung freigegeben und
danach wieder freigelassen. Der Bereitschaftston wurde am echten Ausgang abgespielt.
Dies misst Hardwareübergabe/Verbindung, nicht die Spracherkennungsquote des Wake Words.

Etwa 5,2–5,3 Sekunden bleiben die native SDP/ICE-Verhandlung. Sie wird nicht durch
Weglassen von NAT-Kandidaten beschleunigt, da das Erreichbarkeit beeinträchtigen könnte.
Die Tests sind Einzelmessungen, keine garantierte Obergrenze für jeden Netzwerkzustand.
Reproduktion: [probe_pi.py](probe_pi.py), private Anmeldung nur im Pi-Testverzeichnis.

Die Oberflächenansicht „Verbindung wird aufgebaut“ wird zusätzlich mit einer
klar isolierten UI-Testinstanz geprüft; dort läuft kein Gespräch. Das Bild „Hört zu“
stammt dagegen aus dem echten synthetischen CDB-Test.

Neue Regressionstests prüfen unerreichbare IPv6-Kandidaten, fehlende IPv6-Unterstützung,
Zeitlimits und Socket-Bereinigung, DNS-Cache-Ablauf, unveränderte TLS-Prüfung,
echte lokale TCP-Kommunikation, Abbruch während Audioaufbau sowie die sichtbare
Startphase. Oberflächenbilder:
[Aufbau (isolierte UI-Testinstanz)](../../output/playwright/startup-0.5.39/01-connecting-fixture.png),
[Verbunden (echter CDB-Test)](../../output/playwright/startup-0.5.39/02-connected.png).

Abschluss: 218 Python-Tests auf dem Pi und 99 JavaScript-Tests bestanden.
