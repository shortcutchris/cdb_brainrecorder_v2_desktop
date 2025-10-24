"""
Session-Formular für Metadaten-Bearbeitung
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
                               QLineEdit, QTextEdit, QPushButton, QLabel,
                               QGroupBox)
from PySide6.QtCore import Signal
from typing import Optional, Dict, Any


class SessionFormWidget(QWidget):
    """Formular zur Bearbeitung von Session-Metadaten"""

    save_requested = Signal(dict)  # Wird ausgelöst wenn Speichern geklickt wird

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_session_id: Optional[int] = None
        self._setup_ui()

    def _setup_ui(self):
        """Initialisiert das Formular"""
        layout = QVBoxLayout(self)

        # GroupBox für bessere Optik
        group = QGroupBox("Session Details")
        form_layout = QFormLayout()

        # Felder
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("z.B. Podcast Episode 1")

        self.recorded_at_label = QLabel("-")
        self.duration_label = QLabel("-")
        self.samplerate_label = QLabel("-")
        self.channels_label = QLabel("-")
        self.path_label = QLabel("-")
        self.path_label.setWordWrap(True)

        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Notizen zur Session...")
        self.notes_edit.setMaximumHeight(100)

        # Formular befüllen
        form_layout.addRow("Titel:", self.title_edit)
        form_layout.addRow("Aufnahmedatum:", self.recorded_at_label)
        form_layout.addRow("Dauer (s):", self.duration_label)
        form_layout.addRow("Samplerate:", self.samplerate_label)
        form_layout.addRow("Kanäle:", self.channels_label)
        form_layout.addRow("Dateipfad:", self.path_label)
        form_layout.addRow("Notizen:", self.notes_edit)

        group.setLayout(form_layout)
        layout.addWidget(group)

        # Buttons
        button_layout = QHBoxLayout()
        self.save_button = QPushButton("Speichern")
        self.save_button.clicked.connect(self._on_save_clicked)
        self.save_button.setEnabled(False)

        self.clear_button = QPushButton("Leeren")
        self.clear_button.clicked.connect(self.clear)

        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.clear_button)
        button_layout.addStretch()

        layout.addLayout(button_layout)
        layout.addStretch()

    def load_session(self, session: Dict[str, Any]):
        """Lädt Session-Daten ins Formular"""
        self._current_session_id = session['id']

        self.title_edit.setText(session['title'])
        self.recorded_at_label.setText(session['recorded_at'])
        self.duration_label.setText(str(session['duration_sec']))
        self.samplerate_label.setText(str(session['samplerate']))
        self.channels_label.setText(str(session['channels']))
        self.path_label.setText(session['path'])
        self.notes_edit.setPlainText(session['notes'])

        self.save_button.setEnabled(True)

    def clear(self):
        """Leert das Formular"""
        self._current_session_id = None
        self.title_edit.clear()
        self.recorded_at_label.setText("-")
        self.duration_label.setText("-")
        self.samplerate_label.setText("-")
        self.channels_label.setText("-")
        self.path_label.setText("-")
        self.notes_edit.clear()
        self.save_button.setEnabled(False)

    def _on_save_clicked(self):
        """Wird aufgerufen wenn Speichern geklickt wird"""
        if self._current_session_id is None:
            return

        data = {
            'id': self._current_session_id,
            'title': self.title_edit.text(),
            'notes': self.notes_edit.toPlainText()
        }

        self.save_requested.emit(data)

    def get_current_session_id(self) -> Optional[int]:
        """Gibt die ID der aktuell geladenen Session zurück"""
        return self._current_session_id
