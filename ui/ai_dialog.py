"""
AI-Dialog für Transkription und Textverarbeitung
"""
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                               QLabel, QComboBox, QTextEdit, QGroupBox,
                               QSplitter, QWidget)
from PySide6.QtCore import Qt


class AIDialog(QDialog):
    """Dialog für KI-gestützte Textverarbeitung"""

    def __init__(self, session_id: int, parent=None):
        super().__init__(parent)
        self.session_id = session_id
        self._colors = {
            "background": "#000e22",
            "panel": "#001633",
            "border": "#003355",
            "border_hover": "#004466",
            "text": "#e0e0e0",
        }
        self.setObjectName("aiDialogRoot")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._setup_ui()

    def _setup_ui(self):
        """Initialisiert die Benutzeroberfläche"""
        self.setWindowTitle("KI-Funktionen")

        # Dialog fullscreen/maximiert
        self.setWindowState(Qt.WindowState.WindowMaximized)

        # Dark Theme für den gesamten Dialog
        c = self._colors
        self.setStyleSheet(
            f"""
            QDialog#aiDialogRoot {{
                background-color: {c["background"]};
            }}
            QDialog#aiDialogRoot QSplitter {{
                background-color: {c["background"]};
                border: none;
            }}
            QDialog#aiDialogRoot QSplitter::handle {{
                background-color: transparent;
            }}
            QDialog#aiDialogRoot QSplitter::handle:horizontal {{
                border-left: 1px solid {c["border"]};
            }}
            QDialog#aiDialogRoot QSplitter::handle:horizontal:hover {{
                border-left: 1px solid {c["border_hover"]};
            }}
            QDialog#aiDialogRoot QGroupBox {{
                background-color: {c["panel"]};
                color: {c["text"]};
                border: 1px solid {c["border"]};
                border-radius: 10px;
                margin-top: 12px;
                font-weight: bold;
                padding-top: 12px;
            }}
            QDialog#aiDialogRoot QGroupBox::title {{
                subcontrol-origin: margin;
                left: 16px;
                padding: 0 8px;
                background-color: {c["background"]};
                border-radius: 6px;
            }}
            QDialog#aiDialogRoot QTextEdit {{
                background-color: {c["background"]};
                color: {c["text"]};
                border: 1px solid {c["border"]};
                border-radius: 6px;
                padding: 10px;
                font-size: 13px;
            }}
            QDialog#aiDialogRoot QComboBox {{
                background-color: {c["panel"]};
                color: {c["text"]};
                border: 1px solid {c["border"]};
                border-radius: 4px;
                padding: 5px 8px;
                font-size: 13px;
            }}
            QDialog#aiDialogRoot QComboBox:hover {{
                border: 1px solid {c["border_hover"]};
            }}
            QDialog#aiDialogRoot QComboBox::drop-down {{
                border: none;
            }}
            QDialog#aiDialogRoot QComboBox QAbstractItemView {{
                background-color: {c["panel"]};
                color: {c["text"]};
                selection-background-color: #ffaa3a;
                border: 1px solid {c["border"]};
            }}
        """
        )

        # Hauptlayout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Toolbar oben
        toolbar = self._create_toolbar()
        main_layout.addWidget(toolbar)

        # Splitter für die zwei Bereiche
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        splitter.setProperty("handleWidth", 1)

        # Linke Seite: Transkription
        left_group = QGroupBox("Transkription")
        left_group.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        left_layout = QVBoxLayout()
        left_layout.setSpacing(8)
        left_layout.setContentsMargins(12, 12, 12, 12)

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
        right_group.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        right_layout = QVBoxLayout()
        right_layout.setSpacing(8)
        right_layout.setContentsMargins(12, 12, 12, 12)

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
        splitter.setSizes([1, 1])

        main_layout.addWidget(splitter)

    def _create_toolbar(self) -> QWidget:
        """Erstellt die Toolbar"""
        toolbar_widget = QWidget()
        c = self._colors
        toolbar_widget.setObjectName("aiDialogToolbar")
        toolbar_widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        toolbar_widget.setStyleSheet(
            f"""
            QWidget#aiDialogToolbar {{
                background-color: {c["background"]};
                border-bottom: 1px solid {c["border"]};
            }}
        """
        )

        toolbar_layout = QHBoxLayout(toolbar_widget)
        toolbar_layout.setContentsMargins(12, 6, 12, 6)
        toolbar_layout.setSpacing(12)

        # Prompt-Auswahl
        prompt_label = QLabel("Prompt:")
        prompt_label.setStyleSheet(
            f"background-color: transparent; color: {c['text']}; font-size: 13px;"
        )
        toolbar_layout.addWidget(prompt_label)

        self.prompt_combo = QComboBox()
        self.prompt_combo.addItems([
            "Zusammenfassen",
            "Übersetzen",
            # Später über Settings erweiterbar
        ])
        self.prompt_combo.setMinimumWidth(200)
        self.prompt_combo.setStyleSheet(
            f"""
            QComboBox {{
                background-color: {c["panel"]};
                color: {c["text"]};
                border: 1px solid {c["border"]};
                border-radius: 4px;
                padding: 5px 8px;
                font-size: 13px;
            }}
            QComboBox:hover {{
                border: 1px solid {c["border_hover"]};
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox QAbstractItemView {{
                background-color: {c["panel"]};
                color: {c["text"]};
                selection-background-color: #ffaa3a;
                border: 1px solid {c["border"]};
            }}
        """
        )
        toolbar_layout.addWidget(self.prompt_combo)

        # Generieren-Button
        self.generate_button = QPushButton("Generieren")
        self.generate_button.setStyleSheet(
            """
            QPushButton {
                background-color: #ffaa3a;
                color: white;
                font-weight: bold;
                padding: 6px 16px;
                border-radius: 4px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #ff9922;
            }
        """
        )
        self.generate_button.clicked.connect(self._on_generate_clicked)
        toolbar_layout.addWidget(self.generate_button)

        toolbar_layout.addStretch()

        # Schließen-Button
        close_button = QPushButton("Schließen")
        close_button.setStyleSheet(
            f"""
            QPushButton {{
                background-color: transparent;
                color: {c["text"]};
                border: 1px solid {c["border"]};
                border-radius: 6px;
                padding: 6px 16px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {c["panel"]};
                border: 1px solid {c["border_hover"]};
            }}
        """
        )
        close_button.clicked.connect(self.close)
        toolbar_layout.addWidget(close_button)

        return toolbar_widget

    def _on_generate_clicked(self):
        """Wird aufgerufen wenn Generieren geklickt wird"""
        # Placeholder für später
        selected_prompt = self.prompt_combo.currentText()
        # TODO: Hier später die echte AI-Integration
        self.transformed_edit.setPlainText(
            f"[Dummy-Ausgabe für '{selected_prompt}']\n\n"
            f"Hier würde der transformierte Text basierend auf dem gewählten Prompt erscheinen.\n\n"
            f"Prompt: {selected_prompt}\n"
            f"Session ID: {self.session_id}"
        )
