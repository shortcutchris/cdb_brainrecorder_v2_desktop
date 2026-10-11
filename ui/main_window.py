"""
Hauptfenster der Audio Sessions App
"""
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QPushButton, QLabel, QComboBox, QLineEdit,
                               QProgressBar, QSplitter, QGroupBox, QMessageBox,
                               QFileDialog, QToolBar, QSizePolicy, QScrollArea,
                               QFrame, QStackedWidget, QTableWidget, QTableWidgetItem, QHeaderView)
from PySide6.QtCore import Qt, QTimer, QEvent, QCoreApplication
from PySide6.QtGui import QAction, QIcon, QPixmap
import qtawesome as qta
import sys
import os
import time
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent))

from recorder import AudioRecorder
from data.repo import SessionRepository
from ui.table_widget import SessionTableWidget
from ui.meeting_content import MeetingContent
from ui.player_widget import PlayerWidget
from ui.waveform_widget import WaveformWidget
from ui.ai_view import AIView
from ui.settings_dialog import SettingsDialog
from settings import SettingsManager
from simple_translator import SimpleTranslator
from translatable_widget import TranslatableWidget
from services.local_controller import LocalController
from ui.tasks import Task
from ui.queue_status import describe_queue
from meeting_recorder.audio import devices
from PySide6.QtWidgets import QScroller
from ui.responsive_layout import ResponsiveLayoutManager, ScreenSize


class MainWindow(TranslatableWidget, QMainWindow):
    """Hauptfenster der Anwendung"""

    def __init__(self, force_layout=None):
        super().__init__()
        root = Path(os.environ.get('CDB_LOCAL_DATA', str(Path.home()/'.local/share/cdb-recorder-local')))
        self.repo = SessionRepository(os.environ.get('CDB_SESSION_DB', 'data/sessions.db'))
        self.controller = LocalController(self.repo, root)
        self.engine = self.controller.engine
        self.recorder = AudioRecorder(self.engine)
        self.tasks = set()
        self.busy = self.polling = False
        self.state = {}
        self.last_signature = None
        self.settings_manager = SettingsManager()
        self.transcription_worker = None
        self.current_transcribing_session_id = None

        # Absoluter Pfad für Aufnahmen
        self.recordings_dir = Path.cwd() / "recordings"

        # Fenster komplett undurchsichtig machen
        self.setWindowOpacity(1.0)

        # Hidden Fullscreen Toggle - Click Counter
        self.logo_click_count = 0
        self.logo_click_timer = QTimer()
        self.logo_click_timer.setSingleShot(True)
        self.logo_click_timer.timeout.connect(self._reset_logo_clicks)

        # Responsive Layout Detection
        self.layout_manager = ResponsiveLayoutManager()
        if force_layout:
            self.screen_size = force_layout
        else:
            # Auto-detection oder aus Settings laden
            layout_mode = self.settings_manager.get_layout_mode() if hasattr(self.settings_manager, 'get_layout_mode') else "auto"
            if layout_mode == "compact":
                self.screen_size = ScreenSize.COMPACT
            elif layout_mode == "desktop":
                self.screen_size = ScreenSize.DESKTOP
            else:  # auto
                self.screen_size = self.layout_manager.detect_screen_size()

        # Translation Setup mit SimpleTranslator
        self.translator = SimpleTranslator()
        SimpleTranslator.set_instance(self.translator)
        self._load_language()

        self._setup_ui()
        self._connect_signals()
        self._load_sessions()
        self._setup_shortcuts()  # Keyboard Shortcuts (F11 für Fullscreen)
        self.ai_view.controller = self.controller
        self.ai_view.host = self
        self.ai_view.repo = self.repo
        self.device_combo.activated.connect(self._device_selected)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll)
        self.timer.start(1000)
        self.poll()
        self.animation_frame=0
        self.activity_timer=QTimer(self)
        self.activity_timer.timeout.connect(self.animate_activity)
        self.activity_timer.start(160)

        # Splash Screen als Overlay anzeigen
        self._show_splash_screen()

    def _show_message(self, icon_type, title, message):
        """
        Zeigt QMessageBox ohne Icon (für Dark Theme)

        Args:
            icon_type: QMessageBox.Information, QMessageBox.Warning, etc.
            title: Dialog-Titel
            message: Nachricht
        """
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setIcon(QMessageBox.Icon.NoIcon)  # KEIN Icon
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)

        # Button-Icons entfernen (z.B. Pfeil-Icon im OK Button)
        for button in msg_box.buttons():
            button.setIcon(QIcon())  # Leeres Icon = kein Icon

        msg_box.exec()

    def _ask_question(self, title, message):
        """
        Zeigt QMessageBox Frage-Dialog ohne Icon

        Returns:
            True wenn Yes, False wenn No
        """
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setIcon(QMessageBox.Icon.NoIcon)  # KEIN Icon
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        # Button-Icons entfernen
        for button in msg_box.buttons():
            button.setIcon(QIcon())  # Leeres Icon = kein Icon

        reply = msg_box.exec()
        return reply == QMessageBox.StandardButton.Yes

    def _setup_shortcuts(self):
        """Richtet Keyboard Shortcuts ein"""
        from PySide6.QtGui import QShortcut, QKeySequence

        # F11 für Fullscreen Toggle
        self.fullscreen_shortcut = QShortcut(QKeySequence("F11"), self)
        self.fullscreen_shortcut.activated.connect(self._toggle_fullscreen)

        # ESC zum Verlassen des Fullscreen-Modus
        self.escape_shortcut = QShortcut(QKeySequence("Esc"), self)
        self.escape_shortcut.activated.connect(self._exit_fullscreen)

    def _toggle_fullscreen(self):
        """Wechselt zwischen Fullscreen und Normal"""
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def _exit_fullscreen(self):
        """Verlässt den Fullscreen-Modus (nur wenn im Fullscreen)"""
        if self.isFullScreen():
            self.showNormal()

    def _on_logo_clicked(self, event):
        """Hidden Fullscreen Toggle - zählt Klicks auf das Logo"""
        self.logo_click_count += 1

        # Reset Timer bei jedem Klick (2 Sekunden Zeitfenster)
        self.logo_click_timer.stop()
        self.logo_click_timer.start(2000)  # 2 Sekunden

        # Nach 5 Klicks: Toggle Fullscreen
        if self.logo_click_count >= 5:
            self._toggle_fullscreen()
            self._reset_logo_clicks()

    def _reset_logo_clicks(self):
        """Setzt den Logo-Click-Counter zurück"""
        self.logo_click_count = 0

    def _setup_ui(self):
        """Initialisiert die Benutzeroberfläche"""
        self.setWindowTitle(self.tr("Corporate Digital Brain Desktop Recorder"))

        # Setze Mindestgröße basierend auf Screen Size
        min_width, min_height = self.layout_manager.get_minimum_window_size(self.screen_size)
        self.setMinimumSize(min(min_width, 960), min(min_height, 560))

        # Globales Dark Theme Styling für gesamte App
        self.setStyleSheet("""
            /* QLabel - explizite Textfarbe für Raspberry Pi */
            QLabel {
                color: #e0e0e0;
            }

            /* QMessageBox und QDialog - Dark Theme für System-Dialoge */
            QMessageBox {
                background-color: #000e22;
                color: #e0e0e0;
                messagebox-text-interaction-flags: 5;
            }
            QMessageBox QLabel {
                color: #e0e0e0;
                background-color: transparent;
            }
            /* Icon-Bereich verstecken (links neben Text) */
            QMessageBox QLabel#qt_msgbox_label {
                padding-left: 0px;
            }
            QMessageBox QPushButton {
                background-color: #ffaa3a;
                color: #000e22;
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
                font-weight: bold;
                min-width: 70px;
            }
            QMessageBox QPushButton:hover {
                background-color: #ffbb4a;
            }
            QMessageBox QPushButton:pressed {
                background-color: #ee9929;
            }
            QDialog {
                background-color: #000e22;
                color: #e0e0e0;
            }
            QDialog QLabel {
                color: #e0e0e0;
            }

            /* QComboBox - explizite Textfarbe für Dropdown */
            QComboBox {
                color: #e0e0e0;
                background-color: #001633;
                border: 1px solid #003355;
                border-radius: 3px;
                padding: 4px 8px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 4px solid #e0e0e0;
                margin-right: 8px;
            }
            QComboBox QAbstractItemView {
                background-color: #001633;
                color: #e0e0e0;
                selection-background-color: #ffaa3a;
                selection-color: #000e22;
                border: 1px solid #003355;
            }

            /* Scrollbar Styling - Responsive (Touch-optimiert für COMPACT) */
            QScrollBar:vertical {
                background-color: #000e22;
                width: """ + ("24px" if self.screen_size == ScreenSize.COMPACT else "12px") + """;
                border: none;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background-color: #003355;
                border-radius: """ + ("6px" if self.screen_size == ScreenSize.COMPACT else "5px") + """;
                min-height: """ + ("60px" if self.screen_size == ScreenSize.COMPACT else "30px") + """;
                margin: """ + ("4px" if self.screen_size == ScreenSize.COMPACT else "2px") + """;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #004466;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
                border: none;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }

            QScrollBar:horizontal {
                background-color: #000e22;
                height: """ + ("24px" if self.screen_size == ScreenSize.COMPACT else "12px") + """;
                border: none;
                margin: 0px;
            }
            QScrollBar::handle:horizontal {
                background-color: #003355;
                border-radius: """ + ("6px" if self.screen_size == ScreenSize.COMPACT else "5px") + """;
                min-width: """ + ("60px" if self.screen_size == ScreenSize.COMPACT else "30px") + """;
                margin: """ + ("4px" if self.screen_size == ScreenSize.COMPACT else "2px") + """;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #004466;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
                border: none;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: none;
            }
        """)

        # StackedWidget für View-Wechsel (Haupt-View <-> AI-View)
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        # ===== Index 0: Haupt-View =====
        self.main_view = QWidget()
        self.main_view.setStyleSheet("QWidget { background-color: #000e22; }")
        main_layout = QVBoxLayout(self.main_view)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Toolbar als Widget zum Layout hinzufügen
        toolbar = self._create_toolbar()
        main_layout.addWidget(toolbar)

        # Splitter für Sessions-Tabelle (links) und rechte Seite
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Sessions-Tabelle (links) - mit Container für Margins
        left_widget = QWidget()
        left_widget.setStyleSheet("QWidget { background-color: #000e22; }")
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(12, 12, 0, 12)  # 12px Abstand oben und unten
        left_layout.setSpacing(0)

        self.session_table = SessionTableWidget()
        # Compact-Mode für kleine Bildschirme
        if self.screen_size == ScreenSize.COMPACT:
            self.session_table.set_compact_mode(True)
        left_layout.addWidget(self.session_table)

        splitter.addWidget(left_widget)

        # Rechte Seite: Container mit Margin (wie links) für aligned Scrollbar
        right_container = QWidget()
        right_container.setStyleSheet("QWidget { background-color: #000e22; }")
        right_container_layout = QVBoxLayout(right_container)
        right_container_layout.setContentsMargins(12, 12, 0, 12)  # 12px Abstand oben und unten
        right_container_layout.setSpacing(0)

        right_layout = right_container_layout
        right_layout.setContentsMargins(12, 8, 12, 8)
        right_layout.setSpacing(6)
        recorder_group = self._create_recorder_panel()
        recorder_group.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        right_layout.addWidget(recorder_group)
        self.player_widget = PlayerWidget()
        self.player_widget.set_compact_layout()
        right_layout.addWidget(self.player_widget)
        self.session_form = MeetingContent(self.repo)
        right_layout.addWidget(self.session_form, 1)
        splitter.addWidget(right_container)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 7)
        splitter.setSizes([380, 880])
        self.main_splitter = splitter
        # Narrow list: details remain available in the content panel.
        for column in (0, 2, 3, 4, 6): self.session_table.setColumnHidden(column, True)
        self.session_table.horizontalHeader().resizeSection(5, 100)

        main_layout.addWidget(splitter, 1)
        self.queue_panel = QTableWidget(0, 3)
        self.queue_panel.setHorizontalHeaderLabels(['Meeting / FIFO', 'Verarbeitung', 'Aktion'])
        self.queue_panel.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.queue_panel.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.queue_panel.verticalHeader().hide()
        self.queue_panel.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.queue_panel.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.queue_panel.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.queue_panel.setColumnWidth(2, 180)
        self.queue_panel.verticalHeader().setDefaultSectionSize(50)
        self.queue_panel.setFixedHeight(156)
        self.queue_panel.hide()
        self.queue_panel.setStyleSheet('QTableWidget {background:#001633;color:#e0e0e0;border:1px solid #003355;} QHeaderView::section {background:#001633;color:#e0e0e0;border:0;padding:5px;}')
        main_layout.addWidget(self.queue_panel)
        footer = QWidget()
        footer.setFixedHeight(56)
        activity_row = QHBoxLayout(footer)
        activity_row.setContentsMargins(12, 4, 12, 4)
        self.activity_icon = QLabel('○')
        self.activity_icon.setFixedWidth(28)
        self.activity_icon.setStyleSheet('color:#ffaa3a;font-size:24px;')
        self.queue_status = QLabel('Lokale Verarbeitung wird geprüft …')
        self.queue_status.setMinimumWidth(0)
        self.queue_status.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.queue_toggle = QPushButton('Warteschlange anzeigen ▴')
        self.queue_toggle.setCheckable(True)
        self.queue_toggle.setMinimumHeight(48)
        self.queue_toggle.setStyleSheet('background:#ffaa3a;color:#000e22;border:0;border-radius:4px;padding:0 12px;font-weight:bold;')
        self.queue_toggle.toggled.connect(self.toggle_queue)
        activity_row.addWidget(self.activity_icon)
        activity_row.addWidget(self.queue_status, 1)
        activity_row.addWidget(self.queue_toggle)
        main_layout.addWidget(footer)
        self.notice = QLabel('')
        self.notice.setWordWrap(True)
        self.notice.setMaximumHeight(40)
        self.notice.setContentsMargins(12, 0, 12, 4)
        self.notice.hide()
        main_layout.addWidget(self.notice)
        QScroller.grabGesture(self.session_table.viewport(), QScroller.ScrollerGestureType.TouchGesture)
        QScroller.grabGesture(self.queue_panel.viewport(), QScroller.ScrollerGestureType.TouchGesture)

        # ===== Index 1: AI-View =====
        self.ai_view = AIView(repo=self.repo)

        # Views zum StackedWidget hinzufügen
        self.stacked_widget.addWidget(self.main_view)  # Index 0
        self.stacked_widget.addWidget(self.ai_view)    # Index 1

    def _create_toolbar(self) -> QToolBar:
        """Erstellt die Toolbar"""
        toolbar = QToolBar()
        toolbar.setMovable(False)

        # Dark Theme Styling
        toolbar.setStyleSheet("""
            QToolBar {
                background-color: #000e22;
                border-bottom: 1px solid #003355;
                spacing: 12px;
                padding: 12px 16px;
            }
            QToolBar QLabel {
                color: #e0e0e0;
                font-size: 13px;
                padding: 0px 8px;
            }
        """)

        # Logo (Hidden Fullscreen Toggle - 5x klicken)
        self.logo_label = QLabel()
        self.logo_label.setFixedSize(32, 32)
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Logo laden
        from ui.splash_widget import resource_path
        logo_path = resource_path("icon.png")
        if os.path.exists(logo_path):
            logo_pixmap = QPixmap(logo_path).scaled(
                32, 32,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.logo_label.setPixmap(logo_pixmap)

        self.logo_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.logo_label.setToolTip(self.tr("Corporate Digital Brain"))
        self.logo_label.mousePressEvent = self._on_logo_clicked

        toolbar.addWidget(self.logo_label)

        # Kleiner Spacer nach Logo
        logo_spacer = QWidget()
        logo_spacer.setFixedWidth(12)
        toolbar.addWidget(logo_spacer)

        # Suchfeld
        self.search_label = QLabel(self.tr("Suche:"))
        toolbar.addWidget(self.search_label)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(self.tr("Suche nach Titel, Notizen oder Transkription..."))
        search_width = self.layout_manager.get_search_field_width(self.screen_size)
        self.search_edit.setMinimumWidth(search_width)
        self.search_edit.setStyleSheet("""
            QLineEdit {
                background-color: #001633;
                color: #e0e0e0;
                border: 1px solid #003355;
                border-radius: 3px;
                padding: 6px;
                font-size: 13px;
            }
        """)
        self.search_edit.textChanged.connect(self._on_search)
        toolbar.addWidget(self.search_edit)

        # Separator
        toolbar.addSeparator()

        # CSV Export Button
        self.export_button = QPushButton(self.tr("CSV Export"))
        self.export_button.setStyleSheet("""
            QPushButton {
                background-color: #ffaa3a;
                color: #000e22;
                font-weight: bold;
                border-radius: 4px;
                padding: 6px 16px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #ff9922;
            }
        """)
        self.export_button.clicked.connect(self._on_export_csv)
        toolbar.addWidget(self.export_button)

        # Settings-Button
        toolbar.addSeparator()

        self.toolbar_settings_button = QPushButton()
        self.toolbar_settings_button.setMinimumSize(48, 48)
        self.toolbar_settings_button.setIcon(qta.icon('fa5s.cog', color='#000e22'))
        self.toolbar_settings_button.setToolTip(self.tr("Einstellungen"))
        self.toolbar_settings_button.setStyleSheet("""
            QPushButton {
                background-color: #ffaa3a;
                color: #000e22;
                font-weight: bold;
                border-radius: 4px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #ff9922;
            }
        """)
        self.toolbar_settings_button.clicked.connect(self._on_settings_clicked)
        toolbar.addWidget(self.toolbar_settings_button)

        # Spacer rechts
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)

        return toolbar

    def _create_recorder_panel(self):
        self.recorder_group = QGroupBox('')
        layout = QVBoxLayout(self.recorder_group)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        meter_row = QHBoxLayout()
        meter_row.setContentsMargins(8, 0, 8, 0)
        ready_label = QLabel('Aufnahme · lokal')
        meter_row.addWidget(ready_label, 1)
        self.mic_label = QLabel('Mikrofon:')
        self.mic_label.hide()
        self.device_combo = QComboBox()
        self._load_devices()
        self.device_combo.setMinimumHeight(44)
        self.device_combo.setMinimumWidth(100)
        self.device_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.device_combo.setToolTip('Mikrofon · 16000 Hz lokal')
        self.device_combo.hide()
        self.samplerate_label = QLabel('Abtastrate:')
        self.samplerate_combo = QComboBox()
        self.samplerate_combo.addItem('16000 Hz · lokal', 16000)
        self.samplerate_label.hide(); self.samplerate_combo.hide()
        self.level_label = QLabel('Pegel:'); self.level_label.hide()
        self.level_bar = QProgressBar()
        self.level_bar.setRange(0, 100)
        self.level_bar.setFixedWidth(110)
        self.level_bar.setToolTip('Mikrofonpegel')
        self.level_bar.setStyleSheet('QProgressBar {border:1px solid #003355;color:#e0e0e0;} QProgressBar::chunk {background:#ffaa3a;}')
        meter_row.addWidget(self.level_bar)
        self.waveform_widget = WaveformWidget()
        self.waveform_widget.hide()
        self.duration_label = QLabel('00:00:00')
        self.duration_label.setStyleSheet('font-size:20px;font-weight:bold;')
        meter_row.addWidget(self.duration_label)
        layout.addLayout(meter_row)
        self.record_button = QPushButton('●  Aufnahme starten')
        self.record_button.setMinimumHeight(72)
        self.record_button.setStyleSheet('background:#d32f2f;color:white;border:0;border-radius:4px;padding:0 14px;font-size:23px;font-weight:bold;')
        self.record_button.clicked.connect(self._on_record_clicked)
        layout.addWidget(self.record_button)
        self.pause_button = QPushButton(self)
        self.pause_button.hide()
        return self.recorder_group

    def _load_devices(self):
        found = self.recorder.get_devices()
        self.device_combo.clear()
        for d in found:self.device_combo.addItem(d['name'], d['index'])
        if not found:self.device_combo.addItem('Kein Mikrofon · Einstellungen öffnen', None)
        index=self.device_combo.findData(self.engine.store.config()['device'])
        if index>=0:self.device_combo.setCurrentIndex(index)

    def _connect_signals(self):
        """Verbindet Signale"""
        # Recorder Signals (Thread-sicher)
        self.recorder.level_updated.connect(self._on_level_update)
        self.recorder.duration_updated.connect(self._on_duration_update)
        self.recorder.waveform_updated.connect(self._on_waveform_update)

        # Table Selection
        self.session_table.session_selected.connect(self._on_session_selected)

        # Form Save
        self.session_form.failed.connect(self.error)
        self.session_form.saved.connect(lambda _: setattr(self, 'last_signature', None))
        self.session_form.process_requested.connect(self.process_content)

        # Player Signals
        self.player_widget.delete_requested.connect(self._on_player_delete_requested)
        self.player_widget.show_in_folder_requested.connect(self._on_show_in_folder)
        self.player_widget.ai_dialog_requested.connect(self._on_ai_view_requested)

        # AI View Signals
        self.ai_view.back_requested.connect(self._on_ai_back)
        self.ai_view.settings_requested.connect(self._on_settings_clicked)
        self.ai_view.transcription_completed.connect(self._on_transcription_status_update)
        self.player_widget.player.error.connect(self.error)

    def _load_sessions(self, search_term: str = ''):
        """Lädt Sessions aus der Datenbank"""
        sessions = self.repo.get_all(search_term)
        self.session_table.load_sessions(sessions)

        # Auto-select erste Session beim Start (nicht bei Suche)
        # Verhindert dass On-Screen-Keyboard durch Suchfeld-Fokus ausgelöst wird
        if not search_term and sessions and self.session_form.get_current_session_id() is None:
            self.session_table.select_first_session()

    def _on_search(self, text: str):
        """Wird aufgerufen wenn im Suchfeld getippt wird"""
        self._load_sessions(text)

    def _on_samplerate_changed(self):
        """Wird aufgerufen wenn die Sample Rate geändert wird"""
        sample_rate = self.samplerate_combo.currentData()
        self.settings_manager.set_sample_rate(sample_rate)

    def _on_record_clicked(self):
        if self.busy or time.monotonic() < getattr(self, "next_record_action", 0):return
        if self.engine.recorder.active:
            self.next_record_action = time.monotonic() + .65
            self.task(self.engine.stop, lambda _:self.poll(), True)
        else:
            if not self.engine.store.config()['setup_complete']:
                self.error('Bitte unter Einstellungen Audio testen und Einrichtung abschließen.')
                self._on_settings_clicked()
                return
            self.next_record_action = time.monotonic() + .65
            self.task(lambda:self.engine.start(''), lambda _:self.poll(), True)

    def _on_pause_clicked(self):
        pass  # Aufnahmen haben ausschließlich Start und Stop.







    def _on_transcription_status_update(self, session_id: int, status: str):
        """Wird aufgerufen wenn AIView eine Transkription abgeschlossen hat"""
        # Tabelle aktualisieren (mit Blink-Effekt bei Erfolg)
        blink = (status == "completed")
        self.session_table.update_transcription_status(session_id, status, blink=blink)

    def _on_level_update(self, level: float):
        """Aktualisiert die Pegelanzeige"""
        # RMS in Prozent umrechnen (grober Richtwert)
        percent = min(int(level * 200), 100)
        self.level_bar.setValue(percent)

    def _on_duration_update(self, duration: float):
        """Aktualisiert die Laufzeit-Anzeige"""
        hours = int(duration // 3600)
        minutes = int((duration % 3600) // 60)
        seconds = int(duration % 60)
        self.duration_label.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")

    def _on_waveform_update(self, audio_data):
        """Aktualisiert die Waveform-Visualisierung"""
        self.waveform_widget.update_waveform(audio_data)

    def _on_session_selected(self, session_id: int):
        """Wird aufgerufen wenn eine Session in der Tabelle ausgewählt wird"""
        session = self.repo.get_by_id(session_id)
        if session:
            previous = self.session_form.get_current_session_id()
            if not self.session_form.load_session(session):
                self.session_table.blockSignals(True)
                if previous: self.session_table.select_session_by_id(previous)
                self.session_table.blockSignals(False)
                return
            # Audio-Datei in Player laden
            if session['path'] and os.path.exists(session['path']):
                try:self.player_widget.load_file(session['path'], session_id)
                except Exception as e:self.player_widget.clear();self.error('Wiedergabe: '+str(e))
            else:self.player_widget.clear()

    def _on_save_session(self, data: dict):
        """Wird aufgerufen wenn eine Session gespeichert werden soll"""
        session_id = data.pop('id')
        self.repo.update(session_id, **data)
        self._load_sessions(self.search_edit.text())
        self._show_message(QMessageBox.Icon.Information, self.tr("Erfolg"), self.tr("Session wurde aktualisiert!"))

    def _on_player_delete_requested(self, session_id: int):
        """Wird aufgerufen wenn im Player der Löschen-Button geklickt wird"""
        if not self.session_form.flush(): return
        confirmed = self._ask_question(
            self.tr("Löschen bestätigen"),
            self.tr("Möchten Sie diese Session wirklich löschen?\n\n⚠️ Die Audiodatei wird ebenfalls permanent gelöscht!")
        )

        if confirmed:
            try:
                result = self.controller.delete(session_id)
            except Exception as e:
                self.error(str(e))
                return
            self.session_form.clear()
            self.player_widget.clear()
            self._load_sessions(self.search_edit.text())

            # Feedback-Message basierend auf Result
            if result.get("file_deleted"):
                self._show_message(QMessageBox.Icon.Information, self.tr("Erfolg"),
                    self.tr("Session und Audiodatei wurden gelöscht."))
            else:
                reason = result.get("reason", "Unbekannt")
                self._show_message(QMessageBox.Icon.Warning, self.tr("Teilweise erfolgreich"),
                    self.tr("Session wurde gelöscht, aber Audiodatei konnte nicht gelöscht werden:\n{0}").format(reason))

    def _on_show_in_folder(self, file_path: str):
        """Zeigt die Datei im Explorer/Finder"""
        if os.path.exists(file_path):
            # Plattformunabhängig die Datei im Ordner anzeigen
            if sys.platform == 'darwin':  # macOS
                os.system(f'open -R "{file_path}"')
            elif sys.platform == 'win32':  # Windows
                os.system(f'explorer /select,"{file_path}"')
            else:  # Linux
                # Fallback: Ordner öffnen
                folder_path = os.path.dirname(file_path)
                os.system(f'xdg-open "{folder_path}"')
        else:
            self._show_message(QMessageBox.Icon.Warning, self.tr("Warnung"),
                              self.tr("Datei nicht gefunden:\n{0}").format(file_path))

    def _on_ai_view_requested(self, session_id: int):
        """Wechselt zum AI-View für die ausgewählte Session"""
        self.open_queue_session(session_id)

    def _on_ai_back(self):
        """Kehrt vom AI-View zur Hauptansicht zurück"""
        # Direkt zur Hauptansicht wechseln
        self.stacked_widget.setCurrentIndex(0)  # Haupt-View

    def _on_export_csv(self):
        """Exportiert Sessions als CSV"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, self.tr("CSV exportieren"), "sessions.csv", self.tr("CSV Dateien (*.csv)")
        )

        if file_path:
            try:
                self.repo.export_to_csv(file_path)
                self._show_message(QMessageBox.Icon.Information, self.tr("Erfolg"),
                                  self.tr("Sessions wurden exportiert:\n{0}").format(file_path))
            except Exception as e:
                self._show_message(QMessageBox.Icon.Critical, self.tr("Fehler"),
                                  self.tr("Export fehlgeschlagen:\n{0}").format(e))

    def _on_settings_clicked(self):
        """Öffnet den Settings-Dialog"""
        from PySide6.QtWidgets import QDialog

        # Merke aktuelle Sprache
        old_language = self.settings_manager.get_language()

        dialog = SettingsDialog(self.settings_manager, self, local_host=self)

        # Verbinde prompts_changed Signal mit AI View reload
        dialog.prompts_changed.connect(self.ai_view.load_prompts)
        dialog.prompts_changed.connect(self.session_form.load_prompts)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Prüfe ob Sprache geändert wurde
            new_language = self.settings_manager.get_language()

            if old_language != new_language:
                # Sprache hat sich geändert - Live-Update
                self.change_language(new_language)
        self._load_devices()

    def retranslateUi(self):
        """Aktualisiert alle UI-Texte (für Sprachwechsel)"""
        # Fenstertitel
        self.setWindowTitle(self.tr("Corporate Digital Brain Desktop Recorder"))

        # Toolbar
        self.search_label.setText(self.tr("Suche:"))
        self.search_edit.setPlaceholderText(self.tr("Suche nach Titel, Notizen oder Transkription..."))
        self.export_button.setText(self.tr("CSV Export"))
        self.toolbar_settings_button.setToolTip(self.tr("Einstellungen"))

        # Recorder Panel
        self.recorder_group.setTitle("")
        self.mic_label.setText(self.tr("Mikrofon:"))
        self.level_label.setText(self.tr("Pegel:"))

        # Record-Button Text abhängig vom Zustand
        if not self.recorder.is_recording:
            self.record_button.setText("●  " + self.tr("Aufnahme starten"))
        else:
            self.record_button.setText("■  " + self.tr("Aufnahme stoppen"))

        # Pause-Button Text abhängig vom Zustand
        if not self.recorder.is_paused:
            self.pause_button.setText(self.tr("Pausieren"))
        else:
            self.pause_button.setText(self.tr("Fortsetzen"))

        # Trigger retranslate in child widgets
        self.session_table.retranslateUi()
        self.player_widget.retranslateUi()
        self.session_form.retranslateUi()
        self.ai_view.retranslateUi()

    def changeEvent(self, event):
        """Behandelt Änderungs-Events (z.B. Sprachwechsel)"""
        if event.type() == QEvent.Type.LanguageChange:
            self.retranslateUi()
        super().changeEvent(event)

    def _load_language(self):
        """Lädt die Sprache aus den Settings und installiert den Translator"""
        language = self.settings_manager.get_language()

        # Map language name to file
        language_map = {
            "Deutsch": "de_DE",
            "English": "en_US",
            "German": "de_DE"  # Fallback für englische UI
        }

        lang_code = language_map.get(language, "de_DE")

        # Pfad zur Translation-Datei
        trans_dir = Path(__file__).parent.parent / "translations"
        ts_file = trans_dir / f"{lang_code}.ts"

        # Lade .ts Datei mit SimpleTranslator
        if ts_file.exists():
            self.translator.load(str(ts_file))
        else:
            print(f"Warnung: Translation-Datei nicht gefunden: {ts_file}")

    def change_language(self, language: str):
        """Wechselt die Sprache der Anwendung zur Laufzeit"""
        # Speichere neue Sprache
        self.settings_manager.set_language(language)

        # Lade neue Übersetzung
        self._load_language()

        # Trigger UI-Update in allen Widgets
        # QEvent.LanguageChange wird automatisch an alle Widgets gesendet
        event = QEvent(QEvent.Type.LanguageChange)
        QCoreApplication.instance().sendEvent(self, event)

    def _show_splash_screen(self):
        """Zeigt Splash Screen als Overlay"""
        from ui.splash_widget import SplashWidget

        # Splash Widget erstellen
        self.splash_widget = SplashWidget(self)

        # Größe an MainWindow anpassen
        self.splash_widget.setGeometry(self.rect())

        # Über allem anzeigen
        self.splash_widget.raise_()
        self.splash_widget.show()

        # Widget-Referenz löschen wenn geschlossen
        self.splash_widget.finished.connect(lambda: setattr(self, 'splash_widget', None))

        # Animationssequenz starten (Logo fade-in → Pause → Alles fade-out)
        self.splash_widget.start_animation()

    def resizeEvent(self, event):
        """Wird aufgerufen wenn Fenster resized wird"""
        super().resizeEvent(event)
        if hasattr(self, 'queue_panel'):
            self.queue_panel.setFixedHeight(156 if self.height() >= 700 else 66)
            self.queue_panel.horizontalHeader().setVisible(self.height() >= 700)

        # Splash an neue Größe anpassen (falls noch sichtbar)
        # Try-except um RuntimeError zu vermeiden wenn C++ Objekt bereits gelöscht
        if hasattr(self, 'splash_widget') and self.splash_widget is not None:
            try:
                if self.splash_widget.isVisible():
                    self.splash_widget.setGeometry(self.rect())
            except RuntimeError:
                # C++ Objekt bereits gelöscht, Referenz entfernen
                self.splash_widget = None

    def error(self, message):
        self.notice.setText(message)
        self.notice.setVisible(bool(message))

    def task(self, fn, done=None, exclusive=False, error=None):
        if exclusive and self.busy:return
        if exclusive:self.busy=True;self.record_button.setEnabled(False)
        task=Task(fn,self);self.tasks.add(task)
        if done:task.result.connect(done)
        task.failed.connect(error or self.error)
        def finish():
            self.tasks.discard(task)
            if exclusive:self.busy=False;self.record_button.setEnabled(True)
            task.deleteLater()
        task.finished.connect(finish);task.start()

    def _device_selected(self):
        device=self.device_combo.currentData()
        if device:
            self.task(lambda:self.engine.configure({'device':device,'setup_complete':False}),lambda _:self.error('Mikrofon gewählt. Bitte in Einstellungen testen.'),True)

    def poll(self):
        if self.polling:return
        self.polling=True
        def read():
            self.controller.sync()
            state=self.engine.state();state['sessions']=self.repo.get_all()
            raw=None
            if state['recording']['id']:
                path=self.engine.store.folder(state['recording']['id'])/'audio.pcm'
                try:
                    with path.open('rb') as f:
                        f.seek(max(0,path.stat().st_size-32000));raw=f.read(32000)
                except FileNotFoundError:pass
            state['waveform']=raw
            return state
        def done(state):
            self.polling=False;self.state=state
            active=bool(state['recording']['id'])
            self.record_button.setText('■  Aufnahme stoppen' if active else '●  Aufnahme starten')
            self.record_button.setStyleSheet('background:' + ('#b71c1c' if active else '#d32f2f') + ';color:white;border:2px solid ' + ('#ffaaaa' if active else '#d32f2f') + ';border-radius:6px;padding:0 14px;font-size:23px;font-weight:bold;')
            self.device_combo.setEnabled(not active)
            self._on_duration_update(state['recording']['seconds'])
            raw=state['waveform'];self.level_bar.setValue(self.engine.probe.level(raw) if raw else 0)
            if active and not self.waveform_widget.is_recording:self.waveform_widget.start_recording()
            if not active and self.waveform_widget.is_recording:self.waveform_widget.stop_recording()
            if active and raw:
                import numpy as np
                self.waveform_widget.update_waveform(np.frombuffer(raw,dtype='<i2').astype('float32')/32768)
            self.animate_activity()
            signature=[(r['id'],r['title'],r.get('transcription_status'),r.get('duration_sec')) for r in state['sessions']]
            if signature!=self.last_signature:
                selected=self.session_table.get_selected_session_id()
                scroll=self.session_table.verticalScrollBar().value()
                # Refresh statuses without interrupting playback or unsaved notes.
                self.session_table.blockSignals(True)
                self.session_table.load_sessions(self.repo.get_all(self.search_edit.text()))
                if selected>0:self.session_table.select_session_by_id(selected)
                self.session_table.verticalScrollBar().setValue(scroll)
                self.session_table.blockSignals(False)
                if selected<=0 and self.session_table.rowCount():self.session_table.select_first_session()
                self.last_signature=signature
            selected=self.session_table.get_selected_session_id()
            row=next((r for r in state['sessions'] if r['id']==selected),None)
            if row and row.get('path') and self.player_widget.current_file_path!=row['path'] and Path(row['path']).is_file():
                try:self.player_widget.load_file(row['path'],selected)
                except Exception as e:self.error('Wiedergabe: '+str(e))
            if row: self.session_form.refresh(row)
            self.refresh_queue()
            self.ai_view.refresh_local()
        def failed(message):
            self.polling=False;self.error(message)
        self.task(read,done,error=failed)

    def closeEvent(self,event):
        if self.engine.recorder.active:
            self.error('Aufnahme zuerst beenden, damit sie sicher gespeichert wird.');event.ignore();return
        if self.busy or any(t.isRunning() for t in self.tasks):
            self.error('Bitte kurz warten, der laufende Vorgang wird abgeschlossen.');event.ignore();return
        if not self.session_form.flush(): event.ignore();return
        self.timer.stop();self.activity_timer.stop();self.player_widget.player.close();self.engine.close();event.accept()

    def animate_activity(self):
        moving,text,failed=describe_queue(self.state)
        self.queue_status.setToolTip(text)
        short = text.split(' | ')
        # Keep phase/elapsed and all failure/recording indicators visible, titles in tooltip/panel.
        first = short[0].split(' · ')
        first = ' · '.join(first[:2]) if len(first) > 2 else short[0]
        waiting = next((part.split(' · ')[0] for part in short if ' warten' in part), '0 warten')
        extras = [part for part in short if 'Fehler' in part or 'parallel' in part or 'vorbereitet' in part]
        extras = [('Fehler · Details öffnen' if 'Fehler' in part else part) for part in extras]
        if any(r.get('transcription_status') == 'failed' and not r.get('local_job_id') for r in self.state.get('sessions', [])) and not failed:
            extras.append('Fehler · Details öffnen'); failed=True
        self.queue_status.setText(' | '.join([first, waiting] + extras))
        if moving:
            self.animation_frame=(getattr(self,'animation_frame',0)+1)%4
            self.activity_icon.setText(('◐','◓','◑','◒')[self.animation_frame])
        else:self.activity_icon.setText('!' if failed else '✓')

    def toggle_queue(self, opened):
        self.queue_panel.setVisible(opened)
        self.queue_toggle.setText('Warteschlange ausblenden ▾' if opened else 'Warteschlange anzeigen ▴')
        self.refresh_queue()

    def process_content(self, sid, prompt):
        self.task(lambda: self.controller.process(sid, prompt), lambda _: self.poll(), True)

    def open_queue_session(self, sid):
        if not self.session_form.flush(): return
        self.search_edit.clear()
        self.session_table.select_session_by_id(sid)
        self.session_form.tabs.setCurrentIndex(2)

    def retry_queue_session(self, sid, ident):
        if not self.session_form.flush(): return
        if ident:
            self.task(lambda: self.engine.retry(ident), lambda _: self.poll(), True)
        else:
            self.process_content(sid, '')

    def refresh_queue(self):
        sessions = {r.get('local_job_id'): r for r in self.state.get('sessions', []) if r.get('local_job_id')}
        jobs = [j for j in self.state.get('jobs', []) if j['id'] in sessions and j['state'] not in ('completed',)]
        priority = {'recording': 0, 'transcribing': 1, 'summarizing': 1, 'importing': 2, 'queued': 3, 'failed': 4}
        jobs.sort(key=lambda j: (priority.get(j['state'], 5), j.get('queued_at') or j['created']))
        rows = [(sessions[j['id']], j) for j in jobs]
        rows += [(r, None) for r in self.state.get('sessions', []) if not r.get('local_job_id') and r.get('transcription_status') == 'failed']
        signature = [(r['id'], r['title'], j['state'] if j else 'failed', r.get('local_error')) for r,j in rows]
        if signature == getattr(self, '_queue_signature', None): return
        self._queue_signature = signature
        scroll = self.queue_panel.verticalScrollBar().value()
        self.queue_panel.setRowCount(len(rows) or 1)
        if not rows:
            self.queue_panel.setItem(0, 0, QTableWidgetItem('Keine offenen Aufträge'))
            self.queue_panel.setItem(0, 1, QTableWidgetItem('Lokal bereit'))
            self.queue_panel.setCellWidget(0, 2, QWidget())
        names = {'recording': 'Aufnahme läuft', 'transcribing': 'Transkription läuft', 'summarizing': 'Zusammenfassung läuft', 'importing': 'Audio vorbereiten', 'queued': 'Wartet', 'failed': 'Fehler'}
        fifo = 0
        for i, (session, job) in enumerate(rows):
            status = job['state'] if job else 'failed'
            if status == 'queued': fifo += 1
            title = (str(fifo) + '. ' if status == 'queued' else '') + session['title']
            self.queue_panel.setItem(i, 0, QTableWidgetItem(title))
            item = QTableWidgetItem(('Fehler · ' + (session.get('local_error') or 'Details öffnen')) if status == 'failed' else names.get(status, status))
            item.setToolTip(session.get('local_error') or '')
            self.queue_panel.setItem(i, 1, item)
            action = QPushButton('Wiederholen' if status == 'failed' else 'Öffnen')
            action.setMinimumHeight(48)
            action.setStyleSheet('background:#ffaa3a;color:#000e22;border:0;padding:0 8px;font-weight:bold;')
            sid = session['id']; ident = job['id'] if job else None
            if status == 'failed': action.clicked.connect(lambda checked=False, sid=sid, ident=ident: self.retry_queue_session(sid, ident))
            else: action.clicked.connect(lambda checked=False, sid=sid: self.open_queue_session(sid))
            self.queue_panel.setCellWidget(i, 2, action)
        self.queue_panel.verticalScrollBar().setValue(scroll)
