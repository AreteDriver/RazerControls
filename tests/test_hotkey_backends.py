"""Tests for hotkey backends."""

import os
from unittest.mock import MagicMock, patch

from apps.tray.hotkey_backends import (
    PortalGlobalShortcuts,
    X11Hotkeys,
    to_portal_format,
)
from apps.tray.hotkeys import HotkeyListener
from crates.profile_schema import HotkeyBinding, SettingsManager


class TestToPortalFormat:
    """Tests for shortcut format conversion."""

    def test_ctrl_shift_number(self):
        """Test Ctrl+Shift+1 conversion."""
        binding = HotkeyBinding(modifiers=["ctrl", "shift"], key="1")
        assert to_portal_format(binding) == "<Primary><Shift>1"

    def test_ctrl_alt_letter(self):
        """Test Ctrl+Alt+A conversion."""
        binding = HotkeyBinding(modifiers=["ctrl", "alt"], key="a")
        assert to_portal_format(binding) == "<Primary><Alt>a"

    def test_alt_function_key(self):
        """Test Alt+F1 conversion."""
        binding = HotkeyBinding(modifiers=["alt"], key="f1")
        assert to_portal_format(binding) == "<Alt>F1"

    def test_shift_only(self):
        """Test Shift+X conversion."""
        binding = HotkeyBinding(modifiers=["shift"], key="x")
        assert to_portal_format(binding) == "<Shift>x"

    def test_all_modifiers(self):
        """Test Ctrl+Alt+Shift+Z conversion."""
        binding = HotkeyBinding(modifiers=["ctrl", "alt", "shift"], key="z")
        assert to_portal_format(binding) == "<Primary><Alt><Shift>z"

    def test_function_key_only(self):
        """Test F12 with no modifiers."""
        binding = HotkeyBinding(modifiers=[], key="f12")
        assert to_portal_format(binding) == "F12"

    def test_multi_char_key(self):
        """Test multi-char non-function key capitalization."""
        binding = HotkeyBinding(modifiers=["ctrl"], key="escape")
        assert to_portal_format(binding) == "<Primary>Escape"

    def test_special_key_name(self):
        """Test special key names like space."""
        binding = HotkeyBinding(modifiers=["alt"], key="space")
        assert to_portal_format(binding) == "<Alt>Space"


class TestPortalGlobalShortcuts:
    """Tests for Portal backend."""

    def test_not_available_on_x11(self):
        """Portal should not be available on X11."""
        with patch.dict(os.environ, {"XDG_SESSION_TYPE": "x11"}):
            backend = PortalGlobalShortcuts(lambda x: None)
            assert not backend.is_available()

    def test_not_available_without_wayland(self):
        """Portal should not be available without Wayland."""
        with patch.dict(os.environ, {"XDG_SESSION_TYPE": ""}):
            backend = PortalGlobalShortcuts(lambda x: None)
            assert not backend.is_available()

    def test_checks_wayland_session(self):
        """Portal checks for Wayland session type."""
        with patch.dict(os.environ, {"XDG_SESSION_TYPE": "wayland"}):
            with patch("pydbus.SessionBus") as mock_bus:
                # Simulate portal not available
                mock_bus.side_effect = Exception("No portal")
                backend = PortalGlobalShortcuts(lambda x: None)
                assert not backend.is_available()

    def test_name_property(self):
        """Backend name should be class name."""
        backend = PortalGlobalShortcuts(lambda x: None)
        assert backend.name == "PortalGlobalShortcuts"

    def test_register_shortcuts(self):
        """Register shortcuts should store them."""
        backend = PortalGlobalShortcuts(lambda x: None)
        shortcuts = [
            ("profile_0", HotkeyBinding(modifiers=["ctrl"], key="1")),
            ("profile_1", HotkeyBinding(modifiers=["ctrl"], key="2")),
        ]
        assert backend.register_shortcuts(shortcuts)
        assert backend._shortcuts == shortcuts

    def test_is_available_interface_not_found(self):
        """Portal not available if GlobalShortcuts interface missing."""
        with patch.dict(os.environ, {"XDG_SESSION_TYPE": "wayland"}):
            with patch("pydbus.SessionBus") as mock_bus:
                mock_portal = MagicMock()
                # Return XML without GlobalShortcuts interface
                mock_portal.Introspect.return_value = "<node><interface name='org.freedesktop.portal.Other'/></node>"
                mock_bus.return_value.get.return_value = mock_portal
                backend = PortalGlobalShortcuts(lambda x: None)
                assert not backend.is_available()

    def test_is_available_success(self):
        """Portal available when all conditions met."""
        with patch.dict(os.environ, {"XDG_SESSION_TYPE": "wayland"}):
            with patch("pydbus.SessionBus") as mock_bus:
                mock_portal = MagicMock()
                mock_portal.Introspect.return_value = "<node><interface name='org.freedesktop.portal.GlobalShortcuts'/></node>"
                mock_bus.return_value.get.return_value = mock_portal
                backend = PortalGlobalShortcuts(lambda x: None)
                assert backend.is_available()

    def test_start_already_running(self):
        """Start should no-op if already running."""
        backend = PortalGlobalShortcuts(lambda x: None)
        backend._running = True
        # If it tried to access pydbus, this would fail
        backend.start()
        assert backend._running

    def test_start_import_error(self):
        """Start should handle missing pydbus gracefully."""
        backend = PortalGlobalShortcuts(lambda x: None)
        with patch.dict("sys.modules", {"pydbus": None}):
            with patch("builtins.__import__", side_effect=ImportError("No module")):
                backend.start()
                assert not backend._running

    def test_start_exception(self):
        """Start should handle exceptions gracefully."""
        backend = PortalGlobalShortcuts(lambda x: None)
        with patch("pydbus.SessionBus", side_effect=Exception("D-Bus error")):
            backend.start()
            assert not backend._running

    def test_start_no_session_handle(self):
        """Start should handle failed session creation."""
        backend = PortalGlobalShortcuts(lambda x: None)
        with patch("pydbus.SessionBus") as mock_bus:
            mock_portal = MagicMock()
            mock_con = MagicMock()
            mock_con.get_unique_name.return_value = ":1.123"
            mock_bus.return_value.con = mock_con
            mock_bus.return_value.get.return_value = mock_portal
            # Don't set session handle (timeout scenario)
            backend.start()
            # Session handle was never set
            assert not backend._running

    def test_stop_not_running(self):
        """Stop should no-op if not running."""
        backend = PortalGlobalShortcuts(lambda x: None)
        backend._running = False
        backend.stop()  # Should not raise

    def test_stop_cleans_up(self):
        """Stop should clean up resources."""
        backend = PortalGlobalShortcuts(lambda x: None)
        backend._running = True
        backend._bus = MagicMock()
        backend._portal = MagicMock()
        backend._session_handle = "/session/test"
        backend._signal_subscription = 123
        backend.stop()
        assert not backend._running
        assert backend._session_handle is None
        assert backend._portal is None
        assert backend._bus is None

    def test_stop_handles_exception(self):
        """Stop should handle exceptions gracefully."""
        backend = PortalGlobalShortcuts(lambda x: None)
        backend._running = True
        backend._bus = MagicMock()
        backend._bus.con.signal_unsubscribe.side_effect = Exception("Unsubscribe error")
        backend._signal_subscription = 123
        # Should not raise
        backend.stop()


class TestX11Hotkeys:
    """Tests for X11 backend."""

    def test_available_on_x11(self):
        """X11 backend should be available on X11."""
        with patch.dict(os.environ, {"XDG_SESSION_TYPE": "x11"}):
            backend = X11Hotkeys(lambda x: None)
            assert backend.is_available()

    def test_available_when_unset(self):
        """X11 backend should be available when session type not set."""
        with patch.dict(os.environ, {"XDG_SESSION_TYPE": ""}, clear=False):
            # Remove the key entirely for this test
            env = os.environ.copy()
            if "XDG_SESSION_TYPE" in env:
                del env["XDG_SESSION_TYPE"]
            with patch.dict(os.environ, env, clear=True):
                backend = X11Hotkeys(lambda x: None)
                # Will check pynput import
                assert backend.is_available()

    def test_not_available_on_wayland(self):
        """X11 backend should not be available on Wayland."""
        with patch.dict(os.environ, {"XDG_SESSION_TYPE": "wayland"}):
            backend = X11Hotkeys(lambda x: None)
            assert not backend.is_available()

    def test_name_property(self):
        """Backend name should be class name."""
        backend = X11Hotkeys(lambda x: None)
        assert backend.name == "X11Hotkeys"

    def test_register_shortcuts(self):
        """Register shortcuts should store them."""
        backend = X11Hotkeys(lambda x: None)
        shortcuts = [
            ("profile_0", HotkeyBinding(modifiers=["ctrl"], key="1")),
        ]
        assert backend.register_shortcuts(shortcuts)
        assert backend._shortcuts == shortcuts

    def test_check_binding_matching(self):
        """Check binding should match pressed keys."""
        backend = X11Hotkeys(lambda x: None)
        binding = HotkeyBinding(modifiers=["ctrl", "shift"], key="1", enabled=True)

        # No keys pressed
        assert not backend._check_binding(binding)

        # Some modifiers pressed
        backend._current_keys = {"ctrl"}
        assert not backend._check_binding(binding)

        # All modifiers but not key
        backend._current_keys = {"ctrl", "shift"}
        assert not backend._check_binding(binding)

        # All pressed
        backend._current_keys = {"ctrl", "shift", "1"}
        assert backend._check_binding(binding)

    def test_check_binding_disabled(self):
        """Disabled bindings should not match."""
        backend = X11Hotkeys(lambda x: None)
        binding = HotkeyBinding(modifiers=["ctrl"], key="1", enabled=False)
        backend._current_keys = {"ctrl", "1"}
        assert not backend._check_binding(binding)

    def test_check_binding_empty_key(self):
        """Empty key bindings should not match."""
        backend = X11Hotkeys(lambda x: None)
        binding = HotkeyBinding(modifiers=["ctrl"], key="", enabled=True)
        backend._current_keys = {"ctrl"}
        assert not backend._check_binding(binding)

    def test_is_available_pynput_import_error(self):
        """X11 not available if pynput import fails."""
        with patch.dict(os.environ, {"XDG_SESSION_TYPE": "x11"}):
            with patch.dict("sys.modules", {"pynput": None, "pynput.keyboard": None}):
                with patch("builtins.__import__", side_effect=ImportError("No module")):
                    backend = X11Hotkeys(lambda x: None)
                    assert not backend.is_available()

    def test_start_already_running(self):
        """Start should no-op if listener exists."""
        backend = X11Hotkeys(lambda x: None)
        backend._listener = MagicMock()
        # No import needed since listener exists
        backend.start()
        assert backend._listener is not None

    def test_start_creates_listener(self):
        """Start should create and start pynput listener."""
        backend = X11Hotkeys(lambda x: None)
        mock_listener = MagicMock()
        with patch("pynput.keyboard.Listener", return_value=mock_listener):
            backend.start()
            mock_listener.start.assert_called_once()
            assert backend._listener is mock_listener

    def test_start_exception(self):
        """Start should handle exceptions gracefully."""
        backend = X11Hotkeys(lambda x: None)
        with patch("pynput.keyboard.Listener", side_effect=Exception("Listener error")):
            backend.start()
            assert backend._listener is None

    def test_stop_clears_listener(self):
        """Stop should stop and clear listener."""
        backend = X11Hotkeys(lambda x: None)
        mock_listener = MagicMock()
        backend._listener = mock_listener
        backend._current_keys = {"ctrl", "a"}
        backend._triggered = {"profile_0"}
        backend.stop()
        mock_listener.stop.assert_called_once()
        assert backend._listener is None
        assert len(backend._current_keys) == 0
        assert len(backend._triggered) == 0

    def test_stop_no_listener(self):
        """Stop should no-op if no listener."""
        backend = X11Hotkeys(lambda x: None)
        backend._listener = None
        backend.stop()  # Should not raise

    def test_normalize_key_ctrl_left(self):
        """Normalize ctrl_l to ctrl."""
        backend = X11Hotkeys(lambda x: None)
        from pynput import keyboard
        assert backend._normalize_key(keyboard.Key.ctrl_l) == "ctrl"

    def test_normalize_key_ctrl_right(self):
        """Normalize ctrl_r to ctrl."""
        backend = X11Hotkeys(lambda x: None)
        from pynput import keyboard
        assert backend._normalize_key(keyboard.Key.ctrl_r) == "ctrl"

    def test_normalize_key_shift_left(self):
        """Normalize shift_l to shift."""
        backend = X11Hotkeys(lambda x: None)
        from pynput import keyboard
        assert backend._normalize_key(keyboard.Key.shift_l) == "shift"

    def test_normalize_key_shift_right(self):
        """Normalize shift_r to shift."""
        backend = X11Hotkeys(lambda x: None)
        from pynput import keyboard
        assert backend._normalize_key(keyboard.Key.shift_r) == "shift"

    def test_normalize_key_alt_left(self):
        """Normalize alt_l to alt."""
        backend = X11Hotkeys(lambda x: None)
        from pynput import keyboard
        assert backend._normalize_key(keyboard.Key.alt_l) == "alt"

    def test_normalize_key_alt_right(self):
        """Normalize alt_r to alt."""
        backend = X11Hotkeys(lambda x: None)
        from pynput import keyboard
        assert backend._normalize_key(keyboard.Key.alt_r) == "alt"

    def test_normalize_key_function_keys(self):
        """Normalize function keys F1-F12."""
        backend = X11Hotkeys(lambda x: None)
        from pynput import keyboard
        for i in range(1, 13):
            key = getattr(keyboard.Key, f"f{i}")
            assert backend._normalize_key(key) == f"f{i}"

    def test_normalize_key_char(self):
        """Normalize character keys."""
        backend = X11Hotkeys(lambda x: None)
        from pynput.keyboard import KeyCode
        # Lowercase char
        key = KeyCode(char="a")
        assert backend._normalize_key(key) == "a"
        # Uppercase char (should normalize to lowercase)
        key = KeyCode(char="A")
        assert backend._normalize_key(key) == "a"

    def test_normalize_key_number_vk(self):
        """Normalize number keys via vk codes."""
        backend = X11Hotkeys(lambda x: None)
        from pynput.keyboard import KeyCode
        # Number 1 (vk 49)
        key = KeyCode(vk=49)
        assert backend._normalize_key(key) == "1"
        # Number 0 (vk 48)
        key = KeyCode(vk=48)
        assert backend._normalize_key(key) == "0"
        # Number 9 (vk 57)
        key = KeyCode(vk=57)
        assert backend._normalize_key(key) == "9"

    def test_normalize_key_letter_vk(self):
        """Normalize letter keys via vk codes."""
        backend = X11Hotkeys(lambda x: None)
        from pynput.keyboard import KeyCode
        # Letter A (vk 65)
        key = KeyCode(vk=65)
        assert backend._normalize_key(key) == "a"
        # Letter Z (vk 90)
        key = KeyCode(vk=90)
        assert backend._normalize_key(key) == "z"

    def test_normalize_key_unknown(self):
        """Unknown keys return None."""
        backend = X11Hotkeys(lambda x: None)
        from pynput import keyboard
        from pynput.keyboard import KeyCode
        # Unknown special key
        result = backend._normalize_key(keyboard.Key.caps_lock)
        assert result is None
        # Unknown vk code
        key = KeyCode(vk=999)
        assert backend._normalize_key(key) is None

    def test_on_press_adds_key(self):
        """_on_press should add normalized key to current_keys."""
        backend = X11Hotkeys(lambda x: None)
        from pynput.keyboard import KeyCode
        key = KeyCode(char="a")
        backend._on_press(key)
        assert "a" in backend._current_keys

    def test_on_press_triggers_callback(self):
        """_on_press should trigger callback when shortcut matches."""
        callback = MagicMock()
        backend = X11Hotkeys(callback)
        binding = HotkeyBinding(modifiers=["ctrl"], key="a", enabled=True)
        backend._shortcuts = [("profile_0", binding)]
        backend._current_keys = {"ctrl"}

        from pynput.keyboard import KeyCode
        key = KeyCode(char="a")
        backend._on_press(key)

        callback.assert_called_once_with("profile_0")
        assert "profile_0" in backend._triggered

    def test_on_press_no_double_trigger(self):
        """_on_press should not trigger same shortcut twice."""
        callback = MagicMock()
        backend = X11Hotkeys(callback)
        binding = HotkeyBinding(modifiers=["ctrl"], key="a", enabled=True)
        backend._shortcuts = [("profile_0", binding)]
        backend._current_keys = {"ctrl"}
        backend._triggered = {"profile_0"}  # Already triggered

        from pynput.keyboard import KeyCode
        key = KeyCode(char="a")
        backend._on_press(key)

        callback.assert_not_called()

    def test_on_release_removes_key(self):
        """_on_release should remove key from current_keys."""
        backend = X11Hotkeys(lambda x: None)
        backend._current_keys = {"ctrl", "a"}

        from pynput.keyboard import KeyCode
        key = KeyCode(char="a")
        backend._on_release(key)

        assert "a" not in backend._current_keys
        assert "ctrl" in backend._current_keys

    def test_on_release_clears_triggered(self):
        """_on_release should clear triggered state for inactive shortcuts."""
        backend = X11Hotkeys(lambda x: None)
        binding = HotkeyBinding(modifiers=["ctrl"], key="a", enabled=True)
        backend._shortcuts = [("profile_0", binding)]
        backend._current_keys = {"ctrl", "a"}
        backend._triggered = {"profile_0"}

        from pynput.keyboard import KeyCode
        key = KeyCode(char="a")
        backend._on_release(key)

        assert "profile_0" not in backend._triggered


class TestHotkeyListener:
    """Tests for HotkeyListener."""

    def test_selects_x11_on_x11_session(self):
        """Should select X11 backend on X11 session."""
        with patch.dict(os.environ, {"XDG_SESSION_TYPE": "x11"}):
            callback = MagicMock()
            listener = HotkeyListener(callback)
            assert listener.backend_name == "X11Hotkeys"

    def test_no_backend_when_none_available(self):
        """Should have no backend when none available."""
        with patch.dict(os.environ, {"XDG_SESSION_TYPE": "wayland"}):
            with patch(
                "apps.tray.hotkey_backends.PortalGlobalShortcuts.is_available",
                return_value=False,
            ):
                with patch(
                    "apps.tray.hotkey_backends.X11Hotkeys.is_available",
                    return_value=False,
                ):
                    callback = MagicMock()
                    listener = HotkeyListener(callback)
                    assert listener.backend_name is None

    def test_build_shortcuts(self):
        """Should build shortcuts from settings."""
        with patch.dict(os.environ, {"XDG_SESSION_TYPE": "x11"}):
            callback = MagicMock()
            settings = SettingsManager()
            listener = HotkeyListener(callback, settings)

            shortcuts = listener._build_shortcuts()
            # Default settings have 9 enabled shortcuts
            assert len(shortcuts) == 9
            assert shortcuts[0][0] == "profile_0"
            assert shortcuts[0][1].key == "1"

    def test_on_shortcut_activated(self):
        """Should call callback with profile index."""
        with patch.dict(os.environ, {"XDG_SESSION_TYPE": "x11"}):
            callback = MagicMock()
            listener = HotkeyListener(callback)

            listener._on_shortcut_activated("profile_3")
            callback.assert_called_once_with(3)

    def test_on_shortcut_activated_invalid(self):
        """Should handle invalid action IDs gracefully."""
        with patch.dict(os.environ, {"XDG_SESSION_TYPE": "x11"}):
            callback = MagicMock()
            listener = HotkeyListener(callback)

            # Should not crash
            listener._on_shortcut_activated("invalid")
            listener._on_shortcut_activated("profile_")
            listener._on_shortcut_activated("profile_abc")
            callback.assert_not_called()

    def test_start_registers_shortcuts(self):
        """Start should register shortcuts with backend."""
        with patch.dict(os.environ, {"XDG_SESSION_TYPE": "x11"}):
            callback = MagicMock()
            listener = HotkeyListener(callback)

            with patch.object(listener._backend, "register_shortcuts") as mock_register:
                with patch.object(listener._backend, "start"):
                    listener.start()
                    mock_register.assert_called_once()

    def test_stop_stops_backend(self):
        """Stop should stop the backend."""
        with patch.dict(os.environ, {"XDG_SESSION_TYPE": "x11"}):
            callback = MagicMock()
            listener = HotkeyListener(callback)

            with patch.object(listener._backend, "stop") as mock_stop:
                listener.stop()
                mock_stop.assert_called_once()
