"""OpenRazer bridge - discover and control Razer devices via DBus."""

from dataclasses import dataclass, field
from enum import Enum

from pydbus import SessionBus


class LightingEffect(Enum):
    """Available lighting effects."""

    NONE = "none"
    STATIC = "static"
    SPECTRUM = "spectrum"
    BREATHING = "breathing"
    BREATHING_DUAL = "breathing_dual"
    BREATHING_RANDOM = "breathing_random"
    WAVE = "wave"
    REACTIVE = "reactive"
    STARLIGHT = "starlight"
    RIPPLE = "ripple"


class WaveDirection(Enum):
    """Wave effect direction."""

    LEFT = 1
    RIGHT = 2


class ReactiveSpeed(Enum):
    """Reactive effect speed."""

    SHORT = 1
    MEDIUM = 2
    LONG = 3


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
    has_poll_rate: bool = False
    has_logo: bool = False
    has_scroll: bool = False

    # Supported lighting effects
    supported_effects: list[str] = field(default_factory=list)

    # Current state (cached)
    brightness: int = 100
    dpi: tuple[int, int] = (800, 800)
    battery_level: int = -1
    poll_rate: int = 500
    is_charging: bool = False

    # Hardware info
    firmware_version: str = ""
    max_dpi: int = 16000
    available_poll_rates: list[int] = field(default_factory=lambda: [125, 500, 1000])


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

    def _get_device_info(self, object_path: str, serial_hint: str = "") -> RazerDevice | None:
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
        # Check for brightness/lighting
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

        # Check for max DPI
        try:
            device.max_dpi = dbus_dev.maxDPI()
        except Exception:
            pass

        # Check for battery
        try:
            device.battery_level = dbus_dev.getBattery()
            device.has_battery = True
        except Exception:
            pass

        # Check for charging status
        try:
            device.is_charging = dbus_dev.isCharging()
        except Exception:
            pass

        # Check for poll rate
        try:
            device.poll_rate = dbus_dev.getPollRate()
            device.has_poll_rate = True
        except Exception:
            pass

        # Check for firmware version
        try:
            device.firmware_version = dbus_dev.getFirmware()
        except Exception:
            pass

        # Detect supported effects by introspecting available methods
        effects = []
        effect_checks = [
            ("setStatic", "static"),
            ("setSpectrum", "spectrum"),
            ("setBreathSingle", "breathing"),
            ("setBreathDual", "breathing_dual"),
            ("setBreathRandom", "breathing_random"),
            ("setWave", "wave"),
            ("setReactive", "reactive"),
            ("setStarlight", "starlight"),
            ("setRipple", "ripple"),
            ("setNone", "none"),
        ]

        for method_name, effect_name in effect_checks:
            if hasattr(dbus_dev, method_name):
                effects.append(effect_name)

        device.supported_effects = effects

        # Check for logo/scroll lighting
        try:
            dbus_dev.getLogoActive()
            device.has_logo = True
        except Exception:
            pass

        try:
            dbus_dev.getScrollActive()
            device.has_scroll = True
        except Exception:
            pass

    def get_device(self, serial: str) -> RazerDevice | None:
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

    def set_dpi(self, serial: str, dpi_x: int, dpi_y: int | None = None) -> bool:
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
        """Set breathing effect with single color."""
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

    def set_breathing_dual(
        self, serial: str, r1: int, g1: int, b1: int, r2: int, g2: int, b2: int
    ) -> bool:
        """Set breathing effect with two colors."""
        device = self.get_device(serial)
        if not device or not device.has_lighting:
            return False

        try:
            dev = self._bus.get(self.DBUS_INTERFACE, device.object_path)
            dev.setBreathDual(r1, g1, b1, r2, g2, b2)
            return True
        except Exception as e:
            print(f"Error setting breathing dual: {e}")
            return False

    def set_breathing_random(self, serial: str) -> bool:
        """Set breathing effect with random colors."""
        device = self.get_device(serial)
        if not device or not device.has_lighting:
            return False

        try:
            dev = self._bus.get(self.DBUS_INTERFACE, device.object_path)
            dev.setBreathRandom()
            return True
        except Exception as e:
            print(f"Error setting breathing random: {e}")
            return False

    def set_wave_effect(self, serial: str, direction: WaveDirection = WaveDirection.RIGHT) -> bool:
        """Set wave effect with direction."""
        device = self.get_device(serial)
        if not device or not device.has_lighting:
            return False

        try:
            dev = self._bus.get(self.DBUS_INTERFACE, device.object_path)
            dev.setWave(direction.value)
            return True
        except Exception as e:
            print(f"Error setting wave: {e}")
            return False

    def set_reactive_effect(
        self, serial: str, r: int, g: int, b: int, speed: ReactiveSpeed = ReactiveSpeed.MEDIUM
    ) -> bool:
        """Set reactive effect - lights up on keypress."""
        device = self.get_device(serial)
        if not device or not device.has_lighting:
            return False

        try:
            dev = self._bus.get(self.DBUS_INTERFACE, device.object_path)
            dev.setReactive(r, g, b, speed.value)
            return True
        except Exception as e:
            print(f"Error setting reactive: {e}")
            return False

    def set_starlight_effect(
        self,
        serial: str,
        r: int = 0,
        g: int = 255,
        b: int = 0,
        speed: ReactiveSpeed = ReactiveSpeed.MEDIUM,
    ) -> bool:
        """Set starlight effect - random twinkling."""
        device = self.get_device(serial)
        if not device or not device.has_lighting:
            return False

        try:
            dev = self._bus.get(self.DBUS_INTERFACE, device.object_path)
            dev.setStarlight(r, g, b, speed.value)
            return True
        except Exception as e:
            print(f"Error setting starlight: {e}")
            return False

    def set_none_effect(self, serial: str) -> bool:
        """Turn off lighting."""
        device = self.get_device(serial)
        if not device or not device.has_lighting:
            return False

        try:
            dev = self._bus.get(self.DBUS_INTERFACE, device.object_path)
            dev.setNone()
            return True
        except Exception as e:
            print(f"Error turning off lighting: {e}")
            return False

    def set_poll_rate(self, serial: str, poll_rate: int) -> bool:
        """Set device polling rate (125, 500, or 1000 Hz)."""
        device = self.get_device(serial)
        if not device or not device.has_poll_rate:
            return False

        if poll_rate not in [125, 500, 1000]:
            print(f"Invalid poll rate: {poll_rate}. Use 125, 500, or 1000.")
            return False

        try:
            dev = self._bus.get(self.DBUS_INTERFACE, device.object_path)
            dev.setPollRate(poll_rate)
            device.poll_rate = poll_rate
            return True
        except Exception as e:
            print(f"Error setting poll rate: {e}")
            return False

    def get_poll_rate(self, serial: str) -> int | None:
        """Get device polling rate."""
        device = self.get_device(serial)
        if not device or not device.has_poll_rate:
            return None

        try:
            dev = self._bus.get(self.DBUS_INTERFACE, device.object_path)
            rate: int = dev.getPollRate()
            device.poll_rate = rate
            return rate
        except Exception as e:
            print(f"Error getting poll rate: {e}")
            return None

    def get_dpi(self, serial: str) -> tuple[int, int] | None:
        """Get current DPI."""
        device = self.get_device(serial)
        if not device or not device.has_dpi:
            return None

        try:
            dev = self._bus.get(self.DBUS_INTERFACE, device.object_path)
            dpi = dev.getDPI()
            device.dpi = (dpi[0], dpi[1]) if len(dpi) >= 2 else (dpi[0], dpi[0])
            return device.dpi
        except Exception as e:
            print(f"Error getting DPI: {e}")
            return None

    def get_brightness(self, serial: str) -> int | None:
        """Get current brightness."""
        device = self.get_device(serial)
        if not device or not device.has_brightness:
            return None

        try:
            dev = self._bus.get(self.DBUS_INTERFACE, device.object_path)
            brightness: int = dev.getBrightness()
            device.brightness = brightness
            return brightness
        except Exception as e:
            print(f"Error getting brightness: {e}")
            return None

    def get_battery(self, serial: str) -> dict | None:
        """Get battery info (level and charging status)."""
        device = self.get_device(serial)
        if not device or not device.has_battery:
            return None

        try:
            dev = self._bus.get(self.DBUS_INTERFACE, device.object_path)
            level = dev.getBattery()
            device.battery_level = level

            try:
                charging = dev.isCharging()
                device.is_charging = charging
            except Exception:
                charging = False

            return {"level": level, "charging": charging}
        except Exception as e:
            print(f"Error getting battery: {e}")
            return None

    def set_logo_brightness(self, serial: str, brightness: int) -> bool:
        """Set logo brightness (0-100)."""
        device = self.get_device(serial)
        if not device or not device.has_logo:
            return False

        try:
            dev = self._bus.get(self.DBUS_INTERFACE, device.object_path)
            dev.setLogoBrightness(brightness)
            return True
        except Exception as e:
            print(f"Error setting logo brightness: {e}")
            return False

    def set_scroll_brightness(self, serial: str, brightness: int) -> bool:
        """Set scroll wheel brightness (0-100)."""
        device = self.get_device(serial)
        if not device or not device.has_scroll:
            return False

        try:
            dev = self._bus.get(self.DBUS_INTERFACE, device.object_path)
            dev.setScrollBrightness(brightness)
            return True
        except Exception as e:
            print(f"Error setting scroll brightness: {e}")
            return False

    def set_logo_static(self, serial: str, r: int, g: int, b: int) -> bool:
        """Set logo to static color."""
        device = self.get_device(serial)
        if not device or not device.has_logo:
            return False

        try:
            dev = self._bus.get(self.DBUS_INTERFACE, device.object_path)
            dev.setLogoStatic(r, g, b)
            return True
        except Exception as e:
            print(f"Error setting logo color: {e}")
            return False

    def set_scroll_static(self, serial: str, r: int, g: int, b: int) -> bool:
        """Set scroll wheel to static color."""
        device = self.get_device(serial)
        if not device or not device.has_scroll:
            return False

        try:
            dev = self._bus.get(self.DBUS_INTERFACE, device.object_path)
            dev.setScrollStatic(r, g, b)
            return True
        except Exception as e:
            print(f"Error setting scroll color: {e}")
            return False

    def refresh_device(self, serial: str) -> RazerDevice | None:
        """Refresh device state from hardware."""
        device = self.get_device(serial)
        if not device:
            return None

        try:
            dev = self._bus.get(self.DBUS_INTERFACE, device.object_path)
            self._detect_capabilities(dev, device)
            return device
        except Exception as e:
            print(f"Error refreshing device: {e}")
            return None


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
