"""
Hauptfenster der Audio Sessions App
"""
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QPushButton, QLabel, QComboBox, QLineEdit,
                               QProgressBar, QSplitter, QGroupBox, QMessageBox,
                               QFileDialog, QToolBar, QSizePolicy, QScrollArea,
                               QFrame, QStackedWidget)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QAction
import sys
import os
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent))

from recorder import AudioRecorder
from data.repo import SessionRepository
from ui.table_widget import SessionTableWidget
from ui.session_form import SessionFormWidget
from ui.player_widget import PlayerWidget
from ui.waveform_widget import WaveformWidget
from ui.ai_view import AIView
from ui.settings_dialog import SettingsDialog
from settings import SettingsManager


class MainWindow(QMainWindow):
    """Hauptfenster der Anwendung"""

    def __init__(self):
        super().__init__()
        self.recorder = AudioRecorder()
        self.repo = SessionRepository()
        self.settings_manager = SettingsManager()

        self._setup_ui()
        self._connect_signals()
        self._load_sessions()

    def _setup_ui(self):
        """Initialisiert die Benutzeroberfläche"""
        self.setWindowTitle("Audio Sessions - Desktop App")
        self.setMinimumSize(1050, 720)  # Angepasst für kompakteres Layout

        # StackedWidget für View-Wechsel (Haupt-View <-> AI-View)
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        # ===== Index 0: Haupt-View =====
        self.main_view = QWidget()
        main_layout = QVBoxLayout(self.main_view)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Toolbar als Widget zum Layout hinzufügen
        toolbar = self._create_toolbar()
        main_layout.addWidget(toolbar)

        # Splitter für Sessions-Tabelle (links) und rechte Seite
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Sessions-Tabelle (links)
        self.session_table = SessionTableWidget()
        splitter.addWidget(self.session_table)

        # Rechte Seite: Recorder + Player + Formular (in ScrollArea für konstante Abstände)
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setFrameShape(QFrame.Shape.NoFrame)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(12, 12, 12, 12)
        right_layout.setSpacing(16)

        # Recorder Panel
        recorder_group = self._create_recorder_panel()
        recorder_group.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        recorder_group.setMinimumHeight(350)
        right_layout.addWidget(recorder_group)

        # Player Widget
        self.player_widget = PlayerWidget()
        self.player_widget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.player_widget.setMinimumHeight(180)
        right_layout.addWidget(self.player_widget)

        # Session Form
        self.session_form = SessionFormWidget()
        self.session_form.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.session_form.setMinimumHeight(250)  # Reduziert dank kompakterem Layout
        right_layout.addWidget(self.session_form)

        # Stretch am Ende - verhindert dass Widgets zusammengeschoben werden
        right_layout.addStretch()

        right_scroll.setWidget(right_widget)
        splitter.addWidget(right_scroll)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)

        main_layout.addWidget(splitter)

        # ===== Index 1: AI-View =====
        self.ai_view = AIView()

        # Views zum StackedWidget hinzufügen
        self.stacked_widget.addWidget(self.main_view)  # Index 0
        self.stacked_widget.addWidget(self.ai_view)    # Index 1

    def _create_toolbar(self) -> QToolBar:
        """Erstellt die Toolbar"""
        toolbar = QToolBar()
        toolbar.setMovable(False)

        # Dark Theme Styling
        toolbar.setStyleSheet("""
            QToolBar {
                background-color: #2b2b2b;
                border-bottom: 1px solid #4a4a4a;
                spacing: 10px;
                padding: 8px;
            }
            QToolBar QLabel {
                color: #e0e0e0;
                font-size: 13px;
                padding: 0px 8px;
            }
        """)

        # Suchfeld
        search_label = QLabel("Suche:")
        toolbar.addWidget(search_label)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Suche nach Titel oder Notizen...")
        self.search_edit.setMinimumWidth(350)
        self.search_edit.setStyleSheet("""
            QLineEdit {
                background-color: #3a3a3a;
                color: #e0e0e0;
                border: 1px solid #4a4a4a;
                border-radius: 3px;
                padding: 6px;
                font-size: 13px;
            }
        """)
        self.search_edit.textChanged.connect(self._on_search)
        toolbar.addWidget(self.search_edit)

        # Separator
        toolbar.addSeparator()

        # CSV Export Button
        export_button = QPushButton("CSV Export")
        export_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #e0e0e0;
                border: 1px solid #4a4a4a;
                border-radius: 4px;
                padding: 6px 16px;
                font-size: 13px;
            }
            QPushButton:hover {
                border: 1px solid #5a5a5a;
                background-color: #3a3a3a;
            }
        """)
        export_button.clicked.connect(self._on_export_csv)
        toolbar.addWidget(export_button)

        # Settings-Button
        toolbar.addSeparator()

        settings_button = QPushButton("⚙️")
        settings_button.setToolTip("Einstellungen")
        settings_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #e0e0e0;
                border: 1px solid #4a4a4a;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 16px;
            }
            QPushButton:hover {
                border: 1px solid #5a5a5a;
                background-color: #3a3a3a;
            }
        """)
        settings_button.clicked.connect(self._on_settings_clicked)
        toolbar.addWidget(settings_button)

        # Spacer rechts
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)

        return toolbar

    def _create_recorder_panel(self) -> QWidget:
        """Erstellt das Recorder-Panel"""
        # Container Widget erstellen (konsistent mit PlayerWidget und SessionFormWidget)
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)

        # GroupBox erstellen
        group = QGroupBox("Audio Recorder")
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Geräteauswahl
        device_layout = QHBoxLayout()
        device_layout.addWidget(QLabel("Mikrofon:"))
        self.device_combo = QComboBox()
        self._load_devices()
        device_layout.addWidget(self.device_combo)
        layout.addLayout(device_layout)

        # Level-Anzeige
        level_layout = QHBoxLayout()
        level_layout.addWidget(QLabel("Pegel:"))
        self.level_bar = QProgressBar()
        self.level_bar.setMaximum(100)
        self.level_bar.setValue(0)
        level_layout.addWidget(self.level_bar)
        layout.addLayout(level_layout)

        # Waveform-Visualisierung
        self.waveform_widget = WaveformWidget()
        layout.addWidget(self.waveform_widget)

        # Laufzeit
        self.duration_label = QLabel("00:00:00")
        self.duration_label.setStyleSheet("font-size: 24px; font-weight: bold;")
        self.duration_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.duration_label)

        # Buttons
        button_layout = QHBoxLayout()
        self.record_button = QPushButton("Aufnahme starten")
        self.record_button.clicked.connect(self._on_record_clicked)
        self.record_button.setStyleSheet(
            "padding: 10px; font-size: 14px; background-color: #d32f2f; color: white; font-weight: bold;"
        )
        button_layout.addWidget(self.record_button)
        layout.addLayout(button_layout)

        group.setLayout(layout)
        container_layout.addWidget(group)

        return container

    def _load_devices(self):
        """Lädt verfügbare Audiogeräte"""
        devices = self.recorder.get_devices()
        self.device_combo.clear()

        for device in devices:
            self.device_combo.addItem(device['name'], device['index'])

    def _connect_signals(self):
        """Verbindet Signale"""
        # Recorder Signals (Thread-sicher)
        self.recorder.level_updated.connect(self._on_level_update)
        self.recorder.duration_updated.connect(self._on_duration_update)
        self.recorder.waveform_updated.connect(self._on_waveform_update)

        # Table Selection
        self.session_table.session_selected.connect(self._on_session_selected)

        # Form Save
        self.session_form.save_requested.connect(self._on_save_session)

        # Player Signals
        self.player_widget.delete_requested.connect(self._on_player_delete_requested)
        self.player_widget.show_in_folder_requested.connect(self._on_show_in_folder)
        self.player_widget.ai_dialog_requested.connect(self._on_ai_view_requested)

        # AI View Signals
        self.ai_view.back_requested.connect(self._on_ai_back)
        self.ai_view.settings_requested.connect(self._on_settings_clicked)

    def _load_sessions(self, search_term: str = ''):
        """Lädt Sessions aus der Datenbank"""
        sessions = self.repo.get_all(search_term)
        self.session_table.load_sessions(sessions)

    def _on_search(self, text: str):
        """Wird aufgerufen wenn im Suchfeld getippt wird"""
        self._load_sessions(text)

    def _on_record_clicked(self):
        """Wird aufgerufen wenn der Record-Button geklickt wird"""
        if not self.recorder.is_recording:
            # Aufnahme starten
            device_index = self.device_combo.currentData()
            try:
                output_path = self.recorder.start_recording(device_index)
                self.record_button.setText("Aufnahme stoppen")
                self.record_button.setStyleSheet(
                    "padding: 10px; font-size: 14px; background-color: #ff4444; color: white; font-weight: bold;"
                )
                # Waveform-Visualisierung starten
                self.waveform_widget.start_recording()
            except Exception as e:
                QMessageBox.critical(self, "Fehler", f"Aufnahme konnte nicht gestartet werden:\n{e}")
        else:
            # Aufnahme stoppen
            output_path = self.recorder.stop_recording()
            self.record_button.setText("Aufnahme starten")
            self.record_button.setStyleSheet(
                "padding: 10px; font-size: 14px; background-color: #d32f2f; color: white; font-weight: bold;"
            )

            # Waveform-Visualisierung stoppen
            self.waveform_widget.stop_recording()

            # Session in DB speichern
            if output_path:
                self._save_recorded_session(output_path)

            # UI zurücksetzen
            self.level_bar.setValue(0)
            self.duration_label.setText("00:00:00")

    def _save_recorded_session(self, output_path: str):
        """Speichert eine aufgenommene Session in der Datenbank"""
        timestamp = datetime.now().isoformat()
        duration = self.recorder.get_duration_seconds()
        title = f"Session {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        session_id = self.repo.create(
            title=title,
            recorded_at=timestamp,
            path=output_path,
            duration_sec=duration,
            samplerate=self.recorder.samplerate,
            channels=self.recorder.channels,
            notes=''
        )

        # Tabelle aktualisieren
        self._load_sessions()

        QMessageBox.information(self, "Erfolg",
                               f"Session wurde erfolgreich gespeichert!\n{output_path}")

    def _on_level_update(self, level: float):
        """Aktualisiert die Pegelanzeige"""
        # RMS in Prozent umrechnen (grober Richtwert)
        percent = min(int(level * 200), 100)
        self.level_bar.setValue(percent)

    def _on_duration_update(self, duration: float):
        """Aktualisiert die Laufzeit-Anzeige"""
        hours = int(duration // 3600)
        minutes = int((duration % 3600) // 60)
        seconds = int(duration % 60)
        self.duration_label.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")

    def _on_waveform_update(self, audio_data):
        """Aktualisiert die Waveform-Visualisierung"""
        self.waveform_widget.update_waveform(audio_data)

    def _on_session_selected(self, session_id: int):
        """Wird aufgerufen wenn eine Session in der Tabelle ausgewählt wird"""
        session = self.repo.get_by_id(session_id)
        if session:
            self.session_form.load_session(session)
            # Audio-Datei in Player laden
            if session['path'] and os.path.exists(session['path']):
                self.player_widget.load_file(session['path'], session_id)

    def _on_save_session(self, data: dict):
        """Wird aufgerufen wenn eine Session gespeichert werden soll"""
        session_id = data.pop('id')
        self.repo.update(session_id, **data)
        self._load_sessions(self.search_edit.text())
        QMessageBox.information(self, "Erfolg", "Session wurde aktualisiert!")

    def _on_player_delete_requested(self, session_id: int):
        """Wird aufgerufen wenn im Player der Löschen-Button geklickt wird"""
        reply = QMessageBox.question(
            self, "Löschen bestätigen",
            "Möchten Sie diese Session wirklich löschen?\nDie Audiodatei bleibt erhalten.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.repo.delete(session_id)
            self.session_form.clear()
            self.player_widget.clear()
            self._load_sessions(self.search_edit.text())
            QMessageBox.information(self, "Erfolg", "Session wurde gelöscht.")

    def _on_show_in_folder(self, file_path: str):
        """Zeigt die Datei im Explorer/Finder"""
        if os.path.exists(file_path):
            # Plattformunabhängig die Datei im Ordner anzeigen
            if sys.platform == 'darwin':  # macOS
                os.system(f'open -R "{file_path}"')
            elif sys.platform == 'win32':  # Windows
                os.system(f'explorer /select,"{file_path}"')
            else:  # Linux
                # Fallback: Ordner öffnen
                folder_path = os.path.dirname(file_path)
                os.system(f'xdg-open "{folder_path}"')
        else:
            QMessageBox.warning(self, "Warnung",
                               f"Datei nicht gefunden:\n{file_path}")

    def _on_ai_view_requested(self, session_id: int):
        """Wechselt zum AI-View für die ausgewählte Session"""
        # Session in AI-View laden
        self.ai_view.load_session(session_id)

        # Fade-Animation beim Wechsel
        self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(150)  # 150ms
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.95)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.fade_animation.finished.connect(lambda: self._complete_switch_to_ai())
        self.fade_animation.start()

    def _complete_switch_to_ai(self):
        """Komplettiert den Wechsel zum AI-View"""
        self.stacked_widget.setCurrentIndex(1)  # AI-View

        # Fade back in
        fade_in = QPropertyAnimation(self, b"windowOpacity")
        fade_in.setDuration(150)
        fade_in.setStartValue(0.95)
        fade_in.setEndValue(1.0)
        fade_in.setEasingCurve(QEasingCurve.Type.InOutQuad)
        fade_in.start()

    def _on_ai_back(self):
        """Kehrt vom AI-View zur Hauptansicht zurück"""
        # Fade-Animation beim Wechsel zurück
        self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(150)
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.95)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.fade_animation.finished.connect(lambda: self._complete_switch_to_main())
        self.fade_animation.start()

    def _complete_switch_to_main(self):
        """Komplettiert den Wechsel zur Hauptansicht"""
        self.stacked_widget.setCurrentIndex(0)  # Haupt-View

        # Fade back in
        fade_in = QPropertyAnimation(self, b"windowOpacity")
        fade_in.setDuration(150)
        fade_in.setStartValue(0.95)
        fade_in.setEndValue(1.0)
        fade_in.setEasingCurve(QEasingCurve.Type.InOutQuad)
        fade_in.start()

    def _on_export_csv(self):
        """Exportiert Sessions als CSV"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "CSV exportieren", "sessions.csv", "CSV Dateien (*.csv)"
        )

        if file_path:
            try:
                self.repo.export_to_csv(file_path)
                QMessageBox.information(self, "Erfolg",
                                       f"Sessions wurden exportiert:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Fehler", f"Export fehlgeschlagen:\n{e}")

    def _on_settings_clicked(self):
        """Öffnet den Settings-Dialog"""
        from PySide6.QtWidgets import QDialog
        dialog = SettingsDialog(self.settings_manager, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Settings wurden gespeichert
            pass
