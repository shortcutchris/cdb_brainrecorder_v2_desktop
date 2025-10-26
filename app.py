"""
Corporate Digital Brain Desktop Recorder
Main Entry Point
"""
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from ui.main_window import MainWindow


def main():
    """Hauptfunktion"""
    app = QApplication(sys.argv)
    app.setApplicationName("Corporate Digital Brain Desktop Recorder")
    app.setOrganizationName("Corporate Digital Brain")
    app.setWindowIcon(QIcon("icon.png"))

    # Hauptfenster erstellen und anzeigen
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
