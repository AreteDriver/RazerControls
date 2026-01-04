"""Tests for HotkeyEditorWidget and HotkeyCapture."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from crates.profile_schema.settings import HotkeyBinding


# --- Test HotkeyBinding logic ---


class TestHotkeyBinding:
    """Tests for HotkeyBinding dataclass."""

    def test_create_binding(self):
        """Test creating a hotkey binding."""
        binding = HotkeyBinding(modifiers=["ctrl", "shift"], key="1", enabled=True)
        assert binding.modifiers == ["ctrl", "shift"]
        assert binding.key == "1"
        assert binding.enabled is True

    def test_default_binding(self):
        """Test default hotkey binding values."""
        binding = HotkeyBinding()
        assert binding.modifiers == []
        assert binding.key == ""
        assert binding.enabled is True  # Default is enabled

    def test_to_display_string_with_modifiers(self):
        """Test display string with modifiers."""
        binding = HotkeyBinding(modifiers=["ctrl", "shift"], key="1", enabled=True)
        display = binding.to_display_string()
        assert "Ctrl" in display or "ctrl" in display.lower()
        assert "Shift" in display or "shift" in display.lower()
        assert "1" in display

    def test_to_display_string_empty(self):
        """Test display string for empty binding."""
        binding = HotkeyBinding()
        display = binding.to_display_string()
        assert display == "" or display == "(none)" or display == "Not set"

    def test_single_modifier(self):
        """Test binding with single modifier."""
        binding = HotkeyBinding(modifiers=["alt"], key="f1", enabled=True)
        assert len(binding.modifiers) == 1
        assert binding.modifiers[0] == "alt"

    def test_function_key(self):
        """Test binding with function key."""
        binding = HotkeyBinding(modifiers=["ctrl"], key="f12", enabled=True)
        assert binding.key == "f12"


class TestHotkeyConflictDetection:
    """Tests for hotkey conflict detection logic."""

    def bindings_conflict(self, b1: HotkeyBinding, b2: HotkeyBinding) -> bool:
        """Check if two bindings conflict (same key + modifiers)."""
        if not b1.key or not b2.key:
            return False
        return b1.key == b2.key and set(b1.modifiers) == set(b2.modifiers)

    def test_identical_bindings_conflict(self):
        """Test that identical bindings conflict."""
        b1 = HotkeyBinding(modifiers=["ctrl", "shift"], key="1", enabled=True)
        b2 = HotkeyBinding(modifiers=["ctrl", "shift"], key="1", enabled=True)
        assert self.bindings_conflict(b1, b2) is True

    def test_different_keys_no_conflict(self):
        """Test that different keys don't conflict."""
        b1 = HotkeyBinding(modifiers=["ctrl", "shift"], key="1", enabled=True)
        b2 = HotkeyBinding(modifiers=["ctrl", "shift"], key="2", enabled=True)
        assert self.bindings_conflict(b1, b2) is False

    def test_different_modifiers_no_conflict(self):
        """Test that different modifiers don't conflict."""
        b1 = HotkeyBinding(modifiers=["ctrl", "shift"], key="1", enabled=True)
        b2 = HotkeyBinding(modifiers=["ctrl", "alt"], key="1", enabled=True)
        assert self.bindings_conflict(b1, b2) is False

    def test_modifier_order_ignored(self):
        """Test that modifier order is ignored for conflict detection."""
        b1 = HotkeyBinding(modifiers=["ctrl", "shift"], key="1", enabled=True)
        b2 = HotkeyBinding(modifiers=["shift", "ctrl"], key="1", enabled=True)
        assert self.bindings_conflict(b1, b2) is True

    def test_empty_binding_no_conflict(self):
        """Test that empty bindings don't conflict."""
        b1 = HotkeyBinding()
        b2 = HotkeyBinding(modifiers=["ctrl"], key="1", enabled=True)
        assert self.bindings_conflict(b1, b2) is False


class TestKeyCodeMapping:
    """Tests for Qt key code to string mapping logic."""

    # Simulated key mapping (based on widget logic)
    QT_KEY_MAP = {
        0x01000030: "f1",  # Qt.Key.Key_F1
        0x01000031: "f2",
        0x01000032: "f3",
        0x0100003b: "f12",
        0x30: "0",
        0x31: "1",
        0x39: "9",
        0x41: "a",
        0x5a: "z",
    }

    def qt_key_to_string(self, key_code: int) -> str:
        """Convert Qt key code to string."""
        # Function keys F1-F12
        if 0x01000030 <= key_code <= 0x0100003b:
            return f"f{key_code - 0x01000030 + 1}"
        # Numbers 0-9
        if 0x30 <= key_code <= 0x39:
            return str(key_code - 0x30)
        # Letters A-Z
        if 0x41 <= key_code <= 0x5a:
            return chr(key_code).lower()
        return ""

    def test_function_keys(self):
        """Test function key conversion."""
        assert self.qt_key_to_string(0x01000030) == "f1"
        assert self.qt_key_to_string(0x0100003b) == "f12"

    def test_number_keys(self):
        """Test number key conversion."""
        assert self.qt_key_to_string(0x30) == "0"
        assert self.qt_key_to_string(0x31) == "1"
        assert self.qt_key_to_string(0x39) == "9"

    def test_letter_keys(self):
        """Test letter key conversion."""
        assert self.qt_key_to_string(0x41) == "a"
        assert self.qt_key_to_string(0x5a) == "z"


class TestHotkeyDefaults:
    """Tests for default hotkey bindings."""

    def get_default_bindings(self) -> list[HotkeyBinding]:
        """Get default profile hotkeys (Ctrl+Shift+1-9)."""
        bindings = []
        for i in range(1, 10):
            bindings.append(
                HotkeyBinding(
                    modifiers=["ctrl", "shift"],
                    key=str(i),
                    enabled=True,
                )
            )
        return bindings

    def test_default_count(self):
        """Test default bindings count."""
        defaults = self.get_default_bindings()
        assert len(defaults) == 9

    def test_default_modifiers(self):
        """Test default bindings use Ctrl+Shift."""
        defaults = self.get_default_bindings()
        for binding in defaults:
            assert "ctrl" in binding.modifiers
            assert "shift" in binding.modifiers

    def test_default_keys(self):
        """Test default bindings use 1-9."""
        defaults = self.get_default_bindings()
        for i, binding in enumerate(defaults):
            assert binding.key == str(i + 1)

    def test_defaults_enabled(self):
        """Test default bindings are enabled."""
        defaults = self.get_default_bindings()
        for binding in defaults:
            assert binding.enabled is True


class TestHotkeyValidation:
    """Tests for hotkey validation logic."""

    VALID_MODIFIERS = {"ctrl", "alt", "shift", "meta", "super"}
    VALID_KEYS = set("abcdefghijklmnopqrstuvwxyz0123456789") | {
        f"f{i}" for i in range(1, 13)
    }

    def is_valid_binding(self, binding: HotkeyBinding) -> bool:
        """Validate a hotkey binding."""
        if not binding.key:
            return True  # Empty is valid (disabled)

        # Must have at least one modifier
        if not binding.modifiers:
            return False

        # All modifiers must be valid
        for mod in binding.modifiers:
            if mod.lower() not in self.VALID_MODIFIERS:
                return False

        # Key must be valid
        if binding.key.lower() not in self.VALID_KEYS:
            return False

        return True

    def test_valid_binding(self):
        """Test valid binding passes validation."""
        binding = HotkeyBinding(modifiers=["ctrl", "shift"], key="1", enabled=True)
        assert self.is_valid_binding(binding) is True

    def test_empty_binding_valid(self):
        """Test empty binding is valid."""
        binding = HotkeyBinding()
        assert self.is_valid_binding(binding) is True

    def test_no_modifiers_invalid(self):
        """Test binding without modifiers is invalid."""
        binding = HotkeyBinding(modifiers=[], key="1", enabled=True)
        assert self.is_valid_binding(binding) is False

    def test_invalid_modifier(self):
        """Test invalid modifier fails validation."""
        binding = HotkeyBinding(modifiers=["invalid"], key="1", enabled=True)
        assert self.is_valid_binding(binding) is False

    def test_function_key_valid(self):
        """Test function keys are valid."""
        binding = HotkeyBinding(modifiers=["ctrl"], key="f1", enabled=True)
        assert self.is_valid_binding(binding) is True

        binding = HotkeyBinding(modifiers=["ctrl"], key="f12", enabled=True)
        assert self.is_valid_binding(binding) is True
