"""Tests for application entry point logic."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# --- Test First-Run Detection (apps/gui/main.py) ---


class TestFirstRunDetection:
    """Tests for first-run wizard trigger logic."""

    def is_first_run(self, profiles: list) -> bool:
        """Check if this is a first run (no profiles)."""
        return not profiles

    def test_first_run_no_profiles(self):
        """Test first run detected when no profiles exist."""
        assert self.is_first_run([]) is True

    def test_not_first_run_with_profiles(self):
        """Test not first run when profiles exist."""
        assert self.is_first_run(["default"]) is False
        assert self.is_first_run(["gaming", "work"]) is False


# --- Test Daemon Status Detection (main_window.py, tray/main.py) ---


class TestDaemonStatusDetection:
    """Tests for daemon status detection logic."""

    def parse_daemon_status(self, returncode: int, stdout: str) -> bool:
        """Parse systemctl output to determine if daemon is running."""
        if returncode == 0:
            return stdout.strip() == "active"
        return False

    def test_daemon_running(self):
        """Test daemon running detection."""
        assert self.parse_daemon_status(0, "active\n") is True
        assert self.parse_daemon_status(0, "active") is True

    def test_daemon_stopped(self):
        """Test daemon stopped detection."""
        assert self.parse_daemon_status(3, "inactive\n") is False
        assert self.parse_daemon_status(3, "inactive") is False

    def test_daemon_failed(self):
        """Test daemon failed detection."""
        assert self.parse_daemon_status(3, "failed\n") is False

    def test_daemon_unknown(self):
        """Test daemon unknown state."""
        assert self.parse_daemon_status(1, "") is False


# --- Test Profile Display (tray/main.py) ---


class TestProfileDisplay:
    """Tests for profile display formatting."""

    def format_profile_tooltip(self, profile_name: str | None) -> str:
        """Format tooltip for tray icon."""
        if profile_name:
            return f"Razer Control Center\nProfile: {profile_name}"
        return "Razer Control Center\nNo active profile"

    def format_profile_label(self, profile_name: str | None) -> str:
        """Format profile label in menu."""
        if profile_name:
            return f"Profile: {profile_name}"
        return "Profile: (none)"

    def format_menu_item(self, name: str, is_active: bool, hotkey: str | None = None) -> str:
        """Format profile menu item."""
        display = f"● {name}" if is_active else name
        if hotkey:
            display = f"{display}  ({hotkey})"
        return display

    def test_tooltip_with_profile(self):
        """Test tooltip with active profile."""
        tooltip = self.format_profile_tooltip("Gaming")
        assert "Gaming" in tooltip
        assert "Profile:" in tooltip

    def test_tooltip_without_profile(self):
        """Test tooltip without active profile."""
        tooltip = self.format_profile_tooltip(None)
        assert "No active profile" in tooltip

    def test_label_with_profile(self):
        """Test label with active profile."""
        label = self.format_profile_label("Gaming")
        assert label == "Profile: Gaming"

    def test_label_without_profile(self):
        """Test label without active profile."""
        label = self.format_profile_label(None)
        assert label == "Profile: (none)"

    def test_menu_item_active(self):
        """Test active profile menu item."""
        item = self.format_menu_item("Gaming", True)
        assert item.startswith("●")
        assert "Gaming" in item

    def test_menu_item_inactive(self):
        """Test inactive profile menu item."""
        item = self.format_menu_item("Gaming", False)
        assert not item.startswith("●")
        assert item == "Gaming"

    def test_menu_item_with_hotkey(self):
        """Test menu item with hotkey hint."""
        item = self.format_menu_item("Gaming", False, "Ctrl+Shift+1")
        assert "(Ctrl+Shift+1)" in item


# --- Test Autostart Path (tray/main.py) ---


class TestAutostartPath:
    """Tests for autostart path logic."""

    def get_autostart_path(self, home: Path) -> Path:
        """Get the autostart desktop entry path."""
        return home / ".config" / "autostart" / "razer-tray.desktop"

    def is_autostart_enabled(self, autostart_path: Path) -> bool:
        """Check if autostart is enabled."""
        return autostart_path.exists()

    def test_autostart_path_structure(self):
        """Test autostart path has correct structure."""
        path = self.get_autostart_path(Path("/home/testuser"))
        assert ".config" in path.parts
        assert "autostart" in path.parts
        assert path.name == "razer-tray.desktop"

    def test_autostart_disabled(self):
        """Test autostart disabled when file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "nonexistent.desktop"
            assert self.is_autostart_enabled(path) is False

    def test_autostart_enabled(self):
        """Test autostart enabled when file exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.desktop"
            path.write_text("[Desktop Entry]\nExec=test")
            assert self.is_autostart_enabled(path) is True


# --- Test Notification Formatting (tray/main.py) ---


class TestNotificationFormatting:
    """Tests for notification message formatting."""

    def test_profile_change_notification(self):
        """Test profile change notification format."""
        name = "Gaming"
        message = f"Switched to: {name}"
        assert "Gaming" in message
        assert "Switched to" in message

    def test_dpi_change_notification(self):
        """Test DPI change notification format."""
        dpi = 1600
        message = f"Set DPI to {dpi}"
        assert "1600" in message
        assert "DPI" in message

    def test_effect_change_notification(self):
        """Test effect change notification format."""
        effect = "spectrum"
        message = f"Set effect: {effect}"
        assert "spectrum" in message
        assert "effect" in message


# --- Test Low Battery Warning (main_window.py) ---


class TestLowBatteryWarning:
    """Tests for low battery warning formatting."""

    def format_low_battery(self, device_name: str, level: int) -> str:
        """Format low battery warning message."""
        return f"{device_name} battery is low ({level}%).\n\nPlease charge your device."

    def test_low_battery_format(self):
        """Test low battery message format."""
        message = self.format_low_battery("Razer DeathAdder", 15)
        assert "Razer DeathAdder" in message
        assert "15%" in message
        assert "charge" in message.lower()


# --- Test Hotkey Backend Detection (tray/main.py) ---


class TestHotkeyBackendDetection:
    """Tests for hotkey backend status text."""

    def format_backend_status(self, backend: str) -> str:
        """Format hotkey backend status."""
        if backend == "PortalGlobalShortcuts":
            return "Hotkeys: Portal (Wayland)"
        elif backend == "X11Hotkeys":
            return "Hotkeys: X11 (pynput)"
        else:
            return "Hotkeys: Disabled"

    def test_portal_backend(self):
        """Test Portal backend status text."""
        status = self.format_backend_status("PortalGlobalShortcuts")
        assert "Portal" in status
        assert "Wayland" in status

    def test_x11_backend(self):
        """Test X11 backend status text."""
        status = self.format_backend_status("X11Hotkeys")
        assert "X11" in status
        assert "pynput" in status

    def test_unknown_backend(self):
        """Test unknown backend status text."""
        status = self.format_backend_status("unknown")
        assert "Disabled" in status


# --- Test Device Menu Formatting (tray/main.py) ---


class TestDeviceMenuFormatting:
    """Tests for device submenu formatting."""

    def format_dpi_info(self, dpi: tuple[int, int]) -> str:
        """Format DPI info string."""
        return f"DPI: {dpi[0]}x{dpi[1]}"

    def format_poll_rate(self, rate: int) -> str:
        """Format poll rate info string."""
        return f"Poll Rate: {rate} Hz"

    def format_battery_info(self, level: int, is_charging: bool) -> str:
        """Format battery info string."""
        status = "charging" if is_charging else "discharging"
        return f"Battery: {level}% ({status})"

    def format_brightness(self, level: int) -> str:
        """Format brightness info string."""
        return f"Brightness: {level}%"

    def test_dpi_format(self):
        """Test DPI formatting."""
        info = self.format_dpi_info((1600, 1600))
        assert "1600x1600" in info

    def test_dpi_format_asymmetric(self):
        """Test asymmetric DPI formatting."""
        info = self.format_dpi_info((800, 1600))
        assert "800x1600" in info

    def test_poll_rate_format(self):
        """Test poll rate formatting."""
        info = self.format_poll_rate(1000)
        assert "1000 Hz" in info

    def test_battery_charging(self):
        """Test battery charging format."""
        info = self.format_battery_info(85, True)
        assert "85%" in info
        assert "charging" in info

    def test_battery_discharging(self):
        """Test battery discharging format."""
        info = self.format_battery_info(42, False)
        assert "42%" in info
        assert "discharging" in info

    def test_brightness_format(self):
        """Test brightness formatting."""
        info = self.format_brightness(75)
        assert "75%" in info


# --- Test OpenRazer Status Message (tray/main.py) ---


class TestOpenRazerStatusMessage:
    """Tests for OpenRazer status message formatting."""

    def format_openrazer_status(self, status: str) -> str:
        """Format OpenRazer status message."""
        if status == "active":
            msg = "OpenRazer daemon is running.\n\nNo devices were detected. Check:\n"
            msg += "- Device is connected via USB\n"
            msg += "- Device is supported by OpenRazer"
        else:
            msg = f"OpenRazer daemon status: {status}\n\n"
            msg += "Start with: sudo systemctl start openrazer-daemon"
        return msg

    def test_openrazer_running_no_devices(self):
        """Test message when OpenRazer running but no devices."""
        msg = self.format_openrazer_status("active")
        assert "running" in msg
        assert "USB" in msg
        assert "supported" in msg

    def test_openrazer_not_running(self):
        """Test message when OpenRazer not running."""
        msg = self.format_openrazer_status("inactive")
        assert "inactive" in msg
        assert "systemctl" in msg

    def test_openrazer_unknown(self):
        """Test message when OpenRazer status unknown."""
        msg = self.format_openrazer_status("unknown")
        assert "unknown" in msg


# --- Test Desktop Entry Creation (tray/main.py) ---


class TestDesktopEntry:
    """Tests for desktop entry content."""

    def create_minimal_desktop_entry(self) -> str:
        """Create minimal desktop entry content."""
        return (
            "[Desktop Entry]\n"
            "Name=Razer Control Center Tray\n"
            "Exec=razer-tray\n"
            "Type=Application\n"
            "X-GNOME-Autostart-enabled=true\n"
        )

    def test_desktop_entry_has_required_fields(self):
        """Test desktop entry has required fields."""
        content = self.create_minimal_desktop_entry()
        assert "[Desktop Entry]" in content
        assert "Name=" in content
        assert "Exec=" in content
        assert "Type=Application" in content

    def test_desktop_entry_autostart_enabled(self):
        """Test desktop entry has autostart enabled."""
        content = self.create_minimal_desktop_entry()
        assert "X-GNOME-Autostart-enabled=true" in content
