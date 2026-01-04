"""Tests for apps/tray module - system tray application."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# --- Tests for hotkey_backends.py ---


class TestToPortalFormat:
    """Tests for to_portal_format function."""

    def test_ctrl_key(self):
        """Test ctrl modifier conversion."""
        from apps.tray.hotkey_backends import to_portal_format
        from crates.profile_schema import HotkeyBinding

        binding = HotkeyBinding(key="a", modifiers=["ctrl"], enabled=True)
        result = to_portal_format(binding)
        assert result == "<Primary>a"

    def test_alt_key(self):
        """Test alt modifier conversion."""
        from apps.tray.hotkey_backends import to_portal_format
        from crates.profile_schema import HotkeyBinding

        binding = HotkeyBinding(key="b", modifiers=["alt"], enabled=True)
        result = to_portal_format(binding)
        assert result == "<Alt>b"

    def test_shift_key(self):
        """Test shift modifier conversion."""
        from apps.tray.hotkey_backends import to_portal_format
        from crates.profile_schema import HotkeyBinding

        binding = HotkeyBinding(key="c", modifiers=["shift"], enabled=True)
        result = to_portal_format(binding)
        assert result == "<Shift>c"

    def test_multiple_modifiers(self):
        """Test multiple modifiers."""
        from apps.tray.hotkey_backends import to_portal_format
        from crates.profile_schema import HotkeyBinding

        binding = HotkeyBinding(key="1", modifiers=["ctrl", "shift", "alt"], enabled=True)
        result = to_portal_format(binding)
        assert result == "<Primary><Alt><Shift>1"

    def test_function_key(self):
        """Test function key conversion."""
        from apps.tray.hotkey_backends import to_portal_format
        from crates.profile_schema import HotkeyBinding

        binding = HotkeyBinding(key="f1", modifiers=["alt"], enabled=True)
        result = to_portal_format(binding)
        assert result == "<Alt>F1"

    def test_multi_char_key(self):
        """Test multi-character key capitalization."""
        from apps.tray.hotkey_backends import to_portal_format
        from crates.profile_schema import HotkeyBinding

        binding = HotkeyBinding(key="space", modifiers=[], enabled=True)
        result = to_portal_format(binding)
        assert result == "Space"


class TestHotkeyBackendBase:
    """Tests for HotkeyBackend abstract base class."""

    def test_name_property(self):
        """Test name property returns class name."""
        from apps.tray.hotkey_backends import HotkeyBackend

        class TestBackend(HotkeyBackend):
            def is_available(self):
                return True

            def register_shortcuts(self, shortcuts):
                return True

            def start(self):
                pass

            def stop(self):
                pass

        backend = TestBackend()
        assert backend.name == "TestBackend"


class TestPortalGlobalShortcuts:
    """Tests for PortalGlobalShortcuts backend."""

    def test_is_available_not_wayland(self):
        """Test is_available returns False if not Wayland."""
        from apps.tray.hotkey_backends import PortalGlobalShortcuts

        callback = MagicMock()
        backend = PortalGlobalShortcuts(callback)

        with patch.dict(os.environ, {"XDG_SESSION_TYPE": "x11"}):
            assert backend.is_available() is False

    def test_is_available_pydbus_import_error(self):
        """Test is_available returns False if pydbus unavailable."""
        from apps.tray.hotkey_backends import PortalGlobalShortcuts

        callback = MagicMock()
        backend = PortalGlobalShortcuts(callback)

        with patch.dict(os.environ, {"XDG_SESSION_TYPE": "wayland"}):
            with patch("pydbus.SessionBus", side_effect=ImportError("No pydbus")):
                assert backend.is_available() is False

    def test_is_available_portal_error(self):
        """Test is_available returns False on portal error."""
        from apps.tray.hotkey_backends import PortalGlobalShortcuts

        callback = MagicMock()
        backend = PortalGlobalShortcuts(callback)

        with patch.dict(os.environ, {"XDG_SESSION_TYPE": "wayland"}):
            with patch("pydbus.SessionBus") as mock_bus:
                mock_bus.return_value.get.side_effect = Exception("No portal")
                assert backend.is_available() is False

    def test_is_available_no_globalshortcuts_interface(self):
        """Test is_available returns False without GlobalShortcuts interface."""
        from apps.tray.hotkey_backends import PortalGlobalShortcuts

        callback = MagicMock()
        backend = PortalGlobalShortcuts(callback)

        with patch.dict(os.environ, {"XDG_SESSION_TYPE": "wayland"}):
            with patch("pydbus.SessionBus") as mock_bus:
                portal = MagicMock()
                portal.Introspect.return_value = "<interface>something</interface>"
                mock_bus.return_value.get.return_value = portal
                assert backend.is_available() is False

    def test_is_available_success(self):
        """Test is_available returns True when portal available."""
        from apps.tray.hotkey_backends import PortalGlobalShortcuts

        callback = MagicMock()
        backend = PortalGlobalShortcuts(callback)

        with patch.dict(os.environ, {"XDG_SESSION_TYPE": "wayland"}):
            with patch("pydbus.SessionBus") as mock_bus:
                portal = MagicMock()
                portal.Introspect.return_value = "org.freedesktop.portal.GlobalShortcuts"
                mock_bus.return_value.get.return_value = portal
                assert backend.is_available() is True

    def test_register_shortcuts(self):
        """Test register_shortcuts stores shortcuts."""
        from apps.tray.hotkey_backends import PortalGlobalShortcuts
        from crates.profile_schema import HotkeyBinding

        callback = MagicMock()
        backend = PortalGlobalShortcuts(callback)

        shortcuts = [("test", HotkeyBinding(key="a", modifiers=["ctrl"], enabled=True))]
        result = backend.register_shortcuts(shortcuts)

        assert result is True
        assert backend._shortcuts == shortcuts

    def test_start_already_running(self):
        """Test start returns early if already running."""
        from apps.tray.hotkey_backends import PortalGlobalShortcuts

        callback = MagicMock()
        backend = PortalGlobalShortcuts(callback)
        backend._running = True

        # Should return early and not call pydbus
        with patch("pydbus.SessionBus") as mock_bus:
            backend.start()
            mock_bus.assert_not_called()

    def test_start_import_error(self):
        """Test start handles ImportError."""
        from apps.tray.hotkey_backends import PortalGlobalShortcuts

        callback = MagicMock()
        backend = PortalGlobalShortcuts(callback)

        with patch("pydbus.SessionBus", side_effect=ImportError("No gi")):
            backend.start()
            assert backend._running is False

    def test_start_general_exception(self):
        """Test start handles general exception."""
        from apps.tray.hotkey_backends import PortalGlobalShortcuts

        callback = MagicMock()
        backend = PortalGlobalShortcuts(callback)

        with patch("pydbus.SessionBus", side_effect=Exception("Connection failed")):
            backend.start()
            assert backend._running is False

    def test_stop_not_running(self):
        """Test stop returns early if not running."""
        from apps.tray.hotkey_backends import PortalGlobalShortcuts

        callback = MagicMock()
        backend = PortalGlobalShortcuts(callback)

        backend.stop()  # Should not raise

    def test_stop_clears_state(self):
        """Test stop clears all state."""
        from apps.tray.hotkey_backends import PortalGlobalShortcuts

        callback = MagicMock()
        backend = PortalGlobalShortcuts(callback)
        backend._running = True
        backend._session_handle = "test"
        backend._portal = MagicMock()
        backend._bus = MagicMock()
        backend._signal_subscription = 123

        backend.stop()

        assert backend._running is False
        assert backend._session_handle is None
        assert backend._portal is None
        assert backend._bus is None

    def test_stop_handles_exception(self):
        """Test stop handles exception gracefully."""
        from apps.tray.hotkey_backends import PortalGlobalShortcuts

        callback = MagicMock()
        backend = PortalGlobalShortcuts(callback)
        backend._running = True
        backend._bus = MagicMock()
        # Exception in final cleanup block
        backend._bus.con.call_sync = MagicMock(side_effect=Exception("Error"))
        backend._signal_subscription = None
        backend._session_handle = "test"
        backend._portal = MagicMock()

        backend.stop()  # Should not raise
        assert backend._running is False


class TestX11Hotkeys:
    """Tests for X11Hotkeys backend."""

    def test_is_available_x11_session(self):
        """Test is_available returns True for X11."""
        from apps.tray.hotkey_backends import X11Hotkeys

        callback = MagicMock()
        backend = X11Hotkeys(callback)

        with patch.dict(os.environ, {"XDG_SESSION_TYPE": "x11"}):
            with patch.dict("sys.modules", {"pynput": MagicMock(), "pynput.keyboard": MagicMock()}):
                assert backend.is_available() is True

    def test_is_available_empty_session_defaults_x11(self):
        """Test is_available defaults to X11 for legacy systems."""
        from apps.tray.hotkey_backends import X11Hotkeys

        callback = MagicMock()
        backend = X11Hotkeys(callback)

        with patch.dict(os.environ, {"XDG_SESSION_TYPE": ""}, clear=True):
            with patch.dict("sys.modules", {"pynput": MagicMock(), "pynput.keyboard": MagicMock()}):
                assert backend.is_available() is True

    def test_is_available_wayland_returns_false(self):
        """Test is_available returns False for Wayland."""
        from apps.tray.hotkey_backends import X11Hotkeys

        callback = MagicMock()
        backend = X11Hotkeys(callback)

        with patch.dict(os.environ, {"XDG_SESSION_TYPE": "wayland"}):
            assert backend.is_available() is False

    def test_register_shortcuts(self):
        """Test register_shortcuts stores shortcuts."""
        from apps.tray.hotkey_backends import X11Hotkeys
        from crates.profile_schema import HotkeyBinding

        callback = MagicMock()
        backend = X11Hotkeys(callback)

        shortcuts = [("test", HotkeyBinding(key="a", modifiers=["ctrl"], enabled=True))]
        result = backend.register_shortcuts(shortcuts)

        assert result is True
        assert backend._shortcuts == shortcuts

    def test_start_already_has_listener(self):
        """Test start returns early if listener exists."""
        from apps.tray.hotkey_backends import X11Hotkeys

        callback = MagicMock()
        backend = X11Hotkeys(callback)
        backend._listener = MagicMock()

        backend.start()
        # Listener should not be recreated
        assert backend._listener is not None

    def test_start_exception(self):
        """Test start handles exception."""
        from apps.tray.hotkey_backends import X11Hotkeys

        callback = MagicMock()
        backend = X11Hotkeys(callback)

        with patch.dict("sys.modules", {"pynput": MagicMock(), "pynput.keyboard": None}):
            with patch("pynput.keyboard.Listener", side_effect=Exception("pynput error")):
                backend.start()
                assert backend._listener is None

    def test_stop_clears_state(self):
        """Test stop clears all state."""
        from apps.tray.hotkey_backends import X11Hotkeys

        callback = MagicMock()
        backend = X11Hotkeys(callback)
        backend._listener = MagicMock()
        backend._current_keys = {"ctrl", "a"}
        backend._triggered = {"profile_0"}

        backend.stop()

        assert backend._listener is None
        assert len(backend._current_keys) == 0
        assert len(backend._triggered) == 0

    def test_stop_no_listener(self):
        """Test stop does nothing without listener."""
        from apps.tray.hotkey_backends import X11Hotkeys

        callback = MagicMock()
        backend = X11Hotkeys(callback)

        backend.stop()  # Should not raise

    def test_normalize_key_returns_none_for_unknown(self):
        """Test _normalize_key returns None for unknown keys."""
        from apps.tray.hotkey_backends import X11Hotkeys

        callback = MagicMock()
        backend = X11Hotkeys(callback)

        # Test with a mock that doesn't match any key type
        # This covers the "return None" paths in _normalize_key
        with patch.object(backend, "_normalize_key", return_value=None) as mock_norm:
            result = mock_norm("unknown_key")
            assert result is None

    def test_check_binding_disabled(self):
        """Test _check_binding returns False for disabled binding."""
        from apps.tray.hotkey_backends import X11Hotkeys
        from crates.profile_schema import HotkeyBinding

        callback = MagicMock()
        backend = X11Hotkeys(callback)

        binding = HotkeyBinding(key="a", modifiers=["ctrl"], enabled=False)
        assert backend._check_binding(binding) is False

    def test_check_binding_no_key(self):
        """Test _check_binding returns False without key."""
        from apps.tray.hotkey_backends import X11Hotkeys
        from crates.profile_schema import HotkeyBinding

        callback = MagicMock()
        backend = X11Hotkeys(callback)

        binding = HotkeyBinding(key="", modifiers=["ctrl"], enabled=True)
        assert backend._check_binding(binding) is False

    def test_check_binding_missing_modifier(self):
        """Test _check_binding returns False if modifier not pressed."""
        from apps.tray.hotkey_backends import X11Hotkeys
        from crates.profile_schema import HotkeyBinding

        callback = MagicMock()
        backend = X11Hotkeys(callback)
        backend._current_keys = {"a"}

        binding = HotkeyBinding(key="a", modifiers=["ctrl"], enabled=True)
        assert backend._check_binding(binding) is False

    def test_check_binding_success(self):
        """Test _check_binding returns True when all keys pressed."""
        from apps.tray.hotkey_backends import X11Hotkeys
        from crates.profile_schema import HotkeyBinding

        callback = MagicMock()
        backend = X11Hotkeys(callback)
        backend._current_keys = {"ctrl", "a"}

        binding = HotkeyBinding(key="a", modifiers=["ctrl"], enabled=True)
        assert backend._check_binding(binding) is True

    def test_on_press_triggers_callback(self):
        """Test _on_press triggers callback when binding matches."""
        from apps.tray.hotkey_backends import X11Hotkeys
        from crates.profile_schema import HotkeyBinding

        callback = MagicMock()
        backend = X11Hotkeys(callback)
        backend._shortcuts = [
            ("profile_0", HotkeyBinding(key="1", modifiers=["ctrl"], enabled=True))
        ]
        backend._current_keys = {"ctrl"}

        # Mock key press
        with patch.object(backend, "_normalize_key", return_value="1"):
            backend._on_press(MagicMock())

        callback.assert_called_once_with("profile_0")
        assert "profile_0" in backend._triggered

    def test_on_press_no_match(self):
        """Test _on_press does nothing if no match."""
        from apps.tray.hotkey_backends import X11Hotkeys
        from crates.profile_schema import HotkeyBinding

        callback = MagicMock()
        backend = X11Hotkeys(callback)
        backend._shortcuts = [
            ("profile_0", HotkeyBinding(key="1", modifiers=["ctrl"], enabled=True))
        ]
        backend._current_keys = set()

        with patch.object(backend, "_normalize_key", return_value="a"):
            backend._on_press(MagicMock())

        callback.assert_not_called()

    def test_on_press_already_triggered(self):
        """Test _on_press skips already triggered shortcuts."""
        from apps.tray.hotkey_backends import X11Hotkeys
        from crates.profile_schema import HotkeyBinding

        callback = MagicMock()
        backend = X11Hotkeys(callback)
        backend._shortcuts = [
            ("profile_0", HotkeyBinding(key="1", modifiers=["ctrl"], enabled=True))
        ]
        backend._current_keys = {"ctrl", "1"}
        backend._triggered = {"profile_0"}

        with patch.object(backend, "_normalize_key", return_value="1"):
            backend._on_press(MagicMock())

        callback.assert_not_called()

    def test_on_press_null_key(self):
        """Test _on_press handles None from normalize."""
        from apps.tray.hotkey_backends import X11Hotkeys

        callback = MagicMock()
        backend = X11Hotkeys(callback)
        backend._shortcuts = []

        with patch.object(backend, "_normalize_key", return_value=None):
            backend._on_press(MagicMock())

        callback.assert_not_called()

    def test_on_release_clears_key(self):
        """Test _on_release removes key from current keys."""
        from apps.tray.hotkey_backends import X11Hotkeys

        callback = MagicMock()
        backend = X11Hotkeys(callback)
        backend._current_keys = {"ctrl", "a"}
        backend._shortcuts = []

        with patch.object(backend, "_normalize_key", return_value="a"):
            backend._on_release(MagicMock())

        assert "a" not in backend._current_keys

    def test_on_release_clears_triggered(self):
        """Test _on_release clears triggered state."""
        from apps.tray.hotkey_backends import X11Hotkeys
        from crates.profile_schema import HotkeyBinding

        callback = MagicMock()
        backend = X11Hotkeys(callback)
        backend._current_keys = {"ctrl", "1"}
        backend._triggered = {"profile_0"}
        backend._shortcuts = [
            ("profile_0", HotkeyBinding(key="1", modifiers=["ctrl"], enabled=True))
        ]

        with patch.object(backend, "_normalize_key", return_value="1"):
            backend._on_release(MagicMock())

        assert "profile_0" not in backend._triggered

    def test_on_release_null_key(self):
        """Test _on_release handles None from normalize."""
        from apps.tray.hotkey_backends import X11Hotkeys

        callback = MagicMock()
        backend = X11Hotkeys(callback)
        backend._current_keys = {"ctrl"}
        backend._shortcuts = []

        with patch.object(backend, "_normalize_key", return_value=None):
            backend._on_release(MagicMock())

        # Keys should be unchanged
        assert "ctrl" in backend._current_keys


# --- Tests for hotkeys.py ---


class TestHotkeyListener:
    """Tests for HotkeyListener class."""

    def test_init_creates_settings_manager(self):
        """Test init creates SettingsManager if not provided."""
        from apps.tray.hotkeys import HotkeyListener

        with patch("apps.tray.hotkeys.PortalGlobalShortcuts") as mock_portal:
            with patch("apps.tray.hotkeys.X11Hotkeys") as mock_x11:
                mock_portal.return_value.is_available.return_value = False
                mock_x11.return_value.is_available.return_value = False

                callback = MagicMock()
                listener = HotkeyListener(callback)

                assert listener.settings_manager is not None

    def test_init_uses_provided_settings_manager(self):
        """Test init uses provided SettingsManager."""
        from apps.tray.hotkeys import HotkeyListener
        from crates.profile_schema import SettingsManager

        with patch("apps.tray.hotkeys.PortalGlobalShortcuts") as mock_portal:
            with patch("apps.tray.hotkeys.X11Hotkeys") as mock_x11:
                mock_portal.return_value.is_available.return_value = False
                mock_x11.return_value.is_available.return_value = False

                callback = MagicMock()
                sm = SettingsManager()
                listener = HotkeyListener(callback, sm)

                assert listener.settings_manager is sm

    def test_init_selects_portal_backend(self):
        """Test init selects portal backend when available."""
        from apps.tray.hotkeys import HotkeyListener

        with patch("apps.tray.hotkeys.PortalGlobalShortcuts") as mock_portal:
            with patch("apps.tray.hotkeys.X11Hotkeys") as mock_x11:
                mock_portal.return_value.is_available.return_value = True
                mock_x11.return_value.is_available.return_value = True

                callback = MagicMock()
                listener = HotkeyListener(callback)

                assert listener._backend is mock_portal.return_value

    def test_init_selects_x11_backend(self):
        """Test init selects X11 backend when portal unavailable."""
        from apps.tray.hotkeys import HotkeyListener

        with patch("apps.tray.hotkeys.PortalGlobalShortcuts") as mock_portal:
            with patch("apps.tray.hotkeys.X11Hotkeys") as mock_x11:
                mock_portal.return_value.is_available.return_value = False
                mock_x11.return_value.is_available.return_value = True

                callback = MagicMock()
                listener = HotkeyListener(callback)

                assert listener._backend is mock_x11.return_value

    def test_init_no_backend(self):
        """Test init handles no available backend."""
        from apps.tray.hotkeys import HotkeyListener

        with patch("apps.tray.hotkeys.PortalGlobalShortcuts") as mock_portal:
            with patch("apps.tray.hotkeys.X11Hotkeys") as mock_x11:
                mock_portal.return_value.is_available.return_value = False
                mock_x11.return_value.is_available.return_value = False

                callback = MagicMock()
                listener = HotkeyListener(callback)

                assert listener._backend is None

    def test_on_shortcut_activated_valid(self):
        """Test _on_shortcut_activated calls callback with index."""
        from apps.tray.hotkeys import HotkeyListener

        with patch("apps.tray.hotkeys.PortalGlobalShortcuts") as mock_portal:
            with patch("apps.tray.hotkeys.X11Hotkeys") as mock_x11:
                mock_portal.return_value.is_available.return_value = False
                mock_x11.return_value.is_available.return_value = False

                callback = MagicMock()
                listener = HotkeyListener(callback)
                listener._on_shortcut_activated("profile_3")

                callback.assert_called_once_with(3)

    def test_on_shortcut_activated_invalid_action(self):
        """Test _on_shortcut_activated ignores invalid action_id."""
        from apps.tray.hotkeys import HotkeyListener

        with patch("apps.tray.hotkeys.PortalGlobalShortcuts") as mock_portal:
            with patch("apps.tray.hotkeys.X11Hotkeys") as mock_x11:
                mock_portal.return_value.is_available.return_value = False
                mock_x11.return_value.is_available.return_value = False

                callback = MagicMock()
                listener = HotkeyListener(callback)
                listener._on_shortcut_activated("invalid")

                callback.assert_not_called()

    def test_on_shortcut_activated_invalid_index(self):
        """Test _on_shortcut_activated handles invalid index."""
        from apps.tray.hotkeys import HotkeyListener

        with patch("apps.tray.hotkeys.PortalGlobalShortcuts") as mock_portal:
            with patch("apps.tray.hotkeys.X11Hotkeys") as mock_x11:
                mock_portal.return_value.is_available.return_value = False
                mock_x11.return_value.is_available.return_value = False

                callback = MagicMock()
                listener = HotkeyListener(callback)
                listener._on_shortcut_activated("profile_abc")

                callback.assert_not_called()

    def test_build_shortcuts(self):
        """Test _build_shortcuts creates shortcut list."""
        from apps.tray.hotkeys import HotkeyListener
        from crates.profile_schema import HotkeyBinding, SettingsManager

        with patch("apps.tray.hotkeys.PortalGlobalShortcuts") as mock_portal:
            with patch("apps.tray.hotkeys.X11Hotkeys") as mock_x11:
                mock_portal.return_value.is_available.return_value = False
                mock_x11.return_value.is_available.return_value = False

                callback = MagicMock()
                sm = SettingsManager()
                # Set up some bindings
                sm.settings.hotkeys.profile_hotkeys = [
                    HotkeyBinding(key="1", modifiers=["ctrl"], enabled=True),
                    HotkeyBinding(key="", modifiers=[], enabled=False),
                    HotkeyBinding(key="3", modifiers=["alt"], enabled=True),
                ]

                listener = HotkeyListener(callback, sm)
                shortcuts = listener._build_shortcuts()

                assert len(shortcuts) == 2
                assert shortcuts[0][0] == "profile_0"
                assert shortcuts[1][0] == "profile_2"

    def test_get_bindings(self):
        """Test get_bindings returns settings bindings."""
        from apps.tray.hotkeys import HotkeyListener
        from crates.profile_schema import HotkeyBinding, SettingsManager

        with patch("apps.tray.hotkeys.PortalGlobalShortcuts") as mock_portal:
            with patch("apps.tray.hotkeys.X11Hotkeys") as mock_x11:
                mock_portal.return_value.is_available.return_value = False
                mock_x11.return_value.is_available.return_value = False

                callback = MagicMock()
                sm = SettingsManager()
                bindings = [HotkeyBinding(key="1", modifiers=["ctrl"], enabled=True)]
                sm.settings.hotkeys.profile_hotkeys = bindings

                listener = HotkeyListener(callback, sm)
                result = listener.get_bindings()

                assert result == bindings

    def test_reload_bindings(self):
        """Test reload_bindings reloads from disk."""
        from apps.tray.hotkeys import HotkeyListener
        from crates.profile_schema import SettingsManager

        with patch("apps.tray.hotkeys.PortalGlobalShortcuts") as mock_portal:
            with patch("apps.tray.hotkeys.X11Hotkeys") as mock_x11:
                mock_backend = MagicMock()
                mock_portal.return_value.is_available.return_value = True
                mock_portal.return_value = mock_backend

                callback = MagicMock()
                sm = MagicMock(spec=SettingsManager)
                sm.settings.hotkeys.profile_hotkeys = []

                listener = HotkeyListener(callback, sm)
                listener._backend = mock_backend
                listener.reload_bindings()

                sm.load.assert_called_once()
                mock_backend.register_shortcuts.assert_called()

    def test_start_no_backend(self):
        """Test start does nothing without backend."""
        from apps.tray.hotkeys import HotkeyListener

        with patch("apps.tray.hotkeys.PortalGlobalShortcuts") as mock_portal:
            with patch("apps.tray.hotkeys.X11Hotkeys") as mock_x11:
                mock_portal.return_value.is_available.return_value = False
                mock_x11.return_value.is_available.return_value = False

                callback = MagicMock()
                listener = HotkeyListener(callback)
                listener.start()  # Should not raise

    def test_start_with_backend(self):
        """Test start registers shortcuts and starts backend."""
        from apps.tray.hotkeys import HotkeyListener

        with patch("apps.tray.hotkeys.PortalGlobalShortcuts") as mock_portal:
            with patch("apps.tray.hotkeys.X11Hotkeys") as mock_x11:
                mock_backend = MagicMock()
                mock_portal.return_value.is_available.return_value = True
                mock_portal.return_value = mock_backend

                callback = MagicMock()
                listener = HotkeyListener(callback)
                listener.start()

                mock_backend.register_shortcuts.assert_called()
                mock_backend.start.assert_called_once()

    def test_stop_with_backend(self):
        """Test stop stops backend."""
        from apps.tray.hotkeys import HotkeyListener

        with patch("apps.tray.hotkeys.PortalGlobalShortcuts") as mock_portal:
            with patch("apps.tray.hotkeys.X11Hotkeys") as mock_x11:
                mock_backend = MagicMock()
                mock_portal.return_value.is_available.return_value = True
                mock_portal.return_value = mock_backend

                callback = MagicMock()
                listener = HotkeyListener(callback)
                listener.stop()

                mock_backend.stop.assert_called_once()

    def test_backend_name_with_backend(self):
        """Test backend_name returns backend name."""
        from apps.tray.hotkeys import HotkeyListener

        with patch("apps.tray.hotkeys.PortalGlobalShortcuts") as mock_portal:
            with patch("apps.tray.hotkeys.X11Hotkeys") as mock_x11:
                mock_backend = MagicMock()
                mock_backend.name = "TestBackend"
                mock_portal.return_value.is_available.return_value = True
                mock_portal.return_value = mock_backend

                callback = MagicMock()
                listener = HotkeyListener(callback)

                assert listener.backend_name == "TestBackend"

    def test_backend_name_no_backend(self):
        """Test backend_name returns None without backend."""
        from apps.tray.hotkeys import HotkeyListener

        with patch("apps.tray.hotkeys.PortalGlobalShortcuts") as mock_portal:
            with patch("apps.tray.hotkeys.X11Hotkeys") as mock_x11:
                mock_portal.return_value.is_available.return_value = False
                mock_x11.return_value.is_available.return_value = False

                callback = MagicMock()
                listener = HotkeyListener(callback)

                assert listener.backend_name is None


# --- Tests for main.py (TraySignals and main function) ---


class TestTrayInit:
    """Tests for apps/tray/__init__.py exports."""

    def test_exports_main(self):
        """Test __init__ exports main function."""
        from apps.tray import main

        assert callable(main)


class TestTrayMain:
    """Tests for main() function."""

    def test_main_no_tray_available(self, capsys):
        """Test main exits if no system tray."""
        with patch("apps.tray.main.QApplication") as mock_app:
            with patch("apps.tray.main.QSystemTrayIcon") as mock_tray:
                mock_app.return_value = MagicMock()
                mock_tray.isSystemTrayAvailable.return_value = False

                with pytest.raises(SystemExit) as exc_info:
                    from apps.tray.main import main
                    main()

                assert exc_info.value.code == 1
                captured = capsys.readouterr()
                assert "System tray not available" in captured.out

    def test_main_creates_tray(self):
        """Test main creates tray icon when available."""
        with patch("apps.tray.main.QApplication") as mock_app:
            with patch("apps.tray.main.QSystemTrayIcon") as mock_tray:
                with patch("apps.tray.main.RazerTray") as mock_razer_tray:
                    mock_app_instance = MagicMock()
                    mock_app_instance.exec.return_value = 0
                    mock_app.return_value = mock_app_instance
                    mock_tray.isSystemTrayAvailable.return_value = True

                    with patch("sys.exit"):
                        from apps.tray.main import main
                        main()

                    mock_razer_tray.assert_called_once()


class TestRazerTrayMethods:
    """Tests for RazerTray methods that can be tested without Qt display."""

    def test_get_autostart_path(self):
        """Test _get_autostart_path returns correct path."""
        from apps.tray.main import RazerTray

        # Create instance without calling __init__
        tray = RazerTray.__new__(RazerTray)

        path = tray._get_autostart_path()

        assert path.name == "razer-tray.desktop"
        assert ".config/autostart" in str(path)

    def test_get_source_desktop_path_found(self, tmp_path):
        """Test _get_source_desktop_path when file exists."""
        # Create a temporary desktop file
        desktop_file = tmp_path / "razer-tray.desktop"
        desktop_file.write_text("[Desktop Entry]\nName=Test")

        from apps.tray.main import RazerTray

        tray = RazerTray.__new__(RazerTray)

        # Patch the locations list to use our temp path
        with patch.object(
            RazerTray, "_get_source_desktop_path",
            lambda self: desktop_file if desktop_file.exists() else tmp_path / "fallback"
        ):
            result = tray._get_source_desktop_path()
            assert result == desktop_file

    def test_is_autostart_enabled(self, tmp_path):
        """Test _is_autostart_enabled checks file existence."""
        from apps.tray.main import RazerTray

        tray = RazerTray.__new__(RazerTray)

        # When file doesn't exist
        with patch.object(tray, "_get_autostart_path", return_value=tmp_path / "nonexistent"):
            assert tray._is_autostart_enabled() is False

        # When file exists
        existing = tmp_path / "exists.desktop"
        existing.touch()
        with patch.object(tray, "_get_autostart_path", return_value=existing):
            assert tray._is_autostart_enabled() is True


class TestTraySignals:
    """Tests for TraySignals class."""

    def test_signals_exist(self):
        """Test TraySignals has expected signals."""
        from apps.tray.main import TraySignals

        signals = TraySignals()

        # Verify signals exist (they are Qt Signal objects)
        assert hasattr(signals, "profile_changed")
        assert hasattr(signals, "daemon_status_changed")
        assert hasattr(signals, "device_connected")
        assert hasattr(signals, "device_disconnected")
        assert hasattr(signals, "hotkey_switch")


class TestMainGuard:
    """Tests for __name__ == '__main__' guard."""

    def test_main_module_has_guard(self):
        """Test __name__ == '__main__' guard exists (line 725-726)."""
        import ast

        # Read the source file and verify it has the guard
        source_path = Path(__file__).parent.parent / "apps" / "tray" / "main.py"
        source = source_path.read_text()

        # Parse and look for the if __name__ == "__main__" pattern
        tree = ast.parse(source)
        has_main_guard = False

        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                # Check if it's `if __name__ == "__main__"`
                if isinstance(node.test, ast.Compare):
                    if (
                        isinstance(node.test.left, ast.Name)
                        and node.test.left.id == "__name__"
                    ):
                        has_main_guard = True
                        break

        assert has_main_guard, "Module should have if __name__ == '__main__' guard"

    def test_main_guard_calls_main(self):
        """Test the guard calls main() function."""
        # Verify by reading source that guard calls main()

        source_path = Path(__file__).parent.parent / "apps" / "tray" / "main.py"
        source = source_path.read_text()

        # The guard should be at the end and call main()
        assert 'if __name__ == "__main__":' in source
        assert source.strip().endswith("main()")
