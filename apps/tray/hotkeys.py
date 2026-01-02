"""Global hotkey listener for profile switching.

Listens for customizable hotkeys to switch profiles by position.
"""

from collections.abc import Callable

from pynput import keyboard

from crates.profile_schema import HotkeyBinding, SettingsManager


class HotkeyListener:
    """Global hotkey listener for profile switching.

    Listens for user-configured hotkeys and calls the callback with profile index.
    """

    def __init__(
        self,
        on_profile_switch: Callable[[int], None],
        settings_manager: SettingsManager | None = None,
    ):
        """Initialize the hotkey listener.

        Args:
            on_profile_switch: Callback called with profile index (0-8) when hotkey pressed.
            settings_manager: Settings manager for hotkey configuration.
        """
        self.on_profile_switch = on_profile_switch
        self.settings_manager = settings_manager or SettingsManager()
        self.current_keys: set = set()
        self.listener: keyboard.Listener | None = None
        self._triggered: set[int] = set()  # Prevent repeated triggers while held

    def get_bindings(self) -> list[HotkeyBinding]:
        """Get current hotkey bindings from settings."""
        return self.settings_manager.settings.hotkeys.profile_hotkeys

    def reload_bindings(self) -> None:
        """Reload bindings from settings (call after settings change)."""
        # Force reload settings from disk
        self.settings_manager._settings = None
        self.settings_manager.load()

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
            if key in (keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r):
                return "alt"
            # Handle function keys
            for i in range(1, 13):
                if key == getattr(keyboard.Key, f"f{i}", None):
                    return f"f{i}"
            return None
        elif isinstance(key, keyboard.KeyCode):
            if key.char:
                return key.char.lower()
            # Handle numpad and other special keys
            if key.vk is not None:
                # Number keys 1-9 have vk codes 49-57
                if 49 <= key.vk <= 57:
                    return str(key.vk - 48)
                # Letter keys A-Z have vk codes 65-90
                if 65 <= key.vk <= 90:
                    return chr(key.vk).lower()
        return None

    def _check_binding(self, binding: HotkeyBinding) -> bool:
        """Check if a binding matches current pressed keys."""
        if not binding.enabled or not binding.key:
            return False

        # Check all required modifiers are pressed
        for mod in binding.modifiers:
            if mod not in self.current_keys:
                return False

        # Check the main key is pressed
        return binding.key.lower() in self.current_keys

    def _on_press(self, key) -> None:
        """Handle key press event."""
        normalized = self._normalize_key(key)
        if normalized:
            self.current_keys.add(normalized)

        # Check each hotkey binding
        bindings = self.get_bindings()
        for i, binding in enumerate(bindings):
            if i not in self._triggered and self._check_binding(binding):
                self._triggered.add(i)
                self.on_profile_switch(i)
                break

    def _on_release(self, key) -> None:
        """Handle key release event."""
        normalized = self._normalize_key(key)
        if normalized:
            self.current_keys.discard(normalized)

            # Clear triggered state when key released
            # Check which bindings are no longer active
            bindings = self.get_bindings()
            for i, binding in enumerate(bindings):
                if i in self._triggered and not self._check_binding(binding):
                    self._triggered.discard(i)
