"""Tests for zone definitions and zone editor widget."""

import pytest

from crates.profile_schema import (
    KeyColor,
    LightingConfig,
    MatrixLightingConfig,
    ZoneColor,
)
from crates.zone_definitions import (
    STANDARD_KEYBOARD_ZONES,
    KeyboardLayout,
    KeyPosition,
    Zone,
    ZoneType,
    get_layout_for_device,
    get_zones_for_preset,
)

# --- Zone Definitions Tests ---


class TestKeyPosition:
    """Tests for KeyPosition dataclass."""

    def test_create_key_position(self):
        """Test creating a key position."""
        pos = KeyPosition(row=2, col=5, label="E")
        assert pos.row == 2
        assert pos.col == 5
        assert pos.label == "E"

    def test_key_position_hashable(self):
        """Test that key positions are hashable for use in sets."""
        pos1 = KeyPosition(row=1, col=2, label="A")
        pos2 = KeyPosition(row=1, col=2, label="A")
        pos3 = KeyPosition(row=1, col=3, label="B")

        # Same row/col should hash the same
        assert hash(pos1) == hash(pos2)
        # Different positions should hash differently (usually)
        assert hash(pos1) != hash(pos3)

        # Can be used in a set
        positions = {pos1, pos2, pos3}
        assert len(positions) == 2  # pos1 and pos2 are same position


class TestZone:
    """Tests for Zone dataclass."""

    def test_create_zone(self):
        """Test creating a zone."""
        keys = [KeyPosition(0, 0, "A"), KeyPosition(0, 1, "B")]
        zone = Zone(
            id="test_zone",
            name="Test Zone",
            zone_type=ZoneType.CUSTOM,
            keys=keys,
            description="A test zone",
        )

        assert zone.id == "test_zone"
        assert zone.name == "Test Zone"
        assert zone.zone_type == ZoneType.CUSTOM
        assert len(zone.keys) == 2
        assert zone.description == "A test zone"

    def test_zone_default_description(self):
        """Test zone with default empty description."""
        zone = Zone(
            id="simple",
            name="Simple",
            zone_type=ZoneType.WASD,
            keys=[],
        )
        assert zone.description == ""

    def test_zone_converts_non_list_keys_to_list(self):
        """Test that Zone.__post_init__ converts non-list keys to list."""
        # Pass a tuple instead of a list
        keys_tuple = (KeyPosition(0, 0, "A"), KeyPosition(0, 1, "B"))
        zone = Zone(
            id="tuple_zone",
            name="Tuple Zone",
            zone_type=ZoneType.CUSTOM,
            keys=keys_tuple,  # type: ignore
        )
        # Should be converted to list
        assert isinstance(zone.keys, list)
        assert len(zone.keys) == 2

    def test_zone_converts_generator_keys_to_list(self):
        """Test that Zone.__post_init__ converts generator keys to list."""
        # Pass a generator
        def key_gen():
            yield KeyPosition(1, 0, "Q")
            yield KeyPosition(1, 1, "W")

        zone = Zone(
            id="gen_zone",
            name="Generator Zone",
            zone_type=ZoneType.CUSTOM,
            keys=key_gen(),  # type: ignore
        )
        # Should be converted to list
        assert isinstance(zone.keys, list)
        assert len(zone.keys) == 2


class TestKeyboardLayout:
    """Tests for KeyboardLayout dataclass."""

    def test_create_layout(self):
        """Test creating a keyboard layout."""
        layout = KeyboardLayout(
            device_type="keyboard",
            rows=6,
            cols=22,
            zones=[],
        )

        assert layout.device_type == "keyboard"
        assert layout.rows == 6
        assert layout.cols == 22
        assert layout.zones == []

    def test_get_zone_found(self):
        """Test getting a zone by ID when it exists."""
        zone = Zone(id="wasd", name="WASD", zone_type=ZoneType.WASD, keys=[])
        layout = KeyboardLayout(device_type="keyboard", rows=6, cols=22, zones=[zone])

        result = layout.get_zone("wasd")
        assert result is not None
        assert result.id == "wasd"

    def test_get_zone_not_found(self):
        """Test getting a zone by ID when it doesn't exist."""
        layout = KeyboardLayout(device_type="keyboard", rows=6, cols=22, zones=[])

        result = layout.get_zone("nonexistent")
        assert result is None

    def test_get_all_zone_keys(self):
        """Test collecting all keys from zones."""
        zone1 = Zone(
            id="z1",
            name="Zone 1",
            zone_type=ZoneType.CUSTOM,
            keys=[KeyPosition(0, 0, ""), KeyPosition(0, 1, "")],
        )
        zone2 = Zone(
            id="z2",
            name="Zone 2",
            zone_type=ZoneType.CUSTOM,
            keys=[KeyPosition(1, 0, ""), KeyPosition(1, 1, "")],
        )
        layout = KeyboardLayout(
            device_type="keyboard", rows=6, cols=22, zones=[zone1, zone2]
        )

        keys = layout.get_all_zone_keys()
        assert keys == {(0, 0), (0, 1), (1, 0), (1, 1)}


class TestStandardZones:
    """Tests for standard zone definitions."""

    def test_standard_zones_exist(self):
        """Test that standard zones are defined."""
        assert len(STANDARD_KEYBOARD_ZONES) > 0

    def test_wasd_zone_exists(self):
        """Test that WASD zone is defined correctly."""
        wasd = None
        for zone in STANDARD_KEYBOARD_ZONES:
            if zone.id == "wasd":
                wasd = zone
                break

        assert wasd is not None
        assert wasd.zone_type == ZoneType.WASD
        assert len(wasd.keys) == 4  # W, A, S, D

    def test_function_row_zone_exists(self):
        """Test that function row zone is defined."""
        func_row = None
        for zone in STANDARD_KEYBOARD_ZONES:
            if zone.id == "function_row":
                func_row = zone
                break

        assert func_row is not None
        assert func_row.zone_type == ZoneType.FUNCTION_ROW
        assert len(func_row.keys) == 12  # F1-F12


class TestGetLayoutForDevice:
    """Tests for get_layout_for_device function."""

    def test_keyboard_layout(self):
        """Test layout generation for keyboard."""
        layout = get_layout_for_device("Razer Huntsman", rows=6, cols=22)

        assert layout.device_type == "keyboard"
        assert layout.rows == 6
        assert layout.cols == 22
        assert len(layout.zones) > 0

    def test_mouse_layout(self):
        """Test layout generation for mouse (small matrix)."""
        layout = get_layout_for_device("Razer DeathAdder", rows=1, cols=5)

        assert layout.device_type == "mouse"
        assert len(layout.zones) > 0

    def test_keypad_layout(self):
        """Test layout generation for keypad (medium matrix)."""
        layout = get_layout_for_device("Razer Tartarus", rows=4, cols=8)

        assert layout.device_type == "keypad"
        assert len(layout.zones) == 4  # One zone per row

    def test_other_zone_created(self):
        """Test that 'other' zone is created for unassigned keys."""
        layout = get_layout_for_device("Razer Keyboard", rows=6, cols=22)

        other_zone = layout.get_zone("other")
        # Should have an 'other' zone for remaining keys
        assert other_zone is not None or layout.get_all_zone_keys() == set()


class TestGetZonesForPreset:
    """Tests for get_zones_for_preset function."""

    def test_gaming_preset(self):
        """Test gaming preset returns expected colors."""
        colors = get_zones_for_preset("gaming")

        assert "wasd" in colors
        assert colors["wasd"] == (0, 255, 0)  # Green
        assert "function_row" in colors
        assert colors["function_row"] == (255, 0, 0)  # Red

    def test_productivity_preset(self):
        """Test productivity preset returns expected colors."""
        colors = get_zones_for_preset("productivity")

        assert "function_row" in colors
        assert "number_row" in colors
        assert "nav_cluster" in colors

    def test_stealth_preset(self):
        """Test stealth preset returns empty (all off)."""
        colors = get_zones_for_preset("stealth")
        assert colors == {}

    def test_full_white_preset(self):
        """Test full white preset sets all zones to white."""
        colors = get_zones_for_preset("full_white")

        for zone_id, color in colors.items():
            assert color == (255, 255, 255)

    def test_unknown_preset(self):
        """Test unknown preset returns empty dict."""
        colors = get_zones_for_preset("nonexistent_preset")
        assert colors == {}


# --- Profile Schema Tests ---


class TestZoneColor:
    """Tests for ZoneColor model."""

    def test_create_zone_color(self):
        """Test creating a zone color."""
        zc = ZoneColor(zone_id="wasd", color=(255, 0, 0))
        assert zc.zone_id == "wasd"
        assert zc.color == (255, 0, 0)

    def test_zone_color_to_dict(self):
        """Test zone color serialization."""
        zc = ZoneColor(zone_id="arrows", color=(0, 255, 0))
        data = zc.model_dump()

        assert data["zone_id"] == "arrows"
        assert data["color"] == (0, 255, 0)


class TestKeyColor:
    """Tests for KeyColor model."""

    def test_create_key_color(self):
        """Test creating a key color."""
        kc = KeyColor(row=2, col=5, color=(0, 0, 255))
        assert kc.row == 2
        assert kc.col == 5
        assert kc.color == (0, 0, 255)

    def test_key_color_validation(self):
        """Test that row/col must be non-negative."""
        with pytest.raises(ValueError):
            KeyColor(row=-1, col=0, color=(0, 0, 0))

        with pytest.raises(ValueError):
            KeyColor(row=0, col=-1, color=(0, 0, 0))


class TestMatrixLightingConfig:
    """Tests for MatrixLightingConfig model."""

    def test_create_empty_config(self):
        """Test creating an empty matrix config."""
        config = MatrixLightingConfig()
        assert config.enabled is False
        assert config.zones == []
        assert config.keys == []
        assert config.default_color == (0, 0, 0)

    def test_create_with_zones(self):
        """Test creating a config with zone colors."""
        zones = [
            ZoneColor(zone_id="wasd", color=(0, 255, 0)),
            ZoneColor(zone_id="arrows", color=(255, 0, 0)),
        ]
        config = MatrixLightingConfig(enabled=True, zones=zones)

        assert config.enabled is True
        assert len(config.zones) == 2

    def test_serialization_roundtrip(self):
        """Test that config can be serialized and deserialized."""
        zones = [ZoneColor(zone_id="wasd", color=(0, 255, 0))]
        config = MatrixLightingConfig(
            enabled=True,
            zones=zones,
            default_color=(50, 50, 50),
        )

        data = config.model_dump()
        restored = MatrixLightingConfig(**data)

        assert restored.enabled == config.enabled
        assert len(restored.zones) == len(config.zones)
        assert restored.zones[0].zone_id == "wasd"
        assert restored.default_color == (50, 50, 50)


class TestLightingConfigWithMatrix:
    """Tests for LightingConfig with matrix field."""

    def test_lighting_config_default_no_matrix(self):
        """Test that matrix is None by default."""
        config = LightingConfig()
        assert config.matrix is None

    def test_lighting_config_with_matrix(self):
        """Test LightingConfig with matrix config."""
        matrix = MatrixLightingConfig(enabled=True, zones=[])
        config = LightingConfig(matrix=matrix)

        assert config.matrix is not None
        assert config.matrix.enabled is True

    def test_full_config_serialization(self):
        """Test full config serialization."""
        matrix = MatrixLightingConfig(
            enabled=True,
            zones=[ZoneColor(zone_id="wasd", color=(255, 255, 0))],
        )
        config = LightingConfig(
            effect="static",
            brightness=80,
            color=(255, 0, 255),
            matrix=matrix,
        )

        data = config.model_dump()
        restored = LightingConfig(**data)

        assert restored.matrix is not None
        assert restored.matrix.enabled is True
        assert len(restored.matrix.zones) == 1


# --- Zone to Matrix Conversion Tests ---


class TestZoneToMatrixConversion:
    """Tests for converting zone colors to matrix format."""

    def test_build_matrix_from_zones(self):
        """Test building a matrix from zone colors."""
        # Get a layout
        layout = get_layout_for_device("Keyboard", rows=6, cols=22)

        # Define zone colors
        zone_colors = {
            "wasd": (0, 255, 0),
            "function_row": (255, 0, 0),
        }

        # Build matrix
        rows = layout.rows
        cols = layout.cols
        matrix = [[(0, 0, 0) for _ in range(cols)] for _ in range(rows)]

        for zone_id, color in zone_colors.items():
            zone = layout.get_zone(zone_id)
            if zone:
                for key in zone.keys:
                    if 0 <= key.row < rows and 0 <= key.col < cols:
                        matrix[key.row][key.col] = color

        # Verify WASD keys are green
        wasd_zone = layout.get_zone("wasd")
        if wasd_zone:
            for key in wasd_zone.keys:
                assert matrix[key.row][key.col] == (0, 255, 0)

    def test_overlapping_zones(self):
        """Test that later zones override earlier ones."""
        # ESDF overlaps with WASD (S and D are in both)
        layout = get_layout_for_device("Keyboard", rows=6, cols=22)

        zone_colors = {
            "wasd": (255, 0, 0),  # Red first
            "esdf": (0, 0, 255),  # Blue overrides
        }

        # Build matrix with explicit ordering
        rows = layout.rows
        cols = layout.cols
        matrix = [[(0, 0, 0) for _ in range(cols)] for _ in range(rows)]

        for zone_id in ["wasd", "esdf"]:
            color = zone_colors.get(zone_id)
            if color:
                zone = layout.get_zone(zone_id)
                if zone:
                    for key in zone.keys:
                        if 0 <= key.row < rows and 0 <= key.col < cols:
                            matrix[key.row][key.col] = color

        # S key at (3, 1) is in both zones - should be blue (last applied)
        esdf_zone = layout.get_zone("esdf")
        if esdf_zone:
            for key in esdf_zone.keys:
                # All ESDF keys should be blue
                assert matrix[key.row][key.col] == (0, 0, 255)
