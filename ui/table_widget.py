"""
Sessions-Tabelle Widget
"""
from PySide6.QtWidgets import (QTableWidget, QTableWidgetItem, QHeaderView,
                               QAbstractItemView, QLabel)
from PySide6.QtCore import Signal, Qt, QEvent, QTimer, QSize
from PySide6.QtGui import QColor
import qtawesome as qta
from typing import List, Dict, Any
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from translatable_widget import TranslatableWidget


class SessionTableWidget(TranslatableWidget, QTableWidget):
    """Tabelle zur Anzeige aller Audio-Sessions"""

    session_selected = Signal(int)  # Wird ausgelöst wenn eine Session ausgewählt wird
    MIN_DISPLAY_ROWS = 30  # Mindestanzahl an anzuzeigenden Zeilen

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """Initialisiert die Tabelle"""
        # Spalten definieren
        self.setColumnCount(6)
        self.setHorizontalHeaderLabels([
            self.tr("ID"), self.tr("Titel"), self.tr("Aufnahmedatum"), self.tr("Dauer (s)"),
            self.tr("Dateigröße"), self.tr("Transkription"), self.tr("Notizen")
        ])

        # Tabellen-Eigenschaften
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setAlternatingRowColors(True)

        # Zeilennummern ausblenden
        self.verticalHeader().setVisible(False)

        # Zeilenhöhe für bessere Icon-Zentrierung
        self.verticalHeader().setDefaultSectionSize(45)

        # Spaltenbreiten anpassen
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # ID
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)           # Titel
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Aufnahmedatum
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Dauer
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Dateigröße
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)             # Transkription
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)           # Notizen

        # Feste Breite für Transkription-Spalte für zentrierte Icons
        header.resizeSection(5, 80)

        # Gitterlinien ausblenden
        self.setShowGrid(False)

        # Icon-Größe für bessere Zentrierung
        self.setIconSize(QSize(20, 20))

        # Stylesheet für Dark Theme mit blauem Hintergrund
        self.setStyleSheet("""
            QTableWidget {
                background-color: #000e22;
                alternate-background-color: #001633;
                color: #e0e0e0;
                gridline-color: #003355;
                border: none;
            }
            QTableWidget::item {
                border-color: #003355;
                padding: 4px;
            }
            QTableWidget::item:selected {
                background-color: #002244;
                color: #ffffff;
            }
            QHeaderView::section {
                background-color: #001633;
                color: #e0e0e0;
                border: none;
                padding: 6px;
                font-weight: bold;
            }
            QTableCornerButton::section {
                background-color: #000e22;
                border: none;
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

            # Dateigröße
            file_size = session.get('file_size', 0)
            file_size_item = QTableWidgetItem(self._format_file_size(file_size))
            file_size_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setItem(row_idx, 4, file_size_item)

            # Transkription Status
            status = session.get('transcription_status', None)
            status_widget = self._create_status_widget(status)
            self.setCellWidget(row_idx, 5, status_widget)

            notes_text = session['notes'][:50] + '...' if len(session['notes']) > 50 else session['notes']
            notes_item = QTableWidgetItem(notes_text)
            notes_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setItem(row_idx, 6, notes_item)

        # Fülle Tabelle mit leeren Zeilen auf, um MIN_DISPLAY_ROWS zu erreichen
        current_rows = len(sessions)
        if current_rows < self.MIN_DISPLAY_ROWS:
            for row_idx in range(current_rows, self.MIN_DISPLAY_ROWS):
                self.insertRow(row_idx)
                # Füge leere Items in alle Spalten ein (außer Transkription-Spalte 5)
                for col_idx in range(7):
                    if col_idx != 5:  # Überspringe Transkriptions-Spalte (nutzt Widgets)
                        empty_item = QTableWidgetItem("")
                        empty_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                        self.setItem(row_idx, col_idx, empty_item)

    def _on_selection_changed(self):
        """Wird aufgerufen wenn die Selektion sich ändert"""
        selected_rows = self.selectionModel().selectedRows()
        if selected_rows:
            row = selected_rows[0].row()
            id_item = self.item(row, 0)
            # Nur echte Sessions verarbeiten (ID-Spalte nicht leer)
            if id_item and id_item.text().strip():
                session_id = int(id_item.text())
                self.session_selected.emit(session_id)

    def get_selected_session_id(self) -> int:
        """Gibt die ID der aktuell ausgewählten Session zurück"""
        selected_rows = self.selectionModel().selectedRows()
        if selected_rows:
            row = selected_rows[0].row()
            id_item = self.item(row, 0)
            # Nur echte Sessions verarbeiten (ID-Spalte nicht leer)
            if id_item and id_item.text().strip():
                return int(id_item.text())
        return -1

    def clear_selection(self):
        """Löscht die aktuelle Selektion"""
        self.clearSelection()

    def _format_file_size(self, size_bytes: int) -> str:
        """Formatiert Dateigröße in menschenlesbarem Format"""
        if size_bytes == 0:
            return "-"

        units = ['B', 'KB', 'MB', 'GB']
        unit_index = 0
        size = float(size_bytes)

        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1

        if unit_index == 0:  # Bytes
            return f"{int(size)} {units[unit_index]}"
        else:
            return f"{size:.1f} {units[unit_index]}"

    def _create_status_widget(self, status: str = None) -> QLabel:
        """Erstellt ein zentriertes Status-Widget mit Icon"""
        if status == "completed":
            icon = qta.icon('fa5s.check-circle', color='#4caf50')  # Green
        elif status == "pending":
            icon = qta.icon('fa5s.spinner', color='#ffc107')  # Yellow/Orange
        elif status == "error":
            icon = qta.icon('fa5s.times-circle', color='#f44336')  # Red
        else:
            icon = qta.icon('fa5s.circle', color='#9e9e9e')  # Gray

        # Erstelle QLabel mit Icon und zentriere es horizontal und vertikal
        label = QLabel()
        label.setPixmap(icon.pixmap(QSize(20, 20)))
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("background-color: transparent;")
        return label

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
            id_item = self.item(row, 0)
            if id_item and id_item.text().strip() and int(id_item.text()) == session_id:
                # Erstelle neues Status-Widget
                status_widget = self._create_status_widget(status)
                self.setCellWidget(row, 5, status_widget)

                # Blink-Effekt bei Fertigstellung
                if blink and status == "completed":
                    self._blink_status(row, 5)
                break

    def _blink_status(self, row: int, col: int, blinks: int = 3):
        """Lässt eine Zelle blinken"""
        widget = self.cellWidget(row, col)
        if not widget or not isinstance(widget, QLabel):
            return

        # Original-Pixmap merken
        original_pixmap = widget.pixmap()
        # Helles Blink-Icon erstellen
        blink_icon = qta.icon('fa5s.check-circle', color='#ffffff')
        blink_pixmap = blink_icon.pixmap(QSize(20, 20))

        blink_count = [0]  # Mutable counter für nested function

        def toggle_icon():
            if blink_count[0] < blinks * 2:
                if blink_count[0] % 2 == 0:
                    # Weißes Icon anzeigen
                    widget.setPixmap(blink_pixmap)
                else:
                    # Original-Icon anzeigen
                    widget.setPixmap(original_pixmap)
                blink_count[0] += 1
            else:
                # Am Ende sicherstellen, dass das Original-Icon angezeigt wird
                widget.setPixmap(original_pixmap)
                timer.stop()

        timer = QTimer()
        timer.timeout.connect(toggle_icon)
        timer.start(300)  # 300ms interval

    def retranslateUi(self):
        """Aktualisiert alle UI-Texte (für Sprachwechsel)"""
        # Header-Labels neu setzen
        self.setHorizontalHeaderLabels([
            self.tr("ID"), self.tr("Titel"), self.tr("Aufnahmedatum"), self.tr("Dauer (s)"),
            self.tr("Dateigröße"), self.tr("Transkription"), self.tr("Notizen")
        ])

    def changeEvent(self, event):
        """Behandelt Änderungs-Events (z.B. Sprachwechsel)"""
        if event.type() == QEvent.Type.LanguageChange:
            self.retranslateUi()
        super().changeEvent(event)
