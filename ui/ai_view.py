"""
AI-View für Transkription und Textverarbeitung
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QLabel, QComboBox, QTextEdit, QGroupBox,
                               QSplitter, QToolBar, QSizePolicy)
from PySide6.QtCore import Qt, Signal


class AIView(QWidget):
    """View für KI-gestützte Textverarbeitung"""

    # Signale
    back_requested = Signal()  # Wird ausgelöst wenn Zurück geklickt wird
    settings_requested = Signal()  # Wird ausgelöst wenn Settings geklickt wird

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_session_id = None
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
        left_group = QGroupBox("Transkription")
        left_layout = QVBoxLayout()

        self.transcription_edit = QTextEdit()
        self.transcription_edit.setPlaceholderText("Transkription wird hier erscheinen...")
        # Dummy-Daten
        self.transcription_edit.setPlainText(
            "Dies ist eine Beispiel-Transkription der Audio-Session.\n\n"
            "Hier würde später die automatische Transkription der aufgenommenen "
            "Audio-Datei erscheinen.\n\n"
            "Der Text ist editierbar und kann vor der Verarbeitung angepasst werden.\n\n"
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
            "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua."
        )

        left_layout.addWidget(self.transcription_edit)
        left_group.setLayout(left_layout)
        splitter.addWidget(left_group)

        # Rechte Seite: Transformierter Text
        right_group = QGroupBox("Transformierter Text")
        right_layout = QVBoxLayout()

        self.transformed_edit = QTextEdit()
        self.transformed_edit.setPlaceholderText("Hier erscheint der transformierte Text...")
        # Dummy-Daten
        self.transformed_edit.setPlainText(
            "Hier erscheint der transformierte Text nach dem Klick auf 'Generieren'.\n\n"
            "Je nach gewähltem Prompt wird der Text:\n"
            "- Zusammengefasst\n"
            "- Übersetzt\n"
            "- Oder anderweitig transformiert\n\n"
            "Auch dieser Text ist editierbar."
        )

        right_layout.addWidget(self.transformed_edit)
        right_group.setLayout(right_layout)
        splitter.addWidget(right_group)

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
        back_button = QPushButton("← Zurück")
        back_button.setToolTip("Zurück zur Hauptansicht")
        back_button.setStyleSheet("""
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
        back_button.clicked.connect(self.back_requested.emit)
        toolbar.addWidget(back_button)

        # Separator
        toolbar.addSeparator()

        # Prompt-Auswahl
        prompt_label = QLabel("Prompt:")
        toolbar.addWidget(prompt_label)

        self.prompt_combo = QComboBox()
        self.prompt_combo.addItems([
            "Zusammenfassen",
            "Übersetzen",
            # Später über Settings erweiterbar
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
        self.generate_button = QPushButton("Generieren")
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
        settings_button.clicked.connect(self.settings_requested.emit)
        toolbar.addWidget(settings_button)

        # Spacer rechts
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)

        return toolbar

    def load_session(self, session_id: int):
        """Lädt eine Session in den AI-View"""
        self.current_session_id = session_id
        # TODO: Später echte Transkription laden
        # Aktuell bleiben Dummy-Daten

    def _on_generate_clicked(self):
        """Wird aufgerufen wenn Generieren geklickt wird"""
        # Placeholder für später
        selected_prompt = self.prompt_combo.currentText()
        # TODO: Hier später die echte AI-Integration
        self.transformed_edit.setPlainText(
            f"[Dummy-Ausgabe für '{selected_prompt}']\n\n"
            f"Hier würde der transformierte Text basierend auf dem gewählten Prompt erscheinen.\n\n"
            f"Prompt: {selected_prompt}\n"
            f"Session ID: {self.current_session_id}"
        )
