"""Main application window."""

import subprocess
import threading
from pathlib import Path

from PySide6.QtCore import QObject, QSize, QTimer, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from crates.device_registry import DeviceRegistry
from crates.profile_schema import Profile, ProfileLoader
from services.openrazer_bridge import OpenRazerBridge

from .icons import RazerIcons
from .widgets.app_matcher import AppMatcherWidget
from .widgets.battery_monitor import BatteryMonitorWidget
from .widgets.binding_editor import BindingEditorWidget
from .widgets.device_list import DeviceListWidget
from .widgets.device_visual import DeviceVisualWidget
from .widgets.dpi_editor import DPIStageEditor
from .widgets.macro_editor import MacroEditorWidget
from .widgets.profile_panel import ProfilePanel
from .widgets.razer_controls import RazerControlsWidget
from .widgets.zone_editor import ZoneEditorWidget


class InputMonitor(QObject):
    """Monitor input events from a device and emit button press signals."""

    button_pressed = Signal(str)  # input_code (e.g., 'BTN_LEFT')

    def __init__(self, parent=None):
        super().__init__(parent)
        self._thread: threading.Thread | None = None
        self._running = False
        self._device_path: str | None = None

    def start_monitoring(self, device_path: str) -> None:
        """Start monitoring a device for input events."""
        self.stop_monitoring()
        self._device_path = device_path
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def stop_monitoring(self) -> None:
        """Stop monitoring."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=0.5)
            self._thread = None

    def _monitor_loop(self) -> None:
        """Read events from device (runs in thread)."""
        try:
            import evdev
            from evdev import ecodes

            device = evdev.InputDevice(self._device_path)
            # Don't grab - just read events passively
            for event in device.read_loop():
                if not self._running:
                    break
                # Only emit on key/button press (value=1)
                if event.type == ecodes.EV_KEY and event.value == 1:
                    code_name = ecodes.KEY.get(event.code) or ecodes.BTN.get(event.code)
                    if code_name:
                        # Handle tuple case (some codes have aliases)
                        if isinstance(code_name, tuple):
                            code_name = code_name[0]
                        self.button_pressed.emit(code_name)
        except (OSError, ImportError, AttributeError):
            pass  # Device disconnected, inaccessible, or evdev not available


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Razer Control Center")
        self.setMinimumSize(1000, 700)

        # Initialize components
        self.profile_loader = ProfileLoader()
        self.device_registry = DeviceRegistry()
        self.openrazer = OpenRazerBridge()

        # Current state
        self.current_profile: Profile | None = None

        # Input monitor for button highlighting in Device View (init early)
        self.input_monitor = InputMonitor(self)
        self.input_monitor.button_pressed.connect(self._on_physical_button_pressed)

        # Set up UI (statusbar first since daemon tab uses it)
        self._setup_statusbar()
        self._setup_ui()

        # Load data
        self._load_initial_data()

        # Auto-refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self._refresh_device_status)
        self.refresh_timer.start(5000)  # Every 5 seconds

    def _setup_ui(self):
        """Set up the main UI."""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Left panel - Profile list
        self.profile_panel = ProfilePanel()
        self.profile_panel.profile_selected.connect(self._on_profile_selected)
        self.profile_panel.profile_created.connect(self._on_profile_created)
        self.profile_panel.profile_deleted.connect(self._on_profile_deleted)
        layout.addWidget(self.profile_panel, 1)

        # Right panel - Tabs
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 3)

        # Configure tab icon size
        self.tabs.setIconSize(QSize(18, 18))

        # Devices tab
        self.devices_tab = QWidget()
        self._setup_devices_tab()
        self.tabs.addTab(self.devices_tab, RazerIcons.get(RazerIcons.TAB_DEVICES), "Devices")

        # Bindings tab
        self.bindings_tab = QWidget()
        self._setup_bindings_tab()
        self.tabs.addTab(self.bindings_tab, RazerIcons.get(RazerIcons.TAB_BINDINGS), "Bindings")

        # Macros tab
        self.macro_editor = MacroEditorWidget()
        self.macro_editor.macros_updated.connect(self._on_macros_changed)
        self.tabs.addTab(self.macro_editor, RazerIcons.get(RazerIcons.TAB_MACROS), "Macros")

        # App Switching tab
        self.app_matcher = AppMatcherWidget()
        self.app_matcher.patterns_changed.connect(self._on_app_patterns_changed)
        self.tabs.addTab(self.app_matcher, RazerIcons.get(RazerIcons.TAB_APPS), "App Switching")

        # Razer tab (OpenRazer controls)
        self.razer_tab = RazerControlsWidget(self.openrazer)
        self.razer_tab.device_selected.connect(self._on_razer_device_selected)
        self.tabs.addTab(self.razer_tab, RazerIcons.get(RazerIcons.TAB_LIGHTING), "Lighting & DPI")

        # Device View tab (visual device layout)
        self.device_view_tab = QWidget()
        self._setup_device_view_tab()
        self.tabs.addTab(
            self.device_view_tab, RazerIcons.get(RazerIcons.TAB_DEVICE_VIEW), "Device View"
        )

        # Zone Lighting tab (per-key RGB)
        self.zone_editor = ZoneEditorWidget(self.openrazer)
        self.zone_editor.config_changed.connect(self._on_zone_config_changed)
        self.tabs.addTab(self.zone_editor, RazerIcons.get(RazerIcons.TAB_ZONES), "Zone Lighting")

        # DPI Stages tab
        self.dpi_editor = DPIStageEditor(self.openrazer)
        self.tabs.addTab(self.dpi_editor, RazerIcons.get(RazerIcons.TAB_DPI), "DPI Stages")

        # Battery tab
        self.battery_monitor = BatteryMonitorWidget(self.openrazer)
        self.battery_monitor.low_battery_warning.connect(self._on_low_battery)
        self.tabs.addTab(self.battery_monitor, RazerIcons.get(RazerIcons.TAB_BATTERY), "Battery")

        # Daemon tab
        self.daemon_tab = QWidget()
        self._setup_daemon_tab()
        self.tabs.addTab(self.daemon_tab, RazerIcons.get(RazerIcons.TAB_DAEMON), "Daemon")

        # Menu bar
        self._setup_menu()

    def _setup_menu(self):
        """Set up the menu bar."""
        menubar = self.menuBar()

        # Settings menu
        settings_menu = menubar.addMenu("Settings")

        hotkeys_action = settings_menu.addAction("Configure Hotkeys...")
        hotkeys_action.triggered.connect(self._configure_hotkeys)

        # Help menu
        help_menu = menubar.addMenu("Help")

        wizard_action = help_menu.addAction("Run Setup Wizard...")
        wizard_action.triggered.connect(self._run_setup_wizard)

        help_menu.addSeparator()

        about_action = help_menu.addAction("About")
        about_action.triggered.connect(self._show_about)

    def _run_setup_wizard(self):
        """Open the setup wizard."""
        from .widgets.setup_wizard import SetupWizard

        wizard = SetupWizard(self)
        wizard.exec()

        # Refresh profiles after wizard
        self.profile_panel.refresh()

    def _show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About Razer Control Center",
            "Razer Control Center for Linux\n\n"
            "Configure button remapping, macros, RGB lighting,\n"
            "and DPI settings for your Razer devices.\n\n"
            "https://github.com/AreteDriver/Razer_Controls",
        )

    def _configure_hotkeys(self):
        """Open the hotkey configuration dialog."""
        from .widgets.hotkey_editor import HotkeyEditorDialog

        dialog = HotkeyEditorDialog(self)
        dialog.exec()

    def _setup_devices_tab(self):
        """Set up the devices configuration tab."""
        layout = QVBoxLayout(self.devices_tab)

        # Device list
        group = QGroupBox("Input Devices")
        group_layout = QVBoxLayout(group)

        self.device_list = DeviceListWidget(self.device_registry)
        self.device_list.selection_changed.connect(self._on_device_selection_changed)
        group_layout.addWidget(self.device_list)

        # Buttons
        btn_layout = QHBoxLayout()
        self.refresh_devices_btn = QPushButton(RazerIcons.get(RazerIcons.ACTION_REFRESH), "Refresh")
        self.refresh_devices_btn.clicked.connect(self._refresh_devices)
        btn_layout.addWidget(self.refresh_devices_btn)

        self.apply_devices_btn = QPushButton(
            RazerIcons.get(RazerIcons.ACTION_APPLY), "Apply to Profile"
        )
        self.apply_devices_btn.clicked.connect(self._apply_device_selection)
        btn_layout.addWidget(self.apply_devices_btn)
        btn_layout.addStretch()

        group_layout.addLayout(btn_layout)
        layout.addWidget(group)

        # Info section
        info = QLabel(
            "Select the input devices that should be remapped.\n"
            "Only selected devices will have their input captured and remapped."
        )
        info.setStyleSheet("color: #888888; padding: 8px;")
        layout.addWidget(info)

    def _setup_bindings_tab(self):
        """Set up the bindings editor tab."""
        layout = QVBoxLayout(self.bindings_tab)

        self.binding_editor = BindingEditorWidget()
        self.binding_editor.bindings_changed.connect(self._on_bindings_changed)
        layout.addWidget(self.binding_editor)

    def _setup_device_view_tab(self):
        """Set up the device view tab with visual device layout."""
        layout = QVBoxLayout(self.device_view_tab)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Top bar with device selector
        from PySide6.QtWidgets import QComboBox

        top_bar = QHBoxLayout()
        top_bar.setSpacing(8)

        top_bar.addWidget(QLabel("Device:"))
        self.device_view_combo = QComboBox()
        self.device_view_combo.setMinimumWidth(200)
        self.device_view_combo.currentIndexChanged.connect(self._on_device_view_changed)
        top_bar.addWidget(self.device_view_combo)

        self.test_buttons_btn = QPushButton("Test Buttons")
        self.test_buttons_btn.setMaximumWidth(100)
        self.test_buttons_btn.clicked.connect(self._test_button_highlighting)
        top_bar.addWidget(self.test_buttons_btn)
        top_bar.addStretch()

        layout.addLayout(top_bar)

        # Device visual widget
        self.device_visual = DeviceVisualWidget()
        self.device_visual.button_clicked.connect(self._on_device_button_clicked)
        self.device_visual.zone_clicked.connect(self._on_device_zone_clicked)
        layout.addWidget(self.device_visual, 1)

    def _on_device_view_changed(self, index: int):
        """Handle device selection in Device View tab."""
        if index < 0:
            return
        device = self.device_view_combo.itemData(index)
        if device:
            self._current_razer_device = device.serial
            self.device_visual.set_device(
                device.name,
                device.device_type,
                device.matrix_cols if hasattr(device, "matrix_cols") else None,
            )
            # Start monitoring input events for button highlighting
            self._start_input_monitoring(device.name)

    def _start_input_monitoring(self, device_name: str):
        """Find and monitor the evdev input device for button highlighting."""
        # Search device registry for matching device
        devices = self.device_registry.scan_devices()
        for dev_info in devices:
            # Match by name (partial match for Razer devices)
            if "razer" in dev_info.name.lower() and any(
                part.lower() in dev_info.name.lower() for part in device_name.split()
            ):
                self.input_monitor.start_monitoring(dev_info.event_path)
                return
        # Fallback: stop monitoring if no match
        self.input_monitor.stop_monitoring()

    def _test_button_highlighting(self):
        """Test button highlighting by cycling through all buttons."""
        layout = self.device_visual.get_layout()
        if not layout:
            self.statusbar.showMessage("No device layout loaded")
            return

        buttons = [b for b in layout.buttons if not b.is_zone]
        if not buttons:
            self.statusbar.showMessage("No buttons in layout")
            return

        self._test_index = 0
        self._test_buttons = buttons

        def highlight_next():
            if self._test_index < len(self._test_buttons):
                btn = self._test_buttons[self._test_index]
                self.device_visual.highlight_button(btn.id, 250)
                self.statusbar.showMessage(f"Testing: {btn.label}")
                self._test_index += 1
                QTimer.singleShot(300, highlight_next)
            else:
                self.statusbar.showMessage("Button test complete")

        highlight_next()

    def _on_device_button_clicked(self, button_id: str, input_code: str):
        """Handle button click on device visual."""
        self.statusbar.showMessage(f"Button clicked: {button_id} ({input_code})")

    def _on_physical_button_pressed(self, input_code: str):
        """Handle physical button press - highlight in device view."""
        self.device_visual.highlight_button_by_input_code(input_code)

    def _on_device_zone_clicked(self, zone_id: str):
        """Handle zone click on device visual - open color picker."""
        from PySide6.QtWidgets import QColorDialog

        current_device = getattr(self, "_current_razer_device", None)
        if not current_device:
            self.statusbar.showMessage("Select a device first")
            return

        color = QColorDialog.getColor()
        if color.isValid():
            # Set the zone color in the visual widget
            self.device_visual.set_zone_color(zone_id, color)
            # Try to apply to actual device
            try:
                self.openrazer.set_static_color(
                    current_device, color.red(), color.green(), color.blue()
                )
                self.statusbar.showMessage(f"Set {zone_id} to {color.name()}")
            except Exception as e:
                self.statusbar.showMessage(f"Failed to set color: {e}")

    def _setup_daemon_tab(self):
        """Set up the daemon control tab."""
        layout = QVBoxLayout(self.daemon_tab)

        # Status group
        status_group = QGroupBox("Daemon Status")
        status_layout = QGridLayout(status_group)

        status_layout.addWidget(QLabel("Service Status:"), 0, 0)
        self.daemon_status_label = QLabel("Unknown")
        status_layout.addWidget(self.daemon_status_label, 0, 1)

        status_layout.addWidget(QLabel("Active Profile:"), 1, 0)
        self.active_profile_label = QLabel("-")
        status_layout.addWidget(self.active_profile_label, 1, 1)

        layout.addWidget(status_group)

        # Control buttons
        ctrl_group = QGroupBox("Controls")
        ctrl_layout = QHBoxLayout(ctrl_group)

        self.start_daemon_btn = QPushButton(RazerIcons.get(RazerIcons.ACTION_PLAY), "Start")
        self.start_daemon_btn.clicked.connect(self._start_daemon)
        ctrl_layout.addWidget(self.start_daemon_btn)

        self.stop_daemon_btn = QPushButton(RazerIcons.get(RazerIcons.ACTION_STOP), "Stop")
        self.stop_daemon_btn.clicked.connect(self._stop_daemon)
        ctrl_layout.addWidget(self.stop_daemon_btn)

        self.restart_daemon_btn = QPushButton(RazerIcons.get(RazerIcons.ACTION_REFRESH), "Restart")
        self.restart_daemon_btn.clicked.connect(self._restart_daemon)
        ctrl_layout.addWidget(self.restart_daemon_btn)

        ctrl_layout.addStretch()
        layout.addWidget(ctrl_group)

        # Enable on login
        auto_group = QGroupBox("Autostart")
        auto_layout = QVBoxLayout(auto_group)

        self.autostart_check = QCheckBox("Start daemon on login")
        self.autostart_check.toggled.connect(self._toggle_autostart)
        auto_layout.addWidget(self.autostart_check)

        layout.addWidget(auto_group)
        layout.addStretch()

        # Update status
        self._update_daemon_status()

    def _setup_statusbar(self):
        """Set up the status bar."""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self.statusbar.showMessage("Ready")

    def _load_initial_data(self):
        """Load initial data."""
        # Refresh device list
        self.device_list.refresh()

        # Load profiles
        self.profile_panel.load_profiles(self.profile_loader)

        # Connect to OpenRazer
        if self.openrazer.connect():
            self.statusbar.showMessage("Connected to OpenRazer daemon", 3000)
            self.razer_tab.refresh_devices()
            self._populate_device_view_combo()
        else:
            self.statusbar.showMessage("OpenRazer daemon not available", 5000)

    def _populate_device_view_combo(self):
        """Populate the device view combo with discovered devices."""
        self.device_view_combo.clear()
        devices = self.openrazer.discover_devices()
        for device in devices:
            self.device_view_combo.addItem(device.name, device)
        if devices:
            self.device_view_combo.setCurrentIndex(0)

    def _on_profile_selected(self, profile_id: str):
        """Handle profile selection."""
        profile = self.profile_loader.load_profile(profile_id)
        if profile:
            self.current_profile = profile
            self._update_ui_for_profile(profile)
            self.statusbar.showMessage(f"Loaded profile: {profile.name}")

    def _update_ui_for_profile(self, profile: Profile):
        """Update UI elements for a loaded profile."""
        # Update device selection
        self.device_list.set_selected_devices(profile.input_devices)

        # Update binding editor
        self.binding_editor.load_profile(profile)

        # Update macro editor
        self.macro_editor.set_macros(profile.macros)

        # Update app matcher
        self.app_matcher.load_profile(profile)

        # Update zone editor if we have a device selected
        if self.zone_editor.current_device:
            device = self.zone_editor.current_device
            # Find device config in profile
            for dc in profile.devices:
                if dc.device_id == device.serial and dc.lighting and dc.lighting.matrix:
                    # Restore zone colors
                    zone_colors = {zc.zone_id: zc.color for zc in dc.lighting.matrix.zones}
                    self.zone_editor.set_zone_colors(zone_colors)
                    break

        # Update active profile label
        active_id = self.profile_loader.get_active_profile_id()
        if active_id == profile.id:
            self.active_profile_label.setText(f"{profile.name} (Active)")
        else:
            self.active_profile_label.setText(profile.name)

    def _on_profile_created(self, profile: Profile):
        """Handle new profile creation."""
        self.profile_loader.save_profile(profile)
        self.profile_panel.load_profiles(self.profile_loader)
        self.statusbar.showMessage(f"Created profile: {profile.name}")

    def _on_profile_deleted(self, profile_id: str):
        """Handle profile deletion."""
        self.profile_loader.delete_profile(profile_id)
        if self.current_profile and self.current_profile.id == profile_id:
            self.current_profile = None
            self.binding_editor.clear()
        self.statusbar.showMessage("Profile deleted")

    def _on_device_selection_changed(self, selected_ids: list[str]):
        """Handle device selection change."""
        pass  # Will be applied when user clicks Apply

    def _apply_device_selection(self):
        """Apply device selection to current profile."""
        if not self.current_profile:
            QMessageBox.warning(self, "No Profile", "Please select a profile first.")
            return

        selected = self.device_list.get_selected_devices()
        self.current_profile.input_devices = selected
        self.profile_loader.save_profile(self.current_profile)
        self.statusbar.showMessage("Device selection saved")

    def _on_bindings_changed(self):
        """Handle bindings change."""
        if self.current_profile:
            # Get updated layers from editor
            layers = self.binding_editor.get_layers()
            macros = self.binding_editor.get_macros()
            self.current_profile.layers = layers
            self.current_profile.macros = macros
            self.profile_loader.save_profile(self.current_profile)
            self.statusbar.showMessage("Bindings saved")

    def _on_macros_changed(self, macros: list):
        """Handle macros change."""
        if self.current_profile:
            self.current_profile.macros = macros
            self.profile_loader.save_profile(self.current_profile)
            self.statusbar.showMessage("Macros saved")

    def _on_app_patterns_changed(self):
        """Handle app pattern change."""
        if self.current_profile:
            self.profile_loader.save_profile(self.current_profile)
            self.statusbar.showMessage("App patterns saved")

    def _on_low_battery(self, device_name: str, level: int):
        """Handle low battery warning."""
        QMessageBox.warning(
            self,
            "Low Battery",
            f"{device_name} battery is low ({level}%).\n\nPlease charge your device.",
        )

    def _on_razer_device_selected(self, device):
        """Handle Razer device selection - update DPI, zone, binding, and visual editors."""
        self.dpi_editor.set_device(device)
        self.zone_editor.set_device(device)

        # Update device visual
        self._current_razer_device = device
        if device:
            self.device_visual.set_device(
                device.name,
                device.device_type,
                device.matrix_cols if hasattr(device, "matrix_cols") else None,
            )
            self.device_visual.clear_zone_colors()

            # Update binding editor's device visual too
            self.binding_editor.set_device(device.name, device.device_type)

    def _on_zone_config_changed(self):
        """Handle zone lighting config change."""
        if self.current_profile:
            # Save zone colors to profile
            from crates.profile_schema import MatrixLightingConfig, ZoneColor

            zone_colors = self.zone_editor.get_zone_colors()
            zones = [
                ZoneColor(zone_id=zid, color=c) for zid, c in zone_colors.items() if c != (0, 0, 0)
            ]

            # Find or create device config for current device
            device = self.zone_editor.current_device
            if device:
                # Get or create device config
                device_config = None
                for dc in self.current_profile.devices:
                    if dc.device_id == device.serial:
                        device_config = dc
                        break

                if device_config is None:
                    from crates.profile_schema import DeviceConfig, LightingConfig

                    device_config = DeviceConfig(device_id=device.serial)
                    self.current_profile.devices.append(device_config)

                # Update matrix config
                if device_config.lighting is None:
                    from crates.profile_schema import LightingConfig

                    device_config.lighting = LightingConfig()

                device_config.lighting.matrix = MatrixLightingConfig(enabled=True, zones=zones)

                self.profile_loader.save_profile(self.current_profile)
                self.statusbar.showMessage("Zone lighting saved")

    def _refresh_devices(self):
        """Refresh device list."""
        self.device_list.refresh()
        self.razer_tab.refresh_devices()
        self.battery_monitor.refresh_devices()
        self.statusbar.showMessage("Devices refreshed")

    def _refresh_device_status(self):
        """Periodic refresh of device status."""
        self._update_daemon_status()

    def _update_daemon_status(self):
        """Update daemon status display."""
        try:
            result = subprocess.run(
                ["systemctl", "--user", "is-active", "razer-remap-daemon"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            if result.returncode == 0:
                self.daemon_status_label.setText("Running")
                self.daemon_status_label.setStyleSheet("color: #2da05a;")
            else:
                self.daemon_status_label.setText("Stopped")
                self.daemon_status_label.setStyleSheet("color: #888888;")
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            self.daemon_status_label.setText("Unknown")
            self.daemon_status_label.setStyleSheet("color: #888888;")

        # Check autostart (block signals to avoid triggering toggle during init)
        service_path = Path.home() / ".config" / "systemd" / "user" / "razer-remap-daemon.service"
        self.autostart_check.blockSignals(True)
        self.autostart_check.setChecked(service_path.exists())
        self.autostart_check.blockSignals(False)

    def _start_daemon(self):
        """Start the remap daemon."""
        try:
            subprocess.run(
                ["systemctl", "--user", "start", "razer-remap-daemon"], check=True, timeout=5
            )
            self.statusbar.showMessage("Daemon started")
            self._update_daemon_status()
        except subprocess.CalledProcessError as e:
            QMessageBox.warning(self, "Error", f"Failed to start daemon: {e}")
        except FileNotFoundError:
            QMessageBox.warning(
                self, "Error", "systemctl not found. Please install the systemd service first."
            )

    def _stop_daemon(self):
        """Stop the remap daemon."""
        try:
            subprocess.run(
                ["systemctl", "--user", "stop", "razer-remap-daemon"], check=True, timeout=5
            )
            self.statusbar.showMessage("Daemon stopped")
            self._update_daemon_status()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to stop daemon: {e}")

    def _restart_daemon(self):
        """Restart the remap daemon."""
        try:
            subprocess.run(
                ["systemctl", "--user", "restart", "razer-remap-daemon"], check=True, timeout=5
            )
            self.statusbar.showMessage("Daemon restarted")
            self._update_daemon_status()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to restart daemon: {e}")

    def _toggle_autostart(self, enabled: bool):
        """Toggle daemon autostart on login."""
        if enabled:
            self._enable_autostart()
        else:
            self._disable_autostart()

    def _enable_autostart(self):
        """Enable daemon autostart."""
        try:
            subprocess.run(
                ["systemctl", "--user", "enable", "razer-remap-daemon"], check=True, timeout=5
            )
            self.statusbar.showMessage("Autostart enabled")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to enable autostart: {e}")

    def _disable_autostart(self):
        """Disable daemon autostart."""
        try:
            subprocess.run(
                ["systemctl", "--user", "disable", "razer-remap-daemon"], check=True, timeout=5
            )
            self.statusbar.showMessage("Autostart disabled")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to disable autostart: {e}")

    def closeEvent(self, event):
        """Handle window close."""
        self.refresh_timer.stop()
        self.input_monitor.stop_monitoring()
        event.accept()
