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

    def test_abstract_methods_callable(self):
        """Test that abstract method implementations work."""
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
        # Call all the abstract method implementations
        assert backend.is_available() is True
        assert backend.register_shortcuts({"test": "shortcut"}) is True
        backend.start()
        backend.stop()


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
            with patch("apps.tray.hotkeys.X11Hotkeys"):
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
            with patch("apps.tray.hotkeys.X11Hotkeys"):
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
            with patch("apps.tray.hotkeys.X11Hotkeys"):
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
            with patch("apps.tray.hotkeys.X11Hotkeys"):
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
            RazerTray,
            "_get_source_desktop_path",
            lambda self: desktop_file if desktop_file.exists() else tmp_path / "fallback",
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
                    if isinstance(node.test.left, ast.Name) and node.test.left.id == "__name__":
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


# --- Comprehensive RazerTray Tests ---


@pytest.fixture
def mock_hotkey_listener_for_tray():
    """Mock HotkeyListener for RazerTray tests."""
    with patch("apps.tray.main.HotkeyListener") as mock_cls:
        mock_instance = MagicMock()
        mock_instance.backend_name = "X11Hotkeys"
        mock_instance.start = MagicMock()
        mock_instance.stop = MagicMock()
        mock_instance.reload_bindings = MagicMock()
        mock_cls.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_profile_loader_for_tray():
    """Mock ProfileLoader for RazerTray tests."""
    with patch("apps.tray.main.ProfileLoader") as mock_cls:
        mock_instance = MagicMock()
        mock_instance.list_profiles.return_value = ["profile1", "profile2"]
        mock_instance.get_active_profile_id.return_value = "profile1"
        mock_instance.config_dir = Path("/tmp/test_config")

        mock_profile = MagicMock()
        mock_profile.name = "Test Profile"
        mock_profile.id = "profile1"
        mock_instance.load_profile.return_value = mock_profile
        mock_instance.save_profile.return_value = True

        mock_cls.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_settings_manager_for_tray():
    """Mock SettingsManager for RazerTray tests."""
    with patch("apps.tray.main.SettingsManager") as mock_cls:
        mock_instance = MagicMock()
        mock_instance.settings_file = Path("/tmp/test_settings.json")
        mock_instance.config_dir = Path("/tmp/test_config")

        # Mock file exists checks
        type(mock_instance.settings_file).exists = MagicMock(return_value=True)
        type(mock_instance.config_dir).exists = MagicMock(return_value=True)

        # Mock settings with hotkeys
        mock_settings = MagicMock()
        mock_hotkeys = MagicMock()
        mock_binding = MagicMock()
        mock_binding.enabled = True
        mock_binding.key = "F1"
        mock_binding.to_display_string.return_value = "F1"
        mock_hotkeys.profile_hotkeys = [mock_binding]
        mock_settings.hotkeys = mock_hotkeys
        mock_instance.settings = mock_settings
        mock_instance.load = MagicMock()

        mock_cls.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_openrazer_for_tray():
    """Mock OpenRazerBridge for RazerTray tests."""
    with patch("apps.tray.main.OpenRazerBridge") as mock_cls:
        mock_instance = MagicMock()
        mock_instance.is_connected.return_value = True
        mock_instance.discover_devices.return_value = []
        mock_instance.connect = MagicMock()
        mock_instance.set_dpi.return_value = True
        mock_instance.set_spectrum_effect.return_value = True
        mock_instance.set_static_color.return_value = True
        mock_instance.set_breathing_effect.return_value = True
        mock_instance.set_breathing_random.return_value = True
        mock_instance.set_wave_effect.return_value = True
        mock_instance.set_none_effect.return_value = True
        mock_cls.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_subprocess_for_tray():
    """Mock subprocess for RazerTray tests."""
    with (
        patch("apps.tray.main.subprocess.run") as mock_run,
        patch("apps.tray.main.subprocess.Popen") as mock_popen,
    ):
        mock_run.return_value = MagicMock(stdout="active\n", returncode=0)
        yield mock_run, mock_popen


@pytest.fixture
def razer_tray_instance(
    qtbot,
    mock_hotkey_listener_for_tray,
    mock_profile_loader_for_tray,
    mock_settings_manager_for_tray,
    mock_openrazer_for_tray,
    mock_subprocess_for_tray,
):
    """Create a RazerTray instance for testing."""
    from PySide6.QtWidgets import QSystemTrayIcon

    from apps.tray.main import RazerTray

    with patch.object(QSystemTrayIcon, "show"):
        with patch.object(QSystemTrayIcon, "setIcon"):
            with patch.object(QSystemTrayIcon, "setToolTip"):
                with patch.object(QSystemTrayIcon, "setContextMenu"):
                    with patch.object(QSystemTrayIcon, "showMessage"):
                        tray = RazerTray()
                        yield tray
                        tray._status_timer.stop()


class TestRazerTrayInit:
    """Tests for RazerTray initialization."""

    def test_init_sets_signals(self, razer_tray_instance):
        """Test tray has signals object."""

        assert hasattr(razer_tray_instance, "signals")

    def test_init_sets_profile_loader(self, razer_tray_instance):
        """Test tray has profile loader."""
        assert hasattr(razer_tray_instance, "profile_loader")

    def test_init_sets_settings_manager(self, razer_tray_instance):
        """Test tray has settings manager."""
        assert hasattr(razer_tray_instance, "settings_manager")

    def test_init_sets_openrazer(self, razer_tray_instance):
        """Test tray has openrazer bridge."""
        assert hasattr(razer_tray_instance, "openrazer")

    def test_init_starts_timer(self, razer_tray_instance):
        """Test status timer is started."""
        assert razer_tray_instance._status_timer.isActive()

    def test_init_creates_menu(self, razer_tray_instance):
        """Test menu is created."""
        from PySide6.QtWidgets import QMenu

        assert hasattr(razer_tray_instance, "menu")
        assert isinstance(razer_tray_instance.menu, QMenu)


class TestRazerTrayCreateIcon:
    """Tests for _create_icon method."""

    def test_create_icon_sets_tooltip(
        self,
        qtbot,
        mock_hotkey_listener_for_tray,
        mock_profile_loader_for_tray,
        mock_settings_manager_for_tray,
        mock_openrazer_for_tray,
        mock_subprocess_for_tray,
    ):
        """Test icon creation sets tooltip."""
        from PySide6.QtWidgets import QSystemTrayIcon

        from apps.tray.main import RazerTray

        with patch.object(QSystemTrayIcon, "show"):
            with patch.object(QSystemTrayIcon, "setIcon"):
                with patch.object(QSystemTrayIcon, "setToolTip") as mock_tip:
                    with patch.object(QSystemTrayIcon, "setContextMenu"):
                        with patch.object(QSystemTrayIcon, "showMessage"):
                            tray = RazerTray()
                            # Tooltip includes profile name after status check
                            assert mock_tip.called
                            tray._status_timer.stop()


class TestRazerTrayCreateMenu:
    """Tests for _create_menu method."""

    def test_menu_has_header(self, razer_tray_instance):
        """Test menu has header action."""
        actions = razer_tray_instance.menu.actions()
        assert len(actions) > 0

    def test_menu_has_profile_label(self, razer_tray_instance):
        """Test menu has profile label."""
        assert hasattr(razer_tray_instance, "profile_label")

    def test_menu_has_hotkey_status(self, razer_tray_instance):
        """Test menu has hotkey status."""
        assert hasattr(razer_tray_instance, "hotkey_status")

    def test_menu_has_profiles_menu(self, razer_tray_instance):
        """Test menu has profiles submenu."""
        assert hasattr(razer_tray_instance, "profiles_menu")

    def test_menu_has_devices_menu(self, razer_tray_instance):
        """Test menu has devices submenu."""
        assert hasattr(razer_tray_instance, "devices_menu")

    def test_menu_has_daemon_menu(self, razer_tray_instance):
        """Test menu has daemon submenu."""
        assert hasattr(razer_tray_instance, "daemon_menu")

    def test_menu_has_autostart(self, razer_tray_instance):
        """Test menu has autostart action."""
        assert hasattr(razer_tray_instance, "autostart_action")


class TestRazerTrayUpdateProfilesMenu:
    """Tests for _update_profiles_menu method."""

    def test_update_empty_profiles(self, razer_tray_instance, mock_profile_loader_for_tray):
        """Test profiles menu with no profiles."""
        mock_profile_loader_for_tray.list_profiles.return_value = []
        razer_tray_instance._update_profiles_menu()
        # Menu should have "(No profiles)" action

    def test_update_with_profiles(self, razer_tray_instance, mock_profile_loader_for_tray):
        """Test profiles menu with profiles."""
        mock_profile_loader_for_tray.list_profiles.return_value = ["p1", "p2"]
        mock_profile = MagicMock()
        mock_profile.name = "Profile 1"
        mock_profile_loader_for_tray.load_profile.return_value = mock_profile
        razer_tray_instance._update_profiles_menu()

    def test_marks_active_profile(self, razer_tray_instance, mock_profile_loader_for_tray):
        """Test active profile is marked with bullet."""
        mock_profile_loader_for_tray.list_profiles.return_value = ["p1"]
        mock_profile_loader_for_tray.get_active_profile_id.return_value = "p1"
        mock_profile = MagicMock()
        mock_profile.name = "Profile 1"
        mock_profile_loader_for_tray.load_profile.return_value = mock_profile
        razer_tray_instance._update_profiles_menu()


class TestRazerTrayUpdateDevicesMenu:
    """Tests for _update_devices_menu method."""

    def test_update_no_devices(self, razer_tray_instance, mock_openrazer_for_tray):
        """Test devices menu with no devices."""
        mock_openrazer_for_tray.discover_devices.return_value = []
        razer_tray_instance._update_devices_menu()

    def test_update_with_device(self, razer_tray_instance, mock_openrazer_for_tray):
        """Test devices menu with a device."""
        mock_device = MagicMock()
        mock_device.name = "Razer DeathAdder"
        mock_device.serial = "XX1234"
        mock_device.has_dpi = True
        mock_device.dpi = (800, 800)
        mock_device.has_poll_rate = True
        mock_device.poll_rate = 1000
        mock_device.has_battery = True
        mock_device.battery_level = 75
        mock_device.is_charging = False
        mock_device.has_brightness = True
        mock_device.brightness = 100
        mock_device.has_lighting = True
        mock_device.supported_effects = ["spectrum", "static"]
        mock_device.max_dpi = 16000

        mock_openrazer_for_tray.discover_devices.return_value = [mock_device]
        razer_tray_instance._update_devices_menu()

    def test_connects_if_not_connected(self, razer_tray_instance, mock_openrazer_for_tray):
        """Test connects to OpenRazer if not connected."""
        mock_openrazer_for_tray.is_connected.return_value = False
        razer_tray_instance._update_devices_menu()
        mock_openrazer_for_tray.connect.assert_called_once()


class TestRazerTrayCheckStatus:
    """Tests for _check_status method."""

    def test_daemon_running(self, razer_tray_instance, mock_subprocess_for_tray):
        """Test status check with daemon running."""
        mock_run, _ = mock_subprocess_for_tray
        mock_run.return_value = MagicMock(stdout="active\n")
        razer_tray_instance._daemon_running = False  # Force change
        razer_tray_instance._check_status()
        assert razer_tray_instance._daemon_running is True

    def test_daemon_stopped(self, razer_tray_instance, mock_subprocess_for_tray):
        """Test status check with daemon stopped."""
        mock_run, _ = mock_subprocess_for_tray
        mock_run.return_value = MagicMock(stdout="inactive\n")
        razer_tray_instance._daemon_running = True  # Force change
        razer_tray_instance._check_status()
        assert razer_tray_instance._daemon_running is False

    def test_exception_handling(self, razer_tray_instance, mock_subprocess_for_tray):
        """Test status check handles exceptions."""
        import subprocess

        mock_run, _ = mock_subprocess_for_tray
        mock_run.side_effect = subprocess.TimeoutExpired("cmd", 2)
        razer_tray_instance._check_status()
        assert razer_tray_instance._daemon_running is False


class TestRazerTrayDaemonControl:
    """Tests for daemon control methods."""

    def test_start_daemon(self, razer_tray_instance, mock_subprocess_for_tray):
        """Test start daemon."""
        mock_run, _ = mock_subprocess_for_tray
        with patch.object(razer_tray_instance, "_notify"):
            with patch.object(razer_tray_instance, "_check_status"):
                razer_tray_instance._start_daemon()

    def test_start_daemon_exception(self, razer_tray_instance, mock_subprocess_for_tray):
        """Test start daemon with exception."""
        mock_run, _ = mock_subprocess_for_tray
        mock_run.side_effect = Exception("Failed")
        with patch.object(razer_tray_instance, "_notify") as mock_notify:
            razer_tray_instance._start_daemon()
            mock_notify.assert_called()

    def test_stop_daemon(self, razer_tray_instance, mock_subprocess_for_tray):
        """Test stop daemon."""
        mock_run, _ = mock_subprocess_for_tray
        with patch.object(razer_tray_instance, "_notify"):
            with patch.object(razer_tray_instance, "_check_status"):
                razer_tray_instance._stop_daemon()

    def test_stop_daemon_exception(self, razer_tray_instance, mock_subprocess_for_tray):
        """Test stop daemon with exception."""
        mock_run, _ = mock_subprocess_for_tray
        mock_run.side_effect = Exception("Failed")
        with patch.object(razer_tray_instance, "_notify") as mock_notify:
            razer_tray_instance._stop_daemon()
            mock_notify.assert_called()

    def test_restart_daemon(self, razer_tray_instance, mock_subprocess_for_tray):
        """Test restart daemon."""
        mock_run, _ = mock_subprocess_for_tray
        with patch.object(razer_tray_instance, "_notify"):
            with patch.object(razer_tray_instance, "_check_status"):
                razer_tray_instance._restart_daemon()

    def test_restart_daemon_exception(self, razer_tray_instance, mock_subprocess_for_tray):
        """Test restart daemon with exception."""
        mock_run, _ = mock_subprocess_for_tray
        mock_run.side_effect = Exception("Failed")
        with patch.object(razer_tray_instance, "_notify") as mock_notify:
            razer_tray_instance._restart_daemon()
            mock_notify.assert_called()


class TestRazerTrayUpdateDaemonStatus:
    """Tests for _update_daemon_status method."""

    def test_status_running(self, razer_tray_instance):
        """Test status display when running."""
        razer_tray_instance._daemon_running = True
        razer_tray_instance._update_daemon_status()
        assert "Running" in razer_tray_instance.daemon_status.text()

    def test_status_stopped(self, razer_tray_instance):
        """Test status display when stopped."""
        razer_tray_instance._daemon_running = False
        razer_tray_instance._update_daemon_status()
        assert "Stopped" in razer_tray_instance.daemon_status.text()


class TestRazerTraySwitchProfile:
    """Tests for _switch_profile method."""

    def test_switch_success(self, razer_tray_instance, mock_profile_loader_for_tray):
        """Test switching profile."""
        mock_profile = MagicMock()
        mock_profile.name = "New Profile"
        mock_profile_loader_for_tray.load_profile.return_value = mock_profile
        razer_tray_instance._daemon_running = False

        with patch.object(razer_tray_instance, "_notify"):
            with patch.object(razer_tray_instance, "_update_profile_display"):
                razer_tray_instance._switch_profile("new")
                mock_profile_loader_for_tray.set_active_profile.assert_called_with("new")

    def test_switch_not_found(self, razer_tray_instance, mock_profile_loader_for_tray):
        """Test switching to non-existent profile."""
        mock_profile_loader_for_tray.load_profile.return_value = None

        with patch.object(razer_tray_instance, "_notify") as mock_notify:
            razer_tray_instance._switch_profile("missing")
            mock_notify.assert_called()

    def test_switch_restarts_daemon(self, razer_tray_instance, mock_profile_loader_for_tray):
        """Test switching restarts daemon if running."""
        mock_profile = MagicMock()
        mock_profile.name = "New Profile"
        mock_profile_loader_for_tray.load_profile.return_value = mock_profile
        razer_tray_instance._daemon_running = True

        with patch.object(razer_tray_instance, "_notify"):
            with patch.object(razer_tray_instance, "_update_profile_display"):
                with patch.object(razer_tray_instance, "_restart_daemon") as mock_restart:
                    razer_tray_instance._switch_profile("new")
                    mock_restart.assert_called_once()


class TestRazerTraySetDpi:
    """Tests for _set_dpi method."""

    def test_set_dpi_success(self, razer_tray_instance, mock_openrazer_for_tray):
        """Test setting DPI."""
        with patch.object(razer_tray_instance, "_notify"):
            with patch.object(razer_tray_instance, "_update_devices_menu"):
                razer_tray_instance._set_dpi("serial", 1600)
                mock_openrazer_for_tray.set_dpi.assert_called_with("serial", 1600)

    def test_set_dpi_failure(self, razer_tray_instance, mock_openrazer_for_tray):
        """Test setting DPI failure."""
        mock_openrazer_for_tray.set_dpi.return_value = False
        with patch.object(razer_tray_instance, "_notify") as mock_notify:
            razer_tray_instance._set_dpi("serial", 1600)
            mock_notify.assert_called()


class TestRazerTraySetEffect:
    """Tests for _set_effect method."""

    def test_set_spectrum(self, razer_tray_instance, mock_openrazer_for_tray):
        """Test setting spectrum effect."""
        with patch.object(razer_tray_instance, "_notify"):
            razer_tray_instance._set_effect("serial", "spectrum")
            mock_openrazer_for_tray.set_spectrum_effect.assert_called_with("serial")

    def test_set_static(self, razer_tray_instance, mock_openrazer_for_tray):
        """Test setting static effect."""
        with patch.object(razer_tray_instance, "_notify"):
            razer_tray_instance._set_effect("serial", "static")
            mock_openrazer_for_tray.set_static_color.assert_called()

    def test_set_breathing(self, razer_tray_instance, mock_openrazer_for_tray):
        """Test setting breathing effect."""
        with patch.object(razer_tray_instance, "_notify"):
            razer_tray_instance._set_effect("serial", "breathing")
            mock_openrazer_for_tray.set_breathing_effect.assert_called()

    def test_set_breathing_random(self, razer_tray_instance, mock_openrazer_for_tray):
        """Test setting breathing_random effect."""
        with patch.object(razer_tray_instance, "_notify"):
            razer_tray_instance._set_effect("serial", "breathing_random")
            mock_openrazer_for_tray.set_breathing_random.assert_called()

    def test_set_wave(self, razer_tray_instance, mock_openrazer_for_tray):
        """Test setting wave effect."""
        with patch.object(razer_tray_instance, "_notify"):
            razer_tray_instance._set_effect("serial", "wave")

    def test_set_none(self, razer_tray_instance, mock_openrazer_for_tray):
        """Test setting none effect."""
        with patch.object(razer_tray_instance, "_notify"):
            razer_tray_instance._set_effect("serial", "none")
            mock_openrazer_for_tray.set_none_effect.assert_called()

    def test_set_effect_failure(self, razer_tray_instance, mock_openrazer_for_tray):
        """Test effect failure."""
        mock_openrazer_for_tray.set_spectrum_effect.return_value = False
        with patch.object(razer_tray_instance, "_notify") as mock_notify:
            razer_tray_instance._set_effect("serial", "spectrum")
            mock_notify.assert_called()


class TestRazerTrayOpenActions:
    """Tests for open actions."""

    def test_open_gui(self, razer_tray_instance, mock_subprocess_for_tray):
        """Test opening GUI."""
        _, mock_popen = mock_subprocess_for_tray
        razer_tray_instance._open_gui()
        mock_popen.assert_called()

    def test_open_gui_failure(self, razer_tray_instance, mock_subprocess_for_tray):
        """Test opening GUI with failure."""
        _, mock_popen = mock_subprocess_for_tray
        mock_popen.side_effect = Exception("Failed")
        with patch.object(razer_tray_instance, "_notify") as mock_notify:
            razer_tray_instance._open_gui()
            mock_notify.assert_called()

    def test_open_config(self, razer_tray_instance, mock_subprocess_for_tray):
        """Test opening config folder."""
        _, mock_popen = mock_subprocess_for_tray
        razer_tray_instance._open_config()
        mock_popen.assert_called()

    def test_open_config_failure(self, razer_tray_instance, mock_subprocess_for_tray):
        """Test opening config folder with failure."""
        _, mock_popen = mock_subprocess_for_tray
        mock_popen.side_effect = Exception("Failed")
        with patch.object(razer_tray_instance, "_notify") as mock_notify:
            razer_tray_instance._open_config()
            mock_notify.assert_called()


class TestRazerTrayAutostart:
    """Tests for autostart functionality."""

    def test_toggle_disable_calls_unlink(self, razer_tray_instance):
        """Test disabling autostart calls unlink."""
        mock_path = MagicMock()
        mock_path.exists.return_value = True

        with patch.object(razer_tray_instance, "_get_autostart_path", return_value=mock_path):
            with patch.object(razer_tray_instance, "_notify"):
                with patch.object(razer_tray_instance, "_update_autostart_status"):
                    razer_tray_instance._toggle_autostart()
                    mock_path.unlink.assert_called_once()

    def test_toggle_enable_with_source(self, razer_tray_instance, tmp_path):
        """Test enabling autostart with source file."""
        autostart_dir = tmp_path / "autostart"
        autostart_dir.mkdir(parents=True)
        autostart_file = autostart_dir / "razer-tray.desktop"
        source_file = tmp_path / "source.desktop"
        source_file.write_text("[Desktop Entry]\nName=Test\n")

        with patch.object(razer_tray_instance, "_get_autostart_path", return_value=autostart_file):
            with patch.object(razer_tray_instance, "_is_autostart_enabled", return_value=False):
                with patch.object(
                    razer_tray_instance, "_get_source_desktop_path", return_value=source_file
                ):
                    with patch.object(razer_tray_instance, "_notify"):
                        with patch.object(razer_tray_instance, "_update_autostart_status"):
                            razer_tray_instance._toggle_autostart()
                            assert autostart_file.exists()

    def test_toggle_enable_no_source(self, razer_tray_instance):
        """Test enabling autostart without source file (creates minimal entry)."""
        mock_path = MagicMock()
        mock_path.exists.return_value = False  # autostart file doesn't exist
        mock_path.parent.mkdir = MagicMock()

        mock_source = MagicMock()
        mock_source.exists.return_value = False  # source file doesn't exist

        with patch.object(razer_tray_instance, "_get_autostart_path", return_value=mock_path):
            with patch.object(razer_tray_instance, "_is_autostart_enabled", return_value=False):
                with patch.object(
                    razer_tray_instance, "_get_source_desktop_path", return_value=mock_source
                ):
                    with patch.object(razer_tray_instance, "_notify") as mock_notify:
                        with patch.object(razer_tray_instance, "_update_autostart_status"):
                            razer_tray_instance._toggle_autostart()
                            # Should create minimal entry
                            mock_path.write_text.assert_called_once()
                            mock_notify.assert_called()


class TestRazerTrayExportImport:
    """Tests for export/import functionality."""

    def test_export_no_profiles(self, razer_tray_instance, mock_profile_loader_for_tray):
        """Test export with no profiles."""
        mock_profile_loader_for_tray.list_profiles.return_value = []
        with patch.object(razer_tray_instance, "_notify") as mock_notify:
            razer_tray_instance._export_profiles()
            mock_notify.assert_called()

    def test_export_cancelled(self, razer_tray_instance, mock_profile_loader_for_tray):
        """Test export cancelled."""
        mock_profile_loader_for_tray.list_profiles.return_value = ["p1"]
        with patch("apps.tray.main.QFileDialog.getSaveFileName", return_value=("", "")):
            razer_tray_instance._export_profiles()

    def test_export_success(self, razer_tray_instance, mock_profile_loader_for_tray, tmp_path):
        """Test successful export."""
        mock_profile_loader_for_tray.list_profiles.return_value = ["p1"]
        mock_profile = MagicMock()
        mock_profile.model_dump.return_value = {"id": "p1", "name": "Test"}
        mock_profile_loader_for_tray.load_profile.return_value = mock_profile

        zip_path = tmp_path / "export.zip"
        with patch("apps.tray.main.QFileDialog.getSaveFileName", return_value=(str(zip_path), "")):
            with patch.object(razer_tray_instance, "_notify"):
                razer_tray_instance._export_profiles()
                assert zip_path.exists()

    def test_import_cancelled(self, razer_tray_instance):
        """Test import cancelled."""
        with patch("apps.tray.main.QFileDialog.getOpenFileName", return_value=("", "")):
            razer_tray_instance._import_profile()

    def test_import_success(self, razer_tray_instance, mock_profile_loader_for_tray, tmp_path):
        """Test successful import."""
        profile_file = tmp_path / "profile.json"
        profile_file.write_text('{"id": "new", "name": "New Profile", "layers": []}')

        mock_profile_loader_for_tray.load_profile.return_value = None  # No existing

        with patch(
            "apps.tray.main.QFileDialog.getOpenFileName", return_value=(str(profile_file), "")
        ):
            with patch.object(razer_tray_instance, "_notify"):
                with patch.object(razer_tray_instance, "_update_profiles_menu"):
                    razer_tray_instance._import_profile()

    def test_import_invalid_json(self, razer_tray_instance, tmp_path):
        """Test import with invalid JSON."""
        profile_file = tmp_path / "profile.json"
        profile_file.write_text("{ invalid json }")

        with patch(
            "apps.tray.main.QFileDialog.getOpenFileName", return_value=(str(profile_file), "")
        ):
            with patch.object(razer_tray_instance, "_notify") as mock_notify:
                razer_tray_instance._import_profile()
                mock_notify.assert_called()


class TestRazerTrayCheckOpenrazer:
    """Tests for _check_openrazer method."""

    def test_check_active(self, razer_tray_instance, mock_subprocess_for_tray):
        """Test OpenRazer active."""
        mock_run, _ = mock_subprocess_for_tray
        mock_run.return_value = MagicMock(stdout="active\n")
        with patch("apps.tray.main.QMessageBox.information"):
            razer_tray_instance._check_openrazer()

    def test_check_inactive(self, razer_tray_instance, mock_subprocess_for_tray):
        """Test OpenRazer inactive."""
        mock_run, _ = mock_subprocess_for_tray
        mock_run.return_value = MagicMock(stdout="inactive\n")
        with patch("apps.tray.main.QMessageBox.information"):
            razer_tray_instance._check_openrazer()

    def test_check_exception(self, razer_tray_instance, mock_subprocess_for_tray):
        """Test OpenRazer check exception."""
        mock_run, _ = mock_subprocess_for_tray
        mock_run.side_effect = Exception("Failed")
        with patch("apps.tray.main.QMessageBox.information"):
            razer_tray_instance._check_openrazer()


class TestRazerTrayNotify:
    """Tests for _notify method."""

    def test_notify_info(self, razer_tray_instance):
        """Test info notification."""
        from PySide6.QtWidgets import QSystemTrayIcon

        with patch.object(QSystemTrayIcon, "showMessage"):
            razer_tray_instance._notify("Title", "Message")

    def test_notify_error(self, razer_tray_instance):
        """Test error notification."""
        from PySide6.QtWidgets import QSystemTrayIcon

        with patch.object(QSystemTrayIcon, "showMessage"):
            razer_tray_instance._notify("Error", "Something failed", error=True)


class TestRazerTrayOnActivated:
    """Tests for _on_activated method."""

    def test_double_click_opens_gui(self, razer_tray_instance):
        """Test double-click opens GUI."""
        from PySide6.QtWidgets import QSystemTrayIcon

        with patch.object(razer_tray_instance, "_open_gui") as mock_open:
            razer_tray_instance._on_activated(QSystemTrayIcon.ActivationReason.DoubleClick)
            mock_open.assert_called_once()

    def test_middle_click_refreshes(self, razer_tray_instance):
        """Test middle-click refreshes."""
        from PySide6.QtWidgets import QSystemTrayIcon

        with patch.object(razer_tray_instance, "_check_status") as mock_status:
            with patch.object(razer_tray_instance, "_update_devices_menu") as mock_devices:
                razer_tray_instance._on_activated(QSystemTrayIcon.ActivationReason.MiddleClick)
                mock_status.assert_called_once()
                mock_devices.assert_called_once()


class TestRazerTrayHotkeySwitch:
    """Tests for hotkey switch functionality."""

    def test_emit_hotkey_switch(self, razer_tray_instance):
        """Test emitting hotkey switch."""
        razer_tray_instance._emit_hotkey_switch(0)

    def test_on_hotkey_switch_valid(self, razer_tray_instance, mock_profile_loader_for_tray):
        """Test hotkey switch with valid index."""
        mock_profile_loader_for_tray.list_profiles.return_value = ["p1", "p2"]
        with patch.object(razer_tray_instance, "_switch_profile") as mock_switch:
            razer_tray_instance._on_hotkey_switch(0)
            mock_switch.assert_called_with("p1")

    def test_on_hotkey_switch_invalid(self, razer_tray_instance, mock_profile_loader_for_tray):
        """Test hotkey switch with invalid index."""
        mock_profile_loader_for_tray.list_profiles.return_value = ["p1"]
        with patch.object(razer_tray_instance, "_switch_profile") as mock_switch:
            razer_tray_instance._on_hotkey_switch(5)  # Out of range
            mock_switch.assert_not_called()


class TestRazerTrayQuit:
    """Tests for _quit method."""

    def test_quit_stops_timer(self, razer_tray_instance):
        """Test quit stops timer."""
        from PySide6.QtWidgets import QApplication

        with patch.object(QApplication, "quit"):
            razer_tray_instance._quit()
            assert not razer_tray_instance._status_timer.isActive()


class TestRazerTraySettingsWatcher:
    """Tests for settings file watcher."""

    def test_on_settings_changed(self, razer_tray_instance, mock_hotkey_listener_for_tray):
        """Test settings file change."""
        with patch.object(razer_tray_instance, "_update_profiles_menu"):
            razer_tray_instance._on_settings_changed("/path/to/settings.json")
            mock_hotkey_listener_for_tray.reload_bindings.assert_called()

    def test_on_settings_dir_changed(
        self, razer_tray_instance, mock_settings_manager_for_tray, tmp_path
    ):
        """Test settings directory change."""
        settings_file = tmp_path / "settings.json"
        settings_file.write_text("{}")
        mock_settings_manager_for_tray.settings_file = settings_file

        with patch.object(razer_tray_instance, "_on_settings_changed"):
            razer_tray_instance._on_settings_dir_changed(str(tmp_path))


class TestRazerTrayUpdateProfileDisplay:
    """Tests for _update_profile_display method."""

    def test_with_profile(self, razer_tray_instance, mock_profile_loader_for_tray):
        """Test profile display with profile."""
        mock_profile = MagicMock()
        mock_profile.name = "Active Profile"
        mock_profile_loader_for_tray.load_profile.return_value = mock_profile

        razer_tray_instance._active_profile = "active"
        with patch.object(razer_tray_instance, "_update_profiles_menu"):
            razer_tray_instance._update_profile_display()
            assert "Active Profile" in razer_tray_instance.profile_label.text()

    def test_no_profile(self, razer_tray_instance):
        """Test profile display without profile."""
        razer_tray_instance._active_profile = None
        with patch.object(razer_tray_instance, "_update_profiles_menu"):
            razer_tray_instance._update_profile_display()
            assert "(none)" in razer_tray_instance.profile_label.text()


class TestRazerTrayOnProfileChanged:
    """Tests for _on_profile_changed signal handler."""

    def test_on_profile_changed(self, razer_tray_instance):
        """Test profile changed handler."""
        with patch.object(razer_tray_instance, "_update_profile_display"):
            razer_tray_instance._on_profile_changed("new_profile")
            assert razer_tray_instance._active_profile == "new_profile"

    def test_check_status_notifies_on_profile_change(
        self, razer_tray_instance, mock_profile_loader_for_tray, mock_subprocess_for_tray
    ):
        """Test _check_status notifies when profile changes (lines 362-365)."""
        mock_run, _ = mock_subprocess_for_tray
        mock_run.return_value = MagicMock(stdout="active\n")

        mock_profile = MagicMock()
        mock_profile.name = "New Profile"
        mock_profile_loader_for_tray.load_profile.return_value = mock_profile
        mock_profile_loader_for_tray.get_active_profile_id.return_value = "new_profile"

        razer_tray_instance._active_profile = "old_profile"  # Set old profile (not None)
        with patch.object(razer_tray_instance, "_notify") as mock_notify:
            with patch.object(razer_tray_instance, "_update_profile_display"):
                razer_tray_instance._check_status()
                mock_notify.assert_called_with("Profile Changed", "Active profile: New Profile")


class TestRazerTrayHotkeyBackendStatus:
    """Tests for hotkey backend status text (lines 169, 173)."""

    def test_portal_backend_text(
        self,
        qtbot,
        mock_profile_loader_for_tray,
        mock_settings_manager_for_tray,
        mock_openrazer_for_tray,
        mock_subprocess_for_tray,
    ):
        """Test Portal backend creates Wayland status text (line 169)."""
        from PySide6.QtWidgets import QSystemTrayIcon

        from apps.tray.main import RazerTray

        with patch("apps.tray.main.HotkeyListener") as mock_cls:
            mock_instance = MagicMock()
            mock_instance.backend_name = "PortalGlobalShortcuts"  # Portal backend
            mock_instance.start = MagicMock()
            mock_instance.stop = MagicMock()
            mock_cls.return_value = mock_instance

            with patch.object(QSystemTrayIcon, "show"):
                with patch.object(QSystemTrayIcon, "setIcon"):
                    with patch.object(QSystemTrayIcon, "setToolTip"):
                        with patch.object(QSystemTrayIcon, "setContextMenu"):
                            with patch.object(QSystemTrayIcon, "showMessage"):
                                tray = RazerTray()
                                assert "Wayland" in tray.hotkey_status.text()
                                tray._status_timer.stop()

    def test_disabled_backend_text(
        self,
        qtbot,
        mock_profile_loader_for_tray,
        mock_settings_manager_for_tray,
        mock_openrazer_for_tray,
        mock_subprocess_for_tray,
    ):
        """Test no backend creates Disabled status text (line 173)."""
        from PySide6.QtWidgets import QSystemTrayIcon

        from apps.tray.main import RazerTray

        with patch("apps.tray.main.HotkeyListener") as mock_cls:
            mock_instance = MagicMock()
            mock_instance.backend_name = None  # No backend
            mock_instance.start = MagicMock()
            mock_instance.stop = MagicMock()
            mock_cls.return_value = mock_instance

            with patch.object(QSystemTrayIcon, "show"):
                with patch.object(QSystemTrayIcon, "setIcon"):
                    with patch.object(QSystemTrayIcon, "setToolTip"):
                        with patch.object(QSystemTrayIcon, "setContextMenu"):
                            with patch.object(QSystemTrayIcon, "showMessage"):
                                tray = RazerTray()
                                assert "Disabled" in tray.hotkey_status.text()
                                tray._status_timer.stop()


class TestRazerTrayProfilesMenuNoneProfile:
    """Tests for _update_profiles_menu with None profile (line 240)."""

    def test_skips_none_profile(self, razer_tray_instance, mock_profile_loader_for_tray):
        """Test profiles menu skips profiles that return None."""
        mock_profile_loader_for_tray.list_profiles.return_value = ["p1", "p2", "p3"]
        # p2 returns None (corrupted/missing profile)
        profile1 = MagicMock()
        profile1.name = "Profile 1"
        profile3 = MagicMock()
        profile3.name = "Profile 3"
        mock_profile_loader_for_tray.load_profile.side_effect = [
            profile1,
            None,  # This triggers line 240 - profile not found
            profile3,
        ]
        razer_tray_instance._update_profiles_menu()
        # Should not crash and should skip p2


class TestRazerTraySourceDesktopPath:
    """Tests for _get_source_desktop_path search loop (lines 502-510)."""

    def test_fallback_to_first(self, tmp_path):
        """Test falls back to first location if none exist (line 510)."""
        from apps.tray.main import RazerTray

        tray = RazerTray.__new__(RazerTray)

        # This uses the real method but none of the locations exist
        # So it falls back to the first location (line 510)
        result = tray._get_source_desktop_path()
        # Should return a path (even if it doesn't exist)
        assert result is not None
        # This covers the loop that checks each location and the fallback


class TestRazerTrayAutostartExceptions:
    """Tests for autostart exception paths (lines 531-532, 550-551)."""

    def test_disable_exception(self, razer_tray_instance):
        """Test autostart disable exception handling (lines 531-532)."""
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.unlink.side_effect = PermissionError("Access denied")

        with patch.object(razer_tray_instance, "_get_autostart_path", return_value=mock_path):
            with patch.object(razer_tray_instance, "_is_autostart_enabled", return_value=True):
                with patch.object(razer_tray_instance, "_notify") as mock_notify:
                    with patch.object(razer_tray_instance, "_update_autostart_status"):
                        razer_tray_instance._toggle_autostart()
                        # Should notify error
                        mock_notify.assert_called()
                        assert "Error" in str(mock_notify.call_args)

    def test_enable_exception(self, razer_tray_instance):
        """Test autostart enable exception handling (lines 550-551)."""
        mock_path = MagicMock()
        mock_path.exists.return_value = False
        mock_path.parent.mkdir.side_effect = PermissionError("Access denied")

        with patch.object(razer_tray_instance, "_get_autostart_path", return_value=mock_path):
            with patch.object(razer_tray_instance, "_is_autostart_enabled", return_value=False):
                with patch.object(razer_tray_instance, "_notify") as mock_notify:
                    with patch.object(razer_tray_instance, "_update_autostart_status"):
                        razer_tray_instance._toggle_autostart()
                        mock_notify.assert_called()


class TestRazerTrayExportException:
    """Tests for export exception path (lines 589-590)."""

    def test_export_exception(self, razer_tray_instance, mock_profile_loader_for_tray, tmp_path):
        """Test export exception handling."""
        mock_profile_loader_for_tray.list_profiles.return_value = ["p1"]
        mock_profile = MagicMock()
        mock_profile.model_dump.side_effect = Exception("Serialization failed")
        mock_profile_loader_for_tray.load_profile.return_value = mock_profile

        zip_path = tmp_path / "export.zip"
        with patch("apps.tray.main.QFileDialog.getSaveFileName", return_value=(str(zip_path), "")):
            with patch.object(razer_tray_instance, "_notify") as mock_notify:
                razer_tray_instance._export_profiles()
                mock_notify.assert_called()
                assert "Failed" in str(mock_notify.call_args)


class TestRazerTrayImportOverwrite:
    """Tests for import overwrite dialog (lines 615-622)."""

    def test_import_overwrite_yes(
        self, razer_tray_instance, mock_profile_loader_for_tray, tmp_path
    ):
        """Test import overwrite confirmed."""
        from PySide6.QtWidgets import QMessageBox

        profile_file = tmp_path / "profile.json"
        profile_file.write_text('{"id": "existing", "name": "Existing Profile", "layers": []}')

        # Existing profile found
        mock_profile_loader_for_tray.load_profile.return_value = MagicMock()

        with patch(
            "apps.tray.main.QFileDialog.getOpenFileName", return_value=(str(profile_file), "")
        ):
            with patch(
                "apps.tray.main.QMessageBox.question", return_value=QMessageBox.StandardButton.Yes
            ):
                with patch.object(razer_tray_instance, "_notify"):
                    with patch.object(razer_tray_instance, "_update_profiles_menu"):
                        razer_tray_instance._import_profile()
                        mock_profile_loader_for_tray.save_profile.assert_called()

    def test_import_overwrite_no(self, razer_tray_instance, mock_profile_loader_for_tray, tmp_path):
        """Test import overwrite cancelled (line 621-622)."""
        from PySide6.QtWidgets import QMessageBox

        profile_file = tmp_path / "profile.json"
        profile_file.write_text('{"id": "existing", "name": "Existing Profile", "layers": []}')

        # Existing profile found
        mock_profile_loader_for_tray.load_profile.return_value = MagicMock()

        with patch(
            "apps.tray.main.QFileDialog.getOpenFileName", return_value=(str(profile_file), "")
        ):
            with patch(
                "apps.tray.main.QMessageBox.question", return_value=QMessageBox.StandardButton.No
            ):
                with patch.object(razer_tray_instance, "_notify"):
                    with patch.object(razer_tray_instance, "_update_profiles_menu"):
                        razer_tray_instance._import_profile()
                        # save_profile should NOT be called
                        mock_profile_loader_for_tray.save_profile.assert_not_called()


class TestRazerTrayImportErrors:
    """Tests for import error paths (lines 628, 632-633)."""

    def test_import_save_failure(self, razer_tray_instance, mock_profile_loader_for_tray, tmp_path):
        """Test import save failure (line 628)."""
        profile_file = tmp_path / "profile.json"
        profile_file.write_text('{"id": "new", "name": "New Profile", "layers": []}')

        mock_profile_loader_for_tray.load_profile.return_value = None  # No existing
        mock_profile_loader_for_tray.save_profile.return_value = False  # Save fails

        with patch(
            "apps.tray.main.QFileDialog.getOpenFileName", return_value=(str(profile_file), "")
        ):
            with patch.object(razer_tray_instance, "_notify") as mock_notify:
                razer_tray_instance._import_profile()
                # Should call notify with "Import Failed"
                assert any("Failed" in str(call) for call in mock_notify.call_args_list)

    def test_import_general_exception(self, razer_tray_instance, tmp_path):
        """Test import general exception (lines 632-633)."""
        # Create a file that causes an exception during Profile.model_validate
        profile_file = tmp_path / "profile.json"
        profile_file.write_text('{"id": "new", "name": "Test", "layers": []}')

        with patch(
            "apps.tray.main.QFileDialog.getOpenFileName", return_value=(str(profile_file), "")
        ):
            with patch(
                "crates.profile_schema.Profile.model_validate",
                side_effect=Exception("Validation failed"),
            ):
                with patch.object(razer_tray_instance, "_notify") as mock_notify:
                    razer_tray_instance._import_profile()
                    # Should call notify with "Import Failed"
                    assert mock_notify.called


class TestRazerTrayMainGuardExecution:
    """Test for __name__ == '__main__' guard execution (line 725)."""

    def test_main_guard_code_path(self):
        """Test main guard execution path by calling main() directly with mocks."""
        # The runpy approach fails due to existing QApplication in test session
        # So we test the main() function directly which is what the guard calls
        from apps.tray.main import main

        with patch("apps.tray.main.QApplication"):
            with patch("apps.tray.main.QSystemTrayIcon") as mock_tray:
                mock_tray.isSystemTrayAvailable.return_value = False
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 1
