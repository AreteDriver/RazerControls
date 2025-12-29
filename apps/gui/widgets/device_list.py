"""Device list widget for selecting input devices."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QListWidget, QListWidgetItem, QLabel
)
from PySide6.QtCore import Qt, Signal

from crates.device_registry import DeviceRegistry


class DeviceListWidget(QWidget):
    """Widget for displaying and selecting input devices."""

    selection_changed = Signal(list)  # Emits list of selected device IDs

    def __init__(self, registry: DeviceRegistry, parent=None):
        super().__init__(parent)
        self.registry = registry
        self._setup_ui()

    def _setup_ui(self):
        """Set up the widget UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Info label
        self.info_label = QLabel("Select devices to remap:")
        layout.addWidget(self.info_label)

        # Device list
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.MultiSelection)
        self.list_widget.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.list_widget)

    def refresh(self):
        """Refresh the device list."""
        self.list_widget.clear()
        devices = self.registry.scan_devices()

        # Filter to show only Razer devices prominently
        razer_devices = [d for d in devices if "razer" in d.stable_id.lower()]
        other_devices = [d for d in devices if "razer" not in d.stable_id.lower()]

        # Add Razer devices first
        for device in razer_devices:
            item = self._create_device_item(device, is_razer=True)
            self.list_widget.addItem(item)

        # Add separator if we have both types
        if razer_devices and other_devices:
            separator = QListWidgetItem("--- Other Devices ---")
            separator.setFlags(Qt.NoItemFlags)
            separator.setForeground(Qt.gray)
            self.list_widget.addItem(separator)

        # Add other devices
        for device in other_devices:
            item = self._create_device_item(device, is_razer=False)
            self.list_widget.addItem(item)

    def _create_device_item(self, device, is_razer: bool) -> QListWidgetItem:
        """Create a list item for a device."""
        # Format display text
        device_type = []
        if device.is_mouse:
            device_type.append("Mouse")
        if device.is_keyboard:
            device_type.append("Keyboard")
        type_str = ", ".join(device_type) if device_type else "Input"

        display_text = f"{device.name}\n  Type: {type_str}\n  ID: {device.stable_id}"

        item = QListWidgetItem(display_text)
        item.setData(Qt.UserRole, device.stable_id)

        if is_razer:
            item.setForeground(Qt.green)

        return item

    def _on_selection_changed(self):
        """Handle selection change."""
        selected = self.get_selected_devices()
        self.selection_changed.emit(selected)

    def get_selected_devices(self) -> list[str]:
        """Get list of selected device IDs."""
        selected = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.isSelected():
                device_id = item.data(Qt.UserRole)
                if device_id:
                    selected.append(device_id)
        return selected

    def set_selected_devices(self, device_ids: list[str]):
        """Set the selected devices by ID."""
        self.list_widget.clearSelection()
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            device_id = item.data(Qt.UserRole)
            if device_id in device_ids:
                item.setSelected(True)
