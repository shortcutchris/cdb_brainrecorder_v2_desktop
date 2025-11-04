"""
Session-Formular für Metadaten-Bearbeitung
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                               QLineEdit, QTextEdit, QPushButton, QLabel,
                               QGroupBox)
from PySide6.QtCore import Signal, QEvent
from typing import Optional, Dict, Any
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from translatable_widget import TranslatableWidget


class SessionFormWidget(TranslatableWidget, QWidget):
    """Formular zur Bearbeitung von Session-Metadaten"""

    save_requested = Signal(dict)  # Wird ausgelöst wenn Speichern geklickt wird

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_session_id: Optional[int] = None
        self._setup_ui()

    def _setup_ui(self):
        """Initialisiert das Formular"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # GroupBox für bessere Optik
        self.group = QGroupBox("")
        self.group.setStyleSheet("""
            QGroupBox {
                border: 1px solid #003355;
                background-color: #001633;
                border-radius: 4px;
                margin-top: 0px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 0px;
                padding: 0 0px;
            }
        """)
        group_layout = QVBoxLayout()
        group_layout.setContentsMargins(12, 12, 12, 12)
        group_layout.setSpacing(12)

        # Felder
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText(self.tr("z.B. Podcast Episode 1"))

        self.recorded_at_label = QLabel("-")
        self.recorded_at_label.setStyleSheet("color: #e0e0e0;")
        self.duration_label = QLabel("-")
        self.duration_label.setStyleSheet("color: #e0e0e0;")
        self.samplerate_label = QLabel("-")
        self.samplerate_label.setStyleSheet("color: #e0e0e0;")
        self.channels_label = QLabel("-")
        self.channels_label.setStyleSheet("color: #e0e0e0;")
        self.path_label = QLabel("-")
        self.path_label.setWordWrap(True)
        self.path_label.setStyleSheet("padding: 2px; color: #e0e0e0;")

        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText(self.tr("Notizen zur Session..."))
        self.notes_edit.setMaximumHeight(60)

        # Titel - Label und Feld horizontal
        title_layout = QHBoxLayout()
        self.title_label = QLabel(self.tr("Titel:"))
        title_layout.addWidget(self.title_label)
        title_layout.addWidget(self.title_edit)
        group_layout.addLayout(title_layout)

        # Aufnahmedatum - Label und Wert horizontal
        recorded_layout = QHBoxLayout()
        self.recorded_label = QLabel(self.tr("Aufnahmedatum:"))
        recorded_layout.addWidget(self.recorded_label)
        recorded_layout.addWidget(self.recorded_at_label)
        recorded_layout.addStretch()
        group_layout.addLayout(recorded_layout)

        # Dauer - Label und Wert horizontal
        duration_layout = QHBoxLayout()
        self.duration_text_label = QLabel(self.tr("Dauer (s):"))
        duration_layout.addWidget(self.duration_text_label)
        duration_layout.addWidget(self.duration_label)
        duration_layout.addStretch()
        group_layout.addLayout(duration_layout)

        # Samplerate und Kanäle in einer Zeile
        tech_layout = QHBoxLayout()
        self.samplerate_text_label = QLabel(self.tr("Samplerate:"))
        tech_layout.addWidget(self.samplerate_text_label)
        tech_layout.addWidget(self.samplerate_label)
        tech_layout.addSpacing(20)
        self.channels_text_label = QLabel(self.tr("Kanäle:"))
        tech_layout.addWidget(self.channels_text_label)
        tech_layout.addWidget(self.channels_label)
        tech_layout.addStretch()
        group_layout.addLayout(tech_layout)

        # Dateipfad - Label und Wert horizontal
        path_layout = QHBoxLayout()
        self.path_text_label = QLabel(self.tr("Dateipfad:"))
        path_layout.addWidget(self.path_text_label)
        path_layout.addWidget(self.path_label, 1)  # stretch factor 1
        group_layout.addLayout(path_layout)

        # Notizen - Label und Feld vertikal (braucht mehr Platz)
        self.notes_text_label = QLabel(self.tr("Notizen:"))
        group_layout.addWidget(self.notes_text_label)
        group_layout.addWidget(self.notes_edit)

        # Buttons - innerhalb der GroupBox
        button_style = """
            QPushButton {
                background-color: #ffaa3a;
                color: #000e22;
                font-weight: bold;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #ff9922;
            }
            QPushButton:disabled {
                background-color: #001b36;
                color: #5a7791;
            }
        """

        button_layout = QHBoxLayout()
        self.save_button = QPushButton(self.tr("Speichern"))
        self.save_button.setStyleSheet(button_style)
        self.save_button.clicked.connect(self._on_save_clicked)
        self.save_button.setEnabled(False)

        self.clear_button = QPushButton(self.tr("Leeren"))
        self.clear_button.setStyleSheet(button_style)
        self.clear_button.clicked.connect(self.clear)

        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.clear_button)
        button_layout.addStretch()

        group_layout.addLayout(button_layout)

        self.group.setLayout(group_layout)
        layout.addWidget(self.group)

    def set_compact_mode(self, enabled: bool):
        """
        Aktiviert Compact-Mode für kleine Bildschirme

        Args:
            enabled: True für Compact-Mode
        """
        # In diesem Widget ist das Layout bereits kompakt
        # Wir könnten hier in Zukunft weitere Anpassungen vornehmen
        # z.B. kleinere Schriftgrößen, weniger Padding, etc.
        pass

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

    def retranslateUi(self):
        """Aktualisiert alle UI-Texte (für Sprachwechsel)"""
        # GroupBox
        self.group.setTitle("")

        # Placeholders
        self.title_edit.setPlaceholderText(self.tr("z.B. Podcast Episode 1"))
        self.notes_edit.setPlaceholderText(self.tr("Notizen zur Session..."))

        # Labels
        self.title_label.setText(self.tr("Titel:"))
        self.recorded_label.setText(self.tr("Aufnahmedatum:"))
        self.duration_text_label.setText(self.tr("Dauer (s):"))
        self.samplerate_text_label.setText(self.tr("Samplerate:"))
        self.channels_text_label.setText(self.tr("Kanäle:"))
        self.path_text_label.setText(self.tr("Dateipfad:"))
        self.notes_text_label.setText(self.tr("Notizen:"))

        # Buttons
        self.save_button.setText(self.tr("Speichern"))
        self.clear_button.setText(self.tr("Leeren"))

    def changeEvent(self, event):
        """Behandelt Änderungs-Events (z.B. Sprachwechsel)"""
        if event.type() == QEvent.Type.LanguageChange:
            self.retranslateUi()
        super().changeEvent(event)
