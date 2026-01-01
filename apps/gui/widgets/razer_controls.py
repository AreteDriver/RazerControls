"""Razer device controls widget for lighting and DPI."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from services.openrazer_bridge import OpenRazerBridge, RazerDevice


class ColorButton(QPushButton):
    """Button that displays and selects a color."""

    color_changed = Signal(tuple)  # Emits (r, g, b)

    def __init__(self, color: tuple = (68, 215, 44), parent=None):
        super().__init__(parent)
        self._color = color
        self._update_style()
        self.clicked.connect(self._pick_color)
        self.setMinimumSize(60, 30)

    def _update_style(self):
        """Update button style to show current color."""
        r, g, b = self._color
        # Choose text color based on brightness
        brightness = (r * 299 + g * 587 + b * 114) / 1000
        text_color = "black" if brightness > 128 else "white"
        self.setStyleSheet(
            f"background-color: rgb({r},{g},{b}); "
            f"color: {text_color}; "
            f"border: 1px solid #3d3d3d; "
            f"border-radius: 4px;"
        )
        self.setText(f"#{r:02x}{g:02x}{b:02x}")

    def _pick_color(self):
        """Open color picker dialog."""
        current = QColor(*self._color)
        color = QColorDialog.getColor(current, self, "Select Color")
        if color.isValid():
            self._color = (color.red(), color.green(), color.blue())
            self._update_style()
            self.color_changed.emit(self._color)

    def get_color(self) -> tuple:
        """Get current color as (r, g, b)."""
        return self._color

    def set_color(self, color: tuple):
        """Set the color."""
        self._color = color
        self._update_style()


class RazerControlsWidget(QWidget):
    """Widget for controlling Razer device lighting and DPI."""

    def __init__(self, bridge: OpenRazerBridge, parent=None):
        super().__init__(parent)
        self.bridge = bridge
        self.current_device: RazerDevice | None = None
        self._setup_ui()

    def _setup_ui(self):
        """Set up the widget UI."""
        layout = QVBoxLayout(self)

        # Device selector
        device_layout = QHBoxLayout()
        device_layout.addWidget(QLabel("Device:"))
        self.device_combo = QComboBox()
        self.device_combo.currentIndexChanged.connect(self._on_device_changed)
        device_layout.addWidget(self.device_combo, 1)

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_devices)
        device_layout.addWidget(self.refresh_btn)

        layout.addLayout(device_layout)

        # Lighting controls
        self.lighting_group = QGroupBox("Lighting")
        self._setup_lighting_controls()
        layout.addWidget(self.lighting_group)

        # DPI controls
        self.dpi_group = QGroupBox("DPI")
        self._setup_dpi_controls()
        layout.addWidget(self.dpi_group)

        # Device info
        self.info_group = QGroupBox("Device Info")
        self._setup_info_panel()
        layout.addWidget(self.info_group)

        layout.addStretch()

    def _setup_lighting_controls(self):
        """Set up lighting control widgets."""
        layout = QGridLayout(self.lighting_group)

        # Brightness
        layout.addWidget(QLabel("Brightness:"), 0, 0)
        self.brightness_slider = QSlider(Qt.Horizontal)
        self.brightness_slider.setRange(0, 100)
        self.brightness_slider.setValue(100)
        self.brightness_slider.valueChanged.connect(self._on_brightness_changed)
        layout.addWidget(self.brightness_slider, 0, 1)

        self.brightness_label = QLabel("100%")
        layout.addWidget(self.brightness_label, 0, 2)

        # Effect
        layout.addWidget(QLabel("Effect:"), 1, 0)
        self.effect_combo = QComboBox()
        self.effect_combo.addItems(["Static", "Breathing", "Spectrum", "Reactive", "Off"])
        self.effect_combo.currentTextChanged.connect(self._on_effect_changed)
        layout.addWidget(self.effect_combo, 1, 1, 1, 2)

        # Color
        layout.addWidget(QLabel("Color:"), 2, 0)
        self.color_btn = ColorButton((68, 215, 44))
        self.color_btn.color_changed.connect(self._on_color_changed)
        layout.addWidget(self.color_btn, 2, 1, 1, 2)

        # Apply button
        self.apply_lighting_btn = QPushButton("Apply Lighting")
        self.apply_lighting_btn.clicked.connect(self._apply_lighting)
        layout.addWidget(self.apply_lighting_btn, 3, 0, 1, 3)

    def _setup_dpi_controls(self):
        """Set up DPI control widgets."""
        layout = QGridLayout(self.dpi_group)

        # DPI X
        layout.addWidget(QLabel("DPI:"), 0, 0)
        self.dpi_spin = QSpinBox()
        self.dpi_spin.setRange(100, 20000)
        self.dpi_spin.setValue(1600)
        self.dpi_spin.setSingleStep(100)
        layout.addWidget(self.dpi_spin, 0, 1)

        # Quick presets
        layout.addWidget(QLabel("Presets:"), 1, 0)
        preset_layout = QHBoxLayout()
        for dpi in [800, 1600, 3200, 6400]:
            btn = QPushButton(str(dpi))
            btn.clicked.connect(lambda checked, d=dpi: self.dpi_spin.setValue(d))
            preset_layout.addWidget(btn)
        layout.addLayout(preset_layout, 1, 1)

        # Apply button
        self.apply_dpi_btn = QPushButton("Apply DPI")
        self.apply_dpi_btn.clicked.connect(self._apply_dpi)
        layout.addWidget(self.apply_dpi_btn, 2, 0, 1, 2)

    def _setup_info_panel(self):
        """Set up device info panel."""
        layout = QGridLayout(self.info_group)

        layout.addWidget(QLabel("Name:"), 0, 0)
        self.info_name = QLabel("-")
        layout.addWidget(self.info_name, 0, 1)

        layout.addWidget(QLabel("Type:"), 1, 0)
        self.info_type = QLabel("-")
        layout.addWidget(self.info_type, 1, 1)

        layout.addWidget(QLabel("Serial:"), 2, 0)
        self.info_serial = QLabel("-")
        layout.addWidget(self.info_serial, 2, 1)

        layout.addWidget(QLabel("Battery:"), 3, 0)
        self.info_battery = QLabel("-")
        layout.addWidget(self.info_battery, 3, 1)

    def refresh_devices(self):
        """Refresh the device list."""
        self.device_combo.clear()
        devices = self.bridge.discover_devices()

        if not devices:
            self.device_combo.addItem("No devices found")
            self._set_controls_enabled(False)
            return

        for device in devices:
            self.device_combo.addItem(device.name, device.serial)

        self._set_controls_enabled(True)

        if self.device_combo.count() > 0:
            self.device_combo.setCurrentIndex(0)

    def _on_device_changed(self, index: int):
        """Handle device selection change."""
        if index < 0:
            return

        serial = self.device_combo.currentData()
        if not serial:
            return

        device = self.bridge.get_device(serial)
        if device:
            self.current_device = device
            self._update_ui_for_device(device)

    def _update_ui_for_device(self, device: RazerDevice):
        """Update UI for selected device."""
        # Update info panel
        self.info_name.setText(device.name)
        self.info_type.setText(device.device_type)
        self.info_serial.setText(device.serial)

        if device.has_battery:
            self.info_battery.setText(f"{device.battery_level}%")
        else:
            self.info_battery.setText("N/A")

        # Update lighting controls
        self.lighting_group.setEnabled(device.has_lighting)
        if device.has_brightness:
            self.brightness_slider.setValue(device.brightness)

        # Update DPI controls
        self.dpi_group.setEnabled(device.has_dpi)
        if device.has_dpi:
            self.dpi_spin.setValue(device.dpi[0])

    def _set_controls_enabled(self, enabled: bool):
        """Enable or disable all controls."""
        self.lighting_group.setEnabled(enabled)
        self.dpi_group.setEnabled(enabled)

    def _on_brightness_changed(self, value: int):
        """Handle brightness slider change."""
        self.brightness_label.setText(f"{value}%")

    def _on_effect_changed(self, effect: str):
        """Handle effect selection change."""
        # Enable/disable color button based on effect
        needs_color = effect in ("Static", "Breathing", "Reactive")
        self.color_btn.setEnabled(needs_color)

    def _on_color_changed(self, color: tuple):
        """Handle color change."""
        pass  # Will be applied when user clicks Apply

    def _apply_lighting(self):
        """Apply current lighting settings."""
        if not self.current_device:
            return

        serial = self.current_device.serial

        # Apply brightness
        brightness = self.brightness_slider.value()
        self.bridge.set_brightness(serial, brightness)

        # Apply effect with color
        effect = self.effect_combo.currentText()
        r, g, b = self.color_btn.get_color()

        if effect == "Static":
            self.bridge.set_static_color(serial, r, g, b)
        elif effect == "Breathing":
            self.bridge.set_breathing_effect(serial, r, g, b)
        elif effect == "Spectrum":
            self.bridge.set_spectrum_effect(serial)
        elif effect == "Off":
            self.bridge.set_brightness(serial, 0)

    def _apply_dpi(self):
        """Apply current DPI setting."""
        if not self.current_device:
            return

        dpi = self.dpi_spin.value()
        self.bridge.set_dpi(self.current_device.serial, dpi)
