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


class AudioRecorder(QObject):
    """Audio Recorder für Mikrofonaufnahmen"""

    # Qt Signals für Thread-sichere UI-Updates
    level_updated = Signal(float)  # RMS-Level 0.0 - 1.0
    duration_updated = Signal(float)  # Dauer in Sekunden

    def __init__(self, samplerate: int = 44100, channels: int = 1):
        super().__init__()
        self.samplerate = samplerate
        self.channels = channels
        self.is_recording = False
        self.frames = []
        self.stream: Optional[sd.InputStream] = None
        self.output_path: Optional[str] = None
        self._start_time: Optional[float] = None

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

    def _audio_callback(self, indata, frames, time, status):
        """Callback für Audio-Stream"""
        if status:
            print(f"Status: {status}")

        # Daten speichern
        self.frames.append(indata.copy())

        # RMS-Level berechnen und Signal emittieren
        rms = np.sqrt(np.mean(indata**2))
        self.level_updated.emit(float(rms))

        # Dauer berechnen und Signal emittieren
        if self._start_time:
            duration = time.currentTime - self._start_time
            self.duration_updated.emit(duration)

    def start_recording(self, device_index: Optional[int] = None,
                       output_dir: str = "recordings") -> str:
        """Startet die Aufnahme und gibt den Output-Pfad zurück"""
        if self.is_recording:
            raise RuntimeError("Aufnahme läuft bereits")

        # Output-Pfad erstellen
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.output_path = f"{output_dir}/session_{timestamp}.wav"

        # Frames zurücksetzen
        self.frames = []

        # Stream starten
        self.stream = sd.InputStream(
            device=device_index,
            channels=self.channels,
            samplerate=self.samplerate,
            callback=self._audio_callback
        )

        self.stream.start()
        self.is_recording = True
        self._start_time = self.stream.time

        return self.output_path

    def stop_recording(self) -> Optional[str]:
        """Stoppt die Aufnahme und speichert die Datei"""
        if not self.is_recording:
            return None

        # Stream stoppen
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None

        self.is_recording = False
        self._start_time = None

        # Daten zusammenfügen und speichern
        if self.frames and self.output_path:
            audio_data = np.concatenate(self.frames, axis=0)
            sf.write(self.output_path, audio_data, self.samplerate)
            return self.output_path

        return None

    def get_duration_seconds(self) -> int:
        """Gibt die Dauer der Aufnahme in Sekunden zurück"""
        if not self.frames:
            return 0

        total_frames = sum(len(f) for f in self.frames)
        return int(total_frames / self.samplerate)
