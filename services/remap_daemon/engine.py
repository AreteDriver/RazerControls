"""Remap engine - core remapping logic with multi-layer support."""

import time
from dataclasses import dataclass, field

from evdev import InputEvent, UInput, ecodes

from crates.keycode_map import schema_to_evdev_code
from crates.profile_schema import ActionType, Binding, MacroAction, MacroStepType, Profile


@dataclass
class ActiveBinding:
    """Tracks an active (pressed) binding and its output state."""

    input_code: int
    binding: Binding
    layer_id: str
    output_codes: list[int] = field(default_factory=list)  # Keys we're holding down


@dataclass
class KeyState:
    """Tracks the complete state of pressed keys and active bindings."""

    # Physical keys currently pressed (input codes)
    physical_pressed: set[int] = field(default_factory=set)

    # Currently active layer
    active_layer: str = "base"

    # Active bindings - maps input_code -> ActiveBinding
    # This tracks what output keys are being held for each input
    active_bindings: dict[int, ActiveBinding] = field(default_factory=dict)

    # Output keys currently held (for stuck key prevention)
    output_held: set[int] = field(default_factory=set)

    # Layer modifier currently held (if any)
    layer_modifier_held: int | None = None


class RemapEngine:
    """Core remapping engine - translates input events to output events.

    Supports:
    - Multi-layer bindings with hold-modifier switching (Hypershift)
    - Stuck key prevention on layer changes
    - Proper key state tracking for clean up/down handling
    """

    def __init__(self, profile: Profile):
        self.profile = profile
        self.state = KeyState()
        self._uinput: UInput | None = None
        self._bindings: dict[str, dict[int, Binding]] = {}  # layer_id -> code -> binding
        self._macros: dict[str, MacroAction] = {}
        self._layer_modifiers: dict[int, str] = {}  # input_code -> layer_id
        self._layer_by_id: dict[str, object] = {}  # layer_id -> Layer object

        self._build_lookup_tables()

    def _build_lookup_tables(self) -> None:
        """Build fast lookup tables from profile."""
        # Index macros by ID
        for macro in self.profile.macros:
            self._macros[macro.id] = macro

        # Index bindings by layer and input code
        for layer in self.profile.layers:
            self._layer_by_id[layer.id] = layer
            layer_bindings: dict[int, Binding] = {}

            for binding in layer.bindings:
                code = schema_to_evdev_code(binding.input_code)
                if code is not None:
                    layer_bindings[code] = binding

            self._bindings[layer.id] = layer_bindings

            # Track layer modifiers (hold key to activate layer)
            if layer.hold_modifier_input_code:
                mod_code = schema_to_evdev_code(layer.hold_modifier_input_code)
                if mod_code is not None:
                    self._layer_modifiers[mod_code] = layer.id

    def set_uinput(self, uinput: UInput) -> None:
        """Set the uinput device for output."""
        self._uinput = uinput

    def process_event(self, event: InputEvent) -> bool:
        """Process an input event and emit remapped output.

        Returns True if the event was handled (consumed), False if it should pass through.
        """
        if event.type != ecodes.EV_KEY:
            # Pass through non-key events (mouse motion, scroll, etc.)
            return False

        code = event.code
        value = event.value  # 0=up, 1=down, 2=repeat

        # Handle layer modifier keys first
        if code in self._layer_modifiers:
            return self._handle_layer_modifier(code, value)

        # Handle regular key/button events
        if value == 1:  # Key down
            return self._handle_key_down(code)
        elif value == 0:  # Key up
            return self._handle_key_up(code)
        elif value == 2:  # Repeat
            return self._handle_key_repeat(code)

        return False

    def _handle_layer_modifier(self, code: int, value: int) -> bool:
        """Handle a layer modifier key (Hypershift-style)."""
        layer_id = self._layer_modifiers[code]

        if value == 1:  # Modifier pressed - activate layer
            # Release any keys that would change behavior on the new layer
            self._release_conflicting_keys(layer_id)

            self.state.active_layer = layer_id
            self.state.layer_modifier_held = code
            # print(f"[Layer] Activated: {layer_id}")

        elif value == 0:  # Modifier released - return to base
            if self.state.layer_modifier_held == code:
                # Release any keys that were activated on this layer
                self._release_layer_keys(layer_id)

                self.state.active_layer = "base"
                self.state.layer_modifier_held = None
                # print(f"[Layer] Returned to: base")

        # Layer modifiers are consumed (not passed through)
        return True

    def _release_conflicting_keys(self, new_layer: str) -> None:
        """Release keys that have different bindings on the new layer.

        This prevents stuck keys when switching layers.
        """
        to_release = []

        for input_code, active in self.state.active_bindings.items():
            # Check if this key has a different binding on the new layer
            new_binding = self._get_binding_for_layer(input_code, new_layer)
            old_binding = active.binding

            # If binding differs, release the old output
            if new_binding != old_binding:
                to_release.append(input_code)

        for input_code in to_release:
            self._release_active_binding(input_code)

    def _release_layer_keys(self, layer_id: str) -> None:
        """Release all keys that were activated while on a specific layer."""
        to_release = []

        for input_code, active in self.state.active_bindings.items():
            if active.layer_id == layer_id:
                to_release.append(input_code)

        for input_code in to_release:
            self._release_active_binding(input_code)

    def _release_active_binding(self, input_code: int) -> None:
        """Release an active binding's output keys."""
        if input_code not in self.state.active_bindings:
            return

        active = self.state.active_bindings[input_code]

        # Release output keys in reverse order
        for output_code in reversed(active.output_codes):
            self._emit_key(output_code, 0)
            self.state.output_held.discard(output_code)

        del self.state.active_bindings[input_code]

    def _handle_key_down(self, code: int) -> bool:
        """Handle a key/button press."""
        self.state.physical_pressed.add(code)

        # Look up binding in current layer
        binding = self._get_binding(code)

        if binding is None:
            # No binding - pass through
            return False

        # Track this as an active binding
        active = ActiveBinding(
            input_code=code,
            binding=binding,
            layer_id=self.state.active_layer,
            output_codes=[],
        )

        # Execute the binding
        output_codes = self._execute_binding_down(binding)
        active.output_codes = output_codes

        # Track output keys as held
        for oc in output_codes:
            self.state.output_held.add(oc)

        self.state.active_bindings[code] = active
        return True

    def _handle_key_up(self, code: int) -> bool:
        """Handle a key/button release."""
        self.state.physical_pressed.discard(code)

        # Check if we have an active binding for this key
        if code in self.state.active_bindings:
            self._release_active_binding(code)
            return True

        # No active binding - might have been passthrough
        return False

    def _handle_key_repeat(self, code: int) -> bool:
        """Handle a key repeat event."""
        # For now, consume repeats for bound keys
        if code in self.state.active_bindings:
            return True
        return False

    def _get_binding(self, code: int) -> Binding | None:
        """Get the binding for a key code in the current layer."""
        return self._get_binding_for_layer(code, self.state.active_layer)

    def _get_binding_for_layer(self, code: int, layer_id: str) -> Binding | None:
        """Get the binding for a key code in a specific layer."""
        # Check specified layer
        if layer_id in self._bindings:
            binding = self._bindings[layer_id].get(code)
            if binding:
                return binding

        # Fall back to base layer (unless we're already checking base)
        if layer_id != "base" and "base" in self._bindings:
            return self._bindings["base"].get(code)

        return None

    def _execute_binding_down(self, binding: Binding) -> list[int]:
        """Execute a binding on key down. Returns list of output codes held."""
        output_codes = []

        if binding.action_type == ActionType.PASSTHROUGH:
            code = schema_to_evdev_code(binding.input_code)
            if code:
                self._emit_key(code, 1)
                output_codes.append(code)

        elif binding.action_type == ActionType.KEY:
            if binding.output_keys:
                code = schema_to_evdev_code(binding.output_keys[0])
                if code:
                    self._emit_key(code, 1)
                    output_codes.append(code)

        elif binding.action_type == ActionType.CHORD:
            # Press all keys in order
            for key in binding.output_keys:
                code = schema_to_evdev_code(key)
                if code:
                    self._emit_key(code, 1)
                    output_codes.append(code)

        elif binding.action_type == ActionType.MACRO:
            # Execute macro (fire-and-forget, no held keys)
            if binding.macro_id and binding.macro_id in self._macros:
                self._execute_macro(self._macros[binding.macro_id])

        elif binding.action_type == ActionType.DISABLED:
            # Consume the event, output nothing
            pass

        return output_codes

    def _emit_key(self, code: int, value: int) -> None:
        """Emit a key event through uinput."""
        if self._uinput:
            self._uinput.write(ecodes.EV_KEY, code, value)
            self._uinput.syn()

    def _execute_macro(self, macro: MacroAction) -> None:
        """Execute a macro sequence."""
        for repeat in range(macro.repeat_count):
            for step in macro.steps:
                self._execute_macro_step(step)

            if macro.repeat_delay_ms > 0 and repeat < macro.repeat_count - 1:
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
                    time.sleep(0.01)
                    self._emit_key(code, 0)

        elif step.type == MacroStepType.DELAY:
            if step.delay_ms:
                time.sleep(step.delay_ms / 1000.0)

        elif step.type == MacroStepType.TEXT:
            if step.text:
                self._type_text(step.text)

    def _type_text(self, text: str) -> None:
        """Type a text string by emitting key events."""
        char_to_key = {
            " ": "SPACE",
            "\n": "ENTER",
            "\t": "TAB",
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
                continue

            code = schema_to_evdev_code(key)
            if code:
                if needs_shift:
                    shift_code = schema_to_evdev_code("SHIFT")
                    if shift_code:
                        self._emit_key(shift_code, 1)

                self._emit_key(code, 1)
                time.sleep(0.01)
                self._emit_key(code, 0)

                if needs_shift and shift_code:
                    self._emit_key(shift_code, 0)

                time.sleep(0.01)

    def release_all_keys(self) -> None:
        """Release all currently held output keys. Call on shutdown."""
        # Release all active bindings
        for input_code in list(self.state.active_bindings.keys()):
            self._release_active_binding(input_code)

        # Safety: release any tracked output keys
        for code in list(self.state.output_held):
            self._emit_key(code, 0)
        self.state.output_held.clear()

    def reload_profile(self, profile: Profile) -> None:
        """Reload with a new profile."""
        # Release all held keys first
        self.release_all_keys()

        # Reset state
        self.profile = profile
        self.state = KeyState()
        self._bindings.clear()
        self._macros.clear()
        self._layer_modifiers.clear()
        self._layer_by_id.clear()

        # Rebuild lookup tables
        self._build_lookup_tables()

    def get_layer_info(self) -> dict:
        """Get current layer state info (for debugging/GUI)."""
        return {
            "active_layer": self.state.active_layer,
            "layer_modifier_held": self.state.layer_modifier_held,
            "active_bindings": len(self.state.active_bindings),
            "output_held": len(self.state.output_held),
            "available_layers": list(self._bindings.keys()),
        }
