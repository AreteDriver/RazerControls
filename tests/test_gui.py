"""Tests for GUI module imports and basic structure."""

import ast
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Set offscreen platform before any Qt imports
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


class TestGUIImports:
    """Tests that GUI modules can be imported."""

    def test_widgets_init_imports(self):
        """Test that widgets __init__ exports the expected classes."""
        from apps.gui.widgets import (
            AppMatcherWidget,
            BatteryMonitorWidget,
            BindingEditorWidget,
            DeviceListWidget,
            DPIStageEditor,
            HotkeyEditorDialog,
            HotkeyEditorWidget,
            MacroEditorWidget,
            ProfilePanel,
            RazerControlsWidget,
            SetupWizard,
            ZoneEditorWidget,
        )

        # Verify these are classes
        assert isinstance(AppMatcherWidget, type)
        assert isinstance(BatteryMonitorWidget, type)
        assert isinstance(BindingEditorWidget, type)
        assert isinstance(DeviceListWidget, type)
        assert isinstance(DPIStageEditor, type)
        assert isinstance(HotkeyEditorDialog, type)
        assert isinstance(HotkeyEditorWidget, type)
        assert isinstance(MacroEditorWidget, type)
        assert isinstance(ProfilePanel, type)
        assert isinstance(RazerControlsWidget, type)
        assert isinstance(SetupWizard, type)
        assert isinstance(ZoneEditorWidget, type)

    def test_main_window_import(self):
        """Test that MainWindow can be imported."""
        from apps.gui.main_window import MainWindow

        assert isinstance(MainWindow, type)

    def test_theme_import(self):
        """Test that theme module can be imported."""
        from apps.gui.theme import apply_dark_theme

        assert callable(apply_dark_theme)


class TestGUIMainGuard:
    """Tests for __name__ == '__main__' guard in GUI main."""

    def test_main_guard_exists(self):
        """Test that main guard exists in GUI main.py."""
        source_path = Path(__file__).parent.parent / "apps" / "gui" / "main.py"
        tree = ast.parse(source_path.read_text())

        has_main_guard = False
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                if (
                    isinstance(node.test, ast.Compare)
                    and isinstance(node.test.left, ast.Name)
                    and node.test.left.id == "__name__"
                ):
                    has_main_guard = True
                    break

        assert has_main_guard, "main guard not found in GUI main.py"


class TestGUIWidgetStructure:
    """Tests for GUI widget class structure."""

    def test_macro_editor_has_recording_worker(self):
        """Test that macro_editor has RecordingWorker class."""
        from apps.gui.widgets.macro_editor import RecordingWorker

        assert isinstance(RecordingWorker, type)

    def test_binding_editor_structure(self):
        """Test binding_editor module structure."""
        from apps.gui.widgets.binding_editor import BindingEditorWidget

        # Verify it's a QWidget subclass
        from PySide6.QtWidgets import QWidget

        assert issubclass(BindingEditorWidget, QWidget)

    def test_profile_panel_structure(self):
        """Test profile_panel module structure."""
        from apps.gui.widgets.profile_panel import ProfilePanel

        from PySide6.QtWidgets import QWidget

        assert issubclass(ProfilePanel, QWidget)

    def test_setup_wizard_structure(self):
        """Test setup_wizard module structure."""
        from apps.gui.widgets.setup_wizard import SetupWizard

        from PySide6.QtWidgets import QDialog

        assert issubclass(SetupWizard, QDialog)


class TestWidgetInstantiation:
    """Tests that widgets can be instantiated with mocked dependencies."""

    @pytest.fixture
    def qapp(self):
        """Create QApplication for widget tests."""
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app

    @pytest.fixture
    def mock_bridge(self):
        """Mock OpenRazer bridge."""
        bridge = MagicMock()
        bridge.discover_devices.return_value = []
        return bridge

    @pytest.fixture
    def mock_loader(self):
        """Mock profile loader."""
        loader = MagicMock()
        loader.list_profiles.return_value = []
        loader.get_active_profile.return_value = None
        return loader

    def test_device_list_widget(self, qapp):
        """Test DeviceListWidget instantiation."""
        from apps.gui.widgets.device_list import DeviceListWidget

        mock_registry = MagicMock()
        mock_registry.scan_devices.return_value = []
        widget = DeviceListWidget(registry=mock_registry)
        assert widget is not None
        widget.close()

    def test_profile_panel_widget(self, qapp, mock_loader):
        """Test ProfilePanel instantiation."""
        from apps.gui.widgets.profile_panel import ProfilePanel

        with patch("apps.gui.widgets.profile_panel.ProfileLoader", return_value=mock_loader):
            widget = ProfilePanel()
            assert widget is not None
            widget.close()

    def test_hotkey_editor_widget(self, qapp):
        """Test HotkeyEditorWidget instantiation."""
        from apps.gui.widgets.hotkey_editor import HotkeyEditorWidget

        widget = HotkeyEditorWidget()
        assert widget is not None
        widget.close()

    def test_battery_monitor_widget(self, qapp, mock_bridge):
        """Test BatteryMonitorWidget instantiation."""
        from apps.gui.widgets.battery_monitor import BatteryMonitorWidget

        mock_bridge.discover_devices.return_value = []
        widget = BatteryMonitorWidget(bridge=mock_bridge)
        assert widget is not None
        widget.close()

    def test_dpi_stage_editor(self, qapp, mock_bridge):
        """Test DPIStageEditor instantiation."""
        from apps.gui.widgets.dpi_editor import DPIStageEditor

        mock_bridge.get_dpi.return_value = (800, 800)
        widget = DPIStageEditor(bridge=mock_bridge)
        assert widget is not None
        widget.close()


    def test_zone_editor_widget(self, qapp, mock_bridge):
        """Test ZoneEditorWidget instantiation."""
        from apps.gui.widgets.zone_editor import ZoneEditorWidget

        mock_bridge.discover_devices.return_value = []
        widget = ZoneEditorWidget(bridge=mock_bridge)
        assert widget is not None
        widget.close()

    def test_macro_editor_widget(self, qapp):
        """Test MacroEditorWidget instantiation."""
        from apps.gui.widgets.macro_editor import MacroEditorWidget

        widget = MacroEditorWidget()
        assert widget is not None
        widget.close()

    def test_binding_editor_widget(self, qapp):
        """Test BindingEditorWidget instantiation."""
        from apps.gui.widgets.binding_editor import BindingEditorWidget

        widget = BindingEditorWidget()
        assert widget is not None
        widget.close()

    def test_app_matcher_widget(self, qapp):
        """Test AppMatcherWidget instantiation."""
        from apps.gui.widgets.app_matcher import AppMatcherWidget

        widget = AppMatcherWidget()
        assert widget is not None
        widget.close()

    def test_razer_controls_widget(self, qapp, mock_bridge):
        """Test RazerControlsWidget instantiation."""
        from apps.gui.widgets.razer_controls import RazerControlsWidget

        mock_bridge.discover_devices.return_value = []
        widget = RazerControlsWidget(bridge=mock_bridge)
        assert widget is not None
        widget.close()


class TestThemeApplication:
    """Tests for theme application."""

    @pytest.fixture
    def qapp(self):
        """Create QApplication for theme tests."""
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app

    def test_apply_dark_theme(self, qapp):
        """Test applying dark theme to application."""
        from apps.gui.theme import apply_dark_theme

        # Should not raise
        apply_dark_theme(qapp)

    def test_apply_dark_theme_sets_stylesheet(self, qapp):
        """Test that dark theme sets a stylesheet."""
        from apps.gui.theme import apply_dark_theme

        apply_dark_theme(qapp)
        # Theme should set some stylesheet
        assert qapp.styleSheet() is not None


class TestHotkeyCapture:
    """Tests for HotkeyCapture widget."""

    @pytest.fixture
    def qapp(self):
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app

    def test_hotkey_capture_instantiation(self, qapp):
        """Test HotkeyCapture can be created."""
        from apps.gui.widgets.hotkey_editor import HotkeyCapture
        from crates.profile_schema import HotkeyBinding

        binding = HotkeyBinding(key="f1", modifiers=["ctrl"])
        widget = HotkeyCapture(binding)
        assert widget is not None
        assert widget.binding == binding
        widget.close()

    def test_hotkey_capture_set_binding(self, qapp):
        """Test HotkeyCapture.set_binding() method."""
        from apps.gui.widgets.hotkey_editor import HotkeyCapture
        from crates.profile_schema import HotkeyBinding

        binding1 = HotkeyBinding(key="f1", modifiers=["ctrl"])
        binding2 = HotkeyBinding(key="f2", modifiers=["alt"])

        widget = HotkeyCapture(binding1)
        widget.set_binding(binding2)
        assert widget.binding == binding2
        widget.close()

    def test_hotkey_capture_display(self, qapp):
        """Test HotkeyCapture displays binding text."""
        from apps.gui.widgets.hotkey_editor import HotkeyCapture
        from crates.profile_schema import HotkeyBinding

        binding = HotkeyBinding(key="f1", modifiers=["ctrl"])
        widget = HotkeyCapture(binding)
        # Should display binding text
        assert "F1" in widget.text() or "f1" in widget.text().lower()
        widget.close()


class TestHotkeyEditorDialog:
    """Tests for HotkeyEditorDialog."""

    @pytest.fixture
    def qapp(self):
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app

    def test_dialog_instantiation(self, qapp):
        """Test HotkeyEditorDialog can be created."""
        from apps.gui.widgets.hotkey_editor import HotkeyEditorDialog

        dialog = HotkeyEditorDialog()
        assert dialog is not None
        dialog.close()


class TestDeviceListMethods:
    """Tests for DeviceListWidget methods."""

    @pytest.fixture
    def qapp(self):
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app

    def test_refresh_empty(self, qapp):
        """Test refresh with no devices."""
        from apps.gui.widgets.device_list import DeviceListWidget

        mock_registry = MagicMock()
        mock_registry.scan_devices.return_value = []
        widget = DeviceListWidget(registry=mock_registry)
        widget.refresh()
        assert widget.list_widget.count() == 0
        widget.close()

    def test_refresh_with_devices(self, qapp):
        """Test refresh with mock devices."""
        from apps.gui.widgets.device_list import DeviceListWidget

        mock_device = MagicMock()
        mock_device.stable_id = "razer-test-mouse"
        mock_device.name = "Test Mouse"

        mock_registry = MagicMock()
        mock_registry.scan_devices.return_value = [mock_device]
        widget = DeviceListWidget(registry=mock_registry)
        widget.refresh()
        assert widget.list_widget.count() >= 1
        widget.close()


class TestMacroEditorMethods:
    """Tests for MacroEditorWidget methods."""

    @pytest.fixture
    def qapp(self):
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app

    def test_add_macro(self, qapp):
        """Test adding a new macro."""
        from apps.gui.widgets.macro_editor import MacroEditorWidget

        widget = MacroEditorWidget()
        initial_count = len(widget._macros)
        widget._add_macro()
        assert len(widget._macros) == initial_count + 1
        widget.close()

    def test_macro_editor_get_macros(self, qapp):
        """Test getting macros list."""
        from apps.gui.widgets.macro_editor import MacroEditorWidget

        widget = MacroEditorWidget()
        macros = widget.get_macros()
        assert isinstance(macros, list)
        widget.close()
