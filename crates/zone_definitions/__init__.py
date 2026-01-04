"""Zone definitions for keyboard and device layouts.

Provides standard zone definitions for grouping keys that can be
colored together in the zone-based RGB editor.
"""

from dataclasses import dataclass, field
from enum import Enum


class ZoneType(Enum):
    """Types of keyboard zones."""

    FUNCTION_ROW = "function_row"
    NUMBER_ROW = "number_row"
    QWERTY_ROW = "qwerty_row"
    ASDF_ROW = "asdf_row"
    ZXCV_ROW = "zxcv_row"
    MODIFIERS_LEFT = "modifiers_left"
    MODIFIERS_RIGHT = "modifiers_right"
    ARROWS = "arrows"
    NUMPAD = "numpad"
    MEDIA = "media"
    WASD = "wasd"
    ESDF = "esdf"
    NAV_CLUSTER = "nav_cluster"
    SPACEBAR = "spacebar"
    CUSTOM = "custom"


@dataclass
class KeyPosition:
    """Position of a key in the matrix."""

    row: int
    col: int
    label: str = ""

    def __hash__(self):
        return hash((self.row, self.col))


@dataclass
class Zone:
    """A zone of keys that can be colored together."""

    id: str
    name: str
    zone_type: ZoneType
    keys: list[KeyPosition] = field(default_factory=list)
    description: str = ""

    def __post_init__(self):
        # Ensure keys is a list
        if not isinstance(self.keys, list):
            self.keys = list(self.keys)


@dataclass
class KeyboardLayout:
    """Complete keyboard layout with zones."""

    device_type: str  # "keyboard", "keypad", "mouse"
    rows: int
    cols: int
    zones: list[Zone] = field(default_factory=list)

    def get_zone(self, zone_id: str) -> Zone | None:
        """Get a zone by ID."""
        for zone in self.zones:
            if zone.id == zone_id:
                return zone
        return None

    def get_all_zone_keys(self) -> set[tuple[int, int]]:
        """Get all key positions that are assigned to zones."""
        keys = set()
        for zone in self.zones:
            for key in zone.keys:
                keys.add((key.row, key.col))
        return keys


# Standard zone definitions for full-size keyboards (6 rows, 22 cols typical)
def _create_standard_zones() -> list[Zone]:
    """Create standard keyboard zones."""
    zones = []

    # Function row (F1-F12) - typically row 0
    zones.append(
        Zone(
            id="function_row",
            name="Function Keys",
            zone_type=ZoneType.FUNCTION_ROW,
            keys=[KeyPosition(0, c, f"F{c}") for c in range(1, 13)],
            description="F1-F12 function keys",
        )
    )

    # Escape key
    zones.append(
        Zone(
            id="escape",
            name="Escape",
            zone_type=ZoneType.CUSTOM,
            keys=[KeyPosition(0, 0, "Esc")],
            description="Escape key",
        )
    )

    # Number row (1-0) - typically row 1
    zones.append(
        Zone(
            id="number_row",
            name="Number Row",
            zone_type=ZoneType.NUMBER_ROW,
            keys=[KeyPosition(1, c, str(c) if c < 10 else "0") for c in range(1, 11)],
            description="Number keys 1-0",
        )
    )

    # WASD gaming cluster
    zones.append(
        Zone(
            id="wasd",
            name="WASD",
            zone_type=ZoneType.WASD,
            keys=[
                KeyPosition(2, 1, "W"),
                KeyPosition(3, 0, "A"),
                KeyPosition(3, 1, "S"),
                KeyPosition(3, 2, "D"),
            ],
            description="WASD gaming keys",
        )
    )

    # ESDF alternative gaming cluster
    zones.append(
        Zone(
            id="esdf",
            name="ESDF",
            zone_type=ZoneType.ESDF,
            keys=[
                KeyPosition(2, 2, "E"),
                KeyPosition(3, 1, "S"),
                KeyPosition(3, 2, "D"),
                KeyPosition(3, 3, "F"),
            ],
            description="ESDF alternative gaming keys",
        )
    )

    # Arrow keys - typically bottom right
    zones.append(
        Zone(
            id="arrows",
            name="Arrow Keys",
            zone_type=ZoneType.ARROWS,
            keys=[
                KeyPosition(4, 14, "Up"),
                KeyPosition(5, 13, "Left"),
                KeyPosition(5, 14, "Down"),
                KeyPosition(5, 15, "Right"),
            ],
            description="Arrow navigation keys",
        )
    )

    # Left modifiers (Ctrl, Shift, Alt, Win)
    zones.append(
        Zone(
            id="modifiers_left",
            name="Left Modifiers",
            zone_type=ZoneType.MODIFIERS_LEFT,
            keys=[
                KeyPosition(5, 0, "LCtrl"),
                KeyPosition(5, 1, "Win"),
                KeyPosition(5, 2, "LAlt"),
                KeyPosition(4, 0, "LShift"),
                KeyPosition(3, 0, "CapsLock"),
                KeyPosition(2, 0, "Tab"),
            ],
            description="Left side modifier keys",
        )
    )

    # Right modifiers
    zones.append(
        Zone(
            id="modifiers_right",
            name="Right Modifiers",
            zone_type=ZoneType.MODIFIERS_RIGHT,
            keys=[
                KeyPosition(5, 10, "RAlt"),
                KeyPosition(5, 11, "Fn"),
                KeyPosition(5, 12, "Menu"),
                KeyPosition(5, 13, "RCtrl"),
                KeyPosition(4, 12, "RShift"),
            ],
            description="Right side modifier keys",
        )
    )

    # Spacebar
    zones.append(
        Zone(
            id="spacebar",
            name="Spacebar",
            zone_type=ZoneType.SPACEBAR,
            keys=[KeyPosition(5, c, "Space") for c in range(3, 10)],
            description="Spacebar",
        )
    )

    # Navigation cluster (Ins, Del, Home, End, PgUp, PgDn)
    zones.append(
        Zone(
            id="nav_cluster",
            name="Navigation",
            zone_type=ZoneType.NAV_CLUSTER,
            keys=[
                KeyPosition(1, 14, "Ins"),
                KeyPosition(1, 15, "Home"),
                KeyPosition(1, 16, "PgUp"),
                KeyPosition(2, 14, "Del"),
                KeyPosition(2, 15, "End"),
                KeyPosition(2, 16, "PgDn"),
            ],
            description="Navigation cluster",
        )
    )

    # Numpad
    zones.append(
        Zone(
            id="numpad",
            name="Numpad",
            zone_type=ZoneType.NUMPAD,
            keys=[
                KeyPosition(r, c, "")
                for r in range(1, 6)
                for c in range(17, 21)
            ],
            description="Numeric keypad",
        )
    )

    return zones


# Pre-built standard zones
STANDARD_KEYBOARD_ZONES = _create_standard_zones()


def get_layout_for_device(
    device_name: str, rows: int, cols: int
) -> KeyboardLayout:
    """Get the appropriate layout for a device.

    Args:
        device_name: Device name from OpenRazer
        rows: Matrix row count
        cols: Matrix column count

    Returns:
        KeyboardLayout with appropriate zones
    """
    # Determine device type from dimensions
    if cols < 6:
        device_type = "mouse"
    elif cols < 12:
        device_type = "keypad"
    else:
        device_type = "keyboard"

    layout = KeyboardLayout(
        device_type=device_type,
        rows=rows,
        cols=cols,
        zones=[],
    )

    # For non-keyboards, create simple row-based zones
    if device_type != "keyboard":
        for r in range(rows):
            layout.zones.append(
                Zone(
                    id=f"row_{r}",
                    name=f"Row {r + 1}",
                    zone_type=ZoneType.CUSTOM,
                    keys=[KeyPosition(r, c, "") for c in range(cols)],
                    description=f"Row {r + 1} LEDs",
                )
            )
        return layout

    # For keyboards, add zones that fit within the matrix dimensions
    for zone in STANDARD_KEYBOARD_ZONES:
        # Check if all keys in this zone fit in the matrix
        fits = all(
            k.row < rows and k.col < cols
            for k in zone.keys
        )
        if fits and zone.keys:  # Only add non-empty zones that fit
            layout.zones.append(zone)

    # Collect assigned keys
    assigned_keys = layout.get_all_zone_keys()

    # Create an "other" zone for remaining keys
    other_keys = []
    for r in range(rows):
        for c in range(cols):
            if (r, c) not in assigned_keys:
                other_keys.append(KeyPosition(r, c, ""))

    if other_keys:
        layout.zones.append(
            Zone(
                id="other",
                name="Other Keys",
                zone_type=ZoneType.CUSTOM,
                keys=other_keys,
                description="All other keys not in a specific zone",
            )
        )

    return layout


def get_zones_for_preset(preset_name: str) -> dict[str, tuple[int, int, int]]:
    """Get zone colors for a named preset.

    Args:
        preset_name: Name of the preset

    Returns:
        Dict mapping zone_id to RGB color tuple
    """
    presets = {
        "gaming": {
            "wasd": (0, 255, 0),  # Green WASD
            "function_row": (255, 0, 0),  # Red function keys
            "escape": (255, 0, 0),  # Red escape
        },
        "productivity": {
            "function_row": (0, 128, 255),  # Blue function keys
            "number_row": (255, 255, 0),  # Yellow numbers
            "nav_cluster": (0, 255, 128),  # Cyan navigation
        },
        "stealth": {
            # All zones off (black)
        },
        "full_white": {
            "function_row": (255, 255, 255),
            "number_row": (255, 255, 255),
            "wasd": (255, 255, 255),
            "arrows": (255, 255, 255),
            "modifiers_left": (255, 255, 255),
            "modifiers_right": (255, 255, 255),
            "spacebar": (255, 255, 255),
            "other": (255, 255, 255),
        },
    }

    return presets.get(preset_name, {})


__all__ = [
    "ZoneType",
    "KeyPosition",
    "Zone",
    "KeyboardLayout",
    "STANDARD_KEYBOARD_ZONES",
    "get_layout_for_device",
    "get_zones_for_preset",
]
