"""Remap engine - core remapping logic."""

import time
from dataclasses import dataclass, field
from typing import Optional

from evdev import UInput, ecodes, InputEvent

from crates.profile_schema import Profile, Binding, MacroAction, ActionType, MacroStepType
from crates.keycode_map import schema_to_evdev_code


@dataclass
class KeyState:
    """Tracks the state of pressed keys."""
    pressed: set[int] = field(default_factory=set)
    active_layer: str = "base"


class RemapEngine:
    """Core remapping engine - translates input events to output events."""

    def __init__(self, profile: Profile):
        self.profile = profile
        self.state = KeyState()
        self._uinput: Optional[UInput] = None
        self._bindings: dict[str, dict[int, Binding]] = {}  # layer -> code -> binding
        self._macros: dict[str, MacroAction] = {}
        self._layer_modifiers: dict[int, str] = {}  # code -> layer_id

        self._build_lookup_tables()

    def _build_lookup_tables(self) -> None:
        """Build fast lookup tables from profile."""
        # Index macros by ID
        for macro in self.profile.macros:
            self._macros[macro.id] = macro

        # Index bindings by layer and input code
        for layer in self.profile.layers:
            layer_bindings: dict[int, Binding] = {}

            for binding in layer.bindings:
                code = schema_to_evdev_code(binding.input_code)
                if code is not None:
                    layer_bindings[code] = binding

            self._bindings[layer.id] = layer_bindings

            # Track layer modifiers
            if layer.hold_modifier_input_code:
                mod_code = schema_to_evdev_code(layer.hold_modifier_input_code)
                if mod_code is not None:
                    self._layer_modifiers[mod_code] = layer.id

    def set_uinput(self, uinput: UInput) -> None:
        """Set the uinput device for output."""
        self._uinput = uinput

    def process_event(self, event: InputEvent) -> bool:
        """
        Process an input event and emit remapped output.

        Returns True if the event was handled (consumed), False if it should pass through.
        """
        if event.type != ecodes.EV_KEY:
            # Pass through non-key events (mouse motion, etc.)
            return False

        code = event.code
        value = event.value  # 0=up, 1=down, 2=repeat

        # Check for layer modifier
        if code in self._layer_modifiers:
            layer_id = self._layer_modifiers[code]
            if value == 1:  # Key down
                self.state.active_layer = layer_id
            elif value == 0:  # Key up
                self.state.active_layer = "base"
            # Don't pass through layer modifiers
            return True

        # Look up binding in active layer, fall back to base
        binding = self._get_binding(code)

        if binding is None:
            # No binding - pass through
            return False

        # Handle the binding
        if value == 1:  # Key down
            self.state.pressed.add(code)
            self._handle_binding_down(binding)
            return True
        elif value == 0:  # Key up
            self.state.pressed.discard(code)
            self._handle_binding_up(binding)
            return True
        elif value == 2:  # Repeat
            # For repeats, we might want to re-trigger some actions
            return True

        return False

    def _get_binding(self, code: int) -> Optional[Binding]:
        """Get the binding for a key code, checking active layer first."""
        # Check active layer
        if self.state.active_layer in self._bindings:
            binding = self._bindings[self.state.active_layer].get(code)
            if binding:
                return binding

        # Fall back to base layer
        if "base" in self._bindings:
            return self._bindings["base"].get(code)

        return None

    def _handle_binding_down(self, binding: Binding) -> None:
        """Handle a binding activation (key down)."""
        if binding.action_type == ActionType.PASSTHROUGH:
            # Pass through the original key
            code = schema_to_evdev_code(binding.input_code)
            if code:
                self._emit_key(code, 1)

        elif binding.action_type == ActionType.KEY:
            # Single key output
            if binding.output_keys:
                code = schema_to_evdev_code(binding.output_keys[0])
                if code:
                    self._emit_key(code, 1)

        elif binding.action_type == ActionType.CHORD:
            # Multiple keys pressed together
            for key in binding.output_keys:
                code = schema_to_evdev_code(key)
                if code:
                    self._emit_key(code, 1)

        elif binding.action_type == ActionType.MACRO:
            # Execute macro
            if binding.macro_id and binding.macro_id in self._macros:
                self._execute_macro(self._macros[binding.macro_id])

        elif binding.action_type == ActionType.DISABLED:
            # Do nothing - consume the event
            pass

    def _handle_binding_up(self, binding: Binding) -> None:
        """Handle a binding deactivation (key up)."""
        if binding.action_type == ActionType.PASSTHROUGH:
            code = schema_to_evdev_code(binding.input_code)
            if code:
                self._emit_key(code, 0)

        elif binding.action_type == ActionType.KEY:
            if binding.output_keys:
                code = schema_to_evdev_code(binding.output_keys[0])
                if code:
                    self._emit_key(code, 0)

        elif binding.action_type == ActionType.CHORD:
            # Release in reverse order
            for key in reversed(binding.output_keys):
                code = schema_to_evdev_code(key)
                if code:
                    self._emit_key(code, 0)

        # Macros and disabled don't need key up handling

    def _emit_key(self, code: int, value: int) -> None:
        """Emit a key event through uinput."""
        if self._uinput:
            self._uinput.write(ecodes.EV_KEY, code, value)
            self._uinput.syn()

    def _execute_macro(self, macro: MacroAction) -> None:
        """Execute a macro sequence."""
        for _ in range(macro.repeat_count):
            for step in macro.steps:
                self._execute_macro_step(step)

            if macro.repeat_delay_ms > 0 and _ < macro.repeat_count - 1:
                time.sleep(macro.repeat_delay_ms / 1000.0)

    def _execute_macro_step(self, step) -> None:
        """Execute a single macro step."""
        if step.type == MacroStepType.KEY_DOWN:
            if step.key:
                code = schema_to_evdev_code(step.key)
                if code:
                    self._emit_key(code, 1)

        elif step.type == MacroStepType.KEY_UP:
            if step.key:
                code = schema_to_evdev_code(step.key)
                if code:
                    self._emit_key(code, 0)

        elif step.type == MacroStepType.KEY_PRESS:
            if step.key:
                code = schema_to_evdev_code(step.key)
                if code:
                    self._emit_key(code, 1)
                    time.sleep(0.01)  # Brief delay
                    self._emit_key(code, 0)

        elif step.type == MacroStepType.DELAY:
            if step.delay_ms:
                time.sleep(step.delay_ms / 1000.0)

        elif step.type == MacroStepType.TEXT:
            if step.text:
                self._type_text(step.text)

    def _type_text(self, text: str) -> None:
        """Type a text string by emitting key events."""
        # Basic text typing - handles lowercase letters and common chars
        # For full support, would need shift handling
        char_to_key = {
            ' ': 'SPACE',
            '\n': 'ENTER',
            '\t': 'TAB',
        }

        for char in text:
            if char.isalpha():
                key = char.upper()
                needs_shift = char.isupper()
            elif char.isdigit():
                key = char
                needs_shift = False
            elif char in char_to_key:
                key = char_to_key[char]
                needs_shift = False
            else:
                continue  # Skip unsupported chars

            code = schema_to_evdev_code(key)
            if code:
                if needs_shift:
                    shift_code = schema_to_evdev_code('SHIFT')
                    if shift_code:
                        self._emit_key(shift_code, 1)

                self._emit_key(code, 1)
                time.sleep(0.01)
                self._emit_key(code, 0)

                if needs_shift and shift_code:
                    self._emit_key(shift_code, 0)

                time.sleep(0.01)

    def reload_profile(self, profile: Profile) -> None:
        """Reload with a new profile."""
        # Release any stuck keys
        for code in list(self.state.pressed):
            self._emit_key(code, 0)

        self.profile = profile
        self.state = KeyState()
        self._bindings.clear()
        self._macros.clear()
        self._layer_modifiers.clear()
        self._build_lookup_tables()
