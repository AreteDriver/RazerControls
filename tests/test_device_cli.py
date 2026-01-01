"""Tests for the device CLI tool."""

import argparse
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest

from tools.device_cli import (
    cmd_brightness,
    cmd_dpi,
    cmd_info,
    cmd_list,
    cmd_poll_rate,
    find_device,
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
            with patch("sys.stdout", new=StringIO()) as mock_out:
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
