"""
Settings-Dialog für App-Einstellungen
"""
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,
                               QPushButton, QLabel, QComboBox, QCheckBox, QGroupBox, QLineEdit,
                               QListWidget, QMessageBox, QListWidgetItem)
from PySide6.QtCore import Qt, QEvent, Signal
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from translatable_widget import TranslatableWidget
from ui.prompt_editor_dialog import PromptEditorDialog


class SettingsDialog(TranslatableWidget, QDialog):
    """Settings-Dialog für Sprache und Auto-Transkription"""

    # Signal wird ausgelöst wenn Prompts geändert wurden
    prompts_changed = Signal()

    def __init__(self, settings_manager, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self._setup_ui()
        self._load_settings()
        self._load_prompts()

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

        # OpenAI API Einstellungen
        self.openai_group = QGroupBox(self.tr("OpenAI API"))
        openai_layout = QVBoxLayout()
        openai_layout.setSpacing(12)
        openai_layout.setContentsMargins(12, 20, 12, 12)

        self.api_key_label = QLabel(self.tr("API Key:"))
        openai_layout.addWidget(self.api_key_label)

        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setPlaceholderText("sk-...")
        self.api_key_input.setMinimumWidth(350)
        self.api_key_input.setStyleSheet("""
            QLineEdit {
                background-color: #3a3a3a;
                color: #e0e0e0;
                border: 1px solid #4a4a4a;
                border-radius: 3px;
                padding: 6px;
                font-size: 13px;
                font-family: monospace;
            }
            QLineEdit:hover {
                border: 1px solid #5a5a5a;
            }
            QLineEdit:focus {
                border: 1px solid #1976d2;
            }
        """)
        openai_layout.addWidget(self.api_key_input, 0, Qt.AlignmentFlag.AlignLeft)

        self.openai_group.setLayout(openai_layout)
        layout.addWidget(self.openai_group)

        # AI Prompts Verwaltung
        self.prompts_group = QGroupBox(self.tr("AI Prompts"))
        prompts_layout = QVBoxLayout()
        prompts_layout.setSpacing(12)
        prompts_layout.setContentsMargins(12, 20, 12, 12)

        # Scrollbare Prompts-Liste
        self.prompts_list = QListWidget()
        self.prompts_list.setMaximumHeight(200)
        self.prompts_list.setMinimumHeight(150)
        self.prompts_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.prompts_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.prompts_list.itemDoubleClicked.connect(self._on_edit_prompt)
        self.prompts_list.itemSelectionChanged.connect(self._on_prompt_selection_changed)
        self.prompts_list.setStyleSheet("""
            QListWidget {
                background-color: #1e1e1e;
                color: #e0e0e0;
                border: 1px solid #4a4a4a;
                border-radius: 3px;
                padding: 8px;
            }
            QListWidget::item {
                padding: 8px;
                border-radius: 3px;
            }
            QListWidget::item:selected {
                background-color: #1976d2;
            }
            QListWidget::item:hover {
                background-color: #3a3a3a;
            }
            QScrollBar:vertical {
                background: #2b2b2b;
                width: 12px;
            }
            QScrollBar::handle:vertical {
                background: #4a4a4a;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical:hover {
                background: #5a5a5a;
            }
        """)
        prompts_layout.addWidget(self.prompts_list)

        # Buttons für Prompt-Verwaltung
        prompts_buttons_layout = QHBoxLayout()
        prompts_buttons_layout.setSpacing(8)

        self.new_prompt_button = QPushButton(self.tr("Neu"))
        self.new_prompt_button.setStyleSheet("""
            QPushButton {
                background-color: #1976d2;
                color: white;
                font-weight: bold;
                padding: 6px 16px;
                border-radius: 4px;
                font-size: 13px;
                border: none;
            }
            QPushButton:hover {
                background-color: #1565c0;
            }
        """)
        self.new_prompt_button.clicked.connect(self._on_new_prompt)
        prompts_buttons_layout.addWidget(self.new_prompt_button)

        self.edit_prompt_button = QPushButton(self.tr("Bearbeiten"))
        self.edit_prompt_button.setEnabled(False)
        self.edit_prompt_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #e0e0e0;
                border: 1px solid #4a4a4a;
                border-radius: 4px;
                padding: 6px 16px;
                font-size: 13px;
            }
            QPushButton:hover:enabled {
                border: 1px solid #5a5a5a;
                background-color: #3a3a3a;
            }
            QPushButton:disabled {
                color: #808080;
                border-color: #3a3a3a;
            }
        """)
        self.edit_prompt_button.clicked.connect(self._on_edit_prompt)
        prompts_buttons_layout.addWidget(self.edit_prompt_button)

        self.delete_prompt_button = QPushButton(self.tr("Löschen"))
        self.delete_prompt_button.setEnabled(False)
        self.delete_prompt_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #e0e0e0;
                border: 1px solid #4a4a4a;
                border-radius: 4px;
                padding: 6px 16px;
                font-size: 13px;
            }
            QPushButton:hover:enabled {
                border: 1px solid #d32f2f;
                background-color: #d32f2f;
                color: white;
            }
            QPushButton:disabled {
                color: #808080;
                border-color: #3a3a3a;
            }
        """)
        self.delete_prompt_button.clicked.connect(self._on_delete_prompt)
        prompts_buttons_layout.addWidget(self.delete_prompt_button)

        prompts_buttons_layout.addStretch()
        prompts_layout.addLayout(prompts_buttons_layout)

        self.prompts_group.setLayout(prompts_layout)
        layout.addWidget(self.prompts_group)

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

        api_key = self.settings_manager.get_openai_api_key()
        self.api_key_input.setText(api_key)

    def _save_and_accept(self):
        """Speichert Settings und schließt Dialog"""
        self.settings_manager.set_language(self.language_combo.currentText())
        self.settings_manager.set_auto_transcription(
            self.auto_transcription_checkbox.isChecked()
        )
        self.settings_manager.set_openai_api_key(self.api_key_input.text())
        self.accept()

    # ========== Prompt Management ==========

    def _load_prompts(self):
        """Lädt alle Prompts in die Liste"""
        self.prompts_list.clear()

        prompts = self.settings_manager.get_all_prompts()
        for prompt in prompts:
            # Item erstellen
            display_name = prompt['name']
            if prompt.get('is_default', False):
                display_name += f" ({self.tr('Standard')})"

            item = QListWidgetItem(display_name)
            item.setData(Qt.ItemDataRole.UserRole, prompt)  # Prompt-Daten an Item hängen
            self.prompts_list.addItem(item)

    def _on_prompt_selection_changed(self):
        """Wird aufgerufen wenn Prompt-Auswahl sich ändert"""
        selected_items = self.prompts_list.selectedItems()

        if not selected_items:
            # Keine Auswahl
            self.edit_prompt_button.setEnabled(False)
            self.delete_prompt_button.setEnabled(False)
            return

        # Ein Prompt ausgewählt
        item = selected_items[0]
        prompt = item.data(Qt.ItemDataRole.UserRole)

        # Bearbeiten immer möglich
        self.edit_prompt_button.setEnabled(True)

        # Löschen nur für Custom Prompts
        is_default = prompt.get('is_default', False)
        self.delete_prompt_button.setEnabled(not is_default)

    def _on_new_prompt(self):
        """Erstellt einen neuen Prompt"""
        dialog = PromptEditorDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_result()
            if data:
                # Prompt speichern
                self.settings_manager.add_prompt(data['name'], data['prompt_text'])
                # Liste neu laden
                self._load_prompts()
                # Signal auslösen
                self.prompts_changed.emit()

    def _on_edit_prompt(self):
        """Bearbeitet den ausgewählten Prompt"""
        selected_items = self.prompts_list.selectedItems()
        if not selected_items:
            return

        item = selected_items[0]
        prompt = item.data(Qt.ItemDataRole.UserRole)

        # Standard-Prompts können nicht bearbeitet werden
        if prompt.get('is_default', False):
            QMessageBox.information(
                self,
                self.tr("Bearbeiten nicht möglich"),
                self.tr("Standard-Prompts können nicht bearbeitet werden.")
            )
            return

        # Dialog öffnen
        dialog = PromptEditorDialog(self, prompt=prompt)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_result()
            if data:
                # Prompt aktualisieren
                self.settings_manager.update_prompt(
                    prompt['id'],
                    data['name'],
                    data['prompt_text']
                )
                # Liste neu laden
                self._load_prompts()
                # Signal auslösen
                self.prompts_changed.emit()

    def _on_delete_prompt(self):
        """Löscht den ausgewählten Prompt"""
        selected_items = self.prompts_list.selectedItems()
        if not selected_items:
            return

        item = selected_items[0]
        prompt = item.data(Qt.ItemDataRole.UserRole)

        # Standard-Prompts können nicht gelöscht werden
        if prompt.get('is_default', False):
            QMessageBox.warning(
                self,
                self.tr("Löschen nicht möglich"),
                self.tr("Standard-Prompts können nicht gelöscht werden.")
            )
            return

        # Bestätigung
        reply = QMessageBox.question(
            self,
            self.tr("Prompt löschen"),
            self.tr("Möchten Sie diesen Prompt wirklich löschen?\n\n{0}").format(prompt['name']),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Prompt löschen
            self.settings_manager.delete_prompt(prompt['id'])
            # Liste neu laden
            self._load_prompts()
            # Signal auslösen
            self.prompts_changed.emit()

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
        self.openai_group.setTitle(self.tr("OpenAI API"))
        self.api_key_label.setText(self.tr("API Key:"))

        # AI Prompts
        self.prompts_group.setTitle(self.tr("AI Prompts"))
        self.new_prompt_button.setText(self.tr("Neu"))
        self.edit_prompt_button.setText(self.tr("Bearbeiten"))
        self.delete_prompt_button.setText(self.tr("Löschen"))
        # Liste neu laden um "(Standard)" zu übersetzen
        self._load_prompts()

        self.cancel_button.setText(self.tr("Abbrechen"))
        self.save_button.setText(self.tr("Speichern"))

    def changeEvent(self, event):
        """Behandelt Änderungs-Events (z.B. Sprachwechsel)"""
        if event.type() == QEvent.Type.LanguageChange:
            self.retranslateUi()
        super().changeEvent(event)
