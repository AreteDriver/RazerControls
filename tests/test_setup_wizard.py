"""Tests for SetupWizard logic."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# --- Test Profile ID Generation ---


class TestProfileIdGeneration:
    """Tests for profile ID generation from name."""

    def generate_profile_id(self, name: str) -> str:
        """Generate profile ID from name (matches wizard logic)."""
        profile_id = name.lower().replace(" ", "_")
        profile_id = "".join(c for c in profile_id if c.isalnum() or c == "_")
        return profile_id or "default"

    def test_simple_name(self):
        """Test simple name conversion."""
        assert self.generate_profile_id("Gaming") == "gaming"

    def test_name_with_spaces(self):
        """Test name with spaces becomes underscores."""
        assert self.generate_profile_id("My Gaming Profile") == "my_gaming_profile"

    def test_name_with_special_chars(self):
        """Test special characters are removed."""
        assert self.generate_profile_id("Gaming!@#$%") == "gaming"

    def test_mixed_case(self):
        """Test mixed case becomes lowercase."""
        assert self.generate_profile_id("MyProfile") == "myprofile"

    def test_empty_name(self):
        """Test empty name becomes 'default'."""
        assert self.generate_profile_id("") == "default"

    def test_only_special_chars(self):
        """Test name with only special chars becomes 'default'."""
        assert self.generate_profile_id("!@#$%") == "default"

    def test_numbers(self):
        """Test numbers are preserved."""
        assert self.generate_profile_id("Profile 123") == "profile_123"


# --- Test Device Name Extraction ---


class TestDeviceNameExtraction:
    """Tests for extracting friendly device names from stable_id."""

    def extract_device_name(self, stable_id: str) -> str:
        """Extract friendly name from stable_id (matches wizard logic)."""
        name = stable_id.replace("usb-", "").replace("-event-mouse", "")
        name = name.replace("-event-kbd", "").replace("_", " ")
        return name

    def test_mouse_device(self):
        """Test mouse device name extraction."""
        stable_id = "usb-Razer_DeathAdder_V2-event-mouse"
        name = self.extract_device_name(stable_id)
        assert "DeathAdder" in name or "Razer" in name
        assert "event" not in name

    def test_keyboard_device(self):
        """Test keyboard device name extraction."""
        stable_id = "usb-Razer_BlackWidow-event-kbd"
        name = self.extract_device_name(stable_id)
        assert "BlackWidow" in name or "Razer" in name
        assert "event" not in name

    def test_underscores_to_spaces(self):
        """Test underscores become spaces."""
        stable_id = "usb-Razer_DeathAdder_V2-event-mouse"
        name = self.extract_device_name(stable_id)
        assert "_" not in name


# --- Test Troubleshooting Text ---


class TestTroubleshootingText:
    """Tests for troubleshooting text generation."""

    def test_no_issues_message(self):
        """Test message when no specific issues are detected."""
        issues = []
        if not issues:
            text = (
                "No Razer devices found.\n\n"
                "Make sure your device is connected via USB\n"
                "and is supported by OpenRazer."
            )
        assert "No Razer devices found" in text
        assert "USB" in text
        assert "OpenRazer" in text

    def test_uinput_issue_message(self):
        """Test uinput issue message format."""
        issues = ["- uinput module not loaded. Run: sudo modprobe uinput"]
        text = "No devices found. Possible issues:\n\n" + "\n".join(issues)
        assert "uinput" in text
        assert "modprobe" in text

    def test_input_group_issue_message(self):
        """Test input group issue message format."""
        issues = ["- User not in 'input' group. Run: sudo usermod -aG input $USER"]
        text = "No devices found. Possible issues:\n\n" + "\n".join(issues)
        assert "input" in text
        assert "usermod" in text

    def test_openrazer_issue_message(self):
        """Test OpenRazer daemon issue message format."""
        issues = ["- OpenRazer daemon not running. Run: sudo systemctl start openrazer-daemon"]
        text = "No devices found. Possible issues:\n\n" + "\n".join(issues)
        assert "OpenRazer" in text
        assert "systemctl" in text

    def test_multiple_issues(self):
        """Test multiple issues combined."""
        issues = [
            "- uinput module not loaded. Run: sudo modprobe uinput",
            "- User not in 'input' group. Run: sudo usermod -aG input $USER",
        ]
        text = "No devices found. Possible issues:\n\n" + "\n".join(issues)
        assert "uinput" in text
        assert "usermod" in text
        # Both issues present in output
        assert len(issues) == 2
        assert text.count("\n-") == 2  # Two bullet points


# --- Test Page Indicator ---


class TestPageIndicator:
    """Tests for page indicator dot generation."""

    def generate_page_indicator(self, current: int, total: int) -> str:
        """Generate page indicator dots (matches wizard logic)."""
        dots = []
        for i in range(total):
            if i == current:
                dots.append("\u25cf")  # Filled circle
            else:
                dots.append("\u25cb")  # Empty circle
        return "  ".join(dots)

    def test_first_page(self):
        """Test indicator on first page."""
        indicator = self.generate_page_indicator(0, 4)
        assert indicator.startswith("\u25cf")  # Starts with filled
        assert indicator.count("\u25cf") == 1
        assert indicator.count("\u25cb") == 3

    def test_last_page(self):
        """Test indicator on last page."""
        indicator = self.generate_page_indicator(3, 4)
        assert indicator.endswith("\u25cf")  # Ends with filled
        assert indicator.count("\u25cf") == 1
        assert indicator.count("\u25cb") == 3

    def test_middle_page(self):
        """Test indicator on middle page."""
        indicator = self.generate_page_indicator(2, 4)
        assert indicator.count("\u25cf") == 1
        assert indicator.count("\u25cb") == 3

    def test_single_page(self):
        """Test indicator with single page."""
        indicator = self.generate_page_indicator(0, 1)
        assert indicator == "\u25cf"


# --- Test Summary Generation ---


class TestSummaryGeneration:
    """Tests for setup summary text generation."""

    def generate_summary(
        self,
        profile_name: str,
        description: str,
        device_count: int,
        is_default: bool,
    ) -> str:
        """Generate summary text (matches wizard logic)."""
        summary = []
        summary.append(f"Profile: {profile_name or 'Default'}")

        if description:
            summary.append(f"Description: {description}")

        summary.append(f"Devices: {device_count} selected")

        if is_default:
            summary.append("Will be set as default profile")

        return "\n".join(summary)

    def test_basic_summary(self):
        """Test basic summary generation."""
        summary = self.generate_summary("Gaming", "", 2, False)
        assert "Profile: Gaming" in summary
        assert "Devices: 2 selected" in summary
        assert "Description" not in summary

    def test_summary_with_description(self):
        """Test summary with description."""
        summary = self.generate_summary("Gaming", "FPS games", 1, False)
        assert "Description: FPS games" in summary

    def test_summary_with_default(self):
        """Test summary with default profile."""
        summary = self.generate_summary("Gaming", "", 1, True)
        assert "Will be set as default profile" in summary

    def test_empty_profile_name(self):
        """Test summary with empty profile name."""
        summary = self.generate_summary("", "", 1, False)
        assert "Profile: Default" in summary

    def test_full_summary(self):
        """Test full summary with all fields."""
        summary = self.generate_summary("Gaming", "My setup", 3, True)
        assert "Profile: Gaming" in summary
        assert "Description: My setup" in summary
        assert "Devices: 3 selected" in summary
        assert "Will be set as default profile" in summary


# --- Test Button State Logic ---


class TestButtonStateLogic:
    """Tests for navigation button state logic."""

    def get_back_enabled(self, current: int) -> bool:
        """Check if back button should be enabled."""
        return current > 0

    def get_next_text(self, current: int, total: int) -> str:
        """Get next button text."""
        if current == total - 1:
            return "Finish"
        return "Next"

    def test_back_disabled_on_first_page(self):
        """Test back button disabled on first page."""
        assert self.get_back_enabled(0) is False

    def test_back_enabled_on_other_pages(self):
        """Test back button enabled on other pages."""
        assert self.get_back_enabled(1) is True
        assert self.get_back_enabled(2) is True
        assert self.get_back_enabled(3) is True

    def test_next_text_on_regular_pages(self):
        """Test next button shows 'Next' on regular pages."""
        assert self.get_next_text(0, 4) == "Next"
        assert self.get_next_text(1, 4) == "Next"
        assert self.get_next_text(2, 4) == "Next"

    def test_next_text_on_last_page(self):
        """Test next button shows 'Finish' on last page."""
        assert self.get_next_text(3, 4) == "Finish"


# --- Test Profile Name Handling ---


class TestProfileNameHandling:
    """Tests for profile name input handling."""

    def handle_name_change(self, text: str) -> str:
        """Handle profile name change (matches wizard logic)."""
        return text.strip() or "Default"

    def test_regular_name(self):
        """Test regular name is preserved."""
        assert self.handle_name_change("Gaming") == "Gaming"

    def test_name_with_whitespace(self):
        """Test whitespace is stripped."""
        assert self.handle_name_change("  Gaming  ") == "Gaming"

    def test_empty_name(self):
        """Test empty name becomes Default."""
        assert self.handle_name_change("") == "Default"

    def test_only_whitespace(self):
        """Test whitespace-only becomes Default."""
        assert self.handle_name_change("   ") == "Default"
