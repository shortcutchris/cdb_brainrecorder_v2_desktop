# Interne Soundbar in Recorder Studio einrichten und testen

Diese Anleitung gilt für den Raspberry Pi 5 mit der USB-Soundbar `188A` am internen Waveshare-PCIe-Board (C). Der [Hardware-Leitfaden](https://github.com/shortcutchris/raspberry_pi_meeting_recorder/blob/main/docs/hardware-tests/soundbar-am-internen-usb-board.md) beschreibt die Verkabelung, das erprobte Gen1-Bootprofil und den Wiederanlauf bei einem festgefahrenen USB-Controller.

## Vor dem ersten Hörtest

Im Terminal des angemeldeten Pi-Desktopbenutzers prüfen:

```sh
lsusb -d 0020:0b21
wpctl status
command -v pactl
command -v paplay
```

Die USB-Abfrage soll die `188A` finden. Unter **Audio → Sinks** soll PipeWire **188A Analog Stereo** anbieten. Studio verwendet `pactl` für die Geräteauswahl und `paplay` für den Testton. Fehlen diese Programme auf einer bestehenden Installation, das Paket aus den konfigurierten Raspberry-Pi-OS-Paketquellen installieren:

```sh
sudo apt-get install --no-install-recommends pulseaudio-utils
```

Der vorhandene PipeWire-Dienst stellt die PulseAudio-Schnittstelle bereit. Das Paket enthält die Clientprogramme. Das [SD-Image-Rezept](../../scripts/prepare_customer_image.py) enthält `pulseaudio-utils` bereits; auf jeder frisch beschriebenen Karte den realen Ausgang und den Hörtest prüfen. Ein reines Studio-App-Update installiert fehlende Systempakete auf einem Bestandsgerät nicht nach.

## Test am Gehäuse

1. Laufende Aufnahme, Pause oder Unterhaltung zuerst regulär abschließen. **Einstellungen → Audio → Lautsprecher** öffnen und **Geräte aktualisieren** antippen.
2. **188A Analog Stereo** wählen. Ein ebenfalls angeschlossener **reSpeaker XVF3800** hat einen eigenen Ausgang. Studio speichert die Auswahl und setzt die Soundbar als Standardausgang des Pi. Stummschaltung prüfen; beim bestätigten Test waren **40 %** eingestellt.
3. **Testton am Pi** antippen. Am Gehäuse zuerst links einen tieferen Ton (440 Hz), danach rechts einen höheren Ton (660 Hz) bestätigen. Bei Fernbedienung über einen Browser spielt dieser Knopf ebenfalls auf dem Pi.
4. Bei Bedarf den technischen Abschluss prüfen: `curl -fsS http://127.0.0.1:8088/api/speakers` liefert auf dem Gerät unter anderem `available`, `selected`, `is_default` und den letzten Teststatus. Für die Hörabnahme zählt zusätzlich die Rückmeldung vor Ort.

Auf dem ersten Gerät liegt außerdem **Bibliothek → Lautsprechertest – links und rechts**. Dieser Bibliothekseintrag ist eine lokal hinterlegte WAV-Datei. Der Bibliotheksplayer spielt auf dem Gerät, auf dem der Browser läuft. Für einen neuen Pi steht der eingebaute Testknopf auch ohne diesen Eintrag zur Verfügung.

## Wenn Studio „Kein Lautsprecher erkannt“ meldet

| Beobachtung | Nächster Schritt |
| --- | --- |
| `wpctl status` zeigt die 188A, Studio meldet fehlendes `pactl` oder `paplay` | `pulseaudio-utils` installieren und die Geräte in Studio aktualisieren. |
| Nur der reSpeaker erscheint, `lsusb -d 0020:0b21` findet kein Gerät | Den internen Hub und das Bootprotokoll prüfen. Bei `HC died` dem [Wiederanlauf im Hardware-Leitfaden](https://github.com/shortcutchris/raspberry_pi_meeting_recorder/blob/main/docs/hardware-tests/soundbar-am-internen-usb-board.md#wenn-der-usb-controller-h%C3%A4ngen-bleibt) folgen. |
| 188A ist sichtbar, aber der Test bleibt stumm | Auswahl, Stummschaltung und Lautstärke prüfen. Nach dem Versuch USB-Erkennung und Kernelprotokoll erneut prüfen. Ein abgeschlossener Abspielprozess allein belegt keine hörbare Ausgabe. |

**Abnahme vom 12. November 2026:** Auf Recorder Studio 0.5.71 wurden die fehlenden Clientprogramme installiert. Nach einem geordneten Neustart erkannte Studio Soundbar und reSpeaker getrennt. Die 188A blieb intern angeschlossen. Der Test erreichte ihren USB-Wiedergabestrom, und Chris bestätigte beide Kanäle am Gehäuse.

## Erneuter Controllerausfall am 23. November

Am 24.11.2026 bei der Nachfrage zum Klangtest erneut lesend geprüft. Der Kernel
zeigt: Soundbar `0020:0b21` beim Boot am 23.11. um 16:42 Uhr erkannt; um
**18:58:35 Uhr (Europe/Berlin)** meldet der externe Controller `0001:01:00.0`
`xHCI host controller not responding, assume dead`, `HC died; cleaning up`
und einen Timeout bei `configure endpoint`. Danach verschwinden der interne
Hub und die Soundbar. Das liegt vor dem App-Update auf 0.5.99 am 24. November.

Bei dieser ersten Prüfung ist der VL805/806 noch per PCI sichtbar, aber `lsusb` enthält weder den
internen Hub noch die Soundbar. PipeWire bietet nur den separat angeschlossenen
reSpeaker. Die gespeicherte Auswahl bleibt die 188A; `/api/speakers` meldet
`available=false`. Keine automatische Umleitung auf den reSpeaker vorgenommen.
Das Bootprofil enthält weiterhin externes PCIe, 100 ms Resetverzögerung und Gen1.
`get_throttled` liefert aktuell `0x0`; das erklärt die Ursache des USB-Hängers nicht.

Chris hat den Pi anschließend selbst aus- und wieder eingeschaltet. Danach
waren interner Hub und 188A wieder vorhanden; die gespeicherte Soundbar war
verfügbar und als Standard ausgewählt. Am 24.11. um **09:40:26 Uhr** tritt beim
erneuten Audiotest derselbe Fehler wieder auf: `HC died`, Timeout beim
`configure endpoint`, danach `Not enough bandwidth for altsetting 1`,
`usb_set_interface failed (-62)` und Abmeldung von Hub und Soundbar.

Der Links-/Rechts-Abspielprozess auf Recorder 0.5.100 meldete zwar `completed`,
aber eine hörbare Ausgabe wurde nicht bestätigt. Der folgende Glockentest
wurde mit „Gewählter Lautsprecher nicht verbunden“ abgelehnt. Lautsprecherwahl
und Lautstärke wurden nicht geändert. Kein Umleiten auf den reSpeaker.
`get_throttled=0x0`; das schließt ein Problem der Erweiterungsboardversorgung
oder PCIe-Verbindung nicht aus. Die Bandbreitenmeldung allein beweist keine
reale Überlastung des Busses.

Ein Neustart ist damit nur ein vorübergehender Wiederanlauf. Als nächste
Diagnose sind FPC-Verbindung, Boardversorgung und der externe Controller samt
Treiber zu prüfen. Die Grundursache bleibt offen. Das Zusatzdisplay hängt an
einem anderen USB-Controller und bleibt dabei erreichbar.

## Nachprüfung am 24. November, nach der UI-Abnahme von 0.5.104

Zwei getrennte Prüfungen von USB/PCIe und Audio-Ansteuerung bestätigen den
Controllerausfall von 09:40:26 Uhr. PipeWire/WirePlumber liefen seit 09:23 Uhr ohne
Dienstneustart weiter. Die Soundbar fehlt auf USB-, ALSA- und PipeWire-Ebene.
Der später angelegte UI-Testtimer lief korrekt ab, konnte jedoch keinen Alarmton
ausgeben. Um 13:26:17 Uhr wurde über die normale Lautsprecherkonfiguration der
reSpeaker als Ausgang gespeichert; das war kein automatischer App-Fallback.
Ein verfügbarer reSpeaker-Ausgang belegt keine Ausgabe über die USB-Soundbar.

Das Gerät ist verschraubt. Ein zunächst als erfolgt gemeldetes Umstecken wurde
vom Nutzer ausdrücklich korrigiert; ein Vergleichstest direkt am Pi hat nicht
stattgefunden. Ein gezieltes Neubinden nur des externen VIA-Controllers wurde
vorbereitet, nach Aktivitätsprüfung aber durch die erforderliche
Administrator-Passwortbestätigung vor Ausführung gestoppt. Kein Reset, kein
Neustart, kein neues Release und keine Lautsprecheränderung durch diese Prüfung.
Details und Grenzen: [Bedien- und Hardwareprüfung](../ui-acceptance-0.5.104/README.md).
