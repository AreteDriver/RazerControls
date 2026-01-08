"""Binding editor widget for configuring key bindings."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from apps.gui.widgets.device_visual.device_visual_widget import DeviceVisualWidget
from crates.device_layouts import DeviceLayoutRegistry
from crates.keycode_map import evdev_code_to_schema
from crates.profile_schema import (
    ActionType,
    Binding,
    Layer,
    MacroAction,
    MacroStep,
    MacroStepType,
    Profile,
)

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

# Common hold modifier keys for Hypershift
HOLD_MODIFIER_OPTIONS = [
    ("", "(None - Base Layer)"),
    ("BTN_MIDDLE", "Middle Click"),
    ("BTN_SIDE", "Side Button (Back)"),
    ("BTN_EXTRA", "Extra Button (Forward)"),
    ("KEY_CAPSLOCK", "Caps Lock"),
    ("KEY_F13", "F13"),
    ("KEY_F14", "F14"),
    ("KEY_F15", "F15"),
]


class LayerDialog(QDialog):
    """Dialog for editing layer properties including hold modifier."""

    def __init__(self, layer: Layer | None = None, is_base: bool = False, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Layer" if layer else "New Layer")
        self.setMinimumWidth(350)
        self.is_base = is_base

        layout = QFormLayout(self)

        # Layer name
        self.name_edit = QLineEdit()
        if layer:
            self.name_edit.setText(layer.name)
        layout.addRow("Name:", self.name_edit)

        # Hold modifier (Hypershift key)
        self.modifier_combo = QComboBox()
        self.modifier_combo.setEditable(True)
        for code, name in HOLD_MODIFIER_OPTIONS:
            self.modifier_combo.addItem(name, code)

        if is_base:
            self.modifier_combo.setEnabled(False)
            self.modifier_combo.setToolTip("Base layer cannot have a hold modifier")
        else:
            self.modifier_combo.setToolTip(
                "Hold this key to activate this layer (like Razer Hypershift)"
            )

        if layer and layer.hold_modifier_input_code:
            idx = self.modifier_combo.findData(layer.hold_modifier_input_code)
            if idx >= 0:
                self.modifier_combo.setCurrentIndex(idx)
            else:
                self.modifier_combo.setEditText(layer.hold_modifier_input_code)

        layout.addRow("Hold Modifier:", self.modifier_combo)

        # Help text
        help_label = QLabel(
            "The hold modifier is the key you hold to activate this layer.\n"
            "While held, bindings from this layer are used instead of base."
        )
        help_label.setStyleSheet("color: #888888; font-size: 11px;")
        help_label.setWordWrap(True)
        layout.addRow(help_label)

        # Buttons
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addRow(self.buttons)

    def get_layer_data(self) -> tuple[str, str | None]:
        """Get layer name and hold modifier code."""
        name = self.name_edit.text().strip() or "Unnamed Layer"
        modifier = self.modifier_combo.currentData()
        if not modifier:
            # Check if user typed a custom value
            text = self.modifier_combo.currentText()
            if text and text != "(None - Base Layer)":
                # Try to extract code from "Name (CODE)" format
                if "(" in text and ")" in text:
                    modifier = text.split("(")[-1].rstrip(")")
                else:
                    modifier = text
            else:
                modifier = None
        return name, modifier


class BindingDialog(QDialog):
    """Dialog for editing a single binding."""

    def __init__(
        self,
        binding: Binding | None = None,
        macros: list[MacroAction] | None = None,
        parent=None,
    ):
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
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
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
                # Parse keys separated by + and normalize to uppercase for single letters
                output_keys = []
                for k in output_text.split("+"):
                    key = k.strip()
                    # Normalize single letters to uppercase
                    if len(key) == 1 and key.isalpha():
                        key = key.upper()
                    output_keys.append(key)

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
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
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
        """Set up the bindings tab with device visual."""
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Top bar: Device and Layer selectors
        top_bar = QHBoxLayout()
        top_bar.setSpacing(8)

        top_bar.addWidget(QLabel("Device:"))
        self.device_combo = QComboBox()
        self.device_combo.setMinimumWidth(150)
        self._populate_device_combo()
        self.device_combo.currentIndexChanged.connect(self._on_device_combo_changed)
        top_bar.addWidget(self.device_combo)

        top_bar.addWidget(QLabel("Layer:"))
        self.layer_combo = QComboBox()
        self.layer_combo.setMinimumWidth(120)
        self.layer_combo.currentIndexChanged.connect(self._on_layer_changed)
        top_bar.addWidget(self.layer_combo)

        self.edit_layer_btn = QPushButton("Edit")
        self.edit_layer_btn.setMaximumWidth(50)
        self.edit_layer_btn.clicked.connect(self._edit_layer)
        self.edit_layer_btn.setToolTip("Edit layer name and hold modifier (Hypershift)")
        top_bar.addWidget(self.edit_layer_btn)

        self.add_layer_btn = QPushButton("+")
        self.add_layer_btn.setMaximumWidth(30)
        self.add_layer_btn.clicked.connect(self._add_layer)
        self.add_layer_btn.setToolTip("Add a new layer with Hypershift support")
        top_bar.addWidget(self.add_layer_btn)

        self.del_layer_btn = QPushButton("−")
        self.del_layer_btn.setMaximumWidth(30)
        self.del_layer_btn.clicked.connect(self._delete_layer)
        self.del_layer_btn.setToolTip("Delete current layer")
        top_bar.addWidget(self.del_layer_btn)

        top_bar.addStretch()

        # Layer info (Hypershift key indicator)
        self.layer_info_label = QLabel("")
        self.layer_info_label.setStyleSheet("color: #44d72c; font-size: 11px;")
        top_bar.addWidget(self.layer_info_label)

        layout.addLayout(top_bar)

        # Splitter: Device visual on left, bindings list on right
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left side: Device visual
        device_panel = QWidget()
        device_panel_layout = QVBoxLayout(device_panel)
        device_panel_layout.setContentsMargins(0, 0, 0, 0)
        device_panel_layout.setSpacing(2)

        # Device info label
        self.device_info_label = QLabel("Click a button to configure")
        self.device_info_label.setStyleSheet("color: #888; font-size: 10px;")

        device_panel_layout.addWidget(self.device_info_label)

        # Device visual widget
        self.device_visual = DeviceVisualWidget()
        self.device_visual.button_clicked.connect(self._on_device_button_clicked)
        self.device_visual.button_right_clicked.connect(self._on_device_button_right_clicked)
        self.device_visual.setMinimumWidth(180)
        device_panel_layout.addWidget(self.device_visual, 1)

        splitter.addWidget(device_panel)

        # Right side: Bindings list
        bindings_panel = QWidget()
        bindings_layout = QVBoxLayout(bindings_panel)
        bindings_layout.setContentsMargins(0, 0, 0, 0)

        # Bindings list
        self.bindings_list = QListWidget()
        self.bindings_list.itemDoubleClicked.connect(self._edit_binding)
        self.bindings_list.currentItemChanged.connect(self._on_binding_selected)
        bindings_layout.addWidget(self.bindings_list)

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
        bindings_layout.addLayout(btn_layout)

        splitter.addWidget(bindings_panel)

        # Set splitter proportions (40% device, 60% bindings)
        splitter.setSizes([400, 600])

        layout.addWidget(splitter, 1)

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

    def _populate_device_combo(self) -> None:
        """Populate the device selector with available layouts."""
        registry = DeviceLayoutRegistry()
        registry.load_layouts()

        self.device_combo.clear()
        self.device_combo.addItem("-- Select Device --", None)

        # Group by category
        categories = {"mouse": [], "keyboard": [], "keypad": []}
        for layout in registry._layouts.values():
            cat = layout.category.value
            if cat in categories:
                categories[cat].append((layout.name, layout.id))

        # Add mice
        if categories["mouse"]:
            self.device_combo.addItem("--- Mice ---", None)
            for name, layout_id in sorted(categories["mouse"]):
                self.device_combo.addItem(f"  {name}", layout_id)

        # Add keyboards
        if categories["keyboard"]:
            self.device_combo.addItem("--- Keyboards ---", None)
            for name, layout_id in sorted(categories["keyboard"]):
                self.device_combo.addItem(f"  {name}", layout_id)

        # Add keypads
        if categories["keypad"]:
            self.device_combo.addItem("--- Keypads ---", None)
            for name, layout_id in sorted(categories["keypad"]):
                self.device_combo.addItem(f"  {name}", layout_id)

        # Default to DeathAdder V2 if available
        for i in range(self.device_combo.count()):
            if "deathadder" in (self.device_combo.itemData(i) or "").lower():
                self.device_combo.setCurrentIndex(i)
                break

    def _on_device_combo_changed(self) -> None:
        """Handle device selection from combo box."""
        layout_id = self.device_combo.currentData()
        if not layout_id or layout_id.startswith("---"):
            return

        # Get layout from registry
        registry = DeviceLayoutRegistry()
        registry.load_layouts()
        layout = registry._layouts.get(layout_id)
        if layout:
            self.device_visual.set_layout(layout)
            self._sync_device_button_bindings()

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

    def set_device(self, device_name: str, device_type: str | None = None) -> None:
        """Set the device for the visual representation."""
        self.device_visual.set_device(device_name, device_type)
        self._sync_device_button_bindings()

    def _on_device_button_clicked(self, button_id: str, input_code: str) -> None:
        """Handle click on a device button - add or edit binding."""
        layer = self._get_current_layer()
        if not layer:
            return

        # Check if binding already exists for this input
        existing_binding = None
        for binding in layer.bindings:
            if binding.input_code == input_code:
                existing_binding = binding
                break

        if existing_binding:
            # Edit existing binding
            self._edit_binding_dialog(existing_binding)
        else:
            # Add new binding with this input pre-filled
            self._add_binding_for_input(input_code)

        self._sync_device_button_bindings()

    def _on_device_button_right_clicked(self, button_id: str) -> None:
        """Handle right-click on device button - show context menu."""
        # The DeviceVisualWidget already shows a context menu
        pass

    def _on_binding_selected(self, current: QListWidgetItem, previous: QListWidgetItem) -> None:
        """Highlight the corresponding button when a binding is selected."""
        if not current:
            self.device_visual.select_button(None)
            return

        binding = current.data(Qt.ItemDataRole.UserRole)
        if not binding:
            return

        # Find button with matching input code
        layout = self.device_visual.get_layout()
        if layout:
            for button in layout.buttons:
                if button.input_code == binding.input_code:
                    self.device_visual.select_button(button.id)
                    return

        self.device_visual.select_button(None)

    def _add_binding_for_input(self, input_code: str) -> None:
        """Add a new binding with pre-filled input code."""
        layer = self._get_current_layer()
        if not layer:
            return

        # Create a binding with just the input code
        prefilled_binding = Binding(
            input_code=input_code,
            action_type=ActionType.KEY,
            output_keys=[],
        )

        macros = self.current_profile.macros if self.current_profile else []
        dialog = BindingDialog(binding=prefilled_binding, macros=macros, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            binding = dialog.get_binding()
            if binding:
                layer.bindings.append(binding)
                self._refresh_bindings()
                self.bindings_changed.emit()

    def _sync_device_button_bindings(self) -> None:
        """Update the device visual to show which buttons have bindings."""
        layer = self._get_current_layer()
        if not layer:
            return

        # Build dict of input_code -> binding display
        bindings_map = {}
        for binding in layer.bindings:
            bindings_map[binding.input_code] = self._format_binding_short(binding)

        self.device_visual.set_button_bindings(bindings_map)

    def _format_binding_short(self, binding: Binding) -> str:
        """Format a binding for short display on device."""
        if binding.action_type == ActionType.KEY:
            return binding.output_keys[0] if binding.output_keys else "?"
        elif binding.action_type == ActionType.CHORD:
            return "+".join(binding.output_keys[:2])  # First 2 keys
        elif binding.action_type == ActionType.MACRO:
            return "Macro"
        elif binding.action_type == ActionType.PASSTHROUGH:
            return "Pass"
        else:
            return "Off"

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
        self._update_layer_info()
        self._sync_device_button_bindings()

    def _update_layer_info(self):
        """Update the layer info label."""
        layer = self._get_current_layer()
        if not layer:
            self.layer_info_label.setText("")
            self.del_layer_btn.setEnabled(False)
            return

        # Can't delete base layer
        is_base = layer.id == "base"
        self.del_layer_btn.setEnabled(not is_base)

        if layer.hold_modifier_input_code:
            mod_name = evdev_code_to_schema(layer.hold_modifier_input_code)
            self.layer_info_label.setText(f"Hypershift: Hold {mod_name} to activate")
        elif is_base:
            self.layer_info_label.setText("Base layer (always active when no modifier held)")
        else:
            self.layer_info_label.setText("No hold modifier set - edit layer to add one")

    def _refresh_bindings(self):
        """Refresh the bindings list."""
        self.bindings_list.clear()
        layer = self._get_current_layer()
        if not layer:
            return

        for binding in layer.bindings:
            display = self._format_binding(binding)
            item = QListWidgetItem(display)
            item.setData(Qt.ItemDataRole.UserRole, binding)
            self.bindings_list.addItem(item)

    def _refresh_macros(self):
        """Refresh the macros list."""
        self.macros_list.clear()
        if not self.current_profile:
            return

        for macro in self.current_profile.macros:
            display = f"{macro.name} ({len(macro.steps)} steps)"
            item = QListWidgetItem(display)
            item.setData(Qt.ItemDataRole.UserRole, macro)
            self.macros_list.addItem(item)

    def _format_binding(self, binding: Binding) -> str:
        """Format a binding for display."""
        input_name = evdev_code_to_schema(binding.input_code)

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
        """Add a new layer with Hypershift support."""
        if not self.current_profile:
            return

        dialog = LayerDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name, modifier = dialog.get_layer_data()

            # Generate unique ID
            layer_num = len(self.current_profile.layers) + 1
            layer_id = f"layer_{layer_num}"

            layer = Layer(
                id=layer_id,
                name=name,
                bindings=[],
                hold_modifier_input_code=modifier,
            )
            self.current_profile.layers.append(layer)
            self.layer_combo.addItem(layer.name, layer.id)
            self.layer_combo.setCurrentIndex(self.layer_combo.count() - 1)
            self.bindings_changed.emit()

    def _edit_layer(self):
        """Edit the current layer's properties."""
        layer = self._get_current_layer()
        if not layer:
            return

        is_base = layer.id == "base"
        dialog = LayerDialog(layer=layer, is_base=is_base, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name, modifier = dialog.get_layer_data()
            layer.name = name
            if not is_base:
                layer.hold_modifier_input_code = modifier

            # Update combo box text
            idx = self.layer_combo.currentIndex()
            self.layer_combo.setItemText(idx, name)

            self._update_layer_info()
            self.bindings_changed.emit()

    def _delete_layer(self):
        """Delete the current layer."""
        layer = self._get_current_layer()
        if not layer or layer.id == "base":
            return

        # Confirm deletion
        from PySide6.QtWidgets import QMessageBox

        reply = QMessageBox.question(
            self,
            "Delete Layer",
            f"Delete layer '{layer.name}' and all its bindings?",
            QMessageBox.Yes | QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            self.current_profile.layers.remove(layer)
            idx = self.layer_combo.currentIndex()
            self.layer_combo.removeItem(idx)
            self.bindings_changed.emit()

    def _add_binding(self):
        """Add a new binding."""
        layer = self._get_current_layer()
        if not layer:
            return

        macros = self.current_profile.macros if self.current_profile else []
        dialog = BindingDialog(macros=macros, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            binding = dialog.get_binding()
            if binding:
                layer.bindings.append(binding)
                self._refresh_bindings()
                self.bindings_changed.emit()

    def _edit_binding(self, item: QListWidgetItem):
        """Edit a binding from double-click."""
        binding = item.data(Qt.ItemDataRole.UserRole)
        if binding:
            self._edit_binding_dialog(binding)

    def _edit_selected_binding(self):
        """Edit the selected binding."""
        item = self.bindings_list.currentItem()
        if item:
            binding = item.data(Qt.ItemDataRole.UserRole)
            if binding:
                self._edit_binding_dialog(binding)

    def _edit_binding_dialog(self, binding: Binding):
        """Open dialog to edit a binding."""
        layer = self._get_current_layer()
        if not layer:
            return

        macros = self.current_profile.macros if self.current_profile else []
        dialog = BindingDialog(binding=binding, macros=macros, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
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
            binding = item.data(Qt.ItemDataRole.UserRole)
            if binding in layer.bindings:
                layer.bindings.remove(binding)
                self._refresh_bindings()
                self.bindings_changed.emit()

    def _add_macro(self):
        """Add a new macro."""
        if not self.current_profile:
            return

        dialog = MacroDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            macro = dialog.get_macro()
            if macro:
                self.current_profile.macros.append(macro)
                self._refresh_macros()
                self.bindings_changed.emit()

    def _edit_macro(self, item: QListWidgetItem):
        """Edit a macro from double-click."""
        macro = item.data(Qt.ItemDataRole.UserRole)
        if macro:
            self._edit_macro_dialog(macro)

    def _edit_selected_macro(self):
        """Edit the selected macro."""
        item = self.macros_list.currentItem()
        if item:
            macro = item.data(Qt.ItemDataRole.UserRole)
            if macro:
                self._edit_macro_dialog(macro)

    def _edit_macro_dialog(self, macro: MacroAction):
        """Open dialog to edit a macro."""
        if not self.current_profile:
            return

        dialog = MacroDialog(macro=macro, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
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
            macro = item.data(Qt.ItemDataRole.UserRole)
            if macro in self.current_profile.macros:
                self.current_profile.macros.remove(macro)
                self._refresh_macros()
                self.bindings_changed.emit()
