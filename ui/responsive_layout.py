"""
Responsive Layout Manager für verschiedene Bildschirmgrößen
"""
import platform
from enum import Enum
from PySide6.QtWidgets import QApplication


class ScreenSize(Enum):
    """Bildschirmgrößen-Kategorien"""
    COMPACT = "compact"    # Raspberry Pi (ARM) - Touch-optimiert
    DESKTOP = "desktop"    # Desktop (Mac/Windows/Linux)


class ResponsiveLayoutManager:
    """Verwaltet responsive Layout-Anpassungen"""

    @staticmethod
    def detect_screen_size() -> ScreenSize:
        """
        Erkennt das System und gibt die passende Layout-Kategorie zurück

        Raspberry Pi (ARM) → COMPACT (Touch-optimiert)
        Andere Systeme → DESKTOP

        Returns:
            ScreenSize: COMPACT für Raspberry Pi, DESKTOP für Desktop-Systeme
        """
        # Raspberry Pi Detection (ARM-Architektur)
        is_raspberry_pi = platform.machine().startswith('aarch') or platform.machine().startswith('arm')

        if is_raspberry_pi:
            # Raspberry Pi → immer Touch-optimiertes Compact-Layout
            return ScreenSize.COMPACT

        # Alle anderen Systeme (Mac, Windows, Intel-Linux) → Desktop-Layout
        return ScreenSize.DESKTOP

    @staticmethod
    def get_touch_button_size(screen_size: ScreenSize) -> int:
        """
        Gibt die optimale Button-Größe für Touch-Bedienung zurück

        Args:
            screen_size: Die Bildschirmgröße-Kategorie

        Returns:
            int: Button-Größe in Pixeln
        """
        if screen_size == ScreenSize.COMPACT:
            return 50  # Größere Buttons für Touch auf kleinen Displays
        return 40  # Standard-Größe für Desktop

    @staticmethod
    def get_minimum_window_size(screen_size: ScreenSize) -> tuple[int, int]:
        """
        Gibt die Mindestfenstergröße zurück

        Args:
            screen_size: Die Bildschirmgröße-Kategorie

        Returns:
            tuple: (width, height) in Pixeln
        """
        if screen_size == ScreenSize.COMPACT:
            return (1280, 720)  # Raspberry Pi Auflösung
        return (1050, 720)  # Desktop Mindestgröße

    @staticmethod
    def get_search_field_width(screen_size: ScreenSize) -> int:
        """
        Gibt die optimale Suchfeld-Breite zurück

        Args:
            screen_size: Die Bildschirmgröße-Kategorie

        Returns:
            int: Breite in Pixeln
        """
        if screen_size == ScreenSize.COMPACT:
            return 200  # Kompakter für kleine Displays
        return 350  # Standard für Desktop

    @staticmethod
    def get_waveform_height(screen_size: ScreenSize) -> int:
        """
        Gibt die optimale Waveform-Höhe zurück

        Args:
            screen_size: Die Bildschirmgröße-Kategorie

        Returns:
            int: Höhe in Pixeln
        """
        if screen_size == ScreenSize.COMPACT:
            return 60  # Kompakter für kleine Displays
        return 100  # Standard für Desktop

    @staticmethod
    def get_recorder_panel_height(screen_size: ScreenSize) -> int:
        """
        Gibt die optimale Recorder-Panel-Höhe zurück

        Args:
            screen_size: Die Bildschirmgröße-Kategorie

        Returns:
            int: Mindesthöhe in Pixeln
        """
        if screen_size == ScreenSize.COMPACT:
            return 280  # Kompakter für kleine Displays
        return 350  # Standard für Desktop

    @staticmethod
    def get_player_widget_height(screen_size: ScreenSize) -> int:
        """
        Gibt die optimale Player-Widget-Höhe zurück

        Args:
            screen_size: Die Bildschirmgröße-Kategorie

        Returns:
            int: Mindesthöhe in Pixeln
        """
        if screen_size == ScreenSize.COMPACT:
            return 150  # Kompakter für kleine Displays
        return 180  # Standard für Desktop

    @staticmethod
    def get_session_form_height(screen_size: ScreenSize) -> int:
        """
        Gibt die optimale Session-Form-Höhe zurück

        Args:
            screen_size: Die Bildschirmgröße-Kategorie

        Returns:
            int: Mindesthöhe in Pixeln
        """
        if screen_size == ScreenSize.COMPACT:
            return 200  # Kompakter für kleine Displays
        return 250  # Standard für Desktop
