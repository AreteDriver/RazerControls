"""Battery monitor widget for wireless Razer devices."""

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from services.openrazer_bridge import OpenRazerBridge, RazerDevice


class BatteryDeviceCard(QFrame):
    """Card displaying battery status for a single device."""

    LOW_BATTERY_THRESHOLD = 20
    CRITICAL_BATTERY_THRESHOLD = 10

    def __init__(self, device: RazerDevice, parent=None):
        super().__init__(parent)
        self.device = device
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Device name
        self.name_label = QLabel(self.device.name)
        self.name_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(self.name_label)

        # Device type
        self.type_label = QLabel(self.device.device_type)
        self.type_label.setStyleSheet("color: #888888; font-size: 11px;")
        layout.addWidget(self.type_label)

        # Battery bar and percentage
        bar_layout = QHBoxLayout()
        bar_layout.setSpacing(10)

        self.battery_bar = QProgressBar()
        self.battery_bar.setRange(0, 100)
        self.battery_bar.setTextVisible(False)
        self.battery_bar.setMinimumWidth(150)
        self.battery_bar.setMaximumHeight(20)
        bar_layout.addWidget(self.battery_bar, 1)

        self.percent_label = QLabel("---%")
        self.percent_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.percent_label.setMinimumWidth(50)
        bar_layout.addWidget(self.percent_label)

        layout.addLayout(bar_layout)

        # Status row (charging, time estimate)
        status_layout = QHBoxLayout()

        self.status_label = QLabel()
        self.status_label.setStyleSheet("font-size: 12px;")
        status_layout.addWidget(self.status_label)

        status_layout.addStretch()

        layout.addLayout(status_layout)

        # Initial update
        self.update_battery()

    def update_battery(self):
        """Update battery display."""
        level = self.device.battery_level
        is_charging = self.device.is_charging

        # Update progress bar
        if level >= 0:
            self.battery_bar.setValue(level)
            self.percent_label.setText(f"{level}%")

            # Color coding based on level
            if is_charging:
                color = "#3498db"  # Blue for charging
                self.status_label.setText("⚡ Charging")
                self.status_label.setStyleSheet("color: #3498db; font-size: 12px;")
            elif level <= self.CRITICAL_BATTERY_THRESHOLD:
                color = "#e74c3c"  # Red for critical
                self.status_label.setText("⚠ Critical - Charge Now!")
                self.status_label.setStyleSheet(
                    "color: #e74c3c; font-size: 12px; font-weight: bold;"
                )
            elif level <= self.LOW_BATTERY_THRESHOLD:
                color = "#f39c12"  # Orange for low
                self.status_label.setText("⚠ Low Battery")
                self.status_label.setStyleSheet("color: #f39c12; font-size: 12px;")
            elif level >= 80:
                color = "#27ae60"  # Green for good
                self.status_label.setText("✓ Good")
                self.status_label.setStyleSheet("color: #27ae60; font-size: 12px;")
            else:
                color = "#f1c40f"  # Yellow for medium
                self.status_label.setText("Normal")
                self.status_label.setStyleSheet("color: #888888; font-size: 12px;")

            # Apply color to progress bar
            self.battery_bar.setStyleSheet(
                f"""
                QProgressBar {{
                    border: 1px solid #cccccc;
                    border-radius: 5px;
                    background-color: #f0f0f0;
                }}
                QProgressBar::chunk {{
                    background-color: {color};
                    border-radius: 4px;
                }}
                """
            )
        else:
            self.battery_bar.setValue(0)
            self.percent_label.setText("N/A")
            self.status_label.setText("Unable to read battery")
            self.status_label.setStyleSheet("color: #888888; font-size: 12px;")


class BatteryMonitorWidget(QWidget):
    """Widget for monitoring battery status of wireless Razer devices."""

    low_battery_warning = Signal(str, int)  # (device_name, level)

    def __init__(self, bridge: OpenRazerBridge, parent=None):
        super().__init__(parent)
        self.bridge = bridge
        self._device_cards: dict[str, BatteryDeviceCard] = {}
        self._warned_devices: set[str] = set()  # Track devices we've warned about

        self._setup_ui()

        # Auto-refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_batteries)
        self.refresh_timer.start(30000)  # Every 30 seconds

        # Initial refresh
        self.refresh_devices()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Header
        header_layout = QHBoxLayout()

        title = QLabel("Battery Status")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        # Refresh interval selector
        header_layout.addWidget(QLabel("Refresh:"))
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(10, 300)
        self.interval_spin.setValue(30)
        self.interval_spin.setSuffix(" sec")
        self.interval_spin.valueChanged.connect(self._on_interval_changed)
        header_layout.addWidget(self.interval_spin)

        layout.addLayout(header_layout)

        # Devices container
        self.devices_group = QGroupBox("Wireless Devices")
        self.devices_layout = QVBoxLayout(self.devices_group)
        self.devices_layout.setSpacing(10)

        # Placeholder for no devices
        self.no_devices_label = QLabel(
            "No wireless devices with battery found.\n\n"
            "Connect a wireless Razer device to see battery status."
        )
        self.no_devices_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.no_devices_label.setStyleSheet("color: #888888; padding: 40px;")
        self.devices_layout.addWidget(self.no_devices_label)

        layout.addWidget(self.devices_group)

        # Status bar
        self.status_label = QLabel("Last updated: Never")
        self.status_label.setStyleSheet("color: #888888; font-size: 11px;")
        layout.addWidget(self.status_label)

        layout.addStretch()

    def _on_interval_changed(self, value: int):
        """Handle refresh interval change."""
        self.refresh_timer.setInterval(value * 1000)

    def refresh_devices(self):
        """Refresh device list and rebuild cards."""
        # Clear existing cards
        for card in self._device_cards.values():
            card.deleteLater()
        self._device_cards.clear()

        # Get devices with battery
        devices = self.bridge.discover_devices()
        battery_devices = [d for d in devices if d.has_battery]

        # Show/hide placeholder
        self.no_devices_label.setVisible(len(battery_devices) == 0)

        # Create cards for each device
        for device in battery_devices:
            card = BatteryDeviceCard(device)
            self._device_cards[device.serial] = card
            self.devices_layout.insertWidget(
                self.devices_layout.count() - 1, card
            )  # Insert before stretch

        self.refresh_batteries()

    def refresh_batteries(self):
        """Refresh battery levels for all devices."""
        from datetime import datetime

        for serial, card in self._device_cards.items():
            # Get fresh battery data
            battery_info = self.bridge.get_battery(serial)
            if battery_info:
                card.device.battery_level = battery_info["level"]
                card.device.is_charging = battery_info["charging"]
                card.update_battery()

                # Check for low battery warning
                level = battery_info["level"]
                if (
                    level <= BatteryDeviceCard.LOW_BATTERY_THRESHOLD
                    and not battery_info["charging"]
                    and serial not in self._warned_devices
                ):
                    self._warned_devices.add(serial)
                    self.low_battery_warning.emit(card.device.name, level)

                # Reset warning if battery is charged
                if level > BatteryDeviceCard.LOW_BATTERY_THRESHOLD + 10:
                    self._warned_devices.discard(serial)

        # Update status
        now = datetime.now().strftime("%H:%M:%S")
        self.status_label.setText(f"Last updated: {now}")

    def showEvent(self, event):
        """Refresh when widget becomes visible."""
        super().showEvent(event)
        self.refresh_batteries()

    def hideEvent(self, event):
        """Called when widget is hidden."""
        super().hideEvent(event)
