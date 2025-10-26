"""
AI-View für Transkription und Textverarbeitung
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QLabel, QComboBox, QTextEdit, QGroupBox,
                               QSplitter, QToolBar, QSizePolicy, QMessageBox)
from PySide6.QtCore import Qt, Signal, QEvent
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from translatable_widget import TranslatableWidget
from data.repo import SessionRepository
from services.workers import TranscriptionWorker, TransformationWorker
from settings import SettingsManager


class AIView(TranslatableWidget, QWidget):
    """View für KI-gestützte Textverarbeitung"""

    # Signale
    back_requested = Signal()  # Wird ausgelöst wenn Zurück geklickt wird
    settings_requested = Signal()  # Wird ausgelöst wenn Settings geklickt wird
    transcription_completed = Signal(int, str)  # (session_id, status)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_session_id = None
        self.current_session_path = None
        self.repo = SessionRepository()
        self.settings_manager = SettingsManager()
        self.transcription_worker = None
        self.transformation_worker = None
        self._setup_ui()

    def _setup_ui(self):
        """Initialisiert die Benutzeroberfläche"""
        # Dark Theme für den gesamten View
        self.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
            }
            QGroupBox {
                color: #e0e0e0;
                border: 1px solid #4a4a4a;
                border-radius: 4px;
                margin-top: 0px;
                font-weight: bold;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QTextEdit {
                background-color: #1e1e1e;
                color: #e0e0e0;
                border: 1px solid #4a4a4a;
                border-radius: 2px;
                padding: 8px;
                font-size: 13px;
            }
        """)

        # Hauptlayout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Toolbar oben
        toolbar = self._create_toolbar()
        main_layout.addWidget(toolbar)

        # Splitter für die zwei Bereiche
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Linke Seite: Transkription
        self.left_group = QGroupBox(self.tr("Transkription"))
        left_layout = QVBoxLayout()

        # Transkription starten Button (initially hidden)
        self.transcribe_button = QPushButton(self.tr("Transkription starten"))
        self.transcribe_button.setStyleSheet("""
            QPushButton {
                background-color: #1976d2;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #1565c0;
            }
            QPushButton:disabled {
                background-color: #4a4a4a;
                color: #808080;
            }
        """)
        self.transcribe_button.clicked.connect(self._on_transcribe_clicked)
        self.transcribe_button.hide()  # Initially hidden
        left_layout.addWidget(self.transcribe_button)

        self.transcription_edit = QTextEdit()
        self.transcription_edit.setPlaceholderText(self.tr("Transkription wird hier erscheinen..."))

        left_layout.addWidget(self.transcription_edit)
        self.left_group.setLayout(left_layout)
        splitter.addWidget(self.left_group)

        # Rechte Seite: Transformierter Text
        self.right_group = QGroupBox(self.tr("Transformierter Text"))
        right_layout = QVBoxLayout()

        self.transformed_edit = QTextEdit()
        self.transformed_edit.setPlaceholderText(self.tr("Hier erscheint der transformierte Text..."))
        # Dummy-Daten
        self.transformed_edit.setPlainText(
            self.tr("Hier erscheint der transformierte Text nach dem Klick auf 'Generieren'.\n\n"
            "Je nach gewähltem Prompt wird der Text:\n"
            "- Zusammengefasst\n"
            "- Übersetzt\n"
            "- Oder anderweitig transformiert\n\n"
            "Auch dieser Text ist editierbar.")
        )

        right_layout.addWidget(self.transformed_edit)
        self.right_group.setLayout(right_layout)
        splitter.addWidget(self.right_group)

        # Splitter 50/50
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        main_layout.addWidget(splitter)

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

        # Zurück-Button
        self.back_button = QPushButton(self.tr("← Zurück"))
        self.back_button.setToolTip(self.tr("Zurück zur Hauptansicht"))
        self.back_button.setStyleSheet("""
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
        self.back_button.clicked.connect(self.back_requested.emit)
        toolbar.addWidget(self.back_button)

        # Separator
        toolbar.addSeparator()

        # Prompt-Auswahl
        self.prompt_label = QLabel(self.tr("Prompt:"))
        toolbar.addWidget(self.prompt_label)

        self.prompt_combo = QComboBox()
        self.prompt_combo.addItems([
            self.tr("Zusammenfassen"),
            self.tr("Übersetzen"),
            self.tr("Strukturieren")
        ])
        self.prompt_combo.setMinimumWidth(200)
        self.prompt_combo.setStyleSheet("""
            QComboBox {
                background-color: #3a3a3a;
                color: #e0e0e0;
                border: 1px solid #4a4a4a;
                border-radius: 3px;
                padding: 5px;
                font-size: 13px;
            }
            QComboBox:hover {
                border: 1px solid #5a5a5a;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #3a3a3a;
                color: #e0e0e0;
                selection-background-color: #1976d2;
                border: 1px solid #4a4a4a;
            }
        """)
        toolbar.addWidget(self.prompt_combo)

        # Generieren-Button
        self.generate_button = QPushButton(self.tr("Generieren"))
        self.generate_button.setStyleSheet("""
            QPushButton {
                background-color: #1976d2;
                color: white;
                font-weight: bold;
                padding: 6px 16px;
                border-radius: 4px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #1565c0;
            }
        """)
        self.generate_button.clicked.connect(self._on_generate_clicked)
        toolbar.addWidget(self.generate_button)

        # Settings-Button
        toolbar.addSeparator()

        self.settings_button = QPushButton("⚙️")
        self.settings_button.setToolTip(self.tr("Einstellungen"))
        self.settings_button.setStyleSheet("""
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
        self.settings_button.clicked.connect(self.settings_requested.emit)
        toolbar.addWidget(self.settings_button)

        # Spacer rechts
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)

        return toolbar

    def load_session(self, session_id: int):
        """Lädt eine Session in den AI-View"""
        self.current_session_id = session_id

        # Session aus Datenbank laden
        session = self.repo.get_by_id(session_id)
        if not session:
            return

        self.current_session_path = session['path']

        # Prüfe ob Transkript existiert
        transcript = session.get('transcript_text', None)

        if transcript:
            # Transkript vorhanden: anzeigen
            self.transcription_edit.setPlainText(transcript)
            self.transcribe_button.hide()
        else:
            # Kein Transkript: Button zeigen
            self.transcription_edit.clear()
            self.transcription_edit.setPlaceholderText(
                self.tr("Keine Transkription vorhanden. Klicken Sie auf 'Transkription starten'.")
            )
            self.transcribe_button.show()

        # Rechte Seite leeren
        self.transformed_edit.clear()

    def _on_transcribe_clicked(self):
        """Wird aufgerufen wenn 'Transkription starten' geklickt wird"""
        # Prüfe API Key
        api_key = self.settings_manager.get_openai_api_key()
        if not api_key:
            QMessageBox.warning(
                self,
                self.tr("API Key fehlt"),
                self.tr("Bitte geben Sie zuerst einen OpenAI API Key in den Einstellungen ein.")
            )
            return

        # Prüfe ob Audio-Datei existiert
        if not self.current_session_path or not Path(self.current_session_path).exists():
            QMessageBox.warning(
                self,
                self.tr("Audio-Datei nicht gefunden"),
                self.tr("Die Audio-Datei für diese Session wurde nicht gefunden.")
            )
            return

        # Button deaktivieren
        self.transcribe_button.setEnabled(False)
        self.transcribe_button.setText(self.tr("Transkribiere..."))

        # Worker starten
        language = self.settings_manager.get_transcription_language()
        self.transcription_worker = TranscriptionWorker(
            self.current_session_path,
            api_key,
            language
        )
        self.transcription_worker.progress.connect(self._on_transcription_progress)
        self.transcription_worker.finished.connect(self._on_transcription_finished)
        self.transcription_worker.error.connect(self._on_transcription_error)
        self.transcription_worker.start()

    def _on_transcription_progress(self, message: str):
        """Progress-Update von Transkription"""
        self.transcription_edit.setPlaceholderText(message)

    def _on_transcription_finished(self, result: dict):
        """Transkription abgeschlossen"""
        # Transkript anzeigen
        self.transcription_edit.setPlainText(result['text'])
        self.transcribe_button.hide()

        # In Datenbank speichern
        self.repo.update_transcript(
            self.current_session_id,
            result['text'],
            result['tokens_used'],
            "completed"
        )

        # Signal an MainWindow (für Tabellen-Update)
        self.transcription_completed.emit(self.current_session_id, "completed")

        # Button zurücksetzen
        self.transcribe_button.setEnabled(True)
        self.transcribe_button.setText(self.tr("Transkription starten"))

    def _on_transcription_error(self, error_message: str):
        """Transkription fehlgeschlagen"""
        QMessageBox.critical(
            self,
            self.tr("Transkription fehlgeschlagen"),
            self.tr("Fehler: {0}").format(error_message)
        )

        # Status in DB setzen
        self.repo.set_transcription_status(self.current_session_id, "error")
        self.transcription_completed.emit(self.current_session_id, "error")

        # Button zurücksetzen
        self.transcribe_button.setEnabled(True)
        self.transcribe_button.setText(self.tr("Transkription starten"))

    def _on_generate_clicked(self):
        """Wird aufgerufen wenn Generieren geklickt wird"""
        # Prüfe ob Transkript vorhanden
        if not self.transcription_edit.toPlainText():
            QMessageBox.warning(
                self,
                self.tr("Keine Transkription"),
                self.tr("Bitte transkribieren Sie zuerst die Audio-Datei.")
            )
            return

        # Prüfe API Key
        api_key = self.settings_manager.get_openai_api_key()
        if not api_key:
            QMessageBox.warning(
                self,
                self.tr("API Key fehlt"),
                self.tr("Bitte geben Sie zuerst einen OpenAI API Key in den Einstellungen ein.")
            )
            return

        # Button deaktivieren
        self.generate_button.setEnabled(False)
        self.generate_button.setText(self.tr("Generiere..."))

        # Task aus Dropdown ermitteln
        prompt_text = self.prompt_combo.currentText()
        task_map = {
            self.tr("Zusammenfassen"): "zusammenfassen",
            self.tr("Übersetzen"): "uebersetzen",
            self.tr("Strukturieren"): "strukturieren"
        }
        task = task_map.get(prompt_text, "zusammenfassen")

        # Worker starten
        text = self.transcription_edit.toPlainText()
        self.transformation_worker = TransformationWorker(
            text=text,
            task=task,
            api_key=api_key,
            reasoning="medium",
            verbosity="low"
        )
        self.transformation_worker.progress.connect(self._on_transformation_progress)
        self.transformation_worker.finished.connect(self._on_transformation_finished)
        self.transformation_worker.error.connect(self._on_transformation_error)
        self.transformation_worker.start()

    def _on_transformation_progress(self, message: str):
        """Progress-Update von Transformation"""
        self.transformed_edit.setPlaceholderText(message)

    def _on_transformation_finished(self, result: dict):
        """Transformation abgeschlossen"""
        self.transformed_edit.setPlainText(result['result'])

        # Button zurücksetzen
        self.generate_button.setEnabled(True)
        self.generate_button.setText(self.tr("Generieren"))

    def _on_transformation_error(self, error_message: str):
        """Transformation fehlgeschlagen"""
        QMessageBox.critical(
            self,
            self.tr("Transformation fehlgeschlagen"),
            self.tr("Fehler: {0}").format(error_message)
        )

        # Button zurücksetzen
        self.generate_button.setEnabled(True)
        self.generate_button.setText(self.tr("Generieren"))

    def retranslateUi(self):
        """Aktualisiert alle UI-Texte (für Sprachwechsel)"""
        # GroupBoxes
        self.left_group.setTitle(self.tr("Transkription"))
        self.right_group.setTitle(self.tr("Transformierter Text"))

        # Buttons
        self.transcribe_button.setText(self.tr("Transkription starten"))

        # Placeholders
        self.transcription_edit.setPlaceholderText(self.tr("Transkription wird hier erscheinen..."))
        self.transformed_edit.setPlaceholderText(self.tr("Hier erscheint der transformierte Text..."))

        # Toolbar
        self.back_button.setText(self.tr("← Zurück"))
        self.back_button.setToolTip(self.tr("Zurück zur Hauptansicht"))
        self.prompt_label.setText(self.tr("Prompt:"))

        # Prompt-Combo neu befüllen (Auswahl beibehalten)
        current_prompt = self.prompt_combo.currentText()
        self.prompt_combo.clear()
        self.prompt_combo.addItems([
            self.tr("Zusammenfassen"),
            self.tr("Übersetzen"),
            self.tr("Strukturieren")
        ])
        # Versuchen Auswahl wiederherzustellen (funktioniert nur wenn exakte Übereinstimmung)
        index = self.prompt_combo.findText(current_prompt)
        if index >= 0:
            self.prompt_combo.setCurrentIndex(index)

        self.generate_button.setText(self.tr("Generieren"))
        self.settings_button.setToolTip(self.tr("Einstellungen"))

    def changeEvent(self, event):
        """Behandelt Änderungs-Events (z.B. Sprachwechsel)"""
        if event.type() == QEvent.Type.LanguageChange:
            self.retranslateUi()
        super().changeEvent(event)
