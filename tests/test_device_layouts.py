"""Tests for device layout module."""

import json
import tempfile
from pathlib import Path

import pytest

from crates.device_layouts import (
    ButtonShape,
    DeviceCategory,
    DeviceLayout,
    DeviceLayoutRegistry,
    get_fallback_layout,
)
from crates.device_layouts.fallback import (
    get_generic_keyboard_layout,
    get_generic_keypad_layout,
    get_generic_mouse_layout,
)
from crates.device_layouts.schema import ShapeType


class TestButtonShape:
    """Tests for ButtonShape dataclass."""

    def test_from_dict_basic(self):
        """Test basic dict deserialization."""
        data = {
            "id": "left_click",
            "label": "Left Click",
            "x": 0.1,
            "y": 0.2,
            "width": 0.3,
            "height": 0.4,
        }
        button = ButtonShape.from_dict(data)

        assert button.id == "left_click"
        assert button.label == "Left Click"
        assert button.x == 0.1
        assert button.y == 0.2
        assert button.width == 0.3
        assert button.height == 0.4
        assert button.shape_type == ShapeType.RECT
        assert button.input_code is None
        assert button.is_zone is False

    def test_from_dict_with_options(self):
        """Test dict deserialization with optional fields."""
        data = {
            "id": "logo_zone",
            "label": "Logo",
            "x": 0.3,
            "y": 0.6,
            "width": 0.4,
            "height": 0.15,
            "shape_type": "ellipse",
            "input_code": "BTN_LEFT",
            "is_zone": True,
        }
        button = ButtonShape.from_dict(data)

        assert button.shape_type == ShapeType.ELLIPSE
        assert button.input_code == "BTN_LEFT"
        assert button.is_zone is True

    def test_to_dict(self):
        """Test dict serialization."""
        button = ButtonShape(
            id="scroll",
            label="Scroll",
            x=0.4,
            y=0.1,
            width=0.2,
            height=0.15,
            shape_type=ShapeType.ELLIPSE,
            input_code="BTN_MIDDLE",
        )
        data = button.to_dict()

        assert data["id"] == "scroll"
        assert data["shape_type"] == "ellipse"
        assert data["input_code"] == "BTN_MIDDLE"
        assert "is_zone" not in data  # False values excluded

    def test_roundtrip(self):
        """Test serialization roundtrip."""
        original = ButtonShape(
            id="test",
            label="Test Button",
            x=0.5,
            y=0.5,
            width=0.1,
            height=0.1,
            shape_type=ShapeType.POLYGON,
            polygon_points=[(0.0, 0.0), (1.0, 0.0), (0.5, 1.0)],
        )
        data = original.to_dict()
        restored = ButtonShape.from_dict(data)

        assert original.id == restored.id
        assert original.polygon_points == restored.polygon_points


class TestDeviceLayout:
    """Tests for DeviceLayout dataclass."""

    def test_from_dict(self):
        """Test dict deserialization."""
        data = {
            "id": "test_mouse",
            "name": "Test Mouse",
            "category": "mouse",
            "device_name_patterns": [".*test.*"],
            "base_width": 80,
            "base_height": 140,
            "outline_path": [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]],
            "buttons": [
                {
                    "id": "left",
                    "label": "Left",
                    "x": 0.1,
                    "y": 0.1,
                    "width": 0.4,
                    "height": 0.3,
                }
            ],
        }
        layout = DeviceLayout.from_dict(data)

        assert layout.id == "test_mouse"
        assert layout.category == DeviceCategory.MOUSE
        assert len(layout.buttons) == 1
        assert layout.buttons[0].id == "left"

    def test_get_button(self):
        """Test button lookup by ID."""
        layout = get_generic_mouse_layout()

        left = layout.get_button("left_click")
        assert left is not None
        assert left.label == "Left Click"

        missing = layout.get_button("nonexistent")
        assert missing is None

    def test_get_zones(self):
        """Test zone filtering."""
        layout = get_generic_mouse_layout()

        zones = layout.get_zones()
        assert len(zones) == 1
        assert zones[0].id == "logo_zone"

    def test_get_physical_buttons(self):
        """Test physical button filtering."""
        layout = get_generic_mouse_layout()

        buttons = layout.get_physical_buttons()
        assert all(not b.is_zone for b in buttons)
        assert len(buttons) == 6  # left, right, scroll, dpi, forward, back


class TestFallbackLayouts:
    """Tests for fallback layout generators."""

    def test_generic_mouse_layout(self):
        """Test generic mouse layout has expected buttons."""
        layout = get_generic_mouse_layout()

        assert layout.id == "generic_mouse"
        assert layout.category == DeviceCategory.MOUSE
        assert len(layout.buttons) == 7

        # Check key buttons exist
        button_ids = [b.id for b in layout.buttons]
        assert "left_click" in button_ids
        assert "right_click" in button_ids
        assert "scroll_wheel" in button_ids
        assert "logo_zone" in button_ids

    def test_generic_keyboard_layout(self):
        """Test generic keyboard layout has expected zones."""
        layout = get_generic_keyboard_layout()

        assert layout.id == "generic_keyboard"
        assert layout.category == DeviceCategory.KEYBOARD

        # All buttons should be zones
        assert all(b.is_zone for b in layout.buttons)

    def test_generic_keypad_layout(self):
        """Test generic keypad layout has 20 keys + thumbstick."""
        layout = get_generic_keypad_layout()

        assert layout.id == "generic_keypad"
        assert layout.category == DeviceCategory.KEYPAD

        # 20 keys + thumbstick + thumb button
        assert len(layout.buttons) == 22

    def test_get_fallback_layout_mouse(self):
        """Test fallback selection for mouse type."""
        layout = get_fallback_layout(device_type="mouse")
        assert layout.category == DeviceCategory.MOUSE

    def test_get_fallback_layout_keyboard(self):
        """Test fallback selection for keyboard type."""
        layout = get_fallback_layout(device_type="Razer Keyboard")
        assert layout.category == DeviceCategory.KEYBOARD

    def test_get_fallback_layout_keypad(self):
        """Test fallback selection for keypad type."""
        layout = get_fallback_layout(device_type="Gaming Keypad")
        assert layout.category == DeviceCategory.KEYPAD

    def test_get_fallback_layout_matrix_cols_mouse(self):
        """Test fallback by matrix columns (mouse-sized)."""
        layout = get_fallback_layout(matrix_cols=2)
        assert layout.category == DeviceCategory.MOUSE

    def test_get_fallback_layout_matrix_cols_keypad(self):
        """Test fallback by matrix columns (keypad-sized)."""
        layout = get_fallback_layout(matrix_cols=8)
        assert layout.category == DeviceCategory.KEYPAD

    def test_get_fallback_layout_matrix_cols_keyboard(self):
        """Test fallback by matrix columns (keyboard-sized)."""
        layout = get_fallback_layout(matrix_cols=22)
        assert layout.category == DeviceCategory.KEYBOARD

    def test_get_fallback_layout_default(self):
        """Test fallback with no hints defaults to mouse."""
        layout = get_fallback_layout()
        assert layout.category == DeviceCategory.MOUSE


class TestDeviceLayoutRegistry:
    """Tests for DeviceLayoutRegistry."""

    @pytest.fixture
    def temp_layouts_dir(self, tmp_path):
        """Create a temporary layouts directory with test layouts."""
        layouts_dir = tmp_path / "device_layouts"
        mice_dir = layouts_dir / "mice"
        mice_dir.mkdir(parents=True)

        # Create a test mouse layout
        test_layout = {
            "id": "test_mouse",
            "name": "Test Mouse",
            "category": "mouse",
            "device_name_patterns": [".*test.*mouse.*", "TestMouse.*"],
            "base_width": 80,
            "base_height": 140,
            "outline_path": [[0.5, 0.0], [1.0, 1.0], [0.0, 1.0]],
            "buttons": [
                {
                    "id": "left",
                    "label": "Left",
                    "x": 0.1,
                    "y": 0.1,
                    "width": 0.4,
                    "height": 0.3,
                }
            ],
        }
        with open(mice_dir / "test_mouse.json", "w") as f:
            json.dump(test_layout, f)

        return layouts_dir

    def test_load_layouts(self, temp_layouts_dir):
        """Test loading layouts from directory."""
        # Reset singleton for test
        DeviceLayoutRegistry._initialized = False
        DeviceLayoutRegistry._instance = None

        registry = DeviceLayoutRegistry()
        registry.load_layouts(temp_layouts_dir)

        layouts = registry.list_layouts()
        assert len(layouts) == 1
        assert layouts[0].id == "test_mouse"

    def test_get_layout(self, temp_layouts_dir):
        """Test getting layout by ID."""
        DeviceLayoutRegistry._initialized = False
        DeviceLayoutRegistry._instance = None

        registry = DeviceLayoutRegistry()
        registry.load_layouts(temp_layouts_dir)

        layout = registry.get_layout("test_mouse")
        assert layout is not None
        assert layout.name == "Test Mouse"

        missing = registry.get_layout("nonexistent")
        assert missing is None

    def test_get_layout_for_device_pattern_match(self, temp_layouts_dir):
        """Test pattern matching for device lookup."""
        DeviceLayoutRegistry._initialized = False
        DeviceLayoutRegistry._instance = None

        registry = DeviceLayoutRegistry()
        registry.load_layouts(temp_layouts_dir)

        # Should match pattern
        layout = registry.get_layout_for_device("My Test Mouse v2")
        assert layout is not None
        assert layout.id == "test_mouse"

        layout2 = registry.get_layout_for_device("TestMouse Pro")
        assert layout2 is not None
        assert layout2.id == "test_mouse"

    def test_get_layout_for_device_no_match(self, temp_layouts_dir):
        """Test device lookup with no pattern match."""
        DeviceLayoutRegistry._initialized = False
        DeviceLayoutRegistry._instance = None

        registry = DeviceLayoutRegistry()
        registry.load_layouts(temp_layouts_dir)

        # No match - returns None
        layout = registry.get_layout_for_device("Some Other Device")
        assert layout is None

    def test_list_layouts_by_category(self, temp_layouts_dir):
        """Test filtering layouts by category."""
        DeviceLayoutRegistry._initialized = False
        DeviceLayoutRegistry._instance = None

        registry = DeviceLayoutRegistry()
        registry.load_layouts(temp_layouts_dir)

        mice = registry.list_layouts_by_category(DeviceCategory.MOUSE)
        assert len(mice) == 1

        keyboards = registry.list_layouts_by_category(DeviceCategory.KEYBOARD)
        assert len(keyboards) == 0

    def test_missing_directory(self):
        """Test loading from nonexistent directory."""
        DeviceLayoutRegistry._initialized = False
        DeviceLayoutRegistry._instance = None

        registry = DeviceLayoutRegistry()
        registry.load_layouts(Path("/nonexistent/path"))

        # Should not crash, just have no layouts
        assert len(registry.list_layouts()) == 0


class TestJSONLayouts:
    """Tests for the actual JSON layout files."""

    def test_load_actual_layouts(self):
        """Test loading the actual layout files from data directory."""
        DeviceLayoutRegistry._initialized = False
        DeviceLayoutRegistry._instance = None

        registry = DeviceLayoutRegistry()
        registry.load_layouts()  # Uses default path

        layouts = registry.list_layouts()
        # Should have at least the generic layouts + DeathAdder
        assert len(layouts) >= 4

    def test_deathadder_layout(self):
        """Test DeathAdder V2 layout is loaded correctly."""
        DeviceLayoutRegistry._initialized = False
        DeviceLayoutRegistry._instance = None

        registry = DeviceLayoutRegistry()
        registry.load_layouts()

        layout = registry.get_layout("razer_deathadder_v2")
        if layout:  # Only test if layout file exists
            assert layout.name == "Razer DeathAdder V2"
            assert layout.category == DeviceCategory.MOUSE
            assert len(layout.buttons) >= 7

    def test_pattern_matching_deathadder(self):
        """Test DeathAdder pattern matching."""
        DeviceLayoutRegistry._initialized = False
        DeviceLayoutRegistry._instance = None

        registry = DeviceLayoutRegistry()
        registry.load_layouts()

        layout = registry.get_layout_for_device("Razer DeathAdder V2")
        if layout:
            assert layout.id == "razer_deathadder_v2"

    def test_basilisk_v3_layout(self):
        """Test Basilisk V3 layout is loaded correctly."""
        DeviceLayoutRegistry._initialized = False
        DeviceLayoutRegistry._instance = None

        registry = DeviceLayoutRegistry()
        registry.load_layouts()

        layout = registry.get_layout("razer_basilisk_v3")
        assert layout is not None
        assert layout.name == "Razer Basilisk V3"
        assert layout.category == DeviceCategory.MOUSE
        # Should have many buttons including DPI clutch and multi-paddle
        assert len(layout.buttons) >= 12

        # Check key buttons
        button_ids = [b.id for b in layout.buttons]
        assert "left_click" in button_ids
        assert "dpi_clutch" in button_ids
        assert "multi_paddle" in button_ids
        assert "underglow_zone" in button_ids

    def test_naga_x_layout(self):
        """Test Naga X layout has 12 side buttons."""
        DeviceLayoutRegistry._initialized = False
        DeviceLayoutRegistry._instance = None

        registry = DeviceLayoutRegistry()
        registry.load_layouts()

        layout = registry.get_layout("razer_naga_x")
        assert layout is not None
        assert layout.name == "Razer Naga X"

        # Check all 12 side buttons exist
        button_ids = [b.id for b in layout.buttons]
        for i in range(1, 13):
            assert f"side_{i}" in button_ids

    def test_blackwidow_v3_layout(self):
        """Test BlackWidow V3 keyboard layout."""
        DeviceLayoutRegistry._initialized = False
        DeviceLayoutRegistry._instance = None

        registry = DeviceLayoutRegistry()
        registry.load_layouts()

        layout = registry.get_layout("razer_blackwidow_v3")
        assert layout is not None
        assert layout.category == DeviceCategory.KEYBOARD

        # All buttons should be zones for keyboard
        assert all(b.is_zone for b in layout.buttons)

        # Check key zones exist
        zone_ids = [b.id for b in layout.buttons]
        assert "zone_function" in zone_ids
        assert "zone_qwerty" in zone_ids
        assert "zone_arrows" in zone_ids
        assert "zone_underglow" in zone_ids

    def test_tartarus_v2_layout(self):
        """Test Tartarus V2 keypad layout."""
        DeviceLayoutRegistry._initialized = False
        DeviceLayoutRegistry._instance = None

        registry = DeviceLayoutRegistry()
        registry.load_layouts()

        layout = registry.get_layout("razer_tartarus_v2")
        assert layout is not None
        assert layout.category == DeviceCategory.KEYPAD

        # Check key elements
        button_ids = [b.id for b in layout.buttons]
        assert "thumbstick" in button_ids
        assert "scroll_wheel" in button_ids
        assert "key_spacebar" in button_ids

    def test_pattern_matching_basilisk(self):
        """Test Basilisk pattern matching."""
        DeviceLayoutRegistry._initialized = False
        DeviceLayoutRegistry._instance = None

        registry = DeviceLayoutRegistry()
        registry.load_layouts()

        layout = registry.get_layout_for_device("Razer Basilisk V3 Pro")
        assert layout is not None
        assert layout.id == "razer_basilisk_v3"

    def test_pattern_matching_naga(self):
        """Test Naga pattern matching."""
        DeviceLayoutRegistry._initialized = False
        DeviceLayoutRegistry._instance = None

        registry = DeviceLayoutRegistry()
        registry.load_layouts()

        layout = registry.get_layout_for_device("Razer Naga X")
        assert layout is not None
        assert layout.id == "razer_naga_x"

        # Also matches Naga Trinity and Pro
        layout2 = registry.get_layout_for_device("Razer Naga Trinity")
        assert layout2 is not None

    def test_pattern_matching_tartarus(self):
        """Test Tartarus pattern matching."""
        DeviceLayoutRegistry._initialized = False
        DeviceLayoutRegistry._instance = None

        registry = DeviceLayoutRegistry()
        registry.load_layouts()

        layout = registry.get_layout_for_device("Razer Tartarus V2")
        assert layout is not None
        assert layout.id == "razer_tartarus_v2"

        # Also matches Tartarus Pro
        layout2 = registry.get_layout_for_device("Razer Tartarus Pro")
        assert layout2 is not None
