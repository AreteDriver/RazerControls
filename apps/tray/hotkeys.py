"""Global hotkey listener for profile switching.

Listens for Ctrl+Shift+1 through Ctrl+Shift+9 to switch profiles by position.
"""

from collections.abc import Callable

from pynput import keyboard


class HotkeyListener:
    """Global hotkey listener for profile switching.

    Listens for Ctrl+Shift+{1-9} and calls the callback with the profile index.
    """

    def __init__(self, on_profile_switch: Callable[[int], None]):
        """Initialize the hotkey listener.

        Args:
            on_profile_switch: Callback called with profile index (0-8) when hotkey pressed.
        """
        self.on_profile_switch = on_profile_switch
        self.current_keys: set = set()
        self.listener: keyboard.Listener | None = None
        self._triggered: set[int] = set()  # Prevent repeated triggers while held

    def start(self) -> None:
        """Start listening for hotkeys."""
        self.listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self.listener.daemon = True
        self.listener.start()

    def stop(self) -> None:
        """Stop listening for hotkeys."""
        if self.listener:
            self.listener.stop()
            self.listener = None

    def _normalize_key(self, key) -> str | None:
        """Normalize a key to a comparable string."""
        if isinstance(key, keyboard.Key):
            # Handle modifier keys
            if key in (keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
                return "ctrl"
            if key in (keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r):
                return "shift"
            return None
        elif isinstance(key, keyboard.KeyCode):
            if key.char:
                return key.char
            # Handle numpad and other special keys
            if key.vk is not None:
                # Number keys 1-9 have vk codes 49-57
                if 49 <= key.vk <= 57:
                    return str(key.vk - 48)
        return None

    def _on_press(self, key) -> None:
        """Handle key press event."""
        normalized = self._normalize_key(key)
        if normalized:
            self.current_keys.add(normalized)

        # Check for Ctrl+Shift+{1-9}
        if "ctrl" in self.current_keys and "shift" in self.current_keys:
            for i in range(1, 10):
                if str(i) in self.current_keys and i not in self._triggered:
                    self._triggered.add(i)
                    self.on_profile_switch(i - 1)  # 0-indexed
                    break

    def _on_release(self, key) -> None:
        """Handle key release event."""
        normalized = self._normalize_key(key)
        if normalized:
            self.current_keys.discard(normalized)

            # Clear triggered state when number key released
            if normalized.isdigit():
                self._triggered.discard(int(normalized))
