"""Keycode mapping tables and utilities."""

from evdev import ecodes

# evdev code name -> schema key name (human friendly)
# We use evdev names directly for most keys, but provide aliases
EVDEV_TO_SCHEMA: dict[str, str] = {
    # Mouse buttons
    "BTN_LEFT": "MOUSE_LEFT",
    "BTN_RIGHT": "MOUSE_RIGHT",
    "BTN_MIDDLE": "MOUSE_MIDDLE",
    "BTN_SIDE": "MOUSE_SIDE",
    "BTN_EXTRA": "MOUSE_EXTRA",
    "BTN_FORWARD": "MOUSE_FORWARD",
    "BTN_BACK": "MOUSE_BACK",
    "BTN_TASK": "MOUSE_TASK",

    # Modifiers
    "KEY_LEFTCTRL": "CTRL",
    "KEY_RIGHTCTRL": "CTRL_R",
    "KEY_LEFTSHIFT": "SHIFT",
    "KEY_RIGHTSHIFT": "SHIFT_R",
    "KEY_LEFTALT": "ALT",
    "KEY_RIGHTALT": "ALT_R",
    "KEY_LEFTMETA": "META",
    "KEY_RIGHTMETA": "META_R",

    # Special keys
    "KEY_ESC": "ESC",
    "KEY_TAB": "TAB",
    "KEY_CAPSLOCK": "CAPS",
    "KEY_ENTER": "ENTER",
    "KEY_SPACE": "SPACE",
    "KEY_BACKSPACE": "BACKSPACE",
    "KEY_DELETE": "DELETE",
    "KEY_INSERT": "INSERT",
    "KEY_HOME": "HOME",
    "KEY_END": "END",
    "KEY_PAGEUP": "PAGEUP",
    "KEY_PAGEDOWN": "PAGEDOWN",

    # Arrows
    "KEY_UP": "UP",
    "KEY_DOWN": "DOWN",
    "KEY_LEFT": "LEFT",
    "KEY_RIGHT": "RIGHT",

    # Function keys
    "KEY_F1": "F1",
    "KEY_F2": "F2",
    "KEY_F3": "F3",
    "KEY_F4": "F4",
    "KEY_F5": "F5",
    "KEY_F6": "F6",
    "KEY_F7": "F7",
    "KEY_F8": "F8",
    "KEY_F9": "F9",
    "KEY_F10": "F10",
    "KEY_F11": "F11",
    "KEY_F12": "F12",
    "KEY_F13": "F13",
    "KEY_F14": "F14",
    "KEY_F15": "F15",
    "KEY_F16": "F16",
    "KEY_F17": "F17",
    "KEY_F18": "F18",
    "KEY_F19": "F19",
    "KEY_F20": "F20",
    "KEY_F21": "F21",
    "KEY_F22": "F22",
    "KEY_F23": "F23",
    "KEY_F24": "F24",

    # Media keys
    "KEY_MUTE": "MUTE",
    "KEY_VOLUMEDOWN": "VOL_DOWN",
    "KEY_VOLUMEUP": "VOL_UP",
    "KEY_PLAYPAUSE": "PLAY_PAUSE",
    "KEY_STOPCD": "STOP",
    "KEY_PREVIOUSSONG": "PREV_TRACK",
    "KEY_NEXTSONG": "NEXT_TRACK",

    # Print screen / scroll lock / pause
    "KEY_SYSRQ": "PRINT_SCREEN",
    "KEY_SCROLLLOCK": "SCROLL_LOCK",
    "KEY_PAUSE": "PAUSE",
}

# Add letter keys (A-Z)
for i, letter in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
    EVDEV_TO_SCHEMA[f"KEY_{letter}"] = letter

# Add number keys (0-9)
for i in range(10):
    EVDEV_TO_SCHEMA[f"KEY_{i}"] = str(i)

# Add numpad keys
for i in range(10):
    EVDEV_TO_SCHEMA[f"KEY_KP{i}"] = f"NUM_{i}"
EVDEV_TO_SCHEMA["KEY_KPENTER"] = "NUM_ENTER"
EVDEV_TO_SCHEMA["KEY_KPPLUS"] = "NUM_PLUS"
EVDEV_TO_SCHEMA["KEY_KPMINUS"] = "NUM_MINUS"
EVDEV_TO_SCHEMA["KEY_KPASTERISK"] = "NUM_MULT"
EVDEV_TO_SCHEMA["KEY_KPSLASH"] = "NUM_DIV"
EVDEV_TO_SCHEMA["KEY_KPDOT"] = "NUM_DOT"
EVDEV_TO_SCHEMA["KEY_NUMLOCK"] = "NUM_LOCK"

# Punctuation
EVDEV_TO_SCHEMA["KEY_MINUS"] = "MINUS"
EVDEV_TO_SCHEMA["KEY_EQUAL"] = "EQUAL"
EVDEV_TO_SCHEMA["KEY_LEFTBRACE"] = "LBRACKET"
EVDEV_TO_SCHEMA["KEY_RIGHTBRACE"] = "RBRACKET"
EVDEV_TO_SCHEMA["KEY_SEMICOLON"] = "SEMICOLON"
EVDEV_TO_SCHEMA["KEY_APOSTROPHE"] = "APOSTROPHE"
EVDEV_TO_SCHEMA["KEY_GRAVE"] = "GRAVE"
EVDEV_TO_SCHEMA["KEY_BACKSLASH"] = "BACKSLASH"
EVDEV_TO_SCHEMA["KEY_COMMA"] = "COMMA"
EVDEV_TO_SCHEMA["KEY_DOT"] = "DOT"
EVDEV_TO_SCHEMA["KEY_SLASH"] = "SLASH"

# Build reverse mapping: schema name -> evdev code name
SCHEMA_TO_EVDEV: dict[str, str] = {v: k for k, v in EVDEV_TO_SCHEMA.items()}

# Also allow evdev names directly in schema
for evdev_name in EVDEV_TO_SCHEMA.keys():
    if evdev_name not in SCHEMA_TO_EVDEV:
        SCHEMA_TO_EVDEV[evdev_name] = evdev_name

# Schema name -> uinput code (integer)
SCHEMA_TO_UINPUT: dict[str, int] = {}

def _build_uinput_map():
    """Build the schema -> uinput code mapping."""
    for evdev_name, schema_name in EVDEV_TO_SCHEMA.items():
        # Get the actual evdev code
        code = getattr(ecodes, evdev_name, None)
        if code is not None:
            SCHEMA_TO_UINPUT[schema_name] = code
            # Also allow evdev name directly
            SCHEMA_TO_UINPUT[evdev_name] = code

_build_uinput_map()


def evdev_code_to_schema(evdev_name: str) -> str:
    """Convert an evdev code name to schema key name."""
    return EVDEV_TO_SCHEMA.get(evdev_name, evdev_name)


def schema_to_evdev_code(schema_name: str) -> int | None:
    """Convert a schema key name to evdev/uinput code."""
    # First check our mapping
    if schema_name in SCHEMA_TO_UINPUT:
        return SCHEMA_TO_UINPUT[schema_name]

    # Try direct evdev lookup
    evdev_name = SCHEMA_TO_EVDEV.get(schema_name, schema_name)
    code = getattr(ecodes, evdev_name, None)
    if code is not None:
        return code

    # Try with KEY_ prefix
    code = getattr(ecodes, f"KEY_{schema_name}", None)
    if code is not None:
        return code

    # Try with BTN_ prefix
    code = getattr(ecodes, f"BTN_{schema_name}", None)
    return code


def get_all_schema_keys() -> list[str]:
    """Get all available schema key names."""
    keys = set(EVDEV_TO_SCHEMA.values())
    # Also include evdev names that can be used directly
    keys.update(EVDEV_TO_SCHEMA.keys())
    return sorted(keys)


def evdev_event_to_schema(event_type: int, event_code: int) -> str | None:
    """Convert an evdev event type/code pair to schema key name."""
    # Look up the code name
    if event_type == ecodes.EV_KEY:
        code_name = ecodes.KEY.get(event_code) or ecodes.BTN.get(event_code)
        if code_name:
            if isinstance(code_name, list):
                code_name = code_name[0]
            return evdev_code_to_schema(code_name)
    return None
