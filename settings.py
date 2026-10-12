"""
Settings-Manager für persistente App-Einstellungen
"""
from PySide6.QtCore import QSettings
import json
import uuid



TASK_RULES = (
    "Aufgaben sind nur ausdrücklich genannte Beauftragungen oder Zusagen mit konkreter Handlung. "
    "Leite niemals eine Aufgabe aus einem Zustand, einer Information oder einem Problem ab. "
    "Ein Budgetbetrag ist nur eine Information, keine Aufgabe 'Budget festlegen'. "
    "Eine nicht freigegebene Bestellung ist ein offener Status, keine Aufgabe 'Bestellung freigeben'. "
    "Ein angekündigter Testtermin gehört zu Terminen, nicht automatisch zu Aufgaben. "
    "Vorschläge sind keine vereinbarten Aufgaben. Verantwortliche und Fristen nur übernehmen, "
    "wenn ausdrücklich genannt, sonst 'nicht genannt'. Wochentage nicht in Kalenderdaten umrechnen. "
    "Keine Fakten erfinden. Keine zusätzliche abschließende Zusammenfassung. "
)
MEETING_PROMPT = (
    "Schreibe ein knappes deutsches Meetingprotokoll ohne Übersetzung. Abschnitte: Kurzüberblick, "
    "Entscheidungen, Aufgaben, Termine, Offene Punkte. " + TASK_RULES +
    "Pro Aufgabe nur eine Zeile: Person: konkrete Handlung — Frist. "
    "Ohne belegte Aufgaben schreibe 'Keine vereinbarten Aufgaben genannt'."
)
TASK_PROMPT = (
    "Schreibe auf Deutsch nur diese drei Abschnitte: Aufgaben, Termine, Offene Punkte. " + TASK_RULES +
    "Pro Aufgabe genau eine kurze Zeile: Person: konkrete Handlung — Frist. "
    "Keine Unterpunkte für Handlung oder Ziel. Allgemeine Informationen wie das Budget weglassen. "
    "Ohne belegte Aufgaben schreibe 'Keine vereinbarten Aufgaben genannt'."
)

class SettingsManager:
    """Zentrale Settings-Verwaltung mit QSettings"""

    def __init__(self, settings=None):
        # QSettings speichert automatisch plattformabhängig
        # macOS: ~/Library/Preferences/com.AudioSessions.AudioRecorderApp.plist
        # Windows: Registry
        # Linux: ~/.config/AudioSessions/AudioRecorderApp.conf
        self.settings = settings if settings is not None else QSettings("AudioSessions", "AudioRecorderApp")
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

    def get_sample_rate(self) -> int:
        """Gibt die Audio Sample Rate zurück"""
        return self.settings.value("sample_rate", 48000, type=int)

    def set_sample_rate(self, rate: int):
        """Setzt die Audio Sample Rate"""
        self.settings.setValue("sample_rate", rate)

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
        return [
            {"id": "zusammenfassen", "name": "Meetingprotokoll",
             "prompt_text": MEETING_PROMPT, "is_default": True},
            {"id": "aufgaben", "name": "Aufgaben & nächste Schritte",
             "prompt_text": TASK_PROMPT, "is_default": True},
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

    # ========== Layout & Display Settings ==========

    def get_layout_mode(self) -> str:
        """
        Gibt den Layout-Modus zurück

        Returns:
            str: "auto", "compact", oder "desktop"
        """
        return self.settings.value("layout_mode", "auto")

    def set_layout_mode(self, mode: str):
        """
        Setzt den Layout-Modus

        Args:
            mode: "auto", "compact", oder "desktop"
        """
        self.settings.setValue("layout_mode", mode)

    def get_touch_mode(self) -> bool:
        """Gibt zurück ob Touch-Modus aktiviert ist"""
        return self.settings.value("touch_mode", False, type=bool)

    def set_touch_mode(self, enabled: bool):
        """Setzt den Touch-Modus"""
        self.settings.setValue("touch_mode", enabled)
