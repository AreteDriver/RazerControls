"""Tests for the macro CLI tool."""

import argparse
import json
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from crates.profile_schema import MacroAction, MacroStep, MacroStepType, Profile, ProfileLoader
from tools.macro_cli import (
    cmd_add,
    cmd_list,
    cmd_remove,
    cmd_show,
    find_keyboard_device,
)


@pytest.fixture
def temp_config():
    """Create a temporary config directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir)
        loader = ProfileLoader(config_dir=config_dir)
        yield config_dir, loader


@pytest.fixture
def sample_macro():
    """Create a sample macro."""
    return MacroAction(
        id="test-macro",
        name="Test Macro",
        steps=[
            MacroStep(type=MacroStepType.KEY_PRESS, key="A"),
            MacroStep(type=MacroStepType.DELAY, delay_ms=100),
            MacroStep(type=MacroStepType.KEY_PRESS, key="B"),
        ],
        repeat_count=2,
        repeat_delay_ms=50,
    )


@pytest.fixture
def profile_with_macro(temp_config, sample_macro):
    """Create a profile with a macro."""
    config_dir, loader = temp_config
    profile = Profile(
        id="macro-profile",
        name="Macro Profile",
        input_devices=[],
        macros=[sample_macro],
    )
    loader.save_profile(profile)
    loader.set_active_profile(profile.id)
    return profile


class TestFindKeyboardDevice:
    """Tests for find_keyboard_device function."""

    def test_find_keyboard_no_devices(self):
        """Test finding keyboard when no devices exist."""
        with patch("tools.macro_cli.list_devices", return_value=[]):
            result = find_keyboard_device()
            assert result is None

    def test_find_keyboard_with_keyboard(self):
        """Test finding keyboard device."""
        mock_device = MagicMock()
        mock_device.capabilities.return_value = {
            1: [30, 44]  # EV_KEY with KEY_A (30) and KEY_Z (44)
        }

        with patch("tools.macro_cli.list_devices", return_value=["/dev/input/event0"]):
            with patch("tools.macro_cli.InputDevice", return_value=mock_device):
                with patch("tools.macro_cli.ecodes") as mock_ecodes:
                    mock_ecodes.EV_KEY = 1
                    mock_ecodes.KEY_A = 30
                    mock_ecodes.KEY_Z = 44
                    result = find_keyboard_device()
                    assert result == "/dev/input/event0"


class TestCmdList:
    """Tests for cmd_list command."""

    def test_list_no_profile(self, temp_config):
        """Test listing when no active profile."""
        config_dir, _ = temp_config
        args = argparse.Namespace(config_dir=config_dir)

        with patch("sys.stdout", new=StringIO()) as mock_out:
            result = cmd_list(args)

        assert result == 1
        assert "No active profile" in mock_out.getvalue()

    def test_list_no_macros(self, temp_config):
        """Test listing when profile has no macros."""
        config_dir, loader = temp_config
        profile = Profile(id="empty", name="Empty Profile", input_devices=[], macros=[])
        loader.save_profile(profile)
        loader.set_active_profile(profile.id)

        args = argparse.Namespace(config_dir=config_dir)

        with patch("sys.stdout", new=StringIO()) as mock_out:
            result = cmd_list(args)

        assert result == 0
        assert "no macros defined" in mock_out.getvalue()

    def test_list_with_macros(self, temp_config, profile_with_macro):
        """Test listing macros."""
        config_dir, _ = temp_config
        args = argparse.Namespace(config_dir=config_dir)

        with patch("sys.stdout", new=StringIO()) as mock_out:
            result = cmd_list(args)

        assert result == 0
        output = mock_out.getvalue()
        assert "test-macro" in output
        assert "Test Macro" in output
        assert "1 macro(s) found" in output


class TestCmdShow:
    """Tests for cmd_show command."""

    def test_show_no_profile(self, temp_config):
        """Test showing when no active profile."""
        config_dir, _ = temp_config
        args = argparse.Namespace(config_dir=config_dir, macro_id="test")

        with patch("sys.stdout", new=StringIO()) as mock_out:
            result = cmd_show(args)

        assert result == 1
        assert "No active profile" in mock_out.getvalue()

    def test_show_macro_not_found(self, temp_config, profile_with_macro):
        """Test showing macro that doesn't exist."""
        config_dir, _ = temp_config
        args = argparse.Namespace(config_dir=config_dir, macro_id="nonexistent")

        with patch("sys.stdout", new=StringIO()) as mock_out:
            result = cmd_show(args)

        assert result == 1
        assert "not found" in mock_out.getvalue()

    def test_show_macro(self, temp_config, profile_with_macro):
        """Test showing macro details."""
        config_dir, _ = temp_config
        args = argparse.Namespace(config_dir=config_dir, macro_id="test-macro")

        with patch("sys.stdout", new=StringIO()) as mock_out:
            result = cmd_show(args)

        assert result == 0
        output = mock_out.getvalue()
        assert "Test Macro" in output
        assert "test-macro" in output
        assert "Repeat: 2x" in output
        assert "Steps (3)" in output


class TestCmdAdd:
    """Tests for cmd_add command."""

    def test_add_no_profile(self, temp_config):
        """Test adding when no active profile."""
        config_dir, _ = temp_config
        args = argparse.Namespace(config_dir=config_dir, file="test.json", force=False)

        with patch("sys.stdout", new=StringIO()) as mock_out:
            result = cmd_add(args)

        assert result == 1
        assert "No active profile" in mock_out.getvalue()

    def test_add_file_not_found(self, temp_config, profile_with_macro):
        """Test adding when file doesn't exist."""
        config_dir, _ = temp_config
        args = argparse.Namespace(config_dir=config_dir, file="/nonexistent.json", force=False)

        with patch("sys.stdout", new=StringIO()) as mock_out:
            result = cmd_add(args)

        assert result == 1
        assert "File not found" in mock_out.getvalue()

    def test_add_invalid_json(self, temp_config, profile_with_macro):
        """Test adding with invalid JSON file."""
        config_dir, _ = temp_config

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("not valid json")
            f.flush()

            args = argparse.Namespace(config_dir=config_dir, file=f.name, force=False)

            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_add(args)

            assert result == 1
            assert "Invalid macro file" in mock_out.getvalue()

    def test_add_macro(self, temp_config):
        """Test adding a macro."""
        config_dir, loader = temp_config

        # Create profile without macros
        profile = Profile(id="test", name="Test", input_devices=[], macros=[])
        loader.save_profile(profile)
        loader.set_active_profile(profile.id)

        # Create macro file
        macro_data = {
            "id": "new-macro",
            "name": "New Macro",
            "steps": [{"type": "key_press", "key": "X"}],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(macro_data, f)
            f.flush()

            args = argparse.Namespace(config_dir=config_dir, file=f.name, force=False)

            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_add(args)

            assert result == 0
            assert "Added macro 'new-macro'" in mock_out.getvalue()

        # Verify macro was added
        updated = loader.load_profile("test")
        assert len(updated.macros) == 1
        assert updated.macros[0].id == "new-macro"

    def test_add_duplicate_no_force(self, temp_config, profile_with_macro):
        """Test adding duplicate macro without force."""
        config_dir, _ = temp_config

        macro_data = {
            "id": "test-macro",  # Same ID as existing
            "name": "Duplicate",
            "steps": [{"type": "key_press", "key": "X"}],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(macro_data, f)
            f.flush()

            args = argparse.Namespace(config_dir=config_dir, file=f.name, force=False)

            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_add(args)

            assert result == 1
            assert "already exists" in mock_out.getvalue()

    def test_add_duplicate_with_force(self, temp_config, profile_with_macro):
        """Test adding duplicate macro with force."""
        config_dir, loader = temp_config

        macro_data = {
            "id": "test-macro",  # Same ID as existing
            "name": "Replaced Macro",
            "steps": [{"type": "key_press", "key": "X"}],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(macro_data, f)
            f.flush()

            args = argparse.Namespace(config_dir=config_dir, file=f.name, force=True)

            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_add(args)

            assert result == 0
            assert "Added macro" in mock_out.getvalue()

        # Verify macro was replaced
        updated = loader.load_profile("macro-profile")
        assert len(updated.macros) == 1
        assert updated.macros[0].name == "Replaced Macro"


class TestCmdRemove:
    """Tests for cmd_remove command."""

    def test_remove_no_profile(self, temp_config):
        """Test removing when no active profile."""
        config_dir, _ = temp_config
        args = argparse.Namespace(config_dir=config_dir, macro_id="test")

        with patch("sys.stdout", new=StringIO()) as mock_out:
            result = cmd_remove(args)

        assert result == 1
        assert "No active profile" in mock_out.getvalue()

    def test_remove_not_found(self, temp_config, profile_with_macro):
        """Test removing macro that doesn't exist."""
        config_dir, _ = temp_config
        args = argparse.Namespace(config_dir=config_dir, macro_id="nonexistent")

        with patch("sys.stdout", new=StringIO()) as mock_out:
            result = cmd_remove(args)

        assert result == 1
        assert "not found" in mock_out.getvalue()

    def test_remove_macro(self, temp_config, profile_with_macro):
        """Test removing a macro."""
        config_dir, loader = temp_config
        args = argparse.Namespace(config_dir=config_dir, macro_id="test-macro")

        with patch("sys.stdout", new=StringIO()) as mock_out:
            result = cmd_remove(args)

        assert result == 0
        assert "Removed macro 'test-macro'" in mock_out.getvalue()

        # Verify macro was removed
        updated = loader.load_profile("macro-profile")
        assert len(updated.macros) == 0
