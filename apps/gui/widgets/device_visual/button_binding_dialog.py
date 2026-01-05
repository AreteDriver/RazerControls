"""Dialog for configuring button key bindings."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from crates.device_layouts import ButtonShape

# Common key bindings organized by category
COMMON_KEYS = {
    "Mouse": [
        ("Left Click", "BTN_LEFT"),
        ("Right Click", "BTN_RIGHT"),
        ("Middle Click", "BTN_MIDDLE"),
        ("Forward", "BTN_FORWARD"),
        ("Back", "BTN_BACK"),
        ("Side", "BTN_SIDE"),
        ("Extra", "BTN_EXTRA"),
    ],
    "Modifiers": [
        ("Left Ctrl", "KEY_LEFTCTRL"),
        ("Right Ctrl", "KEY_RIGHTCTRL"),
        ("Left Shift", "KEY_LEFTSHIFT"),
        ("Right Shift", "KEY_RIGHTSHIFT"),
        ("Left Alt", "KEY_LEFTALT"),
        ("Right Alt", "KEY_RIGHTALT"),
        ("Left Super", "KEY_LEFTMETA"),
        ("Right Super", "KEY_RIGHTMETA"),
    ],
    "Navigation": [
        ("Up", "KEY_UP"),
        ("Down", "KEY_DOWN"),
        ("Left", "KEY_LEFT"),
        ("Right", "KEY_RIGHT"),
        ("Page Up", "KEY_PAGEUP"),
        ("Page Down", "KEY_PAGEDOWN"),
        ("Home", "KEY_HOME"),
        ("End", "KEY_END"),
    ],
    "Function": [
        ("F1", "KEY_F1"),
        ("F2", "KEY_F2"),
        ("F3", "KEY_F3"),
        ("F4", "KEY_F4"),
        ("F5", "KEY_F5"),
        ("F6", "KEY_F6"),
        ("F7", "KEY_F7"),
        ("F8", "KEY_F8"),
        ("F9", "KEY_F9"),
        ("F10", "KEY_F10"),
        ("F11", "KEY_F11"),
        ("F12", "KEY_F12"),
    ],
    "Media": [
        ("Play/Pause", "KEY_PLAYPAUSE"),
        ("Stop", "KEY_STOPCD"),
        ("Next Track", "KEY_NEXTSONG"),
        ("Prev Track", "KEY_PREVIOUSSONG"),
        ("Volume Up", "KEY_VOLUMEUP"),
        ("Volume Down", "KEY_VOLUMEDOWN"),
        ("Mute", "KEY_MUTE"),
    ],
    "Common": [
        ("Escape", "KEY_ESC"),
        ("Tab", "KEY_TAB"),
        ("Space", "KEY_SPACE"),
        ("Enter", "KEY_ENTER"),
        ("Backspace", "KEY_BACKSPACE"),
        ("Delete", "KEY_DELETE"),
        ("Insert", "KEY_INSERT"),
        ("Print Screen", "KEY_SYSRQ"),
    ],
}

# Qt key to evdev key mapping for key capture
QT_TO_EVDEV = {
    Qt.Key.Key_Escape: "KEY_ESC",
    Qt.Key.Key_Tab: "KEY_TAB",
    Qt.Key.Key_Backspace: "KEY_BACKSPACE",
    Qt.Key.Key_Return: "KEY_ENTER",
    Qt.Key.Key_Enter: "KEY_ENTER",
    Qt.Key.Key_Insert: "KEY_INSERT",
    Qt.Key.Key_Delete: "KEY_DELETE",
    Qt.Key.Key_Home: "KEY_HOME",
    Qt.Key.Key_End: "KEY_END",
    Qt.Key.Key_PageUp: "KEY_PAGEUP",
    Qt.Key.Key_PageDown: "KEY_PAGEDOWN",
    Qt.Key.Key_Left: "KEY_LEFT",
    Qt.Key.Key_Up: "KEY_UP",
    Qt.Key.Key_Right: "KEY_RIGHT",
    Qt.Key.Key_Down: "KEY_DOWN",
    Qt.Key.Key_Space: "KEY_SPACE",
    Qt.Key.Key_F1: "KEY_F1",
    Qt.Key.Key_F2: "KEY_F2",
    Qt.Key.Key_F3: "KEY_F3",
    Qt.Key.Key_F4: "KEY_F4",
    Qt.Key.Key_F5: "KEY_F5",
    Qt.Key.Key_F6: "KEY_F6",
    Qt.Key.Key_F7: "KEY_F7",
    Qt.Key.Key_F8: "KEY_F8",
    Qt.Key.Key_F9: "KEY_F9",
    Qt.Key.Key_F10: "KEY_F10",
    Qt.Key.Key_F11: "KEY_F11",
    Qt.Key.Key_F12: "KEY_F12",
    Qt.Key.Key_A: "KEY_A",
    Qt.Key.Key_B: "KEY_B",
    Qt.Key.Key_C: "KEY_C",
    Qt.Key.Key_D: "KEY_D",
    Qt.Key.Key_E: "KEY_E",
    Qt.Key.Key_F: "KEY_F",
    Qt.Key.Key_G: "KEY_G",
    Qt.Key.Key_H: "KEY_H",
    Qt.Key.Key_I: "KEY_I",
    Qt.Key.Key_J: "KEY_J",
    Qt.Key.Key_K: "KEY_K",
    Qt.Key.Key_L: "KEY_L",
    Qt.Key.Key_M: "KEY_M",
    Qt.Key.Key_N: "KEY_N",
    Qt.Key.Key_O: "KEY_O",
    Qt.Key.Key_P: "KEY_P",
    Qt.Key.Key_Q: "KEY_Q",
    Qt.Key.Key_R: "KEY_R",
    Qt.Key.Key_S: "KEY_S",
    Qt.Key.Key_T: "KEY_T",
    Qt.Key.Key_U: "KEY_U",
    Qt.Key.Key_V: "KEY_V",
    Qt.Key.Key_W: "KEY_W",
    Qt.Key.Key_X: "KEY_X",
    Qt.Key.Key_Y: "KEY_Y",
    Qt.Key.Key_Z: "KEY_Z",
    Qt.Key.Key_0: "KEY_0",
    Qt.Key.Key_1: "KEY_1",
    Qt.Key.Key_2: "KEY_2",
    Qt.Key.Key_3: "KEY_3",
    Qt.Key.Key_4: "KEY_4",
    Qt.Key.Key_5: "KEY_5",
    Qt.Key.Key_6: "KEY_6",
    Qt.Key.Key_7: "KEY_7",
    Qt.Key.Key_8: "KEY_8",
    Qt.Key.Key_9: "KEY_9",
}


class KeyCaptureWidget(QLineEdit):
    """Line edit that captures key presses."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setPlaceholderText("Click and press a key...")
        self._captured_key: str | None = None

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Capture key press and convert to evdev code."""
        key = event.key()

        # Check for modifier keys
        if key == Qt.Key.Key_Control:
            self._captured_key = "KEY_LEFTCTRL"
        elif key == Qt.Key.Key_Shift:
            self._captured_key = "KEY_LEFTSHIFT"
        elif key == Qt.Key.Key_Alt:
            self._captured_key = "KEY_LEFTALT"
        elif key == Qt.Key.Key_Meta:
            self._captured_key = "KEY_LEFTMETA"
        elif key in QT_TO_EVDEV:
            self._captured_key = QT_TO_EVDEV[key]
        else:
            # Try to get text representation
            text = event.text().upper()
            if text and text.isalnum():
                if text.isdigit():
                    self._captured_key = f"KEY_{text}"
                else:
                    self._captured_key = f"KEY_{text}"
            else:
                return

        self.setText(self._captured_key)

    def get_key(self) -> str | None:
        """Get the captured key code."""
        return self._captured_key

    def set_key(self, key: str | None) -> None:
        """Set the key code."""
        self._captured_key = key
        self.setText(key or "")


class ButtonBindingDialog(QDialog):
    """Dialog for configuring button bindings."""

    def __init__(
        self,
        button: ButtonShape,
        current_binding: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._button = button
        self._binding: str | None = current_binding

        self.setWindowTitle(f"Configure: {button.label}")
        self.setMinimumWidth(400)
        self._setup_ui()

        if current_binding:
            self._manual_input.setText(current_binding)

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)

        # Button info
        info_label = QLabel(f"Button: <b>{self._button.label}</b> ({self._button.id})")
        layout.addWidget(info_label)

        if self._button.input_code:
            default_label = QLabel(f"Default: {self._button.input_code}")
            default_label.setStyleSheet("color: gray;")
            layout.addWidget(default_label)

        # Tab widget for different binding methods
        tabs = QTabWidget()
        layout.addWidget(tabs)

        # Tab 1: Common bindings
        common_tab = QWidget()
        common_layout = QVBoxLayout(common_tab)

        self._category_combo = QComboBox()
        self._category_combo.addItems(list(COMMON_KEYS.keys()))
        self._category_combo.currentTextChanged.connect(self._update_key_list)
        common_layout.addWidget(self._category_combo)

        self._key_combo = QComboBox()
        common_layout.addWidget(self._key_combo)
        self._update_key_list(self._category_combo.currentText())

        use_common_btn = QPushButton("Use Selected")
        use_common_btn.clicked.connect(self._use_common_binding)
        common_layout.addWidget(use_common_btn)
        common_layout.addStretch()

        tabs.addTab(common_tab, "Common Keys")

        # Tab 2: Key capture
        capture_tab = QWidget()
        capture_layout = QVBoxLayout(capture_tab)

        capture_layout.addWidget(QLabel("Press any key to capture:"))
        self._key_capture = KeyCaptureWidget()
        capture_layout.addWidget(self._key_capture)

        use_capture_btn = QPushButton("Use Captured Key")
        use_capture_btn.clicked.connect(self._use_captured_binding)
        capture_layout.addWidget(use_capture_btn)
        capture_layout.addStretch()

        tabs.addTab(capture_tab, "Capture Key")

        # Tab 3: Manual entry
        manual_tab = QWidget()
        manual_layout = QFormLayout(manual_tab)

        self._manual_input = QLineEdit()
        self._manual_input.setPlaceholderText("e.g., KEY_A, BTN_LEFT, KEY_LEFTCTRL")
        manual_layout.addRow("Key Code:", self._manual_input)

        tabs.addTab(manual_tab, "Manual")

        # Current binding display
        current_layout = QHBoxLayout()
        current_layout.addWidget(QLabel("Binding:"))
        self._current_label = QLabel(self._binding or "(none)")
        self._current_label.setStyleSheet("font-weight: bold;")
        current_layout.addWidget(self._current_label)
        current_layout.addStretch()

        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self._clear_binding)
        current_layout.addWidget(clear_btn)
        layout.addLayout(current_layout)

        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _update_key_list(self, category: str) -> None:
        """Update key combo based on category."""
        self._key_combo.clear()
        for label, code in COMMON_KEYS.get(category, []):
            self._key_combo.addItem(label, code)

    def _use_common_binding(self) -> None:
        """Use the selected common binding."""
        code = self._key_combo.currentData()
        if code:
            self._binding = code
            self._current_label.setText(code)
            self._manual_input.setText(code)

    def _use_captured_binding(self) -> None:
        """Use the captured key binding."""
        key = self._key_capture.get_key()
        if key:
            self._binding = key
            self._current_label.setText(key)
            self._manual_input.setText(key)

    def _clear_binding(self) -> None:
        """Clear the current binding."""
        self._binding = None
        self._current_label.setText("(none)")
        self._manual_input.clear()
        self._key_capture.set_key(None)

    def _on_accept(self) -> None:
        """Accept the dialog with current binding."""
        # Check manual input first
        manual = self._manual_input.text().strip()
        if manual:
            self._binding = manual
        self.accept()

    def get_binding(self) -> str | None:
        """Get the configured binding."""
        return self._binding
