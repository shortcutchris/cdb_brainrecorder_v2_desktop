"""
Einfacher Translation-Manager der .ts XML-Dateien direkt liest
Ersetzt QTranslator da lrelease nicht verfügbar ist
"""
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Optional


class SimpleTranslator:
    """Einfacher Übersetzer für .ts Dateien"""

    # Globale Instanz für tr() Zugriff
    _instance: Optional['SimpleTranslator'] = None

    def __init__(self):
        self.translations: Dict[str, Dict[str, str]] = {}
        self.current_language = "de_DE"

    @classmethod
    def instance(cls) -> 'SimpleTranslator':
        """Gibt die globale Instanz zurück"""
        if cls._instance is None:
            cls._instance = SimpleTranslator()
        return cls._instance

    @classmethod
    def set_instance(cls, translator: 'SimpleTranslator'):
        """Setzt die globale Instanz"""
        cls._instance = translator

    def load(self, ts_file: str) -> bool:
        """Lädt eine .ts Datei"""
        ts_path = Path(ts_file)

        if not ts_path.exists():
            print(f"Warnung: Translation-Datei nicht gefunden: {ts_file}")
            return False

        try:
            tree = ET.parse(ts_path)
            root = tree.getroot()

            self.translations.clear()

            # Parse all contexts
            for context in root.findall('.//context'):
                context_name_elem = context.find('name')
                if context_name_elem is None:
                    continue

                context_name = context_name_elem.text

                if context_name not in self.translations:
                    self.translations[context_name] = {}

                # Parse all messages in this context
                for message in context.findall('message'):
                    source_elem = message.find('source')
                    trans_elem = message.find('translation')

                    if source_elem is not None and trans_elem is not None:
                        source_text = source_elem.text or ""
                        trans_text = trans_elem.text or source_text

                        self.translations[context_name][source_text] = trans_text

            # Extract language from filename
            if 'en_US' in ts_file:
                self.current_language = "en_US"
            elif 'de_DE' in ts_file:
                self.current_language = "de_DE"

            print(f"✓ Sprache geladen: {self.current_language} ({len(self.translations)} Contexts)")
            return True

        except Exception as e:
            print(f"Fehler beim Laden von {ts_file}: {e}")
            import traceback
            traceback.print_exc()
            return False

    def translate(self, context: str, source_text: str) -> str:
        """Übersetzt einen Text"""
        # Suche in dem spezifischen Context
        if context in self.translations:
            if source_text in self.translations[context]:
                return self.translations[context][source_text]

        # Fallback: Suche in allen Contexts
        for ctx_translations in self.translations.values():
            if source_text in ctx_translations:
                return ctx_translations[source_text]

        # Fallback: Originaltext zurückgeben
        return source_text

    def get_current_language(self) -> str:
        """Gibt die aktuelle Sprache zurück"""
        return self.current_language


# Globale tr() Funktion für einfachen Zugriff
def tr(source_text: str, context: str = "Unknown") -> str:
    """Globale Übersetzungsfunktion"""
    translator = SimpleTranslator.instance()
    return translator.translate(context, source_text)
