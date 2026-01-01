"""DPI Stage Editor widget for configuring mouse DPI stages."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from crates.profile_schema import DPIConfig
from services.openrazer_bridge import OpenRazerBridge, RazerDevice


class DPIStageItem(QFrame):
    """Visual representation of a single DPI stage."""

    changed = Signal()
    remove_requested = Signal()

    def __init__(self, dpi: int, max_dpi: int, index: int, parent=None):
        super().__init__(parent)
        self.index = index
        self.max_dpi = max_dpi
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self._setup_ui(dpi)

    def _setup_ui(self, dpi: int):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(10)

        # Stage number label
        self.stage_label = QLabel(f"Stage {self.index + 1}")
        self.stage_label.setMinimumWidth(60)
        self.stage_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.stage_label)

        # DPI slider
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(100, self.max_dpi)
        self.slider.setValue(dpi)
        self.slider.setSingleStep(100)
        self.slider.setPageStep(400)
        self.slider.valueChanged.connect(self._on_slider_changed)
        layout.addWidget(self.slider, 1)

        # DPI spin box
        self.spin = QSpinBox()
        self.spin.setRange(100, self.max_dpi)
        self.spin.setValue(dpi)
        self.spin.setSingleStep(100)
        self.spin.setMinimumWidth(70)
        self.spin.valueChanged.connect(self._on_spin_changed)
        layout.addWidget(self.spin)

        # Visual DPI bar (shows relative to max)
        self.dpi_bar = QFrame()
        self.dpi_bar.setMinimumHeight(8)
        self.dpi_bar.setMaximumHeight(8)
        self._update_bar_color(dpi)

        # Remove button
        self.remove_btn = QPushButton("×")
        self.remove_btn.setFixedSize(24, 24)
        self.remove_btn.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.remove_btn.clicked.connect(self.remove_requested.emit)
        layout.addWidget(self.remove_btn)

    def _on_slider_changed(self, value: int):
        """Handle slider value change."""
        # Round to nearest 100
        rounded = round(value / 100) * 100
        if rounded != value:
            self.slider.blockSignals(True)
            self.slider.setValue(rounded)
            self.slider.blockSignals(False)
            value = rounded

        self.spin.blockSignals(True)
        self.spin.setValue(value)
        self.spin.blockSignals(False)
        self._update_bar_color(value)
        self.changed.emit()

    def _on_spin_changed(self, value: int):
        """Handle spin box value change."""
        self.slider.blockSignals(True)
        self.slider.setValue(value)
        self.slider.blockSignals(False)
        self._update_bar_color(value)
        self.changed.emit()

    def _update_bar_color(self, dpi: int):
        """Update bar color based on DPI level."""
        ratio = dpi / self.max_dpi
        if ratio < 0.25:
            color = "#3498db"  # Blue - low
        elif ratio < 0.5:
            color = "#2ecc71"  # Green - medium
        elif ratio < 0.75:
            color = "#f1c40f"  # Yellow - high
        else:
            color = "#e74c3c"  # Red - very high

        self.dpi_bar.setStyleSheet(f"background-color: {color}; border-radius: 4px;")

    def get_dpi(self) -> int:
        """Get current DPI value."""
        return self.spin.value()

    def set_active(self, active: bool):
        """Set whether this stage is the active one."""
        if active:
            self.setStyleSheet(
                "QFrame { background-color: #e8f4f8; "
                "border: 2px solid #3498db; border-radius: 4px; }"
            )
            self.stage_label.setText(f"Stage {self.index + 1} ●")
        else:
            self.setStyleSheet("QFrame { border-radius: 4px; }")
            self.stage_label.setText(f"Stage {self.index + 1}")


class DPIStageEditor(QWidget):
    """Widget for editing DPI stages configuration."""

    stages_changed = Signal(list)  # Emitted when stages are modified
    active_stage_changed = Signal(int)  # Emitted when active stage changes

    MAX_STAGES = 5
    PRESET_DPIS = [400, 800, 1200, 1600, 2400, 3200, 4800, 6400]

    def __init__(self, bridge: OpenRazerBridge, parent=None):
        super().__init__(parent)
        self.bridge = bridge
        self.current_device: RazerDevice | None = None
        self._stage_items: list[DPIStageItem] = []
        self._active_stage = 0

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Header
        header_layout = QHBoxLayout()

        title = QLabel("DPI Stages")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        # Device info
        self.device_label = QLabel("No device selected")
        self.device_label.setStyleSheet("color: #888888;")
        header_layout.addWidget(self.device_label)

        layout.addLayout(header_layout)

        # Stages container
        self.stages_group = QGroupBox("Configure Stages")
        self.stages_layout = QVBoxLayout(self.stages_group)
        self.stages_layout.setSpacing(8)

        # Placeholder
        self.no_device_label = QLabel("Select a device with DPI support to configure stages.")
        self.no_device_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.no_device_label.setStyleSheet("color: #888888; padding: 40px;")
        self.stages_layout.addWidget(self.no_device_label)

        layout.addWidget(self.stages_group)

        # Control buttons
        btn_layout = QHBoxLayout()

        self.add_btn = QPushButton("Add Stage")
        self.add_btn.clicked.connect(self._add_stage)
        self.add_btn.setEnabled(False)
        btn_layout.addWidget(self.add_btn)

        btn_layout.addStretch()

        # Preset buttons
        btn_layout.addWidget(QLabel("Presets:"))
        for name, stages in [
            ("Gaming", [400, 800, 1600]),
            ("Productivity", [800, 1600, 3200]),
            ("High Precision", [400, 800, 1200, 1600, 2400]),
        ]:
            btn = QPushButton(name)
            btn.clicked.connect(lambda checked, s=stages: self._apply_preset(s))
            btn_layout.addWidget(btn)

        layout.addLayout(btn_layout)

        # Apply button
        apply_layout = QHBoxLayout()
        apply_layout.addStretch()

        self.apply_btn = QPushButton("Apply to Device")
        self.apply_btn.setEnabled(False)
        self.apply_btn.clicked.connect(self._apply_to_device)
        self.apply_btn.setStyleSheet("font-weight: bold; padding: 8px 16px;")
        apply_layout.addWidget(self.apply_btn)

        layout.addLayout(apply_layout)

        # Active stage selector
        active_group = QGroupBox("Active Stage")
        active_layout = QHBoxLayout(active_group)

        self.stage_buttons: list[QPushButton] = []
        for i in range(self.MAX_STAGES):
            btn = QPushButton(str(i + 1))
            btn.setFixedSize(40, 40)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, idx=i: self._set_active_stage(idx))
            btn.setVisible(False)
            self.stage_buttons.append(btn)
            active_layout.addWidget(btn)

        active_layout.addStretch()

        self.current_dpi_label = QLabel("Current: ---")
        self.current_dpi_label.setStyleSheet("font-size: 14px;")
        active_layout.addWidget(self.current_dpi_label)

        layout.addWidget(active_group)

        layout.addStretch()

    def set_device(self, device: RazerDevice | None):
        """Set the current device to configure."""
        self.current_device = device

        # Clear existing stages
        for item in self._stage_items:
            item.deleteLater()
        self._stage_items.clear()

        if device and device.has_dpi:
            self.no_device_label.setVisible(False)
            self.device_label.setText(f"{device.name} (max: {device.max_dpi} DPI)")
            self.add_btn.setEnabled(True)
            self.apply_btn.setEnabled(True)

            # Create default stages if none exist
            default_stages = [800, 1600, 3200]
            for dpi in default_stages:
                if dpi <= device.max_dpi:
                    self._create_stage_item(dpi)

            self._update_stage_buttons()
            self._set_active_stage(0)

            # Set current DPI
            self.current_dpi_label.setText(f"Current: {device.dpi[0]} DPI")
        else:
            self.no_device_label.setVisible(True)
            self.device_label.setText("No device selected")
            self.add_btn.setEnabled(False)
            self.apply_btn.setEnabled(False)
            self.current_dpi_label.setText("Current: ---")

            for btn in self.stage_buttons:
                btn.setVisible(False)

    def set_config(self, config: DPIConfig):
        """Load DPI config into editor."""
        if not self.current_device:
            return

        # Clear existing
        for item in self._stage_items:
            item.deleteLater()
        self._stage_items.clear()

        # Create stages from config
        for dpi in config.stages:
            if dpi <= self.current_device.max_dpi:
                self._create_stage_item(dpi)

        self._update_stage_buttons()
        self._set_active_stage(config.active_stage)

    def get_config(self) -> DPIConfig:
        """Get current DPI config."""
        stages = [item.get_dpi() for item in self._stage_items]
        return DPIConfig(stages=stages, active_stage=self._active_stage)

    def _create_stage_item(self, dpi: int) -> DPIStageItem | None:
        """Create a new stage item."""
        if not self.current_device:
            return None

        index = len(self._stage_items)
        item = DPIStageItem(dpi, self.current_device.max_dpi, index)
        item.changed.connect(self._on_stage_changed)
        item.remove_requested.connect(lambda: self._remove_stage(item))

        self._stage_items.append(item)
        self.stages_layout.insertWidget(self.stages_layout.count() - 1, item)

        return item

    def _add_stage(self):
        """Add a new DPI stage."""
        if len(self._stage_items) >= self.MAX_STAGES:
            QMessageBox.information(
                self, "Maximum Stages", f"Maximum of {self.MAX_STAGES} stages allowed."
            )
            return

        if not self.current_device:
            return

        # Calculate a reasonable default DPI
        if self._stage_items:
            last_dpi = self._stage_items[-1].get_dpi()
            new_dpi = min(last_dpi + 800, self.current_device.max_dpi)
        else:
            new_dpi = 800

        self._create_stage_item(new_dpi)
        self._update_stage_buttons()
        self._on_stage_changed()

    def _remove_stage(self, item: DPIStageItem):
        """Remove a DPI stage."""
        if len(self._stage_items) <= 1:
            QMessageBox.warning(self, "Cannot Remove", "At least one DPI stage is required.")
            return

        self._stage_items.remove(item)
        item.deleteLater()

        # Update indices
        for i, stage in enumerate(self._stage_items):
            stage.index = i
            stage.stage_label.setText(f"Stage {i + 1}")

        # Adjust active stage if needed
        if self._active_stage >= len(self._stage_items):
            self._set_active_stage(len(self._stage_items) - 1)

        self._update_stage_buttons()
        self._on_stage_changed()

    def _update_stage_buttons(self):
        """Update stage selector buttons."""
        for i, btn in enumerate(self.stage_buttons):
            if i < len(self._stage_items):
                btn.setVisible(True)
                btn.setChecked(i == self._active_stage)
            else:
                btn.setVisible(False)

    def _set_active_stage(self, index: int):
        """Set the active DPI stage."""
        if index >= len(self._stage_items):
            return

        self._active_stage = index

        # Update visual indicators
        for i, item in enumerate(self._stage_items):
            item.set_active(i == index)

        for i, btn in enumerate(self.stage_buttons):
            btn.setChecked(i == index)

        # Update current DPI display
        if self._stage_items:
            dpi = self._stage_items[index].get_dpi()
            self.current_dpi_label.setText(f"Current: {dpi} DPI")

        self.active_stage_changed.emit(index)

    def _on_stage_changed(self):
        """Handle stage value change."""
        stages = [item.get_dpi() for item in self._stage_items]
        self.stages_changed.emit(stages)

        # Update current DPI display
        if self._stage_items and self._active_stage < len(self._stage_items):
            dpi = self._stage_items[self._active_stage].get_dpi()
            self.current_dpi_label.setText(f"Current: {dpi} DPI")

    def _apply_preset(self, stages: list[int]):
        """Apply a preset DPI configuration."""
        if not self.current_device:
            return

        # Clear existing
        for item in self._stage_items:
            item.deleteLater()
        self._stage_items.clear()

        # Create stages
        for dpi in stages:
            if dpi <= self.current_device.max_dpi:
                self._create_stage_item(dpi)

        self._update_stage_buttons()
        self._set_active_stage(0)
        self._on_stage_changed()

    def _apply_to_device(self):
        """Apply current active stage DPI to device."""
        if not self.current_device or not self._stage_items:
            return

        dpi = self._stage_items[self._active_stage].get_dpi()
        if self.bridge.set_dpi(self.current_device.serial, dpi):
            self.current_device.dpi = (dpi, dpi)
            QMessageBox.information(
                self, "DPI Applied", f"Set DPI to {dpi} on {self.current_device.name}"
            )
        else:
            QMessageBox.warning(self, "Error", "Failed to apply DPI to device.")
