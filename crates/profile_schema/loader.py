"""Profile loader - handles loading and saving profiles."""

import json
from pathlib import Path
from typing import Optional

from .schema import Profile, MacroAction


class ProfileLoader:
    """Loads and saves profiles from the config directory."""

    def __init__(self, config_dir: Optional[Path] = None):
        if config_dir is None:
            config_dir = Path.home() / ".config" / "razer-control-center"
        self.config_dir = config_dir
        self.profiles_dir = config_dir / "profiles"
        self.macros_file = config_dir / "macros.json"
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        """Ensure config directories exist."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.profiles_dir.mkdir(exist_ok=True)

    def list_profiles(self) -> list[str]:
        """List all profile IDs."""
        profiles = []
        for f in self.profiles_dir.glob("*.json"):
            profiles.append(f.stem)
        return sorted(profiles)

    def load_profile(self, profile_id: str) -> Optional[Profile]:
        """Load a profile by ID."""
        path = self.profiles_dir / f"{profile_id}.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text())
            return Profile.model_validate(data)
        except Exception as e:
            print(f"Error loading profile {profile_id}: {e}")
            return None

    def save_profile(self, profile: Profile) -> bool:
        """Save a profile to disk."""
        path = self.profiles_dir / f"{profile.id}.json"
        try:
            data = profile.model_dump(mode="json")
            path.write_text(json.dumps(data, indent=2))
            return True
        except Exception as e:
            print(f"Error saving profile {profile.id}: {e}")
            return False

    def delete_profile(self, profile_id: str) -> bool:
        """Delete a profile."""
        path = self.profiles_dir / f"{profile_id}.json"
        if path.exists():
            path.unlink()
            return True
        return False

    def load_global_macros(self) -> list[MacroAction]:
        """Load global macros."""
        if not self.macros_file.exists():
            return []
        try:
            data = json.loads(self.macros_file.read_text())
            return [MacroAction.model_validate(m) for m in data]
        except Exception as e:
            print(f"Error loading macros: {e}")
            return []

    def save_global_macros(self, macros: list[MacroAction]) -> bool:
        """Save global macros."""
        try:
            data = [m.model_dump(mode="json") for m in macros]
            self.macros_file.write_text(json.dumps(data, indent=2))
            return True
        except Exception as e:
            print(f"Error saving macros: {e}")
            return False

    def get_active_profile_path(self) -> Path:
        """Get path to the active profile marker file."""
        return self.config_dir / "active_profile"

    def get_active_profile_id(self) -> Optional[str]:
        """Get the currently active profile ID."""
        path = self.get_active_profile_path()
        if path.exists():
            return path.read_text().strip()
        return None

    def set_active_profile(self, profile_id: str) -> None:
        """Set the active profile."""
        path = self.get_active_profile_path()
        path.write_text(profile_id)

    def load_active_profile(self) -> Optional[Profile]:
        """Load the currently active profile."""
        profile_id = self.get_active_profile_id()
        if profile_id:
            return self.load_profile(profile_id)
        # Fall back to default profile
        for pid in self.list_profiles():
            profile = self.load_profile(pid)
            if profile and profile.is_default:
                return profile
        return None
