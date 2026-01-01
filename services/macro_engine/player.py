"""Macro player - executes macros through uinput."""

import time
from collections.abc import Callable

from evdev import UInput, ecodes

from crates.keycode_map import schema_to_evdev_code
from crates.profile_schema import MacroAction, MacroStep, MacroStepType


class MacroPlayer:
    """Plays back macros by emitting key events.

    Usage:
        player = MacroPlayer()
        player.play(macro)
    """

    def __init__(self, uinput: UInput | None = None):
        """Initialize player.

        Args:
            uinput: UInput device to emit events. If None, one will be created.
        """
        self._uinput = uinput
        self._owns_uinput = False
        self._playing = False
        self._cancelled = False
        self._on_step: Callable[[MacroStep, int], None] | None = None

    def _ensure_uinput(self) -> None:
        """Ensure we have a uinput device."""
        if self._uinput is None:
            capabilities = {
                ecodes.EV_KEY: list(range(0, 256)) + list(range(0x110, 0x120)),
            }
            self._uinput = UInput(capabilities, name="Razer Macro Player")
            self._owns_uinput = True

    def close(self) -> None:
        """Close the uinput device if we own it."""
        if self._owns_uinput and self._uinput:
            self._uinput.close()
            self._uinput = None
            self._owns_uinput = False

    def set_uinput(self, uinput: UInput) -> None:
        """Set the uinput device to use."""
        if self._owns_uinput and self._uinput:
            self._uinput.close()
            self._owns_uinput = False
        self._uinput = uinput

    def set_step_callback(self, callback: Callable[[MacroStep, int], None]) -> None:
        """Set callback for each step executed.

        Args:
            callback: Called with (step, step_index) for each step
        """
        self._on_step = callback

    def is_playing(self) -> bool:
        """Check if currently playing."""
        return self._playing

    def cancel(self) -> None:
        """Cancel the current playback."""
        self._cancelled = True

    def play(
        self,
        macro: MacroAction,
        speed_multiplier: float = 1.0,
    ) -> bool:
        """Play a macro.

        Args:
            macro: The macro to play
            speed_multiplier: Speed multiplier (0.5 = half speed, 2.0 = double)

        Returns:
            True if completed, False if cancelled
        """
        self._ensure_uinput()
        self._playing = True
        self._cancelled = False

        try:
            for repeat in range(macro.repeat_count):
                if self._cancelled:
                    return False

                for i, step in enumerate(macro.steps):
                    if self._cancelled:
                        return False

                    if self._on_step:
                        self._on_step(step, i)

                    self._execute_step(step, speed_multiplier)

                # Repeat delay
                if macro.repeat_delay_ms > 0 and repeat < macro.repeat_count - 1:
                    delay = macro.repeat_delay_ms / 1000.0 / speed_multiplier
                    if not self._sleep_interruptible(delay):
                        return False

            return True

        finally:
            self._playing = False

    def _execute_step(self, step: MacroStep, speed_multiplier: float) -> None:
        """Execute a single macro step."""
        if step.type == MacroStepType.KEY_DOWN:
            if step.key:
                code = schema_to_evdev_code(step.key)
                if code is not None:
                    self._emit_key(code, 1)

        elif step.type == MacroStepType.KEY_UP:
            if step.key:
                code = schema_to_evdev_code(step.key)
                if code is not None:
                    self._emit_key(code, 0)

        elif step.type == MacroStepType.KEY_PRESS:
            if step.key:
                code = schema_to_evdev_code(step.key)
                if code is not None:
                    self._emit_key(code, 1)
                    time.sleep(0.01 / speed_multiplier)
                    self._emit_key(code, 0)

        elif step.type == MacroStepType.DELAY:
            if step.delay_ms:
                delay = step.delay_ms / 1000.0 / speed_multiplier
                self._sleep_interruptible(delay)

        elif step.type == MacroStepType.TEXT:
            if step.text:
                self._type_text(step.text, speed_multiplier)

    def _emit_key(self, code: int, value: int) -> None:
        """Emit a key event."""
        if self._uinput:
            self._uinput.write(ecodes.EV_KEY, code, value)
            self._uinput.syn()

    def _sleep_interruptible(self, seconds: float) -> bool:
        """Sleep but check for cancellation.

        Returns:
            True if sleep completed, False if cancelled
        """
        end_time = time.time() + seconds
        while time.time() < end_time:
            if self._cancelled:
                return False
            remaining = end_time - time.time()
            time.sleep(min(0.05, remaining))
        return True

    def _type_text(self, text: str, speed_multiplier: float) -> None:
        """Type a string of text."""
        # Character to key mapping
        char_to_key = {
            " ": "SPACE",
            "\n": "ENTER",
            "\t": "TAB",
            "-": "MINUS",
            "=": "EQUAL",
            "[": "LBRACKET",
            "]": "RBRACKET",
            ";": "SEMICOLON",
            "'": "APOSTROPHE",
            "`": "GRAVE",
            "\\": "BACKSLASH",
            ",": "COMMA",
            ".": "DOT",
            "/": "SLASH",
        }

        # Shifted characters
        shift_chars = {
            "!": "1",
            "@": "2",
            "#": "3",
            "$": "4",
            "%": "5",
            "^": "6",
            "&": "7",
            "*": "8",
            "(": "9",
            ")": "0",
            "_": "MINUS",
            "+": "EQUAL",
            "{": "LBRACKET",
            "}": "RBRACKET",
            ":": "SEMICOLON",
            '"': "APOSTROPHE",
            "~": "GRAVE",
            "|": "BACKSLASH",
            "<": "COMMA",
            ">": "DOT",
            "?": "SLASH",
        }

        shift_code = schema_to_evdev_code("SHIFT")

        for char in text:
            if self._cancelled:
                return

            needs_shift = False
            key = None

            if char.isalpha():
                key = char.upper()
                needs_shift = char.isupper()
            elif char.isdigit():
                key = char
            elif char in char_to_key:
                key = char_to_key[char]
            elif char in shift_chars:
                key = shift_chars[char]
                needs_shift = True

            if key:
                code = schema_to_evdev_code(key)
                if code is not None:
                    if needs_shift and shift_code:
                        self._emit_key(shift_code, 1)

                    self._emit_key(code, 1)
                    time.sleep(0.01 / speed_multiplier)
                    self._emit_key(code, 0)

                    if needs_shift and shift_code:
                        self._emit_key(shift_code, 0)

                    time.sleep(0.01 / speed_multiplier)

    def play_steps(self, steps: list[MacroStep], speed_multiplier: float = 1.0) -> bool:
        """Play a list of steps directly.

        Args:
            steps: List of MacroStep objects
            speed_multiplier: Speed multiplier

        Returns:
            True if completed, False if cancelled
        """
        macro = MacroAction(
            id="temp",
            name="Temporary",
            steps=steps,
        )
        return self.play(macro, speed_multiplier)


def play_macro_once(macro: MacroAction, speed_multiplier: float = 1.0) -> bool:
    """Convenience function to play a macro once.

    Creates a temporary player, plays the macro, and cleans up.
    """
    player = MacroPlayer()
    try:
        return player.play(macro, speed_multiplier)
    finally:
        player.close()
