"""
Audio Sessions - Desktop App
Main Entry Point
"""
import sys
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow


def main():
    """Hauptfunktion"""
    app = QApplication(sys.argv)
    app.setApplicationName("Audio Sessions")
    app.setOrganizationName("Audio Sessions")

    # Hauptfenster erstellen und anzeigen
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
