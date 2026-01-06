"""Main GUI application entry point."""

import atexit
import fcntl
import os
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from crates.profile_schema import ProfileLoader

from .main_window import MainWindow

# Single-instance lock
LOCK_FILE = Path.home() / ".cache" / "razer-control-center.lock"
_lock_file_handle = None


def acquire_instance_lock() -> bool:
    """Try to acquire single-instance lock. Returns True if acquired."""
    global _lock_file_handle
    try:
        LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
        _lock_file_handle = open(LOCK_FILE, "w")
        fcntl.flock(_lock_file_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        _lock_file_handle.write(str(os.getpid()))
        _lock_file_handle.flush()
        return True
    except OSError:
        if _lock_file_handle:
            _lock_file_handle.close()
            _lock_file_handle = None
        return False


def release_instance_lock():
    """Release the single-instance lock."""
    global _lock_file_handle
    if _lock_file_handle:
        try:
            fcntl.flock(_lock_file_handle.fileno(), fcntl.LOCK_UN)
            _lock_file_handle.close()
        except OSError:
            pass
        _lock_file_handle = None


def main():
    """Main entry point for the GUI application."""
    # Single-instance check
    if not acquire_instance_lock():
        app = QApplication(sys.argv)
        QMessageBox.warning(
            None,
            "Already Running",
            "Razer Control Center is already running.\n\n"
            "Check your system tray for the existing instance.",
        )
        sys.exit(1)

    atexit.register(release_instance_lock)

    # High DPI scaling is enabled by default in Qt6
    app = QApplication(sys.argv)
    app.setApplicationName("Razer Control Center")
    app.setOrganizationName("RazerControlCenter")

    # Apply dark theme
    app.setStyle("Fusion")
    from .theme import apply_dark_theme

    apply_dark_theme(app)

    # Check if first run (no profiles exist)
    loader = ProfileLoader()
    if not loader.list_profiles():
        from .widgets.setup_wizard import SetupWizard

        wizard = SetupWizard()
        if wizard.exec() != QDialog.DialogCode.Accepted:
            sys.exit(0)  # User cancelled setup

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
