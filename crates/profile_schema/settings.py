"""Application settings with custom hotkey support."""

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class HotkeyBinding(BaseModel):
    """A hotkey binding for an action."""

    modifiers: list[str] = Field(default_factory=list)  # ["ctrl", "shift", "alt"]
    key: str = ""  # "1", "a", "f1", etc.
    enabled: bool = True

    def to_display_string(self) -> str:
        """Return human-readable hotkey string like 'Ctrl+Shift+1'."""
        if not self.key:
            return "Not set"
        parts = []
        if "ctrl" in self.modifiers:
            parts.append("Ctrl")
        if "alt" in self.modifiers:
            parts.append("Alt")
        if "shift" in self.modifiers:
            parts.append("Shift")
        parts.append(self.key.upper())
        return "+".join(parts)

    @classmethod
    def from_string(cls, s: str) -> "HotkeyBinding":
        """Parse a hotkey string like 'Ctrl+Shift+1'."""
        if not s or s == "Not set":
            return cls()
        parts = [p.strip().lower() for p in s.split("+")]
        modifiers = []
        key = ""
        for part in parts:
            if part in ("ctrl", "control"):
                modifiers.append("ctrl")
            elif part in ("alt",):
                modifiers.append("alt")
            elif part in ("shift",):
                modifiers.append("shift")
            else:
                key = part
        return cls(modifiers=modifiers, key=key, enabled=True)


class HotkeySettings(BaseModel):
    """Hotkey configuration for profile switching."""

    # Profile switch hotkeys (index 0-8 for profiles 1-9)
    profile_hotkeys: list[HotkeyBinding] = Field(default_factory=list)

    def get_default_hotkeys(self) -> list[HotkeyBinding]:
        """Return default Ctrl+Shift+1-9 hotkeys."""
        return [
            HotkeyBinding(modifiers=["ctrl", "shift"], key=str(i), enabled=True)
            for i in range(1, 10)
        ]

    def ensure_defaults(self) -> None:
        """Ensure we have 9 hotkey slots, filling with defaults if needed."""
        defaults = self.get_default_hotkeys()
        while len(self.profile_hotkeys) < 9:
            idx = len(self.profile_hotkeys)
            self.profile_hotkeys.append(defaults[idx])


class AppSettings(BaseModel):
    """Application-wide settings."""

    hotkeys: HotkeySettings = Field(default_factory=HotkeySettings)
    show_notifications: bool = True
    start_minimized: bool = False
    check_updates: bool = True

    def model_post_init(self, __context: Any) -> None:
        """Ensure hotkey defaults are set."""
        self.hotkeys.ensure_defaults()


class SettingsManager:
    """Manages application settings storage."""

    def __init__(self, config_dir: Path | None = None):
        if config_dir is None:
            config_dir = Path.home() / ".config" / "razer-control-center"
        self.config_dir = config_dir
        self.settings_file = config_dir / "settings.json"
        self._settings: AppSettings | None = None

    def load(self) -> AppSettings:
        """Load settings from disk, creating defaults if needed."""
        if self._settings is not None:
            return self._settings

        if self.settings_file.exists():
            try:
                data = json.loads(self.settings_file.read_text())
                self._settings = AppSettings.model_validate(data)
            except Exception as e:
                print(f"Error loading settings: {e}")
                self._settings = AppSettings()
        else:
            self._settings = AppSettings()

        return self._settings

    def save(self) -> bool:
        """Save settings to disk."""
        if self._settings is None:
            return False

        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            data = self._settings.model_dump(mode="json")
            self.settings_file.write_text(json.dumps(data, indent=2))
            return True
        except Exception as e:
            print(f"Error saving settings: {e}")
            return False

    @property
    def settings(self) -> AppSettings:
        """Get current settings, loading if needed."""
        return self.load()

    def update_hotkey(self, index: int, binding: HotkeyBinding) -> bool:
        """Update a profile hotkey binding."""
        settings = self.load()
        if 0 <= index < len(settings.hotkeys.profile_hotkeys):
            settings.hotkeys.profile_hotkeys[index] = binding
            return self.save()
        return False

    def reset_hotkeys(self) -> bool:
        """Reset hotkeys to defaults."""
        settings = self.load()
        settings.hotkeys.profile_hotkeys = settings.hotkeys.get_default_hotkeys()
        return self.save()
