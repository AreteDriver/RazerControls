"""Tests for RemapDaemon - main daemon orchestration."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from evdev import InputEvent, ecodes

from crates.profile_schema import Binding, Layer, Profile
from services.remap_daemon.daemon import RemapDaemon

# --- Fixtures ---


@pytest.fixture
def mock_profile():
    """Create a mock profile."""
    return Profile(
        id="test",
        name="Test Profile",
        input_devices=["razer_mouse_001"],
        layers=[
            Layer(
                id="base",
                name="Base Layer",
                bindings=[
                    Binding(input_code="BTN_SIDE", output_keys=["A"]),
                ],
            )
        ],
    )


@pytest.fixture
def mock_profile_loader(mock_profile):
    """Create a mock ProfileLoader."""
    loader = MagicMock()
    loader.load_active_profile.return_value = mock_profile
    loader.save_profile = MagicMock()
    loader.set_active_profile = MagicMock()
    return loader


@pytest.fixture
def mock_device_registry():
    """Create a mock DeviceRegistry."""
    registry = MagicMock()
    registry.get_event_path.return_value = "/dev/input/event5"
    registry.get_razer_devices.return_value = []
    registry.scan_devices.return_value = []
    return registry


@pytest.fixture
def mock_input_device():
    """Create a mock InputDevice."""
    device = MagicMock()
    device.name = "Razer Test Mouse"
    device.grab = MagicMock()
    device.ungrab = MagicMock()
    device.read = MagicMock(return_value=[])
    device.fileno = MagicMock(return_value=5)
    return device


@pytest.fixture
def mock_uinput():
    """Create a mock UInput."""
    uinput = MagicMock()
    uinput.name = "Razer Control Center Virtual Device"
    uinput.write = MagicMock()
    uinput.write_event = MagicMock()
    uinput.syn = MagicMock()
    uinput.close = MagicMock()
    return uinput


# --- Test Classes ---


class TestRemapDaemonInit:
    """Tests for RemapDaemon initialization."""

    def test_init_defaults(self):
        """Test default initialization."""
        daemon = RemapDaemon()

        assert daemon.config_dir is None
        assert daemon.engine is None
        assert daemon.uinput is None
        assert daemon.grabbed_devices == {}
        assert daemon.running is False
        assert daemon.enable_app_watcher is False
        assert daemon.app_watcher is None

    def test_init_with_config_dir(self):
        """Test initialization with config directory."""
        config_dir = Path("/tmp/test_config")
        daemon = RemapDaemon(config_dir=config_dir)

        assert daemon.config_dir == config_dir

    def test_init_with_app_watcher(self):
        """Test initialization with app watcher enabled."""
        daemon = RemapDaemon(enable_app_watcher=True)

        assert daemon.enable_app_watcher is True


class TestSetup:
    """Tests for daemon setup."""

    @patch("services.remap_daemon.daemon.UInput")
    @patch("services.remap_daemon.daemon.InputDevice")
    @patch("services.remap_daemon.daemon.ProfileLoader")
    @patch("services.remap_daemon.daemon.DeviceRegistry")
    def test_setup_success(
        self,
        mock_registry_class,
        mock_loader_class,
        mock_input_device_class,
        mock_uinput_class,
        mock_profile,
        mock_profile_loader,
        mock_device_registry,
        mock_input_device,
        mock_uinput,
    ):
        """Test successful setup."""
        mock_loader_class.return_value = mock_profile_loader
        mock_registry_class.return_value = mock_device_registry
        mock_input_device_class.return_value = mock_input_device
        mock_uinput_class.return_value = mock_uinput

        daemon = RemapDaemon()
        result = daemon.setup()

        assert result is True
        assert daemon.engine is not None
        assert daemon.uinput == mock_uinput
        assert "razer_mouse_001" in daemon.grabbed_devices

    @patch("services.remap_daemon.daemon.UInput")
    @patch("services.remap_daemon.daemon.ProfileLoader")
    @patch("services.remap_daemon.daemon.DeviceRegistry")
    def test_setup_creates_default_profile_if_none(
        self,
        mock_registry_class,
        mock_loader_class,
        mock_uinput_class,
        mock_device_registry,
        mock_uinput,
    ):
        """Test setup creates default profile when none exists."""
        mock_loader = MagicMock()
        mock_loader.load_active_profile.return_value = None
        mock_loader_class.return_value = mock_loader

        mock_registry_class.return_value = mock_device_registry
        mock_uinput_class.return_value = mock_uinput

        daemon = RemapDaemon()
        daemon.setup()

        mock_loader.save_profile.assert_called_once()
        mock_loader.set_active_profile.assert_called_once()

    @patch("services.remap_daemon.daemon.UInput")
    @patch("services.remap_daemon.daemon.ProfileLoader")
    @patch("services.remap_daemon.daemon.DeviceRegistry")
    def test_setup_fails_on_uinput_error(
        self,
        mock_registry_class,
        mock_loader_class,
        mock_uinput_class,
        mock_profile_loader,
        mock_device_registry,
    ):
        """Test setup fails when UInput creation fails."""
        mock_loader_class.return_value = mock_profile_loader
        mock_registry_class.return_value = mock_device_registry
        mock_uinput_class.side_effect = PermissionError("No permission")

        daemon = RemapDaemon()
        result = daemon.setup()

        assert result is False


class TestGrabDevices:
    """Tests for device grabbing."""

    @patch("services.remap_daemon.daemon.UInput")
    @patch("services.remap_daemon.daemon.InputDevice")
    @patch("services.remap_daemon.daemon.ProfileLoader")
    @patch("services.remap_daemon.daemon.DeviceRegistry")
    def test_grab_devices_success(
        self,
        mock_registry_class,
        mock_loader_class,
        mock_input_device_class,
        mock_uinput_class,
        mock_profile,
        mock_profile_loader,
        mock_device_registry,
        mock_input_device,
        mock_uinput,
    ):
        """Test successful device grabbing."""
        mock_loader_class.return_value = mock_profile_loader
        mock_registry_class.return_value = mock_device_registry
        mock_input_device_class.return_value = mock_input_device
        mock_uinput_class.return_value = mock_uinput

        daemon = RemapDaemon()
        daemon.setup()

        mock_input_device.grab.assert_called_once()
        assert "razer_mouse_001" in daemon.grabbed_devices

    @patch("services.remap_daemon.daemon.UInput")
    @patch("services.remap_daemon.daemon.InputDevice")
    @patch("services.remap_daemon.daemon.ProfileLoader")
    @patch("services.remap_daemon.daemon.DeviceRegistry")
    def test_grab_devices_permission_denied(
        self,
        mock_registry_class,
        mock_loader_class,
        mock_input_device_class,
        mock_uinput_class,
        mock_profile,
        mock_profile_loader,
        mock_device_registry,
        mock_uinput,
    ):
        """Test handling permission denied on grab."""
        mock_loader_class.return_value = mock_profile_loader
        mock_registry_class.return_value = mock_device_registry
        mock_input_device_class.side_effect = PermissionError("No permission")
        mock_uinput_class.return_value = mock_uinput

        daemon = RemapDaemon()
        result = daemon.setup()

        assert result is False
        assert len(daemon.grabbed_devices) == 0

    @patch("services.remap_daemon.daemon.UInput")
    @patch("services.remap_daemon.daemon.ProfileLoader")
    @patch("services.remap_daemon.daemon.DeviceRegistry")
    def test_grab_devices_device_not_found(
        self,
        mock_registry_class,
        mock_loader_class,
        mock_uinput_class,
        mock_profile_loader,
        mock_uinput,
    ):
        """Test handling device not found."""
        mock_loader_class.return_value = mock_profile_loader

        mock_registry = MagicMock()
        mock_registry.get_event_path.return_value = None  # Device not found
        mock_registry_class.return_value = mock_registry

        mock_uinput_class.return_value = mock_uinput

        daemon = RemapDaemon()
        result = daemon.setup()

        assert result is False

    @patch("services.remap_daemon.daemon.UInput")
    @patch("services.remap_daemon.daemon.ProfileLoader")
    @patch("services.remap_daemon.daemon.DeviceRegistry")
    def test_grab_no_devices_configured(
        self,
        mock_registry_class,
        mock_loader_class,
        mock_uinput_class,
        mock_device_registry,
        mock_uinput,
    ):
        """Test handling no devices in profile."""
        mock_loader = MagicMock()
        mock_loader.load_active_profile.return_value = Profile(
            id="empty",
            name="Empty Profile",
            input_devices=[],  # No devices
            layers=[Layer(id="base", name="Base", bindings=[])],
        )
        mock_loader_class.return_value = mock_loader
        mock_registry_class.return_value = mock_device_registry
        mock_uinput_class.return_value = mock_uinput

        daemon = RemapDaemon()
        result = daemon.setup()

        assert result is False


class TestCleanup:
    """Tests for daemon cleanup."""

    @patch("services.remap_daemon.daemon.UInput")
    @patch("services.remap_daemon.daemon.InputDevice")
    @patch("services.remap_daemon.daemon.ProfileLoader")
    @patch("services.remap_daemon.daemon.DeviceRegistry")
    def test_cleanup_releases_devices(
        self,
        mock_registry_class,
        mock_loader_class,
        mock_input_device_class,
        mock_uinput_class,
        mock_profile,
        mock_profile_loader,
        mock_device_registry,
        mock_input_device,
        mock_uinput,
    ):
        """Test cleanup releases grabbed devices."""
        mock_loader_class.return_value = mock_profile_loader
        mock_registry_class.return_value = mock_device_registry
        mock_input_device_class.return_value = mock_input_device
        mock_uinput_class.return_value = mock_uinput

        daemon = RemapDaemon()
        daemon.setup()
        daemon.cleanup()

        mock_input_device.ungrab.assert_called_once()
        mock_uinput.close.assert_called_once()
        assert len(daemon.grabbed_devices) == 0
        assert daemon.uinput is None

    @patch("services.remap_daemon.daemon.UInput")
    @patch("services.remap_daemon.daemon.InputDevice")
    @patch("services.remap_daemon.daemon.ProfileLoader")
    @patch("services.remap_daemon.daemon.DeviceRegistry")
    def test_cleanup_releases_held_keys(
        self,
        mock_registry_class,
        mock_loader_class,
        mock_input_device_class,
        mock_uinput_class,
        mock_profile,
        mock_profile_loader,
        mock_device_registry,
        mock_input_device,
        mock_uinput,
    ):
        """Test cleanup releases held keys via engine."""
        mock_loader_class.return_value = mock_profile_loader
        mock_registry_class.return_value = mock_device_registry
        mock_input_device_class.return_value = mock_input_device
        mock_uinput_class.return_value = mock_uinput

        daemon = RemapDaemon()
        daemon.setup()

        # Mock release_all_keys
        daemon.engine.release_all_keys = MagicMock()

        daemon.cleanup()

        daemon.engine.release_all_keys.assert_called_once()

    def test_cleanup_handles_no_setup(self):
        """Test cleanup works even without setup."""
        daemon = RemapDaemon()
        # Should not raise
        daemon.cleanup()


class TestPassthroughEvent:
    """Tests for event passthrough."""

    @patch("services.remap_daemon.daemon.UInput")
    @patch("services.remap_daemon.daemon.InputDevice")
    @patch("services.remap_daemon.daemon.ProfileLoader")
    @patch("services.remap_daemon.daemon.DeviceRegistry")
    def test_passthrough_writes_event(
        self,
        mock_registry_class,
        mock_loader_class,
        mock_input_device_class,
        mock_uinput_class,
        mock_profile,
        mock_profile_loader,
        mock_device_registry,
        mock_input_device,
        mock_uinput,
    ):
        """Test passthrough writes event to uinput."""
        mock_loader_class.return_value = mock_profile_loader
        mock_registry_class.return_value = mock_device_registry
        mock_input_device_class.return_value = mock_input_device
        mock_uinput_class.return_value = mock_uinput

        daemon = RemapDaemon()
        daemon.setup()

        # Create a key event
        event = InputEvent(0, 0, ecodes.EV_KEY, ecodes.KEY_Q, 1)
        daemon._passthrough_event(event)

        mock_uinput.write_event.assert_called_with(event)
        mock_uinput.syn.assert_called()

    @patch("services.remap_daemon.daemon.UInput")
    @patch("services.remap_daemon.daemon.InputDevice")
    @patch("services.remap_daemon.daemon.ProfileLoader")
    @patch("services.remap_daemon.daemon.DeviceRegistry")
    def test_passthrough_no_syn_for_syn_event(
        self,
        mock_registry_class,
        mock_loader_class,
        mock_input_device_class,
        mock_uinput_class,
        mock_profile,
        mock_profile_loader,
        mock_device_registry,
        mock_input_device,
        mock_uinput,
    ):
        """Test passthrough doesn't syn for EV_SYN events."""
        mock_loader_class.return_value = mock_profile_loader
        mock_registry_class.return_value = mock_device_registry
        mock_input_device_class.return_value = mock_input_device
        mock_uinput_class.return_value = mock_uinput

        daemon = RemapDaemon()
        daemon.setup()

        # Create a SYN event
        event = InputEvent(0, 0, ecodes.EV_SYN, 0, 0)
        daemon._passthrough_event(event)

        mock_uinput.write_event.assert_called_with(event)
        mock_uinput.syn.assert_not_called()


class TestProfileManagement:
    """Tests for profile reload and switching."""

    @patch("services.remap_daemon.daemon.UInput")
    @patch("services.remap_daemon.daemon.InputDevice")
    @patch("services.remap_daemon.daemon.ProfileLoader")
    @patch("services.remap_daemon.daemon.DeviceRegistry")
    def test_reload_profile(
        self,
        mock_registry_class,
        mock_loader_class,
        mock_input_device_class,
        mock_uinput_class,
        mock_profile,
        mock_profile_loader,
        mock_device_registry,
        mock_input_device,
        mock_uinput,
    ):
        """Test profile reloading."""
        mock_loader_class.return_value = mock_profile_loader
        mock_registry_class.return_value = mock_device_registry
        mock_input_device_class.return_value = mock_input_device
        mock_uinput_class.return_value = mock_uinput

        daemon = RemapDaemon()
        daemon.setup()

        # Mock reload_profile on engine
        daemon.engine.reload_profile = MagicMock()

        daemon.reload_profile()

        mock_profile_loader.load_active_profile.assert_called()
        daemon.engine.reload_profile.assert_called_once()

    @patch("services.remap_daemon.daemon.UInput")
    @patch("services.remap_daemon.daemon.InputDevice")
    @patch("services.remap_daemon.daemon.ProfileLoader")
    @patch("services.remap_daemon.daemon.DeviceRegistry")
    def test_switch_profile(
        self,
        mock_registry_class,
        mock_loader_class,
        mock_input_device_class,
        mock_uinput_class,
        mock_profile,
        mock_profile_loader,
        mock_device_registry,
        mock_input_device,
        mock_uinput,
    ):
        """Test switching to a different profile."""
        mock_loader_class.return_value = mock_profile_loader
        mock_registry_class.return_value = mock_device_registry
        mock_input_device_class.return_value = mock_input_device
        mock_uinput_class.return_value = mock_uinput

        daemon = RemapDaemon()
        daemon.setup()

        # Mock reload_profile on engine
        daemon.engine.reload_profile = MagicMock()

        new_profile = Profile(
            id="new",
            name="New Profile",
            layers=[Layer(id="base", name="Base", bindings=[])],
        )
        daemon.switch_profile(new_profile)

        mock_profile_loader.set_active_profile.assert_called_with("new")
        daemon.engine.reload_profile.assert_called_with(new_profile)

    def test_switch_profile_without_engine(self):
        """Test switch_profile does nothing without engine."""
        daemon = RemapDaemon()
        # Should not raise
        daemon.switch_profile(MagicMock())


class TestAppWatcher:
    """Tests for app watcher integration."""

    @patch("services.remap_daemon.daemon.AppWatcher")
    @patch("services.remap_daemon.daemon.UInput")
    @patch("services.remap_daemon.daemon.InputDevice")
    @patch("services.remap_daemon.daemon.ProfileLoader")
    @patch("services.remap_daemon.daemon.DeviceRegistry")
    def test_start_app_watcher(
        self,
        mock_registry_class,
        mock_loader_class,
        mock_input_device_class,
        mock_uinput_class,
        mock_app_watcher_class,
        mock_profile,
        mock_profile_loader,
        mock_device_registry,
        mock_input_device,
        mock_uinput,
    ):
        """Test starting app watcher."""
        mock_loader_class.return_value = mock_profile_loader
        mock_registry_class.return_value = mock_device_registry
        mock_input_device_class.return_value = mock_input_device
        mock_uinput_class.return_value = mock_uinput

        mock_watcher = MagicMock()
        mock_watcher.start.return_value = True
        mock_watcher.backend_name = "x11"
        mock_app_watcher_class.return_value = mock_watcher

        daemon = RemapDaemon(enable_app_watcher=True)
        daemon.setup()
        daemon._start_app_watcher()

        mock_app_watcher_class.assert_called_once()
        mock_watcher.start.assert_called_once()
        assert daemon.app_watcher == mock_watcher

    @patch("services.remap_daemon.daemon.AppWatcher")
    @patch("services.remap_daemon.daemon.UInput")
    @patch("services.remap_daemon.daemon.InputDevice")
    @patch("services.remap_daemon.daemon.ProfileLoader")
    @patch("services.remap_daemon.daemon.DeviceRegistry")
    def test_stop_app_watcher(
        self,
        mock_registry_class,
        mock_loader_class,
        mock_input_device_class,
        mock_uinput_class,
        mock_app_watcher_class,
        mock_profile,
        mock_profile_loader,
        mock_device_registry,
        mock_input_device,
        mock_uinput,
    ):
        """Test stopping app watcher."""
        mock_loader_class.return_value = mock_profile_loader
        mock_registry_class.return_value = mock_device_registry
        mock_input_device_class.return_value = mock_input_device
        mock_uinput_class.return_value = mock_uinput

        mock_watcher = MagicMock()
        mock_watcher.start.return_value = True
        mock_watcher.backend_name = "x11"
        mock_app_watcher_class.return_value = mock_watcher

        daemon = RemapDaemon(enable_app_watcher=True)
        daemon.setup()
        daemon._start_app_watcher()
        daemon._stop_app_watcher()

        mock_watcher.stop.assert_called_once()
        assert daemon.app_watcher is None

    def test_app_watcher_not_started_when_disabled(self):
        """Test app watcher not started when disabled."""
        daemon = RemapDaemon(enable_app_watcher=False)
        daemon._start_app_watcher()

        assert daemon.app_watcher is None


class TestCreateDefaultProfile:
    """Tests for default profile creation."""

    @patch("services.remap_daemon.daemon.ProfileLoader")
    @patch("services.remap_daemon.daemon.DeviceRegistry")
    def test_creates_valid_profile(
        self,
        mock_registry_class,
        mock_loader_class,
        mock_device_registry,
    ):
        """Test default profile is valid."""
        mock_loader_class.return_value = MagicMock()
        mock_registry_class.return_value = mock_device_registry

        daemon = RemapDaemon()
        profile = daemon._create_default_profile()

        assert profile.id == "default"
        assert profile.name == "Default Profile"
        assert profile.is_default is True
        assert len(profile.layers) == 1
        assert profile.layers[0].id == "base"

    @patch("services.remap_daemon.daemon.ProfileLoader")
    @patch("services.remap_daemon.daemon.DeviceRegistry")
    def test_includes_first_mouse(
        self,
        mock_registry_class,
        mock_loader_class,
    ):
        """Test default profile includes first mouse device."""
        mock_loader_class.return_value = MagicMock()

        mock_mouse = MagicMock()
        mock_mouse.stable_id = "razer_deathadder_001"
        mock_mouse.is_mouse = True

        mock_keyboard = MagicMock()
        mock_keyboard.stable_id = "razer_keyboard_001"
        mock_keyboard.is_mouse = False

        mock_registry = MagicMock()
        mock_registry.get_razer_devices.return_value = [mock_keyboard, mock_mouse]
        mock_registry_class.return_value = mock_registry

        daemon = RemapDaemon()
        profile = daemon._create_default_profile()

        assert profile.input_devices == ["razer_deathadder_001"]


class TestSetupErrorHandling:
    """Tests for error handling during setup."""

    @patch("services.remap_daemon.daemon.UInput")
    @patch("services.remap_daemon.daemon.ProfileLoader")
    @patch("services.remap_daemon.daemon.DeviceRegistry")
    def test_setup_fails_on_oserror(
        self,
        mock_registry_class,
        mock_loader_class,
        mock_uinput_class,
        mock_profile_loader,
        mock_device_registry,
    ):
        """Test setup fails when UInput creation raises OSError (lines 66-69)."""
        mock_loader_class.return_value = mock_profile_loader
        mock_registry_class.return_value = mock_device_registry
        mock_uinput_class.side_effect = OSError("Failed to open uinput")

        daemon = RemapDaemon()
        result = daemon.setup()

        assert result is False


class TestGrabDevicesListRazer:
    """Tests for grab_devices listing Razer devices."""

    @patch("services.remap_daemon.daemon.UInput")
    @patch("services.remap_daemon.daemon.ProfileLoader")
    @patch("services.remap_daemon.daemon.DeviceRegistry")
    def test_lists_available_razer_devices_when_none_configured(
        self,
        mock_registry_class,
        mock_loader_class,
        mock_uinput_class,
        mock_uinput,
    ):
        """Test lists available Razer devices when none configured (lines 101-105)."""
        # Profile with no input devices
        mock_loader = MagicMock()
        mock_loader.load_active_profile.return_value = Profile(
            id="empty",
            name="Empty Profile",
            input_devices=[],
            layers=[Layer(id="base", name="Base", bindings=[])],
        )
        mock_loader_class.return_value = mock_loader

        # Registry has available Razer devices
        mock_razer_device = MagicMock()
        mock_razer_device.stable_id = "usb-razer_mouse-001"
        mock_razer_device.name = "Razer Test Mouse"
        mock_razer_device.event_path = "/dev/input/event5"

        mock_registry = MagicMock()
        mock_registry.scan_devices.return_value = [mock_razer_device]
        mock_registry_class.return_value = mock_registry

        mock_uinput_class.return_value = mock_uinput

        daemon = RemapDaemon()
        result = daemon.setup()

        # Should fail (no devices configured)
        assert result is False
        # Should have scanned for devices
        mock_registry.scan_devices.assert_called_once()


class TestGrabDevicesOSError:
    """Tests for OSError handling during device grab."""

    @patch("services.remap_daemon.daemon.UInput")
    @patch("services.remap_daemon.daemon.InputDevice")
    @patch("services.remap_daemon.daemon.ProfileLoader")
    @patch("services.remap_daemon.daemon.DeviceRegistry")
    def test_grab_device_oserror(
        self,
        mock_registry_class,
        mock_loader_class,
        mock_input_device_class,
        mock_uinput_class,
        mock_profile,
        mock_profile_loader,
        mock_device_registry,
        mock_uinput,
    ):
        """Test handling OSError when grabbing device (lines 125-126)."""
        mock_loader_class.return_value = mock_profile_loader
        mock_registry_class.return_value = mock_device_registry
        mock_uinput_class.return_value = mock_uinput

        # InputDevice constructor succeeds, but grab() raises OSError
        mock_device = MagicMock()
        mock_device.grab.side_effect = OSError("Device busy")
        mock_input_device_class.return_value = mock_device

        daemon = RemapDaemon()
        result = daemon.setup()

        assert result is False
        assert len(daemon.grabbed_devices) == 0


class TestCleanupExceptionHandling:
    """Tests for exception handling during cleanup."""

    @patch("services.remap_daemon.daemon.UInput")
    @patch("services.remap_daemon.daemon.InputDevice")
    @patch("services.remap_daemon.daemon.ProfileLoader")
    @patch("services.remap_daemon.daemon.DeviceRegistry")
    def test_cleanup_handles_ungrab_oserror(
        self,
        mock_registry_class,
        mock_loader_class,
        mock_input_device_class,
        mock_uinput_class,
        mock_profile,
        mock_profile_loader,
        mock_device_registry,
        mock_uinput,
    ):
        """Test cleanup handles OSError when ungrabbing (lines 190-191)."""
        mock_loader_class.return_value = mock_profile_loader
        mock_registry_class.return_value = mock_device_registry
        mock_uinput_class.return_value = mock_uinput

        mock_device = MagicMock()
        mock_device.name = "Test Device"
        mock_device.fileno.return_value = 5
        mock_device.ungrab.side_effect = OSError("Device not grabbed")
        mock_input_device_class.return_value = mock_device

        daemon = RemapDaemon()
        daemon.setup()
        # Should not raise
        daemon.cleanup()
        assert len(daemon.grabbed_devices) == 0

    @patch("services.remap_daemon.daemon.UInput")
    @patch("services.remap_daemon.daemon.InputDevice")
    @patch("services.remap_daemon.daemon.ProfileLoader")
    @patch("services.remap_daemon.daemon.DeviceRegistry")
    def test_cleanup_handles_unregister_keyerror(
        self,
        mock_registry_class,
        mock_loader_class,
        mock_input_device_class,
        mock_uinput_class,
        mock_profile,
        mock_profile_loader,
        mock_device_registry,
        mock_uinput,
    ):
        """Test cleanup handles KeyError when unregistering (lines 194-195)."""
        mock_loader_class.return_value = mock_profile_loader
        mock_registry_class.return_value = mock_device_registry
        mock_uinput_class.return_value = mock_uinput

        mock_device = MagicMock()
        mock_device.name = "Test Device"
        mock_device.fileno.return_value = 5
        mock_input_device_class.return_value = mock_device

        daemon = RemapDaemon()
        daemon.setup()
        # Manually unregister to trigger KeyError on cleanup
        daemon.selector.unregister(mock_device)
        # Should not raise
        daemon.cleanup()
        assert len(daemon.grabbed_devices) == 0

    @patch("services.remap_daemon.daemon.UInput")
    @patch("services.remap_daemon.daemon.InputDevice")
    @patch("services.remap_daemon.daemon.ProfileLoader")
    @patch("services.remap_daemon.daemon.DeviceRegistry")
    def test_cleanup_handles_uinput_close_oserror(
        self,
        mock_registry_class,
        mock_loader_class,
        mock_input_device_class,
        mock_uinput_class,
        mock_profile,
        mock_profile_loader,
        mock_device_registry,
    ):
        """Test cleanup handles OSError when closing uinput (lines 203-204)."""
        mock_loader_class.return_value = mock_profile_loader
        mock_registry_class.return_value = mock_device_registry

        mock_uinput = MagicMock()
        mock_uinput.name = "Test UInput"
        mock_uinput.close.side_effect = OSError("Already closed")
        mock_uinput_class.return_value = mock_uinput

        mock_device = MagicMock()
        mock_device.name = "Test Device"
        mock_device.fileno.return_value = 5
        mock_input_device_class.return_value = mock_device

        daemon = RemapDaemon()
        daemon.setup()
        # Should not raise
        daemon.cleanup()
        assert daemon.uinput is None


class TestAppWatcherFailure:
    """Tests for app watcher failure to start."""

    @patch("services.remap_daemon.daemon.AppWatcher")
    @patch("services.remap_daemon.daemon.UInput")
    @patch("services.remap_daemon.daemon.InputDevice")
    @patch("services.remap_daemon.daemon.ProfileLoader")
    @patch("services.remap_daemon.daemon.DeviceRegistry")
    def test_app_watcher_fails_to_start(
        self,
        mock_registry_class,
        mock_loader_class,
        mock_input_device_class,
        mock_uinput_class,
        mock_app_watcher_class,
        mock_profile,
        mock_profile_loader,
        mock_device_registry,
        mock_input_device,
        mock_uinput,
    ):
        """Test handling when app watcher fails to start (lines 239-240)."""
        mock_loader_class.return_value = mock_profile_loader
        mock_registry_class.return_value = mock_device_registry
        mock_input_device_class.return_value = mock_input_device
        mock_uinput_class.return_value = mock_uinput

        mock_watcher = MagicMock()
        mock_watcher.start.return_value = False  # Fails to start
        mock_app_watcher_class.return_value = mock_watcher

        daemon = RemapDaemon(enable_app_watcher=True)
        daemon.setup()
        daemon._start_app_watcher()

        mock_watcher.start.assert_called_once()
        assert daemon.app_watcher is None  # Should be set to None on failure


class TestRunMethod:
    """Tests for the run() method and main loop."""

    @patch("services.remap_daemon.daemon.UInput")
    @patch("services.remap_daemon.daemon.InputDevice")
    @patch("services.remap_daemon.daemon.ProfileLoader")
    @patch("services.remap_daemon.daemon.DeviceRegistry")
    def test_run_without_setup(
        self,
        mock_registry_class,
        mock_loader_class,
        mock_input_device_class,
        mock_uinput_class,
    ):
        """Test run returns early without proper setup (lines 132-134)."""
        daemon = RemapDaemon()
        # Should return without error when not set up
        daemon.run()
        assert daemon.running is False

    @patch("services.remap_daemon.daemon.signal")
    @patch("services.remap_daemon.daemon.UInput")
    @patch("services.remap_daemon.daemon.InputDevice")
    @patch("services.remap_daemon.daemon.ProfileLoader")
    @patch("services.remap_daemon.daemon.DeviceRegistry")
    def test_run_processes_events(
        self,
        mock_registry_class,
        mock_loader_class,
        mock_input_device_class,
        mock_uinput_class,
        mock_signal,
        mock_profile,
        mock_profile_loader,
        mock_device_registry,
        mock_uinput,
    ):
        """Test run processes events from devices (lines 151-165)."""
        mock_loader_class.return_value = mock_profile_loader
        mock_registry_class.return_value = mock_device_registry
        mock_uinput_class.return_value = mock_uinput

        # Create mock device with events
        key_event = InputEvent(0, 0, ecodes.EV_KEY, ecodes.KEY_A, 1)
        mock_device = MagicMock()
        mock_device.name = "Test Device"
        mock_device.fileno.return_value = 5
        mock_device.read.return_value = [key_event]
        mock_input_device_class.return_value = mock_device

        daemon = RemapDaemon()
        daemon.setup()

        # Simulate selector returning events once, then stopping
        call_count = [0]

        def mock_select(timeout):
            call_count[0] += 1
            if call_count[0] == 1:
                mock_key = MagicMock()
                mock_key.fileobj = mock_device
                return [(mock_key, None)]
            else:
                daemon.running = False
                return []

        daemon.selector.select = mock_select
        daemon.run()

        mock_device.read.assert_called()

    @patch("services.remap_daemon.daemon.signal")
    @patch("services.remap_daemon.daemon.UInput")
    @patch("services.remap_daemon.daemon.InputDevice")
    @patch("services.remap_daemon.daemon.ProfileLoader")
    @patch("services.remap_daemon.daemon.DeviceRegistry")
    def test_run_handles_read_oserror(
        self,
        mock_registry_class,
        mock_loader_class,
        mock_input_device_class,
        mock_uinput_class,
        mock_signal,
        mock_profile,
        mock_profile_loader,
        mock_device_registry,
        mock_uinput,
    ):
        """Test run handles OSError during device read (lines 162-163)."""
        mock_loader_class.return_value = mock_profile_loader
        mock_registry_class.return_value = mock_device_registry
        mock_uinput_class.return_value = mock_uinput

        # Create mock device that raises OSError on read
        mock_device = MagicMock()
        mock_device.name = "Test Device"
        mock_device.fileno.return_value = 5
        mock_device.read.side_effect = OSError("Device disconnected")
        mock_input_device_class.return_value = mock_device

        daemon = RemapDaemon()
        daemon.setup()

        # Simulate selector returning events once, then stopping
        call_count = [0]

        def mock_select(timeout):
            call_count[0] += 1
            if call_count[0] == 1:
                mock_key = MagicMock()
                mock_key.fileobj = mock_device
                return [(mock_key, None)]
            else:
                daemon.running = False
                return []

        daemon.selector.select = mock_select
        # Should not raise
        daemon.run()

    @patch("services.remap_daemon.daemon.signal")
    @patch("services.remap_daemon.daemon.UInput")
    @patch("services.remap_daemon.daemon.InputDevice")
    @patch("services.remap_daemon.daemon.ProfileLoader")
    @patch("services.remap_daemon.daemon.DeviceRegistry")
    def test_run_signal_handler(
        self,
        mock_registry_class,
        mock_loader_class,
        mock_input_device_class,
        mock_uinput_class,
        mock_signal,
        mock_profile,
        mock_profile_loader,
        mock_device_registry,
        mock_uinput,
    ):
        """Test signal handler stops the daemon (lines 137-139, 141-142)."""
        mock_loader_class.return_value = mock_profile_loader
        mock_registry_class.return_value = mock_device_registry
        mock_uinput_class.return_value = mock_uinput

        mock_device = MagicMock()
        mock_device.name = "Test Device"
        mock_device.fileno.return_value = 5
        mock_input_device_class.return_value = mock_device

        daemon = RemapDaemon()
        daemon.setup()

        # Capture the signal handler
        handler = None

        def capture_handler(sig, func):
            nonlocal handler
            if sig == 2:  # SIGINT
                handler = func

        mock_signal.signal.side_effect = capture_handler
        mock_signal.SIGINT = 2
        mock_signal.SIGTERM = 15

        # Run with a select that triggers the handler
        call_count = [0]

        def mock_select(timeout):
            nonlocal handler
            call_count[0] += 1
            if call_count[0] == 1 and handler:
                handler(2, None)  # Simulate SIGINT
            return []

        daemon.selector.select = mock_select
        daemon.run()

        assert daemon.running is False

    @patch("services.remap_daemon.daemon.signal")
    @patch("services.remap_daemon.daemon.UInput")
    @patch("services.remap_daemon.daemon.InputDevice")
    @patch("services.remap_daemon.daemon.ProfileLoader")
    @patch("services.remap_daemon.daemon.DeviceRegistry")
    def test_run_passthrough_unhandled_events(
        self,
        mock_registry_class,
        mock_loader_class,
        mock_input_device_class,
        mock_uinput_class,
        mock_signal,
        mock_profile_loader,
        mock_device_registry,
        mock_uinput,
    ):
        """Test run passes through unhandled events (lines 159-161)."""
        # Use profile with no bindings so events are unhandled
        mock_loader = MagicMock()
        mock_loader.load_active_profile.return_value = Profile(
            id="test",
            name="Test",
            input_devices=["razer_mouse_001"],
            layers=[Layer(id="base", name="Base", bindings=[])],
        )
        mock_loader_class.return_value = mock_loader
        mock_registry_class.return_value = mock_device_registry
        mock_uinput_class.return_value = mock_uinput

        # Create mock device with an event that won't be handled
        rel_event = InputEvent(0, 0, ecodes.EV_REL, ecodes.REL_X, 10)
        mock_device = MagicMock()
        mock_device.name = "Test Device"
        mock_device.fileno.return_value = 5
        mock_device.read.return_value = [rel_event]
        mock_input_device_class.return_value = mock_device

        daemon = RemapDaemon()
        daemon.setup()

        call_count = [0]

        def mock_select(timeout):
            call_count[0] += 1
            if call_count[0] == 1:
                mock_key = MagicMock()
                mock_key.fileobj = mock_device
                return [(mock_key, None)]
            else:
                daemon.running = False
                return []

        daemon.selector.select = mock_select
        daemon.run()

        # Unhandled event should be passed through
        mock_uinput.write_event.assert_called()


class TestMainFunction:
    """Tests for the main() entry point."""

    @patch("services.remap_daemon.daemon.DeviceRegistry")
    @patch("services.remap_daemon.daemon.logging")
    @patch("sys.argv", ["remap-daemon", "--list-devices"])
    def test_main_list_devices(self, mock_logging, mock_registry_class, capsys):
        """Test main with --list-devices flag (lines 285-302)."""
        from services.remap_daemon.daemon import main

        mock_device = MagicMock()
        mock_device.stable_id = "usb-razer_mouse-001"
        mock_device.name = "Razer Test Mouse"
        mock_device.event_path = "/dev/input/event5"
        mock_device.is_mouse = True
        mock_device.is_keyboard = False

        mock_registry = MagicMock()
        mock_registry.scan_devices.return_value = [mock_device]
        mock_registry_class.return_value = mock_registry

        main()

        captured = capsys.readouterr()
        assert "usb-razer_mouse-001" in captured.out
        assert "Razer Test Mouse" in captured.out
        assert "mouse" in captured.out

    @patch("services.remap_daemon.daemon.DeviceRegistry")
    @patch("services.remap_daemon.daemon.logging")
    @patch("sys.argv", ["remap-daemon", "--list-devices"])
    def test_main_list_devices_keyboard(self, mock_logging, mock_registry_class, capsys):
        """Test main with --list-devices shows keyboard type."""
        from services.remap_daemon.daemon import main

        mock_device = MagicMock()
        mock_device.stable_id = "usb-razer_kbd-001"
        mock_device.name = "Razer Keyboard"
        mock_device.event_path = "/dev/input/event6"
        mock_device.is_mouse = False
        mock_device.is_keyboard = True

        mock_registry = MagicMock()
        mock_registry.scan_devices.return_value = [mock_device]
        mock_registry_class.return_value = mock_registry

        main()

        captured = capsys.readouterr()
        assert "keyboard" in captured.out

    @patch("services.remap_daemon.daemon.DeviceRegistry")
    @patch("services.remap_daemon.daemon.logging")
    @patch("sys.argv", ["remap-daemon", "--list-devices"])
    def test_main_list_devices_other_type(self, mock_logging, mock_registry_class, capsys):
        """Test main with --list-devices shows 'other' for unknown device type."""
        from services.remap_daemon.daemon import main

        mock_device = MagicMock()
        mock_device.stable_id = "usb-razer_other-001"
        mock_device.name = "Razer Unknown"
        mock_device.event_path = "/dev/input/event7"
        mock_device.is_mouse = False
        mock_device.is_keyboard = False

        mock_registry = MagicMock()
        mock_registry.scan_devices.return_value = [mock_device]
        mock_registry_class.return_value = mock_registry

        main()

        captured = capsys.readouterr()
        assert "other" in captured.out

    @patch("services.remap_daemon.daemon.RemapDaemon")
    @patch("services.remap_daemon.daemon.logging")
    @patch("sys.exit")
    @patch("sys.argv", ["remap-daemon"])
    def test_main_setup_failure_exits(self, mock_exit, mock_logging, mock_daemon_class):
        """Test main exits with code 1 on setup failure (lines 306-308)."""
        from services.remap_daemon.daemon import main

        mock_daemon = MagicMock()
        mock_daemon.setup.return_value = False
        mock_daemon_class.return_value = mock_daemon

        main()

        mock_exit.assert_called_with(1)

    @patch("services.remap_daemon.daemon.RemapDaemon")
    @patch("services.remap_daemon.daemon.logging")
    @patch("sys.argv", ["remap-daemon"])
    def test_main_runs_daemon(self, mock_logging, mock_daemon_class):
        """Test main runs daemon on successful setup (lines 304, 310)."""
        from services.remap_daemon.daemon import main

        mock_daemon = MagicMock()
        mock_daemon.setup.return_value = True
        mock_daemon_class.return_value = mock_daemon

        main()

        mock_daemon.setup.assert_called_once()
        mock_daemon.run.assert_called_once()

    @patch("services.remap_daemon.daemon.RemapDaemon")
    @patch("services.remap_daemon.daemon.logging")
    @patch("sys.argv", ["remap-daemon", "--verbose"])
    def test_main_verbose_flag(self, mock_logging, mock_daemon_class):
        """Test main with --verbose flag sets debug logging (line 278)."""
        from services.remap_daemon.daemon import main

        mock_daemon = MagicMock()
        mock_daemon.setup.return_value = True
        mock_daemon_class.return_value = mock_daemon

        main()

        # Should configure logging with DEBUG level
        mock_logging.basicConfig.assert_called_once()
        call_kwargs = mock_logging.basicConfig.call_args[1]
        assert call_kwargs["level"] == mock_logging.DEBUG

    @patch("services.remap_daemon.daemon.RemapDaemon")
    @patch("services.remap_daemon.daemon.logging")
    @patch("sys.argv", ["remap-daemon", "--app-watcher"])
    def test_main_app_watcher_flag(self, mock_logging, mock_daemon_class):
        """Test main with --app-watcher flag (lines 264-268)."""
        from services.remap_daemon.daemon import main

        mock_daemon = MagicMock()
        mock_daemon.setup.return_value = True
        mock_daemon_class.return_value = mock_daemon

        main()

        mock_daemon_class.assert_called_once()
        call_kwargs = mock_daemon_class.call_args[1]
        assert call_kwargs["enable_app_watcher"] is True

    @patch("services.remap_daemon.daemon.RemapDaemon")
    @patch("services.remap_daemon.daemon.logging")
    @patch("sys.argv", ["remap-daemon", "--config-dir", "/tmp/custom"])
    def test_main_config_dir_flag(self, mock_logging, mock_daemon_class):
        """Test main with --config-dir flag (lines 254-258)."""
        from services.remap_daemon.daemon import main

        mock_daemon = MagicMock()
        mock_daemon.setup.return_value = True
        mock_daemon_class.return_value = mock_daemon

        main()

        mock_daemon_class.assert_called_once()
        call_args = mock_daemon_class.call_args
        assert call_args[0][0] == Path("/tmp/custom")


class TestMainGuard:
    """Tests for if __name__ == '__main__' guard."""

    @pytest.mark.filterwarnings("ignore:.*found in sys.modules.*:RuntimeWarning")
    @patch("services.remap_daemon.daemon.RemapDaemon")
    @patch("services.remap_daemon.daemon.logging")
    @patch("sys.argv", ["remap-daemon", "--list-devices"])
    def test_main_guard_via_runpy(self, mock_logging, mock_daemon_class):
        """Test __name__ == '__main__' guard (line 314) via runpy."""
        import runpy

        mock_registry = MagicMock()
        mock_registry.scan_devices.return_value = []

        with patch("services.remap_daemon.daemon.DeviceRegistry", return_value=mock_registry):
            # Run the module as __main__ - this triggers line 314
            runpy.run_module("services.remap_daemon.daemon", run_name="__main__", alter_sys=True)
