"""
Corporate Digital Brain Desktop Recorder
Main Entry Point
"""
import sys
import os
import platform
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from ui.main_window import MainWindow


def main():
    """Hauptfunktion"""
    app = QApplication(sys.argv)
    app.setApplicationName("Corporate Digital Brain Desktop Recorder")
    app.setOrganizationName("Corporate Digital Brain")
    app.setWindowIcon(QIcon("icon.png"))

    # Hauptfenster erstellen
    window = MainWindow()

    # Auto-Fullscreen auf Raspberry Pi oder via Environment Variable
    is_raspberry_pi = platform.machine().startswith('aarch') or platform.machine().startswith('arm')
    fullscreen_env = os.getenv('FULLSCREEN', '').lower() == 'true'

    # Starte im Fullscreen-Modus wenn:
    # - Auf Raspberry Pi (außer FULLSCREEN=false explizit gesetzt)
    # - Oder FULLSCREEN=true Environment Variable gesetzt
    if (is_raspberry_pi and os.getenv('FULLSCREEN', '').lower() != 'false') or fullscreen_env:
        window.showFullScreen()
    else:
        window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
