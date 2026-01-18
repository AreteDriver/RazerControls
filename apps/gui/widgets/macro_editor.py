"""Macro editor widget for visual macro creation and editing."""

import uuid

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QComboBox,
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
    QProgressBar,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from crates.keycode_map import get_all_schema_keys
from crates.profile_schema import MacroAction, MacroStep, MacroStepType


class RecordingWorker(QThread):
    """Background worker for recording macros from input devices."""

    step_recorded = Signal(str)  # Key name for live display
    recording_finished = Signal(object)  # MacroAction result
    error_occurred = Signal(str)  # Error message
    progress_update = Signal(int)  # Seconds elapsed

    def __init__(
        self,
        device_path: str,
        stop_key: str = "ESC",
        timeout: int = 60,
        parent=None,
    ):
        super().__init__(parent)
        self.device_path = device_path
        self.stop_key = stop_key
        self.timeout = timeout
        self._should_stop = False

    def run(self):
        """Run the recording in background thread."""
        try:
            # Import here to avoid issues if evdev not installed
            from services.macro_engine.recorder import DeviceMacroRecorder, RecordedEvent

            recorder = DeviceMacroRecorder(
                device_path=self.device_path,
                stop_key=self.stop_key,
            )

            def on_event(event: RecordedEvent):
                action = "↓" if event.value == 1 else "↑"
                self.step_recorded.emit(f"{event.key_name} {action}")

            macro = recorder.record_from_device(
                timeout=float(self.timeout),
                on_event=on_event,
            )

            self.recording_finished.emit(macro)

        except PermissionError:
            self.error_occurred.emit(
                "Permission denied. Add yourself to the 'input' group:\n"
                "  sudo usermod -aG input $USER\n"
                "Then log out and back in."
            )
        except FileNotFoundError:
            self.error_occurred.emit(f"Device not found: {self.device_path}")
        except Exception as e:
            self.error_occurred.emit(f"Recording error: {e}")

    def stop(self):
        """Signal the worker to stop."""
        self._should_stop = True


class RecordingDialog(QDialog):
    """Dialog for configuring and running macro recording."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Record Macro from Device")
        self.setMinimumWidth(450)
        self.setMinimumHeight(350)

        self._worker: RecordingWorker | None = None
        self._recorded_macro: MacroAction | None = None

        self._setup_ui()
        self._populate_devices()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Device selection
        device_group = QGroupBox("Device Settings")
        device_layout = QFormLayout(device_group)

        self.device_combo = QComboBox()
        device_layout.addRow("Input Device:", self.device_combo)

        self.stop_key_combo = QComboBox()
        self.stop_key_combo.addItems(["ESC", "F12", "PAUSE", "SCROLLLOCK"])
        self.stop_key_combo.setEditable(True)
        device_layout.addRow("Stop Key:", self.stop_key_combo)

        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(10, 300)
        self.timeout_spin.setValue(60)
        self.timeout_spin.setSuffix(" seconds")
        device_layout.addRow("Timeout:", self.timeout_spin)

        layout.addWidget(device_group)

        # Recording status
        status_group = QGroupBox("Recording")
        status_layout = QVBoxLayout(status_group)

        self.status_label = QLabel("Ready to record")
        self.status_label.setStyleSheet("font-weight: bold;")
        status_layout.addWidget(self.status_label)

        self.key_log = QTextEdit()
        self.key_log.setReadOnly(True)
        self.key_log.setMaximumHeight(120)
        self.key_log.setPlaceholderText("Recorded keys will appear here...")
        status_layout.addWidget(self.key_log)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        status_layout.addWidget(self.progress_bar)

        layout.addWidget(status_group)

        # Buttons
        btn_layout = QHBoxLayout()

        self.start_btn = QPushButton("Start Recording")
        self.start_btn.clicked.connect(self._start_recording)
        btn_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self._stop_recording)
        self.stop_btn.setEnabled(False)
        btn_layout.addWidget(self.stop_btn)

        btn_layout.addStretch()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        self.accept_btn = QPushButton("Use Recording")
        self.accept_btn.clicked.connect(self.accept)
        self.accept_btn.setEnabled(False)
        btn_layout.addWidget(self.accept_btn)

        layout.addLayout(btn_layout)

    def _populate_devices(self):
        """Find available input devices."""
        self.device_combo.clear()

        try:
            from evdev import InputDevice, ecodes, list_devices

            for path in list_devices():
                try:
                    dev = InputDevice(path)
                    caps = dev.capabilities()
                    # Only show devices with key events
                    if ecodes.EV_KEY in caps:
                        name = dev.name or "Unknown"
                        self.device_combo.addItem(f"{name} ({path})", path)
                except OSError:
                    continue

        except ImportError:
            self.device_combo.addItem("evdev not installed", None)
            self.start_btn.setEnabled(False)

        if self.device_combo.count() == 0:
            self.device_combo.addItem("No input devices found", None)
            self.start_btn.setEnabled(False)

    def _start_recording(self):
        """Start the recording worker."""
        device_path = self.device_combo.currentData()
        if not device_path:
            QMessageBox.warning(self, "Error", "Please select a valid input device.")
            return

        self.key_log.clear()
        self.status_label.setText("Recording... Press keys on your device")
        self.status_label.setStyleSheet("color: red; font-weight: bold;")
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.device_combo.setEnabled(False)
        self.stop_key_combo.setEnabled(False)
        self.timeout_spin.setEnabled(False)

        stop_key = self.stop_key_combo.currentText()

        self._worker = RecordingWorker(
            device_path=device_path,
            stop_key=stop_key,
            timeout=self.timeout_spin.value(),
            parent=self,
        )
        self._worker.step_recorded.connect(self._on_step_recorded)
        self._worker.recording_finished.connect(self._on_recording_finished)
        self._worker.error_occurred.connect(self._on_error)
        self._worker.start()

    def _stop_recording(self):
        """Stop the recording worker."""
        if self._worker and self._worker.isRunning():
            self._worker.stop()
            self._worker.wait(2000)

    def _on_step_recorded(self, key_text: str):
        """Handle a key being recorded."""
        self.key_log.append(key_text)
        # Auto-scroll to bottom
        scrollbar = self.key_log.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _on_recording_finished(self, macro: MacroAction):
        """Handle recording completion."""
        self._recorded_macro = macro
        step_count = len(macro.steps) if macro else 0

        self.status_label.setText(f"Recording complete: {step_count} steps")
        self.status_label.setStyleSheet("color: green; font-weight: bold;")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.device_combo.setEnabled(True)
        self.stop_key_combo.setEnabled(True)
        self.timeout_spin.setEnabled(True)
        self.accept_btn.setEnabled(step_count > 0)

    def _on_error(self, error_msg: str):
        """Handle recording error."""
        self.status_label.setText("Error")
        self.status_label.setStyleSheet("color: red; font-weight: bold;")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.device_combo.setEnabled(True)
        self.stop_key_combo.setEnabled(True)
        self.timeout_spin.setEnabled(True)

        QMessageBox.critical(self, "Recording Error", error_msg)

    def get_recorded_macro(self) -> MacroAction | None:
        """Get the recorded macro."""
        return self._recorded_macro


class StepEditorDialog(QDialog):
    """Dialog for editing a single macro step."""

    def __init__(self, step: MacroStep | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Macro Step")
        self.setMinimumWidth(350)

        self._step = step
        self._setup_ui()

        if step:
            self._load_step(step)

    def _setup_ui(self):
        layout = QFormLayout(self)

        # Step type
        self.type_combo = QComboBox()
        self.type_combo.addItem("Key Press", MacroStepType.KEY_PRESS)
        self.type_combo.addItem("Key Down", MacroStepType.KEY_DOWN)
        self.type_combo.addItem("Key Up", MacroStepType.KEY_UP)
        self.type_combo.addItem("Delay", MacroStepType.DELAY)
        self.type_combo.addItem("Type Text", MacroStepType.TEXT)
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        layout.addRow("Type:", self.type_combo)

        # Key selector (for key actions)
        self.key_combo = QComboBox()
        self.key_combo.setEditable(True)
        for key in sorted(get_all_schema_keys()):
            self.key_combo.addItem(key)
        layout.addRow("Key:", self.key_combo)

        # Delay input (for delay actions)
        self.delay_spin = QSpinBox()
        self.delay_spin.setRange(1, 10000)
        self.delay_spin.setValue(100)
        self.delay_spin.setSuffix(" ms")
        layout.addRow("Delay:", self.delay_spin)

        # Text input (for text actions)
        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("Text to type...")
        layout.addRow("Text:", self.text_input)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

        self._on_type_changed()

    def _on_type_changed(self):
        """Show/hide fields based on step type."""
        step_type = self.type_combo.currentData()

        is_key = step_type in (
            MacroStepType.KEY_PRESS,
            MacroStepType.KEY_DOWN,
            MacroStepType.KEY_UP,
        )
        is_delay = step_type == MacroStepType.DELAY
        is_text = step_type == MacroStepType.TEXT

        self.key_combo.setVisible(is_key)
        self.delay_spin.setVisible(is_delay)
        self.text_input.setVisible(is_text)

    def _load_step(self, step: MacroStep):
        """Load step data into dialog."""
        # Set type
        for i in range(self.type_combo.count()):
            if self.type_combo.itemData(i) == step.type:
                self.type_combo.setCurrentIndex(i)
                break

        if step.key:
            idx = self.key_combo.findText(step.key)
            if idx >= 0:
                self.key_combo.setCurrentIndex(idx)
            else:
                self.key_combo.setEditText(step.key)

        if step.delay_ms:
            self.delay_spin.setValue(step.delay_ms)

        if step.text:
            self.text_input.setText(step.text)

    def get_step(self) -> MacroStep:
        """Get the configured step."""
        step_type = self.type_combo.currentData()

        return MacroStep(
            type=step_type,
            key=self.key_combo.currentText()
            if step_type
            in (
                MacroStepType.KEY_PRESS,
                MacroStepType.KEY_DOWN,
                MacroStepType.KEY_UP,
            )
            else None,
            delay_ms=self.delay_spin.value() if step_type == MacroStepType.DELAY else None,
            text=self.text_input.text() if step_type == MacroStepType.TEXT else None,
        )


class MacroEditorWidget(QWidget):
    """Widget for creating and editing macros."""

    macro_changed = Signal(MacroAction)  # Emitted when macro is modified
    macros_updated = Signal(list)  # Emitted when macro list changes

    def __init__(self, parent=None):
        super().__init__(parent)
        self._macros: list[MacroAction] = []
        self._current_macro: MacroAction | None = None
        self._recording = False

        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)

        # Left side - macro list
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)

        left_layout.addWidget(QLabel("Macros:"))

        self.macro_list = QListWidget()
        self.macro_list.currentItemChanged.connect(self._on_macro_selected)
        left_layout.addWidget(self.macro_list)

        # Macro list buttons
        macro_btn_layout = QHBoxLayout()
        self.add_macro_btn = QPushButton("New")
        self.add_macro_btn.clicked.connect(self._add_macro)
        macro_btn_layout.addWidget(self.add_macro_btn)

        self.delete_macro_btn = QPushButton("Delete")
        self.delete_macro_btn.clicked.connect(self._delete_macro)
        self.delete_macro_btn.setEnabled(False)
        macro_btn_layout.addWidget(self.delete_macro_btn)

        left_layout.addLayout(macro_btn_layout)

        # Right side - macro editor
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # Macro properties
        props_group = QGroupBox("Macro Properties")
        props_layout = QFormLayout(props_group)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Macro name...")
        self.name_input.textChanged.connect(self._on_name_changed)
        props_layout.addRow("Name:", self.name_input)

        self.repeat_spin = QSpinBox()
        self.repeat_spin.setRange(1, 100)
        self.repeat_spin.setValue(1)
        self.repeat_spin.valueChanged.connect(self._on_repeat_changed)
        props_layout.addRow("Repeat:", self.repeat_spin)

        self.repeat_delay_spin = QSpinBox()
        self.repeat_delay_spin.setRange(0, 5000)
        self.repeat_delay_spin.setValue(0)
        self.repeat_delay_spin.setSuffix(" ms")
        self.repeat_delay_spin.valueChanged.connect(self._on_repeat_delay_changed)
        props_layout.addRow("Repeat Delay:", self.repeat_delay_spin)

        right_layout.addWidget(props_group)

        # Steps editor
        steps_group = QGroupBox("Steps")
        steps_layout = QVBoxLayout(steps_group)

        self.steps_list = QListWidget()
        self.steps_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.steps_list.model().rowsMoved.connect(self._on_steps_reordered)
        steps_layout.addWidget(self.steps_list)

        # Step buttons
        step_btn_layout = QHBoxLayout()

        self.add_step_btn = QPushButton("Add Step")
        self.add_step_btn.clicked.connect(self._add_step)
        step_btn_layout.addWidget(self.add_step_btn)

        self.edit_step_btn = QPushButton("Edit")
        self.edit_step_btn.clicked.connect(self._edit_step)
        self.edit_step_btn.setEnabled(False)
        step_btn_layout.addWidget(self.edit_step_btn)

        self.delete_step_btn = QPushButton("Delete")
        self.delete_step_btn.clicked.connect(self._delete_step)
        self.delete_step_btn.setEnabled(False)
        step_btn_layout.addWidget(self.delete_step_btn)

        steps_layout.addLayout(step_btn_layout)

        # Record button
        record_layout = QHBoxLayout()
        self.record_btn = QPushButton("Record from Device")
        self.record_btn.setCheckable(True)
        self.record_btn.clicked.connect(self._toggle_recording)
        record_layout.addWidget(self.record_btn)

        self.record_status = QLabel()
        record_layout.addWidget(self.record_status)
        record_layout.addStretch()

        steps_layout.addLayout(record_layout)

        right_layout.addWidget(steps_group)

        # Test button
        test_layout = QHBoxLayout()
        self.test_btn = QPushButton("Test Macro")
        self.test_btn.clicked.connect(self._test_macro)
        self.test_btn.setEnabled(False)
        test_layout.addWidget(self.test_btn)
        test_layout.addStretch()
        right_layout.addLayout(test_layout)

        # Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([200, 400])

        layout.addWidget(splitter)

        # Connect step selection
        self.steps_list.currentItemChanged.connect(self._on_step_selected)
        self.steps_list.itemDoubleClicked.connect(self._edit_step)

        # Disable editor initially
        self._set_editor_enabled(False)

    def set_macros(self, macros: list[MacroAction]):
        """Set the list of macros to edit."""
        self._macros = macros
        self._refresh_macro_list()

    def get_macros(self) -> list[MacroAction]:
        """Get the current macro list."""
        return self._macros

    def _refresh_macro_list(self):
        """Refresh the macro list widget."""
        self.macro_list.clear()
        for macro in self._macros:
            item = QListWidgetItem(macro.name)
            item.setData(Qt.ItemDataRole.UserRole, macro.id)
            self.macro_list.addItem(item)

    def _on_macro_selected(self, current, previous):
        """Handle macro selection change."""
        if current:
            macro_id = current.data(Qt.ItemDataRole.UserRole)
            self._current_macro = next((m for m in self._macros if m.id == macro_id), None)
            self._load_macro(self._current_macro)
            self._set_editor_enabled(True)
            self.delete_macro_btn.setEnabled(True)
        else:
            self._current_macro = None
            self._set_editor_enabled(False)
            self.delete_macro_btn.setEnabled(False)

    def _load_macro(self, macro: MacroAction | None):
        """Load macro data into editor."""
        if not macro:
            return

        self.name_input.blockSignals(True)
        self.name_input.setText(macro.name)
        self.name_input.blockSignals(False)

        self.repeat_spin.blockSignals(True)
        self.repeat_spin.setValue(macro.repeat_count)
        self.repeat_spin.blockSignals(False)

        self.repeat_delay_spin.blockSignals(True)
        self.repeat_delay_spin.setValue(macro.repeat_delay_ms)
        self.repeat_delay_spin.blockSignals(False)

        self._refresh_steps_list()
        self.test_btn.setEnabled(len(macro.steps) > 0)

    def _refresh_steps_list(self):
        """Refresh the steps list widget."""
        self.steps_list.clear()
        if not self._current_macro:
            return

        for i, step in enumerate(self._current_macro.steps):
            text = self._step_to_text(step)
            item = QListWidgetItem(f"{i + 1}. {text}")
            item.setData(Qt.ItemDataRole.UserRole, i)
            self.steps_list.addItem(item)

    def _step_to_text(self, step: MacroStep) -> str:
        """Convert step to display text."""
        if step.type == MacroStepType.KEY_PRESS:
            return f"Press {step.key}"
        elif step.type == MacroStepType.KEY_DOWN:
            return f"Hold {step.key}"
        elif step.type == MacroStepType.KEY_UP:
            return f"Release {step.key}"
        elif step.type == MacroStepType.DELAY:
            return f"Wait {step.delay_ms}ms"
        elif step.type == MacroStepType.TEXT:
            return f'Type "{step.text}"'
        return str(step.type)

    def _set_editor_enabled(self, enabled: bool):
        """Enable/disable the editor panel."""
        self.name_input.setEnabled(enabled)
        self.repeat_spin.setEnabled(enabled)
        self.repeat_delay_spin.setEnabled(enabled)
        self.steps_list.setEnabled(enabled)
        self.add_step_btn.setEnabled(enabled)
        self.record_btn.setEnabled(enabled)

    def _on_step_selected(self, current, previous):
        """Handle step selection change."""
        has_selection = current is not None
        self.edit_step_btn.setEnabled(has_selection)
        self.delete_step_btn.setEnabled(has_selection)

    def _add_macro(self):
        """Add a new macro."""
        macro = MacroAction(
            id=str(uuid.uuid4())[:8],
            name=f"Macro {len(self._macros) + 1}",
            steps=[],
        )
        self._macros.append(macro)
        self._refresh_macro_list()

        # Select the new macro
        self.macro_list.setCurrentRow(len(self._macros) - 1)
        self.macros_updated.emit(self._macros)

    def _delete_macro(self):
        """Delete the selected macro."""
        if not self._current_macro:
            return

        confirm = QMessageBox.question(
            self,
            "Delete Macro",
            f"Delete macro '{self._current_macro.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if confirm == QMessageBox.StandardButton.Yes:
            self._macros = [m for m in self._macros if m.id != self._current_macro.id]
            self._current_macro = None
            self._refresh_macro_list()
            self.macros_updated.emit(self._macros)

    def _add_step(self):
        """Add a new step to the current macro."""
        if not self._current_macro:
            return

        dialog = StepEditorDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            step = dialog.get_step()
            self._current_macro.steps.append(step)
            self._refresh_steps_list()
            self._emit_macro_changed()
            self.test_btn.setEnabled(True)

    def _edit_step(self):
        """Edit the selected step."""
        if not self._current_macro:
            return

        current = self.steps_list.currentItem()
        if not current:
            return

        idx = current.data(Qt.ItemDataRole.UserRole)
        step = self._current_macro.steps[idx]

        dialog = StepEditorDialog(step, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._current_macro.steps[idx] = dialog.get_step()
            self._refresh_steps_list()
            self._emit_macro_changed()

    def _delete_step(self):
        """Delete the selected step."""
        if not self._current_macro:
            return

        current = self.steps_list.currentItem()
        if not current:
            return

        idx = current.data(Qt.ItemDataRole.UserRole)
        del self._current_macro.steps[idx]
        self._refresh_steps_list()
        self._emit_macro_changed()
        self.test_btn.setEnabled(len(self._current_macro.steps) > 0)

    def _on_steps_reordered(self):
        """Handle steps being reordered via drag-drop."""
        if not self._current_macro:
            return

        # Rebuild steps list from widget order
        new_steps = []
        for i in range(self.steps_list.count()):
            item = self.steps_list.item(i)
            old_idx = item.data(Qt.ItemDataRole.UserRole)
            new_steps.append(self._current_macro.steps[old_idx])

        self._current_macro.steps = new_steps
        self._refresh_steps_list()
        self._emit_macro_changed()

    def _on_name_changed(self, text: str):
        """Handle macro name change."""
        if self._current_macro:
            self._current_macro.name = text
            # Update list item
            current = self.macro_list.currentItem()
            if current:
                current.setText(text)
            self._emit_macro_changed()

    def _on_repeat_changed(self, value: int):
        """Handle repeat count change."""
        if self._current_macro:
            self._current_macro.repeat_count = value
            self._emit_macro_changed()

    def _on_repeat_delay_changed(self, value: int):
        """Handle repeat delay change."""
        if self._current_macro:
            self._current_macro.repeat_delay_ms = value
            self._emit_macro_changed()

    def _emit_macro_changed(self):
        """Emit signal that macro was modified."""
        if self._current_macro:
            self.macro_changed.emit(self._current_macro)
            self.macros_updated.emit(self._macros)

    def _toggle_recording(self):
        """Toggle macro recording mode."""
        if self._recording:
            self._stop_recording()
        else:
            self._start_recording()

    def _start_recording(self):
        """Start recording macro from device input."""
        if not self._current_macro:
            return

        # Show recording dialog
        dialog = RecordingDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            recorded = dialog.get_recorded_macro()
            if recorded and recorded.steps:
                # Replace current macro steps with recorded steps
                self._current_macro.steps = recorded.steps
                self._refresh_steps_list()
                self._emit_macro_changed()
                self.test_btn.setEnabled(True)

                self.record_status.setText(f"Recorded {len(recorded.steps)} steps")
                self.record_status.setStyleSheet("color: green;")
            else:
                self.record_status.setText("No steps recorded")
                self.record_status.setStyleSheet("color: orange;")
        else:
            self.record_status.setText("")
            self.record_status.setStyleSheet("")

        # Reset button state
        self.record_btn.setChecked(False)

    def _stop_recording(self):
        """Stop recording (legacy, kept for compatibility)."""
        self._recording = False
        self.record_btn.setText("Record from Device")
        self.record_btn.setChecked(False)
        self.record_status.setText("")
        self.record_status.setStyleSheet("")

    def _test_macro(self):
        """Test the current macro."""
        if not self._current_macro or not self._current_macro.steps:
            return

        # Show what would be played
        steps_text = "\n".join(
            f"  {i + 1}. {self._step_to_text(s)}" for i, s in enumerate(self._current_macro.steps)
        )

        QMessageBox.information(
            self,
            "Test Macro",
            f"Macro '{self._current_macro.name}' would execute:\n\n"
            f"{steps_text}\n\n"
            f"Repeat: {self._current_macro.repeat_count}x\n"
            f"Delay between repeats: {self._current_macro.repeat_delay_ms}ms\n\n"
            "Note: Actual playback requires the remap daemon running.",
        )
