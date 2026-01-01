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
