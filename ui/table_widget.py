"""
Sessions-Tabelle Widget
"""
from PySide6.QtWidgets import (QTableWidget, QTableWidgetItem, QHeaderView,
                               QAbstractItemView)
from PySide6.QtCore import Signal, Qt, QEvent, QTimer
from PySide6.QtGui import QColor
from typing import List, Dict, Any
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from translatable_widget import TranslatableWidget


class SessionTableWidget(TranslatableWidget, QTableWidget):
    """Tabelle zur Anzeige aller Audio-Sessions"""

    session_selected = Signal(int)  # Wird ausgelöst wenn eine Session ausgewählt wird

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """Initialisiert die Tabelle"""
        # Spalten definieren
        self.setColumnCount(8)
        self.setHorizontalHeaderLabels([
            self.tr("ID"), self.tr("Titel"), self.tr("Aufnahmedatum"), self.tr("Dauer (s)"),
            self.tr("Samplerate"), self.tr("Kanäle"), self.tr("Transkription"), self.tr("Notizen")
        ])

        # Tabellen-Eigenschaften
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setAlternatingRowColors(True)

        # Zeilennummern ausblenden
        self.verticalHeader().setVisible(False)

        # Spaltenbreiten anpassen
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # ID
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)           # Titel
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Aufnahmedatum
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Dauer
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Samplerate
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # Kanäle
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)  # Transkription
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)           # Notizen

        # Stylesheet für schwarze Tabellenränder
        self.setStyleSheet("""
            QTableWidget {
                gridline-color: black;
                border: 1px solid black;
            }
            QTableWidget::item {
                border-color: black;
            }
            QHeaderView::section {
                border: 1px solid black;
            }
            QTableCornerButton::section {
                background-color: #2b2b2b;
                border: 1px solid black;
            }
        """)

        # Signal verbinden
        self.itemSelectionChanged.connect(self._on_selection_changed)

    def load_sessions(self, sessions: List[Dict[str, Any]]):
        """Lädt Sessions in die Tabelle"""
        self.setRowCount(0)  # Tabelle leeren

        for row_idx, session in enumerate(sessions):
            self.insertRow(row_idx)

            # Daten einfügen mit horizontaler Zentrierung
            id_item = QTableWidgetItem(str(session['id']))
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setItem(row_idx, 0, id_item)

            title_item = QTableWidgetItem(session['title'])
            title_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setItem(row_idx, 1, title_item)

            date_item = QTableWidgetItem(session['recorded_at'])
            date_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setItem(row_idx, 2, date_item)

            duration_item = QTableWidgetItem(str(session['duration_sec']))
            duration_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setItem(row_idx, 3, duration_item)

            samplerate_item = QTableWidgetItem(str(session['samplerate']))
            samplerate_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setItem(row_idx, 4, samplerate_item)

            channels_item = QTableWidgetItem(str(session['channels']))
            channels_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setItem(row_idx, 5, channels_item)

            # Transkription Status
            status = session.get('transcription_status', None)
            status_item = self._create_status_item(status)
            self.setItem(row_idx, 6, status_item)

            notes_text = session['notes'][:50] + '...' if len(session['notes']) > 50 else session['notes']
            notes_item = QTableWidgetItem(notes_text)
            notes_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setItem(row_idx, 7, notes_item)

    def _on_selection_changed(self):
        """Wird aufgerufen wenn die Selektion sich ändert"""
        selected_rows = self.selectionModel().selectedRows()
        if selected_rows:
            row = selected_rows[0].row()
            session_id = int(self.item(row, 0).text())
            self.session_selected.emit(session_id)

    def get_selected_session_id(self) -> int:
        """Gibt die ID der aktuell ausgewählten Session zurück"""
        selected_rows = self.selectionModel().selectedRows()
        if selected_rows:
            row = selected_rows[0].row()
            return int(self.item(row, 0).text())
        return -1

    def clear_selection(self):
        """Löscht die aktuelle Selektion"""
        self.clearSelection()

    def _create_status_item(self, status: str = None) -> QTableWidgetItem:
        """Erstellt ein Status-Item mit Icon und Farbe"""
        if status == "completed":
            icon = "✓"
            color = QColor(76, 175, 80)  # Green
        elif status == "pending":
            icon = "⚙"
            color = QColor(255, 193, 7)  # Yellow/Orange
        elif status == "error":
            icon = "✗"
            color = QColor(244, 67, 54)  # Red
        else:
            icon = "-"
            color = QColor(158, 158, 158)  # Gray

        item = QTableWidgetItem(icon)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        item.setForeground(color)
        return item

    def update_transcription_status(self, session_id: int, status: str, blink: bool = False):
        """
        Aktualisiert den Transkriptions-Status einer Session

        Args:
            session_id: Die ID der Session
            status: Status ("completed", "pending", "error", None)
            blink: Ob der Status blinken soll (z.B. bei Fertigstellung)
        """
        # Finde die Zeile mit der Session-ID
        for row in range(self.rowCount()):
            if int(self.item(row, 0).text()) == session_id:
                # Erstelle neues Status-Item
                status_item = self._create_status_item(status)
                self.setItem(row, 6, status_item)

                # Blink-Effekt bei Fertigstellung
                if blink and status == "completed":
                    self._blink_status(row, 6)
                break

    def _blink_status(self, row: int, col: int, blinks: int = 3):
        """Lässt eine Zelle blinken"""
        item = self.item(row, col)
        if not item:
            return

        original_color = item.foreground().color()
        blink_count = [0]  # Mutable counter für nested function

        def toggle_color():
            if blink_count[0] < blinks * 2:
                if blink_count[0] % 2 == 0:
                    item.setForeground(QColor(255, 255, 255))  # White
                else:
                    item.setForeground(original_color)
                blink_count[0] += 1
            else:
                timer.stop()

        timer = QTimer()
        timer.timeout.connect(toggle_color)
        timer.start(300)  # 300ms interval

    def retranslateUi(self):
        """Aktualisiert alle UI-Texte (für Sprachwechsel)"""
        # Header-Labels neu setzen
        self.setHorizontalHeaderLabels([
            self.tr("ID"), self.tr("Titel"), self.tr("Aufnahmedatum"), self.tr("Dauer (s)"),
            self.tr("Samplerate"), self.tr("Kanäle"), self.tr("Transkription"), self.tr("Notizen")
        ])

    def changeEvent(self, event):
        """Behandelt Änderungs-Events (z.B. Sprachwechsel)"""
        if event.type() == QEvent.Type.LanguageChange:
            self.retranslateUi()
        super().changeEvent(event)
