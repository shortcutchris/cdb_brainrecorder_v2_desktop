"""
Hauptfenster der Audio Sessions App
"""
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QPushButton, QLabel, QComboBox, QLineEdit,
                               QProgressBar, QSplitter, QGroupBox, QMessageBox,
                               QFileDialog, QToolBar, QSizePolicy, QSpacerItem)
from PySide6.QtCore import Qt, QTimer
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


class MainWindow(QMainWindow):
    """Hauptfenster der Anwendung"""

    def __init__(self):
        super().__init__()
        self.recorder = AudioRecorder()
        self.repo = SessionRepository()

        self._setup_ui()
        self._connect_signals()
        self._load_sessions()

    def _setup_ui(self):
        """Initialisiert die Benutzeroberfläche"""
        self.setWindowTitle("Audio Sessions - Desktop App")
        self.setMinimumSize(1200, 900)  # Angepasst für kompakteres Layout

        # Zentrales Widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Toolbar
        self._create_toolbar()

        # Splitter für Sessions-Tabelle (links) und rechte Seite
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Sessions-Tabelle (links)
        self.session_table = SessionTableWidget()
        splitter.addWidget(self.session_table)

        # Rechte Seite: Recorder + Player + Formular
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        # Recorder Panel
        recorder_group = self._create_recorder_panel()
        recorder_group.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        recorder_group.setMinimumHeight(350)
        right_layout.addWidget(recorder_group)
        # Fester Spacer mit Fixed Policy - verhindert Komprimierung
        right_layout.addSpacerItem(QSpacerItem(0, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))

        # Player Widget
        self.player_widget = PlayerWidget()
        self.player_widget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.player_widget.setMinimumHeight(180)
        right_layout.addWidget(self.player_widget)
        # Fester Spacer mit Fixed Policy - verhindert Komprimierung
        right_layout.addSpacerItem(QSpacerItem(0, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))

        # Session Form
        self.session_form = SessionFormWidget()
        self.session_form.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.session_form.setMinimumHeight(250)  # Reduziert dank kompakterem Layout
        right_layout.addWidget(self.session_form)

        # Stretch am Ende - verhindert dass Widgets zusammengeschoben werden
        right_layout.addStretch()

        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)

        main_layout.addWidget(splitter)

    def _create_toolbar(self):
        """Erstellt die Toolbar"""
        toolbar = QToolBar()
        self.addToolBar(toolbar)

        # Suchfeld
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Suche nach Titel oder Notizen...")
        self.search_edit.setMaximumWidth(300)
        self.search_edit.textChanged.connect(self._on_search)
        toolbar.addWidget(QLabel("Suche:"))
        toolbar.addWidget(self.search_edit)

        toolbar.addSeparator()

        # Aktionen
        new_action = QAction("Neu", self)
        new_action.triggered.connect(self._on_new_session)
        toolbar.addAction(new_action)

        delete_action = QAction("Löschen", self)
        delete_action.triggered.connect(self._on_delete_session)
        toolbar.addAction(delete_action)

        toolbar.addSeparator()

        export_action = QAction("CSV Export", self)
        export_action.triggered.connect(self._on_export_csv)
        toolbar.addAction(export_action)

        open_action = QAction("Datei öffnen", self)
        open_action.triggered.connect(self._on_open_file)
        toolbar.addAction(open_action)

    def _create_recorder_panel(self) -> QWidget:
        """Erstellt das Recorder-Panel"""
        # Container Widget erstellen (konsistent mit PlayerWidget und SessionFormWidget)
        container = QWidget()
        container_layout = QVBoxLayout(container)

        # GroupBox erstellen
        group = QGroupBox("Audio Recorder")
        layout = QVBoxLayout()

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
        self.record_button.setStyleSheet("padding: 10px; font-size: 14px;")
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
                    "padding: 10px; font-size: 14px; background-color: #ff4444;"
                )
                # Waveform-Visualisierung starten
                self.waveform_widget.start_recording()
            except Exception as e:
                QMessageBox.critical(self, "Fehler", f"Aufnahme konnte nicht gestartet werden:\n{e}")
        else:
            # Aufnahme stoppen
            output_path = self.recorder.stop_recording()
            self.record_button.setText("Aufnahme starten")
            self.record_button.setStyleSheet("padding: 10px; font-size: 14px;")

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
                self.player_widget.load_file(session['path'])

    def _on_save_session(self, data: dict):
        """Wird aufgerufen wenn eine Session gespeichert werden soll"""
        session_id = data.pop('id')
        self.repo.update(session_id, **data)
        self._load_sessions(self.search_edit.text())
        QMessageBox.information(self, "Erfolg", "Session wurde aktualisiert!")

    def _on_new_session(self):
        """Erstellt eine neue manuelle Session"""
        # Für MVP nicht implementiert - könnte später hinzugefügt werden
        QMessageBox.information(self, "Info",
                               "Neue Sessions werden automatisch durch Aufnahmen erstellt.")

    def _on_delete_session(self):
        """Löscht die ausgewählte Session"""
        session_id = self.session_table.get_selected_session_id()
        if session_id == -1:
            QMessageBox.warning(self, "Warnung", "Bitte wählen Sie eine Session aus.")
            return

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

    def _on_open_file(self):
        """Öffnet die Audio-Datei der ausgewählten Session"""
        session_id = self.session_table.get_selected_session_id()
        if session_id == -1:
            QMessageBox.warning(self, "Warnung", "Bitte wählen Sie eine Session aus.")
            return

        session = self.repo.get_by_id(session_id)
        if session and session['path']:
            path = session['path']
            if os.path.exists(path):
                # Plattformunabhängig die Datei öffnen
                if sys.platform == 'darwin':  # macOS
                    os.system(f'open "{path}"')
                elif sys.platform == 'win32':  # Windows
                    os.startfile(path)
                else:  # Linux
                    os.system(f'xdg-open "{path}"')
            else:
                QMessageBox.warning(self, "Warnung",
                                   f"Datei nicht gefunden:\n{path}")
