"""
Audio Recorder mit Live-Pegelanzeige
"""
import sounddevice as sd
import soundfile as sf
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Optional
from PySide6.QtCore import QObject, Signal
import time


class AudioRecorder(QObject):
    """Audio Recorder für Mikrofonaufnahmen"""

    # Qt Signals für Thread-sichere UI-Updates
    level_updated = Signal(float)  # RMS-Level 0.0 - 1.0
    duration_updated = Signal(float)  # Dauer in Sekunden
    waveform_updated = Signal(object)  # Audio-Daten für Waveform-Visualisierung

    def __init__(self, samplerate: int = 44100, channels: int = 1):
        super().__init__()
        self.samplerate = samplerate
        self.channels = channels
        self.is_recording = False
        self.is_paused = False
        self.frames = []
        self.paused_frames = []
        self.paused_device: Optional[int] = None
        self.stream: Optional[sd.InputStream] = None
        self.output_path: Optional[str] = None
        self._start_time: Optional[float] = None
        self._recorded_frames = 0  # Frame-basierte Zeiterfassung (kein stream.time mehr)

    def get_devices(self):
        """Gibt eine Liste aller verfügbaren Eingabegeräte zurück"""
        devices = sd.query_devices()
        input_devices = []

        for idx, device in enumerate(devices):
            if device['max_input_channels'] > 0:
                input_devices.append({
                    'index': idx,
                    'name': device['name'],
                    'channels': device['max_input_channels']
                })

        return input_devices

    def _audio_callback(self, indata, frames, time_info, status):
        """Callback für Audio-Stream - verwendet frame-basierte Zeiterfassung"""
        if status:
            print(f"Audio Status: {status}")

        # Daten speichern
        self.frames.append(indata.copy())

        # Frame-Counter erhöhen für präzise Zeiterfassung
        self._recorded_frames += len(indata)

        # RMS-Level berechnen und Signal emittieren
        rms = np.sqrt(np.mean(indata**2))
        self.level_updated.emit(float(rms))

        # Dauer aus Frame-Count berechnen (zuverlässig auf allen Plattformen!)
        duration = self._recorded_frames / self.samplerate
        self.duration_updated.emit(duration)

        # Waveform-Daten für Visualisierung emittieren
        self.waveform_updated.emit(indata.copy())

    def start_recording(self, device_index: Optional[int] = None,
                       output_dir: str = "recordings",
                       samplerate: Optional[int] = None) -> str:
        """Startet die Aufnahme und gibt den Output-Pfad zurück"""
        if self.is_recording:
            raise RuntimeError("Aufnahme läuft bereits")

        # Sample Rate überschreiben wenn angegeben
        if samplerate is not None:
            self.samplerate = samplerate

        # Device validieren und optimieren (für USB-Geräte)
        if device_index is not None:
            try:
                device_info = sd.query_devices(device_index)
                print(f"Verwende Gerät: {device_info['name']}")
                # Channels anpassen falls Gerät weniger unterstützt
                if device_info['max_input_channels'] < self.channels:
                    self.channels = device_info['max_input_channels']
            except Exception as e:
                print(f"Device-Validierung fehlgeschlagen: {e}, verwende Standard-Gerät")
                device_index = None

        # Output-Pfad als absoluten Pfad erstellen
        output_path = Path(output_dir).resolve()
        output_path.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.output_path = str(output_path / f"session_{timestamp}.wav")

        # Frames und Counter zurücksetzen
        self.frames = []
        self._recorded_frames = 0

        # Stream mit USB-optimierten Parametern starten
        self.stream = sd.InputStream(
            device=device_index,
            channels=self.channels,
            samplerate=self.samplerate,
            callback=self._audio_callback,
            blocksize=2048,  # Größere Blöcke für USB-Geräte (reduziert Timing-Fehler)
            latency='high',  # Stabilität über Latenz (wichtig für USB)
            prime_output_buffers_using_stream_callback=False,
            dither_off=True  # Weniger CPU-Last auf Raspberry Pi
        )

        self.stream.start()
        self.is_recording = True
        self._start_time = time.time()  # Nur für Referenz, nicht für Zeitberechnung

        print(f"🎙️ Aufnahme gestartet: {self.channels} Kanal(e), {self.samplerate} Hz")
        print(f"📁 Output: {self.output_path}")

        return self.output_path

    def stop_recording(self) -> Optional[str]:
        """Stoppt die Aufnahme und speichert die Datei"""
        if not self.is_recording:
            return None

        # Stream stoppen und warten bis alle Callbacks verarbeitet sind
        if self.stream and not self.is_paused:
            self.stream.stop()
            # Kurz warten damit letzte Callbacks verarbeitet werden
            time.sleep(0.1)
            self.stream.close()

        # Immer aktuelle frames verwenden (auch wenn pausiert, da paused_frames bei resume in frames kopiert wird)
        frames_to_save = self.paused_frames if self.is_paused else self.frames

        # Debug-Ausgabe für Diagnose
        total_frames = sum(len(f) for f in frames_to_save)
        duration = total_frames / self.samplerate
        print(f"📊 Aufnahme beendet: {len(frames_to_save)} Chunks, {total_frames} Frames, {duration:.2f} Sekunden")

        # Daten zusammenfügen und speichern (vor State-Reset!)
        output_file = None
        if frames_to_save and self.output_path:
            audio_data = np.concatenate(frames_to_save, axis=0)
            sf.write(self.output_path, audio_data, self.samplerate)
            output_file = self.output_path
            print(f"✅ Audio gespeichert: {output_file}")

        # Jetzt erst State zurücksetzen
        self.stream = None
        self.is_recording = False
        self.is_paused = False
        self._start_time = None
        self._recorded_frames = 0
        self.paused_frames = []
        self.paused_device = None
        self.frames = []  # Frames auch zurücksetzen

        return output_file

    def pause_recording(self) -> bool:
        """Pausiert die Aufnahme ohne Datei zu speichern"""
        if not self.is_recording or self.is_paused:
            return False

        # Device-Index merken
        self.paused_device = self.stream.device if self.stream else None

        # Stream stoppen
        if self.stream:
            self.stream.stop()
            # Kurz warten damit letzte Callbacks verarbeitet werden
            time.sleep(0.1)
            self.stream.close()
            self.stream = None

        # Frames sichern
        self.paused_frames = self.frames.copy()
        self.is_paused = True

        # Debug-Ausgabe
        total_frames = sum(len(f) for f in self.paused_frames)
        duration = total_frames / self.samplerate
        print(f"⏸️ Aufnahme pausiert: {len(self.paused_frames)} Chunks, {duration:.2f} Sekunden")

        return True

    def resume_recording(self) -> bool:
        """Setzt pausierte Aufnahme fort"""
        if not self.is_recording or not self.is_paused:
            return False

        # Frames wiederherstellen
        self.frames = self.paused_frames.copy()

        # Frame-Counter auf aktuelle Anzahl setzen
        self._recorded_frames = sum(len(f) for f in self.frames)

        # Debug-Ausgabe
        duration = self._recorded_frames / self.samplerate
        print(f"▶️ Aufnahme fortgesetzt: {len(self.frames)} Chunks, {duration:.2f} Sekunden wiederhergestellt")

        # Stream mit USB-optimierten Parametern neu starten
        self.stream = sd.InputStream(
            device=self.paused_device,
            channels=self.channels,
            samplerate=self.samplerate,
            callback=self._audio_callback,
            blocksize=2048,  # USB-optimiert
            latency='high',  # Stabilität
            prime_output_buffers_using_stream_callback=False,
            dither_off=True
        )
        self.stream.start()

        # Nur Referenz-Zeit setzen (Frame-Counter macht Zeitberechnung)
        self._start_time = time.time()

        self.is_paused = False
        self.paused_frames = []

        return True

    def get_duration_seconds(self) -> int:
        """Gibt die Dauer der Aufnahme in Sekunden zurück"""
        if not self.frames:
            return 0

        total_frames = sum(len(f) for f in self.frames)
        return int(total_frames / self.samplerate)
