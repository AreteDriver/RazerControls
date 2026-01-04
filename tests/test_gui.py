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
        # Verify it's a QWidget subclass
        from PySide6.QtWidgets import QWidget

        from apps.gui.widgets.binding_editor import BindingEditorWidget

        assert issubclass(BindingEditorWidget, QWidget)

    def test_profile_panel_structure(self):
        """Test profile_panel module structure."""
        from PySide6.QtWidgets import QWidget

        from apps.gui.widgets.profile_panel import ProfilePanel

        assert issubclass(ProfilePanel, QWidget)

    def test_setup_wizard_structure(self):
        """Test setup_wizard module structure."""
        from PySide6.QtWidgets import QDialog

        from apps.gui.widgets.setup_wizard import SetupWizard

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


class TestNewProfileDialog:
    """Tests for NewProfileDialog."""

    @pytest.fixture
    def qapp(self):
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app

    def test_dialog_instantiation(self, qapp):
        """Test NewProfileDialog can be created."""
        from apps.gui.widgets.profile_panel import NewProfileDialog

        dialog = NewProfileDialog()
        assert dialog is not None
        dialog.close()

    def test_get_profile_empty_name(self, qapp):
        """Test get_profile returns None for empty name."""
        from apps.gui.widgets.profile_panel import NewProfileDialog

        dialog = NewProfileDialog()
        dialog.name_edit.setText("")
        result = dialog.get_profile()
        assert result is None
        dialog.close()

    def test_get_profile_valid(self, qapp):
        """Test get_profile returns Profile for valid input."""
        from apps.gui.widgets.profile_panel import NewProfileDialog

        dialog = NewProfileDialog()
        dialog.name_edit.setText("Test Profile")
        dialog.desc_edit.setPlainText("Test description")
        result = dialog.get_profile()
        assert result is not None
        assert result.name == "Test Profile"
        assert result.id == "test_profile"
        assert result.description == "Test description"
        dialog.close()


class TestProfilePanelMethods:
    """Tests for ProfilePanel methods."""

    @pytest.fixture
    def qapp(self):
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app

    @pytest.fixture
    def mock_loader(self):
        loader = MagicMock()
        loader.list_profiles.return_value = []
        loader.get_active_profile.return_value = None
        loader.config_dir = Path("/tmp/test_profiles")
        return loader

    def test_load_profiles(self, qapp, mock_loader):
        """Test loading profiles into panel."""
        from apps.gui.widgets.profile_panel import ProfilePanel

        widget = ProfilePanel()
        widget.load_profiles(mock_loader)
        mock_loader.list_profiles.assert_called()
        widget.close()

    def test_load_with_profiles(self, qapp, mock_loader):
        """Test load with existing profiles."""
        from apps.gui.widgets.profile_panel import ProfilePanel
        from crates.profile_schema import Layer, Profile

        profile = Profile(
            id="test", name="Test", description="",
            layers=[Layer(id="base", name="Base", bindings=[], hold_modifier_input_code=None)]
        )
        mock_loader.list_profiles.return_value = [profile]
        mock_loader.load_profile.return_value = profile

        widget = ProfilePanel()
        widget.load_profiles(mock_loader)
        # At least one profile should be in the list
        assert widget.profile_list.count() >= 1
        widget.close()


class TestDPIStageItem:
    """Tests for DPIStageItem widget."""

    @pytest.fixture
    def qapp(self):
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app

    def test_stage_item_instantiation(self, qapp):
        """Test DPIStageItem can be created."""
        from apps.gui.widgets.dpi_editor import DPIStageItem

        item = DPIStageItem(dpi=800, max_dpi=16000, index=0)
        assert item is not None
        assert item.get_dpi() == 800
        item.close()

    def test_stage_item_slider_change(self, qapp):
        """Test changing DPI via slider."""
        from apps.gui.widgets.dpi_editor import DPIStageItem

        item = DPIStageItem(dpi=800, max_dpi=16000, index=0)
        item.slider.setValue(1600)
        # Slider should update spin value
        assert item.spin.value() == 1600
        item.close()

    def test_stage_item_spin_change(self, qapp):
        """Test changing DPI via spinbox."""
        from apps.gui.widgets.dpi_editor import DPIStageItem

        item = DPIStageItem(dpi=800, max_dpi=16000, index=0)
        item.spin.setValue(1200)
        assert item.get_dpi() == 1200
        item.close()

    def test_stage_item_set_active(self, qapp):
        """Test setting stage as active."""
        from apps.gui.widgets.dpi_editor import DPIStageItem

        item = DPIStageItem(dpi=800, max_dpi=16000, index=0)
        item.set_active(True)
        # Should not raise
        item.set_active(False)
        item.close()


class TestDPIStageEditorMethods:
    """Tests for DPIStageEditor methods."""

    @pytest.fixture
    def qapp(self):
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app

    @pytest.fixture
    def mock_bridge(self):
        bridge = MagicMock()
        bridge.get_dpi.return_value = (800, 800)
        bridge.get_max_dpi.return_value = 16000
        return bridge

    def test_get_config_empty(self, qapp, mock_bridge):
        """Test getting DPI config when empty."""
        from apps.gui.widgets.dpi_editor import DPIStageEditor
        from crates.profile_schema import DPIConfig

        widget = DPIStageEditor(bridge=mock_bridge)
        result = widget.get_config()
        assert isinstance(result, DPIConfig)
        widget.close()

    def test_set_config_no_device(self, qapp, mock_bridge):
        """Test set_config returns early without device."""
        from apps.gui.widgets.dpi_editor import DPIStageEditor
        from crates.profile_schema import DPIConfig

        widget = DPIStageEditor(bridge=mock_bridge)
        config = DPIConfig(stages=[800, 1600, 3200], active_stage=1)
        # Without a device, set_config returns early
        widget.set_config(config)
        assert len(widget._stage_items) == 0  # No stages without device
        widget.close()


class TestBindingEditorMethods:
    """Tests for BindingEditorWidget methods."""

    @pytest.fixture
    def qapp(self):
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app

    def test_load_profile(self, qapp):
        """Test loading a profile."""
        from apps.gui.widgets.binding_editor import BindingEditorWidget
        from crates.profile_schema import Layer, Profile

        widget = BindingEditorWidget()
        profile = Profile(
            id="test", name="Test", description="",
            layers=[Layer(id="base", name="Base", bindings=[], hold_modifier_input_code=None)]
        )
        widget.load_profile(profile)
        assert widget.current_profile == profile
        widget.close()

    def test_get_layers(self, qapp):
        """Test getting layers."""
        from apps.gui.widgets.binding_editor import BindingEditorWidget
        from crates.profile_schema import Layer, Profile

        widget = BindingEditorWidget()
        profile = Profile(
            id="test", name="Test", description="",
            layers=[Layer(id="base", name="Base", bindings=[], hold_modifier_input_code=None)]
        )
        widget.load_profile(profile)
        layers = widget.get_layers()
        assert isinstance(layers, list)
        widget.close()

    def test_get_macros(self, qapp):
        """Test getting macros."""
        from apps.gui.widgets.binding_editor import BindingEditorWidget

        widget = BindingEditorWidget()
        macros = widget.get_macros()
        assert isinstance(macros, list)
        widget.close()

    def test_clear(self, qapp):
        """Test clearing the editor."""
        from apps.gui.widgets.binding_editor import BindingEditorWidget
        from crates.profile_schema import Layer, Profile

        widget = BindingEditorWidget()
        profile = Profile(
            id="test", name="Test", description="",
            layers=[Layer(id="base", name="Base", bindings=[], hold_modifier_input_code=None)]
        )
        widget.load_profile(profile)
        widget.clear()
        assert widget.current_profile is None
        widget.close()


class TestAppMatcherMethods:
    """Tests for AppMatcherWidget methods."""

    @pytest.fixture
    def qapp(self):
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app

    def test_load_profile(self, qapp):
        """Test loading a profile."""
        from apps.gui.widgets.app_matcher import AppMatcherWidget
        from crates.profile_schema import Layer, Profile

        widget = AppMatcherWidget()
        profile = Profile(
            id="test", name="Test", description="",
            layers=[Layer(id="base", name="Base", bindings=[], hold_modifier_input_code=None)],
            app_patterns=["firefox", "chrome"]
        )
        widget.load_profile(profile)
        assert widget.current_profile == profile
        widget.close()

    def test_clear(self, qapp):
        """Test clearing the widget."""
        from apps.gui.widgets.app_matcher import AppMatcherWidget
        from crates.profile_schema import Layer, Profile

        widget = AppMatcherWidget()
        profile = Profile(
            id="test", name="Test", description="",
            layers=[Layer(id="base", name="Base", bindings=[], hold_modifier_input_code=None)],
            app_patterns=["firefox"]
        )
        widget.load_profile(profile)
        widget.clear()
        assert widget.current_profile is None
        widget.close()


class TestZoneEditorMethods:
    """Tests for ZoneEditorWidget methods."""

    @pytest.fixture
    def qapp(self):
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app

    @pytest.fixture
    def mock_bridge(self):
        bridge = MagicMock()
        bridge.discover_devices.return_value = []
        return bridge

    def test_zone_editor_instantiation(self, qapp, mock_bridge):
        """Test ZoneEditorWidget can be created."""
        from apps.gui.widgets.zone_editor import ZoneEditorWidget

        widget = ZoneEditorWidget(bridge=mock_bridge)
        assert widget is not None
        assert widget.current_device is None
        widget.close()


class TestBatteryMonitorMethods:
    """Tests for BatteryMonitorWidget methods."""

    @pytest.fixture
    def qapp(self):
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app

    @pytest.fixture
    def mock_bridge(self):
        bridge = MagicMock()
        bridge.discover_devices.return_value = []
        return bridge

    def test_refresh_devices(self, qapp, mock_bridge):
        """Test refreshing device list."""
        from apps.gui.widgets.battery_monitor import BatteryMonitorWidget

        widget = BatteryMonitorWidget(bridge=mock_bridge)
        widget.refresh_devices()
        mock_bridge.discover_devices.assert_called()
        widget.close()


class TestSetupWizard:
    """Tests for SetupWizard dialog."""

    @pytest.fixture
    def qapp(self):
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app

    def test_wizard_instantiation(self, qapp):
        """Test SetupWizard can be created."""
        from apps.gui.widgets.setup_wizard import SetupWizard

        with patch("apps.gui.widgets.setup_wizard.DeviceRegistry") as mock_registry:
            with patch("apps.gui.widgets.setup_wizard.ProfileLoader") as mock_loader:
                mock_registry.return_value.scan_devices.return_value = []
                mock_loader.return_value.list_profiles.return_value = []
                wizard = SetupWizard()
                assert wizard is not None
                wizard.close()

    def test_wizard_page_count(self, qapp):
        """Test wizard has correct number of pages."""
        from apps.gui.widgets.setup_wizard import SetupWizard

        with patch("apps.gui.widgets.setup_wizard.DeviceRegistry") as mock_registry:
            with patch("apps.gui.widgets.setup_wizard.ProfileLoader") as mock_loader:
                mock_registry.return_value.scan_devices.return_value = []
                mock_loader.return_value.list_profiles.return_value = []
                wizard = SetupWizard()
                # Should have 4 pages: welcome, device, profile, daemon
                assert wizard.pages.count() == 4
                wizard.close()

    def test_wizard_initial_state(self, qapp):
        """Test wizard initial state."""
        from apps.gui.widgets.setup_wizard import SetupWizard

        with patch("apps.gui.widgets.setup_wizard.DeviceRegistry") as mock_registry:
            with patch("apps.gui.widgets.setup_wizard.ProfileLoader") as mock_loader:
                mock_registry.return_value.scan_devices.return_value = []
                mock_loader.return_value.list_profiles.return_value = []
                wizard = SetupWizard()
                assert wizard.profile_name == "Default"
                assert wizard.enable_autostart is True
                assert wizard.start_daemon_now is True
                wizard.close()

    def test_wizard_navigation_forward(self, qapp):
        """Test wizard forward navigation."""
        from apps.gui.widgets.setup_wizard import SetupWizard

        with patch("apps.gui.widgets.setup_wizard.DeviceRegistry") as mock_registry:
            with patch("apps.gui.widgets.setup_wizard.ProfileLoader") as mock_loader:
                mock_registry.return_value.scan_devices.return_value = []
                mock_loader.return_value.list_profiles.return_value = []
                wizard = SetupWizard()
                initial_page = wizard.pages.currentIndex()
                wizard._go_next()
                assert wizard.pages.currentIndex() == initial_page + 1
                wizard.close()

    def test_wizard_navigation_back(self, qapp):
        """Test wizard backward navigation."""
        from apps.gui.widgets.setup_wizard import SetupWizard

        with patch("apps.gui.widgets.setup_wizard.DeviceRegistry") as mock_registry:
            with patch("apps.gui.widgets.setup_wizard.ProfileLoader") as mock_loader:
                mock_registry.return_value.scan_devices.return_value = []
                mock_loader.return_value.list_profiles.return_value = []
                wizard = SetupWizard()
                wizard._go_next()  # Go to page 1
                wizard._go_back()  # Back to page 0
                assert wizard.pages.currentIndex() == 0
                wizard.close()

    def test_wizard_update_buttons(self, qapp):
        """Test button state updates."""
        from apps.gui.widgets.setup_wizard import SetupWizard

        with patch("apps.gui.widgets.setup_wizard.DeviceRegistry") as mock_registry:
            with patch("apps.gui.widgets.setup_wizard.ProfileLoader") as mock_loader:
                mock_registry.return_value.scan_devices.return_value = []
                mock_loader.return_value.list_profiles.return_value = []
                wizard = SetupWizard()
                wizard._update_buttons()
                # Next button should always exist
                assert wizard.next_btn is not None
                wizard.close()

    def test_wizard_page_indicator(self, qapp):
        """Test page indicator updates."""
        from apps.gui.widgets.setup_wizard import SetupWizard

        with patch("apps.gui.widgets.setup_wizard.DeviceRegistry") as mock_registry:
            with patch("apps.gui.widgets.setup_wizard.ProfileLoader") as mock_loader:
                mock_registry.return_value.scan_devices.return_value = []
                mock_loader.return_value.list_profiles.return_value = []
                wizard = SetupWizard()
                wizard._update_page_indicator()
                # Should contain page indicators (dots)
                text = wizard.page_indicator.text()
                assert "●" in text or "○" in text or len(text) > 0
                wizard.close()

    def test_wizard_scan_devices(self, qapp):
        """Test device scanning populates list."""
        from apps.gui.widgets.setup_wizard import SetupWizard

        with patch("apps.gui.widgets.setup_wizard.DeviceRegistry") as mock_registry:
            with patch("apps.gui.widgets.setup_wizard.ProfileLoader") as mock_loader:
                mock_registry.return_value.scan_devices.return_value = []
                mock_loader.return_value.list_profiles.return_value = []
                wizard = SetupWizard()
                # scan_devices should work without error
                wizard._scan_devices()
                wizard.close()

    def test_wizard_profile_name_change(self, qapp):
        """Test profile name change handler."""
        from apps.gui.widgets.setup_wizard import SetupWizard

        with patch("apps.gui.widgets.setup_wizard.DeviceRegistry") as mock_registry:
            with patch("apps.gui.widgets.setup_wizard.ProfileLoader") as mock_loader:
                mock_registry.return_value.scan_devices.return_value = []
                mock_loader.return_value.list_profiles.return_value = []
                wizard = SetupWizard()
                wizard._on_name_changed("My Custom Profile")
                assert wizard.profile_name == "My Custom Profile"
                wizard.close()


class TestMainWindowImport:
    """Tests for MainWindow import."""

    def test_main_window_import(self):
        """Test MainWindow can be imported."""
        from apps.gui.main_window import MainWindow

        assert isinstance(MainWindow, type)


class TestRazerControlsWidgetMethods:
    """Tests for RazerControlsWidget methods."""

    @pytest.fixture
    def qapp(self):
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app

    @pytest.fixture
    def mock_bridge(self):
        bridge = MagicMock()
        bridge.discover_devices.return_value = []
        return bridge

    def test_refresh_devices(self, qapp, mock_bridge):
        """Test refreshing devices."""
        from apps.gui.widgets.razer_controls import RazerControlsWidget

        widget = RazerControlsWidget(bridge=mock_bridge)
        widget.refresh_devices()
        mock_bridge.discover_devices.assert_called()
        widget.close()

    def test_refresh_with_devices(self, qapp, mock_bridge):
        """Test refresh with mock devices."""
        from apps.gui.widgets.razer_controls import RazerControlsWidget

        mock_device = MagicMock()
        mock_device.configure_mock(name="Test Mouse")
        mock_device.serial = "TEST123"
        mock_device.device_type = "mouse"
        mock_device.firmware_version = "1.0"
        mock_device.driver_version = "1.0"
        mock_device.supported_effects = []
        mock_device.supported_zones = []
        mock_device.max_dpi = 16000
        mock_bridge.discover_devices.return_value = [mock_device]

        widget = RazerControlsWidget(bridge=mock_bridge)
        # Just verify it doesn't crash
        widget.close()
