"""GUI widgets."""

from .app_matcher import AppMatcherWidget
from .battery_monitor import BatteryMonitorWidget
from .binding_editor import BindingEditorWidget
from .device_list import DeviceListWidget
from .dpi_editor import DPIStageEditor
from .hotkey_editor import HotkeyEditorDialog, HotkeyEditorWidget
from .macro_editor import MacroEditorWidget
from .profile_panel import ProfilePanel
from .razer_controls import RazerControlsWidget
from .setup_wizard import SetupWizard

__all__ = [
    "AppMatcherWidget",
    "BatteryMonitorWidget",
    "BindingEditorWidget",
    "DeviceListWidget",
    "DPIStageEditor",
    "HotkeyEditorDialog",
    "HotkeyEditorWidget",
    "MacroEditorWidget",
    "ProfilePanel",
    "RazerControlsWidget",
    "SetupWizard",
]
