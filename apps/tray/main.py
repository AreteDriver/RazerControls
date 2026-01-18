"""System tray application for Razer Control Center.

Provides:
- Quick profile switching
- Device status monitoring
- Daemon control
- Desktop notifications
"""

import atexit
import fcntl
import os
import shutil
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QFileSystemWatcher, QObject, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QMenu,
    QMessageBox,
    QSystemTrayIcon,
)

from crates.profile_schema import ProfileLoader, SettingsManager
from services.openrazer_bridge import OpenRazerBridge

from .hotkeys import HotkeyListener

# Single-instance lock
LOCK_FILE = Path.home() / ".cache" / "razer-tray.lock"
_lock_file_handle = None


def acquire_instance_lock() -> bool:
    """Try to acquire single-instance lock. Returns True if acquired."""
    global _lock_file_handle
    try:
        LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
        _lock_file_handle = open(LOCK_FILE, "w")
        fcntl.flock(_lock_file_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        _lock_file_handle.write(str(os.getpid()))
        _lock_file_handle.flush()
        return True
    except OSError:
        if _lock_file_handle:
            _lock_file_handle.close()
            _lock_file_handle = None
        return False


def release_instance_lock():
    """Release the single-instance lock."""
    global _lock_file_handle
    if _lock_file_handle:
        try:
            fcntl.flock(_lock_file_handle.fileno(), fcntl.LOCK_UN)
            _lock_file_handle.close()
        except OSError:
            pass
        _lock_file_handle = None


class TraySignals(QObject):
    """Signals for cross-thread communication."""

    profile_changed = Signal(str)
    daemon_status_changed = Signal(bool)
    device_connected = Signal(str)
    device_disconnected = Signal(str)
    hotkey_switch = Signal(int)  # Profile index from hotkey


class RazerTray(QSystemTrayIcon):
    """System tray icon for Razer Control Center."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.signals = TraySignals()
        self.profile_loader = ProfileLoader()
        self.settings_manager = SettingsManager()
        self.openrazer = OpenRazerBridge()

        # State
        self._active_profile: str | None = None
        self._daemon_running = False
        self._devices: list = []

        # Start global hotkey listener (share settings manager)
        # Must be before _create_menu() which accesses hotkey_listener.backend_name
        self.hotkey_listener = HotkeyListener(self._emit_hotkey_switch, self.settings_manager)
        self.hotkey_listener.start()

        # Create icon
        self._create_icon()

        # Create menu
        self._create_menu()

        # Set up timers
        self._status_timer = QTimer()
        self._status_timer.timeout.connect(self._check_status)
        self._status_timer.start(5000)  # Check every 5 seconds

        # Initial status check
        self._check_status()

        # Connect signals
        self.activated.connect(self._on_activated)
        self.signals.profile_changed.connect(self._on_profile_changed)
        self.signals.hotkey_switch.connect(self._on_hotkey_switch)

        # Watch settings file for changes (hotkey reload on save)
        self._settings_watcher = QFileSystemWatcher()
        self._setup_settings_watcher()

        # Show the tray icon
        self.show()

    def _create_icon(self) -> None:
        """Create the tray icon."""
        # Create a simple green Razer-style icon
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw a green circle (Razer green: #44D62C)
        painter.setBrush(QColor("#44D62C"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(4, 4, 56, 56)

        # Draw "R" in the center
        painter.setPen(QColor("white"))
        font = QFont("Arial", 32, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "R")

        painter.end()

        self.setIcon(QIcon(pixmap))
        self.setToolTip("Razer Control Center")

    def _setup_settings_watcher(self) -> None:
        """Set up file watcher for settings changes."""
        settings_file = str(self.settings_manager.settings_file)

        # Ensure settings file exists (creates defaults if needed)
        self.settings_manager.load()
        if self.settings_manager.settings_file.exists():
            self._settings_watcher.addPath(settings_file)
            self._settings_watcher.fileChanged.connect(self._on_settings_changed)

        # Also watch the directory in case file is recreated
        settings_dir = str(self.settings_manager.config_dir)
        if self.settings_manager.config_dir.exists():
            self._settings_watcher.addPath(settings_dir)
            self._settings_watcher.directoryChanged.connect(self._on_settings_dir_changed)

    def _on_settings_changed(self, path: str) -> None:
        """Handle settings file change."""
        # Reload hotkey bindings
        self.hotkey_listener.reload_bindings()

        # Update profiles menu to show new hotkey hints
        self._update_profiles_menu()

        # Re-add the file to watcher (some editors replace the file)
        if path not in self._settings_watcher.files():
            if Path(path).exists():
                self._settings_watcher.addPath(path)

    def _on_settings_dir_changed(self, path: str) -> None:
        """Handle settings directory change (file created/deleted)."""
        settings_file = str(self.settings_manager.settings_file)

        # If settings file was recreated, start watching it
        if self.settings_manager.settings_file.exists():
            if settings_file not in self._settings_watcher.files():
                self._settings_watcher.addPath(settings_file)
                # Reload since file changed
                self._on_settings_changed(settings_file)

    def _create_menu(self) -> None:
        """Create the context menu."""
        self.menu = QMenu()

        # Header
        header = self.menu.addAction("Razer Control Center")
        header.setEnabled(False)
        self.menu.addSeparator()

        # Active profile display
        self.profile_label = self.menu.addAction("Profile: (loading...)")
        self.profile_label.setEnabled(False)

        # Hotkey backend status
        backend = self.hotkey_listener.backend_name
        if backend == "PortalGlobalShortcuts":
            backend_text = "Hotkeys: Portal (Wayland)"
        elif backend == "X11Hotkeys":
            backend_text = "Hotkeys: X11 (pynput)"
        else:
            backend_text = "Hotkeys: Disabled"
        self.hotkey_status = self.menu.addAction(backend_text)
        self.hotkey_status.setEnabled(False)

        # Profiles submenu
        self.profiles_menu = self.menu.addMenu("Switch Profile")
        self._update_profiles_menu()

        self.menu.addSeparator()

        # Devices submenu
        self.devices_menu = self.menu.addMenu("Devices")
        self._update_devices_menu()

        self.menu.addSeparator()

        # Daemon control
        self.daemon_menu = self.menu.addMenu("Daemon")
        self.daemon_status = self.daemon_menu.addAction("Status: Unknown")
        self.daemon_status.setEnabled(False)
        self.daemon_menu.addSeparator()
        self.daemon_start = self.daemon_menu.addAction("Start Daemon")
        self.daemon_start.triggered.connect(self._start_daemon)
        self.daemon_stop = self.daemon_menu.addAction("Stop Daemon")
        self.daemon_stop.triggered.connect(self._stop_daemon)
        self.daemon_restart = self.daemon_menu.addAction("Restart Daemon")
        self.daemon_restart.triggered.connect(self._restart_daemon)

        self.menu.addSeparator()

        # Quick actions
        open_gui = self.menu.addAction("Open Control Center")
        open_gui.triggered.connect(self._open_gui)

        open_config = self.menu.addAction("Open Config Folder")
        open_config.triggered.connect(self._open_config)

        # Autostart toggle
        self.autostart_action = self.menu.addAction("")
        self.autostart_action.setCheckable(True)
        self._update_autostart_status()
        self.autostart_action.triggered.connect(self._toggle_autostart)

        self.menu.addSeparator()

        # Quit
        quit_action = self.menu.addAction("Quit")
        quit_action.triggered.connect(self._quit)

        self.setContextMenu(self.menu)

    def _update_profiles_menu(self) -> None:
        """Update the profiles submenu."""
        self.profiles_menu.clear()

        profiles = self.profile_loader.list_profiles()
        active_id = self.profile_loader.get_active_profile_id()
        bindings = self.settings_manager.settings.hotkeys.profile_hotkeys

        if not profiles:
            no_profiles = self.profiles_menu.addAction("(No profiles)")
            no_profiles.setEnabled(False)
            return

        for idx, profile_id in enumerate(profiles):
            profile = self.profile_loader.load_profile(profile_id)
            if not profile:
                continue

            name = profile.name
            if profile_id == active_id:
                name = f"● {name}"

            # Add hotkey hint for first 9 profiles (if binding exists and is enabled)
            if idx < len(bindings):
                binding = bindings[idx]
                if binding.enabled and binding.key:
                    hotkey_str = binding.to_display_string()
                    name = f"{name}  ({hotkey_str})"

            action = self.profiles_menu.addAction(name)
            action.setData(profile_id)
            action.triggered.connect(lambda checked, pid=profile_id: self._switch_profile(pid))

        self.profiles_menu.addSeparator()

        # Export/Import
        export_action = self.profiles_menu.addAction("Export All...")
        export_action.triggered.connect(self._export_profiles)
        import_action = self.profiles_menu.addAction("Import...")
        import_action.triggered.connect(self._import_profile)

        self.profiles_menu.addSeparator()
        refresh = self.profiles_menu.addAction("Refresh")
        refresh.triggered.connect(self._update_profiles_menu)

    def _update_devices_menu(self) -> None:
        """Update the devices submenu."""
        self.devices_menu.clear()

        # Try to connect to OpenRazer
        if not self.openrazer.is_connected():
            self.openrazer.connect()

        devices = self.openrazer.discover_devices()
        self._devices = devices

        if not devices:
            no_devices = self.devices_menu.addAction("(No devices found)")
            no_devices.setEnabled(False)
            self.devices_menu.addSeparator()
            check_openrazer = self.devices_menu.addAction("Check OpenRazer...")
            check_openrazer.triggered.connect(self._check_openrazer)
            return

        for dev in devices:
            device_menu = self.devices_menu.addMenu(dev.name)

            # Device info
            info = device_menu.addAction(f"Serial: {dev.serial}")
            info.setEnabled(False)

            if dev.has_dpi:
                dpi_info = device_menu.addAction(f"DPI: {dev.dpi[0]}x{dev.dpi[1]}")
                dpi_info.setEnabled(False)

            if dev.has_poll_rate:
                poll_info = device_menu.addAction(f"Poll Rate: {dev.poll_rate} Hz")
                poll_info.setEnabled(False)

            if dev.has_battery:
                status = "charging" if dev.is_charging else "discharging"
                batt_info = device_menu.addAction(f"Battery: {dev.battery_level}% ({status})")
                batt_info.setEnabled(False)

            if dev.has_brightness:
                bright_info = device_menu.addAction(f"Brightness: {dev.brightness}%")
                bright_info.setEnabled(False)

            # Quick actions
            if dev.has_dpi or dev.has_lighting:
                device_menu.addSeparator()

            if dev.has_dpi:
                dpi_menu = device_menu.addMenu("Set DPI")
                for dpi in [400, 800, 1600, 3200, 6400]:
                    if dpi <= dev.max_dpi:
                        dpi_action = dpi_menu.addAction(f"{dpi}")
                        dpi_action.triggered.connect(
                            lambda checked, s=dev.serial, d=dpi: self._set_dpi(s, d)
                        )

            if dev.has_lighting and dev.supported_effects:
                effect_menu = device_menu.addMenu("Lighting")
                for effect in dev.supported_effects:
                    effect_action = effect_menu.addAction(effect.capitalize())
                    effect_action.triggered.connect(
                        lambda checked, s=dev.serial, e=effect: self._set_effect(s, e)
                    )

        self.devices_menu.addSeparator()
        refresh = self.devices_menu.addAction("Refresh")
        refresh.triggered.connect(self._update_devices_menu)

    def _check_status(self) -> None:
        """Check daemon and profile status."""
        # Check daemon status
        try:
            result = subprocess.run(
                ["systemctl", "--user", "is-active", "razer-remap-daemon"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            running = result.stdout.strip() == "active"
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            running = False

        if running != self._daemon_running:
            self._daemon_running = running
            self._update_daemon_status()

        # Check active profile
        active_id = self.profile_loader.get_active_profile_id()
        if active_id != self._active_profile:
            old_profile = self._active_profile
            self._active_profile = active_id
            self._update_profile_display()

            if old_profile is not None:  # Don't notify on startup
                profile = self.profile_loader.load_profile(active_id) if active_id else None
                name = profile.name if profile else active_id
                self._notify("Profile Changed", f"Active profile: {name}")

    def _update_daemon_status(self) -> None:
        """Update daemon status display."""
        if self._daemon_running:
            self.daemon_status.setText("Status: Running")
            self.daemon_start.setEnabled(False)
            self.daemon_stop.setEnabled(True)
        else:
            self.daemon_status.setText("Status: Stopped")
            self.daemon_start.setEnabled(True)
            self.daemon_stop.setEnabled(False)

    def _update_profile_display(self) -> None:
        """Update the profile display in menu."""
        if self._active_profile:
            profile = self.profile_loader.load_profile(self._active_profile)
            name = profile.name if profile else self._active_profile
            self.profile_label.setText(f"Profile: {name}")
            self.setToolTip(f"Razer Control Center\nProfile: {name}")
        else:
            self.profile_label.setText("Profile: (none)")
            self.setToolTip("Razer Control Center\nNo active profile")

        self._update_profiles_menu()

    def _switch_profile(self, profile_id: str) -> None:
        """Switch to a different profile."""
        profile = self.profile_loader.load_profile(profile_id)
        if not profile:
            self._notify("Error", f"Profile not found: {profile_id}", error=True)
            return

        self.profile_loader.set_active_profile(profile_id)
        self._active_profile = profile_id
        self._update_profile_display()

        # Restart daemon to apply
        if self._daemon_running:
            self._restart_daemon()
            self._notify("Profile Activated", f"Switched to: {profile.name}")
        else:
            self._notify("Profile Activated", f"Switched to: {profile.name}\n(Daemon not running)")

    def _set_dpi(self, serial: str, dpi: int) -> None:
        """Set DPI for a device."""
        if self.openrazer.set_dpi(serial, dpi):
            self._notify("DPI Changed", f"Set DPI to {dpi}")
            self._update_devices_menu()
        else:
            self._notify("Error", "Failed to set DPI", error=True)

    def _set_effect(self, serial: str, effect: str) -> None:
        """Set lighting effect for a device."""
        success = False

        if effect == "spectrum":
            success = self.openrazer.set_spectrum_effect(serial)
        elif effect == "static":
            success = self.openrazer.set_static_color(serial, 0, 255, 0)  # Green
        elif effect == "breathing":
            success = self.openrazer.set_breathing_effect(serial, 0, 255, 0)
        elif effect == "breathing_random":
            success = self.openrazer.set_breathing_random(serial)
        elif effect == "wave":
            from services.openrazer_bridge import WaveDirection

            success = self.openrazer.set_wave_effect(serial, WaveDirection.RIGHT)
        elif effect == "none":
            success = self.openrazer.set_none_effect(serial)

        if success:
            self._notify("Lighting Changed", f"Set effect: {effect}")
        else:
            self._notify("Error", f"Failed to set effect: {effect}", error=True)

    def _start_daemon(self) -> None:
        """Start the remap daemon."""
        try:
            subprocess.run(
                ["systemctl", "--user", "start", "razer-remap-daemon"],
                check=True,
                timeout=5,
            )
            self._notify("Daemon Started", "Remap daemon is now running")
            self._check_status()
        except Exception as e:
            self._notify("Error", f"Failed to start daemon: {e}", error=True)

    def _stop_daemon(self) -> None:
        """Stop the remap daemon."""
        try:
            subprocess.run(
                ["systemctl", "--user", "stop", "razer-remap-daemon"],
                check=True,
                timeout=5,
            )
            self._notify("Daemon Stopped", "Remap daemon has stopped")
            self._check_status()
        except Exception as e:
            self._notify("Error", f"Failed to stop daemon: {e}", error=True)

    def _restart_daemon(self) -> None:
        """Restart the remap daemon."""
        try:
            subprocess.run(
                ["systemctl", "--user", "restart", "razer-remap-daemon"],
                check=True,
                timeout=5,
            )
            self._notify("Daemon Restarted", "Remap daemon has restarted")
            self._check_status()
        except Exception as e:
            self._notify("Error", f"Failed to restart daemon: {e}", error=True)

    def _open_gui(self) -> None:
        """Open the main GUI application."""
        try:
            subprocess.Popen(["razer-control-center"])
        except Exception as e:
            self._notify("Error", f"Failed to open GUI: {e}", error=True)

    def _open_config(self) -> None:
        """Open the config folder in file manager."""
        config_dir = self.profile_loader.config_dir
        try:
            subprocess.Popen(["xdg-open", str(config_dir)])
        except Exception as e:
            self._notify("Error", f"Failed to open folder: {e}", error=True)

    def _get_autostart_path(self) -> Path:
        """Get the autostart desktop entry path."""
        return Path.home() / ".config" / "autostart" / "razer-tray.desktop"

    def _get_source_desktop_path(self) -> Path:
        """Get the source desktop entry path."""
        # Check common locations
        locations = [
            Path(__file__).parent.parent.parent / "packaging" / "razer-tray.desktop",
            Path.home() / ".local" / "share" / "applications" / "razer-tray.desktop",
            Path("/usr/share/applications/razer-tray.desktop"),
        ]
        for loc in locations:
            if loc.exists():
                return loc
        return locations[0]  # Fallback to packaging dir

    def _is_autostart_enabled(self) -> bool:
        """Check if autostart is enabled."""
        return self._get_autostart_path().exists()

    def _update_autostart_status(self) -> None:
        """Update the autostart menu item."""
        enabled = self._is_autostart_enabled()
        self.autostart_action.setChecked(enabled)
        self.autostart_action.setText("Start on Login" if not enabled else "Start on Login ✓")

    def _toggle_autostart(self) -> None:
        """Toggle autostart on/off."""
        autostart_path = self._get_autostart_path()

        if self._is_autostart_enabled():
            # Disable autostart
            try:
                autostart_path.unlink()
                self._notify("Autostart Disabled", "Tray will not start on login")
            except Exception as e:
                self._notify("Error", f"Failed to disable autostart: {e}", error=True)
        else:
            # Enable autostart
            try:
                autostart_path.parent.mkdir(parents=True, exist_ok=True)
                source = self._get_source_desktop_path()
                if source.exists():
                    shutil.copy(source, autostart_path)
                else:
                    # Create minimal desktop entry
                    autostart_path.write_text(
                        "[Desktop Entry]\n"
                        "Name=Razer Control Center Tray\n"
                        "Exec=razer-tray\n"
                        "Type=Application\n"
                        "X-GNOME-Autostart-enabled=true\n"
                    )
                self._notify("Autostart Enabled", "Tray will start on login")
            except Exception as e:
                self._notify("Error", f"Failed to enable autostart: {e}", error=True)

        self._update_autostart_status()

    def _export_profiles(self) -> None:
        """Export all profiles to a zip file."""
        import json
        import zipfile
        from datetime import datetime

        profiles = self.profile_loader.list_profiles()
        if not profiles:
            self._notify("Export", "No profiles to export", error=True)
            return

        # Get save location
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"razer_profiles_{timestamp}.zip"

        file_path, _ = QFileDialog.getSaveFileName(
            None,
            "Export Profiles",
            str(Path.home() / default_name),
            "Zip Files (*.zip);;All Files (*)",
        )

        if not file_path:
            return

        try:
            with zipfile.ZipFile(file_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for pid in profiles:
                    profile = self.profile_loader.load_profile(pid)
                    if profile:
                        data = profile.model_dump(mode="json")
                        zf.writestr(f"{pid}.json", json.dumps(data, indent=2))

            self._notify("Export Complete", f"Exported {len(profiles)} profile(s)")
        except Exception as e:
            self._notify("Export Failed", str(e), error=True)

    def _import_profile(self) -> None:
        """Import a profile from a JSON file."""
        import json

        from crates.profile_schema import Profile

        file_path, _ = QFileDialog.getOpenFileName(
            None,
            "Import Profile",
            str(Path.home()),
            "JSON Files (*.json);;All Files (*)",
        )

        if not file_path:
            return

        try:
            data = json.loads(Path(file_path).read_text())
            profile = Profile.model_validate(data)

            # Check for existing
            existing = self.profile_loader.load_profile(profile.id)
            if existing:
                reply = QMessageBox.question(
                    None,
                    "Profile Exists",
                    f"Profile '{profile.id}' already exists. Overwrite?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return

            if self.profile_loader.save_profile(profile):
                self._notify("Import Complete", f"Imported '{profile.name}'")
                self._update_profiles_menu()
            else:
                self._notify("Import Failed", "Could not save profile", error=True)

        except json.JSONDecodeError as e:
            self._notify("Import Failed", f"Invalid JSON: {e}", error=True)
        except Exception as e:
            self._notify("Import Failed", str(e), error=True)

    def _check_openrazer(self) -> None:
        """Show OpenRazer status."""
        try:
            result = subprocess.run(
                ["systemctl", "is-active", "openrazer-daemon"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            status = result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            status = "unknown"

        if status == "active":
            msg = "OpenRazer daemon is running.\n\nNo devices were detected. Check:\n"
            msg += "- Device is connected via USB\n"
            msg += "- Device is supported by OpenRazer"
        else:
            msg = f"OpenRazer daemon status: {status}\n\n"
            msg += "Start with: sudo systemctl start openrazer-daemon"

        QMessageBox.information(None, "OpenRazer Status", msg)

    def _notify(self, title: str, message: str, error: bool = False) -> None:
        """Show a desktop notification."""
        icon = (
            QSystemTrayIcon.MessageIcon.Critical
            if error
            else QSystemTrayIcon.MessageIcon.Information
        )
        self.showMessage(title, message, icon, 3000)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Handle tray icon activation."""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._open_gui()
        elif reason == QSystemTrayIcon.ActivationReason.MiddleClick:
            # Quick refresh
            self._check_status()
            self._update_devices_menu()

    def _on_profile_changed(self, profile_id: str) -> None:
        """Handle profile change signal."""
        self._active_profile = profile_id
        self._update_profile_display()

    def _emit_hotkey_switch(self, index: int) -> None:
        """Emit hotkey switch signal (called from background thread)."""
        self.signals.hotkey_switch.emit(index)

    def _on_hotkey_switch(self, index: int) -> None:
        """Handle hotkey profile switch (runs on main thread)."""
        profiles = self.profile_loader.list_profiles()
        if 0 <= index < len(profiles):
            profile_id = profiles[index]
            self._switch_profile(profile_id)

    def _quit(self) -> None:
        """Quit the tray application."""
        self._status_timer.stop()
        self.hotkey_listener.stop()
        QApplication.quit()


def main():
    """Main entry point for the tray application."""
    # Single-instance check
    if not acquire_instance_lock():
        app = QApplication(sys.argv)
        QMessageBox.warning(
            None,
            "Already Running",
            "Razer Tray is already running.\n\nCheck your system tray for the existing instance.",
        )
        sys.exit(1)

    atexit.register(release_instance_lock)

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # Keep running in tray

    # Check if system tray is available
    if not QSystemTrayIcon.isSystemTrayAvailable():
        print("Error: System tray not available")
        print("Make sure you have a system tray/panel running")
        sys.exit(1)

    # Create tray icon
    tray = RazerTray()

    # Show startup notification
    tray.showMessage(
        "Razer Control Center",
        "Running in system tray",
        QSystemTrayIcon.MessageIcon.Information,
        2000,
    )

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
