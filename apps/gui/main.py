"""Main GUI application entry point."""

import sys

from PySide6.QtWidgets import QApplication

from .main_window import MainWindow


def main():
    """Main entry point for the GUI application."""
    # High DPI scaling is enabled by default in Qt6
    app = QApplication(sys.argv)
    app.setApplicationName("Razer Control Center")
    app.setOrganizationName("RazerControlCenter")

    # Apply dark theme
    app.setStyle("Fusion")
    from .theme import apply_dark_theme
    apply_dark_theme(app)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
