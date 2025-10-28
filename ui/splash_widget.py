"""
Splash Screen Widget als Overlay für MainWindow
"""
import sys
import os
from PySide6.QtWidgets import QWidget, QGraphicsOpacityEffect
from PySide6.QtGui import QPainter, QColor, QPixmap, QFont
from PySide6.QtCore import Qt, QPropertyAnimation, Signal, Property, QTimer


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

        # Logo Opacity für Fade-in Animation (startet unsichtbar)
        self._logo_opacity = 0.0

    def paintEvent(self, event):
        """Zeichnet den Splash Screen"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Hintergrund: Dunkelblau wie Logo
        painter.fillRect(self.rect(), QColor("#000e22"))

        # Logo perfekt zentriert zeichnen mit aktueller Opacity
        if not self.logo.isNull():
            logo_size = 300
            logo_scaled = self.logo.scaled(
                logo_size, logo_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            x = (self.width() - logo_scaled.width()) // 2
            y = (self.height() - logo_scaled.height()) // 2

            # Setze Opacity für Logo
            painter.setOpacity(self._logo_opacity)
            painter.drawPixmap(x, y, logo_scaled)
            painter.setOpacity(1.0)  # Zurücksetzen

    def get_logo_opacity(self) -> float:
        """Getter für logo_opacity Property"""
        return self._logo_opacity

    def set_logo_opacity(self, value: float):
        """Setter für logo_opacity Property"""
        self._logo_opacity = value
        self.update()  # Widget neu zeichnen

    # Qt Property für Animation-System
    logo_opacity = Property(float, get_logo_opacity, set_logo_opacity)

    def start_animation(self):
        """Startet die 3-Phasen Animationssequenz"""
        # Phase 1: Logo fade-in (800ms)
        self.logo_fade_in = QPropertyAnimation(self, b"logo_opacity")
        self.logo_fade_in.setDuration(800)
        self.logo_fade_in.setStartValue(0.0)
        self.logo_fade_in.setEndValue(1.0)
        self.logo_fade_in.finished.connect(self._on_logo_fade_in_finished)
        self.logo_fade_in.start()

    def _on_logo_fade_in_finished(self):
        """Phase 2: Nach Logo fade-in, warte 1500ms, dann Phase 3"""
        QTimer.singleShot(1500, lambda: self.fade_out(500))

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
