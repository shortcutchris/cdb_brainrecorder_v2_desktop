"""
Sessions-Tabelle Widget
"""
from PySide6.QtWidgets import (QTableWidget, QTableWidgetItem, QHeaderView,
                               QAbstractItemView)
from PySide6.QtCore import Signal, Qt
from typing import List, Dict, Any


class SessionTableWidget(QTableWidget):
    """Tabelle zur Anzeige aller Audio-Sessions"""

    session_selected = Signal(int)  # Wird ausgelöst wenn eine Session ausgewählt wird

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """Initialisiert die Tabelle"""
        # Spalten definieren
        self.setColumnCount(7)
        self.setHorizontalHeaderLabels([
            "ID", "Titel", "Aufnahmedatum", "Dauer (s)",
            "Samplerate", "Kanäle", "Notizen"
        ])

        # Tabellen-Eigenschaften
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setAlternatingRowColors(True)

        # Spaltenbreiten anpassen
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)

        # Signal verbinden
        self.itemSelectionChanged.connect(self._on_selection_changed)

    def load_sessions(self, sessions: List[Dict[str, Any]]):
        """Lädt Sessions in die Tabelle"""
        self.setRowCount(0)  # Tabelle leeren

        for row_idx, session in enumerate(sessions):
            self.insertRow(row_idx)

            # Daten einfügen
            self.setItem(row_idx, 0, QTableWidgetItem(str(session['id'])))
            self.setItem(row_idx, 1, QTableWidgetItem(session['title']))
            self.setItem(row_idx, 2, QTableWidgetItem(session['recorded_at']))
            self.setItem(row_idx, 3, QTableWidgetItem(str(session['duration_sec'])))
            self.setItem(row_idx, 4, QTableWidgetItem(str(session['samplerate'])))
            self.setItem(row_idx, 5, QTableWidgetItem(str(session['channels'])))
            self.setItem(row_idx, 6, QTableWidgetItem(session['notes'][:50] + '...'
                                                      if len(session['notes']) > 50
                                                      else session['notes']))

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
