"""
Qt Worker-Threads für asynchrone OpenAI API-Calls
"""
from PySide6.QtCore import QThread, Signal
from services.audio_session_service import AudioSessionService


class TranscriptionWorker(QThread):
    """Worker-Thread für Audio-Transkription"""

    finished = Signal(dict)  # Result-Dict
    error = Signal(str)      # Error-Message
    progress = Signal(str)   # Progress-Message

    def __init__(self, audio_file_path: str, api_key: str, language: str = "de"):
        """
        Initialisiert den Worker

        Args:
            audio_file_path: Pfad zur Audio-Datei
            api_key: OpenAI API Key
            language: Sprache als ISO-639-1 Code
        """
        super().__init__()
        self.audio_file_path = audio_file_path
        self.api_key = api_key
        self.language = language

    def run(self):
        """Führt Transkription aus"""
        self.progress.emit("Starte Transkription...")

        service = AudioSessionService(api_key=self.api_key)
        result = service.transcribe(self.audio_file_path, self.language)

        if result.get("success"):
            self.progress.emit("Transkription abgeschlossen")
            self.finished.emit(result)
        else:
            self.error.emit(result.get("error", "Unbekannter Fehler"))


class TransformationWorker(QThread):
    """Worker-Thread für Text-Transformation"""

    finished = Signal(dict)  # Result-Dict
    error = Signal(str)      # Error-Message
    progress = Signal(str)   # Progress-Message

    def __init__(
        self,
        text: str,
        prompt_id: str,
        api_key: str,
        reasoning: str = "medium",
        verbosity: str = "low"
    ):
        """
        Initialisiert den Worker

        Args:
            text: Zu transformierender Text
            prompt_id: ID des zu verwendenden Prompts
            api_key: OpenAI API Key
            reasoning: Reasoning-Level
            verbosity: Verbosity-Level
        """
        super().__init__()
        self.text = text
        self.prompt_id = prompt_id
        self.api_key = api_key
        self.reasoning = reasoning
        self.verbosity = verbosity

    def run(self):
        """Führt Transformation aus"""
        self.progress.emit("Transformation wird durchgeführt...")

        service = AudioSessionService(api_key=self.api_key)
        result = service.transform(
            text=self.text,
            prompt_id=self.prompt_id,
            reasoning_effort=self.reasoning,
            verbosity=self.verbosity
        )

        if result.get("success"):
            self.progress.emit("Transformation abgeschlossen")
            self.finished.emit(result)
        else:
            self.error.emit(result.get("error", "Unbekannter Fehler"))
