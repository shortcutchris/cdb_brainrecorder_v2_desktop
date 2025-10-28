"""
Splash Screen Widget als Overlay für MainWindow
"""
import sys
import os
from PySide6.QtWidgets import QWidget, QGraphicsOpacityEffect
from PySide6.QtGui import QPainter, QColor, QPixmap, QFont
from PySide6.QtCore import Qt, QPropertyAnimation, Signal


def resource_path(relative_path):
    """Gibt den absoluten Pfad zu einer Ressource zurück (PyInstaller-kompatibel)"""
    try:
        # PyInstaller erstellt einen temp Ordner und speichert den Pfad in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # Wenn nicht gebundled, nutze den aktuellen Ordner
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


class SplashWidget(QWidget):
    """Splash Screen als Overlay Widget"""

    finished = Signal()  # Emitted wenn Fade-out abgeschlossen

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)

        # Opacity Effect für Fade-out Animation
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.opacity_effect.setOpacity(1.0)
        self.setGraphicsEffect(self.opacity_effect)

        # Logo laden (PyInstaller-kompatibel)
        logo_path = resource_path("icon.png")
        self.logo = QPixmap(logo_path)

    def paintEvent(self, event):
        """Zeichnet den Splash Screen"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Hintergrund: Dunkelblau wie Logo
        painter.fillRect(self.rect(), QColor("#0c1e2e"))

        # Logo zentriert zeichnen
        if not self.logo.isNull():
            logo_size = 300
            logo_scaled = self.logo.scaled(
                logo_size, logo_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            x = (self.width() - logo_scaled.width()) // 2
            y = (self.height() - logo_scaled.height()) // 2 - 40  # Etwas nach oben
            painter.drawPixmap(x, y, logo_scaled)

        # Text unter Logo
        painter.setPen(QColor("#ffffff"))
        font = QFont("Arial", 16, QFont.Weight.Bold)
        painter.setFont(font)

        text_y = self.height() // 2 + 180
        painter.drawText(
            0, text_y, self.width(), 100,
            Qt.AlignmentFlag.AlignCenter,
            "Corporate Digital Brain\nDesktop Recorder"
        )

    def fade_out(self, duration=500):
        """Startet Fade-out Animation"""
        self.animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.animation.setDuration(duration)
        self.animation.setStartValue(1.0)
        self.animation.setEndValue(0.0)
        self.animation.finished.connect(self._on_animation_finished)
        self.animation.start()

    def _on_animation_finished(self):
        """Wird aufgerufen wenn Animation fertig ist"""
        self.finished.emit()
        self.close()  # Widget schließen
