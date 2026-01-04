"""Profile schema definitions using Pydantic."""

from enum import Enum

from pydantic import BaseModel, Field


class ActionType(str, Enum):
    """Types of actions a binding can perform."""

    KEY = "key"  # Single key press
    CHORD = "chord"  # Multiple keys pressed together
    MACRO = "macro"  # Reference to a macro
    PASSTHROUGH = "passthrough"  # Pass the original key through
    DISABLED = "disabled"  # Block the key entirely


class MacroStepType(str, Enum):
    """Types of steps in a macro."""

    KEY_DOWN = "key_down"
    KEY_UP = "key_up"
    KEY_PRESS = "key_press"  # Down + Up
    DELAY = "delay"
    TEXT = "text"  # Type a string


class LightingEffect(str, Enum):
    """Supported lighting effects."""

    STATIC = "static"
    BREATHING = "breathing"
    SPECTRUM = "spectrum"
    WAVE = "wave"
    REACTIVE = "reactive"
    OFF = "off"


class MacroStep(BaseModel):
    """A single step in a macro sequence."""

    type: MacroStepType
    key: str | None = None  # For key actions
    delay_ms: int | None = None  # For delay actions
    text: str | None = None  # For text actions


class MacroAction(BaseModel):
    """A macro definition - a sequence of steps."""

    id: str = Field(..., description="Unique macro identifier")
    name: str = Field(..., description="Human-readable name")
    steps: list[MacroStep] = Field(default_factory=list)
    repeat_count: int = Field(default=1, ge=1, le=100)
    repeat_delay_ms: int = Field(default=0, ge=0, le=5000)


class Binding(BaseModel):
    """A key/button binding configuration."""

    input_code: str = Field(..., description="evdev input code, e.g., BTN_SIDE")
    action_type: ActionType = ActionType.KEY
    output_keys: list[str] = Field(default_factory=list, description="Keys to output")
    macro_id: str | None = Field(None, description="Reference to macro if action_type=macro")


class Layer(BaseModel):
    """A layer of bindings - base layer or shift layer."""

    id: str = Field(..., description="Layer identifier")
    name: str = Field(..., description="Human-readable name")
    bindings: list[Binding] = Field(default_factory=list)
    hold_modifier_input_code: str | None = Field(
        None, description="If set, this layer activates when this key is held"
    )


class ZoneColor(BaseModel):
    """Color assignment for a lighting zone."""

    zone_id: str = Field(..., description="Zone identifier (e.g., 'wasd', 'function_row')")
    color: tuple[int, int, int] = Field(..., description="RGB color tuple")


class KeyColor(BaseModel):
    """Color for a specific key position in the matrix."""

    row: int = Field(..., ge=0, description="Row index (0-based)")
    col: int = Field(..., ge=0, description="Column index (0-based)")
    color: tuple[int, int, int] = Field(..., description="RGB color tuple")


class MatrixLightingConfig(BaseModel):
    """Per-key/matrix lighting configuration."""

    enabled: bool = Field(default=False, description="Whether matrix mode is active")

    # Zone-based colors (used by zone editor)
    zones: list[ZoneColor] = Field(default_factory=list)

    # Per-key colors (for visual keyboard editor, future)
    keys: list[KeyColor] = Field(default_factory=list)

    # Default color for keys not explicitly set
    default_color: tuple[int, int, int] = Field(
        default=(0, 0, 0), description="Fallback color for unset keys"
    )


class LightingConfig(BaseModel):
    """Lighting configuration for a device."""

    effect: LightingEffect = LightingEffect.STATIC
    brightness: int = Field(default=100, ge=0, le=100)
    color: tuple[int, int, int] = Field(default=(0, 255, 0), description="RGB tuple")
    speed: int = Field(default=50, ge=0, le=100, description="Effect speed")

    # Matrix/per-key lighting (optional)
    matrix: MatrixLightingConfig | None = Field(
        default=None, description="Per-key RGB configuration"
    )


class DPIConfig(BaseModel):
    """DPI configuration for mice."""

    stages: list[int] = Field(default_factory=lambda: [800, 1600, 3200], description="DPI stages")
    active_stage: int = Field(default=0, ge=0, description="Index of active stage")


class DeviceConfig(BaseModel):
    """Configuration for a specific Razer device."""

    device_id: str = Field(..., description="Stable device identifier")
    lighting: LightingConfig | None = None
    dpi: DPIConfig | None = None


class Profile(BaseModel):
    """A complete profile configuration."""

    id: str = Field(..., description="Unique profile identifier")
    name: str = Field(..., description="Human-readable name")
    description: str = Field(default="")

    # Input device selection (stable IDs)
    input_devices: list[str] = Field(
        default_factory=list, description="List of input device stable IDs to grab"
    )

    # Layers for key remapping
    layers: list[Layer] = Field(default_factory=list)

    # Macros defined in this profile
    macros: list[MacroAction] = Field(default_factory=list)

    # Per-device hardware configs (lighting, DPI)
    devices: list[DeviceConfig] = Field(default_factory=list)

    # App matching for auto-switching
    match_process_names: list[str] = Field(
        default_factory=list, description="Process names that trigger this profile"
    )
    is_default: bool = Field(default=False, description="Use as fallback profile")
