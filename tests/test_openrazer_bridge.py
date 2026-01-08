"""Tests for OpenRazerBridge - D-Bus communication with OpenRazer daemon."""

from unittest.mock import MagicMock, patch

import pytest

from services.openrazer_bridge.bridge import (
    LightingEffect,
    OpenRazerBridge,
    RazerDevice,
    ReactiveSpeed,
    WaveDirection,
)

# --- Fixtures ---


@pytest.fixture
def mock_session_bus():
    """Create a mock SessionBus."""
    with patch("services.openrazer_bridge.bridge.SessionBus") as mock:
        bus_instance = MagicMock()
        mock.return_value = bus_instance
        yield bus_instance


@pytest.fixture
def mock_daemon(mock_session_bus):
    """Create a mock OpenRazer daemon."""
    daemon = MagicMock()
    daemon.getDevices.return_value = ["PM1234567890"]
    mock_session_bus.get.return_value = daemon
    return daemon


@pytest.fixture
def mock_device():
    """Create a mock device DBus object."""
    device = MagicMock()
    device.getSerial.return_value = "PM1234567890"
    device.getDeviceName.return_value = "Razer DeathAdder V2"
    device.getDeviceType.return_value = "mouse"
    device.getBrightness.return_value = 75
    device.getDPI.return_value = [800, 800]
    device.maxDPI.return_value = 20000
    device.getPollRate.return_value = 1000
    device.getFirmware.return_value = "1.0.0"
    return device


@pytest.fixture
def sample_device():
    """Create a sample RazerDevice."""
    return RazerDevice(
        serial="PM1234567890",
        name="Razer DeathAdder V2",
        device_type="mouse",
        object_path="/org/razer/device/PM1234567890",
        has_lighting=True,
        has_brightness=True,
        has_dpi=True,
        has_battery=False,
        has_poll_rate=True,
        brightness=75,
        dpi=(800, 800),
        poll_rate=1000,
    )


# --- Test Classes ---


class TestRazerDevice:
    """Tests for RazerDevice dataclass."""

    def test_default_values(self):
        """Test RazerDevice default values."""
        device = RazerDevice(
            serial="TEST123",
            name="Test Device",
            device_type="mouse",
            object_path="/org/razer/device/TEST123",
        )
        assert device.has_lighting is False
        assert device.has_brightness is False
        assert device.has_dpi is False
        assert device.has_battery is False
        assert device.brightness == 100
        assert device.dpi == (800, 800)


class TestEnums:
    """Tests for bridge enums."""

    def test_lighting_effect_values(self):
        """Test LightingEffect enum values."""
        assert LightingEffect.STATIC.value == "static"
        assert LightingEffect.SPECTRUM.value == "spectrum"
        assert LightingEffect.WAVE.value == "wave"

    def test_wave_direction_values(self):
        """Test WaveDirection enum values."""
        assert WaveDirection.LEFT.value == 1
        assert WaveDirection.RIGHT.value == 2

    def test_reactive_speed_values(self):
        """Test ReactiveSpeed enum values."""
        assert ReactiveSpeed.SHORT.value == 1
        assert ReactiveSpeed.MEDIUM.value == 2
        assert ReactiveSpeed.LONG.value == 3


class TestBridgeInit:
    """Tests for OpenRazerBridge initialization."""

    def test_init_creates_bus(self, mock_session_bus):
        """Test init creates session bus."""
        bridge = OpenRazerBridge()
        assert bridge._bus is not None
        assert bridge._daemon is None


class TestConnect:
    """Tests for connect method."""

    def test_connect_success(self, mock_session_bus):
        """Test successful connection."""
        daemon = MagicMock()
        mock_session_bus.get.return_value = daemon

        bridge = OpenRazerBridge()
        result = bridge.connect()

        assert result is True
        assert bridge._daemon == daemon
        mock_session_bus.get.assert_called_with("org.razer", "/org/razer")

    def test_connect_failure(self, mock_session_bus):
        """Test connection failure."""
        mock_session_bus.get.side_effect = Exception("DBus error")

        bridge = OpenRazerBridge()
        result = bridge.connect()

        assert result is False
        assert bridge._daemon is None

    def test_is_connected(self, mock_session_bus):
        """Test is_connected returns correct state."""
        bridge = OpenRazerBridge()
        assert bridge.is_connected() is False

        daemon = MagicMock()
        mock_session_bus.get.return_value = daemon
        bridge.connect()
        assert bridge.is_connected() is True


class TestDiscoverDevices:
    """Tests for device discovery."""

    def test_discover_devices(self, mock_session_bus, mock_device):
        """Test discovering devices."""
        daemon = MagicMock()
        daemon.getDevices.return_value = ["PM1234567890"]

        def get_side_effect(interface, path):
            if path == "/org/razer":
                return daemon
            return mock_device

        mock_session_bus.get.side_effect = get_side_effect

        bridge = OpenRazerBridge()
        devices = bridge.discover_devices()

        assert len(devices) == 1
        assert devices[0].serial == "PM1234567890"
        assert devices[0].name == "Razer DeathAdder V2"

    def test_discover_no_devices(self, mock_session_bus):
        """Test discovery with no devices."""
        daemon = MagicMock()
        daemon.getDevices.return_value = []
        mock_session_bus.get.return_value = daemon

        bridge = OpenRazerBridge()
        devices = bridge.discover_devices()

        assert len(devices) == 0

    def test_discover_caches_devices(self, mock_session_bus, mock_device):
        """Test discovered devices are cached."""
        daemon = MagicMock()
        daemon.getDevices.return_value = ["PM1234567890"]

        def get_side_effect(interface, path):
            if path == "/org/razer":
                return daemon
            return mock_device

        mock_session_bus.get.side_effect = get_side_effect

        bridge = OpenRazerBridge()
        bridge.discover_devices()

        # Should be able to get device by serial
        device = bridge.get_device("PM1234567890")
        assert device is not None
        assert device.serial == "PM1234567890"


class TestGetDevice:
    """Tests for get_device method."""

    def test_get_cached_device(self, mock_session_bus, sample_device):
        """Test getting a cached device."""
        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = sample_device

        device = bridge.get_device("PM1234567890")
        assert device == sample_device

    def test_get_unknown_device_triggers_discovery(self, mock_session_bus):
        """Test getting unknown device triggers re-scan."""
        daemon = MagicMock()
        daemon.getDevices.return_value = []
        mock_session_bus.get.return_value = daemon

        bridge = OpenRazerBridge()
        device = bridge.get_device("UNKNOWN123")

        assert device is None
        # Should have tried to discover
        daemon.getDevices.assert_called()


class TestBrightness:
    """Tests for brightness control."""

    def test_set_brightness(self, mock_session_bus, sample_device, mock_device):
        """Test setting brightness."""
        mock_session_bus.get.return_value = mock_device

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = sample_device

        result = bridge.set_brightness("PM1234567890", 50)

        assert result is True
        mock_device.setBrightness.assert_called_with(50)
        assert sample_device.brightness == 50

    def test_set_brightness_no_capability(self, mock_session_bus, sample_device):
        """Test setting brightness on device without capability."""
        sample_device.has_brightness = False

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = sample_device

        result = bridge.set_brightness("PM1234567890", 50)
        assert result is False

    def test_get_brightness(self, mock_session_bus, sample_device, mock_device):
        """Test getting brightness."""
        mock_device.getBrightness.return_value = 80
        mock_session_bus.get.return_value = mock_device

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = sample_device

        brightness = bridge.get_brightness("PM1234567890")

        assert brightness == 80


class TestDPI:
    """Tests for DPI control."""

    def test_set_dpi(self, mock_session_bus, sample_device, mock_device):
        """Test setting DPI."""
        mock_session_bus.get.return_value = mock_device

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = sample_device

        result = bridge.set_dpi("PM1234567890", 1600, 1600)

        assert result is True
        mock_device.setDPI.assert_called_with(1600, 1600)
        assert sample_device.dpi == (1600, 1600)

    def test_set_dpi_single_value(self, mock_session_bus, sample_device, mock_device):
        """Test setting DPI with single value uses same for X and Y."""
        mock_session_bus.get.return_value = mock_device

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = sample_device

        bridge.set_dpi("PM1234567890", 1600)

        mock_device.setDPI.assert_called_with(1600, 1600)

    def test_get_dpi(self, mock_session_bus, sample_device, mock_device):
        """Test getting DPI."""
        mock_device.getDPI.return_value = [1600, 1600]
        mock_session_bus.get.return_value = mock_device

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = sample_device

        dpi = bridge.get_dpi("PM1234567890")

        assert dpi == (1600, 1600)


class TestPollRate:
    """Tests for poll rate control."""

    def test_set_poll_rate(self, mock_session_bus, sample_device, mock_device):
        """Test setting poll rate."""
        mock_session_bus.get.return_value = mock_device

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = sample_device

        result = bridge.set_poll_rate("PM1234567890", 500)

        assert result is True
        mock_device.setPollRate.assert_called_with(500)

    def test_set_invalid_poll_rate(self, mock_session_bus, sample_device):
        """Test setting invalid poll rate."""
        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = sample_device

        result = bridge.set_poll_rate("PM1234567890", 250)

        assert result is False

    def test_get_poll_rate(self, mock_session_bus, sample_device, mock_device):
        """Test getting poll rate."""
        mock_device.getPollRate.return_value = 1000
        mock_session_bus.get.return_value = mock_device

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = sample_device

        rate = bridge.get_poll_rate("PM1234567890")

        assert rate == 1000


class TestLightingEffects:
    """Tests for lighting effect control."""

    def test_set_static_color(self, mock_session_bus, sample_device, mock_device):
        """Test setting static color."""
        mock_session_bus.get.return_value = mock_device

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = sample_device

        result = bridge.set_static_color("PM1234567890", 255, 0, 0)

        assert result is True
        mock_device.setStatic.assert_called_with(255, 0, 0)

    def test_set_spectrum_effect(self, mock_session_bus, sample_device, mock_device):
        """Test setting spectrum effect."""
        mock_session_bus.get.return_value = mock_device

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = sample_device

        result = bridge.set_spectrum_effect("PM1234567890")

        assert result is True
        mock_device.setSpectrum.assert_called()

    def test_set_breathing_effect(self, mock_session_bus, sample_device, mock_device):
        """Test setting breathing effect."""
        mock_session_bus.get.return_value = mock_device

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = sample_device

        result = bridge.set_breathing_effect("PM1234567890", 0, 255, 0)

        assert result is True
        mock_device.setBreathSingle.assert_called_with(0, 255, 0)

    def test_set_breathing_dual(self, mock_session_bus, sample_device, mock_device):
        """Test setting dual color breathing."""
        mock_session_bus.get.return_value = mock_device

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = sample_device

        result = bridge.set_breathing_dual("PM1234567890", 255, 0, 0, 0, 0, 255)

        assert result is True
        mock_device.setBreathDual.assert_called_with(255, 0, 0, 0, 0, 255)

    def test_set_breathing_random(self, mock_session_bus, sample_device, mock_device):
        """Test setting random breathing."""
        mock_session_bus.get.return_value = mock_device

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = sample_device

        result = bridge.set_breathing_random("PM1234567890")

        assert result is True
        mock_device.setBreathRandom.assert_called()

    def test_set_wave_effect(self, mock_session_bus, sample_device, mock_device):
        """Test setting wave effect."""
        mock_session_bus.get.return_value = mock_device

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = sample_device

        result = bridge.set_wave_effect("PM1234567890", WaveDirection.LEFT)

        assert result is True
        mock_device.setWave.assert_called_with(1)

    def test_set_reactive_effect(self, mock_session_bus, sample_device, mock_device):
        """Test setting reactive effect."""
        mock_session_bus.get.return_value = mock_device

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = sample_device

        result = bridge.set_reactive_effect("PM1234567890", 255, 255, 0, ReactiveSpeed.SHORT)

        assert result is True
        mock_device.setReactive.assert_called_with(255, 255, 0, 1)

    def test_set_starlight_effect(self, mock_session_bus, sample_device, mock_device):
        """Test setting starlight effect."""
        mock_session_bus.get.return_value = mock_device

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = sample_device

        result = bridge.set_starlight_effect("PM1234567890", 0, 255, 255)

        assert result is True
        mock_device.setStarlight.assert_called()

    def test_set_none_effect(self, mock_session_bus, sample_device, mock_device):
        """Test turning off lighting."""
        mock_session_bus.get.return_value = mock_device

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = sample_device

        result = bridge.set_none_effect("PM1234567890")

        assert result is True
        mock_device.setNone.assert_called()


class TestLogoAndScroll:
    """Tests for logo and scroll wheel lighting."""

    def test_set_logo_brightness(self, mock_session_bus, mock_device):
        """Test setting logo brightness."""
        mock_session_bus.get.return_value = mock_device

        device = RazerDevice(
            serial="PM1234567890",
            name="Test",
            device_type="mouse",
            object_path="/org/razer/device/PM1234567890",
            has_logo=True,
        )

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = device

        result = bridge.set_logo_brightness("PM1234567890", 50)

        assert result is True
        mock_device.setLogoBrightness.assert_called_with(50)

    def test_set_scroll_brightness(self, mock_session_bus, mock_device):
        """Test setting scroll brightness."""
        mock_session_bus.get.return_value = mock_device

        device = RazerDevice(
            serial="PM1234567890",
            name="Test",
            device_type="mouse",
            object_path="/org/razer/device/PM1234567890",
            has_scroll=True,
        )

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = device

        result = bridge.set_scroll_brightness("PM1234567890", 75)

        assert result is True
        mock_device.setScrollBrightness.assert_called_with(75)

    def test_set_logo_static(self, mock_session_bus, mock_device):
        """Test setting logo static color."""
        mock_session_bus.get.return_value = mock_device

        device = RazerDevice(
            serial="PM1234567890",
            name="Test",
            device_type="mouse",
            object_path="/org/razer/device/PM1234567890",
            has_logo=True,
        )

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = device

        result = bridge.set_logo_static("PM1234567890", 255, 0, 0)

        assert result is True
        mock_device.setLogoStatic.assert_called_with(255, 0, 0)

    def test_set_scroll_static(self, mock_session_bus, mock_device):
        """Test setting scroll static color."""
        mock_session_bus.get.return_value = mock_device

        device = RazerDevice(
            serial="PM1234567890",
            name="Test",
            device_type="mouse",
            object_path="/org/razer/device/PM1234567890",
            has_scroll=True,
        )

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = device

        result = bridge.set_scroll_static("PM1234567890", 0, 255, 0)

        assert result is True
        mock_device.setScrollStatic.assert_called_with(0, 255, 0)


class TestBattery:
    """Tests for battery status."""

    def test_get_battery(self, mock_session_bus, mock_device):
        """Test getting battery status."""
        mock_device.getBattery.return_value = 85
        mock_device.isCharging.return_value = True
        mock_session_bus.get.return_value = mock_device

        device = RazerDevice(
            serial="PM1234567890",
            name="Test",
            device_type="mouse",
            object_path="/org/razer/device/PM1234567890",
            has_battery=True,
        )

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = device

        battery = bridge.get_battery("PM1234567890")

        assert battery is not None
        assert battery["level"] == 85
        assert battery["charging"] is True

    def test_get_battery_no_capability(self, mock_session_bus, sample_device):
        """Test getting battery on device without capability."""
        sample_device.has_battery = False

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = sample_device

        battery = bridge.get_battery("PM1234567890")
        assert battery is None


class TestRefreshDevice:
    """Tests for device refresh."""

    def test_refresh_device(self, mock_session_bus, sample_device, mock_device):
        """Test refreshing device state."""
        mock_device.getBrightness.return_value = 90
        mock_session_bus.get.return_value = mock_device

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = sample_device

        device = bridge.refresh_device("PM1234567890")

        assert device is not None
        assert device.brightness == 90


class TestCapabilityDetection:
    """Tests for capability detection."""

    def test_detects_supported_effects(self, mock_session_bus):
        """Test detection of supported effects."""
        mock_device = MagicMock()
        mock_device.getSerial.return_value = "TEST123"
        mock_device.getDeviceName.return_value = "Test Device"
        mock_device.getDeviceType.return_value = "keyboard"
        mock_device.getBrightness.return_value = 100

        # Make some methods exist
        mock_device.setStatic = MagicMock()
        mock_device.setSpectrum = MagicMock()
        mock_device.setWave = MagicMock()

        daemon = MagicMock()
        daemon.getDevices.return_value = ["TEST123"]

        def get_side_effect(interface, path):
            if path == "/org/razer":
                return daemon
            return mock_device

        mock_session_bus.get.side_effect = get_side_effect

        bridge = OpenRazerBridge()
        devices = bridge.discover_devices()

        assert len(devices) == 1
        device = devices[0]
        assert "static" in device.supported_effects
        assert "spectrum" in device.supported_effects
        assert "wave" in device.supported_effects


class TestErrorHandling:
    """Tests for error handling."""

    def test_set_brightness_handles_error(self, mock_session_bus, sample_device):
        """Test set_brightness handles DBus errors."""
        mock_device = MagicMock()
        mock_device.setBrightness.side_effect = Exception("DBus error")
        mock_session_bus.get.return_value = mock_device

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = sample_device

        result = bridge.set_brightness("PM1234567890", 50)

        assert result is False

    def test_get_dpi_handles_error(self, mock_session_bus, sample_device):
        """Test get_dpi handles DBus errors."""
        mock_device = MagicMock()
        mock_device.getDPI.side_effect = Exception("DBus error")
        mock_session_bus.get.return_value = mock_device

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = sample_device

        result = bridge.get_dpi("PM1234567890")

        assert result is None

    def test_discover_handles_error(self, mock_session_bus):
        """Test discover_devices handles errors."""
        daemon = MagicMock()
        daemon.getDevices.side_effect = Exception("DBus error")
        mock_session_bus.get.return_value = daemon

        bridge = OpenRazerBridge()
        devices = bridge.discover_devices()

        assert devices == []


class TestDiscoverWithAutoConnect:
    """Tests for discover_devices auto-connect behavior."""

    def test_discover_auto_connects(self, mock_session_bus, mock_device):
        """Test discover_devices connects if not already connected (line 106)."""
        daemon = MagicMock()
        daemon.getDevices.return_value = ["TEST123"]

        def get_side_effect(interface, path):
            if path == "/org/razer":
                return daemon
            return mock_device

        mock_session_bus.get.side_effect = get_side_effect

        bridge = OpenRazerBridge()
        assert bridge._daemon is None  # Not connected

        devices = bridge.discover_devices()

        assert bridge._daemon is not None  # Now connected
        assert len(devices) == 1

    def test_discover_returns_empty_when_connect_fails(self, mock_session_bus):
        """Test discover_devices returns [] when connect fails (line 106)."""
        mock_session_bus.get.side_effect = Exception("No daemon")

        bridge = OpenRazerBridge()
        devices = bridge.discover_devices()

        assert devices == []


class TestGetDeviceInfoFallbacks:
    """Tests for _get_device_info fallback handling."""

    def test_device_info_fallback_serial(self, mock_session_bus):
        """Test _get_device_info uses serial hint when getSerial fails (lines 134-135)."""
        mock_dev = MagicMock()
        mock_dev.getSerial.side_effect = Exception("Not available")
        mock_dev.getDeviceName.return_value = "Test Device"
        mock_dev.getDeviceType.return_value = "mouse"
        mock_dev.getBrightness.side_effect = Exception("Not supported")
        mock_session_bus.get.return_value = mock_dev

        bridge = OpenRazerBridge()
        device = bridge._get_device_info("/org/razer/device/HINT123", "HINT123")

        assert device is not None
        assert device.serial == "HINT123"

    def test_device_info_fallback_name(self, mock_session_bus):
        """Test _get_device_info uses default name when getDeviceName fails (lines 139-140)."""
        mock_dev = MagicMock()
        mock_dev.getSerial.return_value = "TEST123"
        mock_dev.getDeviceName.side_effect = Exception("Not available")
        mock_dev.getDeviceType.return_value = "mouse"
        mock_dev.getBrightness.side_effect = Exception("Not supported")
        mock_session_bus.get.return_value = mock_dev

        bridge = OpenRazerBridge()
        device = bridge._get_device_info("/org/razer/device/TEST123")

        assert device is not None
        assert "TEST123" in device.name  # Name contains serial

    def test_device_info_fallback_type(self, mock_session_bus):
        """Test _get_device_info uses 'unknown' when getDeviceType fails (lines 144-145)."""
        mock_dev = MagicMock()
        mock_dev.getSerial.return_value = "TEST123"
        mock_dev.getDeviceName.return_value = "Test Device"
        mock_dev.getDeviceType.side_effect = Exception("Not available")
        mock_dev.getBrightness.side_effect = Exception("Not supported")
        mock_session_bus.get.return_value = mock_dev

        bridge = OpenRazerBridge()
        device = bridge._get_device_info("/org/razer/device/TEST123")

        assert device is not None
        assert device.device_type == "unknown"

    def test_device_info_exception(self, mock_session_bus):
        """Test _get_device_info returns None on exception (lines 159-161)."""
        mock_session_bus.get.side_effect = Exception("DBus error")

        bridge = OpenRazerBridge()
        device = bridge._get_device_info("/org/razer/device/TEST123")

        assert device is None


class TestCapabilityDetectionExceptions:
    """Tests for capability detection exception handling."""

    def test_detect_caps_brightness_exception(self, mock_session_bus):
        """Test brightness detection handles exception (lines 170-171)."""
        mock_dev = MagicMock()
        mock_dev.getBrightness.side_effect = Exception("Not supported")
        # Also mock fallback brightness methods
        mock_dev.getLogoBrightness.side_effect = Exception("Not supported")
        mock_dev.getScrollBrightness.side_effect = Exception("Not supported")
        mock_session_bus.get.return_value = mock_dev

        device = RazerDevice(
            serial="TEST123",
            name="Test",
            device_type="mouse",
            object_path="/org/razer/device/TEST123",
        )
        bridge = OpenRazerBridge()
        bridge._detect_capabilities(mock_dev, device)

        assert device.has_brightness is False

    def test_detect_caps_dpi_exception(self, mock_session_bus):
        """Test DPI detection handles exception (lines 178-179)."""
        mock_dev = MagicMock()
        mock_dev.getBrightness.side_effect = Exception("Not supported")
        mock_dev.getDPI.side_effect = Exception("Not supported")
        mock_session_bus.get.return_value = mock_dev

        device = RazerDevice(
            serial="TEST123",
            name="Test",
            device_type="mouse",
            object_path="/org/razer/device/TEST123",
        )
        bridge = OpenRazerBridge()
        bridge._detect_capabilities(mock_dev, device)

        assert device.has_dpi is False

    def test_detect_caps_max_dpi_exception(self, mock_session_bus):
        """Test max DPI detection handles exception (lines 184-185)."""
        mock_dev = MagicMock()
        mock_dev.getBrightness.side_effect = Exception("Not supported")
        mock_dev.getDPI.return_value = [800, 800]
        mock_dev.maxDPI.side_effect = Exception("Not supported")
        mock_session_bus.get.return_value = mock_dev

        device = RazerDevice(
            serial="TEST123",
            name="Test",
            device_type="mouse",
            object_path="/org/razer/device/TEST123",
        )
        bridge = OpenRazerBridge()
        bridge._detect_capabilities(mock_dev, device)

        assert device.max_dpi == 16000  # Default value

    def test_detect_caps_battery_exception(self, mock_session_bus):
        """Test battery detection handles exception (lines 191-192)."""
        mock_dev = MagicMock()
        mock_dev.getBrightness.side_effect = Exception("Not supported")
        mock_dev.getBattery.side_effect = Exception("Not supported")
        mock_session_bus.get.return_value = mock_dev

        device = RazerDevice(
            serial="TEST123",
            name="Test",
            device_type="mouse",
            object_path="/org/razer/device/TEST123",
        )
        bridge = OpenRazerBridge()
        bridge._detect_capabilities(mock_dev, device)

        assert device.has_battery is False

    def test_detect_caps_charging_exception(self, mock_session_bus):
        """Test charging detection handles exception (lines 197-198)."""
        mock_dev = MagicMock()
        mock_dev.getBrightness.side_effect = Exception("Not supported")
        mock_dev.getBattery.return_value = 80
        mock_dev.isCharging.side_effect = Exception("Not supported")
        mock_session_bus.get.return_value = mock_dev

        device = RazerDevice(
            serial="TEST123",
            name="Test",
            device_type="mouse",
            object_path="/org/razer/device/TEST123",
        )
        bridge = OpenRazerBridge()
        bridge._detect_capabilities(mock_dev, device)

        assert device.is_charging is False

    def test_detect_caps_poll_rate_exception(self, mock_session_bus):
        """Test poll rate detection handles exception (lines 204-205)."""
        mock_dev = MagicMock()
        mock_dev.getBrightness.side_effect = Exception("Not supported")
        mock_dev.getPollRate.side_effect = Exception("Not supported")
        mock_session_bus.get.return_value = mock_dev

        device = RazerDevice(
            serial="TEST123",
            name="Test",
            device_type="mouse",
            object_path="/org/razer/device/TEST123",
        )
        bridge = OpenRazerBridge()
        bridge._detect_capabilities(mock_dev, device)

        assert device.has_poll_rate is False

    def test_detect_caps_firmware_exception(self, mock_session_bus):
        """Test firmware detection handles exception (lines 210-211)."""
        mock_dev = MagicMock()
        mock_dev.getBrightness.side_effect = Exception("Not supported")
        mock_dev.getFirmware.side_effect = Exception("Not supported")
        mock_session_bus.get.return_value = mock_dev

        device = RazerDevice(
            serial="TEST123",
            name="Test",
            device_type="mouse",
            object_path="/org/razer/device/TEST123",
        )
        bridge = OpenRazerBridge()
        bridge._detect_capabilities(mock_dev, device)

        assert device.firmware_version == ""

    def test_detect_caps_logo_exception(self, mock_session_bus):
        """Test logo detection handles exception."""
        mock_dev = MagicMock()
        mock_dev.getBrightness.side_effect = Exception("Not supported")
        mock_dev.getLogoBrightness.side_effect = Exception("Not supported")
        mock_dev.getScrollBrightness.side_effect = Exception("Not supported")
        mock_session_bus.get.return_value = mock_dev

        device = RazerDevice(
            serial="TEST123",
            name="Test",
            device_type="mouse",
            object_path="/org/razer/device/TEST123",
        )
        bridge = OpenRazerBridge()
        bridge._detect_capabilities(mock_dev, device)

        assert device.has_logo is False

    def test_detect_caps_scroll_exception(self, mock_session_bus):
        """Test scroll detection handles exception."""
        mock_dev = MagicMock()
        mock_dev.getBrightness.side_effect = Exception("Not supported")
        mock_dev.getLogoBrightness.side_effect = Exception("Not supported")
        mock_dev.getScrollBrightness.side_effect = Exception("Not supported")
        mock_session_bus.get.return_value = mock_dev

        device = RazerDevice(
            serial="TEST123",
            name="Test",
            device_type="mouse",
            object_path="/org/razer/device/TEST123",
        )
        bridge = OpenRazerBridge()
        bridge._detect_capabilities(mock_dev, device)

        assert device.has_scroll is False

    def test_detect_caps_matrix_success(self, mock_session_bus):
        """Test matrix detection when supported (lines 251-255)."""
        mock_dev = MagicMock()
        mock_dev.getBrightness.side_effect = Exception("Not supported")
        mock_dev.getMatrixDimensions.return_value = [6, 22]
        mock_session_bus.get.return_value = mock_dev

        device = RazerDevice(
            serial="TEST123",
            name="Test",
            device_type="keyboard",
            object_path="/org/razer/device/TEST123",
        )
        bridge = OpenRazerBridge()
        bridge._detect_capabilities(mock_dev, device)

        assert device.has_matrix is True
        assert device.matrix_rows == 6
        assert device.matrix_cols == 22

    def test_detect_caps_matrix_exception(self, mock_session_bus):
        """Test matrix detection handles exception (lines 254-255)."""
        mock_dev = MagicMock()
        mock_dev.getBrightness.side_effect = Exception("Not supported")
        mock_dev.getMatrixDimensions.side_effect = Exception("Not supported")
        mock_session_bus.get.return_value = mock_dev

        device = RazerDevice(
            serial="TEST123",
            name="Test",
            device_type="keyboard",
            object_path="/org/razer/device/TEST123",
        )
        bridge = OpenRazerBridge()
        bridge._detect_capabilities(mock_dev, device)

        assert device.has_matrix is False


class TestEffectMethodErrors:
    """Tests for effect method error handling."""

    def test_set_static_color_no_lighting(self, mock_session_bus, sample_device):
        """Test set_static_color returns False without lighting (line 284)."""
        sample_device.has_lighting = False

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = sample_device

        result = bridge.set_static_color("PM1234567890", 255, 0, 0)
        assert result is False

    def test_set_static_color_error(self, mock_session_bus, sample_device, mock_device):
        """Test set_static_color handles error (lines 290-292)."""
        mock_device.setStatic.side_effect = Exception("DBus error")
        mock_session_bus.get.return_value = mock_device

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = sample_device

        result = bridge.set_static_color("PM1234567890", 255, 0, 0)
        assert result is False

    def test_set_dpi_no_capability(self, mock_session_bus, sample_device):
        """Test set_dpi returns False without capability (line 301)."""
        sample_device.has_dpi = False

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = sample_device

        result = bridge.set_dpi("PM1234567890", 1600)
        assert result is False

    def test_set_dpi_error(self, mock_session_bus, sample_device, mock_device):
        """Test set_dpi handles error (lines 308-310)."""
        mock_device.setDPI.side_effect = Exception("DBus error")
        mock_session_bus.get.return_value = mock_device

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = sample_device

        result = bridge.set_dpi("PM1234567890", 1600)
        assert result is False

    def test_set_spectrum_no_lighting(self, mock_session_bus, sample_device):
        """Test set_spectrum_effect returns False without lighting (line 316)."""
        sample_device.has_lighting = False

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = sample_device

        result = bridge.set_spectrum_effect("PM1234567890")
        assert result is False

    def test_set_spectrum_error(self, mock_session_bus, sample_device, mock_device):
        """Test set_spectrum_effect handles error (lines 322-324)."""
        mock_device.setSpectrum.side_effect = Exception("DBus error")
        mock_session_bus.get.return_value = mock_device

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = sample_device

        result = bridge.set_spectrum_effect("PM1234567890")
        assert result is False

    def test_set_breathing_no_lighting(self, mock_session_bus, sample_device):
        """Test set_breathing_effect returns False without lighting (line 330)."""
        sample_device.has_lighting = False

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = sample_device

        result = bridge.set_breathing_effect("PM1234567890", 255, 0, 0)
        assert result is False

    def test_set_breathing_error(self, mock_session_bus, sample_device, mock_device):
        """Test set_breathing_effect handles error (lines 336-338)."""
        mock_device.setBreathSingle.side_effect = Exception("DBus error")
        mock_session_bus.get.return_value = mock_device

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = sample_device

        result = bridge.set_breathing_effect("PM1234567890", 255, 0, 0)
        assert result is False

    def test_set_breathing_dual_no_lighting(self, mock_session_bus, sample_device):
        """Test set_breathing_dual returns False without lighting (line 346)."""
        sample_device.has_lighting = False

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = sample_device

        result = bridge.set_breathing_dual("PM1234567890", 255, 0, 0, 0, 255, 0)
        assert result is False

    def test_set_breathing_dual_error(self, mock_session_bus, sample_device, mock_device):
        """Test set_breathing_dual handles error (lines 352-354)."""
        mock_device.setBreathDual.side_effect = Exception("DBus error")
        mock_session_bus.get.return_value = mock_device

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = sample_device

        result = bridge.set_breathing_dual("PM1234567890", 255, 0, 0, 0, 255, 0)
        assert result is False

    def test_set_breathing_random_no_lighting(self, mock_session_bus, sample_device):
        """Test set_breathing_random returns False without lighting (line 360)."""
        sample_device.has_lighting = False

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = sample_device

        result = bridge.set_breathing_random("PM1234567890")
        assert result is False

    def test_set_breathing_random_error(self, mock_session_bus, sample_device, mock_device):
        """Test set_breathing_random handles error (lines 366-368)."""
        mock_device.setBreathRandom.side_effect = Exception("DBus error")
        mock_session_bus.get.return_value = mock_device

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = sample_device

        result = bridge.set_breathing_random("PM1234567890")
        assert result is False

    def test_set_wave_no_lighting(self, mock_session_bus, sample_device):
        """Test set_wave_effect returns False without lighting (line 374)."""
        sample_device.has_lighting = False

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = sample_device

        result = bridge.set_wave_effect("PM1234567890")
        assert result is False

    def test_set_wave_error(self, mock_session_bus, sample_device, mock_device):
        """Test set_wave_effect handles error (lines 380-382)."""
        mock_device.setWave.side_effect = Exception("DBus error")
        mock_session_bus.get.return_value = mock_device

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = sample_device

        result = bridge.set_wave_effect("PM1234567890")
        assert result is False

    def test_set_reactive_no_lighting(self, mock_session_bus, sample_device):
        """Test set_reactive_effect returns False without lighting (line 390)."""
        sample_device.has_lighting = False

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = sample_device

        result = bridge.set_reactive_effect("PM1234567890", 255, 0, 0)
        assert result is False

    def test_set_reactive_error(self, mock_session_bus, sample_device, mock_device):
        """Test set_reactive_effect handles error (lines 396-398)."""
        mock_device.setReactive.side_effect = Exception("DBus error")
        mock_session_bus.get.return_value = mock_device

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = sample_device

        result = bridge.set_reactive_effect("PM1234567890", 255, 0, 0)
        assert result is False

    def test_set_starlight_no_lighting(self, mock_session_bus, sample_device):
        """Test set_starlight_effect returns False without lighting (line 411)."""
        sample_device.has_lighting = False

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = sample_device

        result = bridge.set_starlight_effect("PM1234567890")
        assert result is False

    def test_set_starlight_error(self, mock_session_bus, sample_device, mock_device):
        """Test set_starlight_effect handles error (lines 417-419)."""
        mock_device.setStarlight.side_effect = Exception("DBus error")
        mock_session_bus.get.return_value = mock_device

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = sample_device

        result = bridge.set_starlight_effect("PM1234567890")
        assert result is False

    def test_set_none_no_lighting(self, mock_session_bus, sample_device):
        """Test set_none_effect returns False without lighting (line 425)."""
        sample_device.has_lighting = False

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = sample_device

        result = bridge.set_none_effect("PM1234567890")
        assert result is False

    def test_set_none_error(self, mock_session_bus, sample_device, mock_device):
        """Test set_none_effect handles error (lines 431-433)."""
        mock_device.setNone.side_effect = Exception("DBus error")
        mock_session_bus.get.return_value = mock_device

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = sample_device

        result = bridge.set_none_effect("PM1234567890")
        assert result is False


class TestPollRateErrors:
    """Tests for poll rate error handling."""

    def test_set_poll_rate_no_capability(self, mock_session_bus, sample_device):
        """Test set_poll_rate returns False without capability (line 439)."""
        sample_device.has_poll_rate = False

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = sample_device

        result = bridge.set_poll_rate("PM1234567890", 500)
        assert result is False

    def test_set_poll_rate_error(self, mock_session_bus, sample_device, mock_device):
        """Test set_poll_rate handles error (lines 450-452)."""
        mock_device.setPollRate.side_effect = Exception("DBus error")
        mock_session_bus.get.return_value = mock_device

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = sample_device

        result = bridge.set_poll_rate("PM1234567890", 500)
        assert result is False

    def test_get_poll_rate_no_capability(self, mock_session_bus, sample_device):
        """Test get_poll_rate returns None without capability (line 458)."""
        sample_device.has_poll_rate = False

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = sample_device

        result = bridge.get_poll_rate("PM1234567890")
        assert result is None

    def test_get_poll_rate_error(self, mock_session_bus, sample_device, mock_device):
        """Test get_poll_rate handles error (lines 465-467)."""
        mock_device.getPollRate.side_effect = Exception("DBus error")
        mock_session_bus.get.return_value = mock_device

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = sample_device

        result = bridge.get_poll_rate("PM1234567890")
        assert result is None

    def test_get_dpi_no_capability(self, mock_session_bus, sample_device):
        """Test get_dpi returns None without capability (line 473)."""
        sample_device.has_dpi = False

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = sample_device

        result = bridge.get_dpi("PM1234567890")
        assert result is None

    def test_get_brightness_no_capability(self, mock_session_bus, sample_device):
        """Test get_brightness returns None without capability (line 488)."""
        sample_device.has_brightness = False

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = sample_device

        result = bridge.get_brightness("PM1234567890")
        assert result is None

    def test_get_brightness_error(self, mock_session_bus, sample_device, mock_device):
        """Test get_brightness handles error (lines 495-497)."""
        mock_device.getBrightness.side_effect = Exception("DBus error")
        mock_session_bus.get.return_value = mock_device

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = sample_device

        result = bridge.get_brightness("PM1234567890")
        assert result is None


class TestBatteryErrors:
    """Tests for battery error handling."""

    def test_get_battery_charging_exception(self, mock_session_bus, mock_device):
        """Test get_battery handles isCharging exception (lines 513-514)."""
        mock_device.getBattery.return_value = 85
        mock_device.isCharging.side_effect = Exception("Not supported")
        mock_session_bus.get.return_value = mock_device

        device = RazerDevice(
            serial="PM1234567890",
            name="Test",
            device_type="mouse",
            object_path="/org/razer/device/PM1234567890",
            has_battery=True,
        )

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = device

        battery = bridge.get_battery("PM1234567890")

        assert battery is not None
        assert battery["level"] == 85
        assert battery["charging"] is False

    def test_get_battery_error(self, mock_session_bus, mock_device):
        """Test get_battery handles error (lines 517-519)."""
        mock_device.getBattery.side_effect = Exception("DBus error")
        mock_session_bus.get.return_value = mock_device

        device = RazerDevice(
            serial="PM1234567890",
            name="Test",
            device_type="mouse",
            object_path="/org/razer/device/PM1234567890",
            has_battery=True,
        )

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = device

        result = bridge.get_battery("PM1234567890")
        assert result is None


class TestLogoScrollErrors:
    """Tests for logo/scroll error handling."""

    def test_set_logo_brightness_no_capability(self, mock_session_bus):
        """Test set_logo_brightness returns False without capability (line 525)."""
        device = RazerDevice(
            serial="PM1234567890",
            name="Test",
            device_type="mouse",
            object_path="/org/razer/device/PM1234567890",
            has_logo=False,
        )

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = device

        result = bridge.set_logo_brightness("PM1234567890", 50)
        assert result is False

    def test_set_logo_brightness_error(self, mock_session_bus, mock_device):
        """Test set_logo_brightness handles error (lines 531-533)."""
        mock_device.setLogoBrightness.side_effect = Exception("DBus error")
        mock_session_bus.get.return_value = mock_device

        device = RazerDevice(
            serial="PM1234567890",
            name="Test",
            device_type="mouse",
            object_path="/org/razer/device/PM1234567890",
            has_logo=True,
        )

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = device

        result = bridge.set_logo_brightness("PM1234567890", 50)
        assert result is False

    def test_set_scroll_brightness_no_capability(self, mock_session_bus):
        """Test set_scroll_brightness returns False without capability (line 539)."""
        device = RazerDevice(
            serial="PM1234567890",
            name="Test",
            device_type="mouse",
            object_path="/org/razer/device/PM1234567890",
            has_scroll=False,
        )

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = device

        result = bridge.set_scroll_brightness("PM1234567890", 50)
        assert result is False

    def test_set_scroll_brightness_error(self, mock_session_bus, mock_device):
        """Test set_scroll_brightness handles error (lines 545-547)."""
        mock_device.setScrollBrightness.side_effect = Exception("DBus error")
        mock_session_bus.get.return_value = mock_device

        device = RazerDevice(
            serial="PM1234567890",
            name="Test",
            device_type="mouse",
            object_path="/org/razer/device/PM1234567890",
            has_scroll=True,
        )

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = device

        result = bridge.set_scroll_brightness("PM1234567890", 50)
        assert result is False

    def test_set_logo_static_no_capability(self, mock_session_bus):
        """Test set_logo_static returns False without capability (line 553)."""
        device = RazerDevice(
            serial="PM1234567890",
            name="Test",
            device_type="mouse",
            object_path="/org/razer/device/PM1234567890",
            has_logo=False,
        )

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = device

        result = bridge.set_logo_static("PM1234567890", 255, 0, 0)
        assert result is False

    def test_set_logo_static_error(self, mock_session_bus, mock_device):
        """Test set_logo_static handles error (lines 559-561)."""
        mock_device.setLogoStatic.side_effect = Exception("DBus error")
        mock_session_bus.get.return_value = mock_device

        device = RazerDevice(
            serial="PM1234567890",
            name="Test",
            device_type="mouse",
            object_path="/org/razer/device/PM1234567890",
            has_logo=True,
        )

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = device

        result = bridge.set_logo_static("PM1234567890", 255, 0, 0)
        assert result is False

    def test_set_scroll_static_no_capability(self, mock_session_bus):
        """Test set_scroll_static returns False without capability (line 567)."""
        device = RazerDevice(
            serial="PM1234567890",
            name="Test",
            device_type="mouse",
            object_path="/org/razer/device/PM1234567890",
            has_scroll=False,
        )

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = device

        result = bridge.set_scroll_static("PM1234567890", 255, 0, 0)
        assert result is False

    def test_set_scroll_static_error(self, mock_session_bus, mock_device):
        """Test set_scroll_static handles error (lines 573-575)."""
        mock_device.setScrollStatic.side_effect = Exception("DBus error")
        mock_session_bus.get.return_value = mock_device

        device = RazerDevice(
            serial="PM1234567890",
            name="Test",
            device_type="mouse",
            object_path="/org/razer/device/PM1234567890",
            has_scroll=True,
        )

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = device

        result = bridge.set_scroll_static("PM1234567890", 255, 0, 0)
        assert result is False


class TestMatrixMethods:
    """Tests for per-key RGB matrix methods."""

    @pytest.fixture
    def matrix_device(self):
        """Create a device with matrix support."""
        return RazerDevice(
            serial="PM1234567890",
            name="Test Keyboard",
            device_type="keyboard",
            object_path="/org/razer/device/PM1234567890",
            has_matrix=True,
            matrix_rows=6,
            matrix_cols=22,
        )

    def test_set_key_row_no_matrix(self, mock_session_bus):
        """Test set_key_row returns False without matrix (line 591)."""
        device = RazerDevice(
            serial="PM1234567890",
            name="Test",
            device_type="keyboard",
            object_path="/org/razer/device/PM1234567890",
            has_matrix=False,
        )

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = device

        result = bridge.set_key_row("PM1234567890", 0, [(255, 0, 0)])
        assert result is False

    def test_set_key_row_invalid_row(self, mock_session_bus, matrix_device):
        """Test set_key_row returns False for invalid row (lines 594-595)."""
        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = matrix_device

        result = bridge.set_key_row("PM1234567890", -1, [(255, 0, 0)])
        assert result is False

        result = bridge.set_key_row("PM1234567890", 10, [(255, 0, 0)])  # row >= matrix_rows
        assert result is False

    def test_set_key_row_success(self, mock_session_bus, matrix_device, mock_device):
        """Test set_key_row success (lines 597-607)."""
        mock_session_bus.get.return_value = mock_device

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = matrix_device

        colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]
        result = bridge.set_key_row("PM1234567890", 0, colors)

        assert result is True
        mock_device.setKeyRow.assert_called_once()

    def test_set_key_row_error(self, mock_session_bus, matrix_device, mock_device):
        """Test set_key_row handles error (lines 608-610)."""
        mock_device.setKeyRow.side_effect = Exception("DBus error")
        mock_session_bus.get.return_value = mock_device

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = matrix_device

        result = bridge.set_key_row("PM1234567890", 0, [(255, 0, 0)])
        assert result is False

    def test_set_custom_frame_no_matrix(self, mock_session_bus):
        """Test set_custom_frame returns False without matrix (line 618)."""
        device = RazerDevice(
            serial="PM1234567890",
            name="Test",
            device_type="keyboard",
            object_path="/org/razer/device/PM1234567890",
            has_matrix=False,
        )

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = device

        result = bridge.set_custom_frame("PM1234567890")
        assert result is False

    def test_set_custom_frame_success(self, mock_session_bus, matrix_device, mock_device):
        """Test set_custom_frame success (lines 621-624)."""
        mock_session_bus.get.return_value = mock_device

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = matrix_device

        result = bridge.set_custom_frame("PM1234567890")

        assert result is True
        mock_device.setCustom.assert_called_once()

    def test_set_custom_frame_error(self, mock_session_bus, matrix_device, mock_device):
        """Test set_custom_frame handles error (lines 625-627)."""
        mock_device.setCustom.side_effect = Exception("DBus error")
        mock_session_bus.get.return_value = mock_device

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = matrix_device

        result = bridge.set_custom_frame("PM1234567890")
        assert result is False

    def test_set_matrix_colors_no_matrix(self, mock_session_bus):
        """Test set_matrix_colors returns False without matrix (line 642)."""
        device = RazerDevice(
            serial="PM1234567890",
            name="Test",
            device_type="keyboard",
            object_path="/org/razer/device/PM1234567890",
            has_matrix=False,
        )

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = device

        matrix = [[(255, 0, 0)]]
        result = bridge.set_matrix_colors("PM1234567890", matrix)
        assert result is False

    def test_set_matrix_colors_success(self, mock_session_bus, matrix_device, mock_device):
        """Test set_matrix_colors success (lines 646-657)."""
        mock_session_bus.get.return_value = mock_device

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = matrix_device

        # Create a 2x3 matrix (will be padded to device cols)
        matrix = [
            [(255, 0, 0), (0, 255, 0), (0, 0, 255)],
            [(128, 128, 0), (0, 128, 128), (128, 0, 128)],
        ]
        result = bridge.set_matrix_colors("PM1234567890", matrix)

        assert result is True
        assert mock_device.setKeyRow.call_count == 2
        mock_device.setCustom.assert_called_once()

    def test_set_matrix_colors_row_failure(self, mock_session_bus, matrix_device, mock_device):
        """Test set_matrix_colors returns False on row failure (line 654)."""
        # First call succeeds, second fails
        mock_device.setKeyRow.side_effect = [None, Exception("Error")]
        mock_session_bus.get.return_value = mock_device

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = matrix_device

        matrix = [[(255, 0, 0)], [(0, 255, 0)]]
        result = bridge.set_matrix_colors("PM1234567890", matrix)

        assert result is False

    def test_get_matrix_dimensions_no_matrix(self, mock_session_bus):
        """Test get_matrix_dimensions returns None without matrix (lines 666-667)."""
        device = RazerDevice(
            serial="PM1234567890",
            name="Test",
            device_type="keyboard",
            object_path="/org/razer/device/PM1234567890",
            has_matrix=False,
        )

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = device

        result = bridge.get_matrix_dimensions("PM1234567890")
        assert result is None

    def test_get_matrix_dimensions_success(self, mock_session_bus, matrix_device):
        """Test get_matrix_dimensions returns dimensions (line 668)."""
        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = matrix_device

        result = bridge.get_matrix_dimensions("PM1234567890")
        assert result == (6, 22)


class TestRefreshDeviceErrors:
    """Tests for refresh_device error handling."""

    def test_refresh_device_not_found(self, mock_session_bus):
        """Test refresh_device returns None for unknown device (line 674)."""
        daemon = MagicMock()
        daemon.getDevices.return_value = []
        mock_session_bus.get.return_value = daemon

        bridge = OpenRazerBridge()
        result = bridge.refresh_device("UNKNOWN123")

        assert result is None

    def test_refresh_device_error(self, mock_session_bus, sample_device):
        """Test refresh_device handles error (lines 680-682)."""
        mock_session_bus.get.side_effect = Exception("DBus error")

        bridge = OpenRazerBridge()
        bridge._devices["PM1234567890"] = sample_device

        result = bridge.refresh_device("PM1234567890")
        assert result is None


class TestMainFunction:
    """Tests for the main() function."""

    def test_main_connect_failure(self, mock_session_bus, capsys):
        """Test main handles connection failure (lines 689-692)."""
        from services.openrazer_bridge.bridge import main

        mock_session_bus.get.side_effect = Exception("No daemon")

        main()

        captured = capsys.readouterr()
        assert "Failed to connect" in captured.out

    def test_main_no_devices(self, mock_session_bus, capsys):
        """Test main handles no devices (lines 699-701)."""
        from services.openrazer_bridge.bridge import main

        daemon = MagicMock()
        daemon.getDevices.return_value = []
        mock_session_bus.get.return_value = daemon

        main()

        captured = capsys.readouterr()
        assert "No Razer devices found" in captured.out

    def test_main_with_devices(self, mock_session_bus, mock_device, capsys):
        """Test main prints device info (lines 703-719)."""
        from services.openrazer_bridge.bridge import main

        # Set up full device capabilities
        mock_device.getBrightness.return_value = 80
        mock_device.getDPI.return_value = [1600, 1600]
        mock_device.getBattery.return_value = 75
        mock_device.getMatrixDimensions.return_value = [6, 22]

        daemon = MagicMock()
        daemon.getDevices.return_value = ["PM1234567890"]

        def get_side_effect(interface, path):
            if path == "/org/razer":
                return daemon
            return mock_device

        mock_session_bus.get.side_effect = get_side_effect

        main()

        captured = capsys.readouterr()
        assert "Razer DeathAdder V2" in captured.out
        assert "PM1234567890" in captured.out


class TestMainGuard:
    """Tests for __name__ == '__main__' guard."""

    def test_main_guard_via_runpy(self, mock_session_bus):
        """Test __name__ == '__main__' guard (line 723) via runpy."""
        import runpy

        # Set up to avoid actual DBus calls
        daemon = MagicMock()
        daemon.getDevices.return_value = []
        mock_session_bus.get.return_value = daemon

        runpy.run_module("services.openrazer_bridge.bridge", run_name="__main__", alter_sys=True)
