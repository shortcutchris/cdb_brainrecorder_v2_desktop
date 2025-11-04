"""
Audio Player für Wiedergabe von Sessions
"""
import sounddevice as sd
import soundfile as sf
import numpy as np
from pathlib import Path
from typing import Optional
from PySide6.QtCore import QObject, Signal, QTimer
import threading
import time


class AudioPlayer(QObject):
    """Audio Player für Session-Wiedergabe"""

    # Qt Signals
    playback_started = Signal()
    playback_paused = Signal()
    playback_stopped = Signal()
    playback_finished = Signal()
    position_changed = Signal(float)  # Position in Sekunden
    duration_changed = Signal(float)  # Gesamtdauer in Sekunden
    _stop_timer_signal = Signal()  # Internes Signal für Thread-sicheren Timer-Stop

    def __init__(self):
        super().__init__()
        self.is_playing = False
        self.is_paused = False
        self.current_file: Optional[str] = None
        self.audio_data: Optional[np.ndarray] = None
        self.samplerate: int = 44100
        self.stream: Optional[sd.OutputStream] = None
        self.current_frame: int = 0
        self.total_frames: int = 0
        self._position_timer = QTimer()
        self._position_timer.timeout.connect(self._update_position)
        # Signal für Thread-sicheren Timer-Stop
        self._stop_timer_signal.connect(self._position_timer.stop)

    def load_file(self, file_path: str) -> bool:
        """Lädt eine Audio-Datei"""
        try:
            if not Path(file_path).exists():
                return False

            self.audio_data, self.samplerate = sf.read(file_path, dtype='float32')
            self.current_file = file_path
            self.total_frames = len(self.audio_data)
            self.current_frame = 0

            duration = self.total_frames / self.samplerate
            self.duration_changed.emit(duration)
            self.position_changed.emit(0.0)

            return True
        except Exception as e:
            print(f"Fehler beim Laden der Datei: {e}")
            return False

    def play(self):
        """Startet oder setzt die Wiedergabe fort"""
        if self.audio_data is None:
            return

        if self.is_paused:
            # Fortsetzen
            self.is_paused = False
            self.is_playing = True
            self.playback_started.emit()
            self._position_timer.start(100)  # Update alle 100ms
            return

        if self.is_playing:
            return

        # Neue Wiedergabe starten
        self.is_playing = True
        self.is_paused = False
        self.playback_started.emit()
        self._position_timer.start(100)

        # Wiedergabe in separatem Thread
        threading.Thread(target=self._play_audio, daemon=True).start()

    def pause(self):
        """Pausiert die Wiedergabe"""
        if self.is_playing and not self.is_paused:
            self.is_paused = True
            self.is_playing = False
            self.playback_paused.emit()
            self._stop_timer_signal.emit()

    def stop(self):
        """Stoppt die Wiedergabe"""
        # Erst Flags setzen damit Callback aufhört
        self.is_playing = False
        self.is_paused = False
        self._stop_timer_signal.emit()

        # Kurz warten damit laufende Callbacks beendet werden
        time.sleep(0.05)

        # Stream sicher schließen mit Error Handling
        if self.stream:
            try:
                # Nicht stop() aufrufen, direkt abort() für sofortigen Stop
                if self.stream.active:
                    self.stream.abort()
                self.stream.close()
            except Exception as e:
                # Fehler beim Schließen ignorieren (häufig bei ALSA)
                pass
            finally:
                self.stream = None

        # Position zurücksetzen
        self.current_frame = 0

        self.playback_stopped.emit()
        self.position_changed.emit(0.0)

    def seek(self, position: float):
        """Springt zu einer Position (in Sekunden)"""
        if self.audio_data is None:
            return

        was_playing = self.is_playing
        if was_playing:
            self.stop()

        self.current_frame = int(position * self.samplerate)
        self.current_frame = max(0, min(self.current_frame, self.total_frames))

        self.position_changed.emit(self.current_frame / self.samplerate)

        if was_playing:
            self.play()

    def _play_audio(self):
        """Spielt Audio ab (läuft in separatem Thread)"""
        try:
            # Mono zu Stereo falls nötig
            if len(self.audio_data.shape) == 1:
                audio_to_play = self.audio_data
                channels = 1
            else:
                audio_to_play = self.audio_data
                channels = self.audio_data.shape[1]

            # Stream erstellen - Auto-select device für bessere macOS Kompatibilität
            self.stream = sd.OutputStream(
                samplerate=self.samplerate,
                channels=channels,
                dtype='float32'
                # Kein explizites Device - lässt PortAudio das richtige wählen
            )
            self.stream.start()

            # Chunk-Größe
            chunk_size = 1024

            while self.is_playing or self.is_paused:
                if self.is_paused:
                    # Warten während Pause
                    threading.Event().wait(0.1)
                    continue

                if self.current_frame >= self.total_frames:
                    # Ende erreicht
                    self.is_playing = False
                    self.playback_finished.emit()
                    break

                # Nächsten Chunk holen
                end_frame = min(self.current_frame + chunk_size, self.total_frames)
                chunk = audio_to_play[self.current_frame:end_frame]

                # Abspielen
                self.stream.write(chunk)
                self.current_frame = end_frame

                # Kurze Pause, um CPU-Last zu reduzieren und Timing zu verbessern
                time.sleep(0.001)  # 1ms

        except Exception as e:
            print(f"Fehler bei Wiedergabe: {e}")
        finally:
            # Stream sicher schließen
            if self.stream:
                try:
                    # Abort statt stop für schnelleren, sicheren Stop
                    if self.stream.active:
                        self.stream.abort()
                    self.stream.close()
                except Exception:
                    # Fehler beim Stream-Cleanup ignorieren (häufig bei ALSA)
                    pass
                finally:
                    self.stream = None
            # Timer-Stop über Signal (thread-sicher)
            self._stop_timer_signal.emit()

    def _update_position(self):
        """Aktualisiert die Position (wird vom Timer aufgerufen)"""
        if self.audio_data is not None and self.is_playing:
            position = self.current_frame / self.samplerate
            self.position_changed.emit(position)

    def get_duration(self) -> float:
        """Gibt die Gesamtdauer in Sekunden zurück"""
        if self.audio_data is None:
            return 0.0
        return self.total_frames / self.samplerate

    def get_position(self) -> float:
        """Gibt die aktuelle Position in Sekunden zurück"""
        if self.audio_data is None:
            return 0.0
        return self.current_frame / self.samplerate
