"""Binding editor widget for configuring key bindings."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QComboBox, QLineEdit, QDialog, QFormLayout,
    QDialogButtonBox, QTabWidget, QTextEdit, QSpinBox, QScrollArea
)
from PySide6.QtCore import Qt, Signal

from crates.profile_schema import (
    Profile, Layer, Binding, MacroAction, MacroStep,
    ActionType, MacroStepType
)
from crates.keycode_map import get_all_schema_keys, evdev_code_to_schema


# Common input buttons for quick selection
COMMON_INPUTS = {
    "Mouse Buttons": [
        ("BTN_LEFT", "Left Click"),
        ("BTN_RIGHT", "Right Click"),
        ("BTN_MIDDLE", "Middle Click"),
        ("BTN_SIDE", "Side Button (Back)"),
        ("BTN_EXTRA", "Extra Button (Forward)"),
    ],
    "Function Keys": [
        ("KEY_F13", "F13"),
        ("KEY_F14", "F14"),
        ("KEY_F15", "F15"),
        ("KEY_F16", "F16"),
        ("KEY_F17", "F17"),
        ("KEY_F18", "F18"),
    ],
}


class BindingDialog(QDialog):
    """Dialog for editing a single binding."""

    def __init__(self, binding: Binding | None = None, macros: list[MacroAction] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Binding")
        self.setMinimumWidth(400)
        self.macros = macros or []

        layout = QFormLayout(self)

        # Input key
        self.input_combo = QComboBox()
        self.input_combo.setEditable(True)
        self._populate_inputs()
        layout.addRow("Input Key:", self.input_combo)

        # Action type
        self.action_combo = QComboBox()
        self.action_combo.addItem("Key", ActionType.KEY)
        self.action_combo.addItem("Key Chord", ActionType.CHORD)
        self.action_combo.addItem("Macro", ActionType.MACRO)
        self.action_combo.addItem("Passthrough", ActionType.PASSTHROUGH)
        self.action_combo.addItem("Disabled", ActionType.DISABLED)
        self.action_combo.currentIndexChanged.connect(self._on_action_changed)
        layout.addRow("Action:", self.action_combo)

        # Output keys (for KEY and CHORD)
        self.output_edit = QLineEdit()
        self.output_edit.setPlaceholderText("e.g., CTRL+C or F13")
        layout.addRow("Output Keys:", self.output_edit)

        # Macro selection
        self.macro_combo = QComboBox()
        for macro in self.macros:
            self.macro_combo.addItem(macro.name, macro.id)
        layout.addRow("Macro:", self.macro_combo)

        # Buttons
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addRow(self.buttons)

        # Load existing binding
        if binding:
            self._load_binding(binding)

        self._on_action_changed()

    def _populate_inputs(self):
        """Populate input key combo box."""
        for category, keys in COMMON_INPUTS.items():
            self.input_combo.addItem(f"--- {category} ---")
            for code, name in keys:
                self.input_combo.addItem(f"{name} ({code})", code)

    def _load_binding(self, binding: Binding):
        """Load existing binding into dialog."""
        # Set input
        idx = self.input_combo.findData(binding.input_code)
        if idx >= 0:
            self.input_combo.setCurrentIndex(idx)
        else:
            self.input_combo.setEditText(binding.input_code)

        # Set action type
        idx = self.action_combo.findData(binding.action_type)
        if idx >= 0:
            self.action_combo.setCurrentIndex(idx)

        # Set output keys
        if binding.output_keys:
            self.output_edit.setText("+".join(binding.output_keys))

        # Set macro
        if binding.macro_id:
            idx = self.macro_combo.findData(binding.macro_id)
            if idx >= 0:
                self.macro_combo.setCurrentIndex(idx)

    def _on_action_changed(self):
        """Update UI based on action type."""
        action = self.action_combo.currentData()

        # Show/hide output keys
        show_output = action in (ActionType.KEY, ActionType.CHORD)
        self.output_edit.setVisible(show_output)

        # Show/hide macro selection
        show_macro = action == ActionType.MACRO
        self.macro_combo.setVisible(show_macro)

    def get_binding(self) -> Binding | None:
        """Get the configured binding."""
        input_code = self.input_combo.currentData()
        if not input_code:
            input_code = self.input_combo.currentText()
            # Extract code from "Name (CODE)" format
            if "(" in input_code and ")" in input_code:
                input_code = input_code.split("(")[-1].rstrip(")")

        if not input_code or input_code.startswith("---"):
            return None

        action_type = self.action_combo.currentData()
        output_keys = []
        macro_id = None

        if action_type in (ActionType.KEY, ActionType.CHORD):
            output_text = self.output_edit.text().strip()
            if output_text:
                # Parse keys separated by +
                output_keys = [k.strip() for k in output_text.split("+")]

        if action_type == ActionType.MACRO:
            macro_id = self.macro_combo.currentData()

        return Binding(
            input_code=input_code,
            action_type=action_type,
            output_keys=output_keys,
            macro_id=macro_id,
        )


class MacroDialog(QDialog):
    """Dialog for editing a macro."""

    def __init__(self, macro: MacroAction | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Macro")
        self.setMinimumSize(400, 300)

        layout = QFormLayout(self)

        # Name
        self.name_edit = QLineEdit()
        layout.addRow("Name:", self.name_edit)

        # Steps (simplified - just text input for now)
        self.steps_edit = QTextEdit()
        self.steps_edit.setPlaceholderText(
            "Enter macro steps, one per line:\n"
            "key:A (press A)\n"
            "down:CTRL (hold Ctrl)\n"
            "up:CTRL (release Ctrl)\n"
            "delay:100 (wait 100ms)\n"
            "text:hello (type 'hello')"
        )
        layout.addRow("Steps:", self.steps_edit)

        # Repeat
        self.repeat_spin = QSpinBox()
        self.repeat_spin.setRange(1, 100)
        self.repeat_spin.setValue(1)
        layout.addRow("Repeat:", self.repeat_spin)

        # Buttons
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addRow(self.buttons)

        if macro:
            self._load_macro(macro)

    def _load_macro(self, macro: MacroAction):
        """Load existing macro."""
        self.name_edit.setText(macro.name)
        self.repeat_spin.setValue(macro.repeat_count)

        # Convert steps to text
        lines = []
        for step in macro.steps:
            if step.type == MacroStepType.KEY_PRESS:
                lines.append(f"key:{step.key}")
            elif step.type == MacroStepType.KEY_DOWN:
                lines.append(f"down:{step.key}")
            elif step.type == MacroStepType.KEY_UP:
                lines.append(f"up:{step.key}")
            elif step.type == MacroStepType.DELAY:
                lines.append(f"delay:{step.delay_ms}")
            elif step.type == MacroStepType.TEXT:
                lines.append(f"text:{step.text}")
        self.steps_edit.setPlainText("\n".join(lines))

    def get_macro(self) -> MacroAction | None:
        """Get the configured macro."""
        name = self.name_edit.text().strip()
        if not name:
            return None

        # Generate ID from name
        macro_id = name.lower().replace(" ", "_")

        # Parse steps
        steps = []
        for line in self.steps_edit.toPlainText().strip().split("\n"):
            line = line.strip()
            if not line:
                continue

            if ":" not in line:
                continue

            cmd, arg = line.split(":", 1)
            cmd = cmd.lower().strip()
            arg = arg.strip()

            if cmd == "key":
                steps.append(MacroStep(type=MacroStepType.KEY_PRESS, key=arg))
            elif cmd == "down":
                steps.append(MacroStep(type=MacroStepType.KEY_DOWN, key=arg))
            elif cmd == "up":
                steps.append(MacroStep(type=MacroStepType.KEY_UP, key=arg))
            elif cmd == "delay":
                try:
                    ms = int(arg)
                    steps.append(MacroStep(type=MacroStepType.DELAY, delay_ms=ms))
                except ValueError:
                    pass
            elif cmd == "text":
                steps.append(MacroStep(type=MacroStepType.TEXT, text=arg))

        return MacroAction(
            id=macro_id,
            name=name,
            steps=steps,
            repeat_count=self.repeat_spin.value(),
        )


class BindingEditorWidget(QWidget):
    """Widget for editing key bindings and macros."""

    bindings_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_profile: Profile | None = None
        self._setup_ui()

    def _setup_ui(self):
        """Set up the widget UI."""
        layout = QVBoxLayout(self)

        # Tabs for layers and macros
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Bindings tab
        bindings_widget = QWidget()
        self._setup_bindings_tab(bindings_widget)
        self.tabs.addTab(bindings_widget, "Bindings")

        # Macros tab
        macros_widget = QWidget()
        self._setup_macros_tab(macros_widget)
        self.tabs.addTab(macros_widget, "Macros")

    def _setup_bindings_tab(self, widget):
        """Set up the bindings tab."""
        layout = QVBoxLayout(widget)

        # Layer selector
        layer_layout = QHBoxLayout()
        layer_layout.addWidget(QLabel("Layer:"))
        self.layer_combo = QComboBox()
        self.layer_combo.currentIndexChanged.connect(self._on_layer_changed)
        layer_layout.addWidget(self.layer_combo, 1)

        self.add_layer_btn = QPushButton("Add Layer")
        self.add_layer_btn.clicked.connect(self._add_layer)
        layer_layout.addWidget(self.add_layer_btn)

        layout.addLayout(layer_layout)

        # Bindings list
        self.bindings_list = QListWidget()
        self.bindings_list.itemDoubleClicked.connect(self._edit_binding)
        layout.addWidget(self.bindings_list)

        # Buttons
        btn_layout = QHBoxLayout()

        self.add_binding_btn = QPushButton("Add Binding")
        self.add_binding_btn.clicked.connect(self._add_binding)
        btn_layout.addWidget(self.add_binding_btn)

        self.edit_binding_btn = QPushButton("Edit")
        self.edit_binding_btn.clicked.connect(self._edit_selected_binding)
        btn_layout.addWidget(self.edit_binding_btn)

        self.remove_binding_btn = QPushButton("Remove")
        self.remove_binding_btn.clicked.connect(self._remove_binding)
        btn_layout.addWidget(self.remove_binding_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def _setup_macros_tab(self, widget):
        """Set up the macros tab."""
        layout = QVBoxLayout(widget)

        # Macros list
        self.macros_list = QListWidget()
        self.macros_list.itemDoubleClicked.connect(self._edit_macro)
        layout.addWidget(self.macros_list)

        # Buttons
        btn_layout = QHBoxLayout()

        self.add_macro_btn = QPushButton("Add Macro")
        self.add_macro_btn.clicked.connect(self._add_macro)
        btn_layout.addWidget(self.add_macro_btn)

        self.edit_macro_btn = QPushButton("Edit")
        self.edit_macro_btn.clicked.connect(self._edit_selected_macro)
        btn_layout.addWidget(self.edit_macro_btn)

        self.remove_macro_btn = QPushButton("Remove")
        self.remove_macro_btn.clicked.connect(self._remove_macro)
        btn_layout.addWidget(self.remove_macro_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def load_profile(self, profile: Profile):
        """Load a profile into the editor."""
        self.current_profile = profile

        # Load layers
        self.layer_combo.clear()
        for layer in profile.layers:
            self.layer_combo.addItem(layer.name, layer.id)

        # Load macros
        self._refresh_macros()

        # Select first layer
        if self.layer_combo.count() > 0:
            self.layer_combo.setCurrentIndex(0)

    def clear(self):
        """Clear the editor."""
        self.current_profile = None
        self.layer_combo.clear()
        self.bindings_list.clear()
        self.macros_list.clear()

    def get_layers(self) -> list[Layer]:
        """Get the current layers."""
        if self.current_profile:
            return self.current_profile.layers
        return []

    def get_macros(self) -> list[MacroAction]:
        """Get the current macros."""
        if self.current_profile:
            return self.current_profile.macros
        return []

    def _get_current_layer(self) -> Layer | None:
        """Get the currently selected layer."""
        if not self.current_profile:
            return None

        layer_id = self.layer_combo.currentData()
        for layer in self.current_profile.layers:
            if layer.id == layer_id:
                return layer
        return None

    def _on_layer_changed(self):
        """Handle layer selection change."""
        self._refresh_bindings()

    def _refresh_bindings(self):
        """Refresh the bindings list."""
        self.bindings_list.clear()
        layer = self._get_current_layer()
        if not layer:
            return

        for binding in layer.bindings:
            display = self._format_binding(binding)
            item = QListWidgetItem(display)
            item.setData(Qt.UserRole, binding)
            self.bindings_list.addItem(item)

    def _refresh_macros(self):
        """Refresh the macros list."""
        self.macros_list.clear()
        if not self.current_profile:
            return

        for macro in self.current_profile.macros:
            display = f"{macro.name} ({len(macro.steps)} steps)"
            item = QListWidgetItem(display)
            item.setData(Qt.UserRole, macro)
            self.macros_list.addItem(item)

    def _format_binding(self, binding: Binding) -> str:
        """Format a binding for display."""
        input_name = evdev_code_to_schema(binding.input_code)
        action_name = binding.action_type.value

        if binding.action_type == ActionType.KEY:
            output = binding.output_keys[0] if binding.output_keys else "?"
            return f"{input_name} -> {output}"
        elif binding.action_type == ActionType.CHORD:
            output = "+".join(binding.output_keys)
            return f"{input_name} -> {output}"
        elif binding.action_type == ActionType.MACRO:
            return f"{input_name} -> Macro: {binding.macro_id}"
        elif binding.action_type == ActionType.PASSTHROUGH:
            return f"{input_name} -> (passthrough)"
        else:
            return f"{input_name} -> (disabled)"

    def _add_layer(self):
        """Add a new layer."""
        if not self.current_profile:
            return

        # Simple layer naming
        layer_num = len(self.current_profile.layers) + 1
        layer = Layer(
            id=f"layer_{layer_num}",
            name=f"Layer {layer_num}",
            bindings=[],
        )
        self.current_profile.layers.append(layer)
        self.layer_combo.addItem(layer.name, layer.id)
        self.layer_combo.setCurrentIndex(self.layer_combo.count() - 1)
        self.bindings_changed.emit()

    def _add_binding(self):
        """Add a new binding."""
        layer = self._get_current_layer()
        if not layer:
            return

        macros = self.current_profile.macros if self.current_profile else []
        dialog = BindingDialog(macros=macros, parent=self)
        if dialog.exec() == QDialog.Accepted:
            binding = dialog.get_binding()
            if binding:
                layer.bindings.append(binding)
                self._refresh_bindings()
                self.bindings_changed.emit()

    def _edit_binding(self, item: QListWidgetItem):
        """Edit a binding from double-click."""
        binding = item.data(Qt.UserRole)
        if binding:
            self._edit_binding_dialog(binding)

    def _edit_selected_binding(self):
        """Edit the selected binding."""
        item = self.bindings_list.currentItem()
        if item:
            binding = item.data(Qt.UserRole)
            if binding:
                self._edit_binding_dialog(binding)

    def _edit_binding_dialog(self, binding: Binding):
        """Open dialog to edit a binding."""
        layer = self._get_current_layer()
        if not layer:
            return

        macros = self.current_profile.macros if self.current_profile else []
        dialog = BindingDialog(binding=binding, macros=macros, parent=self)
        if dialog.exec() == QDialog.Accepted:
            new_binding = dialog.get_binding()
            if new_binding:
                # Replace binding
                idx = layer.bindings.index(binding)
                layer.bindings[idx] = new_binding
                self._refresh_bindings()
                self.bindings_changed.emit()

    def _remove_binding(self):
        """Remove the selected binding."""
        layer = self._get_current_layer()
        if not layer:
            return

        item = self.bindings_list.currentItem()
        if item:
            binding = item.data(Qt.UserRole)
            if binding in layer.bindings:
                layer.bindings.remove(binding)
                self._refresh_bindings()
                self.bindings_changed.emit()

    def _add_macro(self):
        """Add a new macro."""
        if not self.current_profile:
            return

        dialog = MacroDialog(parent=self)
        if dialog.exec() == QDialog.Accepted:
            macro = dialog.get_macro()
            if macro:
                self.current_profile.macros.append(macro)
                self._refresh_macros()
                self.bindings_changed.emit()

    def _edit_macro(self, item: QListWidgetItem):
        """Edit a macro from double-click."""
        macro = item.data(Qt.UserRole)
        if macro:
            self._edit_macro_dialog(macro)

    def _edit_selected_macro(self):
        """Edit the selected macro."""
        item = self.macros_list.currentItem()
        if item:
            macro = item.data(Qt.UserRole)
            if macro:
                self._edit_macro_dialog(macro)

    def _edit_macro_dialog(self, macro: MacroAction):
        """Open dialog to edit a macro."""
        if not self.current_profile:
            return

        dialog = MacroDialog(macro=macro, parent=self)
        if dialog.exec() == QDialog.Accepted:
            new_macro = dialog.get_macro()
            if new_macro:
                # Preserve original ID
                new_macro.id = macro.id
                idx = self.current_profile.macros.index(macro)
                self.current_profile.macros[idx] = new_macro
                self._refresh_macros()
                self.bindings_changed.emit()

    def _remove_macro(self):
        """Remove the selected macro."""
        if not self.current_profile:
            return

        item = self.macros_list.currentItem()
        if item:
            macro = item.data(Qt.UserRole)
            if macro in self.current_profile.macros:
                self.current_profile.macros.remove(macro)
                self._refresh_macros()
                self.bindings_changed.emit()
