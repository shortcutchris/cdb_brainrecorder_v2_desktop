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
