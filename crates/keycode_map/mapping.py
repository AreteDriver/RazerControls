"""Keycode mapping tables and utilities.

Provides comprehensive mapping between:
- evdev code names (e.g., KEY_A, BTN_LEFT)
- Schema key names (human-friendly, e.g., A, MOUSE_LEFT)
- uinput codes (integer values for emitting events)
"""

from evdev import ecodes

# =============================================================================
# EVDEV TO SCHEMA MAPPING
# =============================================================================
# Maps evdev code names to human-friendly schema names.
# Schema names are what users see in profiles and the GUI.

EVDEV_TO_SCHEMA: dict[str, str] = {
    # -------------------------------------------------------------------------
    # Mouse Buttons
    # -------------------------------------------------------------------------
    "BTN_LEFT": "MOUSE_LEFT",
    "BTN_RIGHT": "MOUSE_RIGHT",
    "BTN_MIDDLE": "MOUSE_MIDDLE",
    "BTN_SIDE": "MOUSE_SIDE",
    "BTN_EXTRA": "MOUSE_EXTRA",
    "BTN_FORWARD": "MOUSE_FORWARD",
    "BTN_BACK": "MOUSE_BACK",
    "BTN_TASK": "MOUSE_TASK",
    # Gaming mouse buttons (some mice have these)
    "BTN_0": "MOUSE_BTN0",
    "BTN_1": "MOUSE_BTN1",
    "BTN_2": "MOUSE_BTN2",
    "BTN_3": "MOUSE_BTN3",
    "BTN_4": "MOUSE_BTN4",
    "BTN_5": "MOUSE_BTN5",
    "BTN_6": "MOUSE_BTN6",
    "BTN_7": "MOUSE_BTN7",
    "BTN_8": "MOUSE_BTN8",
    "BTN_9": "MOUSE_BTN9",
    # -------------------------------------------------------------------------
    # Modifier Keys
    # -------------------------------------------------------------------------
    "KEY_LEFTCTRL": "CTRL",
    "KEY_RIGHTCTRL": "CTRL_R",
    "KEY_LEFTSHIFT": "SHIFT",
    "KEY_RIGHTSHIFT": "SHIFT_R",
    "KEY_LEFTALT": "ALT",
    "KEY_RIGHTALT": "ALT_R",
    "KEY_LEFTMETA": "META",  # Windows/Super key
    "KEY_RIGHTMETA": "META_R",
    # -------------------------------------------------------------------------
    # Special Keys
    # -------------------------------------------------------------------------
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
    "KEY_MENU": "MENU",  # Context menu key
    "KEY_COMPOSE": "COMPOSE",
    "KEY_POWER": "POWER",
    "KEY_SLEEP": "SLEEP",
    "KEY_WAKEUP": "WAKEUP",
    # -------------------------------------------------------------------------
    # Arrow Keys
    # -------------------------------------------------------------------------
    "KEY_UP": "UP",
    "KEY_DOWN": "DOWN",
    "KEY_LEFT": "LEFT",
    "KEY_RIGHT": "RIGHT",
    # -------------------------------------------------------------------------
    # Function Keys (F1-F24)
    # -------------------------------------------------------------------------
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
    # -------------------------------------------------------------------------
    # Media Keys
    # -------------------------------------------------------------------------
    "KEY_MUTE": "MUTE",
    "KEY_VOLUMEDOWN": "VOL_DOWN",
    "KEY_VOLUMEUP": "VOL_UP",
    "KEY_PLAYPAUSE": "PLAY_PAUSE",
    "KEY_STOPCD": "STOP",
    "KEY_PREVIOUSSONG": "PREV_TRACK",
    "KEY_NEXTSONG": "NEXT_TRACK",
    "KEY_MEDIA": "MEDIA",
    "KEY_EJECTCD": "EJECT",
    "KEY_EJECTCLOSECD": "EJECT_CLOSE",
    "KEY_RECORD": "RECORD",
    "KEY_REWIND": "REWIND",
    "KEY_FASTFORWARD": "FAST_FORWARD",
    "KEY_SHUFFLE": "SHUFFLE",
    "KEY_CONFIG": "CONFIG",
    # -------------------------------------------------------------------------
    # Brightness & Display
    # -------------------------------------------------------------------------
    "KEY_BRIGHTNESSDOWN": "BRIGHTNESS_DOWN",
    "KEY_BRIGHTNESSUP": "BRIGHTNESS_UP",
    "KEY_KBDILLUMDOWN": "KBD_BRIGHT_DOWN",
    "KEY_KBDILLUMUP": "KBD_BRIGHT_UP",
    "KEY_KBDILLUMTOGGLE": "KBD_BRIGHT_TOGGLE",
    "KEY_SWITCHVIDEOMODE": "SWITCH_DISPLAY",
    "KEY_DISPLAYTOGGLE": "DISPLAY_TOGGLE",
    # -------------------------------------------------------------------------
    # System Keys
    # -------------------------------------------------------------------------
    "KEY_SYSRQ": "PRINT_SCREEN",
    "KEY_SCROLLLOCK": "SCROLL_LOCK",
    "KEY_PAUSE": "PAUSE",
    "KEY_BREAK": "BREAK",
    "KEY_CALC": "CALCULATOR",
    "KEY_MAIL": "MAIL",
    "KEY_WWW": "BROWSER",
    "KEY_COMPUTER": "MY_COMPUTER",
    "KEY_BACK": "BROWSER_BACK",
    "KEY_FORWARD": "BROWSER_FORWARD",
    "KEY_REFRESH": "BROWSER_REFRESH",
    "KEY_BOOKMARKS": "BOOKMARKS",
    "KEY_HOMEPAGE": "HOMEPAGE",
    "KEY_SEARCH": "SEARCH",
    "KEY_FILE": "FILE_MANAGER",
    "KEY_UNDO": "UNDO",
    "KEY_REDO": "REDO",
    "KEY_CUT": "CUT",
    "KEY_COPY": "COPY",
    "KEY_PASTE": "PASTE",
    "KEY_FIND": "FIND",
    "KEY_HELP": "HELP",
    # -------------------------------------------------------------------------
    # Punctuation & Symbols
    # -------------------------------------------------------------------------
    "KEY_MINUS": "MINUS",
    "KEY_EQUAL": "EQUAL",
    "KEY_LEFTBRACE": "LBRACKET",
    "KEY_RIGHTBRACE": "RBRACKET",
    "KEY_SEMICOLON": "SEMICOLON",
    "KEY_APOSTROPHE": "APOSTROPHE",
    "KEY_GRAVE": "GRAVE",
    "KEY_BACKSLASH": "BACKSLASH",
    "KEY_COMMA": "COMMA",
    "KEY_DOT": "DOT",
    "KEY_SLASH": "SLASH",
    "KEY_102ND": "INTL_BACKSLASH",  # International backslash
    # -------------------------------------------------------------------------
    # Numpad Keys
    # -------------------------------------------------------------------------
    "KEY_NUMLOCK": "NUM_LOCK",
    "KEY_KP0": "NUM_0",
    "KEY_KP1": "NUM_1",
    "KEY_KP2": "NUM_2",
    "KEY_KP3": "NUM_3",
    "KEY_KP4": "NUM_4",
    "KEY_KP5": "NUM_5",
    "KEY_KP6": "NUM_6",
    "KEY_KP7": "NUM_7",
    "KEY_KP8": "NUM_8",
    "KEY_KP9": "NUM_9",
    "KEY_KPENTER": "NUM_ENTER",
    "KEY_KPPLUS": "NUM_PLUS",
    "KEY_KPMINUS": "NUM_MINUS",
    "KEY_KPASTERISK": "NUM_MULT",
    "KEY_KPSLASH": "NUM_DIV",
    "KEY_KPDOT": "NUM_DOT",
    "KEY_KPEQUAL": "NUM_EQUAL",
    "KEY_KPCOMMA": "NUM_COMMA",
    "KEY_KPLEFTPAREN": "NUM_LPAREN",
    "KEY_KPRIGHTPAREN": "NUM_RPAREN",
}

# Add letter keys (A-Z)
for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
    EVDEV_TO_SCHEMA[f"KEY_{letter}"] = letter

# Add number keys (0-9)
for i in range(10):
    EVDEV_TO_SCHEMA[f"KEY_{i}"] = str(i)


# =============================================================================
# REVERSE MAPPINGS
# =============================================================================

# Schema name -> evdev code name
SCHEMA_TO_EVDEV: dict[str, str] = {v: k for k, v in EVDEV_TO_SCHEMA.items()}

# Also allow evdev names directly in schema (for power users)
for evdev_name in list(EVDEV_TO_SCHEMA.keys()):
    if evdev_name not in SCHEMA_TO_EVDEV:
        SCHEMA_TO_EVDEV[evdev_name] = evdev_name

# Schema name -> uinput code (integer)
SCHEMA_TO_UINPUT: dict[str, int] = {}


def _build_uinput_map():
    """Build the schema -> uinput code mapping."""
    for evdev_name, schema_name in EVDEV_TO_SCHEMA.items():
        code = getattr(ecodes, evdev_name, None)
        if code is not None:
            SCHEMA_TO_UINPUT[schema_name] = code
            SCHEMA_TO_UINPUT[evdev_name] = code


_build_uinput_map()


# =============================================================================
# KEY CATEGORIES (for GUI)
# =============================================================================

KEY_CATEGORIES = {
    "Mouse": [
        "MOUSE_LEFT",
        "MOUSE_RIGHT",
        "MOUSE_MIDDLE",
        "MOUSE_SIDE",
        "MOUSE_EXTRA",
        "MOUSE_FORWARD",
        "MOUSE_BACK",
    ],
    "Modifiers": [
        "CTRL",
        "CTRL_R",
        "SHIFT",
        "SHIFT_R",
        "ALT",
        "ALT_R",
        "META",
        "META_R",
    ],
    "Function": [
        "F1",
        "F2",
        "F3",
        "F4",
        "F5",
        "F6",
        "F7",
        "F8",
        "F9",
        "F10",
        "F11",
        "F12",
        "F13",
        "F14",
        "F15",
        "F16",
        "F17",
        "F18",
        "F19",
        "F20",
        "F21",
        "F22",
        "F23",
        "F24",
    ],
    "Navigation": [
        "UP",
        "DOWN",
        "LEFT",
        "RIGHT",
        "HOME",
        "END",
        "PAGEUP",
        "PAGEDOWN",
        "INSERT",
        "DELETE",
    ],
    "Media": [
        "PLAY_PAUSE",
        "STOP",
        "PREV_TRACK",
        "NEXT_TRACK",
        "MUTE",
        "VOL_DOWN",
        "VOL_UP",
        "REWIND",
        "FAST_FORWARD",
    ],
    "System": [
        "ESC",
        "TAB",
        "CAPS",
        "ENTER",
        "SPACE",
        "BACKSPACE",
        "PRINT_SCREEN",
        "SCROLL_LOCK",
        "PAUSE",
        "MENU",
        "POWER",
        "SLEEP",
    ],
    "Numpad": [
        "NUM_LOCK",
        "NUM_0",
        "NUM_1",
        "NUM_2",
        "NUM_3",
        "NUM_4",
        "NUM_5",
        "NUM_6",
        "NUM_7",
        "NUM_8",
        "NUM_9",
        "NUM_ENTER",
        "NUM_PLUS",
        "NUM_MINUS",
        "NUM_MULT",
        "NUM_DIV",
        "NUM_DOT",
    ],
}


# =============================================================================
# PUBLIC API
# =============================================================================


def evdev_code_to_schema(evdev_name: str) -> str:
    """Convert an evdev code name to schema key name.

    Args:
        evdev_name: evdev code name (e.g., 'KEY_A', 'BTN_LEFT')

    Returns:
        Schema key name (e.g., 'A', 'MOUSE_LEFT')
    """
    return EVDEV_TO_SCHEMA.get(evdev_name, evdev_name)


def schema_to_evdev_code(schema_name: str) -> int | None:
    """Convert a schema key name to evdev/uinput code.

    Args:
        schema_name: Schema key name (e.g., 'A', 'CTRL', 'MOUSE_LEFT')

    Returns:
        Integer evdev code, or None if not found
    """
    # Direct lookup in our mapping
    if schema_name in SCHEMA_TO_UINPUT:
        return SCHEMA_TO_UINPUT[schema_name]

    # Try reverse lookup
    evdev_name = SCHEMA_TO_EVDEV.get(schema_name, schema_name)
    code = getattr(ecodes, evdev_name, None)
    if code is not None:
        return int(code)

    # Try with KEY_ prefix
    code = getattr(ecodes, f"KEY_{schema_name}", None)
    if code is not None:
        return int(code)

    # Try with BTN_ prefix
    code = getattr(ecodes, f"BTN_{schema_name}", None)
    return int(code) if code is not None else None


def schema_to_evdev_name(schema_name: str) -> str | None:
    """Convert a schema key name to evdev code name.

    Args:
        schema_name: Schema key name

    Returns:
        evdev code name, or None if not found
    """
    return SCHEMA_TO_EVDEV.get(schema_name)


def get_all_schema_keys() -> list[str]:
    """Get all available schema key names (sorted)."""
    return sorted(set(EVDEV_TO_SCHEMA.values()))


def get_all_evdev_keys() -> list[str]:
    """Get all mapped evdev key names (sorted)."""
    return sorted(EVDEV_TO_SCHEMA.keys())


def get_keys_by_category() -> dict[str, list[str]]:
    """Get schema keys organized by category."""
    return KEY_CATEGORIES.copy()


def is_valid_key(key_name: str) -> bool:
    """Check if a key name is valid (either schema or evdev name).

    Args:
        key_name: Key name to validate

    Returns:
        True if the key is recognized
    """
    if key_name in SCHEMA_TO_UINPUT:
        return True
    if key_name in SCHEMA_TO_EVDEV:
        return True
    # Try with prefixes
    if getattr(ecodes, key_name, None) is not None:
        return True
    if getattr(ecodes, f"KEY_{key_name}", None) is not None:
        return True
    if getattr(ecodes, f"BTN_{key_name}", None) is not None:
        return True
    return False


def validate_key(key_name: str) -> tuple[bool, str]:
    """Validate a key name and return helpful error message.

    Args:
        key_name: Key name to validate

    Returns:
        Tuple of (is_valid, message)
    """
    if not key_name:
        return False, "Key name cannot be empty"

    if is_valid_key(key_name):
        code = schema_to_evdev_code(key_name)
        return True, f"Valid key: {key_name} (code={code})"

    # Try to suggest similar keys
    suggestions = []
    key_upper = key_name.upper()

    for schema_key in get_all_schema_keys():
        if key_upper in schema_key or schema_key in key_upper:
            suggestions.append(schema_key)

    if suggestions:
        return False, f"Unknown key '{key_name}'. Did you mean: {', '.join(suggestions[:5])}"

    return False, f"Unknown key '{key_name}'. Use --list to see available keys."


def evdev_event_to_schema(event_type: int, event_code: int) -> str | None:
    """Convert an evdev event type/code pair to schema key name.

    Args:
        event_type: evdev event type (e.g., EV_KEY)
        event_code: evdev event code

    Returns:
        Schema key name, or None if not a key event
    """
    if event_type == ecodes.EV_KEY:
        code_name = ecodes.KEY.get(event_code) or ecodes.BTN.get(event_code)
        if code_name:
            if isinstance(code_name, list):
                code_name = code_name[0]
            return evdev_code_to_schema(str(code_name))
    return None


def get_key_info(key_name: str) -> dict | None:
    """Get detailed information about a key.

    Args:
        key_name: Schema or evdev key name

    Returns:
        Dict with key info, or None if not found
    """
    if not is_valid_key(key_name):
        return None

    code = schema_to_evdev_code(key_name)
    evdev_name = SCHEMA_TO_EVDEV.get(key_name, key_name)
    schema_name = EVDEV_TO_SCHEMA.get(evdev_name, key_name)

    # Find category
    category = "Other"
    for cat, keys in KEY_CATEGORIES.items():
        if schema_name in keys:
            category = cat
            break

    return {
        "schema_name": schema_name,
        "evdev_name": evdev_name,
        "code": code,
        "category": category,
    }
