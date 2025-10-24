"""
Playback-Widget für Audio-Wiedergabe
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QLabel, QSlider, QGroupBox)
from PySide6.QtCore import Qt, Signal
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from player import AudioPlayer


class PlayerWidget(QWidget):
    """Widget für Audio-Wiedergabe"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.player = AudioPlayer()
        self.is_seeking = False  # Flag für Slider-Interaktion
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """Initialisiert das Widget"""
        layout = QVBoxLayout(self)

        # GroupBox
        group = QGroupBox("Audio Player")
        group_layout = QVBoxLayout()

        # Dateiname-Label
        self.file_label = QLabel("Keine Datei geladen")
        self.file_label.setStyleSheet("font-style: italic;")
        group_layout.addWidget(self.file_label)

        # Zeit-Anzeige
        time_layout = QHBoxLayout()
        self.current_time_label = QLabel("00:00")
        self.total_time_label = QLabel("00:00")
        time_layout.addWidget(self.current_time_label)
        time_layout.addStretch()
        time_layout.addWidget(self.total_time_label)
        group_layout.addLayout(time_layout)

        # Fortschrittsbalken (Slider)
        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setMinimum(0)
        self.progress_slider.setMaximum(1000)  # Verwende 1000 für bessere Genauigkeit
        self.progress_slider.setValue(0)
        self.progress_slider.sliderPressed.connect(self._on_slider_pressed)
        self.progress_slider.sliderReleased.connect(self._on_slider_released)
        self.progress_slider.sliderMoved.connect(self._on_slider_moved)
        group_layout.addWidget(self.progress_slider)

        # Control Buttons
        button_layout = QHBoxLayout()

        self.play_button = QPushButton("Play")
        self.play_button.clicked.connect(self._on_play_clicked)
        self.play_button.setEnabled(False)

        self.pause_button = QPushButton("Pause")
        self.pause_button.clicked.connect(self._on_pause_clicked)
        self.pause_button.setEnabled(False)

        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self._on_stop_clicked)
        self.stop_button.setEnabled(False)

        button_layout.addWidget(self.play_button)
        button_layout.addWidget(self.pause_button)
        button_layout.addWidget(self.stop_button)
        button_layout.addStretch()

        group_layout.addLayout(button_layout)

        group.setLayout(group_layout)
        layout.addWidget(group)

    def _connect_signals(self):
        """Verbindet Player-Signals"""
        self.player.playback_started.connect(self._on_playback_started)
        self.player.playback_paused.connect(self._on_playback_paused)
        self.player.playback_stopped.connect(self._on_playback_stopped)
        self.player.playback_finished.connect(self._on_playback_finished)
        self.player.position_changed.connect(self._on_position_changed)
        self.player.duration_changed.connect(self._on_duration_changed)

    def load_file(self, file_path: str) -> bool:
        """Lädt eine Audio-Datei"""
        success = self.player.load_file(file_path)
        if success:
            filename = Path(file_path).name
            self.file_label.setText(f"Geladen: {filename}")
            self.play_button.setEnabled(True)
            self.stop_button.setEnabled(True)
        else:
            self.file_label.setText("Fehler beim Laden der Datei")
            self.play_button.setEnabled(False)
            self.stop_button.setEnabled(False)
        return success

    def _on_play_clicked(self):
        """Play-Button wurde geklickt"""
        self.player.play()

    def _on_pause_clicked(self):
        """Pause-Button wurde geklickt"""
        self.player.pause()

    def _on_stop_clicked(self):
        """Stop-Button wurde geklickt"""
        self.player.stop()

    def _on_playback_started(self):
        """Wiedergabe wurde gestartet"""
        self.play_button.setEnabled(False)
        self.pause_button.setEnabled(True)
        self.stop_button.setEnabled(True)

    def _on_playback_paused(self):
        """Wiedergabe wurde pausiert"""
        self.play_button.setEnabled(True)
        self.pause_button.setEnabled(False)

    def _on_playback_stopped(self):
        """Wiedergabe wurde gestoppt"""
        self.play_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(True)

    def _on_playback_finished(self):
        """Wiedergabe ist zu Ende"""
        self.play_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(True)

    def _on_position_changed(self, position: float):
        """Position hat sich geändert"""
        if not self.is_seeking:
            # Slider aktualisieren
            duration = self.player.get_duration()
            if duration > 0:
                slider_pos = int((position / duration) * 1000)
                self.progress_slider.setValue(slider_pos)

        # Zeit-Label aktualisieren
        self.current_time_label.setText(self._format_time(position))

    def _on_duration_changed(self, duration: float):
        """Dauer hat sich geändert"""
        self.total_time_label.setText(self._format_time(duration))

    def _on_slider_pressed(self):
        """Slider wurde gedrückt"""
        self.is_seeking = True

    def _on_slider_released(self):
        """Slider wurde losgelassen"""
        self.is_seeking = False
        # Zu neuer Position springen
        duration = self.player.get_duration()
        if duration > 0:
            position = (self.progress_slider.value() / 1000.0) * duration
            self.player.seek(position)

    def _on_slider_moved(self, value: int):
        """Slider wurde bewegt"""
        if self.is_seeking:
            duration = self.player.get_duration()
            if duration > 0:
                position = (value / 1000.0) * duration
                self.current_time_label.setText(self._format_time(position))

    def _format_time(self, seconds: float) -> str:
        """Formatiert Sekunden zu MM:SS"""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"

    def clear(self):
        """Löscht den Player-Zustand"""
        self.player.stop()
        self.file_label.setText("Keine Datei geladen")
        self.current_time_label.setText("00:00")
        self.total_time_label.setText("00:00")
        self.progress_slider.setValue(0)
        self.play_button.setEnabled(False)
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)
