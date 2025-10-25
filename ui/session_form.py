"""
Session-Formular für Metadaten-Bearbeitung
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
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
        group_layout = QVBoxLayout()

        # Felder
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("z.B. Podcast Episode 1")

        self.recorded_at_label = QLabel("-")
        self.duration_label = QLabel("-")
        self.samplerate_label = QLabel("-")
        self.channels_label = QLabel("-")
        self.path_label = QLabel("-")
        self.path_label.setWordWrap(True)
        self.path_label.setStyleSheet("padding: 2px;")

        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Notizen zur Session...")
        self.notes_edit.setMaximumHeight(60)

        # Titel - Label und Feld horizontal
        title_layout = QHBoxLayout()
        title_layout.addWidget(QLabel("Titel:"))
        title_layout.addWidget(self.title_edit)
        group_layout.addLayout(title_layout)

        # Aufnahmedatum - Label und Wert horizontal
        recorded_layout = QHBoxLayout()
        recorded_layout.addWidget(QLabel("Aufnahmedatum:"))
        recorded_layout.addWidget(self.recorded_at_label)
        recorded_layout.addStretch()
        group_layout.addLayout(recorded_layout)

        # Dauer - Label und Wert horizontal
        duration_layout = QHBoxLayout()
        duration_layout.addWidget(QLabel("Dauer (s):"))
        duration_layout.addWidget(self.duration_label)
        duration_layout.addStretch()
        group_layout.addLayout(duration_layout)

        # Samplerate und Kanäle in einer Zeile
        tech_layout = QHBoxLayout()
        tech_layout.addWidget(QLabel("Samplerate:"))
        tech_layout.addWidget(self.samplerate_label)
        tech_layout.addSpacing(20)
        tech_layout.addWidget(QLabel("Kanäle:"))
        tech_layout.addWidget(self.channels_label)
        tech_layout.addStretch()
        group_layout.addLayout(tech_layout)

        # Dateipfad - Label und Wert horizontal
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("Dateipfad:"))
        path_layout.addWidget(self.path_label, 1)  # stretch factor 1
        group_layout.addLayout(path_layout)

        # Notizen - Label und Feld vertikal (braucht mehr Platz)
        group_layout.addWidget(QLabel("Notizen:"))
        group_layout.addWidget(self.notes_edit)

        # Buttons - innerhalb der GroupBox
        button_layout = QHBoxLayout()
        self.save_button = QPushButton("Speichern")
        self.save_button.clicked.connect(self._on_save_clicked)
        self.save_button.setEnabled(False)

        self.clear_button = QPushButton("Leeren")
        self.clear_button.clicked.connect(self.clear)

        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.clear_button)
        button_layout.addStretch()

        group_layout.addLayout(button_layout)

        group.setLayout(group_layout)
        layout.addWidget(group)

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
