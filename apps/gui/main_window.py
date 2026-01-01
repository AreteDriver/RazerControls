"""Main application window."""

import subprocess
from pathlib import Path

from PySide6.QtCore import QTimer
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

from .widgets.app_matcher import AppMatcherWidget
from .widgets.binding_editor import BindingEditorWidget
from .widgets.device_list import DeviceListWidget
from .widgets.profile_panel import ProfilePanel
from .widgets.razer_controls import RazerControlsWidget


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

        # Set up UI
        self._setup_ui()
        self._setup_statusbar()

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

        # Devices tab
        self.devices_tab = QWidget()
        self._setup_devices_tab()
        self.tabs.addTab(self.devices_tab, "Devices")

        # Bindings tab
        self.bindings_tab = QWidget()
        self._setup_bindings_tab()
        self.tabs.addTab(self.bindings_tab, "Bindings")

        # App Switching tab
        self.app_matcher = AppMatcherWidget()
        self.app_matcher.patterns_changed.connect(self._on_app_patterns_changed)
        self.tabs.addTab(self.app_matcher, "App Switching")

        # Razer tab (OpenRazer controls)
        self.razer_tab = RazerControlsWidget(self.openrazer)
        self.tabs.addTab(self.razer_tab, "Lighting & DPI")

        # Daemon tab
        self.daemon_tab = QWidget()
        self._setup_daemon_tab()
        self.tabs.addTab(self.daemon_tab, "Daemon")

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
        self.refresh_devices_btn = QPushButton("Refresh Devices")
        self.refresh_devices_btn.clicked.connect(self._refresh_devices)
        btn_layout.addWidget(self.refresh_devices_btn)

        self.apply_devices_btn = QPushButton("Apply to Profile")
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

        self.start_daemon_btn = QPushButton("Start Daemon")
        self.start_daemon_btn.clicked.connect(self._start_daemon)
        ctrl_layout.addWidget(self.start_daemon_btn)

        self.stop_daemon_btn = QPushButton("Stop Daemon")
        self.stop_daemon_btn.clicked.connect(self._stop_daemon)
        ctrl_layout.addWidget(self.stop_daemon_btn)

        self.restart_daemon_btn = QPushButton("Restart Daemon")
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
        else:
            self.statusbar.showMessage("OpenRazer daemon not available", 5000)

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

        # Update app matcher
        self.app_matcher.load_profile(profile)

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

    def _on_app_patterns_changed(self):
        """Handle app pattern change."""
        if self.current_profile:
            self.profile_loader.save_profile(self.current_profile)
            self.statusbar.showMessage("App patterns saved")

    def _refresh_devices(self):
        """Refresh device list."""
        self.device_list.refresh()
        self.razer_tab.refresh_devices()
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
        except Exception:
            self.daemon_status_label.setText("Unknown")
            self.daemon_status_label.setStyleSheet("color: #888888;")

        # Check autostart
        service_path = Path.home() / ".config" / "systemd" / "user" / "razer-remap-daemon.service"
        self.autostart_check.setChecked(service_path.exists())

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
        event.accept()
