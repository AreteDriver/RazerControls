"""App matching widget for automatic profile switching."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from crates.profile_schema import Profile
from services.app_watcher import AppWatcher


class AddPatternDialog(QDialog):
    """Dialog for adding a new app pattern."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add App Pattern")
        self.setMinimumWidth(350)

        layout = QFormLayout(self)

        # Pattern input
        self.pattern_edit = QLineEdit()
        self.pattern_edit.setPlaceholderText("e.g., firefox, steam*, *.exe")
        layout.addRow("Pattern:", self.pattern_edit)

        # Help text
        help_text = QLabel(
            "Patterns can use:\n"
            "• Exact match: firefox\n"
            "• Wildcards: steam*, *.exe\n"
            "• Substring: chrome (matches com.google.chrome)"
        )
        help_text.setStyleSheet("color: #888888; font-size: 11px;")
        layout.addRow(help_text)

        # Buttons
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addRow(self.buttons)

    def get_pattern(self) -> str:
        """Get the entered pattern."""
        return str(self.pattern_edit.text()).strip()


class AppMatcherWidget(QWidget):
    """Widget for configuring app-based profile switching."""

    patterns_changed = Signal()  # Emitted when patterns change

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_profile: Profile | None = None
        self._setup_ui()

    def _setup_ui(self):
        """Set up the widget UI."""
        layout = QVBoxLayout(self)

        # App patterns group
        patterns_group = QGroupBox("App Patterns")
        patterns_layout = QVBoxLayout(patterns_group)

        # Description
        desc = QLabel(
            "When any of these applications are focused, this profile will activate automatically."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #aaaaaa; margin-bottom: 8px;")
        patterns_layout.addWidget(desc)

        # Pattern list
        self.pattern_list = QListWidget()
        self.pattern_list.setMaximumHeight(150)
        patterns_layout.addWidget(self.pattern_list)

        # Buttons
        btn_layout = QHBoxLayout()

        self.add_btn = QPushButton("Add Pattern")
        self.add_btn.clicked.connect(self._add_pattern)
        btn_layout.addWidget(self.add_btn)

        self.remove_btn = QPushButton("Remove")
        self.remove_btn.clicked.connect(self._remove_pattern)
        self.remove_btn.setEnabled(False)
        btn_layout.addWidget(self.remove_btn)

        btn_layout.addStretch()
        patterns_layout.addLayout(btn_layout)

        layout.addWidget(patterns_group)

        # Default profile checkbox
        default_group = QGroupBox("Default Profile")
        default_layout = QVBoxLayout(default_group)

        self.default_check = QCheckBox("Use as default when no app matches")
        self.default_check.toggled.connect(self._on_default_changed)
        default_layout.addWidget(self.default_check)

        default_desc = QLabel(
            "Only one profile can be the default. When the focused app doesn't match "
            "any pattern, the default profile will be used."
        )
        default_desc.setWordWrap(True)
        default_desc.setStyleSheet("color: #888888; font-size: 11px;")
        default_layout.addWidget(default_desc)

        layout.addWidget(default_group)

        # Test section
        test_group = QGroupBox("Test Active Window")
        test_layout = QVBoxLayout(test_group)

        self.test_btn = QPushButton("Detect Current Window")
        self.test_btn.clicked.connect(self._test_detection)
        test_layout.addWidget(self.test_btn)

        self.test_result = QLabel("Click to detect the currently focused application")
        self.test_result.setWordWrap(True)
        self.test_result.setStyleSheet(
            "color: #888888; padding: 8px; background: #1a1a1a; border-radius: 4px;"
        )
        test_layout.addWidget(self.test_result)

        layout.addWidget(test_group)

        layout.addStretch()

        # Connect selection change
        self.pattern_list.currentRowChanged.connect(self._on_selection_changed)

    def load_profile(self, profile: Profile):
        """Load a profile's app matching settings."""
        self.current_profile = profile
        self._refresh_ui()

    def _refresh_ui(self):
        """Refresh UI from current profile."""
        self.pattern_list.clear()

        if not self.current_profile:
            self.default_check.setChecked(False)
            self.add_btn.setEnabled(False)
            return

        self.add_btn.setEnabled(True)

        # Load patterns
        for pattern in self.current_profile.match_process_names:
            item = QListWidgetItem(pattern)
            self.pattern_list.addItem(item)

        # Load default setting
        self.default_check.setChecked(self.current_profile.is_default)

    def _on_selection_changed(self, row: int):
        """Handle pattern selection change."""
        self.remove_btn.setEnabled(row >= 0)

    def _add_pattern(self):
        """Add a new app pattern."""
        if not self.current_profile:
            return

        dialog = AddPatternDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            pattern = dialog.get_pattern()
            if pattern:
                # Check for duplicates
                if pattern.lower() in [p.lower() for p in self.current_profile.match_process_names]:
                    QMessageBox.warning(self, "Duplicate", "This pattern already exists.")
                    return

                self.current_profile.match_process_names.append(pattern)
                self._refresh_ui()
                self.patterns_changed.emit()

    def _remove_pattern(self):
        """Remove the selected pattern."""
        if not self.current_profile:
            return

        item = self.pattern_list.currentItem()
        if not item:
            return

        pattern = item.text()
        if pattern in self.current_profile.match_process_names:
            self.current_profile.match_process_names.remove(pattern)
            self._refresh_ui()
            self.patterns_changed.emit()

    def _on_default_changed(self, checked: bool):
        """Handle default checkbox change."""
        if not self.current_profile:
            return

        self.current_profile.is_default = checked
        self.patterns_changed.emit()

    def _test_detection(self):
        """Test window detection."""
        try:
            watcher = AppWatcher()

            if not watcher._backend:
                self.test_result.setText(
                    "No backend available.\n\n"
                    "For X11: Install xdotool\n"
                    "For Wayland: Currently only GNOME is supported"
                )
                self.test_result.setStyleSheet(
                    "color: #ff6b6b; padding: 8px; background: #1a1a1a; border-radius: 4px;"
                )
                return

            window_info = watcher._backend.get_active_window()

            if window_info:
                result = (
                    f"Backend: {watcher.backend_name}\n"
                    f"PID: {window_info.pid or 'Unknown'}\n"
                    f"Process: {window_info.process_name or 'Unknown'}\n"
                    f"Class: {window_info.window_class or 'Unknown'}\n"
                    f"Title: {window_info.window_title or 'Unknown'}"
                )
                self.test_result.setText(result)
                self.test_result.setStyleSheet(
                    "color: #2da05a; padding: 8px; background: #1a1a1a; border-radius: 4px;"
                )
            else:
                self.test_result.setText("Could not detect active window")
                self.test_result.setStyleSheet(
                    "color: #ff6b6b; padding: 8px; background: #1a1a1a; border-radius: 4px;"
                )

        except Exception as e:
            self.test_result.setText(f"Error: {e}")
            self.test_result.setStyleSheet(
                "color: #ff6b6b; padding: 8px; background: #1a1a1a; border-radius: 4px;"
            )

    def clear(self):
        """Clear the widget."""
        self.current_profile = None
        self.pattern_list.clear()
        self.default_check.setChecked(False)
        self.add_btn.setEnabled(False)
        self.remove_btn.setEnabled(False)
