"""Tests for the profile CLI tool."""

import argparse
import json
import sys
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
    cmd_export,
    cmd_import,
    cmd_list,
    cmd_new,
    cmd_show,
    cmd_validate,
    get_loader,
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
        args = argparse.Namespace(config_dir=config_dir, profile_id="nonexistent")

        with patch("sys.stderr", new=StringIO()) as mock_err:
            result = cmd_export(args)

        assert result == 1
        assert "not found" in mock_err.getvalue()

    def test_export_profile(self, temp_config, sample_profile):
        """Test exporting a profile."""
        config_dir, loader = temp_config
        loader.save_profile(sample_profile)

        args = argparse.Namespace(config_dir=config_dir, profile_id="test-profile")

        with patch("sys.stdout", new=StringIO()) as mock_out:
            result = cmd_export(args)

        assert result == 0
        output = mock_out.getvalue()

        # Should be valid JSON
        data = json.loads(output)
        assert data["id"] == "test-profile"
        assert data["name"] == "Test Profile"


class TestCmdImport:
    """Tests for cmd_import command."""

    def test_import_file_not_found(self, temp_config):
        """Test importing from a file that doesn't exist."""
        config_dir, _ = temp_config
        args = argparse.Namespace(
            config_dir=config_dir, file="/nonexistent/path.json", force=False
        )

        with patch("sys.stdout", new=StringIO()) as mock_out:
            result = cmd_import(args)

        assert result == 1
        assert "not found" in mock_out.getvalue()

    def test_import_invalid_json(self, temp_config):
        """Test importing invalid JSON."""
        config_dir, _ = temp_config

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("not valid json")
            f.flush()

            args = argparse.Namespace(config_dir=config_dir, file=f.name, force=False)

            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_import(args)

            assert result == 1
            assert "Invalid JSON" in mock_out.getvalue()

    def test_import_profile(self, temp_config, sample_profile):
        """Test importing a profile."""
        config_dir, loader = temp_config

        # Export profile data to file
        data = sample_profile.model_dump(mode="json")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            f.flush()

            args = argparse.Namespace(config_dir=config_dir, file=f.name, force=False)

            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_import(args)

            assert result == 0
            assert "Imported" in mock_out.getvalue()

        imported = loader.load_profile("test-profile")
        assert imported is not None
        assert imported.name == "Test Profile"

    def test_import_existing_no_force(self, temp_config, sample_profile):
        """Test importing over existing profile without force."""
        config_dir, loader = temp_config
        loader.save_profile(sample_profile)

        data = sample_profile.model_dump(mode="json")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            f.flush()

            args = argparse.Namespace(config_dir=config_dir, file=f.name, force=False)

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
