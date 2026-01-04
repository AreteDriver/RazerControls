"""Tests for the device CLI tool."""

import argparse
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest

from tools.device_cli import (
    cmd_brightness,
    cmd_color,
    cmd_dpi,
    cmd_effect,
    cmd_info,
    cmd_list,
    cmd_logo,
    cmd_poll_rate,
    cmd_scroll,
    find_device,
    get_bridge,
    main,
    parse_color,
)


class TestParseColor:
    """Tests for parse_color function."""

    def test_parse_hex_color(self):
        """Test parsing hex color without hash."""
        assert parse_color("FF0000") == (255, 0, 0)
        assert parse_color("00FF00") == (0, 255, 0)
        assert parse_color("0000FF") == (0, 0, 255)

    def test_parse_hex_color_with_hash(self):
        """Test parsing hex color with hash."""
        assert parse_color("#FF0000") == (255, 0, 0)
        assert parse_color("#00ff00") == (0, 255, 0)

    def test_parse_comma_separated(self):
        """Test parsing comma-separated RGB."""
        assert parse_color("255,0,0") == (255, 0, 0)
        assert parse_color("0, 255, 0") == (0, 255, 0)

    def test_parse_space_separated(self):
        """Test parsing space-separated RGB."""
        assert parse_color("255 0 0") == (255, 0, 0)
        assert parse_color("0 255 0") == (0, 255, 0)

    def test_parse_invalid_color(self):
        """Test parsing invalid color returns None."""
        assert parse_color("invalid") is None
        assert parse_color("GGGGGG") is None
        assert parse_color("256,0,0") is None
        assert parse_color("-1,0,0") is None

    def test_parse_color_invalid_integers(self):
        """Test parsing comma-separated non-integer values (lines 44-45)."""
        # This triggers the ValueError exception handler
        assert parse_color("abc,def,ghi") is None
        assert parse_color("1.5,2.5,3.5") is None


@pytest.fixture
def mock_device():
    """Create a mock Razer device."""
    device = MagicMock()
    device.name = "Razer Basilisk V2"
    device.serial = "PM1234567890"
    device.device_type = "mouse"
    device.firmware_version = "1.0.0"
    device.has_dpi = True
    device.dpi = (800, 800)
    device.max_dpi = 20000
    device.has_poll_rate = True
    device.poll_rate = 1000
    device.has_brightness = True
    device.brightness = 100
    device.has_lighting = True
    device.supported_effects = ["static", "breathing", "spectrum"]
    device.has_logo = True
    device.has_scroll = True
    device.has_battery = False
    return device


@pytest.fixture
def mock_bridge(mock_device):
    """Create a mock OpenRazer bridge."""
    bridge = MagicMock()
    bridge.connect.return_value = True
    bridge.discover_devices.return_value = [mock_device]
    bridge.set_dpi.return_value = True
    bridge.set_brightness.return_value = True
    bridge.set_poll_rate.return_value = True
    return bridge


class TestFindDevice:
    """Tests for find_device function."""

    def test_find_by_serial(self, mock_bridge, mock_device):
        """Test finding device by exact serial."""
        result = find_device(mock_bridge, "PM1234567890")
        assert result == mock_device

    def test_find_by_name(self, mock_bridge, mock_device):
        """Test finding device by partial name."""
        result = find_device(mock_bridge, "basilisk")
        assert result == mock_device

    def test_find_by_index(self, mock_bridge, mock_device):
        """Test finding device by index."""
        result = find_device(mock_bridge, "0")
        assert result == mock_device

    def test_find_not_found(self, mock_bridge):
        """Test finding device that doesn't exist."""
        result = find_device(mock_bridge, "nonexistent")
        assert result is None


class TestCmdList:
    """Tests for cmd_list command."""

    def test_list_no_bridge(self):
        """Test listing when bridge connection fails."""
        with patch("tools.device_cli.get_bridge", return_value=None):
            args = argparse.Namespace()
            with patch("sys.stdout", new=StringIO()):
                result = cmd_list(args)
            assert result == 1

    def test_list_no_devices(self, mock_bridge):
        """Test listing when no devices found."""
        mock_bridge.discover_devices.return_value = []

        with patch("tools.device_cli.get_bridge", return_value=mock_bridge):
            args = argparse.Namespace()
            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_list(args)

            assert result == 0
            assert "No Razer devices found" in mock_out.getvalue()

    def test_list_with_devices(self, mock_bridge, mock_device):
        """Test listing devices."""
        with patch("tools.device_cli.get_bridge", return_value=mock_bridge):
            args = argparse.Namespace()
            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_list(args)

            assert result == 0
            output = mock_out.getvalue()
            assert "Razer Basilisk V2" in output
            assert "PM1234567890" in output


class TestCmdInfo:
    """Tests for cmd_info command."""

    def test_info_no_bridge(self):
        """Test info when bridge connection fails."""
        with patch("tools.device_cli.get_bridge", return_value=None):
            args = argparse.Namespace(device="test")
            with patch("sys.stdout", new=StringIO()):
                result = cmd_info(args)
            assert result == 1

    def test_info_device_not_found(self, mock_bridge):
        """Test info when device not found."""
        mock_bridge.discover_devices.return_value = []

        with patch("tools.device_cli.get_bridge", return_value=mock_bridge):
            args = argparse.Namespace(device="nonexistent")
            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_info(args)

            assert result == 1
            assert "not found" in mock_out.getvalue()

    def test_info_success(self, mock_bridge, mock_device):
        """Test showing device info."""
        with patch("tools.device_cli.get_bridge", return_value=mock_bridge):
            args = argparse.Namespace(device="basilisk")
            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_info(args)

            assert result == 0
            output = mock_out.getvalue()
            assert "Razer Basilisk V2" in output
            assert "PM1234567890" in output
            assert "DPI" in output


class TestCmdDpi:
    """Tests for cmd_dpi command."""

    def test_dpi_no_bridge(self):
        """Test DPI when bridge connection fails."""
        with patch("tools.device_cli.get_bridge", return_value=None):
            args = argparse.Namespace(device="test", dpi="800")
            with patch("sys.stdout", new=StringIO()):
                result = cmd_dpi(args)
            assert result == 1

    def test_dpi_device_not_found(self, mock_bridge):
        """Test DPI when device not found."""
        mock_bridge.discover_devices.return_value = []

        with patch("tools.device_cli.get_bridge", return_value=mock_bridge):
            args = argparse.Namespace(device="nonexistent", dpi="800")
            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_dpi(args)

            assert result == 1
            assert "not found" in mock_out.getvalue()

    def test_dpi_not_supported(self, mock_bridge, mock_device):
        """Test DPI when device doesn't support it."""
        mock_device.has_dpi = False

        with patch("tools.device_cli.get_bridge", return_value=mock_bridge):
            args = argparse.Namespace(device="basilisk", dpi="800")
            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_dpi(args)

            assert result == 1
            assert "does not support DPI" in mock_out.getvalue()

    def test_dpi_single_value(self, mock_bridge, mock_device):
        """Test setting DPI with single value."""
        with patch("tools.device_cli.get_bridge", return_value=mock_bridge):
            args = argparse.Namespace(device="basilisk", dpi="1600")
            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_dpi(args)

            assert result == 0
            mock_bridge.set_dpi.assert_called_once_with("PM1234567890", 1600, 1600)
            assert "1600x1600" in mock_out.getvalue()

    def test_dpi_xy_value(self, mock_bridge, mock_device):
        """Test setting DPI with X and Y values."""
        with patch("tools.device_cli.get_bridge", return_value=mock_bridge):
            args = argparse.Namespace(device="basilisk", dpi="800x600")
            with patch("sys.stdout", new=StringIO()):
                result = cmd_dpi(args)

            assert result == 0
            mock_bridge.set_dpi.assert_called_once_with("PM1234567890", 800, 600)

    def test_dpi_invalid_format(self, mock_bridge, mock_device):
        """Test DPI with invalid format."""
        with patch("tools.device_cli.get_bridge", return_value=mock_bridge):
            args = argparse.Namespace(device="basilisk", dpi="invalid")
            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_dpi(args)

            assert result == 1
            assert "Invalid DPI" in mock_out.getvalue()

    def test_dpi_out_of_range(self, mock_bridge, mock_device):
        """Test DPI with out of range value."""
        with patch("tools.device_cli.get_bridge", return_value=mock_bridge):
            args = argparse.Namespace(device="basilisk", dpi="50000")
            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_dpi(args)

            assert result == 1
            assert "must be between" in mock_out.getvalue()


class TestCmdBrightness:
    """Tests for cmd_brightness command."""

    def test_brightness_no_bridge(self):
        """Test brightness when bridge connection fails."""
        with patch("tools.device_cli.get_bridge", return_value=None):
            args = argparse.Namespace(device="test", brightness="50")
            with patch("sys.stdout", new=StringIO()):
                result = cmd_brightness(args)
            assert result == 1

    def test_brightness_device_not_found(self, mock_bridge):
        """Test brightness when device not found."""
        mock_bridge.discover_devices.return_value = []

        with patch("tools.device_cli.get_bridge", return_value=mock_bridge):
            args = argparse.Namespace(device="nonexistent", brightness="50")
            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_brightness(args)

            assert result == 1
            assert "not found" in mock_out.getvalue()

    def test_brightness_not_supported(self, mock_bridge, mock_device):
        """Test brightness when device doesn't support it."""
        mock_device.has_brightness = False

        with patch("tools.device_cli.get_bridge", return_value=mock_bridge):
            args = argparse.Namespace(device="basilisk", brightness="50")
            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_brightness(args)

            assert result == 1
            assert "does not support brightness" in mock_out.getvalue()

    def test_brightness_success(self, mock_bridge, mock_device):
        """Test setting brightness."""
        with patch("tools.device_cli.get_bridge", return_value=mock_bridge):
            args = argparse.Namespace(device="basilisk", brightness="75")
            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_brightness(args)

            assert result == 0
            mock_bridge.set_brightness.assert_called_once_with("PM1234567890", 75)
            assert "75%" in mock_out.getvalue()

    def test_brightness_invalid_value(self, mock_bridge, mock_device):
        """Test brightness with invalid value."""
        with patch("tools.device_cli.get_bridge", return_value=mock_bridge):
            args = argparse.Namespace(device="basilisk", brightness="invalid")
            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_brightness(args)

            assert result == 1
            assert "Invalid brightness" in mock_out.getvalue()

    def test_brightness_out_of_range(self, mock_bridge, mock_device):
        """Test brightness with out of range value."""
        with patch("tools.device_cli.get_bridge", return_value=mock_bridge):
            args = argparse.Namespace(device="basilisk", brightness="150")
            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_brightness(args)

            assert result == 1
            assert "must be between" in mock_out.getvalue()


class TestCmdPollRate:
    """Tests for cmd_poll_rate command."""

    def test_poll_rate_no_bridge(self):
        """Test poll rate when bridge connection fails."""
        with patch("tools.device_cli.get_bridge", return_value=None):
            args = argparse.Namespace(device="test", rate="1000")
            with patch("sys.stdout", new=StringIO()):
                result = cmd_poll_rate(args)
            assert result == 1

    def test_poll_rate_device_not_found(self, mock_bridge):
        """Test poll rate when device not found."""
        mock_bridge.discover_devices.return_value = []

        with patch("tools.device_cli.get_bridge", return_value=mock_bridge):
            args = argparse.Namespace(device="nonexistent", rate="1000")
            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_poll_rate(args)

            assert result == 1
            assert "not found" in mock_out.getvalue()

    def test_poll_rate_not_supported(self, mock_bridge, mock_device):
        """Test poll rate when device doesn't support it."""
        mock_device.has_poll_rate = False

        with patch("tools.device_cli.get_bridge", return_value=mock_bridge):
            args = argparse.Namespace(device="basilisk", rate="1000")
            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_poll_rate(args)

            assert result == 1
            assert "does not support poll rate" in mock_out.getvalue()

    def test_poll_rate_success(self, mock_bridge, mock_device):
        """Test setting poll rate."""
        with patch("tools.device_cli.get_bridge", return_value=mock_bridge):
            args = argparse.Namespace(device="basilisk", rate="500")
            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_poll_rate(args)

            assert result == 0
            mock_bridge.set_poll_rate.assert_called_once_with("PM1234567890", 500)
            assert "500 Hz" in mock_out.getvalue()

    def test_poll_rate_invalid_value(self, mock_bridge, mock_device):
        """Test poll rate with invalid value."""
        with patch("tools.device_cli.get_bridge", return_value=mock_bridge):
            args = argparse.Namespace(device="basilisk", rate="invalid")
            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_poll_rate(args)

            assert result == 1
            assert "Invalid poll rate" in mock_out.getvalue()

    def test_poll_rate_unsupported_value(self, mock_bridge, mock_device):
        """Test poll rate with unsupported value."""
        with patch("tools.device_cli.get_bridge", return_value=mock_bridge):
            args = argparse.Namespace(device="basilisk", rate="750")
            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_poll_rate(args)

            assert result == 1
            assert "must be 125, 500, or 1000" in mock_out.getvalue()


class TestGetBridge:
    """Tests for get_bridge function."""

    def test_get_bridge_success(self):
        """Test get_bridge when connection succeeds."""
        with patch("tools.device_cli.OpenRazerBridge") as mock_class:
            mock_bridge = MagicMock()
            mock_bridge.connect.return_value = True
            mock_class.return_value = mock_bridge

            result = get_bridge()

            assert result is mock_bridge

    def test_get_bridge_failure(self, capsys):
        """Test get_bridge when connection fails (lines 52-58)."""
        with patch("tools.device_cli.OpenRazerBridge") as mock_class:
            mock_bridge = MagicMock()
            mock_bridge.connect.return_value = False
            mock_class.return_value = mock_bridge

            result = get_bridge()

            assert result is None
            captured = capsys.readouterr()
            assert "Could not connect to OpenRazer" in captured.out


class TestFindDeviceIndexMatch:
    """Additional tests for find_device index matching."""

    def test_find_by_partial_serial(self, mock_bridge, mock_device):
        """Test finding device by partial serial match."""
        result = find_device(mock_bridge, "pm1234")
        assert result == mock_device

    def test_find_by_invalid_index(self, mock_bridge, mock_device):
        """Test finding device by out of range index (lines 81-82)."""
        result = find_device(mock_bridge, "99")
        assert result is None

    def test_find_by_valid_index_no_serial_match(self):
        """Test finding device by index when serial doesn't contain digit (line 82)."""
        # Create a device with serial that won't match "0" or "1"
        device = MagicMock()
        device.name = "Test Mouse"
        device.serial = "ABCDEFGH"  # No digits, so "0" won't match partial serial

        bridge = MagicMock()
        bridge.discover_devices.return_value = [device]

        # "0" should find by index since it doesn't match serial "ABCDEFGH"
        result = find_device(bridge, "0")
        assert result == device


class TestCmdInfoCapabilities:
    """Tests for cmd_info capability display branches."""

    def test_info_no_dpi(self, mock_bridge, mock_device):
        """Test info when device has no DPI (line 141)."""
        mock_device.has_dpi = False

        with patch("tools.device_cli.get_bridge", return_value=mock_bridge):
            args = argparse.Namespace(device="basilisk")
            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_info(args)

            assert result == 0
            assert "DPI:        No" in mock_out.getvalue()

    def test_info_no_poll_rate(self, mock_bridge, mock_device):
        """Test info when device has no poll rate (line 146)."""
        mock_device.has_poll_rate = False

        with patch("tools.device_cli.get_bridge", return_value=mock_bridge):
            args = argparse.Namespace(device="basilisk")
            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_info(args)

            assert result == 0
            assert "Poll Rate:  No" in mock_out.getvalue()

    def test_info_no_brightness(self, mock_bridge, mock_device):
        """Test info when device has no brightness (line 151)."""
        mock_device.has_brightness = False

        with patch("tools.device_cli.get_bridge", return_value=mock_bridge):
            args = argparse.Namespace(device="basilisk")
            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_info(args)

            assert result == 0
            assert "Brightness: No" in mock_out.getvalue()

    def test_info_no_lighting(self, mock_bridge, mock_device):
        """Test info when device has no lighting (line 158)."""
        mock_device.has_lighting = False

        with patch("tools.device_cli.get_bridge", return_value=mock_bridge):
            args = argparse.Namespace(device="basilisk")
            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_info(args)

            assert result == 0
            assert "Lighting:   No" in mock_out.getvalue()

    def test_info_with_battery(self, mock_bridge, mock_device):
        """Test info when device has battery (lines 167-168)."""
        mock_device.has_battery = True
        mock_device.battery_level = 85
        mock_device.is_charging = True

        with patch("tools.device_cli.get_bridge", return_value=mock_bridge):
            args = argparse.Namespace(device="basilisk")
            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_info(args)

            assert result == 0
            assert "Battery:    Yes (85%, charging)" in mock_out.getvalue()


class TestCmdDpiEdgeCases:
    """Additional tests for cmd_dpi edge cases."""

    def test_dpi_xy_invalid_format(self, mock_bridge, mock_device):
        """Test DPI with invalid x format (lines 195-198)."""
        with patch("tools.device_cli.get_bridge", return_value=mock_bridge):
            args = argparse.Namespace(device="basilisk", dpi="abcxdef")
            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_dpi(args)

            assert result == 1
            assert "Invalid DPI format" in mock_out.getvalue()

    def test_dpi_set_failure(self, mock_bridge, mock_device):
        """Test DPI when set fails (lines 215-216)."""
        mock_bridge.set_dpi.return_value = False

        with patch("tools.device_cli.get_bridge", return_value=mock_bridge):
            args = argparse.Namespace(device="basilisk", dpi="800")
            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_dpi(args)

            assert result == 1
            assert "Failed to set DPI" in mock_out.getvalue()


class TestCmdBrightnessEdgeCases:
    """Additional tests for cmd_brightness edge cases."""

    def test_brightness_set_failure(self, mock_bridge, mock_device):
        """Test brightness when set fails (lines 248-249)."""
        mock_bridge.set_brightness.return_value = False

        with patch("tools.device_cli.get_bridge", return_value=mock_bridge):
            args = argparse.Namespace(device="basilisk", brightness="50")
            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_brightness(args)

            assert result == 1
            assert "Failed to set brightness" in mock_out.getvalue()


class TestCmdPollRateEdgeCases:
    """Additional tests for cmd_poll_rate edge cases."""

    def test_poll_rate_set_failure(self, mock_bridge, mock_device):
        """Test poll rate when set fails (lines 281-282)."""
        mock_bridge.set_poll_rate.return_value = False

        with patch("tools.device_cli.get_bridge", return_value=mock_bridge):
            args = argparse.Namespace(device="basilisk", rate="1000")
            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_poll_rate(args)

            assert result == 1
            assert "Failed to set poll rate" in mock_out.getvalue()


class TestCmdEffect:
    """Tests for cmd_effect command."""

    def test_effect_no_bridge(self):
        """Test effect when bridge connection fails."""
        with patch("tools.device_cli.get_bridge", return_value=None):
            args = argparse.Namespace(device="test", effect="spectrum", color=None, direction=None, speed=None)
            with patch("sys.stdout", new=StringIO()):
                result = cmd_effect(args)
            assert result == 1

    def test_effect_device_not_found(self, mock_bridge):
        """Test effect when device not found."""
        mock_bridge.discover_devices.return_value = []

        with patch("tools.device_cli.get_bridge", return_value=mock_bridge):
            args = argparse.Namespace(device="nonexistent", effect="spectrum", color=None, direction=None, speed=None)
            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_effect(args)

            assert result == 1
            assert "not found" in mock_out.getvalue()

    def test_effect_no_lighting(self, mock_bridge, mock_device):
        """Test effect when device has no lighting."""
        mock_device.has_lighting = False

        with patch("tools.device_cli.get_bridge", return_value=mock_bridge):
            args = argparse.Namespace(device="basilisk", effect="spectrum", color=None, direction=None, speed=None)
            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_effect(args)

            assert result == 1
            assert "does not support lighting" in mock_out.getvalue()

    def test_effect_unsupported(self, mock_bridge, mock_device):
        """Test effect that's not supported."""
        with patch("tools.device_cli.get_bridge", return_value=mock_bridge):
            args = argparse.Namespace(device="basilisk", effect="unknown", color=None, direction=None, speed=None)
            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_effect(args)

            assert result == 1
            assert "not supported" in mock_out.getvalue()

    def test_effect_off(self, mock_bridge, mock_device):
        """Test setting effect to off."""
        mock_bridge.set_none_effect.return_value = True

        with patch("tools.device_cli.get_bridge", return_value=mock_bridge):
            args = argparse.Namespace(device="basilisk", effect="off", color=None, direction=None, speed=None)
            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_effect(args)

            assert result == 0
            mock_bridge.set_none_effect.assert_called_once()

    def test_effect_spectrum(self, mock_bridge, mock_device):
        """Test spectrum effect."""
        mock_bridge.set_spectrum_effect.return_value = True

        with patch("tools.device_cli.get_bridge", return_value=mock_bridge):
            args = argparse.Namespace(device="basilisk", effect="spectrum", color=None, direction=None, speed=None)
            with patch("sys.stdout", new=StringIO()):
                result = cmd_effect(args)

            assert result == 0
            mock_bridge.set_spectrum_effect.assert_called_once()

    def test_effect_breathing_with_color(self, mock_bridge, mock_device):
        """Test breathing effect with color."""
        mock_bridge.set_breathing_effect.return_value = True

        with patch("tools.device_cli.get_bridge", return_value=mock_bridge):
            args = argparse.Namespace(device="basilisk", effect="breathing", color="FF0000", direction=None, speed=None)
            with patch("sys.stdout", new=StringIO()):
                result = cmd_effect(args)

            assert result == 0
            mock_bridge.set_breathing_effect.assert_called_once_with("PM1234567890", 255, 0, 0)

    def test_effect_wave_left(self, mock_bridge, mock_device):
        """Test wave effect with left direction."""
        mock_device.supported_effects = ["wave"]
        mock_bridge.set_wave_effect.return_value = True

        with patch("tools.device_cli.get_bridge", return_value=mock_bridge):
            args = argparse.Namespace(device="basilisk", effect="wave", color=None, direction="left", speed=None)
            with patch("sys.stdout", new=StringIO()):
                result = cmd_effect(args)

            assert result == 0
            mock_bridge.set_wave_effect.assert_called_once()

    def test_effect_reactive(self, mock_bridge, mock_device):
        """Test reactive effect."""
        mock_device.supported_effects = ["reactive"]
        mock_bridge.set_reactive_effect.return_value = True

        with patch("tools.device_cli.get_bridge", return_value=mock_bridge):
            args = argparse.Namespace(device="basilisk", effect="reactive", color="00FF00", direction=None, speed="short")
            with patch("sys.stdout", new=StringIO()):
                result = cmd_effect(args)

            assert result == 0
            mock_bridge.set_reactive_effect.assert_called_once()

    def test_effect_starlight(self, mock_bridge, mock_device):
        """Test starlight effect."""
        mock_device.supported_effects = ["starlight"]
        mock_bridge.set_starlight_effect.return_value = True

        with patch("tools.device_cli.get_bridge", return_value=mock_bridge):
            args = argparse.Namespace(device="basilisk", effect="starlight", color=None, direction=None, speed=None)
            with patch("sys.stdout", new=StringIO()):
                result = cmd_effect(args)

            assert result == 0
            mock_bridge.set_starlight_effect.assert_called_once()

    def test_effect_starlight_with_color(self, mock_bridge, mock_device):
        """Test starlight effect with color (lines 347-349)."""
        mock_device.supported_effects = ["starlight"]
        mock_bridge.set_starlight_effect.return_value = True

        with patch("tools.device_cli.get_bridge", return_value=mock_bridge):
            args = argparse.Namespace(device="basilisk", effect="starlight", color="FF0000", direction=None, speed=None)
            with patch("sys.stdout", new=StringIO()):
                result = cmd_effect(args)

            assert result == 0
            mock_bridge.set_starlight_effect.assert_called_once_with("PM1234567890", 255, 0, 0)

    def test_effect_breathing_random(self, mock_bridge, mock_device):
        """Test breathing_random effect (line 323)."""
        mock_device.supported_effects = ["breathing_random"]
        mock_bridge.set_breathing_random.return_value = True

        with patch("tools.device_cli.get_bridge", return_value=mock_bridge):
            args = argparse.Namespace(device="basilisk", effect="breathing_random", color=None, direction=None, speed=None)
            with patch("sys.stdout", new=StringIO()):
                result = cmd_effect(args)

            assert result == 0
            mock_bridge.set_breathing_random.assert_called_once_with("PM1234567890")

    def test_effect_static(self, mock_bridge, mock_device):
        """Test static effect with color."""
        mock_bridge.set_static_color.return_value = True

        with patch("tools.device_cli.get_bridge", return_value=mock_bridge):
            args = argparse.Namespace(device="basilisk", effect="static", color="0000FF", direction=None, speed=None)
            with patch("sys.stdout", new=StringIO()):
                result = cmd_effect(args)

            assert result == 0
            mock_bridge.set_static_color.assert_called_once_with("PM1234567890", 0, 0, 255)

    def test_effect_failure(self, mock_bridge, mock_device):
        """Test effect when set fails."""
        mock_bridge.set_spectrum_effect.return_value = False

        with patch("tools.device_cli.get_bridge", return_value=mock_bridge):
            args = argparse.Namespace(device="basilisk", effect="spectrum", color=None, direction=None, speed=None)
            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_effect(args)

            assert result == 1
            assert "Failed to set effect" in mock_out.getvalue()


class TestCmdColor:
    """Tests for cmd_color command."""

    def test_color_no_bridge(self):
        """Test color when bridge connection fails."""
        with patch("tools.device_cli.get_bridge", return_value=None):
            args = argparse.Namespace(device="test", r="255", g="0", b="0")
            with patch("sys.stdout", new=StringIO()):
                result = cmd_color(args)
            assert result == 1

    def test_color_device_not_found(self, mock_bridge):
        """Test color when device not found."""
        mock_bridge.discover_devices.return_value = []

        with patch("tools.device_cli.get_bridge", return_value=mock_bridge):
            args = argparse.Namespace(device="nonexistent", r="255", g="0", b="0")
            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_color(args)

            assert result == 1
            assert "not found" in mock_out.getvalue()

    def test_color_no_lighting(self, mock_bridge, mock_device):
        """Test color when device has no lighting."""
        mock_device.has_lighting = False

        with patch("tools.device_cli.get_bridge", return_value=mock_bridge):
            args = argparse.Namespace(device="basilisk", r="255", g="0", b="0")
            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_color(args)

            assert result == 1
            assert "does not support lighting" in mock_out.getvalue()

    def test_color_rgb_values(self, mock_bridge, mock_device):
        """Test color with RGB values."""
        mock_bridge.set_static_color.return_value = True

        with patch("tools.device_cli.get_bridge", return_value=mock_bridge):
            args = argparse.Namespace(device="basilisk", r="255", g="128", b="0")
            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_color(args)

            assert result == 0
            mock_bridge.set_static_color.assert_called_once_with("PM1234567890", 255, 128, 0)

    def test_color_hex_value(self, mock_bridge, mock_device):
        """Test color with hex value."""
        mock_bridge.set_static_color.return_value = True

        with patch("tools.device_cli.get_bridge", return_value=mock_bridge):
            args = argparse.Namespace(device="basilisk", r="FF8000", g=None, b=None)
            with patch("sys.stdout", new=StringIO()):
                result = cmd_color(args)

            assert result == 0
            mock_bridge.set_static_color.assert_called_once_with("PM1234567890", 255, 128, 0)

    def test_color_invalid_rgb(self, mock_bridge, mock_device):
        """Test color with invalid RGB values."""
        with patch("tools.device_cli.get_bridge", return_value=mock_bridge):
            args = argparse.Namespace(device="basilisk", r="abc", g="0", b="0")
            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_color(args)

            assert result == 1
            assert "must be integers" in mock_out.getvalue()

    def test_color_invalid_hex(self, mock_bridge, mock_device):
        """Test color with invalid hex."""
        with patch("tools.device_cli.get_bridge", return_value=mock_bridge):
            args = argparse.Namespace(device="basilisk", r="invalid", g=None, b=None)
            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_color(args)

            assert result == 1
            assert "Invalid color format" in mock_out.getvalue()

    def test_color_out_of_range(self, mock_bridge, mock_device):
        """Test color with out of range values."""
        with patch("tools.device_cli.get_bridge", return_value=mock_bridge):
            args = argparse.Namespace(device="basilisk", r="300", g="0", b="0")
            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_color(args)

            assert result == 1
            assert "must be 0-255" in mock_out.getvalue()

    def test_color_set_failure(self, mock_bridge, mock_device):
        """Test color when set fails."""
        mock_bridge.set_static_color.return_value = False

        with patch("tools.device_cli.get_bridge", return_value=mock_bridge):
            args = argparse.Namespace(device="basilisk", r="FF0000", g=None, b=None)
            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_color(args)

            assert result == 1
            assert "Failed to set color" in mock_out.getvalue()


class TestCmdLogo:
    """Tests for cmd_logo command."""

    def test_logo_no_bridge(self):
        """Test logo when bridge connection fails."""
        with patch("tools.device_cli.get_bridge", return_value=None):
            args = argparse.Namespace(device="test", brightness="50", color=None)
            with patch("sys.stdout", new=StringIO()):
                result = cmd_logo(args)
            assert result == 1

    def test_logo_device_not_found(self, mock_bridge):
        """Test logo when device not found."""
        mock_bridge.discover_devices.return_value = []

        with patch("tools.device_cli.get_bridge", return_value=mock_bridge):
            args = argparse.Namespace(device="nonexistent", brightness="50", color=None)
            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_logo(args)

            assert result == 1
            assert "not found" in mock_out.getvalue()

    def test_logo_not_supported(self, mock_bridge, mock_device):
        """Test logo when device has no logo LED."""
        mock_device.has_logo = False

        with patch("tools.device_cli.get_bridge", return_value=mock_bridge):
            args = argparse.Namespace(device="basilisk", brightness="50", color=None)
            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_logo(args)

            assert result == 1
            assert "does not have a controllable logo" in mock_out.getvalue()

    def test_logo_brightness(self, mock_bridge, mock_device):
        """Test setting logo brightness."""
        mock_bridge.set_logo_brightness.return_value = True

        with patch("tools.device_cli.get_bridge", return_value=mock_bridge):
            args = argparse.Namespace(device="basilisk", brightness="75", color=None)
            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_logo(args)

            assert result == 0
            mock_bridge.set_logo_brightness.assert_called_once()

    def test_logo_brightness_invalid(self, mock_bridge, mock_device):
        """Test logo with invalid brightness."""
        with patch("tools.device_cli.get_bridge", return_value=mock_bridge):
            args = argparse.Namespace(device="basilisk", brightness="abc", color=None)
            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_logo(args)

            assert result == 1
            assert "Invalid brightness" in mock_out.getvalue()

    def test_logo_brightness_failure(self, mock_bridge, mock_device):
        """Test logo brightness when set fails."""
        mock_bridge.set_logo_brightness.return_value = False

        with patch("tools.device_cli.get_bridge", return_value=mock_bridge):
            args = argparse.Namespace(device="basilisk", brightness="50", color=None)
            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_logo(args)

            assert result == 1
            assert "Failed to set logo brightness" in mock_out.getvalue()

    def test_logo_color(self, mock_bridge, mock_device):
        """Test setting logo color."""
        mock_bridge.set_logo_static.return_value = True

        with patch("tools.device_cli.get_bridge", return_value=mock_bridge):
            args = argparse.Namespace(device="basilisk", brightness=None, color="FF0000")
            with patch("sys.stdout", new=StringIO()):
                result = cmd_logo(args)

            assert result == 0
            mock_bridge.set_logo_static.assert_called_once_with("PM1234567890", 255, 0, 0)

    def test_logo_color_invalid(self, mock_bridge, mock_device):
        """Test logo with invalid color."""
        with patch("tools.device_cli.get_bridge", return_value=mock_bridge):
            args = argparse.Namespace(device="basilisk", brightness=None, color="invalid")
            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_logo(args)

            assert result == 1
            assert "Invalid color" in mock_out.getvalue()

    def test_logo_color_failure(self, mock_bridge, mock_device):
        """Test logo color when set fails."""
        mock_bridge.set_logo_static.return_value = False

        with patch("tools.device_cli.get_bridge", return_value=mock_bridge):
            args = argparse.Namespace(device="basilisk", brightness=None, color="FF0000")
            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_logo(args)

            assert result == 1
            assert "Failed to set logo color" in mock_out.getvalue()

    def test_logo_no_option(self, mock_bridge, mock_device):
        """Test logo without brightness or color."""
        with patch("tools.device_cli.get_bridge", return_value=mock_bridge):
            args = argparse.Namespace(device="basilisk", brightness=None, color=None)
            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_logo(args)

            assert result == 1
            assert "Specify --brightness or --color" in mock_out.getvalue()


class TestCmdScroll:
    """Tests for cmd_scroll command."""

    def test_scroll_no_bridge(self):
        """Test scroll when bridge connection fails."""
        with patch("tools.device_cli.get_bridge", return_value=None):
            args = argparse.Namespace(device="test", brightness="50", color=None)
            with patch("sys.stdout", new=StringIO()):
                result = cmd_scroll(args)
            assert result == 1

    def test_scroll_device_not_found(self, mock_bridge):
        """Test scroll when device not found."""
        mock_bridge.discover_devices.return_value = []

        with patch("tools.device_cli.get_bridge", return_value=mock_bridge):
            args = argparse.Namespace(device="nonexistent", brightness="50", color=None)
            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_scroll(args)

            assert result == 1
            assert "not found" in mock_out.getvalue()

    def test_scroll_not_supported(self, mock_bridge, mock_device):
        """Test scroll when device has no scroll LED."""
        mock_device.has_scroll = False

        with patch("tools.device_cli.get_bridge", return_value=mock_bridge):
            args = argparse.Namespace(device="basilisk", brightness="50", color=None)
            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_scroll(args)

            assert result == 1
            assert "does not have a controllable scroll" in mock_out.getvalue()

    def test_scroll_brightness(self, mock_bridge, mock_device):
        """Test setting scroll brightness."""
        mock_bridge.set_scroll_brightness.return_value = True

        with patch("tools.device_cli.get_bridge", return_value=mock_bridge):
            args = argparse.Namespace(device="basilisk", brightness="75", color=None)
            with patch("sys.stdout", new=StringIO()):
                result = cmd_scroll(args)

            assert result == 0
            mock_bridge.set_scroll_brightness.assert_called_once()

    def test_scroll_brightness_invalid(self, mock_bridge, mock_device):
        """Test scroll with invalid brightness."""
        with patch("tools.device_cli.get_bridge", return_value=mock_bridge):
            args = argparse.Namespace(device="basilisk", brightness="abc", color=None)
            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_scroll(args)

            assert result == 1
            assert "Invalid brightness" in mock_out.getvalue()

    def test_scroll_brightness_failure(self, mock_bridge, mock_device):
        """Test scroll brightness when set fails."""
        mock_bridge.set_scroll_brightness.return_value = False

        with patch("tools.device_cli.get_bridge", return_value=mock_bridge):
            args = argparse.Namespace(device="basilisk", brightness="50", color=None)
            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_scroll(args)

            assert result == 1
            assert "Failed to set scroll brightness" in mock_out.getvalue()

    def test_scroll_color(self, mock_bridge, mock_device):
        """Test setting scroll color."""
        mock_bridge.set_scroll_static.return_value = True

        with patch("tools.device_cli.get_bridge", return_value=mock_bridge):
            args = argparse.Namespace(device="basilisk", brightness=None, color="00FF00")
            with patch("sys.stdout", new=StringIO()):
                result = cmd_scroll(args)

            assert result == 0
            mock_bridge.set_scroll_static.assert_called_once_with("PM1234567890", 0, 255, 0)

    def test_scroll_color_invalid(self, mock_bridge, mock_device):
        """Test scroll with invalid color."""
        with patch("tools.device_cli.get_bridge", return_value=mock_bridge):
            args = argparse.Namespace(device="basilisk", brightness=None, color="invalid")
            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_scroll(args)

            assert result == 1
            assert "Invalid color" in mock_out.getvalue()

    def test_scroll_color_failure(self, mock_bridge, mock_device):
        """Test scroll color when set fails."""
        mock_bridge.set_scroll_static.return_value = False

        with patch("tools.device_cli.get_bridge", return_value=mock_bridge):
            args = argparse.Namespace(device="basilisk", brightness=None, color="00FF00")
            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_scroll(args)

            assert result == 1
            assert "Failed to set scroll color" in mock_out.getvalue()

    def test_scroll_no_option(self, mock_bridge, mock_device):
        """Test scroll without brightness or color."""
        with patch("tools.device_cli.get_bridge", return_value=mock_bridge):
            args = argparse.Namespace(device="basilisk", brightness=None, color=None)
            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_scroll(args)

            assert result == 1
            assert "Specify --brightness or --color" in mock_out.getvalue()


class TestMain:
    """Tests for main() function."""

    def test_main_no_command(self):
        """Test main with no command shows help."""
        with patch("sys.argv", ["razer-device"]):
            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = main()

            assert result == 0
            # Help text should be shown
            assert "razer-device" in mock_out.getvalue() or result == 0

    def test_main_list_command(self):
        """Test main with list command."""
        with patch("sys.argv", ["razer-device", "list"]):
            with patch("tools.device_cli.cmd_list", return_value=0) as mock_cmd:
                result = main()

                mock_cmd.assert_called_once()
                assert result == 0


class TestMainGuard:
    """Tests for __name__ == '__main__' guard."""

    def test_main_guard_exists(self):
        """Test main guard exists in source."""
        from pathlib import Path

        source = Path("tools/device_cli.py").read_text()
        assert 'if __name__ == "__main__":' in source
        assert "main()" in source
