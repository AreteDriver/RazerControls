"""Device registry - enumerate and track input devices with stable IDs."""

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class InputDevice:
    """Represents an input device."""

    stable_id: str  # e.g., usb-Razer_Razer_Basilisk_V2-event-mouse
    name: str  # Human readable name from device
    event_path: str  # e.g., /dev/input/event8
    by_id_path: str | None  # e.g., /dev/input/by-id/usb-Razer_...
    by_path_path: str | None  # e.g., /dev/input/by-path/...
    is_mouse: bool = False
    is_keyboard: bool = False
    capabilities: list[str] = field(default_factory=list)


class DeviceRegistry:
    """Registry for managing input devices with stable identification."""

    def __init__(self, config_dir: Path | None = None):
        if config_dir is None:
            config_dir = Path.home() / ".config" / "razer-control-center"
        self.config_dir = config_dir
        self.devices_file = config_dir / "devices.json"
        self._devices: dict[str, InputDevice] = {}

    def scan_devices(self) -> list[InputDevice]:
        """Scan for all input devices and return them with stable IDs."""
        devices: list[InputDevice] = []

        by_id = Path("/dev/input/by-id")
        if not by_id.exists():
            return devices

        for link in by_id.iterdir():
            if not link.is_symlink():
                continue

            # Get the actual event device
            try:
                target = link.resolve()
                event_path = str(target)

                # Read device name
                name = self._get_device_name(target)

                # Determine device type
                is_mouse = "-mouse" in link.name or "-event-mouse" in link.name
                is_keyboard = "-kbd" in link.name or "-event-kbd" in link.name

                device = InputDevice(
                    stable_id=link.name,
                    name=name,
                    event_path=event_path,
                    by_id_path=str(link),
                    by_path_path=self._find_by_path(target),
                    is_mouse=is_mouse,
                    is_keyboard=is_keyboard,
                )
                devices.append(device)
                self._devices[device.stable_id] = device

            except (OSError, ValueError):
                continue

        return devices

    def _get_device_name(self, event_path: Path) -> str:
        """Get the human-readable name for an input device."""
        # /dev/input/eventX -> /sys/class/input/eventX/device/name
        event_name = event_path.name
        name_path = Path(f"/sys/class/input/{event_name}/device/name")
        try:
            return name_path.read_text().strip()
        except OSError:
            return event_name

    def _find_by_path(self, event_path: Path) -> str | None:
        """Find the by-path symlink for an event device."""
        by_path = Path("/dev/input/by-path")
        if not by_path.exists():
            return None

        for link in by_path.iterdir():
            try:
                if link.resolve() == event_path:
                    return str(link)
            except OSError:
                continue
        return None

    def get_device_by_stable_id(self, stable_id: str) -> InputDevice | None:
        """Get a device by its stable ID."""
        if not self._devices:
            self.scan_devices()
        return self._devices.get(stable_id)

    def get_event_path(self, stable_id: str) -> str | None:
        """Get the current event path for a stable device ID."""
        device = self.get_device_by_stable_id(stable_id)
        if device:
            return device.event_path

        # Try to resolve from by-id directly
        by_id_path = Path("/dev/input/by-id") / stable_id
        if by_id_path.exists():
            try:
                return str(by_id_path.resolve())
            except OSError:
                pass
        return None

    def get_razer_devices(self) -> list[InputDevice]:
        """Get all Razer input devices."""
        if not self._devices:
            self.scan_devices()
        return [d for d in self._devices.values() if "razer" in d.stable_id.lower()]

    def save_selected_devices(self, device_ids: list[str]) -> None:
        """Save selected device IDs to config."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.devices_file.write_text(json.dumps({"selected": device_ids}, indent=2))

    def load_selected_devices(self) -> list[str]:
        """Load selected device IDs from config."""
        if not self.devices_file.exists():
            return []
        try:
            data = json.loads(self.devices_file.read_text())
            selected: list[str] = data.get("selected", [])
            return selected
        except (json.JSONDecodeError, KeyError):
            return []
