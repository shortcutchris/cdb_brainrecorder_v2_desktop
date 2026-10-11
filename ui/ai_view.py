"""
AI-View für Transkription und Textverarbeitung
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QPushButton,
                               QLabel, QComboBox, QTextEdit, QGroupBox,
                               QSplitter, QToolBar, QSizePolicy, QMessageBox, QFileDialog)
from PySide6.QtCore import Qt, Signal, QEvent
import qtawesome as qta
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from translatable_widget import TranslatableWidget
from data.repo import SessionRepository

from settings import SettingsManager


class AIView(TranslatableWidget, QWidget):
    """View für KI-gestützte Textverarbeitung"""

    # Signale
    back_requested = Signal()  # Wird ausgelöst wenn Zurück geklickt wird
    settings_requested = Signal()  # Wird ausgelöst wenn Settings geklickt wird
    transcription_completed = Signal(int, str)  # (session_id, status)

    def __init__(self, parent=None, repo=None):
        super().__init__(parent)
        self.current_session_id = None
        self.current_session_path = None
        self.repo = repo or SessionRepository()
        self.settings_manager = SettingsManager()
        self.transcription_worker = None
        self.transformation_worker = None
        # Gemeinsame Farbpalette für den Dark Mode
        self._colors = {
            "background": "#000e22",
            "panel": "#001633",
            "border": "#003355",
            "border_hover": "#004466",
            "text": "#e0e0e0",
            "muted_text": "#6f8ca3",
            "button_disabled_bg": "#001b36",
            "button_disabled_text": "#5a7791",
        }
        self.setObjectName("aiViewRoot")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._setup_ui()
        self.load_prompts()

    def _setup_ui(self):
        """Initialisiert die Benutzeroberfläche"""
        c = self._colors

        # Dark Theme für den gesamten View
        self.setStyleSheet(
            f"""
            QWidget#aiViewRoot {{
                background-color: {c["background"]};
            }}
            QWidget#aiViewRoot QToolBar {{
                background-color: {c["background"]};
                border-bottom: 1px solid {c["border"]};
                spacing: 12px;
                padding: 12px 16px;
            }}
            QWidget#aiViewRoot QToolBar::separator {{
                background-color: {c["border"]};
                width: 1px;
                height: 24px;
                margin: 0 8px;
            }}
            QWidget#aiViewRoot QToolBar QLabel {{
                color: {c["text"]};
                font-size: 13px;
                padding: 0 8px;
            }}
            QWidget#aiViewRoot QSplitter {{
                background-color: {c["background"]};
                border: none;
            }}
            QWidget#aiViewRoot QSplitter::handle {{
                background-color: transparent;
                border: none;
            }}
            QWidget#aiViewRoot QSplitter::handle:horizontal {{
                background-color: transparent;
                border: none;
            }}
            QWidget#aiViewRoot QSplitter::handle:horizontal:hover {{
                background-color: transparent;
                border: none;
            }}
            QWidget#aiViewRoot QGroupBox {{
                background-color: {c["panel"]};
                color: {c["text"]};
                border: 1px solid {c["border"]};
                border-radius: 10px;
                margin-top: 12px;
                font-weight: bold;
                font-size: 14px;
                padding-top: 12px;
            }}
            QWidget#aiViewRoot QGroupBox::title {{
                subcontrol-origin: margin;
                left: 16px;
                padding: 0 8px;
                background-color: {c["background"]};
                border-radius: 6px;
            }}
            QWidget#aiViewRoot QTextEdit {{
                background-color: {c["background"]};
                color: {c["text"]};
                border: 1px solid {c["border"]};
                border-radius: 6px;
                padding: 10px;
                font-size: 13px;
            }}
            QWidget#aiViewRoot QTextEdit:disabled {{
                color: {c["muted_text"]};
            }}
            QWidget#aiViewRoot QComboBox {{
                background-color: {c["panel"]};
                color: {c["text"]};
                border: 1px solid {c["border"]};
                border-radius: 4px;
                padding: 5px 8px;
                font-size: 13px;
            }}
            QWidget#aiViewRoot QComboBox:hover {{
                border: 1px solid {c["border_hover"]};
            }}
            QWidget#aiViewRoot QComboBox::drop-down {{
                border: none;
            }}
            QWidget#aiViewRoot QComboBox QAbstractItemView {{
                background-color: {c["panel"]};
                color: {c["text"]};
                selection-background-color: #ffaa3a;
                border: 1px solid {c["border"]};
            }}
        """
        )

        # Hauptlayout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 0, 12, 12)
        main_layout.setSpacing(12)

        # Toolbar oben
        toolbar = self._create_toolbar()
        main_layout.addWidget(toolbar)
        self.local_status=QLabel('');self.local_status.setWordWrap(True)
        main_layout.addWidget(self.local_status)

        # Splitter für die zwei Bereiche
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(16)
        splitter.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        # Linke Seite: Transkription
        self.left_group = QGroupBox(self.tr("Transkription"))
        self.left_group.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        left_layout = QVBoxLayout()
        left_layout.setSpacing(8)
        left_layout.setContentsMargins(12, 12, 12, 12)

        # Transkription starten Button (initially hidden)
        self.transcribe_button = QPushButton(self.tr("Transkription starten"))
        self.transcribe_button.setStyleSheet(
            f"""
            QPushButton {{
                background-color: #ffaa3a;
                color: #000e22;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 4px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: #ff9922;
            }}
            QPushButton:disabled {{
                background-color: {c["button_disabled_bg"]};
                color: {c["button_disabled_text"]};
            }}
        """
        )
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
        self.right_group.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        right_layout = QVBoxLayout()
        right_layout.setSpacing(8)
        right_layout.setContentsMargins(12, 12, 12, 12)

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
        splitter.setSizes([1, 1])

        main_layout.addWidget(splitter)

    def _create_toolbar(self) -> QToolBar:
        """Erstellt die Toolbar"""
        toolbar = QToolBar()
        toolbar.setMovable(False)
        c = self._colors
        toolbar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        # Dark Theme Styling
        toolbar.setStyleSheet(
            f"""
            QToolBar {{
                background-color: {c["background"]};
                border-bottom: 1px solid {c["border"]};
                spacing: 12px;
                padding: 12px 16px;
            }}
            QToolBar::separator {{
                background-color: {c["border"]};
                width: 1px;
                height: 24px;
                margin: 0 8px;
            }}
            QToolBar QLabel {{
                color: {c["text"]};
                font-size: 13px;
                padding: 0px 8px;
            }}
        """
        )

        # Zurück-Button
        self.back_button = QPushButton(self.tr("← Zurück"))
        self.back_button.setToolTip(self.tr("Zurück zur Hauptansicht"))
        self.back_button.setStyleSheet("""
            QPushButton {
                background-color: #ffaa3a;
                color: #000e22;
                font-weight: bold;
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #ff9922;
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
        # Prompts werden dynamisch geladen in load_prompts()
        self.prompt_combo.setMinimumWidth(200)
        toolbar.addWidget(self.prompt_combo)

        # Generieren-Button
        self.generate_button = QPushButton(self.tr("Generieren"))
        self.generate_button.setStyleSheet("""
            QPushButton {
                background-color: #ffaa3a;
                color: #000e22;
                font-weight: bold;
                padding: 6px 16px;
                border-radius: 4px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #ff9922;
            }
        """)
        self.generate_button.clicked.connect(self._on_generate_clicked)
        toolbar.addWidget(self.generate_button)
        self.retry_button=QPushButton('Wiederholen')
        self.retry_button.clicked.connect(self.retry_local)
        toolbar.addWidget(self.retry_button)
        self.save_text_button=QPushButton('Text speichern');self.save_text_button.clicked.connect(self.save_text)
        toolbar.addWidget(self.save_text_button)
        self.export_text_button=QPushButton('Export');self.export_text_button.clicked.connect(self.export_text)
        toolbar.addWidget(self.export_text_button)

        # Settings-Button
        toolbar.addSeparator()

        self.settings_button = QPushButton()
        self.settings_button.setIcon(qta.icon('fa5s.cog', color='#000e22'))
        self.settings_button.setToolTip(self.tr("Einstellungen"))
        self.settings_button.setStyleSheet("""
            QPushButton {
                background-color: #ffaa3a;
                color: #000e22;
                font-weight: bold;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #ff9922;
            }
        """)
        self.settings_button.clicked.connect(self.settings_requested.emit)
        toolbar.addWidget(self.settings_button)

        # Spacer rechts
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)

        return toolbar

    def load_prompts(self):
        """Lädt alle Prompts aus Settings und befüllt ComboBox"""
        # Aktuelle Auswahl merken
        current_id = self.prompt_combo.currentData()

        self.prompt_combo.clear()
        prompts = self.settings_manager.get_all_prompts()

        for prompt in prompts:
            # Name anzeigen, ID als Data speichern
            self.prompt_combo.addItem(prompt['name'], prompt['id'])

        # Versuche vorherige Auswahl wiederherzustellen
        if current_id:
            index = self.prompt_combo.findData(current_id)
            if index >= 0:
                self.prompt_combo.setCurrentIndex(index)

    def load_session(self, session_id: int):
        """Lädt eine Session in den AI-View"""
        self.current_session_id = session_id
        self.last_local_result = None

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
        self.transformed_edit.setPlainText(session.get("summary_text") or "")
        self.last_local_result=(session.get('transcript_text') or '',session.get('summary_text') or '')

    def _on_transcribe_clicked(self):
        sid=self.current_session_id
        if not sid:return
        self.host.task(lambda:self.controller.process(sid,reuse_transcript=False),lambda _:self.host.poll(),True)





    def _on_generate_clicked(self):
        sid=self.current_session_id
        if not sid:return
        text=self.transcription_edit.toPlainText().strip()
        if not text:
            self.host.error('Bitte zuerst die Aufnahme lokal transkribieren.');return
        p=self.settings_manager.get_prompt_by_id(self.prompt_combo.currentData()) or {}
        prompt=p.get('prompt_text','')
        self.repo.update(sid,transcript_text=text)
        self.host.task(lambda:self.controller.process(sid,prompt),lambda _:self.host.poll(),True)




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

        # Prompt-Combo neu befüllen mit aktualisierten Prompts
        self.load_prompts()

        self.generate_button.setText(self.tr("Generieren"))
        self.settings_button.setToolTip(self.tr("Einstellungen"))

    def changeEvent(self, event):
        """Behandelt Änderungs-Events (z.B. Sprachwechsel)"""
        if event.type() == QEvent.Type.LanguageChange:
            self.retranslateUi()
        super().changeEvent(event)

    def retry_local(self):
        session=self.repo.get_by_id(self.current_session_id)
        if session and session.get('local_job_id'):
            ident=session['local_job_id']
            self.host.task(lambda:self.controller.engine.retry(ident),lambda _:self.host.poll(),True)
        elif session:
            sid=session['id']
            self.host.task(lambda:self.controller.process(sid),lambda _:self.host.poll(),True)

    def refresh_local(self):
        if not self.current_session_id:return
        session=self.repo.get_by_id(self.current_session_id)
        if not session:return
        status=session.get('transcription_status')
        busy=status in ('importing','recording','queued','transcribing','summarizing')
        self.generate_button.setEnabled(not busy)
        self.save_text_button.setEnabled(not busy)
        self.transcribe_button.setEnabled(not busy)
        self.retry_button.setEnabled(status=='failed')
        names={'importing':'Audio vorbereiten','queued':'Wartet','transcribing':'Transkription läuft','summarizing':'Zusammenfassung läuft','completed':'Fertig','failed':'Fehler'}
        self.generate_button.setText(names.get(status,'Generieren') if busy else 'Generieren')
        result=(session.get('transcript_text') or '',session.get('summary_text') or '')
        if result!=getattr(self,'last_local_result',None):
            previous=getattr(self,'last_local_result',None)
            if previous is not None:
                if result[0]!=previous[0]:self.transcription_edit.setPlainText(result[0])
                if result[1]!=previous[1]:self.transformed_edit.setPlainText(result[1])
            self.last_local_result=result
        if result[0]:self.transcribe_button.hide()
        self.transformed_edit.setPlaceholderText(session.get('local_error') or names.get(status,''))
        self.right_group.setTitle('Transformierter Text · '+names.get(status,'Lokal'))
        self.local_status.setText(names.get(status,'Lokal')+' · '+(session.get('local_error') or 'Verarbeitung bleibt beim Wechsel zu anderen Aufnahmen dieser Session zugeordnet.'))
        self.local_status.setToolTip(session.get('local_metrics') or '')
        self.retry_button.setToolTip(session.get('local_error') or 'Fehlgeschlagenen Auftrag wiederholen')

    def save_text(self):
        if not self.current_session_id:return
        session=self.repo.get_by_id(self.current_session_id)
        if session.get('transcription_status') in ('recording','importing','queued','transcribing','summarizing'):
            self.host.error('Text nach Abschluss der Verarbeitung speichern.');return
        transcript=self.transcription_edit.toPlainText();summary=self.transformed_edit.toPlainText()
        self.repo.update(self.current_session_id,transcript_text=transcript,summary_text=summary)
        self.last_local_result=(transcript,summary)
        self.local_status.setText('Texte gespeichert.')

    def export_text(self):
        if not self.current_session_id:return
        path,_=QFileDialog.getSaveFileName(self,'Text exportieren',f'meeting-{self.current_session_id}.md','Markdown (*.md);;Text (*.txt)')
        if path:
            try:
                Path(path).write_text('# Zusammenfassung\n\n'+self.transformed_edit.toPlainText()+'\n\n# Transkript\n\n'+self.transcription_edit.toPlainText(),encoding='utf-8')
                self.local_status.setText('Text exportiert.')
            except OSError as e:self.host.error(str(e))
