"""Tests for application settings module."""

import json
import tempfile
from pathlib import Path

import pytest

from crates.profile_schema.settings import (
    AppSettings,
    HotkeyBinding,
    HotkeySettings,
    SettingsManager,
)


class TestHotkeyBinding:
    """Tests for HotkeyBinding model."""

    def test_default_values(self):
        """Default binding should have empty modifiers and key."""
        binding = HotkeyBinding()
        assert binding.modifiers == []
        assert binding.key == ""
        assert binding.enabled is True

    def test_with_values(self):
        """Binding should store provided values."""
        binding = HotkeyBinding(modifiers=["ctrl", "shift"], key="1", enabled=False)
        assert binding.modifiers == ["ctrl", "shift"]
        assert binding.key == "1"
        assert binding.enabled is False

    def test_to_display_string_empty(self):
        """Empty binding should display 'Not set'."""
        binding = HotkeyBinding()
        assert binding.to_display_string() == "Not set"

    def test_to_display_string_simple(self):
        """Simple binding should format correctly."""
        binding = HotkeyBinding(modifiers=["ctrl"], key="a")
        assert binding.to_display_string() == "Ctrl+A"

    def test_to_display_string_multiple_modifiers(self):
        """Multiple modifiers should be in order."""
        binding = HotkeyBinding(modifiers=["ctrl", "alt", "shift"], key="f1")
        assert binding.to_display_string() == "Ctrl+Alt+Shift+F1"

    def test_to_display_string_ctrl_shift(self):
        """Ctrl+Shift+1 should format correctly."""
        binding = HotkeyBinding(modifiers=["ctrl", "shift"], key="1")
        assert binding.to_display_string() == "Ctrl+Shift+1"

    def test_to_display_string_alt_only(self):
        """Alt+X should format correctly."""
        binding = HotkeyBinding(modifiers=["alt"], key="x")
        assert binding.to_display_string() == "Alt+X"

    def test_from_string_empty(self):
        """Empty string should return empty binding."""
        binding = HotkeyBinding.from_string("")
        assert binding.modifiers == []
        assert binding.key == ""

    def test_from_string_not_set(self):
        """'Not set' should return empty binding."""
        binding = HotkeyBinding.from_string("Not set")
        assert binding.modifiers == []
        assert binding.key == ""

    def test_from_string_simple(self):
        """Simple hotkey string should parse correctly."""
        binding = HotkeyBinding.from_string("Ctrl+A")
        assert binding.modifiers == ["ctrl"]
        assert binding.key == "a"
        assert binding.enabled is True

    def test_from_string_multiple_modifiers(self):
        """Multiple modifiers should parse correctly."""
        binding = HotkeyBinding.from_string("Ctrl+Alt+Shift+F1")
        assert set(binding.modifiers) == {"ctrl", "alt", "shift"}
        assert binding.key == "f1"

    def test_from_string_control_alias(self):
        """'Control' should be parsed as 'ctrl'."""
        binding = HotkeyBinding.from_string("Control+X")
        assert binding.modifiers == ["ctrl"]
        assert binding.key == "x"

    def test_from_string_case_insensitive(self):
        """Parsing should be case insensitive."""
        binding = HotkeyBinding.from_string("CTRL+SHIFT+A")
        assert set(binding.modifiers) == {"ctrl", "shift"}
        assert binding.key == "a"

    def test_roundtrip(self):
        """to_display_string and from_string should roundtrip."""
        original = HotkeyBinding(modifiers=["ctrl", "shift"], key="5")
        display = original.to_display_string()
        parsed = HotkeyBinding.from_string(display)
        assert set(parsed.modifiers) == set(original.modifiers)
        assert parsed.key == original.key


class TestHotkeySettings:
    """Tests for HotkeySettings model."""

    def test_default_empty(self):
        """Default settings should have empty hotkeys list."""
        settings = HotkeySettings()
        assert settings.profile_hotkeys == []

    def test_get_default_hotkeys(self):
        """Should return 9 default Ctrl+Shift+1-9 hotkeys."""
        settings = HotkeySettings()
        defaults = settings.get_default_hotkeys()

        assert len(defaults) == 9
        for i, binding in enumerate(defaults):
            assert binding.modifiers == ["ctrl", "shift"]
            assert binding.key == str(i + 1)
            assert binding.enabled is True

    def test_ensure_defaults_empty(self):
        """ensure_defaults should fill empty list with defaults."""
        settings = HotkeySettings()
        settings.ensure_defaults()

        assert len(settings.profile_hotkeys) == 9
        assert settings.profile_hotkeys[0].key == "1"
        assert settings.profile_hotkeys[8].key == "9"

    def test_ensure_defaults_partial(self):
        """ensure_defaults should fill remaining slots."""
        settings = HotkeySettings(
            profile_hotkeys=[
                HotkeyBinding(modifiers=["alt"], key="a"),
                HotkeyBinding(modifiers=["alt"], key="b"),
            ]
        )
        settings.ensure_defaults()

        assert len(settings.profile_hotkeys) == 9
        # First two should be preserved
        assert settings.profile_hotkeys[0].key == "a"
        assert settings.profile_hotkeys[1].key == "b"
        # Rest should be defaults
        assert settings.profile_hotkeys[2].key == "3"
        assert settings.profile_hotkeys[8].key == "9"

    def test_ensure_defaults_full(self):
        """ensure_defaults should not modify full list."""
        custom = [
            HotkeyBinding(modifiers=["alt"], key=str(i))
            for i in range(9)
        ]
        settings = HotkeySettings(profile_hotkeys=custom)
        settings.ensure_defaults()

        assert len(settings.profile_hotkeys) == 9
        for i, binding in enumerate(settings.profile_hotkeys):
            assert binding.modifiers == ["alt"]
            assert binding.key == str(i)


class TestAppSettings:
    """Tests for AppSettings model."""

    def test_default_values(self):
        """Default settings should have expected values."""
        settings = AppSettings()
        assert settings.show_notifications is True
        assert settings.start_minimized is False
        assert settings.check_updates is True

    def test_hotkeys_initialized(self):
        """Hotkeys should be initialized with defaults."""
        settings = AppSettings()
        assert len(settings.hotkeys.profile_hotkeys) == 9

    def test_custom_values(self):
        """Custom values should be preserved."""
        settings = AppSettings(
            show_notifications=False,
            start_minimized=True,
            check_updates=False,
        )
        assert settings.show_notifications is False
        assert settings.start_minimized is True
        assert settings.check_updates is False

    def test_serialization(self):
        """Settings should serialize to JSON correctly."""
        settings = AppSettings()
        data = settings.model_dump(mode="json")

        assert "hotkeys" in data
        assert "show_notifications" in data
        assert len(data["hotkeys"]["profile_hotkeys"]) == 9

    def test_deserialization(self):
        """Settings should deserialize from JSON correctly."""
        data = {
            "hotkeys": {
                "profile_hotkeys": [
                    {"modifiers": ["ctrl"], "key": "1", "enabled": True}
                ]
            },
            "show_notifications": False,
        }
        settings = AppSettings.model_validate(data)

        assert settings.show_notifications is False
        # Should fill to 9 hotkeys
        assert len(settings.hotkeys.profile_hotkeys) == 9
        assert settings.hotkeys.profile_hotkeys[0].key == "1"


class TestSettingsManager:
    """Tests for SettingsManager."""

    def test_init_default_path(self):
        """Default path should be in user config."""
        manager = SettingsManager()
        assert manager.config_dir == Path.home() / ".config" / "razer-control-center"
        assert manager.settings_file.name == "settings.json"

    def test_init_custom_path(self):
        """Custom path should be used."""
        custom = Path("/tmp/test-config")
        manager = SettingsManager(config_dir=custom)
        assert manager.config_dir == custom
        assert manager.settings_file == custom / "settings.json"

    def test_load_creates_defaults(self):
        """Load should create default settings if file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SettingsManager(config_dir=Path(tmpdir))
            settings = manager.load()

            assert settings is not None
            assert len(settings.hotkeys.profile_hotkeys) == 9

    def test_load_caches_settings(self):
        """Load should cache settings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SettingsManager(config_dir=Path(tmpdir))
            settings1 = manager.load()
            settings2 = manager.load()

            assert settings1 is settings2

    def test_load_reads_file(self):
        """Load should read from existing file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            config_dir.mkdir(exist_ok=True)

            # Write custom settings
            settings_file = config_dir / "settings.json"
            settings_file.write_text(json.dumps({
                "hotkeys": {
                    "profile_hotkeys": [
                        {"modifiers": ["alt"], "key": "x", "enabled": False}
                    ]
                },
                "show_notifications": False,
            }))

            manager = SettingsManager(config_dir=config_dir)
            settings = manager.load()

            assert settings.show_notifications is False
            assert settings.hotkeys.profile_hotkeys[0].key == "x"
            assert settings.hotkeys.profile_hotkeys[0].enabled is False

    def test_load_handles_invalid_json(self):
        """Load should handle invalid JSON gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            config_dir.mkdir(exist_ok=True)

            settings_file = config_dir / "settings.json"
            settings_file.write_text("not valid json")

            manager = SettingsManager(config_dir=config_dir)
            settings = manager.load()

            # Should return defaults
            assert settings is not None
            assert len(settings.hotkeys.profile_hotkeys) == 9

    def test_save_creates_directory(self):
        """Save should create config directory if needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "new" / "nested" / "dir"
            manager = SettingsManager(config_dir=config_dir)

            # Load to create settings
            manager.load()
            result = manager.save()

            assert result is True
            assert config_dir.exists()
            assert manager.settings_file.exists()

    def test_save_writes_json(self):
        """Save should write valid JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SettingsManager(config_dir=Path(tmpdir))
            manager.load()
            manager.save()

            # Read and verify
            data = json.loads(manager.settings_file.read_text())
            assert "hotkeys" in data
            assert "show_notifications" in data

    def test_save_without_load(self):
        """Save without load should return False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SettingsManager(config_dir=Path(tmpdir))
            result = manager.save()

            assert result is False

    def test_settings_property(self):
        """settings property should load on demand."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SettingsManager(config_dir=Path(tmpdir))

            # Access via property
            settings = manager.settings

            assert settings is not None
            assert len(settings.hotkeys.profile_hotkeys) == 9

    def test_update_hotkey_valid(self):
        """update_hotkey should update and save."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SettingsManager(config_dir=Path(tmpdir))
            manager.load()

            new_binding = HotkeyBinding(modifiers=["alt"], key="z")
            result = manager.update_hotkey(0, new_binding)

            assert result is True
            assert manager.settings.hotkeys.profile_hotkeys[0].key == "z"

            # Verify persisted
            manager2 = SettingsManager(config_dir=Path(tmpdir))
            assert manager2.settings.hotkeys.profile_hotkeys[0].key == "z"

    def test_update_hotkey_invalid_index(self):
        """update_hotkey should return False for invalid index."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SettingsManager(config_dir=Path(tmpdir))
            manager.load()

            new_binding = HotkeyBinding(modifiers=["alt"], key="z")

            assert manager.update_hotkey(-1, new_binding) is False
            assert manager.update_hotkey(100, new_binding) is False

    def test_reset_hotkeys(self):
        """reset_hotkeys should restore defaults."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SettingsManager(config_dir=Path(tmpdir))
            manager.load()

            # Modify a hotkey
            manager.settings.hotkeys.profile_hotkeys[0] = HotkeyBinding(
                modifiers=["alt"], key="custom"
            )
            manager.save()

            # Reset
            result = manager.reset_hotkeys()

            assert result is True
            assert manager.settings.hotkeys.profile_hotkeys[0].key == "1"
            assert manager.settings.hotkeys.profile_hotkeys[0].modifiers == ["ctrl", "shift"]

            # Verify persisted
            manager2 = SettingsManager(config_dir=Path(tmpdir))
            assert manager2.settings.hotkeys.profile_hotkeys[0].key == "1"
