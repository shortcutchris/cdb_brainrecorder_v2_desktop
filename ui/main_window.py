"""
Hauptfenster der Audio Sessions App
"""
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QPushButton, QLabel, QComboBox, QLineEdit,
                               QProgressBar, QSplitter, QGroupBox, QMessageBox,
                               QFileDialog, QToolBar, QSizePolicy, QScrollArea,
                               QFrame, QStackedWidget)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QEvent, QCoreApplication
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
from simple_translator import SimpleTranslator
from translatable_widget import TranslatableWidget
from services.workers import TranscriptionWorker


class MainWindow(TranslatableWidget, QMainWindow):
    """Hauptfenster der Anwendung"""

    def __init__(self):
        super().__init__()
        self.recorder = AudioRecorder()
        self.repo = SessionRepository()
        self.settings_manager = SettingsManager()
        self.transcription_worker = None
        self.current_transcribing_session_id = None

        # Translation Setup mit SimpleTranslator
        self.translator = SimpleTranslator()
        SimpleTranslator.set_instance(self.translator)
        self._load_language()

        self._setup_ui()
        self._connect_signals()
        self._load_sessions()

    def _setup_ui(self):
        """Initialisiert die Benutzeroberfläche"""
        self.setWindowTitle(self.tr("Corporate Digital Brain Desktop Recorder"))
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
                spacing: 12px;
                padding: 12px 16px;
            }
            QToolBar QLabel {
                color: #e0e0e0;
                font-size: 13px;
                padding: 0px 8px;
            }
        """)

        # Suchfeld
        self.search_label = QLabel(self.tr("Suche:"))
        toolbar.addWidget(self.search_label)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(self.tr("Suche nach Titel oder Notizen..."))
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
        self.export_button = QPushButton(self.tr("CSV Export"))
        self.export_button.setStyleSheet("""
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
        self.export_button.clicked.connect(self._on_export_csv)
        toolbar.addWidget(self.export_button)

        # Settings-Button
        toolbar.addSeparator()

        self.toolbar_settings_button = QPushButton("⚙️")
        self.toolbar_settings_button.setToolTip(self.tr("Einstellungen"))
        self.toolbar_settings_button.setStyleSheet("""
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
        self.toolbar_settings_button.clicked.connect(self._on_settings_clicked)
        toolbar.addWidget(self.toolbar_settings_button)

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
        self.recorder_group = QGroupBox(self.tr("Audio Recorder"))
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Geräteauswahl
        device_layout = QHBoxLayout()
        self.mic_label = QLabel(self.tr("Mikrofon:"))
        device_layout.addWidget(self.mic_label)
        self.device_combo = QComboBox()
        self._load_devices()
        device_layout.addWidget(self.device_combo)
        layout.addLayout(device_layout)

        # Level-Anzeige
        level_layout = QHBoxLayout()
        self.level_label = QLabel(self.tr("Pegel:"))
        level_layout.addWidget(self.level_label)
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
        self.record_button = QPushButton(self.tr("Aufnahme starten"))
        self.record_button.clicked.connect(self._on_record_clicked)
        self.record_button.setStyleSheet(
            "padding: 10px; font-size: 14px; background-color: #d32f2f; color: white; font-weight: bold;"
        )
        button_layout.addWidget(self.record_button)
        layout.addLayout(button_layout)

        self.recorder_group.setLayout(layout)
        container_layout.addWidget(self.recorder_group)

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
        self.ai_view.transcription_completed.connect(self._on_transcription_status_update)

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
                self.record_button.setText(self.tr("Aufnahme stoppen"))
                self.record_button.setStyleSheet(
                    "padding: 10px; font-size: 14px; background-color: #ff4444; color: white; font-weight: bold;"
                )
                # Waveform-Visualisierung starten
                self.waveform_widget.start_recording()
            except Exception as e:
                QMessageBox.critical(self, self.tr("Fehler"),
                                   self.tr("Aufnahme konnte nicht gestartet werden:\n{0}").format(e))
        else:
            # Aufnahme stoppen
            output_path = self.recorder.stop_recording()
            self.record_button.setText(self.tr("Aufnahme starten"))
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

        QMessageBox.information(self, self.tr("Erfolg"),
                               self.tr("Session wurde erfolgreich gespeichert!\n{0}").format(output_path))

        # Prüfe ob Auto-Transkription aktiviert ist
        if self.settings_manager.get_auto_transcription():
            self._start_background_transcription(session_id, output_path)

    def _start_background_transcription(self, session_id: int, audio_path: str):
        """Startet die Hintergrund-Transkription einer Session"""
        # Prüfe ob API Key vorhanden
        api_key = self.settings_manager.get_openai_api_key()
        if not api_key:
            print("Warnung: Kein OpenAI API Key gesetzt - Transkription übersprungen")
            return

        # Prüfe ob Audio-Datei existiert
        if not Path(audio_path).exists():
            print(f"Warnung: Audio-Datei nicht gefunden: {audio_path}")
            return

        # Status in DB auf "pending" setzen
        self.repo.set_transcription_status(session_id, "pending")
        self.session_table.update_transcription_status(session_id, "pending", blink=False)

        # Worker starten
        self.current_transcribing_session_id = session_id
        language = self.settings_manager.get_transcription_language()

        self.transcription_worker = TranscriptionWorker(
            audio_path,
            api_key,
            language
        )
        self.transcription_worker.progress.connect(self._on_bg_transcription_progress)
        self.transcription_worker.finished.connect(self._on_bg_transcription_finished)
        self.transcription_worker.error.connect(self._on_bg_transcription_error)
        self.transcription_worker.start()

        print(f"Hintergrund-Transkription gestartet für Session {session_id}")

    def _on_bg_transcription_progress(self, message: str):
        """Progress-Update von Hintergrund-Transkription"""
        # Optional: Status-Bar Message anzeigen
        print(f"Transkription: {message}")

    def _on_bg_transcription_finished(self, result: dict):
        """Hintergrund-Transkription abgeschlossen"""
        if not self.current_transcribing_session_id:
            return

        session_id = self.current_transcribing_session_id

        # In Datenbank speichern
        self.repo.update_transcript(
            session_id,
            result['text'],
            result['tokens_used'],
            "completed"
        )

        # Tabelle aktualisieren (mit Blink-Effekt)
        self.session_table.update_transcription_status(session_id, "completed", blink=True)

        print(f"Transkription abgeschlossen für Session {session_id} ({result['tokens_used']} tokens)")

        # Worker aufräumen
        self.transcription_worker = None
        self.current_transcribing_session_id = None

    def _on_bg_transcription_error(self, error_message: str):
        """Hintergrund-Transkription fehlgeschlagen"""
        if not self.current_transcribing_session_id:
            return

        session_id = self.current_transcribing_session_id

        # Status in DB setzen
        self.repo.set_transcription_status(session_id, "error")
        self.session_table.update_transcription_status(session_id, "error", blink=False)

        print(f"Transkription fehlgeschlagen für Session {session_id}: {error_message}")

        # Worker aufräumen
        self.transcription_worker = None
        self.current_transcribing_session_id = None

    def _on_transcription_status_update(self, session_id: int, status: str):
        """Wird aufgerufen wenn AIView eine Transkription abgeschlossen hat"""
        # Tabelle aktualisieren (mit Blink-Effekt bei Erfolg)
        blink = (status == "completed")
        self.session_table.update_transcription_status(session_id, status, blink=blink)

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
        QMessageBox.information(self, self.tr("Erfolg"), self.tr("Session wurde aktualisiert!"))

    def _on_player_delete_requested(self, session_id: int):
        """Wird aufgerufen wenn im Player der Löschen-Button geklickt wird"""
        reply = QMessageBox.question(
            self, self.tr("Löschen bestätigen"),
            self.tr("Möchten Sie diese Session wirklich löschen?\nDie Audiodatei bleibt erhalten."),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.repo.delete(session_id)
            self.session_form.clear()
            self.player_widget.clear()
            self._load_sessions(self.search_edit.text())
            QMessageBox.information(self, self.tr("Erfolg"), self.tr("Session wurde gelöscht."))

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
            QMessageBox.warning(self, self.tr("Warnung"),
                               self.tr("Datei nicht gefunden:\n{0}").format(file_path))

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
            self, self.tr("CSV exportieren"), "sessions.csv", self.tr("CSV Dateien (*.csv)")
        )

        if file_path:
            try:
                self.repo.export_to_csv(file_path)
                QMessageBox.information(self, self.tr("Erfolg"),
                                       self.tr("Sessions wurden exportiert:\n{0}").format(file_path))
            except Exception as e:
                QMessageBox.critical(self, self.tr("Fehler"),
                                   self.tr("Export fehlgeschlagen:\n{0}").format(e))

    def _on_settings_clicked(self):
        """Öffnet den Settings-Dialog"""
        from PySide6.QtWidgets import QDialog

        # Merke aktuelle Sprache
        old_language = self.settings_manager.get_language()

        dialog = SettingsDialog(self.settings_manager, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Prüfe ob Sprache geändert wurde
            new_language = self.settings_manager.get_language()

            if old_language != new_language:
                # Sprache hat sich geändert - Live-Update
                self.change_language(new_language)

    def retranslateUi(self):
        """Aktualisiert alle UI-Texte (für Sprachwechsel)"""
        # Fenstertitel
        self.setWindowTitle(self.tr("Corporate Digital Brain Desktop Recorder"))

        # Toolbar
        self.search_label.setText(self.tr("Suche:"))
        self.search_edit.setPlaceholderText(self.tr("Suche nach Titel oder Notizen..."))
        self.export_button.setText(self.tr("CSV Export"))
        self.toolbar_settings_button.setToolTip(self.tr("Einstellungen"))

        # Recorder Panel
        self.recorder_group.setTitle(self.tr("Audio Recorder"))
        self.mic_label.setText(self.tr("Mikrofon:"))
        self.level_label.setText(self.tr("Pegel:"))

        # Record-Button Text abhängig vom Zustand
        if not self.recorder.is_recording:
            self.record_button.setText(self.tr("Aufnahme starten"))
        else:
            self.record_button.setText(self.tr("Aufnahme stoppen"))

        # Trigger retranslate in child widgets
        self.session_table.retranslateUi()
        self.player_widget.retranslateUi()
        self.session_form.retranslateUi()
        self.ai_view.retranslateUi()

    def changeEvent(self, event):
        """Behandelt Änderungs-Events (z.B. Sprachwechsel)"""
        if event.type() == QEvent.Type.LanguageChange:
            self.retranslateUi()
        super().changeEvent(event)

    def _load_language(self):
        """Lädt die Sprache aus den Settings und installiert den Translator"""
        language = self.settings_manager.get_language()

        # Map language name to file
        language_map = {
            "Deutsch": "de_DE",
            "English": "en_US",
            "German": "de_DE"  # Fallback für englische UI
        }

        lang_code = language_map.get(language, "de_DE")

        # Pfad zur Translation-Datei
        trans_dir = Path(__file__).parent.parent / "translations"
        ts_file = trans_dir / f"{lang_code}.ts"

        # Lade .ts Datei mit SimpleTranslator
        if ts_file.exists():
            self.translator.load(str(ts_file))
        else:
            print(f"Warnung: Translation-Datei nicht gefunden: {ts_file}")

    def change_language(self, language: str):
        """Wechselt die Sprache der Anwendung zur Laufzeit"""
        # Speichere neue Sprache
        self.settings_manager.set_language(language)

        # Lade neue Übersetzung
        self._load_language()

        # Trigger UI-Update in allen Widgets
        # QEvent.LanguageChange wird automatisch an alle Widgets gesendet
        event = QEvent(QEvent.Type.LanguageChange)
        QCoreApplication.instance().sendEvent(self, event)
