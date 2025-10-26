"""
AI-View für Transkription und Textverarbeitung
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QLabel, QComboBox, QTextEdit, QGroupBox,
                               QSplitter, QToolBar, QSizePolicy)
from PySide6.QtCore import Qt, Signal, QEvent
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from translatable_widget import TranslatableWidget


class AIView(TranslatableWidget, QWidget):
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
        self.left_group = QGroupBox(self.tr("Transkription"))
        left_layout = QVBoxLayout()

        self.transcription_edit = QTextEdit()
        self.transcription_edit.setPlaceholderText(self.tr("Transkription wird hier erscheinen..."))
        # Dummy-Daten
        self.transcription_edit.setPlainText(
            self.tr("Dies ist eine Beispiel-Transkription der Audio-Session.\n\n"
            "Hier würde später die automatische Transkription der aufgenommenen "
            "Audio-Datei erscheinen.\n\n"
            "Der Text ist editierbar und kann vor der Verarbeitung angepasst werden.\n\n"
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
            "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.")
        )

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
        # TODO: Später echte Transkription laden
        # Aktuell bleiben Dummy-Daten

    def _on_generate_clicked(self):
        """Wird aufgerufen wenn Generieren geklickt wird"""
        # Placeholder für später
        selected_prompt = self.prompt_combo.currentText()
        # TODO: Hier später die echte AI-Integration
        self.transformed_edit.setPlainText(
            self.tr("[Dummy-Ausgabe für '{0}']\n\n"
            "Hier würde der transformierte Text basierend auf dem gewählten Prompt erscheinen.\n\n"
            "Prompt: {0}\n"
            "Session ID: {1}").format(selected_prompt, self.current_session_id)
        )

    def retranslateUi(self):
        """Aktualisiert alle UI-Texte (für Sprachwechsel)"""
        # GroupBoxes
        self.left_group.setTitle(self.tr("Transkription"))
        self.right_group.setTitle(self.tr("Transformierter Text"))

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
