"""
Prompt-Editor Dialog für Create/Edit von Custom Prompts
"""
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,
                               QPushButton, QLabel, QLineEdit, QTextEdit, QMessageBox)
from PySide6.QtCore import Qt, QEvent
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from translatable_widget import TranslatableWidget


class PromptEditorDialog(TranslatableWidget, QDialog):
    """Dialog zum Erstellen/Bearbeiten von Prompts"""

    def __init__(self, parent=None, prompt=None):
        super().__init__(parent)
        self.prompt = prompt  # None = Create, Dict = Edit
        self._setup_ui()
        self._load_prompt()

    def _setup_ui(self):
        """Initialisiert die Benutzeroberfläche"""
        # Titel je nach Modus
        if self.prompt is None:
            self.setWindowTitle(self.tr("Prompt erstellen"))
        else:
            self.setWindowTitle(self.tr("Prompt bearbeiten"))

        self.setMinimumWidth(500)
        self.setMinimumHeight(350)

        # Dark Theme
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
            }
            QLabel {
                color: #e0e0e0;
                font-size: 13px;
            }
            QLineEdit {
                background-color: #3a3a3a;
                color: #e0e0e0;
                border: 1px solid #4a4a4a;
                border-radius: 3px;
                padding: 8px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #1976d2;
            }
            QTextEdit {
                background-color: #3a3a3a;
                color: #e0e0e0;
                border: 1px solid #4a4a4a;
                border-radius: 3px;
                padding: 8px;
                font-size: 13px;
            }
            QTextEdit:focus {
                border: 1px solid #1976d2;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        # Name
        self.name_label = QLabel(self.tr("Name:"))
        layout.addWidget(self.name_label)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText(self.tr("z.B. Meeting-Notizen erstellen"))
        layout.addWidget(self.name_edit)

        # Prompt-Text
        self.prompt_text_label = QLabel(self.tr("Prompt-Text:"))
        layout.addWidget(self.prompt_text_label)

        self.prompt_text_edit = QTextEdit()
        self.prompt_text_edit.setPlaceholderText(
            self.tr("Beschreibe hier, was der AI-Assistent mit dem Text machen soll...")
        )
        self.prompt_text_edit.setMinimumHeight(150)
        layout.addWidget(self.prompt_text_edit)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.cancel_button = QPushButton(self.tr("Abbrechen"))
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #e0e0e0;
                border: 1px solid #4a4a4a;
                border-radius: 4px;
                padding: 8px 20px;
                font-size: 13px;
            }
            QPushButton:hover {
                border: 1px solid #5a5a5a;
                background-color: #3a3a3a;
            }
        """)
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)

        self.save_button = QPushButton(self.tr("Speichern"))
        self.save_button.setStyleSheet("""
            QPushButton {
                background-color: #1976d2;
                color: white;
                font-weight: bold;
                padding: 8px 20px;
                border-radius: 4px;
                font-size: 13px;
                border: none;
            }
            QPushButton:hover {
                background-color: #1565c0;
            }
        """)
        self.save_button.clicked.connect(self._on_save)
        button_layout.addWidget(self.save_button)

        layout.addLayout(button_layout)

    def _load_prompt(self):
        """Lädt Prompt-Daten im Edit-Modus"""
        if self.prompt:
            self.name_edit.setText(self.prompt.get("name", ""))
            self.prompt_text_edit.setPlainText(self.prompt.get("prompt_text", ""))

    def _on_save(self):
        """Validierung und Speichern"""
        name = self.name_edit.text().strip()
        prompt_text = self.prompt_text_edit.toPlainText().strip()

        # Validierung
        if not name:
            QMessageBox.warning(
                self,
                self.tr("Validierung"),
                self.tr("Der Prompt-Name darf nicht leer sein.")
            )
            self.name_edit.setFocus()
            return

        if not prompt_text:
            QMessageBox.warning(
                self,
                self.tr("Validierung"),
                self.tr("Der Prompt-Text darf nicht leer sein.")
            )
            self.prompt_text_edit.setFocus()
            return

        # Daten für Rückgabe vorbereiten
        self.result_data = {
            "name": name,
            "prompt_text": prompt_text
        }

        self.accept()

    def get_result(self):
        """Gibt die eingegebenen Daten zurück"""
        return getattr(self, 'result_data', None)

    def retranslateUi(self):
        """Aktualisiert alle UI-Texte (für Sprachwechsel)"""
        # Titel
        if self.prompt is None:
            self.setWindowTitle(self.tr("Prompt erstellen"))
        else:
            self.setWindowTitle(self.tr("Prompt bearbeiten"))

        # Labels
        self.name_label.setText(self.tr("Name:"))
        self.prompt_text_label.setText(self.tr("Prompt-Text:"))

        # Placeholders
        self.name_edit.setPlaceholderText(self.tr("z.B. Meeting-Notizen erstellen"))
        self.prompt_text_edit.setPlaceholderText(
            self.tr("Beschreibe hier, was der AI-Assistent mit dem Text machen soll...")
        )

        # Buttons
        self.cancel_button.setText(self.tr("Abbrechen"))
        self.save_button.setText(self.tr("Speichern"))

    def changeEvent(self, event):
        """Behandelt Änderungs-Events (z.B. Sprachwechsel)"""
        if event.type() == QEvent.Type.LanguageChange:
            self.retranslateUi()
        super().changeEvent(event)
