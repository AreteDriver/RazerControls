"""Tests for MacroPlayer - macro execution."""

import threading
import time
from unittest.mock import MagicMock, call, patch

import pytest
from evdev import ecodes

from crates.profile_schema import MacroAction, MacroStep, MacroStepType
from services.macro_engine.player import MacroPlayer, play_macro_once

# --- Fixtures ---


@pytest.fixture
def mock_uinput():
    """Create a mock UInput device."""
    uinput = MagicMock()
    uinput.write = MagicMock()
    uinput.syn = MagicMock()
    uinput.close = MagicMock()
    return uinput


@pytest.fixture
def simple_macro():
    """Create a simple macro with key presses."""
    return MacroAction(
        id="simple",
        name="Simple Macro",
        steps=[
            MacroStep(type=MacroStepType.KEY_PRESS, key="A"),
            MacroStep(type=MacroStepType.KEY_PRESS, key="B"),
        ],
    )


@pytest.fixture
def complex_macro():
    """Create a complex macro with various step types."""
    return MacroAction(
        id="complex",
        name="Complex Macro",
        steps=[
            MacroStep(type=MacroStepType.KEY_DOWN, key="CTRL"),
            MacroStep(type=MacroStepType.KEY_PRESS, key="A"),
            MacroStep(type=MacroStepType.KEY_UP, key="CTRL"),
            MacroStep(type=MacroStepType.DELAY, delay_ms=10),
            MacroStep(type=MacroStepType.TEXT, text="hi"),
        ],
    )


@pytest.fixture
def repeat_macro():
    """Create a macro with repeats."""
    return MacroAction(
        id="repeat",
        name="Repeat Macro",
        steps=[MacroStep(type=MacroStepType.KEY_PRESS, key="X")],
        repeat_count=3,
        repeat_delay_ms=10,
    )


# --- Test Classes ---


class TestMacroPlayerInit:
    """Tests for MacroPlayer initialization."""

    def test_init_without_uinput(self):
        """Test init without uinput creates one on demand."""
        player = MacroPlayer()
        assert player._uinput is None
        assert player._owns_uinput is False

    def test_init_with_uinput(self, mock_uinput):
        """Test init with provided uinput."""
        player = MacroPlayer(uinput=mock_uinput)
        assert player._uinput == mock_uinput
        assert player._owns_uinput is False

    def test_set_uinput(self, mock_uinput):
        """Test setting uinput device."""
        player = MacroPlayer()
        player.set_uinput(mock_uinput)
        assert player._uinput == mock_uinput


class TestMacroPlayerState:
    """Tests for player state management."""

    def test_is_playing_initially_false(self):
        """Test is_playing is false initially."""
        player = MacroPlayer()
        assert player.is_playing() is False

    def test_cancel_sets_flag(self):
        """Test cancel sets cancelled flag."""
        player = MacroPlayer()
        player.cancel()
        assert player._cancelled is True


class TestKeyPress:
    """Tests for KEY_PRESS macro step."""

    def test_key_press_emits_down_and_up(self, mock_uinput, simple_macro):
        """Test KEY_PRESS emits down then up."""
        player = MacroPlayer(uinput=mock_uinput)
        player.play(simple_macro)

        calls = mock_uinput.write.call_args_list
        # A down, A up, B down, B up
        assert call(ecodes.EV_KEY, ecodes.KEY_A, 1) in calls
        assert call(ecodes.EV_KEY, ecodes.KEY_A, 0) in calls
        assert call(ecodes.EV_KEY, ecodes.KEY_B, 1) in calls
        assert call(ecodes.EV_KEY, ecodes.KEY_B, 0) in calls


class TestKeyDownUp:
    """Tests for KEY_DOWN and KEY_UP macro steps."""

    def test_key_down_emits_press(self, mock_uinput):
        """Test KEY_DOWN emits key press."""
        macro = MacroAction(
            id="test",
            name="Test",
            steps=[MacroStep(type=MacroStepType.KEY_DOWN, key="CTRL")],
        )
        player = MacroPlayer(uinput=mock_uinput)
        player.play(macro)

        mock_uinput.write.assert_called_with(ecodes.EV_KEY, ecodes.KEY_LEFTCTRL, 1)

    def test_key_up_emits_release(self, mock_uinput):
        """Test KEY_UP emits key release."""
        macro = MacroAction(
            id="test",
            name="Test",
            steps=[MacroStep(type=MacroStepType.KEY_UP, key="CTRL")],
        )
        player = MacroPlayer(uinput=mock_uinput)
        player.play(macro)

        mock_uinput.write.assert_called_with(ecodes.EV_KEY, ecodes.KEY_LEFTCTRL, 0)


class TestDelay:
    """Tests for DELAY macro step."""

    def test_delay_waits(self, mock_uinput):
        """Test DELAY step waits."""
        macro = MacroAction(
            id="test",
            name="Test",
            steps=[
                MacroStep(type=MacroStepType.KEY_PRESS, key="A"),
                MacroStep(type=MacroStepType.DELAY, delay_ms=50),
                MacroStep(type=MacroStepType.KEY_PRESS, key="B"),
            ],
        )
        player = MacroPlayer(uinput=mock_uinput)

        start = time.time()
        player.play(macro)
        elapsed = time.time() - start

        # Should have waited at least 50ms
        assert elapsed >= 0.05


class TestTextTyping:
    """Tests for TEXT macro step."""

    def test_types_lowercase(self, mock_uinput):
        """Test typing lowercase letters."""
        macro = MacroAction(
            id="test",
            name="Test",
            steps=[MacroStep(type=MacroStepType.TEXT, text="ab")],
        )
        player = MacroPlayer(uinput=mock_uinput)
        player.play(macro)

        calls = mock_uinput.write.call_args_list
        # Should type a and b (without shift)
        assert call(ecodes.EV_KEY, ecodes.KEY_A, 1) in calls
        assert call(ecodes.EV_KEY, ecodes.KEY_B, 1) in calls

    def test_types_uppercase_with_shift(self, mock_uinput):
        """Test typing uppercase uses shift."""
        macro = MacroAction(
            id="test",
            name="Test",
            steps=[MacroStep(type=MacroStepType.TEXT, text="A")],
        )
        player = MacroPlayer(uinput=mock_uinput)
        player.play(macro)

        calls = mock_uinput.write.call_args_list
        # Should press shift, A, then release
        assert call(ecodes.EV_KEY, ecodes.KEY_LEFTSHIFT, 1) in calls
        assert call(ecodes.EV_KEY, ecodes.KEY_A, 1) in calls
        assert call(ecodes.EV_KEY, ecodes.KEY_LEFTSHIFT, 0) in calls

    def test_types_digits(self, mock_uinput):
        """Test typing digits."""
        macro = MacroAction(
            id="test",
            name="Test",
            steps=[MacroStep(type=MacroStepType.TEXT, text="123")],
        )
        player = MacroPlayer(uinput=mock_uinput)
        player.play(macro)

        calls = mock_uinput.write.call_args_list
        assert call(ecodes.EV_KEY, ecodes.KEY_1, 1) in calls
        assert call(ecodes.EV_KEY, ecodes.KEY_2, 1) in calls
        assert call(ecodes.EV_KEY, ecodes.KEY_3, 1) in calls

    def test_types_special_chars(self, mock_uinput):
        """Test typing special characters."""
        macro = MacroAction(
            id="test",
            name="Test",
            steps=[MacroStep(type=MacroStepType.TEXT, text=" \n")],
        )
        player = MacroPlayer(uinput=mock_uinput)
        player.play(macro)

        calls = mock_uinput.write.call_args_list
        assert call(ecodes.EV_KEY, ecodes.KEY_SPACE, 1) in calls
        assert call(ecodes.EV_KEY, ecodes.KEY_ENTER, 1) in calls

    def test_types_shifted_punctuation(self, mock_uinput):
        """Test typing shifted punctuation like !."""
        macro = MacroAction(
            id="test",
            name="Test",
            steps=[MacroStep(type=MacroStepType.TEXT, text="!")],
        )
        player = MacroPlayer(uinput=mock_uinput)
        player.play(macro)

        calls = mock_uinput.write.call_args_list
        # ! is Shift+1
        assert call(ecodes.EV_KEY, ecodes.KEY_LEFTSHIFT, 1) in calls
        assert call(ecodes.EV_KEY, ecodes.KEY_1, 1) in calls


class TestRepeat:
    """Tests for macro repeating."""

    def test_repeats_specified_times(self, mock_uinput, repeat_macro):
        """Test macro repeats specified number of times."""
        player = MacroPlayer(uinput=mock_uinput)
        player.play(repeat_macro)

        # Count KEY_X presses (down events)
        x_presses = sum(
            1
            for c in mock_uinput.write.call_args_list
            if c == call(ecodes.EV_KEY, ecodes.KEY_X, 1)
        )
        assert x_presses == 3


class TestSpeedMultiplier:
    """Tests for speed multiplier."""

    def test_speed_multiplier_affects_delay(self, mock_uinput):
        """Test speed multiplier affects delays."""
        macro = MacroAction(
            id="test",
            name="Test",
            steps=[MacroStep(type=MacroStepType.DELAY, delay_ms=100)],
        )
        player = MacroPlayer(uinput=mock_uinput)

        # At 2x speed, 100ms delay should be ~50ms
        start = time.time()
        player.play(macro, speed_multiplier=2.0)
        elapsed = time.time() - start

        assert elapsed < 0.1  # Should be faster than normal


class TestCancellation:
    """Tests for macro cancellation."""

    def test_cancel_during_delay(self, mock_uinput):
        """Test cancellation during delay."""
        macro = MacroAction(
            id="test",
            name="Test",
            steps=[
                MacroStep(type=MacroStepType.KEY_PRESS, key="A"),
                MacroStep(type=MacroStepType.DELAY, delay_ms=500),
                MacroStep(type=MacroStepType.KEY_PRESS, key="B"),
            ],
        )
        player = MacroPlayer(uinput=mock_uinput)

        def cancel_after_delay():
            time.sleep(0.05)
            player.cancel()

        thread = threading.Thread(target=cancel_after_delay)
        thread.start()

        result = player.play(macro)
        thread.join()

        assert result is False
        # Should have pressed A but not B
        calls = mock_uinput.write.call_args_list
        assert call(ecodes.EV_KEY, ecodes.KEY_A, 1) in calls
        # B might not be called depending on timing


class TestStepCallback:
    """Tests for step callback."""

    def test_callback_called_for_each_step(self, mock_uinput, simple_macro):
        """Test callback is called for each step."""
        callback = MagicMock()
        player = MacroPlayer(uinput=mock_uinput)
        player.set_step_callback(callback)

        player.play(simple_macro)

        assert callback.call_count == 2


class TestPlaySteps:
    """Tests for play_steps method."""

    def test_play_steps_directly(self, mock_uinput):
        """Test playing steps without full macro."""
        steps = [
            MacroStep(type=MacroStepType.KEY_PRESS, key="A"),
            MacroStep(type=MacroStepType.KEY_PRESS, key="B"),
        ]
        player = MacroPlayer(uinput=mock_uinput)
        result = player.play_steps(steps)

        assert result is True
        calls = mock_uinput.write.call_args_list
        assert call(ecodes.EV_KEY, ecodes.KEY_A, 1) in calls
        assert call(ecodes.EV_KEY, ecodes.KEY_B, 1) in calls


class TestPlayMacroOnce:
    """Tests for play_macro_once convenience function."""

    def test_plays_and_cleans_up(self, simple_macro):
        """Test convenience function plays and cleans up."""
        with patch("services.macro_engine.player.UInput") as mock_uinput_class:
            mock_instance = MagicMock()
            mock_uinput_class.return_value = mock_instance

            result = play_macro_once(simple_macro)

            assert result is True
            mock_instance.close.assert_called_once()


class TestClose:
    """Tests for player cleanup."""

    def test_close_releases_owned_uinput(self):
        """Test close releases owned uinput."""
        with patch("services.macro_engine.player.UInput") as mock_uinput_class:
            mock_instance = MagicMock()
            mock_uinput_class.return_value = mock_instance

            player = MacroPlayer()
            # Trigger uinput creation
            player._ensure_uinput()
            assert player._owns_uinput is True

            player.close()

            mock_instance.close.assert_called_once()
            assert player._uinput is None

    def test_close_does_not_release_external_uinput(self, mock_uinput):
        """Test close does not release externally provided uinput."""
        player = MacroPlayer(uinput=mock_uinput)
        player.close()

        mock_uinput.close.assert_not_called()


class TestInvalidKeys:
    """Tests for invalid key handling."""

    def test_invalid_key_silently_skipped(self, mock_uinput):
        """Test invalid keys are silently skipped."""
        macro = MacroAction(
            id="test",
            name="Test",
            steps=[
                MacroStep(type=MacroStepType.KEY_PRESS, key="INVALID_KEY"),
                MacroStep(type=MacroStepType.KEY_PRESS, key="A"),
            ],
        )
        player = MacroPlayer(uinput=mock_uinput)
        result = player.play(macro)

        assert result is True
        # A should still be pressed even though first key was invalid
        calls = mock_uinput.write.call_args_list
        assert call(ecodes.EV_KEY, ecodes.KEY_A, 1) in calls


class TestComplexMacro:
    """Tests for complex macro with multiple step types."""

    def test_complex_macro_execution(self, mock_uinput, complex_macro):
        """Test complex macro executes all steps correctly."""
        player = MacroPlayer(uinput=mock_uinput)
        result = player.play(complex_macro)

        assert result is True
        calls = mock_uinput.write.call_args_list

        # Should have CTRL down, A press, CTRL up, then text "hi"
        ctrl_down = call(ecodes.EV_KEY, ecodes.KEY_LEFTCTRL, 1)
        ctrl_up = call(ecodes.EV_KEY, ecodes.KEY_LEFTCTRL, 0)

        assert ctrl_down in calls
        assert ctrl_up in calls
        # Text "hi" - h and i keys
        assert call(ecodes.EV_KEY, ecodes.KEY_H, 1) in calls
        assert call(ecodes.EV_KEY, ecodes.KEY_I, 1) in calls
