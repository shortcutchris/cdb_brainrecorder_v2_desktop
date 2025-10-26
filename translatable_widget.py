"""
Mixin für Widgets, das tr() mit SimpleTranslator verbindet
"""
from simple_translator import SimpleTranslator


class TranslatableWidget:
    """
    Mixin-Klasse die tr() überschreibt, um SimpleTranslator zu verwenden

    Verwendung:
        class MyWidget(TranslatableWidget, QWidget):
            def __init__(self):
                super().__init__()
                self.label = QLabel(self.tr("Text"))
    """

    def tr(self, text: str, disambiguation: str = None, n: int = -1) -> str:
        """
        Überschreibt Qt's tr() Methode, um SimpleTranslator zu verwenden

        Args:
            text: Der zu übersetzende Text
            disambiguation: Wird ignoriert (für Qt-Kompatibilität)
            n: Wird ignoriert (für Qt-Kompatibilität)

        Returns:
            Übersetzter Text oder Original wenn keine Übersetzung gefunden
        """
        translator = SimpleTranslator.instance()

        # Verwende Klassenname als Context
        context = self.__class__.__name__

        return translator.translate(context, text)
