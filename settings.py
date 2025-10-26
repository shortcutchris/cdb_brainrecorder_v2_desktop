"""
Settings-Manager für persistente App-Einstellungen
"""
from PySide6.QtCore import QSettings


class SettingsManager:
    """Zentrale Settings-Verwaltung mit QSettings"""

    def __init__(self):
        # QSettings speichert automatisch plattformabhängig
        # macOS: ~/Library/Preferences/com.AudioSessions.AudioRecorderApp.plist
        # Windows: Registry
        # Linux: ~/.config/AudioSessions/AudioRecorderApp.conf
        self.settings = QSettings("AudioSessions", "AudioRecorderApp")

    def get_language(self) -> str:
        """Gibt die aktuelle Sprache zurück"""
        return self.settings.value("language", "Deutsch")

    def set_language(self, language: str):
        """Setzt die Sprache"""
        self.settings.setValue("language", language)

    def get_auto_transcription(self) -> bool:
        """Gibt Auto-Transkription Status zurück"""
        return self.settings.value("auto_transcription", False, type=bool)

    def set_auto_transcription(self, enabled: bool):
        """Setzt Auto-Transkription"""
        self.settings.setValue("auto_transcription", enabled)
