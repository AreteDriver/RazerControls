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
