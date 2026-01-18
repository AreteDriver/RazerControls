"""First-run setup wizard for Razer Control Center.

Guides new users through:
1. Welcome and feature overview
2. Device detection and selection
3. Profile creation
4. Daemon setup (autostart, start now)
"""

import subprocess
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from crates.device_registry import DeviceRegistry
from crates.profile_schema import Layer, Profile, ProfileLoader


class SetupWizard(QDialog):
    """First-run setup wizard."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Razer Control Center - Setup")
        self.setMinimumSize(600, 500)
        self.setModal(True)

        # State
        self.selected_devices: list[str] = []
        self.profile_name = "Default"
        self.profile_description = ""
        self.enable_autostart = True
        self.start_daemon_now = True

        # Services
        self.device_registry = DeviceRegistry()
        self.profile_loader = ProfileLoader()

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the wizard UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)

        # Page stack
        self.pages = QStackedWidget()
        self.pages.addWidget(self._create_welcome_page())
        self.pages.addWidget(self._create_device_page())
        self.pages.addWidget(self._create_profile_page())
        self.pages.addWidget(self._create_daemon_page())
        layout.addWidget(self.pages)

        # Page indicator
        self.page_indicator = QLabel()
        self.page_indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._update_page_indicator()
        layout.addWidget(self.page_indicator)

        # Navigation buttons
        nav_layout = QHBoxLayout()

        self.back_btn = QPushButton("Back")
        self.back_btn.clicked.connect(self._go_back)
        nav_layout.addWidget(self.back_btn)

        nav_layout.addStretch()

        self.next_btn = QPushButton("Next")
        self.next_btn.clicked.connect(self._go_next)
        self.next_btn.setDefault(True)
        self.next_btn.setStyleSheet("QPushButton { background-color: #2da05a; font-weight: bold; }")
        nav_layout.addWidget(self.next_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        nav_layout.addWidget(self.cancel_btn)

        layout.addLayout(nav_layout)

        self._update_buttons()

    def _create_welcome_page(self) -> QWidget:
        """Create the welcome page."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(20)

        # Title
        title = QLabel("Welcome to Razer Control Center")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Description
        desc = QLabel(
            "Configure your Razer devices on Linux with:\n\n"
            "  - Button remapping and key bindings\n"
            "  - Macro recording and playback\n"
            "  - RGB lighting and DPI control\n"
            "  - Multiple profiles with app-based switching\n\n"
            "This wizard will help you set up your first profile."
        )
        desc.setStyleSheet("font-size: 14px;")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc)

        layout.addStretch()

        return page

    def _create_device_page(self) -> QWidget:
        """Create the device detection page."""
        page = QWidget()
        layout = QVBoxLayout(page)

        # Title
        title = QLabel("Select Your Devices")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        desc = QLabel("Select the Razer devices you want to configure:")
        layout.addWidget(desc)

        # Device list
        self.device_list = QListWidget()
        self.device_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        layout.addWidget(self.device_list)

        # Rescan button
        btn_layout = QHBoxLayout()
        rescan_btn = QPushButton("Rescan Devices")
        rescan_btn.clicked.connect(self._scan_devices)
        btn_layout.addWidget(rescan_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Troubleshooting section
        self.trouble_group = QGroupBox("Troubleshooting")
        trouble_layout = QVBoxLayout(self.trouble_group)

        self.trouble_label = QLabel()
        self.trouble_label.setWordWrap(True)
        trouble_layout.addWidget(self.trouble_label)

        layout.addWidget(self.trouble_group)
        self.trouble_group.hide()

        # Initial scan
        self._scan_devices()

        return page

    def _create_profile_page(self) -> QWidget:
        """Create the profile creation page."""
        page = QWidget()
        layout = QVBoxLayout(page)

        # Title
        title = QLabel("Create Your First Profile")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        # Form
        form_group = QGroupBox("Profile Settings")
        form_layout = QFormLayout(form_group)

        self.name_input = QLineEdit("Default")
        self.name_input.textChanged.connect(self._on_name_changed)
        form_layout.addRow("Profile Name:", self.name_input)

        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText("Optional description")
        form_layout.addRow("Description:", self.desc_input)

        self.default_check = QCheckBox("Set as default profile")
        self.default_check.setChecked(True)
        form_layout.addRow("", self.default_check)

        layout.addWidget(form_group)

        # Selected devices summary
        self.devices_summary = QGroupBox("Selected Devices")
        self.devices_summary_layout = QVBoxLayout(self.devices_summary)
        self.devices_summary_label = QLabel("No devices selected")
        self.devices_summary_layout.addWidget(self.devices_summary_label)
        layout.addWidget(self.devices_summary)

        layout.addStretch()

        return page

    def _create_daemon_page(self) -> QWidget:
        """Create the daemon setup page."""
        page = QWidget()
        layout = QVBoxLayout(page)

        # Title
        title = QLabel("Daemon Setup")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        desc = QLabel(
            "The remap daemon runs in the background to handle\nyour key bindings and macros."
        )
        layout.addWidget(desc)

        # Options
        options_group = QGroupBox("Startup Options")
        options_layout = QVBoxLayout(options_group)

        self.autostart_check = QCheckBox("Start daemon automatically on login")
        self.autostart_check.setChecked(True)
        options_layout.addWidget(self.autostart_check)

        self.start_now_check = QCheckBox("Start daemon now")
        self.start_now_check.setChecked(True)
        options_layout.addWidget(self.start_now_check)

        layout.addWidget(options_group)

        # Summary
        summary_group = QGroupBox("Setup Summary")
        self.summary_layout = QVBoxLayout(summary_group)
        self.summary_label = QLabel()
        self.summary_layout.addWidget(self.summary_label)
        layout.addWidget(summary_group)

        layout.addStretch()

        return page

    def _scan_devices(self) -> None:
        """Scan for Razer devices."""
        self.device_list.clear()

        devices = self.device_registry.get_razer_devices()

        if not devices:
            # Show troubleshooting
            self.trouble_group.show()
            trouble_text = self._get_troubleshooting_text()
            self.trouble_label.setText(trouble_text)
            return

        self.trouble_group.hide()

        for device in devices:
            item = QListWidgetItem()
            checkbox = QCheckBox(f"{device.name}")
            checkbox.setProperty("stable_id", device.stable_id)

            # Pre-select mice
            if device.is_mouse:
                checkbox.setChecked(True)

            checkbox.stateChanged.connect(self._on_device_toggled)

            self.device_list.addItem(item)
            self.device_list.setItemWidget(item, checkbox)

        self._update_selected_devices()

    def _get_troubleshooting_text(self) -> str:
        """Get troubleshooting text based on system state."""
        issues = []

        # Check uinput
        try:
            Path("/dev/uinput").stat()
        except (FileNotFoundError, PermissionError):
            issues.append("- uinput module not loaded. Run: sudo modprobe uinput")

        # Check input group
        try:
            result = subprocess.run(["groups"], capture_output=True, text=True, timeout=2)
            if "input" not in result.stdout:
                issues.append("- User not in 'input' group. Run: sudo usermod -aG input $USER")
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass

        # Check OpenRazer
        try:
            result = subprocess.run(
                ["systemctl", "is-active", "openrazer-daemon"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            if result.stdout.strip() != "active":
                issues.append(
                    "- OpenRazer daemon not running. Run: sudo systemctl start openrazer-daemon"
                )
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            issues.append("- Could not check OpenRazer daemon status")

        if not issues:
            return (
                "No Razer devices found.\n\n"
                "Make sure your device is connected via USB\n"
                "and is supported by OpenRazer."
            )

        return "No devices found. Possible issues:\n\n" + "\n".join(issues)

    def _on_device_toggled(self) -> None:
        """Handle device checkbox toggle."""
        self._update_selected_devices()

    def _update_selected_devices(self) -> None:
        """Update the list of selected devices."""
        self.selected_devices = []

        for i in range(self.device_list.count()):
            item = self.device_list.item(i)
            checkbox = self.device_list.itemWidget(item)
            if checkbox and checkbox.isChecked():
                stable_id = checkbox.property("stable_id")
                if stable_id:
                    self.selected_devices.append(stable_id)

    def _on_name_changed(self, text: str) -> None:
        """Handle profile name change."""
        self.profile_name = text.strip() or "Default"

    def _update_page_indicator(self) -> None:
        """Update the page indicator dots."""
        current = self.pages.currentIndex()
        total = self.pages.count()

        dots = []
        for i in range(total):
            if i == current:
                dots.append("\u25cf")  # Filled circle
            else:
                dots.append("\u25cb")  # Empty circle

        self.page_indicator.setText("  ".join(dots))

    def _update_buttons(self) -> None:
        """Update navigation button states."""
        current = self.pages.currentIndex()
        total = self.pages.count()

        self.back_btn.setEnabled(current > 0)

        if current == total - 1:
            self.next_btn.setText("Finish")
        else:
            self.next_btn.setText("Next")

    def _go_back(self) -> None:
        """Go to previous page."""
        current = self.pages.currentIndex()
        if current > 0:
            self.pages.setCurrentIndex(current - 1)
            self._update_page_indicator()
            self._update_buttons()

    def _go_next(self) -> None:
        """Go to next page or finish."""
        current = self.pages.currentIndex()
        total = self.pages.count()

        if current == total - 1:
            # Finish
            self._finish_setup()
        else:
            # Prepare next page
            if current == 1:  # Leaving device page
                self._prepare_profile_page()
            elif current == 2:  # Leaving profile page
                self._prepare_daemon_page()

            self.pages.setCurrentIndex(current + 1)
            self._update_page_indicator()
            self._update_buttons()

    def _prepare_profile_page(self) -> None:
        """Prepare the profile page with selected devices."""
        if self.selected_devices:
            device_names = []
            for sid in self.selected_devices:
                # Extract friendly name from stable_id
                name = sid.replace("usb-", "").replace("-event-mouse", "")
                name = name.replace("-event-kbd", "").replace("_", " ")
                device_names.append(f"  - {name}")
            self.devices_summary_label.setText("\n".join(device_names))
        else:
            self.devices_summary_label.setText("No devices selected")

    def _prepare_daemon_page(self) -> None:
        """Prepare the daemon page with summary."""
        summary = []
        summary.append(f"Profile: {self.name_input.text() or 'Default'}")

        if self.desc_input.text():
            summary.append(f"Description: {self.desc_input.text()}")

        summary.append(f"Devices: {len(self.selected_devices)} selected")

        if self.default_check.isChecked():
            summary.append("Will be set as default profile")

        self.summary_label.setText("\n".join(summary))

    def _finish_setup(self) -> None:
        """Complete the setup wizard."""
        # Create profile
        profile_id = self.name_input.text().lower().replace(" ", "_")
        profile_id = "".join(c for c in profile_id if c.isalnum() or c == "_")
        profile_id = profile_id or "default"

        profile = Profile(
            id=profile_id,
            name=self.name_input.text() or "Default",
            description=self.desc_input.text(),
            input_devices=self.selected_devices,
            layers=[
                Layer(
                    id="base",
                    name="Base Layer",
                    bindings=[],
                    hold_modifier_input_code=None,
                )
            ],
            is_default=self.default_check.isChecked(),
        )

        self.profile_loader.save_profile(profile)
        self.profile_loader.set_active_profile(profile.id)

        # Daemon setup
        if self.autostart_check.isChecked():
            try:
                subprocess.run(
                    ["systemctl", "--user", "enable", "razer-remap-daemon"],
                    check=False,
                    timeout=5,
                )
            except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                pass

        if self.start_now_check.isChecked():
            try:
                subprocess.run(
                    ["systemctl", "--user", "start", "razer-remap-daemon"],
                    check=False,
                    timeout=5,
                )
            except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                pass

        self.accept()
