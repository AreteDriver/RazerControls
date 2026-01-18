"""Hotkey backends for different desktop environments.

Provides platform-specific implementations for global hotkey handling:
- PortalGlobalShortcuts: xdg-desktop-portal for Wayland (GNOME, KDE, etc.)
- X11Hotkeys: pynput-based for X11 sessions
"""

import logging
import os
import threading
from abc import ABC, abstractmethod
from collections.abc import Callable

from crates.profile_schema import HotkeyBinding

logger = logging.getLogger(__name__)


def to_portal_format(binding: HotkeyBinding) -> str:
    """Convert HotkeyBinding to GTK accelerator format for portal.

    Examples:
        ctrl+shift+1 -> <Primary><Shift>1
        alt+f1 -> <Alt>F1
        ctrl+a -> <Primary>a
    """
    parts = []
    if "ctrl" in binding.modifiers:
        parts.append("<Primary>")
    if "alt" in binding.modifiers:
        parts.append("<Alt>")
    if "shift" in binding.modifiers:
        parts.append("<Shift>")

    # Handle function keys and regular keys
    key = binding.key
    if key.startswith("f") and key[1:].isdigit():
        parts.append(key.upper())  # F1, F2, etc.
    elif len(key) == 1:
        parts.append(key)  # Single character keys
    else:
        parts.append(key.capitalize())

    return "".join(parts)


class HotkeyBackend(ABC):
    """Base class for platform-specific hotkey handlers."""

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this backend works in current environment."""

    @abstractmethod
    def register_shortcuts(self, shortcuts: list[tuple[str, HotkeyBinding]]) -> bool:
        """Register shortcuts. Returns True on success.

        Args:
            shortcuts: List of (action_id, binding) tuples
        """

    @abstractmethod
    def start(self) -> None:
        """Start listening for shortcuts."""

    @abstractmethod
    def stop(self) -> None:
        """Stop listening."""

    @property
    def name(self) -> str:
        """Return backend name for logging."""
        return self.__class__.__name__


class PortalGlobalShortcuts(HotkeyBackend):
    """xdg-desktop-portal GlobalShortcuts for Wayland.

    Uses the freedesktop.org portal API which works across all
    Wayland compositors (GNOME, KDE, Hyprland, Sway, etc.)
    """

    PORTAL_BUS = "org.freedesktop.portal.Desktop"
    PORTAL_PATH = "/org/freedesktop/portal/desktop"
    PORTAL_IFACE = "org.freedesktop.portal.GlobalShortcuts"

    def __init__(self, on_activated: Callable[[str], None]):
        """Initialize portal backend.

        Args:
            on_activated: Callback called with shortcut_id when activated
        """
        self.on_activated = on_activated
        self._bus = None
        self._portal = None
        self._session_handle: str | None = None
        self._shortcuts: list[tuple[str, HotkeyBinding]] = []
        self._running = False
        self._signal_subscription = None

    def is_available(self) -> bool:
        """Check if portal service exists and session is Wayland."""
        session_type = os.environ.get("XDG_SESSION_TYPE", "")
        if session_type != "wayland":
            logger.debug("Not Wayland session (XDG_SESSION_TYPE=%s)", session_type)
            return False

        try:
            from pydbus import SessionBus

            bus = SessionBus()
            portal = bus.get(self.PORTAL_BUS, self.PORTAL_PATH)
            # Check if GlobalShortcuts interface exists
            # by checking for the interface in introspection
            introspection = portal.Introspect()
            if "org.freedesktop.portal.GlobalShortcuts" not in introspection:
                logger.debug("GlobalShortcuts interface not found in portal")
                return False
            return True
        except Exception as e:
            logger.debug("Portal not available: %s", e)
            return False

    def register_shortcuts(self, shortcuts: list[tuple[str, HotkeyBinding]]) -> bool:
        """Register shortcuts with the portal."""
        self._shortcuts = shortcuts
        return True

    def start(self) -> None:
        """Start listening for shortcuts via portal."""
        if self._running:
            return

        try:
            from gi.repository import GLib
            from pydbus import SessionBus

            self._bus = SessionBus()
            self._portal = self._bus.get(self.PORTAL_BUS, self.PORTAL_PATH)

            # Create session
            import secrets

            token = secrets.token_hex(8)
            options = {
                "handle_token": GLib.Variant("s", token),
                "session_handle_token": GLib.Variant("s", f"razer_{token}"),
            }

            # Request path for response
            sender = self._bus.con.get_unique_name().replace(".", "_").replace(":", "")
            request_path = f"/org/freedesktop/portal/desktop/request/{sender}/{token}"

            # Subscribe to Response signal before making request
            response_received = threading.Event()
            session_handle = [None]

            def on_response(sender, obj, iface, signal, params):
                if signal == "Response":
                    response_code, results = params
                    if response_code == 0:
                        session_handle[0] = results.get("session_handle", "")
                    response_received.set()

            self._bus.con.signal_subscribe(
                None,
                "org.freedesktop.portal.Request",
                "Response",
                request_path,
                None,
                0,
                on_response,
            )

            # Create session
            self._portal.CreateSession["org.freedesktop.portal.GlobalShortcuts"](options)

            # Wait for response (with timeout)
            response_received.wait(timeout=5.0)
            self._session_handle = session_handle[0]

            if not self._session_handle:
                logger.error("Failed to create portal session")
                return

            logger.info("Portal session created: %s", self._session_handle)

            # Build shortcuts list for portal
            portal_shortcuts = []
            for action_id, binding in self._shortcuts:
                if not binding.enabled or not binding.key:
                    continue
                portal_shortcuts.append(
                    (
                        action_id,
                        {
                            "description": GLib.Variant("s", f"Switch to profile {action_id}"),
                            "preferred_trigger": GLib.Variant("s", to_portal_format(binding)),
                        },
                    )
                )

            if portal_shortcuts:
                # Bind shortcuts
                bind_token = secrets.token_hex(8)
                bind_options = {"handle_token": GLib.Variant("s", bind_token)}

                self._portal.BindShortcuts["org.freedesktop.portal.GlobalShortcuts"](
                    self._session_handle,
                    GLib.Variant("a(sa{sv})", portal_shortcuts),
                    "",  # parent_window
                    bind_options,
                )
                logger.info("Registered %d shortcuts with portal", len(portal_shortcuts))

            # Subscribe to Activated signal
            def on_activated(sender, obj, iface, signal, params):
                if signal == "Activated":
                    _session, shortcut_id, _timestamp, _options = params
                    logger.debug("Shortcut activated: %s", shortcut_id)
                    self.on_activated(shortcut_id)

            self._signal_subscription = self._bus.con.signal_subscribe(
                None,
                self.PORTAL_IFACE,
                "Activated",
                self.PORTAL_PATH,
                None,
                0,
                on_activated,
            )

            self._running = True
            logger.info("Portal hotkey backend started")

        except ImportError as e:
            logger.error("Missing dependency for portal: %s", e)
        except Exception as e:
            logger.error("Failed to start portal backend: %s", e)

    def stop(self) -> None:
        """Stop listening and close session."""
        if not self._running:
            return

        try:
            if self._signal_subscription and self._bus:
                self._bus.con.signal_unsubscribe(self._signal_subscription)
                self._signal_subscription = None

            if self._session_handle and self._portal:
                # Close the session
                try:
                    self._bus.con.call_sync(
                        self.PORTAL_BUS,
                        self._session_handle,
                        "org.freedesktop.portal.Session",
                        "Close",
                        None,
                        None,
                        0,
                        -1,
                        None,
                    )
                except (OSError, AttributeError):
                    pass  # Session may already be closed

            self._session_handle = None
            self._portal = None
            self._bus = None
            self._running = False
            logger.info("Portal hotkey backend stopped")

        except Exception as e:
            logger.error("Error stopping portal backend: %s", e)


class X11Hotkeys(HotkeyBackend):
    """pynput-based hotkeys for X11 sessions."""

    def __init__(self, on_activated: Callable[[str], None]):
        """Initialize X11 backend.

        Args:
            on_activated: Callback called with shortcut_id when activated
        """
        self.on_activated = on_activated
        self._shortcuts: list[tuple[str, HotkeyBinding]] = []
        self._current_keys: set[str] = set()
        self._triggered: set[str] = set()
        self._listener = None

    def is_available(self) -> bool:
        """Check if running on X11."""
        session_type = os.environ.get("XDG_SESSION_TYPE", "")
        # Default to X11 if not specified (legacy systems)
        if session_type in ("x11", ""):
            try:
                from pynput import keyboard  # noqa: F401

                return True
            except ImportError:
                logger.debug("pynput not available")
                return False
        return False

    def register_shortcuts(self, shortcuts: list[tuple[str, HotkeyBinding]]) -> bool:
        """Store shortcuts for matching."""
        self._shortcuts = shortcuts
        return True

    def start(self) -> None:
        """Start pynput listener."""
        if self._listener:
            return

        try:
            from pynput import keyboard

            self._listener = keyboard.Listener(
                on_press=self._on_press,
                on_release=self._on_release,
            )
            self._listener.daemon = True
            self._listener.start()
            logger.info("X11 hotkey backend started")
        except Exception as e:
            logger.error("Failed to start X11 backend: %s", e)

    def stop(self) -> None:
        """Stop pynput listener."""
        if self._listener:
            self._listener.stop()
            self._listener = None
            self._current_keys.clear()
            self._triggered.clear()
            logger.info("X11 hotkey backend stopped")

    def _normalize_key(self, key) -> str | None:
        """Normalize a pynput key to a comparable string."""
        from pynput import keyboard

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
                # Number key 0 has vk code 48
                if key.vk == 48:
                    return "0"
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
            if mod not in self._current_keys:
                return False

        # Check the main key is pressed
        return binding.key.lower() in self._current_keys

    def _on_press(self, key) -> None:
        """Handle key press event."""
        normalized = self._normalize_key(key)
        if normalized:
            self._current_keys.add(normalized)

        # Check each shortcut
        for action_id, binding in self._shortcuts:
            if action_id not in self._triggered and self._check_binding(binding):
                self._triggered.add(action_id)
                self.on_activated(action_id)
                break

    def _on_release(self, key) -> None:
        """Handle key release event."""
        normalized = self._normalize_key(key)
        if normalized:
            self._current_keys.discard(normalized)

            # Clear triggered state for shortcuts no longer active
            for action_id, binding in self._shortcuts:
                if action_id in self._triggered and not self._check_binding(binding):
                    self._triggered.discard(action_id)
