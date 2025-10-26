"""
Settings-Dialog für App-Einstellungen
"""
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,
                               QPushButton, QLabel, QComboBox, QCheckBox, QGroupBox)
from PySide6.QtCore import Qt, QEvent
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from translatable_widget import TranslatableWidget


class SettingsDialog(TranslatableWidget, QDialog):
    """Settings-Dialog für Sprache und Auto-Transkription"""

    def __init__(self, settings_manager, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        """Initialisiert die Benutzeroberfläche"""
        self.setWindowTitle(self.tr("Einstellungen"))
        self.setMinimumWidth(450)
        self.setMinimumHeight(300)

        # Dark Theme
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
            }
            QLabel {
                color: #e0e0e0;
                font-size: 13px;
            }
            QGroupBox {
                color: #e0e0e0;
                border: 1px solid #4a4a4a;
                border-radius: 4px;
                margin-top: 12px;
                font-weight: bold;
                padding-top: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        # Allgemeine Einstellungen
        self.general_group = QGroupBox(self.tr("Allgemein"))
        general_layout = QVBoxLayout()
        general_layout.setSpacing(12)
        general_layout.setContentsMargins(12, 20, 12, 12)

        # Sprache - Linksbündig mit Label und Dropdown untereinander
        self.language_label = QLabel(self.tr("Sprache:"))
        general_layout.addWidget(self.language_label)

        self.language_combo = QComboBox()
        self.language_combo.addItems([self.tr("Deutsch"), self.tr("English")])
        self.language_combo.setMinimumWidth(200)  # Breiter, damit Text lesbar ist
        self.language_combo.setStyleSheet("""
            QComboBox {
                background-color: #3a3a3a;
                color: #e0e0e0;
                border: 1px solid #4a4a4a;
                border-radius: 3px;
                padding: 6px;
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
        general_layout.addWidget(self.language_combo, 0, Qt.AlignmentFlag.AlignLeft)

        self.general_group.setLayout(general_layout)
        layout.addWidget(self.general_group)

        # Transkription Einstellungen
        self.transcription_group = QGroupBox(self.tr("Transkription"))
        transcription_layout = QVBoxLayout()
        transcription_layout.setContentsMargins(12, 20, 12, 12)

        self.auto_transcription_checkbox = QCheckBox(self.tr("Auto-Transkription aktivieren"))
        self.auto_transcription_checkbox.setStyleSheet("""
            QCheckBox {
                color: #e0e0e0;
                font-size: 13px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border: 1px solid #4a4a4a;
                border-radius: 3px;
                background-color: #3a3a3a;
            }
            QCheckBox::indicator:hover {
                border: 1px solid #5a5a5a;
            }
            QCheckBox::indicator:checked {
                background-color: #1976d2;
                border: 1px solid #1976d2;
            }
        """)
        transcription_layout.addWidget(self.auto_transcription_checkbox)

        self.transcription_group.setLayout(transcription_layout)
        layout.addWidget(self.transcription_group)

        layout.addStretch()

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
                border-radius: 4px;
                padding: 8px 20px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #1565c0;
            }
        """)
        self.save_button.clicked.connect(self._save_and_accept)
        button_layout.addWidget(self.save_button)

        layout.addLayout(button_layout)

    def _load_settings(self):
        """Lädt aktuelle Settings in die UI"""
        language = self.settings_manager.get_language()
        self.language_combo.setCurrentText(language)

        auto_transcription = self.settings_manager.get_auto_transcription()
        self.auto_transcription_checkbox.setChecked(auto_transcription)

    def _save_and_accept(self):
        """Speichert Settings und schließt Dialog"""
        self.settings_manager.set_language(self.language_combo.currentText())
        self.settings_manager.set_auto_transcription(
            self.auto_transcription_checkbox.isChecked()
        )
        self.accept()

    def retranslateUi(self):
        """Aktualisiert alle UI-Texte (für Sprachwechsel)"""
        self.setWindowTitle(self.tr("Einstellungen"))
        self.general_group.setTitle(self.tr("Allgemein"))
        self.language_label.setText(self.tr("Sprache:"))

        # Dropdown-Einträge neu setzen (Auswahl beibehalten)
        current_language = self.language_combo.currentText()
        self.language_combo.clear()
        self.language_combo.addItems([self.tr("Deutsch"), self.tr("English")])
        self.language_combo.setCurrentText(current_language)

        self.transcription_group.setTitle(self.tr("Transkription"))
        self.auto_transcription_checkbox.setText(self.tr("Auto-Transkription aktivieren"))
        self.cancel_button.setText(self.tr("Abbrechen"))
        self.save_button.setText(self.tr("Speichern"))

    def changeEvent(self, event):
        """Behandelt Änderungs-Events (z.B. Sprachwechsel)"""
        if event.type() == QEvent.Type.LanguageChange:
            self.retranslateUi()
        super().changeEvent(event)
