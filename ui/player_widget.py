"""
Playback-Widget für Audio-Wiedergabe
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QLabel, QSlider, QGroupBox)
from PySide6.QtCore import Qt, Signal, QEvent
import qtawesome as qta
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from player import AudioPlayer
from translatable_widget import TranslatableWidget


class PlayerWidget(TranslatableWidget, QWidget):
    """Widget für Audio-Wiedergabe"""

    # Signale
    delete_requested = Signal(int)  # Wird ausgelöst wenn Löschen geklickt wird (session_id)
    show_in_folder_requested = Signal(str)  # Wird ausgelöst wenn Ordner-Button geklickt wird (file_path)
    ai_dialog_requested = Signal(int)  # Wird ausgelöst wenn AI-Button geklickt wird (session_id)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.player = AudioPlayer()
        self.is_seeking = False  # Flag für Slider-Interaktion
        self.current_session_id = None  # Aktuell geladene Session-ID
        self.current_file_path = None  # Aktuell geladener Dateipfad
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """Initialisiert das Widget"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # GroupBox
        self.group = QGroupBox("")
        self.group.setStyleSheet("""
            QGroupBox {
                border: 1px solid #003355;
                background-color: #001633;
                border-radius: 4px;
                margin-top: 0px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 0px;
                padding: 0 0px;
            }
        """)
        group_layout = QVBoxLayout()
        group_layout.setContentsMargins(12, 12, 12, 12)
        group_layout.setSpacing(12)

        # Dateiname-Label
        self.file_label = QLabel(self.tr("Keine Datei geladen"))
        self.file_label.setStyleSheet("font-style: italic; color: #e0e0e0;")
        group_layout.addWidget(self.file_label)

        # Zeit-Anzeige
        time_layout = QHBoxLayout()
        self.current_time_label = QLabel("00:00")
        self.current_time_label.setStyleSheet("color: #e0e0e0;")
        self.total_time_label = QLabel("00:00")
        self.total_time_label.setStyleSheet("color: #e0e0e0;")
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

        # Links: Playback-Buttons
        button_style = """
            QPushButton {
                background-color: #ffaa3a;
                color: #000e22;
                font-weight: bold;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #ff9922;
            }
            QPushButton:disabled {
                background-color: #001b36;
                color: #5a7791;
            }
        """

        self.play_button = QPushButton(self.tr("Play"))
        self.play_button.setStyleSheet(button_style)
        self.play_button.clicked.connect(self._on_play_clicked)
        self.play_button.setEnabled(False)

        self.pause_button = QPushButton(self.tr("Pause"))
        self.pause_button.setStyleSheet(button_style)
        self.pause_button.clicked.connect(self._on_pause_clicked)
        self.pause_button.setEnabled(False)

        self.stop_button = QPushButton(self.tr("Stop"))
        self.stop_button.setStyleSheet(button_style)
        self.stop_button.clicked.connect(self._on_stop_clicked)
        self.stop_button.setEnabled(False)

        button_layout.addWidget(self.play_button)
        button_layout.addWidget(self.pause_button)
        button_layout.addWidget(self.stop_button)
        button_layout.addStretch()

        # Rechts: Ordner, AI und Löschen-Buttons
        icon_button_style = """
            QPushButton {
                background-color: #ffaa3a;
                color: #000e22;
                font-weight: bold;
                border-radius: 4px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #ff9922;
            }
            QPushButton:disabled {
                background-color: #001b36;
                color: #5a7791;
            }
        """

        self.folder_button = QPushButton()
        self.folder_button.setIcon(qta.icon('fa5s.folder-open', color='#000e22'))
        self.folder_button.setToolTip(self.tr("Im Ordner zeigen"))
        self.folder_button.clicked.connect(self._on_folder_clicked)
        self.folder_button.setEnabled(False)
        self.folder_button.setStyleSheet(icon_button_style)

        self.ai_button = QPushButton()
        self.ai_button.setIcon(qta.icon('fa5s.robot', color='#000e22'))
        self.ai_button.setToolTip(self.tr("KI-Funktionen"))
        self.ai_button.clicked.connect(self._on_ai_clicked)
        self.ai_button.setEnabled(False)
        self.ai_button.setStyleSheet(icon_button_style)

        self.delete_button = QPushButton(self.tr("Löschen"))
        self.delete_button.setToolTip(self.tr("Session löschen"))
        self.delete_button.clicked.connect(self._on_delete_clicked)
        self.delete_button.setEnabled(False)
        self.delete_button.setStyleSheet("""
            QPushButton {
                background-color: #d32f2f;
                color: white;
                font-weight: bold;
                padding: 6px 12px;
                border: 1px solid #b71c1c;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #c62828;
                border: 1px solid #b71c1c;
            }
            QPushButton:disabled {
                background-color: #5a5a5a;
                border-color: #444444;
            }
        """)

        button_layout.addWidget(self.folder_button)
        button_layout.addWidget(self.ai_button)
        button_layout.addWidget(self.delete_button)

        group_layout.addLayout(button_layout)

        self.group.setLayout(group_layout)
        layout.addWidget(self.group)

    def _connect_signals(self):
        """Verbindet Player-Signals"""
        self.player.playback_started.connect(self._on_playback_started)
        self.player.playback_paused.connect(self._on_playback_paused)
        self.player.playback_stopped.connect(self._on_playback_stopped)
        self.player.playback_finished.connect(self._on_playback_finished)
        self.player.position_changed.connect(self._on_position_changed)
        self.player.duration_changed.connect(self._on_duration_changed)

    def set_touch_mode(self, enabled: bool):
        """
        Aktiviert Touch-Modus mit größeren Buttons

        Args:
            enabled: True für Touch-Modus (50px Buttons), False für Normal (40px)
        """
        button_size = 50 if enabled else 40

        # Setze Größe für alle Buttons
        for button in [self.play_button, self.pause_button, self.stop_button,
                      self.folder_button, self.ai_button, self.delete_button]:
            button.setMinimumHeight(button_size)
            button.setMinimumWidth(button_size)

    def load_file(self, file_path: str, session_id: int = None) -> bool:
        """Lädt eine Audio-Datei"""
        success = self.player.load_file(file_path)
        if success:
            self.current_file_path = file_path
            self.current_session_id = session_id
            filename = Path(file_path).name
            self.file_label.setText(self.tr("Geladen: {0}").format(filename))
            self.play_button.setEnabled(True)
            self.stop_button.setEnabled(True)
            self.folder_button.setEnabled(True)
            self.ai_button.setEnabled(True if session_id else False)
            self.delete_button.setEnabled(True if session_id else False)
        else:
            self.file_label.setText(self.tr("Fehler beim Laden der Datei"))
            self.play_button.setEnabled(False)
            self.stop_button.setEnabled(False)
            self.folder_button.setEnabled(False)
            self.ai_button.setEnabled(False)
            self.delete_button.setEnabled(False)
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

    def _on_folder_clicked(self):
        """Ordner-Button wurde geklickt"""
        if self.current_file_path:
            self.show_in_folder_requested.emit(self.current_file_path)

    def _on_delete_clicked(self):
        """Löschen-Button wurde geklickt"""
        if self.current_session_id:
            self.delete_requested.emit(self.current_session_id)

    def _on_ai_clicked(self):
        """AI-Button wurde geklickt"""
        if self.current_session_id:
            self.ai_dialog_requested.emit(self.current_session_id)

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
        self.current_file_path = None
        self.current_session_id = None
        self.file_label.setText(self.tr("Keine Datei geladen"))
        self.current_time_label.setText("00:00")
        self.total_time_label.setText("00:00")
        self.progress_slider.setValue(0)
        self.play_button.setEnabled(False)
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.folder_button.setEnabled(False)
        self.ai_button.setEnabled(False)
        self.delete_button.setEnabled(False)

    def retranslateUi(self):
        """Aktualisiert alle UI-Texte (für Sprachwechsel)"""
        # GroupBox
        self.group.setTitle("")

        # Buttons
        self.play_button.setText(self.tr("Play"))
        self.pause_button.setText(self.tr("Pause"))
        self.stop_button.setText(self.tr("Stop"))
        self.delete_button.setText(self.tr("Löschen"))

        # Tooltips
        self.folder_button.setToolTip(self.tr("Im Ordner zeigen"))
        self.ai_button.setToolTip(self.tr("KI-Funktionen"))
        self.delete_button.setToolTip(self.tr("Session löschen"))

        # File-Label - nur wenn "Keine Datei geladen" (nicht wenn Datei geladen)
        if self.current_file_path is None:
            self.file_label.setText(self.tr("Keine Datei geladen"))
        else:
            # Dateiname anzeigen
            filename = Path(self.current_file_path).name
            self.file_label.setText(self.tr("Geladen: {0}").format(filename))

    def changeEvent(self, event):
        """Behandelt Änderungs-Events (z.B. Sprachwechsel)"""
        if event.type() == QEvent.Type.LanguageChange:
            self.retranslateUi()
        super().changeEvent(event)
