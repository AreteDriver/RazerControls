"""Tests for the profile CLI tool."""

import argparse
import json
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

from crates.profile_schema import Profile, ProfileLoader
from crates.profile_schema.schema import ActionType, Binding, Layer
from tools.profile_cli import (
    cmd_activate,
    cmd_copy,
    cmd_delete,
    cmd_devices,
    cmd_export,
    cmd_export_all,
    cmd_import,
    cmd_list,
    cmd_new,
    cmd_show,
    cmd_validate,
    get_loader,
    main,
)


@pytest.fixture
def temp_config():
    """Create a temporary config directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir)
        loader = ProfileLoader(config_dir=config_dir)
        yield config_dir, loader


@pytest.fixture
def sample_profile():
    """Create a sample profile."""
    return Profile(
        id="test-profile",
        name="Test Profile",
        description="A test profile",
        input_devices=["usb-Razer_Mouse-event-mouse"],
        layers=[
            Layer(
                id="base",
                name="Base Layer",
                bindings=[
                    Binding(
                        input_code="BTN_SIDE",
                        action_type=ActionType.KEY,
                        output_keys=["KEY_F13"],
                    ),
                ],
            ),
        ],
        is_default=True,
    )


class TestGetLoader:
    """Tests for get_loader function."""

    def test_get_loader_default(self):
        """Test get_loader with default config."""
        loader = get_loader()
        assert loader.config_dir == Path.home() / ".config" / "razer-control-center"

    def test_get_loader_custom_dir(self):
        """Test get_loader with custom directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = get_loader(Path(tmpdir))
            assert loader.config_dir == Path(tmpdir)


class TestCmdList:
    """Tests for cmd_list command."""

    def test_list_empty(self, temp_config):
        """Test listing when no profiles exist."""
        config_dir, _ = temp_config
        args = argparse.Namespace(config_dir=config_dir)

        with patch("sys.stdout", new=StringIO()) as mock_out:
            result = cmd_list(args)

        assert result == 0
        assert "No profiles found" in mock_out.getvalue()

    def test_list_with_profiles(self, temp_config, sample_profile):
        """Test listing profiles."""
        config_dir, loader = temp_config
        loader.save_profile(sample_profile)
        loader.set_active_profile(sample_profile.id)

        args = argparse.Namespace(config_dir=config_dir)

        with patch("sys.stdout", new=StringIO()) as mock_out:
            result = cmd_list(args)

        assert result == 0
        output = mock_out.getvalue()
        assert "test-profile" in output
        assert "[ACTIVE]" in output


class TestCmdShow:
    """Tests for cmd_show command."""

    def test_show_not_found(self, temp_config):
        """Test showing a profile that doesn't exist."""
        config_dir, _ = temp_config
        args = argparse.Namespace(config_dir=config_dir, profile_id="nonexistent")

        with patch("sys.stdout", new=StringIO()) as mock_out:
            result = cmd_show(args)

        assert result == 1
        assert "not found" in mock_out.getvalue()

    def test_show_profile(self, temp_config, sample_profile):
        """Test showing a profile."""
        config_dir, loader = temp_config
        loader.save_profile(sample_profile)

        args = argparse.Namespace(config_dir=config_dir, profile_id="test-profile")

        with patch("sys.stdout", new=StringIO()) as mock_out:
            result = cmd_show(args)

        assert result == 0
        output = mock_out.getvalue()
        assert "Test Profile" in output
        assert "BTN_SIDE" in output
        assert "KEY_F13" in output


class TestCmdNew:
    """Tests for cmd_new command."""

    def test_new_profile(self, temp_config):
        """Test creating a new profile."""
        config_dir, loader = temp_config
        args = argparse.Namespace(
            config_dir=config_dir,
            name="New Profile",
            description="Test description",
            activate=False,
            default=False,
            auto_detect=False,
        )

        with patch("sys.stdout", new=StringIO()) as mock_out:
            result = cmd_new(args)

        assert result == 0
        assert "Created profile" in mock_out.getvalue()

        # Verify profile was created
        profile = loader.load_profile("new_profile")
        assert profile is not None
        assert profile.name == "New Profile"

    def test_new_profile_already_exists(self, temp_config):
        """Test creating a profile that already exists."""
        config_dir, loader = temp_config

        # Create a profile with id "existing"
        existing = Profile(id="existing", name="Existing", input_devices=[])
        loader.save_profile(existing)

        args = argparse.Namespace(
            config_dir=config_dir,
            name="Existing",  # Will generate id "existing"
            description=None,
            activate=False,
            default=False,
            auto_detect=False,
        )

        with patch("sys.stdout", new=StringIO()) as mock_out:
            result = cmd_new(args)

        assert result == 1
        assert "already exists" in mock_out.getvalue()

    def test_new_profile_with_activate(self, temp_config):
        """Test creating and activating a new profile."""
        config_dir, loader = temp_config
        args = argparse.Namespace(
            config_dir=config_dir,
            name="Activated Profile",
            description=None,
            activate=True,
            default=False,
            auto_detect=False,
        )

        with patch("sys.stdout", new=StringIO()):
            result = cmd_new(args)

        assert result == 0
        assert loader.get_active_profile_id() == "activated_profile"


class TestCmdActivate:
    """Tests for cmd_activate command."""

    def test_activate_not_found(self, temp_config):
        """Test activating a profile that doesn't exist."""
        config_dir, _ = temp_config
        args = argparse.Namespace(config_dir=config_dir, profile_id="nonexistent")

        with patch("sys.stdout", new=StringIO()) as mock_out:
            result = cmd_activate(args)

        assert result == 1
        assert "not found" in mock_out.getvalue()

    def test_activate_profile(self, temp_config, sample_profile):
        """Test activating a profile."""
        config_dir, loader = temp_config
        loader.save_profile(sample_profile)

        args = argparse.Namespace(config_dir=config_dir, profile_id="test-profile")

        with patch("sys.stdout", new=StringIO()) as mock_out:
            result = cmd_activate(args)

        assert result == 0
        assert "Activated" in mock_out.getvalue()
        assert loader.get_active_profile_id() == "test-profile"


class TestCmdDelete:
    """Tests for cmd_delete command."""

    def test_delete_not_found(self, temp_config):
        """Test deleting a profile that doesn't exist."""
        config_dir, _ = temp_config
        args = argparse.Namespace(config_dir=config_dir, profile_id="nonexistent", force=True)

        with patch("sys.stdout", new=StringIO()) as mock_out:
            result = cmd_delete(args)

        assert result == 1
        assert "not found" in mock_out.getvalue()

    def test_delete_profile_force(self, temp_config, sample_profile):
        """Test force deleting a profile."""
        config_dir, loader = temp_config
        loader.save_profile(sample_profile)

        args = argparse.Namespace(config_dir=config_dir, profile_id="test-profile", force=True)

        with patch("sys.stdout", new=StringIO()) as mock_out:
            result = cmd_delete(args)

        assert result == 0
        assert "Deleted" in mock_out.getvalue()
        assert loader.load_profile("test-profile") is None

    def test_delete_profile_cancelled(self, temp_config, sample_profile):
        """Test cancelling profile deletion."""
        config_dir, loader = temp_config
        loader.save_profile(sample_profile)

        args = argparse.Namespace(config_dir=config_dir, profile_id="test-profile", force=False)

        with patch("sys.stdout", new=StringIO()) as mock_out:
            with patch("builtins.input", return_value="n"):
                result = cmd_delete(args)

        assert result == 0
        assert "Cancelled" in mock_out.getvalue()
        assert loader.load_profile("test-profile") is not None


class TestCmdCopy:
    """Tests for cmd_copy command."""

    def test_copy_not_found(self, temp_config):
        """Test copying a profile that doesn't exist."""
        config_dir, _ = temp_config
        args = argparse.Namespace(
            config_dir=config_dir, source_id="nonexistent", dest_id="copy", name=None
        )

        with patch("sys.stdout", new=StringIO()) as mock_out:
            result = cmd_copy(args)

        assert result == 1
        assert "not found" in mock_out.getvalue()

    def test_copy_dest_exists(self, temp_config, sample_profile):
        """Test copying when destination already exists."""
        config_dir, loader = temp_config
        loader.save_profile(sample_profile)

        # Create destination profile
        dest = Profile(id="dest", name="Dest", input_devices=[])
        loader.save_profile(dest)

        args = argparse.Namespace(
            config_dir=config_dir, source_id="test-profile", dest_id="dest", name=None
        )

        with patch("sys.stdout", new=StringIO()) as mock_out:
            result = cmd_copy(args)

        assert result == 1
        assert "already exists" in mock_out.getvalue()

    def test_copy_profile(self, temp_config, sample_profile):
        """Test copying a profile."""
        config_dir, loader = temp_config
        loader.save_profile(sample_profile)

        args = argparse.Namespace(
            config_dir=config_dir, source_id="test-profile", dest_id="copy", name="Copy Name"
        )

        with patch("sys.stdout", new=StringIO()) as mock_out:
            result = cmd_copy(args)

        assert result == 0
        assert "Copied" in mock_out.getvalue()

        copy = loader.load_profile("copy")
        assert copy is not None
        assert copy.name == "Copy Name"


class TestCmdExport:
    """Tests for cmd_export command."""

    def test_export_not_found(self, temp_config):
        """Test exporting a profile that doesn't exist."""
        config_dir, _ = temp_config
        args = argparse.Namespace(
            config_dir=config_dir,
            profile_id="nonexistent",
            output=None,
            format=None,
            no_metadata=False,
        )

        with patch("sys.stderr", new=StringIO()) as mock_err:
            result = cmd_export(args)

        assert result == 1
        assert "not found" in mock_err.getvalue()

    def test_export_profile_with_metadata(self, temp_config, sample_profile):
        """Test exporting a profile includes metadata by default."""
        config_dir, loader = temp_config
        loader.save_profile(sample_profile)

        args = argparse.Namespace(
            config_dir=config_dir,
            profile_id="test-profile",
            output=None,
            format=None,
            no_metadata=False,
        )

        with patch("sys.stdout", new=StringIO()) as mock_out:
            result = cmd_export(args)

        assert result == 0
        output = mock_out.getvalue()

        # Should be valid JSON with metadata wrapper
        data = json.loads(output)
        assert "_export" in data
        assert data["_export"]["version"] == "1.0"
        assert "exported_at" in data["_export"]
        assert data["profile"]["id"] == "test-profile"
        assert data["profile"]["name"] == "Test Profile"

    def test_export_profile_no_metadata(self, temp_config, sample_profile):
        """Test exporting without metadata."""
        config_dir, loader = temp_config
        loader.save_profile(sample_profile)

        args = argparse.Namespace(
            config_dir=config_dir,
            profile_id="test-profile",
            output=None,
            format=None,
            no_metadata=True,
        )

        with patch("sys.stdout", new=StringIO()) as mock_out:
            result = cmd_export(args)

        assert result == 0
        output = mock_out.getvalue()

        # Should be plain profile without wrapper
        data = json.loads(output)
        assert "_export" not in data
        assert data["id"] == "test-profile"
        assert data["name"] == "Test Profile"

    def test_export_yaml_format(self, temp_config, sample_profile):
        """Test exporting in YAML format."""
        import yaml

        config_dir, loader = temp_config
        loader.save_profile(sample_profile)

        args = argparse.Namespace(
            config_dir=config_dir,
            profile_id="test-profile",
            output=None,
            format="yaml",
            no_metadata=False,
        )

        with patch("sys.stdout", new=StringIO()) as mock_out:
            result = cmd_export(args)

        assert result == 0
        output = mock_out.getvalue()

        # Should be valid YAML
        data = yaml.safe_load(output)
        assert data["_export"]["format"] == "yaml"
        assert data["profile"]["id"] == "test-profile"

    def test_export_to_file(self, temp_config, sample_profile):
        """Test exporting to a file."""
        config_dir, loader = temp_config
        loader.save_profile(sample_profile)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            output_path = f.name

        args = argparse.Namespace(
            config_dir=config_dir,
            profile_id="test-profile",
            output=output_path,
            format=None,
            no_metadata=False,
        )

        with patch("sys.stdout", new=StringIO()) as mock_out:
            result = cmd_export(args)

        assert result == 0
        assert "Exported" in mock_out.getvalue()

        # Verify file contents
        data = json.loads(Path(output_path).read_text())
        assert data["profile"]["id"] == "test-profile"

    def test_export_yaml_file_auto_detect(self, temp_config, sample_profile):
        """Test YAML format is auto-detected from .yaml extension."""
        import yaml

        config_dir, loader = temp_config
        loader.save_profile(sample_profile)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            output_path = f.name

        args = argparse.Namespace(
            config_dir=config_dir,
            profile_id="test-profile",
            output=output_path,
            format=None,  # Should auto-detect from extension
            no_metadata=False,
        )

        with patch("sys.stdout", new=StringIO()):
            result = cmd_export(args)

        assert result == 0

        # Verify YAML contents
        data = yaml.safe_load(Path(output_path).read_text())
        assert data["_export"]["format"] == "yaml"
        assert data["profile"]["id"] == "test-profile"


class TestCmdImport:
    """Tests for cmd_import command."""

    def test_import_file_not_found(self, temp_config):
        """Test importing from a file that doesn't exist."""
        config_dir, _ = temp_config
        args = argparse.Namespace(
            config_dir=config_dir, file="/nonexistent/path.json", force=False, new_id=None
        )

        with patch("sys.stdout", new=StringIO()) as mock_out:
            result = cmd_import(args)

        assert result == 1
        assert "not found" in mock_out.getvalue()

    def test_import_invalid_json(self, temp_config):
        """Test importing invalid JSON."""
        config_dir, _ = temp_config

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("not valid json {{{{")
            f.flush()

            args = argparse.Namespace(
                config_dir=config_dir, file=f.name, force=False, new_id=None
            )

            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_import(args)

            assert result == 1
            assert "Invalid file format" in mock_out.getvalue()

    def test_import_profile(self, temp_config, sample_profile):
        """Test importing a profile."""
        config_dir, loader = temp_config

        # Export profile data to file
        data = sample_profile.model_dump(mode="json")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            f.flush()

            args = argparse.Namespace(
                config_dir=config_dir, file=f.name, force=False, new_id=None
            )

            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_import(args)

            assert result == 0
            assert "Imported" in mock_out.getvalue()

        imported = loader.load_profile("test-profile")
        assert imported is not None
        assert imported.name == "Test Profile"

    def test_import_yaml(self, temp_config, sample_profile):
        """Test importing a profile from YAML."""
        import yaml

        config_dir, loader = temp_config

        # Export profile data to YAML
        data = sample_profile.model_dump(mode="json")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(data, f)
            f.flush()

            args = argparse.Namespace(
                config_dir=config_dir, file=f.name, force=False, new_id=None
            )

            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_import(args)

            assert result == 0
            assert "Imported" in mock_out.getvalue()

        imported = loader.load_profile("test-profile")
        assert imported is not None
        assert imported.name == "Test Profile"

    def test_import_wrapped_format(self, temp_config, sample_profile):
        """Test importing a profile with metadata wrapper."""
        config_dir, loader = temp_config

        # Create wrapped format (as exported by new version)
        export_data = {
            "_export": {
                "version": "1.0",
                "exported_at": "2024-01-01T00:00:00",
                "format": "json",
            },
            "profile": sample_profile.model_dump(mode="json"),
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(export_data, f)
            f.flush()

            args = argparse.Namespace(
                config_dir=config_dir, file=f.name, force=False, new_id=None
            )

            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_import(args)

            assert result == 0
            assert "Imported" in mock_out.getvalue()

        imported = loader.load_profile("test-profile")
        assert imported is not None
        assert imported.name == "Test Profile"

    def test_import_with_new_id(self, temp_config, sample_profile):
        """Test importing a profile with a new ID."""
        config_dir, loader = temp_config

        data = sample_profile.model_dump(mode="json")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            f.flush()

            args = argparse.Namespace(
                config_dir=config_dir, file=f.name, force=False, new_id="my-custom-id"
            )

            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_import(args)

            assert result == 0
            assert "Imported" in mock_out.getvalue()

        # Original ID should not exist
        assert loader.load_profile("test-profile") is None

        # New ID should exist
        imported = loader.load_profile("my-custom-id")
        assert imported is not None
        assert imported.id == "my-custom-id"
        assert imported.name == "Test Profile"

    def test_import_existing_no_force(self, temp_config, sample_profile):
        """Test importing over existing profile without force."""
        config_dir, loader = temp_config
        loader.save_profile(sample_profile)

        data = sample_profile.model_dump(mode="json")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            f.flush()

            args = argparse.Namespace(
                config_dir=config_dir, file=f.name, force=False, new_id=None
            )

            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_import(args)

            assert result == 1
            assert "already exists" in mock_out.getvalue()


class TestCmdValidate:
    """Tests for cmd_validate command."""

    def test_validate_not_found(self, temp_config):
        """Test validating a profile that doesn't exist."""
        config_dir, _ = temp_config
        args = argparse.Namespace(config_dir=config_dir, profile_id="nonexistent")

        with patch("sys.stdout", new=StringIO()) as mock_out:
            result = cmd_validate(args)

        assert result == 1
        assert "not found" in mock_out.getvalue()

    def test_validate_valid_profile(self, temp_config, sample_profile):
        """Test validating a valid profile."""
        config_dir, loader = temp_config
        loader.save_profile(sample_profile)

        args = argparse.Namespace(config_dir=config_dir, profile_id="test-profile")

        with patch("sys.stdout", new=StringIO()) as mock_out:
            result = cmd_validate(args)

        assert result == 0
        output = mock_out.getvalue()
        assert "0 errors" in output

    def test_validate_profile_with_invalid_keys(self, temp_config):
        """Test validating a profile with invalid key codes."""
        config_dir, loader = temp_config

        profile = Profile(
            id="invalid-profile",
            name="Invalid Profile",
            input_devices=[],
            layers=[
                Layer(
                    id="base",
                    name="Base",
                    bindings=[
                        Binding(
                            input_code="INVALID_KEY",
                            action_type=ActionType.KEY,
                            output_keys=["ALSO_INVALID"],
                        ),
                    ],
                ),
            ],
        )
        loader.save_profile(profile)

        args = argparse.Namespace(config_dir=config_dir, profile_id="invalid-profile")

        with patch("sys.stdout", new=StringIO()) as mock_out:
            result = cmd_validate(args)

        assert result == 1
        output = mock_out.getvalue()
        assert "Errors:" in output

    def test_validate_no_input_devices_warning(self, temp_config):
        """Test validation warns about no input devices."""
        config_dir, loader = temp_config

        profile = Profile(
            id="no-devices",
            name="No Devices",
            input_devices=[],
            layers=[],
        )
        loader.save_profile(profile)

        args = argparse.Namespace(config_dir=config_dir, profile_id="no-devices")

        with patch("sys.stdout", new=StringIO()) as mock_out:
            result = cmd_validate(args)

        assert result == 0  # Warnings don't cause failure
        output = mock_out.getvalue()
        assert "Warnings:" in output
        assert "No input devices" in output


from unittest.mock import MagicMock

from crates.profile_schema.schema import MacroAction, MacroStep, MacroStepType


class TestCmdListWithDefault:
    """Tests for cmd_list with default profiles (lines 61-62)."""

    def test_list_shows_default_status(self, temp_config):
        """Test listing shows default status for non-active default profile."""
        config_dir, loader = temp_config

        profile = Profile(
            id="default",
            name="Default Profile",
            input_devices=[],
            layers=[],
            is_default=True,
        )
        loader.save_profile(profile)
        # Don't set as active

        args = argparse.Namespace(config_dir=config_dir)

        with patch("sys.stdout", new=StringIO()) as mock_out:
            result = cmd_list(args)

        assert result == 0
        assert "[default]" in mock_out.getvalue()


class TestCmdShowBranches:
    """Tests for cmd_show various display branches."""

    def test_show_no_input_devices(self, temp_config):
        """Test showing profile with no input devices (line 96)."""
        config_dir, loader = temp_config

        profile = Profile(
            id="no-devices",
            name="No Devices",
            input_devices=[],
            layers=[],
        )
        loader.save_profile(profile)

        args = argparse.Namespace(config_dir=config_dir, profile_id="no-devices")

        with patch("sys.stdout", new=StringIO()) as mock_out:
            result = cmd_show(args)

        assert result == 0
        assert "(none configured)" in mock_out.getvalue()

    def test_show_macro_binding(self, temp_config):
        """Test showing profile with macro binding (lines 111-114)."""
        config_dir, loader = temp_config

        profile = Profile(
            id="macro-profile",
            name="Macro Profile",
            input_devices=["test-device"],
            layers=[
                Layer(
                    id="base",
                    name="Base",
                    bindings=[
                        Binding(
                            input_code="BTN_SIDE",
                            action_type=ActionType.MACRO,
                            macro_id="test-macro",
                        ),
                    ],
                ),
            ],
        )
        loader.save_profile(profile)

        args = argparse.Namespace(config_dir=config_dir, profile_id="macro-profile")

        with patch("sys.stdout", new=StringIO()) as mock_out:
            result = cmd_show(args)

        assert result == 0
        assert "macro:test-macro" in mock_out.getvalue()

    def test_show_no_bindings(self, temp_config):
        """Test showing layer with no bindings (line 117)."""
        config_dir, loader = temp_config

        profile = Profile(
            id="empty-layer",
            name="Empty Layer",
            input_devices=["test-device"],
            layers=[
                Layer(id="base", name="Base", bindings=[]),
            ],
        )
        loader.save_profile(profile)

        args = argparse.Namespace(config_dir=config_dir, profile_id="empty-layer")

        with patch("sys.stdout", new=StringIO()) as mock_out:
            result = cmd_show(args)

        assert result == 0
        assert "(no bindings)" in mock_out.getvalue()

    def test_show_with_macros(self, temp_config):
        """Test showing profile with macros (lines 121-123)."""
        config_dir, loader = temp_config

        profile = Profile(
            id="with-macros",
            name="With Macros",
            input_devices=[],
            layers=[],
            macros=[
                MacroAction(
                    id="test-macro",
                    name="Test Macro",
                    steps=[MacroStep(type=MacroStepType.KEY_PRESS, key="A")],
                ),
            ],
        )
        loader.save_profile(profile)

        args = argparse.Namespace(config_dir=config_dir, profile_id="with-macros")

        with patch("sys.stdout", new=StringIO()) as mock_out:
            result = cmd_show(args)

        assert result == 0
        output = mock_out.getvalue()
        assert "Macros (1)" in output
        assert "test-macro" in output

    def test_show_with_process_matching(self, temp_config):
        """Test showing profile with process matching (lines 127-129)."""
        config_dir, loader = temp_config

        profile = Profile(
            id="process-match",
            name="Process Match",
            input_devices=[],
            layers=[],
            match_process_names=["firefox", "chrome"],
        )
        loader.save_profile(profile)

        args = argparse.Namespace(config_dir=config_dir, profile_id="process-match")

        with patch("sys.stdout", new=StringIO()) as mock_out:
            result = cmd_show(args)

        assert result == 0
        output = mock_out.getvalue()
        assert "Auto-activate for processes" in output
        assert "firefox" in output


class TestCmdNewBranches:
    """Tests for cmd_new edge cases."""

    def test_new_with_auto_detect(self, temp_config):
        """Test creating profile with auto-detect (lines 151-156)."""
        config_dir, _ = temp_config

        mock_device = MagicMock()
        mock_device.stable_id = "razer-mouse-1"
        mock_device.is_mouse = True

        mock_registry = MagicMock()
        mock_registry.get_razer_devices.return_value = [mock_device]

        args = argparse.Namespace(
            config_dir=config_dir,
            name="Auto Detect",
            description=None,
            activate=False,
            default=False,
            auto_detect=True,
        )

        with patch("tools.profile_cli.DeviceRegistry", return_value=mock_registry):
            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_new(args)

        assert result == 0
        assert "Auto-detected device" in mock_out.getvalue()

    def test_new_save_failure(self, temp_config):
        """Test creating profile when save fails (lines 179-180)."""
        config_dir, loader = temp_config

        args = argparse.Namespace(
            config_dir=config_dir,
            name="Test",
            description=None,
            activate=False,
            default=False,
            auto_detect=False,
        )

        with patch.object(loader, "save_profile", return_value=False):
            with patch("tools.profile_cli.get_loader", return_value=loader):
                with patch("sys.stdout", new=StringIO()) as mock_out:
                    result = cmd_new(args)

        assert result == 1
        assert "Failed to save profile" in mock_out.getvalue()


class TestCmdDeleteBranches:
    """Tests for cmd_delete edge cases."""

    def test_delete_active_profile_warning(self, temp_config, sample_profile):
        """Test deleting active profile shows warning (line 224)."""
        config_dir, loader = temp_config
        loader.save_profile(sample_profile)
        loader.set_active_profile(sample_profile.id)

        args = argparse.Namespace(config_dir=config_dir, profile_id="test-profile", force=True)

        with patch("sys.stdout", new=StringIO()) as mock_out:
            result = cmd_delete(args)

        assert result == 0
        assert "Warning: Deleting the active profile" in mock_out.getvalue()

    def test_delete_failure(self, temp_config, sample_profile):
        """Test deleting profile when delete fails (lines 230-231)."""
        config_dir, loader = temp_config
        loader.save_profile(sample_profile)

        args = argparse.Namespace(config_dir=config_dir, profile_id="test-profile", force=True)

        with patch.object(loader, "delete_profile", return_value=False):
            with patch("tools.profile_cli.get_loader", return_value=loader):
                with patch("sys.stdout", new=StringIO()) as mock_out:
                    result = cmd_delete(args)

        assert result == 1
        assert "Failed to delete profile" in mock_out.getvalue()


class TestCmdCopyBranches:
    """Tests for cmd_copy edge cases."""

    def test_copy_failure(self, temp_config, sample_profile):
        """Test copying profile when save fails (lines 261-262)."""
        config_dir, loader = temp_config
        loader.save_profile(sample_profile)

        args = argparse.Namespace(
            config_dir=config_dir,
            source_id="test-profile",
            dest_id="new-profile",
            name=None,
        )

        # Create a mock loader that returns the real profile but fails to save the copy
        mock_loader = MagicMock()
        mock_loader.load_profile.side_effect = lambda pid: sample_profile if pid == "test-profile" else None
        mock_loader.save_profile.return_value = False

        with patch("tools.profile_cli.get_loader", return_value=mock_loader):
            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_copy(args)

        assert result == 1
        assert "Failed to save copied profile" in mock_out.getvalue()


class TestCmdExportAll:
    """Tests for cmd_export_all function (lines 334-383)."""

    def test_export_all_no_profiles(self, temp_config):
        """Test export-all when no profiles exist."""
        config_dir, _ = temp_config

        args = argparse.Namespace(
            config_dir=config_dir,
            output="/tmp/test",
            zip=False,
            format="json",
            no_metadata=False,
        )

        with patch("sys.stdout", new=StringIO()) as mock_out:
            result = cmd_export_all(args)

        assert result == 1
        assert "No profiles to export" in mock_out.getvalue()

    def test_export_all_to_directory(self, temp_config, sample_profile):
        """Test export-all to directory."""
        config_dir, loader = temp_config
        loader.save_profile(sample_profile)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "exports"

            args = argparse.Namespace(
                config_dir=config_dir,
                output=str(output_dir),
                zip=False,
                format="json",
                no_metadata=False,
            )

            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_export_all(args)

            assert result == 0
            assert output_dir.exists()
            assert (output_dir / "test-profile.json").exists()

    def test_export_all_as_zip(self, temp_config, sample_profile):
        """Test export-all as zip file."""
        config_dir, loader = temp_config
        loader.save_profile(sample_profile)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "backup.zip"

            args = argparse.Namespace(
                config_dir=config_dir,
                output=str(output_path),
                zip=True,
                format="json",
                no_metadata=False,
            )

            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_export_all(args)

            assert result == 0
            assert output_path.exists()

    def test_export_all_zip_to_directory(self, temp_config, sample_profile):
        """Test export-all as zip to directory (auto-generates filename)."""
        config_dir, loader = temp_config
        loader.save_profile(sample_profile)

        with tempfile.TemporaryDirectory() as tmpdir:
            args = argparse.Namespace(
                config_dir=config_dir,
                output=tmpdir,
                zip=True,
                format="yaml",
                no_metadata=False,
            )

            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_export_all(args)

            assert result == 0
            # Should have created a zip file with timestamp
            zip_files = list(Path(tmpdir).glob("razer_profiles_*.zip"))
            assert len(zip_files) == 1


class TestCmdImportBranches:
    """Tests for cmd_import edge cases."""

    def test_import_from_stdin(self, temp_config):
        """Test importing from stdin (lines 393-402)."""
        config_dir, _ = temp_config

        profile_data = {
            "id": "stdin-profile",
            "name": "Stdin Profile",
            "input_devices": [],
            "layers": [],
        }

        args = argparse.Namespace(
            config_dir=config_dir,
            file="-",
            force=False,
            new_id=None,
        )

        with patch("sys.stdin.read", return_value=json.dumps(profile_data)):
            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_import(args)

        assert result == 0
        assert "Imported profile: stdin-profile" in mock_out.getvalue()

    def test_import_stdin_wrapped_format(self, temp_config):
        """Test importing wrapped format from stdin."""
        config_dir, _ = temp_config

        wrapped_data = {
            "_export": {"version": "1.0"},
            "profile": {
                "id": "wrapped-stdin",
                "name": "Wrapped",
                "input_devices": [],
                "layers": [],
            },
        }

        args = argparse.Namespace(
            config_dir=config_dir,
            file="-",
            force=False,
            new_id=None,
        )

        with patch("sys.stdin.read", return_value=json.dumps(wrapped_data)):
            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_import(args)

        assert result == 0

    def test_import_save_failure(self, temp_config):
        """Test importing when save fails (lines 433-434)."""
        config_dir, loader = temp_config

        profile_data = {
            "id": "fail-save",
            "name": "Fail Save",
            "input_devices": [],
            "layers": [],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(profile_data, f)
            f.flush()

            args = argparse.Namespace(
                config_dir=config_dir,
                file=f.name,
                force=False,
                new_id=None,
            )

            with patch.object(loader, "save_profile", return_value=False):
                with patch("tools.profile_cli.get_loader", return_value=loader):
                    with patch("sys.stdout", new=StringIO()) as mock_out:
                        result = cmd_import(args)

            assert result == 1
            assert "Failed to save profile" in mock_out.getvalue()


class TestCmdValidateBranches:
    """Tests for cmd_validate edge cases."""

    def test_validate_macro_not_found(self, temp_config):
        """Test validation catches missing macro reference (lines 474-476)."""
        config_dir, loader = temp_config

        profile = Profile(
            id="bad-macro-ref",
            name="Bad Macro Ref",
            input_devices=["test"],
            layers=[
                Layer(
                    id="base",
                    name="Base",
                    bindings=[
                        Binding(
                            input_code="BTN_SIDE",
                            action_type=ActionType.MACRO,
                            macro_id="nonexistent-macro",
                        ),
                    ],
                ),
            ],
            macros=[],  # No macros defined
        )
        loader.save_profile(profile)

        args = argparse.Namespace(config_dir=config_dir, profile_id="bad-macro-ref")

        with patch("sys.stdout", new=StringIO()) as mock_out:
            result = cmd_validate(args)

        assert result == 1
        assert "macro 'nonexistent-macro' not found" in mock_out.getvalue()

    def test_validate_hold_modifier_invalid(self, temp_config):
        """Test validation catches invalid hold modifier (lines 480-482)."""
        config_dir, loader = temp_config

        profile = Profile(
            id="bad-modifier",
            name="Bad Modifier",
            input_devices=["test"],
            layers=[
                Layer(
                    id="shift",
                    name="Shift Layer",
                    bindings=[],
                    hold_modifier_input_code="INVALID_KEY_XYZ",
                ),
            ],
        )
        loader.save_profile(profile)

        args = argparse.Namespace(config_dir=config_dir, profile_id="bad-modifier")

        with patch("sys.stdout", new=StringIO()) as mock_out:
            result = cmd_validate(args)

        assert result == 1
        assert "hold modifier" in mock_out.getvalue()


class TestCmdDevices:
    """Tests for cmd_devices function (lines 504-533)."""

    def test_devices_no_razer(self, temp_config):
        """Test listing devices when no Razer devices found."""
        config_dir, _ = temp_config

        mock_device = MagicMock()
        mock_device.stable_id = "generic-mouse"

        mock_registry = MagicMock()
        mock_registry.scan_devices.return_value = [mock_device]

        args = argparse.Namespace(config_dir=config_dir)

        with patch("tools.profile_cli.DeviceRegistry", return_value=mock_registry):
            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_devices(args)

        assert result == 0
        assert "No Razer devices found" in mock_out.getvalue()

    def test_devices_with_razer(self, temp_config):
        """Test listing Razer devices."""
        config_dir, _ = temp_config

        mock_device = MagicMock()
        mock_device.stable_id = "usb-Razer_Mouse-event"
        mock_device.name = "Razer Mouse"
        mock_device.is_mouse = True
        mock_device.is_keyboard = False
        mock_device.event_path = "/dev/input/event5"

        mock_registry = MagicMock()
        mock_registry.scan_devices.return_value = [mock_device]

        args = argparse.Namespace(config_dir=config_dir)

        with patch("tools.profile_cli.DeviceRegistry", return_value=mock_registry):
            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_devices(args)

        assert result == 0
        output = mock_out.getvalue()
        assert "Razer Devices" in output
        assert "mouse" in output


class TestMain:
    """Tests for main function (lines 537-653)."""

    def test_main_no_command(self):
        """Test main with no command shows help."""
        with patch("sys.argv", ["razer-profile"]):
            with patch("sys.stdout", new=StringIO()):
                result = main()

        assert result == 0

    def test_main_list_command(self, temp_config):
        """Test main with list command."""
        config_dir, _ = temp_config

        with patch("sys.argv", ["razer-profile", "--config-dir", str(config_dir), "list"]):
            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = main()

        assert result == 0


class TestMainGuard:
    """Tests for __name__ == '__main__' guard."""

    def test_main_guard_exists(self):
        """Test that main guard exists in source."""
        import ast

        source_path = Path(__file__).parent.parent / "tools" / "profile_cli.py"
        tree = ast.parse(source_path.read_text())

        has_main_guard = False
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                if (
                    isinstance(node.test, ast.Compare)
                    and isinstance(node.test.left, ast.Name)
                    and node.test.left.id == "__name__"
                ):
                    has_main_guard = True
                    break

        assert has_main_guard, "main guard not found"
