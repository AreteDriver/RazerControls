"""OpenRazer bridge - discover and control Razer devices via DBus."""

from dataclasses import dataclass, field
from typing import Optional

from pydbus import SessionBus


@dataclass
class RazerDevice:
    """Represents a Razer device discovered via OpenRazer."""
    serial: str
    name: str
    device_type: str
    object_path: str

    # Capabilities
    has_lighting: bool = False
    has_brightness: bool = False
    has_dpi: bool = False
    has_battery: bool = False

    # Current state (cached)
    brightness: int = 100
    dpi: tuple[int, int] = (800, 800)
    battery_level: int = -1

    # Available DPI stages
    dpi_stages: list[int] = field(default_factory=list)


class OpenRazerBridge:
    """Bridge to OpenRazer daemon via DBus."""

    DBUS_INTERFACE = "org.razer"
    DAEMON_PATH = "/org/razer"

    def __init__(self):
        self._bus = SessionBus()
        self._daemon = None
        self._devices: dict[str, RazerDevice] = {}

    def connect(self) -> bool:
        """Connect to OpenRazer daemon."""
        try:
            self._daemon = self._bus.get(self.DBUS_INTERFACE, self.DAEMON_PATH)
            return True
        except Exception as e:
            print(f"Failed to connect to OpenRazer daemon: {e}")
            return False

    def is_connected(self) -> bool:
        """Check if connected to daemon."""
        return self._daemon is not None

    def discover_devices(self) -> list[RazerDevice]:
        """Discover all Razer devices."""
        if not self._daemon:
            if not self.connect():
                return []

        devices = []
        try:
            # getDevices() returns serial numbers, not object paths
            device_serials = self._daemon.getDevices()

            for serial in device_serials:
                # Construct the full object path
                object_path = f"/org/razer/device/{serial}"
                device = self._get_device_info(object_path, serial)
                if device:
                    devices.append(device)
                    self._devices[device.serial] = device

        except Exception as e:
            print(f"Error discovering devices: {e}")

        return devices

    def _get_device_info(self, object_path: str, serial_hint: str = "") -> Optional[RazerDevice]:
        """Get device info from a DBus object path."""
        try:
            dev = self._bus.get(self.DBUS_INTERFACE, object_path)

            # Get basic info - some methods may not exist on all devices
            try:
                serial = dev.getSerial()
            except Exception:
                serial = serial_hint

            try:
                name = dev.getDeviceName()
            except Exception:
                name = f"Razer Device ({serial})"

            try:
                device_type = dev.getDeviceType()
            except Exception:
                device_type = "unknown"

            device = RazerDevice(
                serial=serial,
                name=name,
                device_type=device_type,
                object_path=object_path,
            )

            # Check capabilities by trying to introspect
            self._detect_capabilities(dev, device)

            return device

        except Exception as e:
            print(f"Error getting device info for {object_path}: {e}")
            return None

    def _detect_capabilities(self, dbus_dev, device: RazerDevice) -> None:
        """Detect device capabilities via DBus introspection."""
        # Check for lighting
        try:
            device.brightness = dbus_dev.getBrightness()
            device.has_brightness = True
            device.has_lighting = True
        except Exception:
            pass

        # Check for DPI
        try:
            dpi = dbus_dev.getDPI()
            device.dpi = (dpi[0], dpi[1]) if len(dpi) >= 2 else (dpi[0], dpi[0])
            device.has_dpi = True
        except Exception:
            pass

        # Check for battery
        try:
            device.battery_level = dbus_dev.getBattery()
            device.has_battery = True
        except Exception:
            pass

    def get_device(self, serial: str) -> Optional[RazerDevice]:
        """Get a device by serial number."""
        if serial in self._devices:
            return self._devices[serial]
        # Re-scan if not found
        self.discover_devices()
        return self._devices.get(serial)

    def set_brightness(self, serial: str, brightness: int) -> bool:
        """Set device brightness (0-100)."""
        device = self.get_device(serial)
        if not device or not device.has_brightness:
            return False

        try:
            dev = self._bus.get(self.DBUS_INTERFACE, device.object_path)
            dev.setBrightness(brightness)
            device.brightness = brightness
            return True
        except Exception as e:
            print(f"Error setting brightness: {e}")
            return False

    def set_static_color(self, serial: str, r: int, g: int, b: int) -> bool:
        """Set static lighting color."""
        device = self.get_device(serial)
        if not device or not device.has_lighting:
            return False

        try:
            dev = self._bus.get(self.DBUS_INTERFACE, device.object_path)
            dev.setStatic(r, g, b)
            return True
        except Exception as e:
            print(f"Error setting color: {e}")
            return False

    def set_dpi(self, serial: str, dpi_x: int, dpi_y: Optional[int] = None) -> bool:
        """Set device DPI."""
        if dpi_y is None:
            dpi_y = dpi_x

        device = self.get_device(serial)
        if not device or not device.has_dpi:
            return False

        try:
            dev = self._bus.get(self.DBUS_INTERFACE, device.object_path)
            dev.setDPI(dpi_x, dpi_y)
            device.dpi = (dpi_x, dpi_y)
            return True
        except Exception as e:
            print(f"Error setting DPI: {e}")
            return False

    def set_spectrum_effect(self, serial: str) -> bool:
        """Set spectrum cycling effect."""
        device = self.get_device(serial)
        if not device or not device.has_lighting:
            return False

        try:
            dev = self._bus.get(self.DBUS_INTERFACE, device.object_path)
            dev.setSpectrum()
            return True
        except Exception as e:
            print(f"Error setting spectrum: {e}")
            return False

    def set_breathing_effect(self, serial: str, r: int, g: int, b: int) -> bool:
        """Set breathing effect with color."""
        device = self.get_device(serial)
        if not device or not device.has_lighting:
            return False

        try:
            dev = self._bus.get(self.DBUS_INTERFACE, device.object_path)
            dev.setBreathSingle(r, g, b)
            return True
        except Exception as e:
            print(f"Error setting breathing: {e}")
            return False


def main():
    """Test OpenRazer discovery."""
    bridge = OpenRazerBridge()

    if not bridge.connect():
        print("Failed to connect to OpenRazer daemon")
        print("Is openrazer-daemon running?")
        return

    print("Connected to OpenRazer daemon")
    print("\nDiscovering devices...")

    devices = bridge.discover_devices()

    if not devices:
        print("No Razer devices found")
        return

    for dev in devices:
        print(f"\n{dev.name}")
        print(f"  Serial: {dev.serial}")
        print(f"  Type: {dev.device_type}")
        print(f"  Lighting: {dev.has_lighting}")
        print(f"  Brightness: {dev.has_brightness}")
        if dev.has_brightness:
            print(f"    Current: {dev.brightness}%")
        print(f"  DPI: {dev.has_dpi}")
        if dev.has_dpi:
            print(f"    Current: {dev.dpi}")
        print(f"  Battery: {dev.has_battery}")
        if dev.has_battery:
            print(f"    Level: {dev.battery_level}%")


if __name__ == "__main__":
    main()
