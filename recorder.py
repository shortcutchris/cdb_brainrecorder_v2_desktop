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

        # Waveform-Daten für Visualisierung emittieren
        self.waveform_updated.emit(indata.copy())

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

        # Wenn pausiert, verwende paused_frames
        frames_to_save = self.paused_frames if self.is_paused else self.frames

        # Stream stoppen (nur wenn nicht pausiert)
        if self.stream and not self.is_paused:
            self.stream.stop()
            self.stream.close()

        self.stream = None
        self.is_recording = False
        self.is_paused = False
        self._start_time = None
        self.paused_frames = []
        self.paused_device = None

        # Daten zusammenfügen und speichern
        if frames_to_save and self.output_path:
            audio_data = np.concatenate(frames_to_save, axis=0)
            sf.write(self.output_path, audio_data, self.samplerate)
            return self.output_path

        return None

    def pause_recording(self) -> bool:
        """Pausiert die Aufnahme ohne Datei zu speichern"""
        if not self.is_recording or self.is_paused:
            return False

        # Device-Index merken
        self.paused_device = self.stream.device if self.stream else None

        # Stream stoppen
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None

        # Frames sichern
        self.paused_frames = self.frames.copy()
        self.is_paused = True

        return True

    def resume_recording(self) -> bool:
        """Setzt pausierte Aufnahme fort"""
        if not self.is_recording or not self.is_paused:
            return False

        # Frames wiederherstellen
        self.frames = self.paused_frames.copy()

        # Stream neu starten
        self.stream = sd.InputStream(
            device=self.paused_device,
            channels=self.channels,
            samplerate=self.samplerate,
            callback=self._audio_callback
        )
        self.stream.start()

        # Start-Zeit anpassen (um bereits aufgenommene Zeit zu berücksichtigen)
        if self.frames:
            recorded_frames = sum(len(f) for f in self.frames)
            recorded_duration = recorded_frames / self.samplerate
            self._start_time = self.stream.time - recorded_duration
        else:
            self._start_time = self.stream.time

        self.is_paused = False
        self.paused_frames = []

        return True

    def get_duration_seconds(self) -> int:
        """Gibt die Dauer der Aufnahme in Sekunden zurück"""
        if not self.frames:
            return 0

        total_frames = sum(len(f) for f in self.frames)
        return int(total_frames / self.samplerate)
