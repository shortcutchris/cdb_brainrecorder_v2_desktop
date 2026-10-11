"""Flexible editors with durable saves before selection, tab changes and shutdown."""
from pathlib import Path
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QTextEdit, QPushButton, QLabel, QTabWidget, QComboBox, QFileDialog)
from PySide6.QtCore import Signal, QTimer
from settings import SettingsManager

BUSY = ('importing', 'recording', 'queued', 'transcribing', 'summarizing')


class MeetingContent(QWidget):
    failed = Signal(str)
    saved = Signal(int)
    process_requested = Signal(int, str)

    def __init__(self, repo, parent=None):
        super().__init__(parent)
        self.repo = repo
        self._current_session_id = None
        self._loading = False
        self._dirty = set()
        self._baseline = {}
        self.settings_manager = SettingsManager()
        self.save_timer = QTimer(self)
        self.save_timer.setSingleShot(True)
        self.save_timer.setInterval(350)
        self.save_timer.timeout.connect(self.flush)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        self.details_button = QPushButton('▸ Meetingdetails')
        self.details_button.setCheckable(True)
        layout.addWidget(self.details_button)
        self.details = QWidget()
        dl = QVBoxLayout(self.details)
        dl.setContentsMargins(8, 0, 8, 0)
        self.title_edit = QLineEdit()
        self.title_edit.setMinimumHeight(44)
        self.title_edit.setPlaceholderText('Titel')
        dl.addWidget(self.title_edit)
        self.metadata = QLabel('')
        self.metadata.setWordWrap(True)
        dl.addWidget(self.metadata)
        self.details.hide()
        self.details_button.toggled.connect(self.toggle_details)
        layout.addWidget(self.details)
        self.error_banner = QLabel('')
        self.error_banner.setWordWrap(True)
        self.error_banner.setMaximumHeight(60)
        self.error_banner.setStyleSheet('color:#ffb4b4;padding:4px;')
        self.error_banner.hide()
        layout.addWidget(self.error_banner)
        self.tabs = QTabWidget()
        self.notes_edit = QTextEdit()
        self.transcript_edit = QTextEdit()
        self.summary_edit = QTextEdit()
        self.editors = {'notes': self.notes_edit, 'transcript_text': self.transcript_edit,
                        'summary_text': self.summary_edit}
        for name, editor in zip(('Notizen', 'Transkript', 'Zusammenfassung'), self.editors.values()):
            editor.setAcceptRichText(False)
            editor.setMinimumHeight(60)
            editor.setPlaceholderText(name + ' zu diesem Meeting …')
            self.tabs.addTab(editor, name)
        self.tabs.currentChanged.connect(lambda _: self.flush())
        layout.addWidget(self.tabs, 1)
        self.actions = QWidget()
        actions = QHBoxLayout(self.actions)
        actions.setContentsMargins(0, 0, 0, 0)
        self.prompt_combo = QComboBox()
        self.prompt_combo.setMinimumHeight(44)
        self.prompt_combo.setMinimumWidth(100)
        self.prompt_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.prompt_combo.setToolTip('Bisherige Prompts; Verwaltung in Einstellungen')
        self.load_prompts()
        actions.addWidget(self.prompt_combo, 1)
        self.process_button = QPushButton('Verarbeiten')
        self.process_button.clicked.connect(self.process)
        actions.addWidget(self.process_button)
        self.export_button = QPushButton('Text exportieren')
        self.export_button.clicked.connect(self.export)
        actions.addWidget(self.export_button)
        layout.addWidget(self.actions)
        self.actions.hide()
        self.tabs.currentChanged.connect(lambda index: self.actions.setVisible(index != 0))
        self.save_status = QLabel('Meeting auswählen · automatische Speicherung')
        self.save_status.setMaximumHeight(32)
        self.save_status.hide()
        self.tabs.setToolTip("Änderungen werden automatisch gespeichert")
        for key, editor in self.editors.items():
            editor.textChanged.connect(lambda key=key: self.changed(key))
        self.title_edit.textChanged.connect(lambda _: self.changed('title'))
        self.setStyleSheet('''
            QTextEdit,QLineEdit { background:#000e22; color:#e0e0e0; border:1px solid #003355; padding:8px; }
            QPushButton { background:#ffaa3a; color:#000e22; border:0; border-radius:4px; min-height:44px; padding:0 12px; font-weight:bold; }
            QPushButton:disabled { background:#001b36; color:#6f8ca3; }
            QTabWidget::pane { border:1px solid #003355; }
            QTabBar::tab { background:#001633; color:#e0e0e0; padding:14px 18px; }
            QTabBar::tab:selected { background:#ffaa3a; color:#000e22; }
        ''')
        self.clear()

    def toggle_details(self, opened):
        self.details.setVisible(opened)
        self.details_button.setText(('▾' if opened else '▸') + ' Meetingdetails')

    def load_prompts(self):
        selected = self.prompt_combo.currentData()
        self.prompt_combo.clear()
        for p in self.settings_manager.get_all_prompts():
            self.prompt_combo.addItem(p['name'], p['id'])
        index = self.prompt_combo.findData(selected)
        if index >= 0: self.prompt_combo.setCurrentIndex(index)

    def changed(self, key):
        if self._loading or self._current_session_id is None: return
        self._dirty.add(key)
        self.save_status.setText('Wird gespeichert …')
        self.save_timer.start()

    def flush(self):
        self.save_timer.stop()
        if not self._dirty or self._current_session_id is None: return True
        values = {k: self.title_edit.text() if k == 'title' else self.editors[k].toPlainText()
                  for k in self._dirty}
        try: self.repo.update(self._current_session_id, **values)
        except Exception as e:
            self.save_status.setText('Nicht gespeichert · bitte erneut versuchen')
            self.failed.emit('Text konnte nicht gespeichert werden: ' + str(e))
            return False
        self._baseline.update(values)
        self._dirty.clear()
        self.save_status.setText('Gespeichert')
        self.tabs.setToolTip('Gespeichert · Änderungen bleiben beim Reiterwechsel erhalten')
        self.saved.emit(self._current_session_id)
        return True

    def load_session(self, session):
        if session['id'] == self._current_session_id:
            self.refresh(session)
            return True
        if not self.flush(): return False
        self._loading = True
        self._current_session_id = session['id']
        self.title_edit.setText(session['title'])
        for key, editor in self.editors.items(): editor.setPlainText(session.get(key) or '')
        self._baseline = {k: session.get(k) or '' for k in (*self.editors, 'title')}
        self._loading = False
        self.save_status.setText('Automatische Speicherung · Reiterwechsel behält Änderungen')
        self.refresh(session)
        return True

    def refresh(self, session):
        if session['id'] != self._current_session_id: return
        busy = session.get('transcription_status') in BUSY
        self.process_button.setEnabled(not busy)
        self.process_button.setText('Neu verarbeiten' if session.get('transcription_status') == 'failed' else 'Verarbeiten')
        self.error_banner.setText(session.get('local_error') or '')
        self.error_banner.setVisible(session.get('transcription_status') == 'failed' and bool(session.get('local_error')))
        self.title_edit.setEnabled(True)
        for key, editor in self.editors.items():
            editor.setEnabled(True)
            editor.setReadOnly(busy and key != 'notes')
            value = session.get(key) or ''
            if key not in self._dirty and value != self._baseline.get(key):
                self._loading = True
                position = editor.verticalScrollBar().value()
                old_pos = editor.textCursor().position()
                editor.setPlainText(value)
                cursor = editor.textCursor()
                cursor.setPosition(min(old_pos, len(value)))
                editor.setTextCursor(cursor)
                editor.verticalScrollBar().setValue(position)
                self._baseline[key] = value
                self._loading = False
        self.metadata.setText(f"{session['recorded_at']} · {session['duration_sec']} s · "
                              f"{session['samplerate']} Hz · {session['channels']} Kanal/Kanäle")
        self.metadata.setToolTip(session['path'])
        self.details_button.setToolTip(session['path'])
        self.details_button.setText(('▾' if self.details_button.isChecked() else '▸') + ' ' + self.title_edit.text()[:48] + ' · Details')
        self.process_button.setToolTip(session.get('local_error') or 'Mit ausgewähltem Prompt lokal verarbeiten')
        if busy and not self._dirty:
            self.save_status.setText('Notizen editierbar · KI-Texte bis Abschluss schreibgeschützt')

    def process(self):
        if not self.flush() or self._current_session_id is None: return
        prompt = self.settings_manager.get_prompt_by_id(self.prompt_combo.currentData()) or {}
        self.process_requested.emit(self._current_session_id, prompt.get('prompt_text', ''))

    def export(self):
        if not self.flush() or self._current_session_id is None: return
        path, _ = QFileDialog.getSaveFileName(self, 'Text exportieren',
                    f'meeting-{self._current_session_id}.md', 'Markdown (*.md);;Text (*.txt)')
        if path:
            try:
                Path(path).write_text('# ' + self.title_edit.text() + '\n\n' + '\n\n'.join(
                    '## ' + name + '\n\n' + editor.toPlainText()
                    for name, editor in zip(('Notizen', 'Transkript', 'Zusammenfassung'), self.editors.values())), encoding='utf-8')
            except OSError as e: self.failed.emit(str(e))

    def clear(self):
        if not self.flush(): return False
        self._current_session_id = None
        self._loading = True
        self.title_edit.clear()
        self.title_edit.setEnabled(False)
        for editor in self.editors.values(): editor.clear(); editor.setEnabled(False)
        self.metadata.clear()
        self.error_banner.hide()
        self._baseline = {}
        self._loading = False
        self.process_button.setEnabled(False)
        return True

    def get_current_session_id(self): return self._current_session_id
    def retranslateUi(self): self.load_prompts()
