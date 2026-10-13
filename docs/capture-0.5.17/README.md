# Aufnahmesteuerung 0.5.17 · 13.10.2026

## Bedienung

Zwei gleich große Touchbuttons unter dem Pegel: **Mikro stumm / Mikro einschalten** und **Pause / Fortsetzen**. Mute schreibt Nullsamples, die Zeit läuft weiter. Pause verwirft eingehendes Audio, die gespeicherte Dauer bleibt stehen. Fortsetzen erhält den vorherigen Mute-Zustand. Stoppen funktioniert auch während Pause, erstellt eine WAV-Datei und genau einen Queue-Auftrag. Notizen bleiben verfügbar; die übrigen Ansichten bleiben bis zum Stop gesperrt.

Die Mikrofonquelle bleibt offen, auch wenn ihre Samples verworfen werden. Die App schaltet noch keinen Hardware-Mute und keine Hardware-LED um. Unterbrechungen während Pause enden über die vorhandene Wiederherstellung als gesicherte Teilaufnahme.

## Tests

- Shared engine 0.2.7: 58 Tests auf dem Pi bestanden, inklusive realem PCM-Kindprozess, Nullsamples während Mute, unveränderter Dateigröße während Pause, Resume, Stop und Linux-Absturzabsicherung.
- Python-App: 87 Tests auf dem Pi bestanden.
- JavaScript: 49 Tests bestanden.
- Separate Vorschau auf dem Pi mit künstlicher PCM-Quelle: Aufnahme starten, stummschalten, pausieren, fortsetzen (weiter stumm), Mikro wieder einschalten, Stop, Start einer zweiten Aufnahme und Stop aus Pause. Navigation anschließend wieder frei. Verarbeitung der vorigen Aufnahme lief parallel.
- UI bei 1280 × 720 geprüft, einschließlich Bildschirmtastatur. Screenshots in diesem Ordner stammen aus der synthetischen Testbibliothek; keine echten Meetings oder Cloud-Verarbeitung.

## Bluetooth

Auswahl ergänzt um verbundene Bluetooth-Mikrofone aus PipeWire/PulseAudio. Monitorquellen ausgeschlossen. Aufnahme und 5-Sekunden-Test benutzen FFmpeg/Pulse mit 16-kHz-Mono-PCM. Pairing und Profilumschaltung verbleiben beim Betriebssystem. Bluetooth-Ausgabe war bereits in 0.5.16 enthalten. Das gepaarte Anker PowerConf S3 war bei der Prüfung nicht verbunden; daher noch kein echter Bluetooth-Audiotest.

## ReSpeaker XVF3800: Diagnose und Quellen

Zunächst erschien das eingeschaltete Gerät weder in `lsusb` noch in `arecord -l`. Der USB-Audiotreiber war bereits geladen. Nach dem vom Benutzer ausgelösten Safe Mode wurde **2886:001a, reSpeaker XVF3800 4-Mic Array**, einschließlich DFU Upgrade/Factory/DataPartition erkannt. Die USB-Verbindung funktioniert somit grundsätzlich. Der ursprüngliche Firmwarestand ist unbekannt; I²S-Modus ist eine plausible Ursache, nicht ausgelesen bestätigt.

Seeed dokumentiert für die XIAO-ESP32S3-Variante ab Werk I²S-Firmware, die nicht als USB-Audiogerät erscheint. Die USB-Firmware unterstützt Raspberry Pi OS ohne separaten Audio-Kerneltreiber. LED-Steuerung ist über das offizielle Python-Hosttool möglich. Ein Firmwarewechsel ist separat mit dem Benutzer abzustimmen.

- [Seeed FAQ](https://wiki.seeedstudio.com/respeaker_xvf3800_faq/)
- [XIAO-Variante und Betriebsmodi](https://wiki.seeedstudio.com/respeaker_xvf3800_xiao_getting_started/)
- [Anschlüsse und Safe Mode](https://wiki.seeedstudio.com/respeaker_xvf3800_introduction/)
- [Python-Hosttool und LEDs](https://wiki.seeedstudio.com/respeaker_xvf3800_python_sdk/)
- [Offizielle USB-Firmware](https://github.com/respeaker/reSpeaker_XVF3800_USB_4MIC_ARRAY/tree/master/xmos_firmwares/usb)

Offizielles Repository lokal geprüft bei Commit `4b49bfd19977c63cf6e90dfe9e5827e74e20bf6d`: aktuelles USB-Release v2.1.1, neuer als der in Teilen des Wikis genannte Stand v2.1.0.

## Produktiv installiert

Studio **0.5.17**, Engine **0.2.7** auf dem Pi installiert; Backend und Kiosk aktiv. Alle 22 vorhandenen Aufnahmen, Modellkonfiguration, Brain-Anmeldung und Standardbereich erhalten. Dateihashes lokal/remote identisch (siehe `deployment.json`). Rücksicherung inklusive vorheriger Engine unter `/home/chris/backups/recorder-before-0.5.17`. Separater Vorschaudienst beendet, temporäre Anmeldung entfernt. Das ReSpeaker befindet sich noch im Safe Mode; Firmwarewechsel wartet auf Zustimmung, deshalb noch kein echter Mikrofon-Audiotest.
