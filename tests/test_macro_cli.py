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
    _format_step,
    _parse_step,
    cmd_add,
    cmd_create,
    cmd_list,
    cmd_play,
    cmd_record,
    cmd_remove,
    cmd_show,
    cmd_test,
    find_keyboard_device,
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


class TestFindKeyboardDeviceException:
    """Tests for find_keyboard_device exception handling (lines 45-46)."""

    def test_find_keyboard_device_exception(self):
        """Test exception handling when opening device fails."""
        with patch("tools.macro_cli.list_devices", return_value=["/dev/input/event0"]):
            with patch("tools.macro_cli.InputDevice", side_effect=PermissionError("No access")):
                result = find_keyboard_device()
                assert result is None


class TestCmdRecord:
    """Tests for cmd_record command."""

    def test_record_no_device_found(self):
        """Test record when no keyboard device found."""
        with patch("tools.macro_cli.find_keyboard_device", return_value=None):
            args = argparse.Namespace(device=None, stop_key="ESC")
            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_record(args)
            assert result == 1
            assert "No keyboard device found" in mock_out.getvalue()

    def test_record_device_open_fails(self):
        """Test record when device fails to open."""
        with patch("tools.macro_cli.find_keyboard_device", return_value="/dev/input/event0"):
            with patch("tools.macro_cli.InputDevice", side_effect=PermissionError("No access")):
                args = argparse.Namespace(device=None, stop_key="ESC")
                with patch("sys.stdout", new=StringIO()) as mock_out:
                    result = cmd_record(args)
                assert result == 1
                assert "Could not open device" in mock_out.getvalue()


class TestCmdPlay:
    """Tests for cmd_play command."""

    def test_play_file_not_found(self):
        """Test play when file doesn't exist."""
        args = argparse.Namespace(file="/nonexistent/macro.json")
        with patch("sys.stdout", new=StringIO()) as mock_out:
            result = cmd_play(args)
        assert result == 1
        assert "File not found" in mock_out.getvalue()

    def test_play_invalid_json(self):
        """Test play with invalid JSON file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("not valid json")
            f.flush()

            args = argparse.Namespace(file=f.name)
            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_play(args)
            assert result == 1
            assert "Invalid macro file" in mock_out.getvalue()

    def test_play_success(self):
        """Test successful macro playback."""
        macro_data = {
            "id": "test",
            "name": "Test",
            "steps": [{"type": "key_press", "key": "A"}],
            "repeat_count": 1,
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(macro_data, f)
            f.flush()

            mock_player = MagicMock()
            mock_player.play.return_value = True

            args = argparse.Namespace(file=f.name, speed=1.0, yes=True, verbose=False)

            with patch("tools.macro_cli.MacroPlayer", return_value=mock_player):
                with patch("sys.stdout", new=StringIO()) as mock_out:
                    result = cmd_play(args)

            assert result == 0
            assert "Done" in mock_out.getvalue()
            mock_player.close.assert_called_once()

    def test_play_cancelled(self):
        """Test macro playback cancelled."""
        macro_data = {
            "id": "test",
            "name": "Test",
            "steps": [{"type": "key_press", "key": "A"}],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(macro_data, f)
            f.flush()

            mock_player = MagicMock()
            mock_player.play.return_value = False

            args = argparse.Namespace(file=f.name, speed=1.0, yes=True, verbose=False)

            with patch("tools.macro_cli.MacroPlayer", return_value=mock_player):
                with patch("sys.stdout", new=StringIO()) as mock_out:
                    result = cmd_play(args)

            assert result == 1
            assert "Cancelled" in mock_out.getvalue()

    def test_play_with_speed(self):
        """Test playback with speed modifier."""
        macro_data = {
            "id": "test",
            "name": "Test",
            "steps": [{"type": "key_press", "key": "A"}],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(macro_data, f)
            f.flush()

            mock_player = MagicMock()
            mock_player.play.return_value = True

            args = argparse.Namespace(file=f.name, speed=2.0, yes=True, verbose=False)

            with patch("tools.macro_cli.MacroPlayer", return_value=mock_player):
                with patch("sys.stdout", new=StringIO()) as mock_out:
                    result = cmd_play(args)

            assert result == 0
            assert "Speed: 2.0x" in mock_out.getvalue()

    def test_play_keyboard_interrupt(self):
        """Test playback interrupted by user."""
        macro_data = {
            "id": "test",
            "name": "Test",
            "steps": [{"type": "key_press", "key": "A"}],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(macro_data, f)
            f.flush()

            mock_player = MagicMock()
            mock_player.play.side_effect = KeyboardInterrupt()

            args = argparse.Namespace(file=f.name, speed=1.0, yes=True, verbose=False)

            with patch("tools.macro_cli.MacroPlayer", return_value=mock_player):
                with patch("sys.stdout", new=StringIO()) as mock_out:
                    result = cmd_play(args)

            assert result == 1
            mock_player.cancel.assert_called_once()

    def test_play_confirmation_cancelled(self):
        """Test playback cancelled at confirmation."""
        macro_data = {
            "id": "test",
            "name": "Test",
            "steps": [{"type": "key_press", "key": "A"}],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(macro_data, f)
            f.flush()

            args = argparse.Namespace(file=f.name, speed=1.0, yes=False, verbose=False)

            with patch("builtins.input", side_effect=KeyboardInterrupt()):
                with patch("sys.stdout", new=StringIO()) as mock_out:
                    result = cmd_play(args)

            assert result == 0
            assert "Cancelled" in mock_out.getvalue()

    def test_play_with_verbose(self):
        """Test playback with verbose output."""
        macro_data = {
            "id": "test",
            "name": "Test",
            "steps": [{"type": "key_press", "key": "A"}],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(macro_data, f)
            f.flush()

            mock_player = MagicMock()
            mock_player.play.return_value = True

            args = argparse.Namespace(file=f.name, speed=1.0, yes=True, verbose=True)

            with patch("tools.macro_cli.MacroPlayer", return_value=mock_player):
                with patch("sys.stdout", new=StringIO()):
                    result = cmd_play(args)

            assert result == 0
            # Verify callback was set
            mock_player.set_step_callback.assert_called_once()


class TestCmdAddSaveFailure:
    """Tests for cmd_add save failure (lines 302-303)."""

    def test_add_save_failure(self, temp_config):
        """Test adding when save fails."""
        config_dir, loader = temp_config

        profile = Profile(id="test", name="Test", input_devices=[], macros=[])
        loader.save_profile(profile)
        loader.set_active_profile(profile.id)

        macro_data = {"id": "new", "name": "New", "steps": [{"type": "key_press", "key": "X"}]}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(macro_data, f)
            f.flush()

            args = argparse.Namespace(config_dir=config_dir, file=f.name, force=False)

            with patch.object(loader, "save_profile", return_value=False):
                with patch("tools.macro_cli.ProfileLoader", return_value=loader):
                    with patch("sys.stdout", new=StringIO()) as mock_out:
                        result = cmd_add(args)

            assert result == 1
            assert "Failed to save profile" in mock_out.getvalue()


class TestCmdRemoveSaveFailure:
    """Tests for cmd_remove save failure (lines 331-332)."""

    def test_remove_save_failure(self, temp_config, profile_with_macro):
        """Test removing when save fails."""
        config_dir, loader = temp_config
        args = argparse.Namespace(config_dir=config_dir, macro_id="test-macro")

        with patch.object(loader, "save_profile", return_value=False):
            with patch("tools.macro_cli.ProfileLoader", return_value=loader):
                with patch("sys.stdout", new=StringIO()) as mock_out:
                    result = cmd_remove(args)

        assert result == 1
        assert "Failed to save profile" in mock_out.getvalue()


class TestCmdTest:
    """Tests for cmd_test command (lines 337-423)."""

    def test_test_quit(self):
        """Test quitting immediately."""
        mock_player = MagicMock()
        args = argparse.Namespace()

        with patch("tools.macro_cli.MacroPlayer", return_value=mock_player):
            with patch("builtins.input", return_value="quit"):
                with patch("sys.stdout", new=StringIO()) as mock_out:
                    result = cmd_test(args)

        assert result == 0
        assert "Goodbye" in mock_out.getvalue()
        mock_player.close.assert_called_once()

    def test_test_exit(self):
        """Test exit command."""
        mock_player = MagicMock()
        args = argparse.Namespace()

        with patch("tools.macro_cli.MacroPlayer", return_value=mock_player):
            with patch("builtins.input", return_value="exit"):
                with patch("sys.stdout", new=StringIO()):
                    result = cmd_test(args)

        assert result == 0

    def test_test_type_command(self):
        """Test type command."""
        mock_player = MagicMock()
        args = argparse.Namespace()

        inputs = iter(["type hello", "quit"])
        with patch("tools.macro_cli.MacroPlayer", return_value=mock_player):
            with patch("builtins.input", side_effect=lambda _="": next(inputs)):
                with patch("sys.stdout", new=StringIO()) as mock_out:
                    result = cmd_test(args)

        assert result == 0
        assert "Typing: hello" in mock_out.getvalue()
        mock_player.play_steps.assert_called()

    def test_test_type_no_arg(self):
        """Test type command without argument."""
        mock_player = MagicMock()
        args = argparse.Namespace()

        inputs = iter(["type", "quit"])
        with patch("tools.macro_cli.MacroPlayer", return_value=mock_player):
            with patch("builtins.input", side_effect=lambda _="": next(inputs)):
                with patch("sys.stdout", new=StringIO()) as mock_out:
                    result = cmd_test(args)

        assert result == 0
        assert "Usage: type <text>" in mock_out.getvalue()

    def test_test_key_command(self):
        """Test key command."""
        mock_player = MagicMock()
        args = argparse.Namespace()

        inputs = iter(["key a", "quit"])
        with patch("tools.macro_cli.MacroPlayer", return_value=mock_player):
            with patch("builtins.input", side_effect=lambda _="": next(inputs)):
                with patch("sys.stdout", new=StringIO()) as mock_out:
                    result = cmd_test(args)

        assert result == 0
        assert "Pressing: A" in mock_out.getvalue()

    def test_test_key_no_arg(self):
        """Test key command without argument."""
        mock_player = MagicMock()
        args = argparse.Namespace()

        inputs = iter(["key", "quit"])
        with patch("tools.macro_cli.MacroPlayer", return_value=mock_player):
            with patch("builtins.input", side_effect=lambda _="": next(inputs)):
                with patch("sys.stdout", new=StringIO()) as mock_out:
                    result = cmd_test(args)

        assert result == 0
        assert "Usage: key <keyname>" in mock_out.getvalue()

    def test_test_key_invalid(self):
        """Test key command with invalid key."""
        mock_player = MagicMock()
        args = argparse.Namespace()

        inputs = iter(["key INVALID_KEY_XYZ", "quit"])
        with patch("tools.macro_cli.MacroPlayer", return_value=mock_player):
            with patch("tools.macro_cli.validate_key", return_value=(False, "Unknown key")):
                with patch("builtins.input", side_effect=lambda _="": next(inputs)):
                    with patch("sys.stdout", new=StringIO()) as mock_out:
                        result = cmd_test(args)

        assert result == 0
        assert "Invalid key" in mock_out.getvalue()

    def test_test_chord_command(self):
        """Test chord command."""
        mock_player = MagicMock()
        args = argparse.Namespace()

        inputs = iter(["chord CTRL+C", "quit"])
        with patch("tools.macro_cli.MacroPlayer", return_value=mock_player):
            with patch("tools.macro_cli.validate_key", return_value=(True, "")):
                with patch("builtins.input", side_effect=lambda _="": next(inputs)):
                    with patch("sys.stdout", new=StringIO()) as mock_out:
                        result = cmd_test(args)

        assert result == 0
        assert "Chord: CTRL + C" in mock_out.getvalue()

    def test_test_chord_no_arg(self):
        """Test chord command without argument."""
        mock_player = MagicMock()
        args = argparse.Namespace()

        inputs = iter(["chord", "quit"])
        with patch("tools.macro_cli.MacroPlayer", return_value=mock_player):
            with patch("builtins.input", side_effect=lambda _="": next(inputs)):
                with patch("sys.stdout", new=StringIO()) as mock_out:
                    result = cmd_test(args)

        assert result == 0
        assert "Usage: chord" in mock_out.getvalue()

    def test_test_chord_invalid_key(self):
        """Test chord command with invalid key."""
        mock_player = MagicMock()
        args = argparse.Namespace()

        inputs = iter(["chord CTRL+BADKEY", "quit"])

        def validate_mock(key):
            if key == "BADKEY":
                return (False, "Unknown key")
            return (True, "")

        with patch("tools.macro_cli.MacroPlayer", return_value=mock_player):
            with patch("tools.macro_cli.validate_key", side_effect=validate_mock):
                with patch("builtins.input", side_effect=lambda _="": next(inputs)):
                    with patch("sys.stdout", new=StringIO()) as mock_out:
                        result = cmd_test(args)

        assert result == 0
        assert "Invalid key" in mock_out.getvalue()

    def test_test_delay_command(self):
        """Test delay command."""
        mock_player = MagicMock()
        args = argparse.Namespace()

        inputs = iter(["delay 100", "quit"])
        with patch("tools.macro_cli.MacroPlayer", return_value=mock_player):
            with patch("builtins.input", side_effect=lambda _="": next(inputs)):
                with patch("sys.stdout", new=StringIO()) as mock_out:
                    result = cmd_test(args)

        assert result == 0
        assert "Waiting 100ms" in mock_out.getvalue()

    def test_test_delay_invalid(self):
        """Test delay command with invalid value."""
        mock_player = MagicMock()
        args = argparse.Namespace()

        inputs = iter(["delay abc", "quit"])
        with patch("tools.macro_cli.MacroPlayer", return_value=mock_player):
            with patch("builtins.input", side_effect=lambda _="": next(inputs)):
                with patch("sys.stdout", new=StringIO()) as mock_out:
                    result = cmd_test(args)

        assert result == 0
        assert "Usage: delay" in mock_out.getvalue()

    def test_test_unknown_command(self):
        """Test unknown command."""
        mock_player = MagicMock()
        args = argparse.Namespace()

        inputs = iter(["unknown", "quit"])
        with patch("tools.macro_cli.MacroPlayer", return_value=mock_player):
            with patch("builtins.input", side_effect=lambda _="": next(inputs)):
                with patch("sys.stdout", new=StringIO()) as mock_out:
                    result = cmd_test(args)

        assert result == 0
        assert "Unknown command: unknown" in mock_out.getvalue()

    def test_test_eof(self):
        """Test EOF handling."""
        mock_player = MagicMock()
        args = argparse.Namespace()

        with patch("tools.macro_cli.MacroPlayer", return_value=mock_player):
            with patch("builtins.input", side_effect=EOFError()):
                with patch("sys.stdout", new=StringIO()) as mock_out:
                    result = cmd_test(args)

        assert result == 0
        assert "Goodbye" in mock_out.getvalue()

    def test_test_empty_line(self):
        """Test empty line is skipped."""
        mock_player = MagicMock()
        args = argparse.Namespace()

        inputs = iter(["", "quit"])
        with patch("tools.macro_cli.MacroPlayer", return_value=mock_player):
            with patch("builtins.input", side_effect=lambda _="": next(inputs)):
                with patch("sys.stdout", new=StringIO()):
                    result = cmd_test(args)

        assert result == 0


class TestCmdCreate:
    """Tests for cmd_create command (lines 428-458)."""

    def test_create_invalid_step(self):
        """Test create with invalid step format."""
        args = argparse.Namespace(name="Test", steps=["invalid"], output=None, repeat=1, repeat_delay=0)

        with patch("sys.stdout", new=StringIO()) as mock_out:
            result = cmd_create(args)

        assert result == 1
        assert "Invalid step format" in mock_out.getvalue()

    def test_create_no_steps(self):
        """Test create with no valid steps."""
        args = argparse.Namespace(name="Test", steps=[], output=None, repeat=1, repeat_delay=0)

        with patch("sys.stdout", new=StringIO()) as mock_out:
            result = cmd_create(args)

        assert result == 1
        assert "No steps provided" in mock_out.getvalue()

    def test_create_success(self):
        """Test successful macro creation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.json"
            args = argparse.Namespace(
                name="Test Macro",
                steps=["key:A", "delay:100", "text:hello"],
                output=str(output_path),
                repeat=2,
                repeat_delay=50,
            )

            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_create(args)

            assert result == 0
            assert "Created macro: Test Macro" in mock_out.getvalue()
            assert output_path.exists()

            # Verify saved content
            data = json.loads(output_path.read_text())
            assert data["name"] == "Test Macro"
            assert len(data["steps"]) == 3

    def test_create_default_output(self):
        """Test create with default output filename."""
        args = argparse.Namespace(
            name="My Macro",
            steps=["key:B"],
            output=None,
            repeat=1,
            repeat_delay=0,
        )

        # Mock Path.write_text to avoid file creation
        with patch.object(Path, "write_text"):
            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = cmd_create(args)

        assert result == 0
        assert "Created macro: My Macro" in mock_out.getvalue()


class TestParseStep:
    """Tests for _parse_step function (lines 463-484)."""

    def test_parse_key(self):
        """Test parsing key step."""
        step = _parse_step("key:A")
        assert step is not None
        assert step.type == MacroStepType.KEY_PRESS
        assert step.key == "A"

    def test_parse_press(self):
        """Test parsing press step (alias for key)."""
        step = _parse_step("press:B")
        assert step is not None
        assert step.type == MacroStepType.KEY_PRESS
        assert step.key == "B"

    def test_parse_down(self):
        """Test parsing down step."""
        step = _parse_step("down:CTRL")
        assert step is not None
        assert step.type == MacroStepType.KEY_DOWN
        assert step.key == "CTRL"

    def test_parse_up(self):
        """Test parsing up step."""
        step = _parse_step("up:SHIFT")
        assert step is not None
        assert step.type == MacroStepType.KEY_UP
        assert step.key == "SHIFT"

    def test_parse_delay(self):
        """Test parsing delay step."""
        step = _parse_step("delay:100")
        assert step is not None
        assert step.type == MacroStepType.DELAY
        assert step.delay_ms == 100

    def test_parse_wait(self):
        """Test parsing wait step (alias for delay)."""
        step = _parse_step("wait:200")
        assert step is not None
        assert step.type == MacroStepType.DELAY
        assert step.delay_ms == 200

    def test_parse_text(self):
        """Test parsing text step."""
        step = _parse_step("text:hello world")
        assert step is not None
        assert step.type == MacroStepType.TEXT
        assert step.text == "hello world"

    def test_parse_type(self):
        """Test parsing type step (alias for text)."""
        step = _parse_step("type:test string")
        assert step is not None
        assert step.type == MacroStepType.TEXT
        assert step.text == "test string"

    def test_parse_no_colon(self):
        """Test parsing without colon returns None."""
        step = _parse_step("invalid")
        assert step is None

    def test_parse_invalid_delay(self):
        """Test parsing invalid delay value."""
        step = _parse_step("delay:abc")
        assert step is None

    def test_parse_unknown_type(self):
        """Test parsing unknown step type."""
        step = _parse_step("unknown:value")
        assert step is None


class TestFormatStep:
    """Tests for _format_step function (lines 487-501)."""

    def test_format_key_down(self):
        """Test formatting key down step."""
        step = MacroStep(type=MacroStepType.KEY_DOWN, key="A")
        result = _format_step(step)
        assert "↓" in result
        assert "A" in result

    def test_format_key_up(self):
        """Test formatting key up step."""
        step = MacroStep(type=MacroStepType.KEY_UP, key="B")
        result = _format_step(step)
        assert "↑" in result
        assert "B" in result

    def test_format_key_press(self):
        """Test formatting key press step."""
        step = MacroStep(type=MacroStepType.KEY_PRESS, key="C")
        result = _format_step(step)
        assert "⇅" in result
        assert "C" in result

    def test_format_delay(self):
        """Test formatting delay step."""
        step = MacroStep(type=MacroStepType.DELAY, delay_ms=100)
        result = _format_step(step)
        assert "⏱" in result
        assert "100ms" in result

    def test_format_text(self):
        """Test formatting text step."""
        step = MacroStep(type=MacroStepType.TEXT, text="hello")
        result = _format_step(step)
        assert "📝" in result
        assert "hello" in result

    def test_format_text_long(self):
        """Test formatting long text step (truncated)."""
        long_text = "a" * 50
        step = MacroStep(type=MacroStepType.TEXT, text=long_text)
        result = _format_step(step)
        assert "..." in result
        assert len(result) < len(long_text) + 20

    def test_format_text_none(self):
        """Test formatting text step with None text."""
        step = MacroStep(type=MacroStepType.TEXT, text=None)
        result = _format_step(step)
        assert "📝" in result


class TestMain:
    """Tests for main function (lines 504-601)."""

    def test_main_no_command(self):
        """Test main with no command shows help."""
        with patch("sys.argv", ["razer-macro"]):
            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = main()

        assert result == 0

    def test_main_list_command(self, temp_config):
        """Test main with list command."""
        config_dir, _ = temp_config

        with patch("sys.argv", ["razer-macro", "--config-dir", str(config_dir), "list"]):
            with patch("sys.stdout", new=StringIO()) as mock_out:
                result = main()

        assert result == 1  # No active profile
        assert "No active profile" in mock_out.getvalue()


class TestMainGuard:
    """Tests for __name__ == '__main__' guard."""

    def test_main_guard_exists(self):
        """Test that main guard exists in source."""
        import ast

        source_path = Path(__file__).parent.parent / "tools" / "macro_cli.py"
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
