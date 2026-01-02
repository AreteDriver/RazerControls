"""Hotkey editor widget for configuring profile switch shortcuts."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from crates.profile_schema import HotkeyBinding, ProfileLoader, SettingsManager


class HotkeyCapture(QLineEdit):
    """Line edit that captures key combinations."""

    hotkey_changed = Signal(HotkeyBinding)

    def __init__(self, binding: HotkeyBinding, parent=None):
        super().__init__(parent)
        self.binding = binding
        self.setReadOnly(True)
        self.setPlaceholderText("Click and press keys...")
        self._update_display()
        self._capturing = False

    def _update_display(self) -> None:
        """Update the display text from the binding."""
        self.setText(self.binding.to_display_string())

    def set_binding(self, binding: HotkeyBinding) -> None:
        """Set a new binding."""
        self.binding = binding
        self._update_display()

    def mousePressEvent(self, event) -> None:
        """Start capturing on click."""
        self._capturing = True
        self.setText("Press keys...")
        self.setStyleSheet("background-color: #ffffcc;")
        super().mousePressEvent(event)

    def focusOutEvent(self, event) -> None:
        """Stop capturing on focus loss."""
        self._capturing = False
        self.setStyleSheet("")
        self._update_display()
        super().focusOutEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Capture key press."""
        if not self._capturing:
            super().keyPressEvent(event)
            return

        # Get modifiers
        modifiers = []
        mods = event.modifiers()
        if mods & Qt.KeyboardModifier.ControlModifier:
            modifiers.append("ctrl")
        if mods & Qt.KeyboardModifier.AltModifier:
            modifiers.append("alt")
        if mods & Qt.KeyboardModifier.ShiftModifier:
            modifiers.append("shift")

        # Get the key
        key = event.key()
        key_str = ""

        # Handle special keys
        if Qt.Key.Key_F1 <= key <= Qt.Key.Key_F12:
            key_str = f"f{key - Qt.Key.Key_F1 + 1}"
        elif Qt.Key.Key_0 <= key <= Qt.Key.Key_9:
            key_str = str(key - Qt.Key.Key_0)
        elif Qt.Key.Key_A <= key <= Qt.Key.Key_Z:
            key_str = chr(key).lower()
        elif key == Qt.Key.Key_Escape:
            # Cancel capture
            self._capturing = False
            self.setStyleSheet("")
            self._update_display()
            return
        elif key in (
            Qt.Key.Key_Control,
            Qt.Key.Key_Shift,
            Qt.Key.Key_Alt,
            Qt.Key.Key_Meta,
        ):
            # Just modifiers, keep capturing
            return

        if key_str and modifiers:
            # Valid hotkey captured
            self.binding = HotkeyBinding(
                modifiers=modifiers, key=key_str, enabled=self.binding.enabled
            )
            self._capturing = False
            self.setStyleSheet("")
            self._update_display()
            self.hotkey_changed.emit(self.binding)


class HotkeyEditorWidget(QWidget):
    """Widget for editing hotkey bindings."""

    hotkeys_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings_manager = SettingsManager()
        self.profile_loader = ProfileLoader()
        self._hotkey_widgets: list[tuple[HotkeyCapture, QCheckBox]] = []
        self._init_ui()
        self._load_settings()

    def _init_ui(self) -> None:
        """Initialize the UI."""
        layout = QVBoxLayout(self)

        # Header
        header = QLabel("Configure keyboard shortcuts for quick profile switching.")
        header.setWordWrap(True)
        layout.addWidget(header)

        # Scroll area for hotkeys
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        # Hotkey group
        group = QGroupBox("Profile Hotkeys")
        form = QFormLayout(group)

        # Get profile names
        profile_ids = self.profile_loader.list_profiles()
        profile_names = []
        for pid in profile_ids[:9]:  # Max 9 profiles
            profile = self.profile_loader.load_profile(pid)
            if profile:
                profile_names.append(profile.name)
            else:
                profile_names.append(pid)

        # Pad with empty slots
        while len(profile_names) < 9:
            profile_names.append(f"(Profile {len(profile_names) + 1})")

        # Create hotkey rows
        for i in range(9):
            row = QHBoxLayout()

            # Hotkey capture
            capture = HotkeyCapture(HotkeyBinding())
            capture.setMinimumWidth(150)
            capture.hotkey_changed.connect(lambda b, idx=i: self._on_hotkey_changed(idx, b))
            row.addWidget(capture)

            # Enable checkbox
            enabled = QCheckBox("Enabled")
            enabled.stateChanged.connect(lambda state, idx=i: self._on_enabled_changed(idx, state))
            row.addWidget(enabled)

            self._hotkey_widgets.append((capture, enabled))

            form.addRow(f"{profile_names[i]}:", row)

        scroll_layout.addWidget(group)
        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        # Buttons
        btn_layout = QHBoxLayout()

        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.clicked.connect(self._reset_defaults)
        btn_layout.addWidget(reset_btn)

        btn_layout.addStretch()

        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._save_settings)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def _load_settings(self) -> None:
        """Load current settings into the UI."""
        settings = self.settings_manager.load()
        bindings = settings.hotkeys.profile_hotkeys

        for i, (capture, enabled) in enumerate(self._hotkey_widgets):
            if i < len(bindings):
                capture.set_binding(bindings[i])
                enabled.setChecked(bindings[i].enabled)
            else:
                capture.set_binding(HotkeyBinding())
                enabled.setChecked(False)

    def _on_hotkey_changed(self, index: int, binding: HotkeyBinding) -> None:
        """Handle hotkey change."""
        # Check for conflicts
        for i, (capture, _) in enumerate(self._hotkey_widgets):
            if i != index and capture.binding.key:
                if (
                    capture.binding.key == binding.key
                    and set(capture.binding.modifiers) == set(binding.modifiers)
                ):
                    QMessageBox.warning(
                        self,
                        "Conflict",
                        f"This hotkey is already assigned to profile {i + 1}.",
                    )
                    # Revert
                    self._load_settings()
                    return

    def _on_enabled_changed(self, index: int, state: int) -> None:
        """Handle enabled checkbox change."""
        capture, _ = self._hotkey_widgets[index]
        capture.binding.enabled = state == Qt.CheckState.Checked.value

    def _reset_defaults(self) -> None:
        """Reset hotkeys to defaults."""
        reply = QMessageBox.question(
            self,
            "Reset Hotkeys",
            "Reset all hotkeys to defaults (Ctrl+Shift+1-9)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.settings_manager.reset_hotkeys()
            self._load_settings()
            self.hotkeys_changed.emit()

    def _save_settings(self) -> None:
        """Save current settings."""
        settings = self.settings_manager.load()

        for i, (capture, enabled) in enumerate(self._hotkey_widgets):
            if i < len(settings.hotkeys.profile_hotkeys):
                binding = capture.binding
                binding.enabled = enabled.isChecked()
                settings.hotkeys.profile_hotkeys[i] = binding

        if self.settings_manager.save():
            QMessageBox.information(self, "Saved", "Hotkey settings saved.")
            self.hotkeys_changed.emit()
        else:
            QMessageBox.warning(self, "Error", "Failed to save settings.")


class HotkeyEditorDialog(QDialog):
    """Dialog for editing hotkeys."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configure Hotkeys")
        self.setMinimumSize(400, 450)

        layout = QVBoxLayout(self)
        self.editor = HotkeyEditorWidget()
        layout.addWidget(self.editor)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
