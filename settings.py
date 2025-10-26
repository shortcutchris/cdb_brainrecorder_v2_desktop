"""
Settings-Manager für persistente App-Einstellungen
"""
from PySide6.QtCore import QSettings
import json
import uuid


class SettingsManager:
    """Zentrale Settings-Verwaltung mit QSettings"""

    def __init__(self):
        # QSettings speichert automatisch plattformabhängig
        # macOS: ~/Library/Preferences/com.AudioSessions.AudioRecorderApp.plist
        # Windows: Registry
        # Linux: ~/.config/AudioSessions/AudioRecorderApp.conf
        self.settings = QSettings("AudioSessions", "AudioRecorderApp")
        self._initialize_default_prompts()

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

    def get_openai_api_key(self) -> str:
        """Gibt den OpenAI API Key zurück"""
        return self.settings.value("openai_api_key", "")

    def set_openai_api_key(self, key: str):
        """Setzt den OpenAI API Key"""
        self.settings.setValue("openai_api_key", key)

    def get_transcription_language(self) -> str:
        """Gibt die Transkriptions-Sprache als ISO-639-1 Code zurück"""
        language = self.get_language()
        return "de" if language == "Deutsch" else "en"

    # ========== Prompt Management ==========

    def _initialize_default_prompts(self):
        """Initialisiert Standard-Prompts beim ersten Start"""
        # Prüfe ob Prompts bereits existieren
        existing = self.settings.value("custom_prompts", None)
        if existing is None:
            # Keine Prompts vorhanden → Leere Liste initialisieren
            self.settings.setValue("custom_prompts", "[]")

    def _get_default_prompts(self) -> list:
        """Gibt die fest codierten Standard-Prompts zurück"""
        language = self.get_language()

        if language == "Deutsch":
            return [
                {
                    "id": "zusammenfassen",
                    "name": "Zusammenfassen",
                    "prompt_text": "Fasse den folgenden Transkript-Text prägnant zusammen. Behalte die wichtigsten Informationen und Kernaussagen bei.",
                    "is_default": True
                },
                {
                    "id": "uebersetzen",
                    "name": "Übersetzen",
                    "prompt_text": "Übersetze den folgenden deutschen Text ins Englische. Achte auf natürliche Formulierungen und korrekte Terminologie.",
                    "is_default": True
                },
                {
                    "id": "strukturieren",
                    "name": "Strukturieren",
                    "prompt_text": "Strukturiere den folgenden Transkript-Text übersichtlich. Erstelle Überschriften, Absätze und Stichpunkte für bessere Lesbarkeit.",
                    "is_default": True
                }
            ]
        else:  # English
            return [
                {
                    "id": "summarize",
                    "name": "Summarize",
                    "prompt_text": "Summarize the following transcript text concisely. Keep the most important information and key points.",
                    "is_default": True
                },
                {
                    "id": "translate",
                    "name": "Translate",
                    "prompt_text": "Translate the following German text into English. Pay attention to natural phrasing and correct terminology.",
                    "is_default": True
                },
                {
                    "id": "structure",
                    "name": "Structure",
                    "prompt_text": "Structure the following transcript text clearly. Create headings, paragraphs, and bullet points for better readability.",
                    "is_default": True
                }
            ]

    def get_custom_prompts(self) -> list:
        """Gibt Liste von Custom Prompts zurück"""
        prompts_json = self.settings.value("custom_prompts", "[]")
        try:
            return json.loads(prompts_json)
        except json.JSONDecodeError:
            return []

    def set_custom_prompts(self, prompts: list):
        """Speichert Custom Prompts"""
        prompts_json = json.dumps(prompts, ensure_ascii=False)
        self.settings.setValue("custom_prompts", prompts_json)

    def get_all_prompts(self) -> list:
        """Gibt alle Prompts (Default + Custom) zurück"""
        default_prompts = self._get_default_prompts()
        custom_prompts = self.get_custom_prompts()
        return default_prompts + custom_prompts

    def add_prompt(self, name: str, prompt_text: str) -> str:
        """Fügt einen neuen Prompt hinzu, gibt ID zurück"""
        prompts = self.get_custom_prompts()

        # Generiere eindeutige ID
        prompt_id = f"custom_{uuid.uuid4().hex[:8]}"

        # Neuen Prompt erstellen
        new_prompt = {
            "id": prompt_id,
            "name": name,
            "prompt_text": prompt_text,
            "is_default": False
        }

        prompts.append(new_prompt)
        self.set_custom_prompts(prompts)

        return prompt_id

    def update_prompt(self, prompt_id: str, name: str, prompt_text: str):
        """Aktualisiert einen Prompt"""
        prompts = self.get_custom_prompts()

        for prompt in prompts:
            if prompt["id"] == prompt_id:
                prompt["name"] = name
                prompt["prompt_text"] = prompt_text
                break

        self.set_custom_prompts(prompts)

    def delete_prompt(self, prompt_id: str):
        """Löscht einen Custom Prompt (nur wenn not is_default)"""
        prompts = self.get_custom_prompts()

        # Filter: Alle Prompts außer den zu löschenden
        prompts = [p for p in prompts if p["id"] != prompt_id]

        self.set_custom_prompts(prompts)

    def get_prompt_by_id(self, prompt_id: str) -> dict:
        """Gibt einen einzelnen Prompt anhand der ID zurück"""
        all_prompts = self.get_all_prompts()
        for prompt in all_prompts:
            if prompt["id"] == prompt_id:
                return prompt
        return None
