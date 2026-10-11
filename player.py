"""Bounded-memory soundfile/sounddevice player. Loading reads metadata only."""
import threading
import sounddevice as sd
import soundfile as sf
from PySide6.QtCore import QObject, Signal, QTimer


class AudioPlayer(QObject):
    error = Signal(str)
    playback_started = Signal()
    playback_paused = Signal()
    playback_stopped = Signal()
    playback_finished = Signal()
    position_changed = Signal(float)
    duration_changed = Signal(float)

    def __init__(self):
        super().__init__()
        self.file = self.stream = None
        self.current_file = None
        self.is_playing = self.is_paused = False
        self.lock = threading.RLock()
        self.total_frames = self.current_frame = 0
        self.samplerate = 16000
        self._position_timer = QTimer(self)
        self._position_timer.setInterval(250)
        self._position_timer.timeout.connect(self._tick)

    def load_file(self, path):
        self.stop()
        with self.lock:
            if self.file: self.file.close()
            self.file = sf.SoundFile(path)
            self.samplerate = self.file.samplerate
            self.total_frames = len(self.file)
            self.current_file = path
            self.current_frame = 0
        self.duration_changed.emit(self.total_frames/self.samplerate)
        return True

    def _callback(self, out, frames, times, status):
        with self.lock:
            data = self.file.read(frames, dtype='float32', always_2d=True)
            out.fill(0)
            out[:len(data)] = data
            self.current_frame = self.file.tell()
            if len(data) < frames:
                raise sd.CallbackStop()

    def play(self):
        if not self.file or self.is_playing: return
        if self.current_frame >= self.total_frames: self.seek(0)
        try:
            self.stream = sd.OutputStream(samplerate=self.samplerate, channels=self.file.channels,
                                          blocksize=2048, callback=self._callback)
            self.stream.start()
        except Exception as e:
            if self.stream:self.stream.close();self.stream=None
            self.error.emit('Audioausgabe nicht verfügbar: '+str(e))
            return False
        self.is_playing, self.is_paused = True, False
        self._position_timer.start()
        self.playback_started.emit()

    def _tick(self):
        self.position_changed.emit(self.current_frame/self.samplerate)
        if self.stream and not self.stream.active and self.is_playing:
            self.stop(); self.playback_finished.emit()

    def pause(self):
        if self.stream: self.stream.stop(); self.stream.close(); self.stream = None
        self.is_playing, self.is_paused = False, True
        self._position_timer.stop(); self.playback_paused.emit()

    def stop(self):
        self.pause()
        self.is_paused = False
        if self.file:
            with self.lock: self.file.seek(0); self.current_frame = 0
        self.playback_stopped.emit()

    def seek(self, seconds):
        with self.lock:
            if self.file:
                self.current_frame = min(self.total_frames, max(0, int(seconds*self.samplerate)))
                self.file.seek(self.current_frame)

    def get_position(self): return self.current_frame/self.samplerate
    def get_duration(self): return self.total_frames/self.samplerate
    def close(self):
        self.stop()
        if self.file: self.file.close(); self.file = None
