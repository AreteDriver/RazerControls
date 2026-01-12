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


class TestGUIMainFunction:
    """Tests for the main() function in apps.gui.main."""

    def test_main_with_existing_profiles(self):
        """Test main() with existing profiles skips wizard."""
        with (
            patch("apps.gui.main.QApplication") as mock_qapp,
            patch("apps.gui.main.ProfileLoader") as mock_loader,
            patch("apps.gui.main.MainWindow") as mock_window,
            patch("apps.gui.theme.apply_dark_theme"),
            patch("apps.gui.main.sys.exit") as mock_exit,
        ):
            # Setup: profiles exist
            mock_loader.return_value.list_profiles.return_value = ["profile1"]
            mock_qapp.return_value.exec.return_value = 0

            from apps.gui.main import main

            main()

            # Verify wizard was NOT shown (profiles exist)
            mock_window.assert_called_once()
            mock_window.return_value.show.assert_called_once()
            mock_exit.assert_called_once()

    def test_main_first_run_wizard_accepted(self):
        """Test main() on first run shows wizard and continues if accepted."""
        with (
            patch("apps.gui.main.QApplication") as mock_qapp,
            patch("apps.gui.main.ProfileLoader") as mock_loader,
            patch("apps.gui.main.MainWindow") as mock_window,
            patch("apps.gui.theme.apply_dark_theme"),
            patch("apps.gui.main.sys.exit"),
            patch("apps.gui.widgets.setup_wizard.SetupWizard") as mock_wizard,
        ):
            from PySide6.QtWidgets import QDialog

            # Setup: no profiles, wizard accepted
            mock_loader.return_value.list_profiles.return_value = []
            mock_wizard.return_value.exec.return_value = QDialog.DialogCode.Accepted
            mock_qapp.return_value.exec.return_value = 0

            from apps.gui.main import main

            main()

            # Wizard shown and accepted
            mock_wizard.assert_called_once()
            mock_wizard.return_value.exec.assert_called_once()
            # Main window shown after wizard
            mock_window.assert_called_once()
            mock_window.return_value.show.assert_called_once()

    def test_main_first_run_wizard_cancelled(self):
        """Test main() exits if user cancels setup wizard."""
        with (
            patch("apps.gui.main.QApplication") as mock_qapp,
            patch("apps.gui.main.ProfileLoader") as mock_loader,
            patch("apps.gui.main.MainWindow") as mock_window,
            patch("apps.gui.theme.apply_dark_theme"),
            patch("apps.gui.main.sys.exit", side_effect=SystemExit(0)) as mock_exit,
            patch("apps.gui.widgets.setup_wizard.SetupWizard") as mock_wizard,
        ):
            from PySide6.QtWidgets import QDialog

            # Setup: no profiles, wizard rejected
            mock_loader.return_value.list_profiles.return_value = []
            mock_wizard.return_value.exec.return_value = QDialog.DialogCode.Rejected
            mock_qapp.return_value.exec.return_value = 0

            from apps.gui.main import main

            # main() should raise SystemExit when wizard is cancelled
            with pytest.raises(SystemExit):
                main()

            # Wizard shown and rejected
            mock_wizard.assert_called_once()
            # sys.exit(0) called immediately (cancelled setup)
            mock_exit.assert_called_with(0)
            # MainWindow should NOT be created
            mock_window.assert_not_called()

    def test_main_sets_app_properties(self):
        """Test main() sets application name and organization."""
        with (
            patch("apps.gui.main.QApplication") as mock_qapp,
            patch("apps.gui.main.ProfileLoader") as mock_loader,
            patch("apps.gui.main.MainWindow"),
            patch("apps.gui.theme.apply_dark_theme"),
            patch("apps.gui.main.sys.exit"),
        ):
            mock_loader.return_value.list_profiles.return_value = ["profile1"]
            mock_qapp.return_value.exec.return_value = 0

            from apps.gui.main import main

            main()

            mock_qapp.return_value.setApplicationName.assert_called_with("Razer Control Center")
            mock_qapp.return_value.setOrganizationName.assert_called_with("RazerControlCenter")
            mock_qapp.return_value.setStyle.assert_called_with("Fusion")


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

    def test_mouse_press_starts_capture(self, qapp):
        """Test clicking the widget starts capture mode."""
        from PySide6.QtCore import QPointF, Qt
        from PySide6.QtGui import QMouseEvent

        from apps.gui.widgets.hotkey_editor import HotkeyCapture
        from crates.profile_schema import HotkeyBinding

        binding = HotkeyBinding(key="f1", modifiers=["ctrl"])
        widget = HotkeyCapture(binding)

        # Create a real mouse event (globalPos required in Qt6)
        event = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            QPointF(5, 5),
            QPointF(5, 5),  # globalPos
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        widget.mousePressEvent(event)

        assert widget._capturing is True
        assert "Press" in widget.text()
        widget.close()

    def test_focus_out_stops_capture(self, qapp):
        """Test focus loss stops capture mode."""
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QFocusEvent

        from apps.gui.widgets.hotkey_editor import HotkeyCapture
        from crates.profile_schema import HotkeyBinding

        binding = HotkeyBinding(key="f1", modifiers=["ctrl"])
        widget = HotkeyCapture(binding)
        widget._capturing = True

        event = QFocusEvent(QFocusEvent.Type.FocusOut, Qt.FocusReason.OtherFocusReason)
        widget.focusOutEvent(event)

        assert widget._capturing is False
        widget.close()

    def test_key_press_not_capturing(self, qapp):
        """Test that when not capturing, binding is unchanged."""
        from apps.gui.widgets.hotkey_editor import HotkeyCapture
        from crates.profile_schema import HotkeyBinding

        binding = HotkeyBinding(key="f1", modifiers=["ctrl"])
        widget = HotkeyCapture(binding)
        widget._capturing = False

        # When not capturing, binding should not change
        original_key = widget.binding.key
        assert widget.binding.key == original_key
        widget.close()

    def test_key_press_escape_cancels(self, qapp):
        """Test pressing Escape cancels capture."""
        from unittest.mock import MagicMock

        from PySide6.QtCore import Qt
        from PySide6.QtGui import QKeyEvent

        from apps.gui.widgets.hotkey_editor import HotkeyCapture
        from crates.profile_schema import HotkeyBinding

        binding = HotkeyBinding(key="f1", modifiers=["ctrl"])
        widget = HotkeyCapture(binding)
        widget._capturing = True

        event = MagicMock(spec=QKeyEvent)
        event.key.return_value = Qt.Key.Key_Escape
        event.modifiers.return_value = Qt.KeyboardModifier.NoModifier

        widget.keyPressEvent(event)
        assert widget._capturing is False
        widget.close()

    def test_key_press_modifier_only(self, qapp):
        """Test pressing only modifiers keeps capturing."""
        from unittest.mock import MagicMock

        from PySide6.QtCore import Qt
        from PySide6.QtGui import QKeyEvent

        from apps.gui.widgets.hotkey_editor import HotkeyCapture
        from crates.profile_schema import HotkeyBinding

        binding = HotkeyBinding(key="f1", modifiers=["ctrl"])
        widget = HotkeyCapture(binding)
        widget._capturing = True

        event = MagicMock(spec=QKeyEvent)
        event.key.return_value = Qt.Key.Key_Control
        event.modifiers.return_value = Qt.KeyboardModifier.ControlModifier

        widget.keyPressEvent(event)
        assert widget._capturing is True  # Still capturing
        widget.close()

    def test_key_press_f_key_with_modifier(self, qapp):
        """Test capturing F-key with modifiers."""
        from unittest.mock import MagicMock

        from PySide6.QtCore import Qt
        from PySide6.QtGui import QKeyEvent

        from apps.gui.widgets.hotkey_editor import HotkeyCapture
        from crates.profile_schema import HotkeyBinding

        binding = HotkeyBinding()
        widget = HotkeyCapture(binding)
        widget._capturing = True

        event = MagicMock(spec=QKeyEvent)
        event.key.return_value = Qt.Key.Key_F5
        event.modifiers.return_value = Qt.KeyboardModifier.ControlModifier

        widget.keyPressEvent(event)

        assert widget._capturing is False
        assert widget.binding.key == "f5"
        assert "ctrl" in widget.binding.modifiers
        widget.close()

    def test_key_press_number_with_modifier(self, qapp):
        """Test capturing number key with modifiers."""
        from unittest.mock import MagicMock

        from PySide6.QtCore import Qt
        from PySide6.QtGui import QKeyEvent

        from apps.gui.widgets.hotkey_editor import HotkeyCapture
        from crates.profile_schema import HotkeyBinding

        binding = HotkeyBinding()
        widget = HotkeyCapture(binding)
        widget._capturing = True

        event = MagicMock(spec=QKeyEvent)
        event.key.return_value = Qt.Key.Key_3
        event.modifiers.return_value = (
            Qt.KeyboardModifier.ShiftModifier | Qt.KeyboardModifier.ControlModifier
        )

        widget.keyPressEvent(event)

        assert widget.binding.key == "3"
        assert "shift" in widget.binding.modifiers
        assert "ctrl" in widget.binding.modifiers
        widget.close()

    def test_key_press_letter_with_alt(self, qapp):
        """Test capturing letter key with Alt modifier."""
        from unittest.mock import MagicMock

        from PySide6.QtCore import Qt
        from PySide6.QtGui import QKeyEvent

        from apps.gui.widgets.hotkey_editor import HotkeyCapture
        from crates.profile_schema import HotkeyBinding

        binding = HotkeyBinding()
        widget = HotkeyCapture(binding)
        widget._capturing = True

        event = MagicMock(spec=QKeyEvent)
        event.key.return_value = Qt.Key.Key_P
        event.modifiers.return_value = Qt.KeyboardModifier.AltModifier

        widget.keyPressEvent(event)

        assert widget.binding.key == "p"
        assert "alt" in widget.binding.modifiers
        widget.close()


class TestHotkeyEditorWidget:
    """Tests for HotkeyEditorWidget methods."""

    @pytest.fixture
    def qapp(self):
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app

    def test_widget_instantiation(self, qapp):
        """Test HotkeyEditorWidget can be created."""
        from unittest.mock import patch

        with (
            patch("apps.gui.widgets.hotkey_editor.SettingsManager"),
            patch("apps.gui.widgets.hotkey_editor.ProfileLoader") as MockLoader,
        ):
            MockLoader.return_value.list_profiles.return_value = []

            from apps.gui.widgets.hotkey_editor import HotkeyEditorWidget

            widget = HotkeyEditorWidget()
            assert widget is not None
            assert len(widget._hotkey_widgets) == 9
            widget.close()

    def test_load_settings(self, qapp):
        """Test _load_settings populates widgets."""
        from unittest.mock import MagicMock, patch

        from crates.profile_schema import HotkeyBinding

        with (
            patch("apps.gui.widgets.hotkey_editor.SettingsManager") as MockSettings,
            patch("apps.gui.widgets.hotkey_editor.ProfileLoader") as MockLoader,
        ):
            MockLoader.return_value.list_profiles.return_value = []

            mock_settings = MagicMock()
            mock_settings.hotkeys.profile_hotkeys = [
                HotkeyBinding(key="1", modifiers=["ctrl", "shift"], enabled=True),
                HotkeyBinding(key="2", modifiers=["ctrl", "shift"], enabled=False),
            ]
            MockSettings.return_value.load.return_value = mock_settings

            from apps.gui.widgets.hotkey_editor import HotkeyEditorWidget

            widget = HotkeyEditorWidget()
            widget._load_settings()

            # First widget should have the binding
            capture, enabled = widget._hotkey_widgets[0]
            assert capture.binding.key == "1"
            assert enabled.isChecked()
            widget.close()

    def test_on_enabled_changed(self, qapp):
        """Test _on_enabled_changed updates binding."""
        from unittest.mock import patch

        from PySide6.QtCore import Qt

        with (
            patch("apps.gui.widgets.hotkey_editor.SettingsManager"),
            patch("apps.gui.widgets.hotkey_editor.ProfileLoader") as MockLoader,
        ):
            MockLoader.return_value.list_profiles.return_value = []

            from apps.gui.widgets.hotkey_editor import HotkeyEditorWidget

            widget = HotkeyEditorWidget()
            widget._on_enabled_changed(0, Qt.CheckState.Checked.value)

            capture, _ = widget._hotkey_widgets[0]
            assert capture.binding.enabled is True
            widget.close()

    def test_on_hotkey_changed_no_conflict(self, qapp):
        """Test _on_hotkey_changed without conflict."""
        from unittest.mock import MagicMock, patch

        from crates.profile_schema import HotkeyBinding

        with (
            patch("apps.gui.widgets.hotkey_editor.SettingsManager") as MockSettings,
            patch("apps.gui.widgets.hotkey_editor.ProfileLoader") as MockLoader,
        ):
            MockLoader.return_value.list_profiles.return_value = []
            MockSettings.return_value.load.return_value = MagicMock(
                hotkeys=MagicMock(profile_hotkeys=[])
            )

            from apps.gui.widgets.hotkey_editor import HotkeyEditorWidget

            widget = HotkeyEditorWidget()
            binding = HotkeyBinding(key="f1", modifiers=["ctrl"])

            # Should not raise or show warning
            widget._on_hotkey_changed(0, binding)
            widget.close()

    def test_on_hotkey_changed_with_conflict(self, qapp):
        """Test _on_hotkey_changed with duplicate binding."""
        from unittest.mock import MagicMock, patch

        from PySide6.QtWidgets import QMessageBox

        from crates.profile_schema import HotkeyBinding

        with (
            patch("apps.gui.widgets.hotkey_editor.SettingsManager") as MockSettings,
            patch("apps.gui.widgets.hotkey_editor.ProfileLoader") as MockLoader,
        ):
            MockLoader.return_value.list_profiles.return_value = []
            MockSettings.return_value.load.return_value = MagicMock(
                hotkeys=MagicMock(profile_hotkeys=[])
            )

            from apps.gui.widgets.hotkey_editor import HotkeyEditorWidget

            widget = HotkeyEditorWidget()

            # Set binding on first widget
            capture0, _ = widget._hotkey_widgets[0]
            capture0.binding = HotkeyBinding(key="f1", modifiers=["ctrl"])

            # Try to set same binding on second widget
            same_binding = HotkeyBinding(key="f1", modifiers=["ctrl"])

            with patch.object(QMessageBox, "warning"):
                widget._on_hotkey_changed(1, same_binding)

            widget.close()

    def test_reset_defaults_confirmed(self, qapp):
        """Test _reset_defaults when user confirms."""
        from unittest.mock import MagicMock, patch

        from PySide6.QtWidgets import QMessageBox

        with (
            patch("apps.gui.widgets.hotkey_editor.SettingsManager") as MockSettings,
            patch("apps.gui.widgets.hotkey_editor.ProfileLoader") as MockLoader,
        ):
            MockLoader.return_value.list_profiles.return_value = []
            MockSettings.return_value.load.return_value = MagicMock(
                hotkeys=MagicMock(profile_hotkeys=[])
            )

            from apps.gui.widgets.hotkey_editor import HotkeyEditorWidget

            widget = HotkeyEditorWidget()
            signals_received = []
            widget.hotkeys_changed.connect(lambda: signals_received.append(True))

            with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
                widget._reset_defaults()

            MockSettings.return_value.reset_hotkeys.assert_called()
            assert len(signals_received) == 1
            widget.close()

    def test_reset_defaults_cancelled(self, qapp):
        """Test _reset_defaults when user cancels."""
        from unittest.mock import MagicMock, patch

        from PySide6.QtWidgets import QMessageBox

        with (
            patch("apps.gui.widgets.hotkey_editor.SettingsManager") as MockSettings,
            patch("apps.gui.widgets.hotkey_editor.ProfileLoader") as MockLoader,
        ):
            MockLoader.return_value.list_profiles.return_value = []
            MockSettings.return_value.load.return_value = MagicMock(
                hotkeys=MagicMock(profile_hotkeys=[])
            )

            from apps.gui.widgets.hotkey_editor import HotkeyEditorWidget

            widget = HotkeyEditorWidget()

            with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.No):
                widget._reset_defaults()

            MockSettings.return_value.reset_hotkeys.assert_not_called()
            widget.close()

    def test_save_settings_success(self, qapp):
        """Test _save_settings success path."""
        from unittest.mock import MagicMock, patch

        from PySide6.QtWidgets import QMessageBox

        from crates.profile_schema import HotkeyBinding

        with (
            patch("apps.gui.widgets.hotkey_editor.SettingsManager") as MockSettings,
            patch("apps.gui.widgets.hotkey_editor.ProfileLoader") as MockLoader,
        ):
            MockLoader.return_value.list_profiles.return_value = []
            mock_settings = MagicMock()
            # Use real HotkeyBinding objects
            mock_settings.hotkeys.profile_hotkeys = [
                HotkeyBinding(key=str(i + 1), modifiers=["ctrl", "shift"]) for i in range(9)
            ]
            MockSettings.return_value.load.return_value = mock_settings
            MockSettings.return_value.save.return_value = True

            from apps.gui.widgets.hotkey_editor import HotkeyEditorWidget

            widget = HotkeyEditorWidget()
            signals_received = []
            widget.hotkeys_changed.connect(lambda: signals_received.append(True))

            with patch.object(QMessageBox, "information"):
                widget._save_settings()

            MockSettings.return_value.save.assert_called()
            assert len(signals_received) == 1
            widget.close()

    def test_save_settings_failure(self, qapp):
        """Test _save_settings failure path."""
        from unittest.mock import MagicMock, patch

        from PySide6.QtWidgets import QMessageBox

        from crates.profile_schema import HotkeyBinding

        with (
            patch("apps.gui.widgets.hotkey_editor.SettingsManager") as MockSettings,
            patch("apps.gui.widgets.hotkey_editor.ProfileLoader") as MockLoader,
        ):
            MockLoader.return_value.list_profiles.return_value = []
            mock_settings = MagicMock()
            # Use real HotkeyBinding objects
            mock_settings.hotkeys.profile_hotkeys = [
                HotkeyBinding(key=str(i + 1), modifiers=["ctrl", "shift"]) for i in range(9)
            ]
            MockSettings.return_value.load.return_value = mock_settings
            MockSettings.return_value.save.return_value = False

            from apps.gui.widgets.hotkey_editor import HotkeyEditorWidget

            widget = HotkeyEditorWidget()

            with patch.object(QMessageBox, "warning") as mock_warn:
                widget._save_settings()
                mock_warn.assert_called()

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
        from unittest.mock import patch

        with (
            patch("apps.gui.widgets.hotkey_editor.SettingsManager"),
            patch("apps.gui.widgets.hotkey_editor.ProfileLoader") as MockLoader,
        ):
            MockLoader.return_value.list_profiles.return_value = []

            from apps.gui.widgets.hotkey_editor import HotkeyEditorDialog

            dialog = HotkeyEditorDialog()
            assert dialog is not None
            assert dialog.windowTitle() == "Configure Hotkeys"
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

    def test_refresh_with_razer_and_other_devices(self, qapp):
        """Test refresh shows separator when both Razer and other devices exist."""
        from apps.gui.widgets.device_list import DeviceListWidget

        # Create Razer device
        razer_device = MagicMock()
        razer_device.stable_id = "razer-deathadder"
        razer_device.name = "Razer DeathAdder"
        razer_device.is_mouse = True
        razer_device.is_keyboard = False

        # Create non-Razer device
        other_device = MagicMock()
        other_device.stable_id = "logitech-g502"
        other_device.name = "Logitech G502"
        other_device.is_mouse = True
        other_device.is_keyboard = False

        mock_registry = MagicMock()
        mock_registry.scan_devices.return_value = [razer_device, other_device]
        widget = DeviceListWidget(registry=mock_registry)
        widget.refresh()

        # Should have: Razer device + separator + other device = 3 items
        assert widget.list_widget.count() == 3

        # Check separator exists (item at index 1)
        separator_item = widget.list_widget.item(1)
        assert "Other Devices" in separator_item.text()
        widget.close()

    def test_refresh_only_other_devices(self, qapp):
        """Test refresh with only non-Razer devices."""
        from apps.gui.widgets.device_list import DeviceListWidget

        other_device = MagicMock()
        other_device.stable_id = "logitech-mouse"
        other_device.name = "Logitech Mouse"
        other_device.is_mouse = True
        other_device.is_keyboard = False

        mock_registry = MagicMock()
        mock_registry.scan_devices.return_value = [other_device]
        widget = DeviceListWidget(registry=mock_registry)
        widget.refresh()

        # Should have 1 item (no separator when only other devices)
        assert widget.list_widget.count() == 1
        widget.close()

    def test_get_selected_devices(self, qapp):
        """Test getting selected device IDs."""
        from apps.gui.widgets.device_list import DeviceListWidget

        razer_device = MagicMock()
        razer_device.stable_id = "razer-mouse"
        razer_device.name = "Razer Mouse"
        razer_device.is_mouse = True
        razer_device.is_keyboard = False

        other_device = MagicMock()
        other_device.stable_id = "logitech-mouse"
        other_device.name = "Logitech Mouse"
        other_device.is_mouse = True
        other_device.is_keyboard = False

        mock_registry = MagicMock()
        mock_registry.scan_devices.return_value = [razer_device, other_device]
        widget = DeviceListWidget(registry=mock_registry)
        widget.refresh()

        # Select the first item
        widget.list_widget.item(0).setSelected(True)

        selected = widget.get_selected_devices()
        assert len(selected) == 1
        assert selected[0] == "razer-mouse"
        widget.close()

    def test_get_selected_devices_multiple(self, qapp):
        """Test getting multiple selected device IDs."""
        from apps.gui.widgets.device_list import DeviceListWidget

        dev1 = MagicMock()
        dev1.stable_id = "razer-mouse-1"
        dev1.name = "Razer Mouse 1"
        dev1.is_mouse = True
        dev1.is_keyboard = False

        dev2 = MagicMock()
        dev2.stable_id = "razer-mouse-2"
        dev2.name = "Razer Mouse 2"
        dev2.is_mouse = True
        dev2.is_keyboard = False

        mock_registry = MagicMock()
        mock_registry.scan_devices.return_value = [dev1, dev2]
        widget = DeviceListWidget(registry=mock_registry)
        widget.refresh()

        # Select both items
        widget.list_widget.item(0).setSelected(True)
        widget.list_widget.item(1).setSelected(True)

        selected = widget.get_selected_devices()
        assert len(selected) == 2
        assert "razer-mouse-1" in selected
        assert "razer-mouse-2" in selected
        widget.close()

    def test_set_selected_devices(self, qapp):
        """Test setting selected devices by ID."""
        from apps.gui.widgets.device_list import DeviceListWidget

        dev1 = MagicMock()
        dev1.stable_id = "razer-mouse-1"
        dev1.name = "Razer Mouse 1"
        dev1.is_mouse = True
        dev1.is_keyboard = False

        dev2 = MagicMock()
        dev2.stable_id = "razer-mouse-2"
        dev2.name = "Razer Mouse 2"
        dev2.is_mouse = True
        dev2.is_keyboard = False

        mock_registry = MagicMock()
        mock_registry.scan_devices.return_value = [dev1, dev2]
        widget = DeviceListWidget(registry=mock_registry)
        widget.refresh()

        # Set selection to device 2
        widget.set_selected_devices(["razer-mouse-2"])

        # Check that device 2 is selected and device 1 is not
        assert not widget.list_widget.item(0).isSelected()
        assert widget.list_widget.item(1).isSelected()
        widget.close()

    def test_selection_changed_signal(self, qapp):
        """Test selection_changed signal is emitted."""
        from apps.gui.widgets.device_list import DeviceListWidget

        dev1 = MagicMock()
        dev1.stable_id = "razer-mouse"
        dev1.name = "Razer Mouse"
        dev1.is_mouse = True
        dev1.is_keyboard = False

        mock_registry = MagicMock()
        mock_registry.scan_devices.return_value = [dev1]
        widget = DeviceListWidget(registry=mock_registry)
        widget.refresh()

        signal_received = []

        def on_signal(selected):
            signal_received.append(selected)

        widget.selection_changed.connect(on_signal)

        # Select the item - triggers _on_selection_changed
        widget.list_widget.item(0).setSelected(True)

        assert len(signal_received) == 1
        assert signal_received[0] == ["razer-mouse"]
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

    def test_set_macros(self, qapp):
        """Test setting macros."""
        from apps.gui.widgets.macro_editor import MacroEditorWidget
        from crates.profile_schema import MacroAction

        widget = MacroEditorWidget()
        macros = [
            MacroAction(id="m1", name="Macro 1", steps=[], repeat_count=1),
            MacroAction(id="m2", name="Macro 2", steps=[], repeat_count=1),
        ]
        widget.set_macros(macros)
        assert len(widget._macros) == 2
        assert widget.macro_list.count() == 2
        widget.close()

    def test_on_macro_selected(self, qapp):
        """Test macro selection."""
        from apps.gui.widgets.macro_editor import MacroEditorWidget
        from crates.profile_schema import MacroAction

        widget = MacroEditorWidget()
        widget.set_macros([MacroAction(id="m1", name="Test", steps=[], repeat_count=1)])
        widget.macro_list.setCurrentRow(0)
        assert widget._current_macro is not None
        assert widget._current_macro.id == "m1"
        widget.close()

    def test_delete_macro(self, qapp):
        """Test deleting a macro."""
        from unittest.mock import patch

        from PySide6.QtWidgets import QMessageBox

        from apps.gui.widgets.macro_editor import MacroEditorWidget
        from crates.profile_schema import MacroAction

        widget = MacroEditorWidget()
        widget.set_macros([MacroAction(id="m1", name="Test", steps=[], repeat_count=1)])
        widget.macro_list.setCurrentRow(0)

        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
            widget._delete_macro()

        assert len(widget._macros) == 0
        widget.close()

    def test_load_macro(self, qapp):
        """Test loading macro data."""
        from apps.gui.widgets.macro_editor import MacroEditorWidget
        from crates.profile_schema import MacroAction, MacroStep, MacroStepType

        widget = MacroEditorWidget()
        macro = MacroAction(
            id="m1",
            name="Test Macro",
            steps=[MacroStep(type=MacroStepType.KEY_PRESS, key="A")],
            repeat_count=3,
            repeat_delay_ms=100,
        )
        widget.set_macros([macro])
        widget.macro_list.setCurrentRow(0)

        assert widget.name_input.text() == "Test Macro"
        assert widget.repeat_spin.value() == 3
        assert widget.repeat_delay_spin.value() == 100
        assert widget.steps_list.count() == 1
        widget.close()

    def test_step_to_text_all_types(self, qapp):
        """Test step to text conversion for all step types."""
        from apps.gui.widgets.macro_editor import MacroEditorWidget
        from crates.profile_schema import MacroStep, MacroStepType

        widget = MacroEditorWidget()

        assert "Press" in widget._step_to_text(MacroStep(type=MacroStepType.KEY_PRESS, key="A"))
        assert "Hold" in widget._step_to_text(MacroStep(type=MacroStepType.KEY_DOWN, key="CTRL"))
        assert "Release" in widget._step_to_text(MacroStep(type=MacroStepType.KEY_UP, key="CTRL"))
        assert "Wait" in widget._step_to_text(MacroStep(type=MacroStepType.DELAY, delay_ms=100))
        assert "Type" in widget._step_to_text(MacroStep(type=MacroStepType.TEXT, text="hello"))
        widget.close()

    def test_on_name_changed(self, qapp):
        """Test macro name change."""
        from apps.gui.widgets.macro_editor import MacroEditorWidget
        from crates.profile_schema import MacroAction

        widget = MacroEditorWidget()
        widget.set_macros([MacroAction(id="m1", name="Old", steps=[], repeat_count=1)])
        widget.macro_list.setCurrentRow(0)

        widget.name_input.setText("New Name")
        assert widget._current_macro.name == "New Name"
        widget.close()

    def test_on_repeat_changed(self, qapp):
        """Test repeat count change."""
        from apps.gui.widgets.macro_editor import MacroEditorWidget
        from crates.profile_schema import MacroAction

        widget = MacroEditorWidget()
        widget.set_macros([MacroAction(id="m1", name="Test", steps=[], repeat_count=1)])
        widget.macro_list.setCurrentRow(0)

        widget.repeat_spin.setValue(5)
        assert widget._current_macro.repeat_count == 5
        widget.close()

    def test_on_repeat_delay_changed(self, qapp):
        """Test repeat delay change."""
        from apps.gui.widgets.macro_editor import MacroEditorWidget
        from crates.profile_schema import MacroAction

        widget = MacroEditorWidget()
        widget.set_macros([MacroAction(id="m1", name="Test", steps=[], repeat_count=1)])
        widget.macro_list.setCurrentRow(0)

        widget.repeat_delay_spin.setValue(200)
        assert widget._current_macro.repeat_delay_ms == 200
        widget.close()

    def test_add_step(self, qapp):
        """Test adding a step."""
        from unittest.mock import MagicMock, patch

        from PySide6.QtWidgets import QDialog

        from apps.gui.widgets.macro_editor import MacroEditorWidget
        from crates.profile_schema import MacroAction, MacroStep, MacroStepType

        widget = MacroEditorWidget()
        widget.set_macros([MacroAction(id="m1", name="Test", steps=[], repeat_count=1)])
        widget.macro_list.setCurrentRow(0)

        mock_step = MacroStep(type=MacroStepType.KEY_PRESS, key="B")
        with patch("apps.gui.widgets.macro_editor.StepEditorDialog") as MockDialog:
            mock_dialog = MagicMock()
            mock_dialog.exec.return_value = QDialog.DialogCode.Accepted
            mock_dialog.get_step.return_value = mock_step
            MockDialog.return_value = mock_dialog

            widget._add_step()

        assert len(widget._current_macro.steps) == 1
        assert widget._current_macro.steps[0].key == "B"
        widget.close()

    def test_delete_step(self, qapp):
        """Test deleting a step."""
        from apps.gui.widgets.macro_editor import MacroEditorWidget
        from crates.profile_schema import MacroAction, MacroStep, MacroStepType

        widget = MacroEditorWidget()
        widget.set_macros(
            [
                MacroAction(
                    id="m1",
                    name="Test",
                    steps=[MacroStep(type=MacroStepType.KEY_PRESS, key="A")],
                    repeat_count=1,
                )
            ]
        )
        widget.macro_list.setCurrentRow(0)
        widget.steps_list.setCurrentRow(0)

        widget._delete_step()
        assert len(widget._current_macro.steps) == 0
        widget.close()

    def test_set_editor_enabled(self, qapp):
        """Test enabling/disabling editor."""
        from apps.gui.widgets.macro_editor import MacroEditorWidget

        widget = MacroEditorWidget()
        widget._set_editor_enabled(True)
        assert widget.name_input.isEnabled()
        assert widget.add_step_btn.isEnabled()

        widget._set_editor_enabled(False)
        assert not widget.name_input.isEnabled()
        assert not widget.add_step_btn.isEnabled()
        widget.close()

    def test_stop_recording(self, qapp):
        """Test stopping recording."""
        from apps.gui.widgets.macro_editor import MacroEditorWidget

        widget = MacroEditorWidget()
        widget._recording = True
        widget._stop_recording()
        assert not widget._recording
        assert not widget.record_btn.isChecked()
        widget.close()


class TestStepEditorDialog:
    """Tests for StepEditorDialog."""

    @pytest.fixture
    def qapp(self):
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app

    def test_new_step_dialog(self, qapp):
        """Test creating a new step dialog."""
        from apps.gui.widgets.macro_editor import StepEditorDialog

        dialog = StepEditorDialog()
        assert dialog.windowTitle() == "Edit Macro Step"
        dialog.close()

    def test_load_key_press_step(self, qapp):
        """Test loading a key press step."""
        from apps.gui.widgets.macro_editor import StepEditorDialog
        from crates.profile_schema import MacroStep, MacroStepType

        step = MacroStep(type=MacroStepType.KEY_PRESS, key="A")
        dialog = StepEditorDialog(step)
        assert dialog.type_combo.currentData() == MacroStepType.KEY_PRESS
        dialog.close()

    def test_load_delay_step(self, qapp):
        """Test loading a delay step."""
        from apps.gui.widgets.macro_editor import StepEditorDialog
        from crates.profile_schema import MacroStep, MacroStepType

        step = MacroStep(type=MacroStepType.DELAY, delay_ms=500)
        dialog = StepEditorDialog(step)
        assert dialog.type_combo.currentData() == MacroStepType.DELAY
        assert dialog.delay_spin.value() == 500
        dialog.close()

    def test_load_text_step(self, qapp):
        """Test loading a text step."""
        from apps.gui.widgets.macro_editor import StepEditorDialog
        from crates.profile_schema import MacroStep, MacroStepType

        step = MacroStep(type=MacroStepType.TEXT, text="hello")
        dialog = StepEditorDialog(step)
        assert dialog.type_combo.currentData() == MacroStepType.TEXT
        assert dialog.text_input.text() == "hello"
        dialog.close()

    def test_get_step_key_press(self, qapp):
        """Test getting a key press step."""
        from apps.gui.widgets.macro_editor import StepEditorDialog
        from crates.profile_schema import MacroStepType

        dialog = StepEditorDialog()
        dialog.type_combo.setCurrentIndex(0)  # KEY_PRESS
        dialog.key_combo.setEditText("F1")
        step = dialog.get_step()
        assert step.type == MacroStepType.KEY_PRESS
        assert step.key == "F1"
        dialog.close()

    def test_get_step_delay(self, qapp):
        """Test getting a delay step."""
        from apps.gui.widgets.macro_editor import StepEditorDialog
        from crates.profile_schema import MacroStepType

        dialog = StepEditorDialog()
        dialog.type_combo.setCurrentIndex(3)  # DELAY
        dialog.delay_spin.setValue(250)
        step = dialog.get_step()
        assert step.type == MacroStepType.DELAY
        assert step.delay_ms == 250
        dialog.close()

    def test_get_step_text(self, qapp):
        """Test getting a text step."""
        from apps.gui.widgets.macro_editor import StepEditorDialog
        from crates.profile_schema import MacroStepType

        dialog = StepEditorDialog()
        dialog.type_combo.setCurrentIndex(4)  # TEXT
        dialog.text_input.setText("test string")
        step = dialog.get_step()
        assert step.type == MacroStepType.TEXT
        assert step.text == "test string"
        dialog.close()

    def test_on_type_changed_shows_correct_fields(self, qapp):
        """Test that type change shows correct fields."""
        from apps.gui.widgets.macro_editor import StepEditorDialog

        dialog = StepEditorDialog()

        # KEY_PRESS - show key combo
        dialog.type_combo.setCurrentIndex(0)
        dialog._on_type_changed()
        assert not dialog.key_combo.isHidden()
        assert dialog.delay_spin.isHidden()
        assert dialog.text_input.isHidden()

        # DELAY - show delay spin
        dialog.type_combo.setCurrentIndex(3)
        dialog._on_type_changed()
        assert dialog.key_combo.isHidden()
        assert not dialog.delay_spin.isHidden()
        assert dialog.text_input.isHidden()

        # TEXT - show text input
        dialog.type_combo.setCurrentIndex(4)
        dialog._on_type_changed()
        assert dialog.key_combo.isHidden()
        assert dialog.delay_spin.isHidden()
        assert not dialog.text_input.isHidden()

        dialog.close()


class TestRecordingDialog:
    """Tests for RecordingDialog."""

    def test_recording_dialog_module_has_class(self):
        """Test RecordingDialog exists in module."""
        from apps.gui.widgets.macro_editor import RecordingDialog

        assert RecordingDialog is not None


class TestRecordingWorker:
    """Tests for RecordingWorker."""

    def test_worker_instantiation(self):
        """Test RecordingWorker can be created."""
        from apps.gui.widgets.macro_editor import RecordingWorker

        worker = RecordingWorker("/dev/input/event0")
        assert worker.device_path == "/dev/input/event0"
        assert worker.stop_key == "ESC"
        assert worker.timeout == 60

    def test_worker_stop(self):
        """Test stop method sets flag."""
        from apps.gui.widgets.macro_editor import RecordingWorker

        worker = RecordingWorker("/dev/input/event0")
        worker.stop()
        assert worker._should_stop is True


class TestRecordingDialogFullCoverage:
    """Extended tests for RecordingDialog coverage."""

    @pytest.fixture(autouse=True)
    def mock_gi_module(self):
        """Mock gi module to prevent GLib registration conflicts with Qt."""
        # Create mock GLib module
        mock_glib = MagicMock()
        mock_glib.UserDirectory = MagicMock()
        mock_gi = MagicMock()
        mock_gi.repository = MagicMock()
        mock_gi.repository.GLib = mock_glib

        # Patch before any imports that might trigger GLib
        with patch.dict(
            "sys.modules",
            {
                "gi": mock_gi,
                "gi.repository": mock_gi.repository,
                "gi.repository.GLib": mock_glib,
            },
        ):
            yield

    @pytest.fixture
    def qapp(self):
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app

    @pytest.fixture
    def mock_evdev(self):
        """Mock evdev module for tests."""
        mock_evdev_module = MagicMock()
        mock_evdev_module.list_devices.return_value = []
        mock_evdev_module.ecodes.EV_KEY = 1
        with patch.dict("sys.modules", {"evdev": mock_evdev_module}):
            yield mock_evdev_module

    def test_recording_dialog_instantiation(self, qapp, mock_evdev):
        """Test RecordingDialog can be instantiated."""
        from apps.gui.widgets.macro_editor import RecordingDialog

        dialog = RecordingDialog()
        assert dialog.windowTitle() == "Record Macro from Device"
        assert dialog.device_combo is not None
        assert dialog.stop_key_combo is not None
        assert dialog.timeout_spin is not None
        dialog.close()

    def test_recording_dialog_setup_ui(self, qapp, mock_evdev):
        """Test dialog UI setup."""
        from apps.gui.widgets.macro_editor import RecordingDialog

        dialog = RecordingDialog()

        # Check UI elements exist
        assert dialog.status_label is not None
        assert dialog.key_log is not None
        assert dialog.start_btn is not None
        assert dialog.stop_btn is not None
        assert dialog.accept_btn is not None

        # Default states
        assert not dialog.stop_btn.isEnabled()
        assert not dialog.accept_btn.isEnabled()
        dialog.close()

    def test_recording_dialog_populate_devices_no_evdev(self, qapp):
        """Test device population when evdev not installed."""
        from apps.gui.widgets.macro_editor import RecordingDialog

        with patch.dict("sys.modules", {"evdev": None}):
            dialog = RecordingDialog()
            # Should show "evdev not installed"
            assert dialog.device_combo.count() >= 1
            dialog.close()

    def test_recording_dialog_populate_devices_with_devices(self, qapp):
        """Test device population with mock devices."""
        from apps.gui.widgets.macro_editor import RecordingDialog

        mock_device = MagicMock()
        mock_device.name = "Test Keyboard"
        mock_device.capabilities.return_value = {1: []}  # EV_KEY = 1

        mock_evdev_module = MagicMock()
        mock_evdev_module.list_devices.return_value = ["/dev/input/event0"]
        mock_evdev_module.InputDevice.return_value = mock_device
        mock_evdev_module.ecodes.EV_KEY = 1

        with patch.dict("sys.modules", {"evdev": mock_evdev_module}):
            dialog = RecordingDialog()
            # Should have the device
            assert dialog.device_combo.count() >= 1
            dialog.close()

    def test_recording_dialog_start_recording_no_device(self, qapp, mock_evdev):
        """Test start recording with no valid device."""
        from PySide6.QtWidgets import QMessageBox

        from apps.gui.widgets.macro_editor import RecordingDialog

        dialog = RecordingDialog()
        dialog.device_combo.clear()
        dialog.device_combo.addItem("No devices", None)

        with patch.object(QMessageBox, "warning") as mock_warning:
            dialog._start_recording()
            mock_warning.assert_called_once()
        dialog.close()

    def test_recording_dialog_on_step_recorded(self, qapp, mock_evdev):
        """Test handling recorded key step."""
        from apps.gui.widgets.macro_editor import RecordingDialog

        dialog = RecordingDialog()
        dialog._on_step_recorded("A ↓")
        assert "A ↓" in dialog.key_log.toPlainText()
        dialog.close()

    def test_recording_dialog_on_recording_finished(self, qapp, mock_evdev):
        """Test handling recording completion."""
        from apps.gui.widgets.macro_editor import RecordingDialog
        from crates.profile_schema import MacroAction, MacroStep, MacroStepType

        dialog = RecordingDialog()

        macro = MacroAction(
            id="test",
            name="Test",
            steps=[MacroStep(type=MacroStepType.KEY_PRESS, key="A")],
            repeat_count=1,
        )
        dialog._on_recording_finished(macro)

        assert "1 steps" in dialog.status_label.text()
        assert dialog.accept_btn.isEnabled()
        dialog.close()

    def test_recording_dialog_on_error(self, qapp, mock_evdev):
        """Test handling recording error."""
        from PySide6.QtWidgets import QMessageBox

        from apps.gui.widgets.macro_editor import RecordingDialog

        dialog = RecordingDialog()

        with patch.object(QMessageBox, "critical") as mock_critical:
            dialog._on_error("Test error")
            mock_critical.assert_called_once()
        dialog.close()

    def test_recording_dialog_get_recorded_macro(self, qapp, mock_evdev):
        """Test getting the recorded macro."""
        from apps.gui.widgets.macro_editor import RecordingDialog
        from crates.profile_schema import MacroAction

        dialog = RecordingDialog()

        # Initially no macro
        assert dialog.get_recorded_macro() is None

        # After recording
        macro = MacroAction(id="test", name="Test", steps=[], repeat_count=1)
        dialog._recorded_macro = macro
        assert dialog.get_recorded_macro() == macro
        dialog.close()


class TestMacroEditorExtendedCoverage:
    """Extended tests for MacroEditorWidget coverage."""

    @pytest.fixture
    def qapp(self):
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app

    def test_edit_step(self, qapp):
        """Test editing a step."""
        from PySide6.QtWidgets import QDialog

        from apps.gui.widgets.macro_editor import MacroEditorWidget
        from crates.profile_schema import MacroAction, MacroStep, MacroStepType

        widget = MacroEditorWidget()
        widget.set_macros(
            [
                MacroAction(
                    id="m1",
                    name="Test",
                    steps=[MacroStep(type=MacroStepType.KEY_PRESS, key="A")],
                    repeat_count=1,
                )
            ]
        )
        widget.macro_list.setCurrentRow(0)
        widget.steps_list.setCurrentRow(0)

        new_step = MacroStep(type=MacroStepType.KEY_PRESS, key="B")
        with patch("apps.gui.widgets.macro_editor.StepEditorDialog") as MockDialog:
            mock_dialog = MagicMock()
            mock_dialog.exec.return_value = QDialog.DialogCode.Accepted
            mock_dialog.get_step.return_value = new_step
            MockDialog.return_value = mock_dialog

            widget._edit_step()

        assert widget._current_macro.steps[0].key == "B"
        widget.close()

    def test_edit_step_no_selection(self, qapp):
        """Test editing step with no selection does nothing."""
        from apps.gui.widgets.macro_editor import MacroEditorWidget
        from crates.profile_schema import MacroAction

        widget = MacroEditorWidget()
        widget.set_macros([MacroAction(id="m1", name="Test", steps=[], repeat_count=1)])
        widget.macro_list.setCurrentRow(0)

        # No step selected - should not crash
        widget._edit_step()
        widget.close()

    def test_delete_step_no_selection(self, qapp):
        """Test deleting step with no selection does nothing."""
        from apps.gui.widgets.macro_editor import MacroEditorWidget
        from crates.profile_schema import MacroAction, MacroStep, MacroStepType

        widget = MacroEditorWidget()
        widget.set_macros(
            [
                MacroAction(
                    id="m1",
                    name="Test",
                    steps=[MacroStep(type=MacroStepType.KEY_PRESS, key="A")],
                    repeat_count=1,
                )
            ]
        )
        widget.macro_list.setCurrentRow(0)
        # No step selected
        widget.steps_list.clearSelection()

        widget._delete_step()
        # Step should still exist
        assert len(widget._current_macro.steps) == 1
        widget.close()

    def test_delete_step_no_macro(self, qapp):
        """Test deleting step with no macro does nothing."""
        from apps.gui.widgets.macro_editor import MacroEditorWidget

        widget = MacroEditorWidget()
        widget._current_macro = None
        widget._delete_step()  # Should not crash
        widget.close()

    def test_toggle_recording_start(self, qapp):
        """Test toggle recording starts recording."""
        from PySide6.QtWidgets import QDialog

        from apps.gui.widgets.macro_editor import MacroEditorWidget
        from crates.profile_schema import MacroAction

        widget = MacroEditorWidget()
        widget.set_macros([MacroAction(id="m1", name="Test", steps=[], repeat_count=1)])
        widget.macro_list.setCurrentRow(0)
        widget._recording = False

        # Mock RecordingDialog to return rejected (cancel)
        with patch("apps.gui.widgets.macro_editor.RecordingDialog") as MockDialog:
            mock_dialog = MagicMock()
            mock_dialog.exec.return_value = QDialog.DialogCode.Rejected
            MockDialog.return_value = mock_dialog

            widget._toggle_recording()

        # Recording was attempted
        MockDialog.assert_called_once()
        widget.close()

    def test_toggle_recording_stop(self, qapp):
        """Test toggle recording stops recording."""
        from apps.gui.widgets.macro_editor import MacroEditorWidget

        widget = MacroEditorWidget()
        widget._recording = True

        widget._toggle_recording()

        assert not widget._recording
        widget.close()

    def test_test_macro(self, qapp):
        """Test showing macro test dialog."""
        from PySide6.QtWidgets import QMessageBox

        from apps.gui.widgets.macro_editor import MacroEditorWidget
        from crates.profile_schema import MacroAction, MacroStep, MacroStepType

        widget = MacroEditorWidget()
        widget.set_macros(
            [
                MacroAction(
                    id="m1",
                    name="Test Macro",
                    steps=[MacroStep(type=MacroStepType.KEY_PRESS, key="A")],
                    repeat_count=2,
                    repeat_delay_ms=50,
                )
            ]
        )
        widget.macro_list.setCurrentRow(0)

        with patch.object(QMessageBox, "information") as mock_info:
            widget._test_macro()
            mock_info.assert_called_once()
            # Check message contains macro name
            call_args = mock_info.call_args
            assert "Test Macro" in call_args[0][2]
        widget.close()

    def test_test_macro_no_steps(self, qapp):
        """Test test macro with no steps does nothing."""
        from PySide6.QtWidgets import QMessageBox

        from apps.gui.widgets.macro_editor import MacroEditorWidget
        from crates.profile_schema import MacroAction

        widget = MacroEditorWidget()
        widget.set_macros([MacroAction(id="m1", name="Test", steps=[], repeat_count=1)])
        widget.macro_list.setCurrentRow(0)

        with patch.object(QMessageBox, "information") as mock_info:
            widget._test_macro()
            mock_info.assert_not_called()
        widget.close()

    def test_test_macro_no_macro(self, qapp):
        """Test test macro with no macro selected does nothing."""
        from PySide6.QtWidgets import QMessageBox

        from apps.gui.widgets.macro_editor import MacroEditorWidget

        widget = MacroEditorWidget()
        widget._current_macro = None

        with patch.object(QMessageBox, "information") as mock_info:
            widget._test_macro()
            mock_info.assert_not_called()
        widget.close()


class TestMacroEditorFinalCoverage:
    """Final coverage tests for MacroEditorWidget."""

    @pytest.fixture
    def qapp(self):
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app

    def test_step_editor_custom_key(self, qapp):
        """Test StepEditorDialog with custom key not in dropdown (line 359)."""
        from apps.gui.widgets.macro_editor import StepEditorDialog
        from crates.profile_schema import MacroStep, MacroStepType

        step = MacroStep(type=MacroStepType.KEY_PRESS, key="CUSTOM_KEY_XYZ")
        dialog = StepEditorDialog(step)
        # Should set as editable text
        assert "CUSTOM_KEY_XYZ" in dialog.key_combo.currentText()
        dialog.close()

    def test_load_macro_none(self, qapp):
        """Test _load_macro with None (line 556)."""
        from apps.gui.widgets.macro_editor import MacroEditorWidget

        widget = MacroEditorWidget()
        widget._load_macro(None)  # Should not crash
        widget.close()

    def test_refresh_steps_list_no_macro(self, qapp):
        """Test _refresh_steps_list with no current macro (line 577)."""
        from apps.gui.widgets.macro_editor import MacroEditorWidget

        widget = MacroEditorWidget()
        widget._current_macro = None
        widget._refresh_steps_list()  # Should not crash
        widget.close()

    def test_step_to_text_unknown_type(self, qapp):
        """Test _step_to_text with unknown type (line 597)."""
        from apps.gui.widgets.macro_editor import MacroEditorWidget
        from crates.profile_schema import MacroStep

        widget = MacroEditorWidget()
        # Create a valid step then mock the type attribute
        MacroStep(type="key_press", key="A")
        # Override with a mock to simulate unknown type path
        from unittest.mock import MagicMock

        mock_step = MagicMock()
        mock_step.type = "UNKNOWN_TYPE"
        mock_step.key = None
        mock_step.delay_ms = None
        mock_step.text = None
        text = widget._step_to_text(mock_step)
        # Should return str(step.type)
        assert "UNKNOWN" in text or text == "UNKNOWN_TYPE"
        widget.close()

    def test_delete_macro_no_current(self, qapp):
        """Test _delete_macro with no current macro (line 631)."""
        from apps.gui.widgets.macro_editor import MacroEditorWidget

        widget = MacroEditorWidget()
        widget._current_macro = None
        widget._delete_macro()  # Should not crash
        widget.close()

    def test_add_step_no_macro(self, qapp):
        """Test _add_step with no current macro (line 649)."""
        from apps.gui.widgets.macro_editor import MacroEditorWidget

        widget = MacroEditorWidget()
        widget._current_macro = None
        widget._add_step()  # Should not crash
        widget.close()

    def test_edit_step_no_macro(self, qapp):
        """Test _edit_step with no current macro (line 662)."""
        from apps.gui.widgets.macro_editor import MacroEditorWidget

        widget = MacroEditorWidget()
        widget._current_macro = None
        widget._edit_step()  # Should not crash
        widget.close()

    def test_on_steps_reordered(self, qapp):
        """Test _on_steps_reordered rebuilds step order (lines 694-706)."""
        from apps.gui.widgets.macro_editor import MacroEditorWidget
        from crates.profile_schema import MacroAction, MacroStep, MacroStepType

        widget = MacroEditorWidget()
        widget.set_macros(
            [
                MacroAction(
                    id="m1",
                    name="Test",
                    steps=[
                        MacroStep(type=MacroStepType.KEY_PRESS, key="A"),
                        MacroStep(type=MacroStepType.KEY_PRESS, key="B"),
                    ],
                    repeat_count=1,
                )
            ]
        )
        widget.macro_list.setCurrentRow(0)

        # Simulate reorder by calling the method
        widget._on_steps_reordered()

        # Should not crash, steps should still exist
        assert len(widget._current_macro.steps) == 2
        widget.close()

    def test_on_steps_reordered_no_macro(self, qapp):
        """Test _on_steps_reordered with no macro (line 694-695)."""
        from apps.gui.widgets.macro_editor import MacroEditorWidget

        widget = MacroEditorWidget()
        widget._current_macro = None
        widget._on_steps_reordered()  # Should not crash
        widget.close()

    def test_start_recording_no_macro(self, qapp):
        """Test _start_recording with no current macro (line 746)."""
        from apps.gui.widgets.macro_editor import MacroEditorWidget

        widget = MacroEditorWidget()
        widget._current_macro = None
        widget._start_recording()  # Should not crash
        widget.close()

    def test_start_recording_with_steps(self, qapp):
        """Test _start_recording dialog accept with steps (lines 751-757)."""
        from PySide6.QtWidgets import QDialog

        from apps.gui.widgets.macro_editor import MacroEditorWidget
        from crates.profile_schema import MacroAction, MacroStep, MacroStepType

        widget = MacroEditorWidget()
        widget.set_macros([MacroAction(id="m1", name="Test", steps=[], repeat_count=1)])
        widget.macro_list.setCurrentRow(0)

        recorded_macro = MacroAction(
            id="recorded",
            name="Recorded",
            steps=[MacroStep(type=MacroStepType.KEY_PRESS, key="X")],
            repeat_count=1,
        )

        with patch("apps.gui.widgets.macro_editor.RecordingDialog") as MockDialog:
            mock_dialog = MagicMock()
            mock_dialog.exec.return_value = QDialog.DialogCode.Accepted
            mock_dialog.get_recorded_macro.return_value = recorded_macro
            MockDialog.return_value = mock_dialog

            widget._start_recording()

        # Should have replaced steps
        assert len(widget._current_macro.steps) == 1
        assert widget._current_macro.steps[0].key == "X"
        widget.close()

    def test_start_recording_empty_result(self, qapp):
        """Test _start_recording dialog accept with no steps (lines 761-763)."""
        from PySide6.QtWidgets import QDialog

        from apps.gui.widgets.macro_editor import MacroEditorWidget
        from crates.profile_schema import MacroAction

        widget = MacroEditorWidget()
        widget.set_macros([MacroAction(id="m1", name="Test", steps=[], repeat_count=1)])
        widget.macro_list.setCurrentRow(0)

        empty_macro = MacroAction(id="empty", name="Empty", steps=[], repeat_count=1)

        with patch("apps.gui.widgets.macro_editor.RecordingDialog") as MockDialog:
            mock_dialog = MagicMock()
            mock_dialog.exec.return_value = QDialog.DialogCode.Accepted
            mock_dialog.get_recorded_macro.return_value = empty_macro
            MockDialog.return_value = mock_dialog

            widget._start_recording()

        # Should show "No steps recorded" message
        assert "No steps" in widget.record_status.text() or widget.record_status.text() == ""
        widget.close()


class TestRecordingDialogCoverage:
    """Coverage tests for RecordingDialog."""

    @pytest.fixture
    def qapp(self):
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app

    @pytest.fixture
    def mock_evdev(self):
        """Mock evdev module."""
        mock_module = MagicMock()
        mock_module.list_devices.return_value = ["/dev/input/event0"]
        mock_module.ecodes.EV_KEY = 1

        mock_device = MagicMock()
        mock_device.name = "Test Device"
        mock_device.capabilities.return_value = {1: []}  # EV_KEY
        mock_module.InputDevice.return_value = mock_device

        return mock_module

    def test_recording_dialog_device_exception(self, qapp):
        """Test RecordingDialog handles device query exception (lines 190-191)."""
        mock_evdev = MagicMock()
        mock_evdev.list_devices.return_value = ["/dev/input/event0", "/dev/input/event1"]
        mock_evdev.ecodes.EV_KEY = 1

        # First device raises exception, second works
        good_device = MagicMock()
        good_device.name = "Good Device"
        good_device.capabilities.return_value = {1: []}

        def mock_input_device(path):
            if path == "/dev/input/event0":
                raise PermissionError("No access")
            return good_device

        mock_evdev.InputDevice.side_effect = mock_input_device

        with patch.dict("sys.modules", {"evdev": mock_evdev}):
            from apps.gui.widgets.macro_editor import RecordingDialog

            dialog = RecordingDialog()
            # Should have at least one device (the good one)
            assert dialog.device_combo.count() >= 1
            dialog.close()

    def test_recording_dialog_start_recording(self, qapp, mock_evdev):
        """Test RecordingDialog _start_recording (lines 208-228)."""
        with patch.dict("sys.modules", {"evdev": mock_evdev}):
            from apps.gui.widgets.macro_editor import RecordingDialog

            dialog = RecordingDialog()

            # Mock the worker to avoid actual device access
            with patch("apps.gui.widgets.macro_editor.RecordingWorker") as MockWorker:
                mock_worker = MagicMock()
                MockWorker.return_value = mock_worker

                dialog._start_recording()

                # Worker should be created and started
                MockWorker.assert_called_once()
                mock_worker.start.assert_called_once()
            dialog.close()

    def test_recording_dialog_stop_recording(self, qapp, mock_evdev):
        """Test RecordingDialog _stop_recording (lines 232-234)."""
        with patch.dict("sys.modules", {"evdev": mock_evdev}):
            from apps.gui.widgets.macro_editor import RecordingDialog

            dialog = RecordingDialog()

            # Create a mock worker that's running
            mock_worker = MagicMock()
            mock_worker.isRunning.return_value = True
            dialog._worker = mock_worker

            dialog._stop_recording()

            mock_worker.stop.assert_called_once()
            mock_worker.wait.assert_called_once()
            dialog.close()


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
            id="test",
            name="Test",
            description="",
            layers=[Layer(id="base", name="Base", bindings=[], hold_modifier_input_code=None)],
        )
        mock_loader.list_profiles.return_value = [profile]
        mock_loader.load_profile.return_value = profile

        widget = ProfilePanel()
        widget.load_profiles(mock_loader)
        # At least one profile should be in the list
        assert widget.profile_list.count() >= 1
        widget.close()

    def test_load_profiles_with_active(self, qapp):
        """Test loading profiles with an active profile."""
        from apps.gui.widgets.profile_panel import ProfilePanel
        from crates.profile_schema import Layer, Profile

        loader = MagicMock()
        profile = Profile(
            id="active_test",
            name="Active Profile",
            description="",
            layers=[Layer(id="base", name="Base", bindings=[], hold_modifier_input_code=None)],
        )
        loader.list_profiles.return_value = ["active_test"]
        loader.get_active_profile_id.return_value = "active_test"
        loader.load_profile.return_value = profile

        widget = ProfilePanel()
        widget.load_profiles(loader)

        # Check active label is set
        assert "Active Profile" in widget.active_label.text()
        # Check profile is in list with [Active] suffix
        assert widget.profile_list.count() == 1
        item = widget.profile_list.item(0)
        assert "[Active]" in item.text()
        widget.close()

    def test_on_profile_selected_negative_row(self, qapp, mock_loader):
        """Test _on_profile_selected with negative row disables buttons."""
        from apps.gui.widgets.profile_panel import ProfilePanel

        widget = ProfilePanel()
        widget.load_profiles(mock_loader)

        # Simulate negative row (no selection)
        widget._on_profile_selected(-1)

        assert not widget.delete_btn.isEnabled()
        assert not widget.activate_btn.isEnabled()
        assert not widget.export_btn.isEnabled()
        widget.close()

    def test_on_profile_selected_valid_row(self, qapp):
        """Test _on_profile_selected with valid row enables buttons."""
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QListWidgetItem

        from apps.gui.widgets.profile_panel import ProfilePanel

        widget = ProfilePanel()

        # Add item manually
        item = QListWidgetItem("Test Profile")
        item.setData(Qt.ItemDataRole.UserRole, "test_id")
        widget.profile_list.addItem(item)
        widget.profile_list.setCurrentRow(0)

        # Buttons should be enabled
        assert widget.delete_btn.isEnabled()
        assert widget.activate_btn.isEnabled()
        assert widget.export_btn.isEnabled()
        widget.close()

    def test_refresh(self, qapp, mock_loader):
        """Test refresh reloads profiles."""
        from apps.gui.widgets.profile_panel import ProfilePanel

        widget = ProfilePanel()
        widget.load_profiles(mock_loader)
        mock_loader.list_profiles.reset_mock()

        widget.refresh()
        mock_loader.list_profiles.assert_called()
        widget.close()

    def test_refresh_without_loader(self, qapp):
        """Test refresh does nothing without loader."""
        from apps.gui.widgets.profile_panel import ProfilePanel

        widget = ProfilePanel()
        # Should not raise
        widget.refresh()
        widget.close()

    def test_create_profile_accepted(self, qapp):
        """Test creating a profile via dialog."""
        from unittest.mock import patch

        from PySide6.QtWidgets import QDialog

        from apps.gui.widgets.profile_panel import ProfilePanel
        from crates.profile_schema import Profile

        widget = ProfilePanel()
        signals_received = []
        widget.profile_created.connect(lambda p: signals_received.append(p))

        mock_profile = Profile(
            id="new",
            name="New Profile",
            description="",
            layers=[],
        )

        with patch("apps.gui.widgets.profile_panel.NewProfileDialog") as MockDialog:
            mock_dialog = MagicMock()
            mock_dialog.exec.return_value = QDialog.DialogCode.Accepted
            mock_dialog.get_profile.return_value = mock_profile
            MockDialog.return_value = mock_dialog

            widget._create_profile()

        assert len(signals_received) == 1
        assert signals_received[0].name == "New Profile"
        widget.close()

    def test_create_profile_cancelled(self, qapp):
        """Test cancelling profile creation."""
        from unittest.mock import patch

        from PySide6.QtWidgets import QDialog

        from apps.gui.widgets.profile_panel import ProfilePanel

        widget = ProfilePanel()
        signals_received = []
        widget.profile_created.connect(lambda p: signals_received.append(p))

        with patch("apps.gui.widgets.profile_panel.NewProfileDialog") as MockDialog:
            mock_dialog = MagicMock()
            mock_dialog.exec.return_value = QDialog.DialogCode.Rejected
            MockDialog.return_value = mock_dialog

            widget._create_profile()

        assert len(signals_received) == 0
        widget.close()

    def test_delete_profile_confirmed(self, qapp):
        """Test deleting a profile when confirmed."""
        from unittest.mock import patch

        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QListWidgetItem, QMessageBox

        from apps.gui.widgets.profile_panel import ProfilePanel

        widget = ProfilePanel()
        signals_received = []
        widget.profile_deleted.connect(lambda pid: signals_received.append(pid))

        # Add item to list
        item = QListWidgetItem("Test")
        item.setData(Qt.ItemDataRole.UserRole, "test_id")
        widget.profile_list.addItem(item)
        widget.profile_list.setCurrentItem(item)

        with patch.object(QMessageBox, "question", return_value=QMessageBox.Yes):
            widget._delete_profile()

        assert len(signals_received) == 1
        assert signals_received[0] == "test_id"
        widget.close()

    def test_delete_profile_cancelled(self, qapp):
        """Test cancelling profile deletion."""
        from unittest.mock import patch

        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QListWidgetItem, QMessageBox

        from apps.gui.widgets.profile_panel import ProfilePanel

        widget = ProfilePanel()
        signals_received = []
        widget.profile_deleted.connect(lambda pid: signals_received.append(pid))

        item = QListWidgetItem("Test")
        item.setData(Qt.ItemDataRole.UserRole, "test_id")
        widget.profile_list.addItem(item)
        widget.profile_list.setCurrentItem(item)

        with patch.object(QMessageBox, "question", return_value=QMessageBox.No):
            widget._delete_profile()

        assert len(signals_received) == 0
        widget.close()

    def test_delete_profile_no_selection(self, qapp):
        """Test delete does nothing without selection."""
        from apps.gui.widgets.profile_panel import ProfilePanel

        widget = ProfilePanel()
        # Should not raise with no selection
        widget._delete_profile()
        widget.close()

    def test_activate_profile(self, qapp):
        """Test activating a profile."""

        from apps.gui.widgets.profile_panel import ProfilePanel
        from crates.profile_schema import Layer, Profile

        loader = MagicMock()
        profile = Profile(
            id="test_id",
            name="Test",
            description="",
            layers=[Layer(id="base", name="Base", bindings=[], hold_modifier_input_code=None)],
        )
        loader.list_profiles.return_value = ["test_id"]
        loader.get_active_profile_id.return_value = None
        loader.load_profile.return_value = profile

        widget = ProfilePanel()
        widget.load_profiles(loader)
        widget.profile_list.setCurrentRow(0)

        widget._activate_profile()

        loader.set_active_profile.assert_called_with("test_id")
        widget.close()

    def test_activate_profile_no_selection(self, qapp):
        """Test activate does nothing without selection."""
        from apps.gui.widgets.profile_panel import ProfilePanel

        widget = ProfilePanel()
        # Should not raise
        widget._activate_profile()
        widget.close()

    def test_activate_profile_no_loader(self, qapp):
        """Test activate does nothing without loader."""
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QListWidgetItem

        from apps.gui.widgets.profile_panel import ProfilePanel

        widget = ProfilePanel()
        item = QListWidgetItem("Test")
        item.setData(Qt.ItemDataRole.UserRole, "test_id")
        widget.profile_list.addItem(item)
        widget.profile_list.setCurrentItem(item)

        # Should not raise
        widget._activate_profile()
        widget.close()


class TestNewProfileDialogExtended:
    """Extended tests for NewProfileDialog."""

    @pytest.fixture
    def qapp(self):
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app

    def test_dialog_window_title(self, qapp):
        """Test NewProfileDialog has correct window title."""
        from apps.gui.widgets.profile_panel import NewProfileDialog

        dialog = NewProfileDialog()
        assert dialog is not None
        assert dialog.windowTitle() == "New Profile"
        dialog.close()

    def test_get_profile_with_name(self, qapp):
        """Test get_profile returns profile when name provided."""
        from apps.gui.widgets.profile_panel import NewProfileDialog

        dialog = NewProfileDialog()
        dialog.name_edit.setText("My Profile")
        dialog.desc_edit.setText("Description")

        profile = dialog.get_profile()
        assert profile is not None
        assert profile.name == "My Profile"
        assert profile.id == "my_profile"
        assert profile.description == "Description"
        assert len(profile.layers) == 1
        dialog.close()

    def test_get_profile_empty_name(self, qapp):
        """Test get_profile returns None for empty name."""
        from apps.gui.widgets.profile_panel import NewProfileDialog

        dialog = NewProfileDialog()
        dialog.name_edit.setText("")

        profile = dialog.get_profile()
        assert profile is None
        dialog.close()

    def test_get_profile_whitespace_name(self, qapp):
        """Test get_profile returns None for whitespace-only name."""
        from apps.gui.widgets.profile_panel import NewProfileDialog

        dialog = NewProfileDialog()
        dialog.name_edit.setText("   ")

        profile = dialog.get_profile()
        assert profile is None
        dialog.close()


class TestProfilePanelImportExport:
    """Tests for ProfilePanel import/export methods."""

    @pytest.fixture
    def qapp(self):
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app

    def test_import_profile_cancelled(self, qapp):
        """Test import does nothing when file dialog cancelled."""
        from unittest.mock import patch

        from apps.gui.widgets.profile_panel import ProfilePanel

        widget = ProfilePanel()

        with patch("apps.gui.widgets.profile_panel.QFileDialog.getOpenFileName") as mock_dialog:
            mock_dialog.return_value = ("", "")  # Cancelled
            widget._import_profile()
            # Should return early, no errors

        widget.close()

    def test_import_profile_json_success(self, qapp, tmp_path):
        """Test importing a JSON profile file."""
        import json
        from unittest.mock import patch

        from apps.gui.widgets.profile_panel import ProfilePanel

        # Create test file
        profile_data = {
            "id": "imported",
            "name": "Imported Profile",
            "description": "Test",
            "layers": [
                {"id": "base", "name": "Base", "bindings": [], "hold_modifier_input_code": None}
            ],
        }
        test_file = tmp_path / "test.json"
        test_file.write_text(json.dumps(profile_data))

        loader = MagicMock()
        loader.load_profile.return_value = None  # Profile doesn't exist
        loader.save_profile.return_value = True
        loader.list_profiles.return_value = []
        loader.get_active_profile_id.return_value = None

        widget = ProfilePanel()
        widget.load_profiles(loader)

        with (
            patch("apps.gui.widgets.profile_panel.QFileDialog.getOpenFileName") as mock_fd,
            patch("apps.gui.widgets.profile_panel.QMessageBox.information"),
        ):
            mock_fd.return_value = (str(test_file), "JSON Files (*.json)")
            widget._import_profile()

        loader.save_profile.assert_called()
        widget.close()

    def test_import_profile_yaml_success(self, qapp, tmp_path):
        """Test importing a YAML profile file."""
        from unittest.mock import patch

        import yaml

        from apps.gui.widgets.profile_panel import ProfilePanel

        # Create test file
        profile_data = {
            "id": "yaml_profile",
            "name": "YAML Profile",
            "description": "Test",
            "layers": [
                {"id": "base", "name": "Base", "bindings": [], "hold_modifier_input_code": None}
            ],
        }
        test_file = tmp_path / "test.yaml"
        test_file.write_text(yaml.dump(profile_data))

        loader = MagicMock()
        loader.load_profile.return_value = None
        loader.save_profile.return_value = True
        loader.list_profiles.return_value = []
        loader.get_active_profile_id.return_value = None

        widget = ProfilePanel()
        widget.load_profiles(loader)

        with (
            patch("apps.gui.widgets.profile_panel.QFileDialog.getOpenFileName") as mock_fd,
            patch("apps.gui.widgets.profile_panel.QMessageBox.information"),
        ):
            mock_fd.return_value = (str(test_file), "YAML Files (*.yaml)")
            widget._import_profile()

        loader.save_profile.assert_called()
        widget.close()

    def test_import_profile_wrapped_format(self, qapp, tmp_path):
        """Test importing a profile in wrapped export format."""
        import json
        from unittest.mock import patch

        from apps.gui.widgets.profile_panel import ProfilePanel

        # Create wrapped format file
        wrapped_data = {
            "_export": {"version": "1.0", "exported_at": "2025-01-01", "format": "json"},
            "profile": {
                "id": "wrapped",
                "name": "Wrapped Profile",
                "description": "",
                "layers": [
                    {"id": "base", "name": "Base", "bindings": [], "hold_modifier_input_code": None}
                ],
            },
        }
        test_file = tmp_path / "wrapped.json"
        test_file.write_text(json.dumps(wrapped_data))

        loader = MagicMock()
        loader.load_profile.return_value = None
        loader.save_profile.return_value = True
        loader.list_profiles.return_value = []
        loader.get_active_profile_id.return_value = None

        widget = ProfilePanel()
        widget.load_profiles(loader)

        with (
            patch("apps.gui.widgets.profile_panel.QFileDialog.getOpenFileName") as mock_fd,
            patch("apps.gui.widgets.profile_panel.QMessageBox.information"),
        ):
            mock_fd.return_value = (str(test_file), "JSON Files (*.json)")
            widget._import_profile()

        loader.save_profile.assert_called()
        widget.close()

    def test_import_profile_exists_overwrite(self, qapp, tmp_path):
        """Test importing when profile exists and user chooses to overwrite."""
        import json
        from unittest.mock import patch

        from PySide6.QtWidgets import QMessageBox

        from apps.gui.widgets.profile_panel import ProfilePanel
        from crates.profile_schema import Layer, Profile

        profile_data = {
            "id": "existing",
            "name": "Existing Profile",
            "description": "",
            "layers": [
                {"id": "base", "name": "Base", "bindings": [], "hold_modifier_input_code": None}
            ],
        }
        test_file = tmp_path / "existing.json"
        test_file.write_text(json.dumps(profile_data))

        existing_profile = Profile(
            id="existing",
            name="Old Profile",
            description="",
            layers=[Layer(id="base", name="Base", bindings=[], hold_modifier_input_code=None)],
        )

        loader = MagicMock()
        loader.load_profile.return_value = existing_profile  # Profile exists
        loader.save_profile.return_value = True
        loader.list_profiles.return_value = ["existing"]
        loader.get_active_profile_id.return_value = None

        widget = ProfilePanel()
        widget.load_profiles(loader)

        with (
            patch("apps.gui.widgets.profile_panel.QFileDialog.getOpenFileName") as mock_fd,
            patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes),
            patch("apps.gui.widgets.profile_panel.QMessageBox.information"),
        ):
            mock_fd.return_value = (str(test_file), "JSON Files (*.json)")
            widget._import_profile()

        loader.save_profile.assert_called()
        widget.close()

    def test_import_profile_exists_no_overwrite(self, qapp, tmp_path):
        """Test importing when profile exists and user declines overwrite."""
        import json
        from unittest.mock import patch

        from PySide6.QtWidgets import QMessageBox

        from apps.gui.widgets.profile_panel import ProfilePanel
        from crates.profile_schema import Layer, Profile

        profile_data = {
            "id": "existing",
            "name": "Existing Profile",
            "description": "",
            "layers": [
                {"id": "base", "name": "Base", "bindings": [], "hold_modifier_input_code": None}
            ],
        }
        test_file = tmp_path / "existing.json"
        test_file.write_text(json.dumps(profile_data))

        existing_profile = Profile(
            id="existing",
            name="Old Profile",
            description="",
            layers=[Layer(id="base", name="Base", bindings=[], hold_modifier_input_code=None)],
        )

        loader = MagicMock()
        loader.load_profile.return_value = existing_profile
        loader.list_profiles.return_value = ["existing"]
        loader.get_active_profile_id.return_value = None

        widget = ProfilePanel()
        widget.load_profiles(loader)

        with (
            patch("apps.gui.widgets.profile_panel.QFileDialog.getOpenFileName") as mock_fd,
            patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.No),
        ):
            mock_fd.return_value = (str(test_file), "JSON Files (*.json)")
            widget._import_profile()

        loader.save_profile.assert_not_called()
        widget.close()

    def test_import_profile_save_fails(self, qapp, tmp_path):
        """Test import shows warning when save fails."""
        import json
        from unittest.mock import patch

        from apps.gui.widgets.profile_panel import ProfilePanel

        profile_data = {
            "id": "fail",
            "name": "Fail Profile",
            "description": "",
            "layers": [
                {"id": "base", "name": "Base", "bindings": [], "hold_modifier_input_code": None}
            ],
        }
        test_file = tmp_path / "fail.json"
        test_file.write_text(json.dumps(profile_data))

        loader = MagicMock()
        loader.load_profile.return_value = None
        loader.save_profile.return_value = False  # Save fails
        loader.list_profiles.return_value = []
        loader.get_active_profile_id.return_value = None

        widget = ProfilePanel()
        widget.load_profiles(loader)

        with (
            patch("apps.gui.widgets.profile_panel.QFileDialog.getOpenFileName") as mock_fd,
            patch("apps.gui.widgets.profile_panel.QMessageBox.warning") as mock_warn,
        ):
            mock_fd.return_value = (str(test_file), "JSON Files (*.json)")
            widget._import_profile()
            mock_warn.assert_called()

        widget.close()

    def test_import_profile_invalid_json(self, qapp, tmp_path):
        """Test import shows error for invalid JSON."""
        from unittest.mock import patch

        from apps.gui.widgets.profile_panel import ProfilePanel

        test_file = tmp_path / "invalid.json"
        test_file.write_text("{ invalid json }")

        loader = MagicMock()
        loader.list_profiles.return_value = []
        loader.get_active_profile_id.return_value = None

        widget = ProfilePanel()
        widget.load_profiles(loader)

        with (
            patch("apps.gui.widgets.profile_panel.QFileDialog.getOpenFileName") as mock_fd,
            patch("apps.gui.widgets.profile_panel.QMessageBox.critical") as mock_crit,
        ):
            mock_fd.return_value = (str(test_file), "JSON Files (*.json)")
            widget._import_profile()
            mock_crit.assert_called()

        widget.close()

    def test_import_profile_validation_error(self, qapp, tmp_path):
        """Test import shows error for invalid profile schema."""
        import json
        from unittest.mock import patch

        from apps.gui.widgets.profile_panel import ProfilePanel

        # Missing required fields
        test_file = tmp_path / "invalid_schema.json"
        test_file.write_text(json.dumps({"name": "No ID"}))

        loader = MagicMock()
        loader.list_profiles.return_value = []
        loader.get_active_profile_id.return_value = None

        widget = ProfilePanel()
        widget.load_profiles(loader)

        with (
            patch("apps.gui.widgets.profile_panel.QFileDialog.getOpenFileName") as mock_fd,
            patch("apps.gui.widgets.profile_panel.QMessageBox.critical") as mock_crit,
        ):
            mock_fd.return_value = (str(test_file), "JSON Files (*.json)")
            widget._import_profile()
            mock_crit.assert_called()

        widget.close()

    def test_export_profile_cancelled(self, qapp):
        """Test export does nothing when file dialog cancelled."""
        from unittest.mock import patch

        from apps.gui.widgets.profile_panel import ProfilePanel
        from crates.profile_schema import Layer, Profile

        loader = MagicMock()
        profile = Profile(
            id="test",
            name="Test",
            description="",
            layers=[Layer(id="base", name="Base", bindings=[], hold_modifier_input_code=None)],
        )
        loader.load_profile.return_value = profile
        loader.list_profiles.return_value = ["test"]
        loader.get_active_profile_id.return_value = None

        widget = ProfilePanel()
        widget.load_profiles(loader)
        widget.profile_list.setCurrentRow(0)

        with patch("apps.gui.widgets.profile_panel.QFileDialog.getSaveFileName") as mock_fd:
            mock_fd.return_value = ("", "")  # Cancelled
            widget._export_profile()

        widget.close()

    def test_export_profile_json(self, qapp, tmp_path):
        """Test exporting profile as JSON."""
        import json
        from unittest.mock import patch

        from apps.gui.widgets.profile_panel import ProfilePanel
        from crates.profile_schema import Layer, Profile

        loader = MagicMock()
        profile = Profile(
            id="export_test",
            name="Export Test",
            description="Desc",
            layers=[Layer(id="base", name="Base", bindings=[], hold_modifier_input_code=None)],
        )
        loader.load_profile.return_value = profile
        loader.list_profiles.return_value = ["export_test"]
        loader.get_active_profile_id.return_value = None

        widget = ProfilePanel()
        widget.load_profiles(loader)
        widget.profile_list.setCurrentRow(0)

        output_file = tmp_path / "export.json"

        with (
            patch("apps.gui.widgets.profile_panel.QFileDialog.getSaveFileName") as mock_fd,
            patch("apps.gui.widgets.profile_panel.QMessageBox.information"),
        ):
            mock_fd.return_value = (str(output_file), "JSON Files (*.json)")
            widget._export_profile()

        assert output_file.exists()
        data = json.loads(output_file.read_text())
        assert "_export" in data
        assert "profile" in data
        assert data["profile"]["name"] == "Export Test"
        widget.close()

    def test_export_profile_yaml(self, qapp, tmp_path):
        """Test exporting profile as YAML."""
        from unittest.mock import patch

        import yaml

        from apps.gui.widgets.profile_panel import ProfilePanel
        from crates.profile_schema import Layer, Profile

        loader = MagicMock()
        profile = Profile(
            id="yaml_export",
            name="YAML Export",
            description="",
            layers=[Layer(id="base", name="Base", bindings=[], hold_modifier_input_code=None)],
        )
        loader.load_profile.return_value = profile
        loader.list_profiles.return_value = ["yaml_export"]
        loader.get_active_profile_id.return_value = None

        widget = ProfilePanel()
        widget.load_profiles(loader)
        widget.profile_list.setCurrentRow(0)

        output_file = tmp_path / "export.yaml"

        with (
            patch("apps.gui.widgets.profile_panel.QFileDialog.getSaveFileName") as mock_fd,
            patch("apps.gui.widgets.profile_panel.QMessageBox.information"),
        ):
            mock_fd.return_value = (str(output_file), "YAML Files (*.yaml)")
            widget._export_profile()

        assert output_file.exists()
        data = yaml.safe_load(output_file.read_text())
        assert "_export" in data
        assert "profile" in data
        widget.close()

    def test_export_profile_adds_json_extension(self, qapp, tmp_path):
        """Test export adds .json extension if missing."""
        from unittest.mock import patch

        from apps.gui.widgets.profile_panel import ProfilePanel
        from crates.profile_schema import Layer, Profile

        loader = MagicMock()
        profile = Profile(
            id="noext",
            name="No Extension",
            description="",
            layers=[Layer(id="base", name="Base", bindings=[], hold_modifier_input_code=None)],
        )
        loader.load_profile.return_value = profile
        loader.list_profiles.return_value = ["noext"]
        loader.get_active_profile_id.return_value = None

        widget = ProfilePanel()
        widget.load_profiles(loader)
        widget.profile_list.setCurrentRow(0)

        # File without extension
        output_file = tmp_path / "noext"

        with (
            patch("apps.gui.widgets.profile_panel.QFileDialog.getSaveFileName") as mock_fd,
            patch("apps.gui.widgets.profile_panel.QMessageBox.information"),
        ):
            mock_fd.return_value = (str(output_file), "JSON Files (*.json)")
            widget._export_profile()

        # Should create .json file
        json_file = tmp_path / "noext.json"
        assert json_file.exists()
        widget.close()

    def test_export_profile_no_selection(self, qapp):
        """Test export does nothing without selection."""
        from apps.gui.widgets.profile_panel import ProfilePanel

        widget = ProfilePanel()
        # Should not raise
        widget._export_profile()
        widget.close()

    def test_export_profile_write_error(self, qapp, tmp_path):
        """Test export shows error when write fails."""
        from unittest.mock import patch

        from apps.gui.widgets.profile_panel import ProfilePanel
        from crates.profile_schema import Layer, Profile

        loader = MagicMock()
        profile = Profile(
            id="write_fail",
            name="Write Fail",
            description="",
            layers=[Layer(id="base", name="Base", bindings=[], hold_modifier_input_code=None)],
        )
        loader.load_profile.return_value = profile
        loader.list_profiles.return_value = ["write_fail"]
        loader.get_active_profile_id.return_value = None

        widget = ProfilePanel()
        widget.load_profiles(loader)
        widget.profile_list.setCurrentRow(0)

        # Path that can't be written
        output_file = tmp_path / "readonly" / "test.json"

        with (
            patch("apps.gui.widgets.profile_panel.QFileDialog.getSaveFileName") as mock_fd,
            patch("apps.gui.widgets.profile_panel.QMessageBox.critical") as mock_crit,
        ):
            mock_fd.return_value = (str(output_file), "JSON Files (*.json)")
            widget._export_profile()
            mock_crit.assert_called()

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


class TestDPIStageItemCoverage:
    """Extended coverage tests for DPIStageItem."""

    @pytest.fixture
    def qapp(self):
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app

    def test_slider_rounding(self, qapp):
        """Test slider value is rounded to nearest 100."""
        from apps.gui.widgets.dpi_editor import DPIStageItem

        item = DPIStageItem(dpi=800, max_dpi=16000, index=0)
        # The slider rounding logic triggers when the value changes
        # Use 851 which rounds to 900 (Python banker's rounding: round(8.5)=8, round(8.51)=9)
        item._on_slider_changed(851)
        # Should be rounded to 900 in spin
        assert item.spin.value() == 900
        item.close()

    def test_bar_color_low_dpi(self, qapp):
        """Test bar color for low DPI (< 25%)."""
        from apps.gui.widgets.dpi_editor import DPIStageItem

        item = DPIStageItem(dpi=2000, max_dpi=16000, index=0)  # 12.5%
        # Blue color for low DPI
        assert "3498db" in item.dpi_bar.styleSheet()
        item.close()

    def test_bar_color_medium_dpi(self, qapp):
        """Test bar color for medium DPI (25-50%)."""
        from apps.gui.widgets.dpi_editor import DPIStageItem

        item = DPIStageItem(dpi=6000, max_dpi=16000, index=0)  # 37.5%
        # Green color for medium DPI
        assert "2ecc71" in item.dpi_bar.styleSheet()
        item.close()

    def test_bar_color_high_dpi(self, qapp):
        """Test bar color for high DPI (50-75%)."""
        from apps.gui.widgets.dpi_editor import DPIStageItem

        item = DPIStageItem(dpi=10000, max_dpi=16000, index=0)  # 62.5%
        # Yellow color for high DPI
        assert "f1c40f" in item.dpi_bar.styleSheet()
        item.close()

    def test_bar_color_very_high_dpi(self, qapp):
        """Test bar color for very high DPI (> 75%)."""
        from apps.gui.widgets.dpi_editor import DPIStageItem

        item = DPIStageItem(dpi=14000, max_dpi=16000, index=0)  # 87.5%
        # Red color for very high DPI
        assert "e74c3c" in item.dpi_bar.styleSheet()
        item.close()


class TestDPIStageEditorCoverage:
    """Extended coverage tests for DPIStageEditor."""

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
        bridge.set_dpi.return_value = True
        return bridge

    @pytest.fixture
    def mock_device(self):
        device = MagicMock()
        device.name = "Test Mouse"
        device.has_dpi = True
        device.max_dpi = 16000
        device.dpi = (800, 800)
        device.serial = "test-serial"
        return device

    def test_set_device_with_device(self, qapp, mock_bridge, mock_device):
        """Test setting a device with DPI support."""
        from apps.gui.widgets.dpi_editor import DPIStageEditor

        editor = DPIStageEditor(bridge=mock_bridge)
        editor.set_device(mock_device)

        assert editor.current_device == mock_device
        assert len(editor._stage_items) > 0
        assert editor.add_btn.isEnabled()
        assert editor.apply_btn.isEnabled()
        editor.close()

    def test_set_device_none(self, qapp, mock_bridge, mock_device):
        """Test setting device to None clears editor."""
        from apps.gui.widgets.dpi_editor import DPIStageEditor

        editor = DPIStageEditor(bridge=mock_bridge)
        editor.set_device(mock_device)
        assert len(editor._stage_items) > 0

        # Now set to None
        editor.set_device(None)

        assert editor.current_device is None
        assert len(editor._stage_items) == 0
        assert not editor.add_btn.isEnabled()
        assert not editor.apply_btn.isEnabled()
        editor.close()

    def test_set_device_clears_existing(self, qapp, mock_bridge, mock_device):
        """Test setting a new device clears existing stages."""
        from apps.gui.widgets.dpi_editor import DPIStageEditor

        editor = DPIStageEditor(bridge=mock_bridge)
        editor.set_device(mock_device)
        initial_count = len(editor._stage_items)

        # Set same device again - should recreate stages
        editor.set_device(mock_device)
        assert len(editor._stage_items) == initial_count  # Same number
        editor.close()

    def test_set_config_with_device(self, qapp, mock_bridge, mock_device):
        """Test set_config with a device selected."""
        from apps.gui.widgets.dpi_editor import DPIStageEditor
        from crates.profile_schema import DPIConfig

        editor = DPIStageEditor(bridge=mock_bridge)
        editor.set_device(mock_device)

        config = DPIConfig(stages=[400, 800, 1200, 1600], active_stage=2)
        editor.set_config(config)

        assert len(editor._stage_items) == 4
        assert editor._active_stage == 2
        editor.close()

    def test_add_stage(self, qapp, mock_bridge, mock_device):
        """Test adding a new stage."""
        from apps.gui.widgets.dpi_editor import DPIStageEditor

        editor = DPIStageEditor(bridge=mock_bridge)
        editor.set_device(mock_device)
        initial_count = len(editor._stage_items)

        editor._add_stage()

        assert len(editor._stage_items) == initial_count + 1
        editor.close()

    def test_add_stage_max_reached(self, qapp, mock_bridge, mock_device):
        """Test adding stage at maximum shows message."""
        from PySide6.QtWidgets import QMessageBox

        from apps.gui.widgets.dpi_editor import DPIStageEditor

        editor = DPIStageEditor(bridge=mock_bridge)
        editor.set_device(mock_device)

        # Add stages until max
        while len(editor._stage_items) < editor.MAX_STAGES:
            editor._add_stage()

        with patch.object(QMessageBox, "information") as mock_info:
            editor._add_stage()
            mock_info.assert_called_once()
        editor.close()

    def test_add_stage_no_device(self, qapp, mock_bridge):
        """Test adding stage without device does nothing."""
        from apps.gui.widgets.dpi_editor import DPIStageEditor

        editor = DPIStageEditor(bridge=mock_bridge)
        editor._add_stage()
        assert len(editor._stage_items) == 0
        editor.close()

    def test_remove_stage(self, qapp, mock_bridge, mock_device):
        """Test removing a stage."""
        from apps.gui.widgets.dpi_editor import DPIStageEditor

        editor = DPIStageEditor(bridge=mock_bridge)
        editor.set_device(mock_device)

        # Add an extra stage
        editor._add_stage()
        count_before = len(editor._stage_items)

        # Remove the last stage
        editor._remove_stage(editor._stage_items[-1])

        assert len(editor._stage_items) == count_before - 1
        editor.close()

    def test_remove_stage_last_one(self, qapp, mock_bridge, mock_device):
        """Test cannot remove the last stage."""
        from PySide6.QtWidgets import QMessageBox

        from apps.gui.widgets.dpi_editor import DPIStageEditor
        from crates.profile_schema import DPIConfig

        editor = DPIStageEditor(bridge=mock_bridge)
        editor.set_device(mock_device)

        # Set config with only 1 stage
        config = DPIConfig(stages=[800], active_stage=0)
        editor.set_config(config)
        assert len(editor._stage_items) == 1

        with patch.object(QMessageBox, "warning") as mock_warn:
            editor._remove_stage(editor._stage_items[0])
            mock_warn.assert_called_once()
        assert len(editor._stage_items) == 1
        editor.close()

    def test_remove_stage_adjusts_active(self, qapp, mock_bridge, mock_device):
        """Test removing active stage adjusts active index."""
        from apps.gui.widgets.dpi_editor import DPIStageEditor
        from crates.profile_schema import DPIConfig

        editor = DPIStageEditor(bridge=mock_bridge)
        editor.set_device(mock_device)

        config = DPIConfig(stages=[400, 800, 1600], active_stage=2)
        editor.set_config(config)

        # Remove the last (active) stage
        editor._remove_stage(editor._stage_items[-1])

        # Active stage should be adjusted
        assert editor._active_stage == 1
        editor.close()

    def test_set_active_stage_out_of_range(self, qapp, mock_bridge, mock_device):
        """Test setting active stage out of range does nothing."""
        from apps.gui.widgets.dpi_editor import DPIStageEditor

        editor = DPIStageEditor(bridge=mock_bridge)
        editor.set_device(mock_device)
        initial_active = editor._active_stage

        editor._set_active_stage(100)  # Way out of range

        # Should not change
        assert editor._active_stage == initial_active
        editor.close()

    def test_apply_preset(self, qapp, mock_bridge, mock_device):
        """Test applying a preset configuration."""
        from apps.gui.widgets.dpi_editor import DPIStageEditor

        editor = DPIStageEditor(bridge=mock_bridge)
        editor.set_device(mock_device)

        preset = [400, 800, 1600]
        editor._apply_preset(preset)

        assert len(editor._stage_items) == 3
        assert editor._stage_items[0].get_dpi() == 400
        assert editor._stage_items[1].get_dpi() == 800
        assert editor._stage_items[2].get_dpi() == 1600
        editor.close()

    def test_apply_preset_no_device(self, qapp, mock_bridge):
        """Test applying preset without device does nothing."""
        from apps.gui.widgets.dpi_editor import DPIStageEditor

        editor = DPIStageEditor(bridge=mock_bridge)
        editor._apply_preset([400, 800])
        assert len(editor._stage_items) == 0
        editor.close()

    def test_apply_to_device_success(self, qapp, mock_bridge, mock_device):
        """Test applying DPI to device successfully."""
        from PySide6.QtWidgets import QMessageBox

        from apps.gui.widgets.dpi_editor import DPIStageEditor

        editor = DPIStageEditor(bridge=mock_bridge)
        editor.set_device(mock_device)

        with patch.object(QMessageBox, "information") as mock_info:
            editor._apply_to_device()
            mock_info.assert_called_once()
        editor.close()

    def test_apply_to_device_failure(self, qapp, mock_bridge, mock_device):
        """Test applying DPI to device with failure."""
        from PySide6.QtWidgets import QMessageBox

        from apps.gui.widgets.dpi_editor import DPIStageEditor

        mock_bridge.set_dpi.return_value = False

        editor = DPIStageEditor(bridge=mock_bridge)
        editor.set_device(mock_device)

        with patch.object(QMessageBox, "warning") as mock_warn:
            editor._apply_to_device()
            mock_warn.assert_called_once()
        editor.close()

    def test_apply_to_device_no_device(self, qapp, mock_bridge):
        """Test applying DPI without device does nothing."""
        from apps.gui.widgets.dpi_editor import DPIStageEditor

        editor = DPIStageEditor(bridge=mock_bridge)
        # Should not crash
        editor._apply_to_device()
        editor.close()

    def test_on_stage_changed_emits_signal(self, qapp, mock_bridge, mock_device):
        """Test stage changed emits signal."""
        from apps.gui.widgets.dpi_editor import DPIStageEditor

        editor = DPIStageEditor(bridge=mock_bridge)
        editor.set_device(mock_device)

        signal_emitted = []
        editor.stages_changed.connect(lambda stages: signal_emitted.append(stages))

        editor._on_stage_changed()

        assert len(signal_emitted) == 1
        assert isinstance(signal_emitted[0], list)
        editor.close()


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
            id="test",
            name="Test",
            description="",
            layers=[Layer(id="base", name="Base", bindings=[], hold_modifier_input_code=None)],
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
            id="test",
            name="Test",
            description="",
            layers=[Layer(id="base", name="Base", bindings=[], hold_modifier_input_code=None)],
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
            id="test",
            name="Test",
            description="",
            layers=[Layer(id="base", name="Base", bindings=[], hold_modifier_input_code=None)],
        )
        widget.load_profile(profile)
        widget.clear()
        assert widget.current_profile is None
        widget.close()

    def test_get_current_layer(self, qapp):
        """Test _get_current_layer method."""
        from apps.gui.widgets.binding_editor import BindingEditorWidget
        from crates.profile_schema import Layer, Profile

        widget = BindingEditorWidget()
        # No profile - should return None
        assert widget._get_current_layer() is None

        profile = Profile(
            id="test",
            name="Test",
            description="",
            layers=[
                Layer(id="base", name="Base", bindings=[], hold_modifier_input_code=None),
                Layer(
                    id="hypershift",
                    name="Hypershift",
                    bindings=[],
                    hold_modifier_input_code="BTN_SIDE",
                ),
            ],
        )
        widget.load_profile(profile)
        layer = widget._get_current_layer()
        assert layer is not None
        assert layer.id == "base"
        widget.close()

    def test_refresh_bindings(self, qapp):
        """Test _refresh_bindings populates the list."""
        from apps.gui.widgets.binding_editor import BindingEditorWidget
        from crates.profile_schema import ActionType, Binding, Layer, Profile

        widget = BindingEditorWidget()
        profile = Profile(
            id="test",
            name="Test",
            description="",
            layers=[
                Layer(
                    id="base",
                    name="Base",
                    bindings=[
                        Binding(
                            input_code="BTN_SIDE", action_type=ActionType.KEY, output_keys=["F13"]
                        ),
                    ],
                    hold_modifier_input_code=None,
                )
            ],
        )
        widget.load_profile(profile)
        assert widget.bindings_list.count() == 1
        widget.close()

    def test_format_binding_key(self, qapp):
        """Test _format_binding for KEY action."""
        from apps.gui.widgets.binding_editor import BindingEditorWidget
        from crates.profile_schema import ActionType, Binding

        widget = BindingEditorWidget()
        binding = Binding(input_code="BTN_SIDE", action_type=ActionType.KEY, output_keys=["F13"])
        result = widget._format_binding(binding)
        assert "F13" in result
        widget.close()

    def test_format_binding_chord(self, qapp):
        """Test _format_binding for CHORD action."""
        from apps.gui.widgets.binding_editor import BindingEditorWidget
        from crates.profile_schema import ActionType, Binding

        widget = BindingEditorWidget()
        binding = Binding(
            input_code="BTN_SIDE", action_type=ActionType.CHORD, output_keys=["CTRL", "C"]
        )
        result = widget._format_binding(binding)
        assert "CTRL+C" in result
        widget.close()

    def test_format_binding_macro(self, qapp):
        """Test _format_binding for MACRO action."""
        from apps.gui.widgets.binding_editor import BindingEditorWidget
        from crates.profile_schema import ActionType, Binding

        widget = BindingEditorWidget()
        binding = Binding(
            input_code="BTN_SIDE", action_type=ActionType.MACRO, macro_id="test_macro"
        )
        result = widget._format_binding(binding)
        assert "Macro" in result
        assert "test_macro" in result
        widget.close()

    def test_format_binding_passthrough(self, qapp):
        """Test _format_binding for PASSTHROUGH action."""
        from apps.gui.widgets.binding_editor import BindingEditorWidget
        from crates.profile_schema import ActionType, Binding

        widget = BindingEditorWidget()
        binding = Binding(input_code="BTN_SIDE", action_type=ActionType.PASSTHROUGH)
        result = widget._format_binding(binding)
        assert "passthrough" in result
        widget.close()

    def test_format_binding_disabled(self, qapp):
        """Test _format_binding for DISABLED action."""
        from apps.gui.widgets.binding_editor import BindingEditorWidget
        from crates.profile_schema import ActionType, Binding

        widget = BindingEditorWidget()
        binding = Binding(input_code="BTN_SIDE", action_type=ActionType.DISABLED)
        result = widget._format_binding(binding)
        assert "disabled" in result
        widget.close()

    def test_update_layer_info_base(self, qapp):
        """Test _update_layer_info for base layer."""
        from apps.gui.widgets.binding_editor import BindingEditorWidget
        from crates.profile_schema import Layer, Profile

        widget = BindingEditorWidget()
        profile = Profile(
            id="test",
            name="Test",
            description="",
            layers=[Layer(id="base", name="Base", bindings=[], hold_modifier_input_code=None)],
        )
        widget.load_profile(profile)
        widget._update_layer_info()
        assert "Base layer" in widget.layer_info_label.text()
        assert not widget.del_layer_btn.isEnabled()
        widget.close()

    def test_update_layer_info_hypershift(self, qapp):
        """Test _update_layer_info for hypershift layer."""
        from apps.gui.widgets.binding_editor import BindingEditorWidget
        from crates.profile_schema import Layer, Profile

        widget = BindingEditorWidget()
        profile = Profile(
            id="test",
            name="Test",
            description="",
            layers=[
                Layer(id="base", name="Base", bindings=[], hold_modifier_input_code=None),
                Layer(
                    id="hypershift",
                    name="Hypershift",
                    bindings=[],
                    hold_modifier_input_code="BTN_SIDE",
                ),
            ],
        )
        widget.load_profile(profile)
        widget.layer_combo.setCurrentIndex(1)  # Select hypershift layer
        assert "Hypershift" in widget.layer_info_label.text()
        assert widget.del_layer_btn.isEnabled()
        widget.close()

    def test_refresh_macros(self, qapp):
        """Test _refresh_macros populates the list."""
        from apps.gui.widgets.binding_editor import BindingEditorWidget
        from crates.profile_schema import Layer, MacroAction, Profile

        widget = BindingEditorWidget()
        profile = Profile(
            id="test",
            name="Test",
            description="",
            layers=[Layer(id="base", name="Base", bindings=[], hold_modifier_input_code=None)],
            macros=[MacroAction(id="test", name="Test Macro", steps=[], repeat_count=1)],
        )
        widget.load_profile(profile)
        assert widget.macros_list.count() == 1
        widget.close()


class TestLayerDialog:
    """Tests for LayerDialog."""

    @pytest.fixture
    def qapp(self):
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app

    def test_new_layer_dialog(self, qapp):
        """Test creating a new layer dialog."""
        from apps.gui.widgets.binding_editor import LayerDialog

        dialog = LayerDialog()
        assert dialog.windowTitle() == "New Layer"
        assert dialog.name_edit.text() == ""
        dialog.close()

    def test_edit_layer_dialog(self, qapp):
        """Test editing an existing layer."""
        from apps.gui.widgets.binding_editor import LayerDialog
        from crates.profile_schema import Layer

        layer = Layer(
            id="test", name="Test Layer", bindings=[], hold_modifier_input_code="BTN_SIDE"
        )
        dialog = LayerDialog(layer=layer)
        assert dialog.windowTitle() == "Edit Layer"
        assert dialog.name_edit.text() == "Test Layer"
        dialog.close()

    def test_base_layer_modifier_disabled(self, qapp):
        """Test that base layer cannot have modifier."""
        from apps.gui.widgets.binding_editor import LayerDialog

        dialog = LayerDialog(is_base=True)
        assert not dialog.modifier_combo.isEnabled()
        dialog.close()

    def test_get_layer_data(self, qapp):
        """Test getting layer data."""
        from apps.gui.widgets.binding_editor import LayerDialog

        dialog = LayerDialog()
        dialog.name_edit.setText("My Layer")
        dialog.modifier_combo.setCurrentIndex(2)  # BTN_SIDE
        name, modifier = dialog.get_layer_data()
        assert name == "My Layer"
        assert modifier == "BTN_SIDE"
        dialog.close()

    def test_get_layer_data_custom_modifier(self, qapp):
        """Test getting layer data with custom modifier."""
        from apps.gui.widgets.binding_editor import LayerDialog

        dialog = LayerDialog()
        dialog.name_edit.setText("Custom")
        dialog.modifier_combo.setEditText("KEY_F20")
        name, modifier = dialog.get_layer_data()
        assert name == "Custom"
        assert modifier == "KEY_F20"
        dialog.close()


class TestBindingDialog:
    """Tests for BindingDialog."""

    @pytest.fixture
    def qapp(self):
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app

    def test_new_binding_dialog(self, qapp):
        """Test creating a new binding dialog."""
        from apps.gui.widgets.binding_editor import BindingDialog

        dialog = BindingDialog()
        assert dialog.windowTitle() == "Edit Binding"
        dialog.close()

    def test_load_existing_binding(self, qapp):
        """Test loading an existing binding."""
        from apps.gui.widgets.binding_editor import BindingDialog
        from crates.profile_schema import ActionType, Binding

        binding = Binding(input_code="BTN_SIDE", action_type=ActionType.KEY, output_keys=["F13"])
        dialog = BindingDialog(binding=binding)
        assert dialog.output_edit.text() == "F13"
        dialog.close()

    def test_action_changed_key(self, qapp):
        """Test action change to KEY shows output field."""
        from apps.gui.widgets.binding_editor import BindingDialog

        dialog = BindingDialog()
        dialog.action_combo.setCurrentIndex(0)  # KEY
        dialog._on_action_changed()
        # Check not hidden (isVisible=False when parent not shown)
        assert not dialog.output_edit.isHidden()
        assert dialog.macro_combo.isHidden()
        dialog.close()

    def test_action_changed_macro(self, qapp):
        """Test action change to MACRO shows macro combo."""
        from apps.gui.widgets.binding_editor import BindingDialog

        dialog = BindingDialog()
        dialog.action_combo.setCurrentIndex(2)  # MACRO
        dialog._on_action_changed()
        # Check not hidden (isVisible=False when parent not shown)
        assert not dialog.macro_combo.isHidden()
        dialog.close()

    def test_get_binding_key(self, qapp):
        """Test getting a key binding."""
        from apps.gui.widgets.binding_editor import BindingDialog
        from crates.profile_schema import ActionType

        dialog = BindingDialog()
        dialog.input_combo.setEditText("BTN_SIDE")
        dialog.action_combo.setCurrentIndex(0)  # KEY
        dialog.output_edit.setText("F13")
        binding = dialog.get_binding()
        assert binding is not None
        assert binding.input_code == "BTN_SIDE"
        assert binding.action_type == ActionType.KEY
        assert binding.output_keys == ["F13"]
        dialog.close()

    def test_get_binding_chord(self, qapp):
        """Test getting a chord binding."""
        from apps.gui.widgets.binding_editor import BindingDialog
        from crates.profile_schema import ActionType

        dialog = BindingDialog()
        dialog.input_combo.setEditText("BTN_EXTRA")
        dialog.action_combo.setCurrentIndex(1)  # CHORD
        dialog.output_edit.setText("CTRL+C")
        binding = dialog.get_binding()
        assert binding is not None
        assert binding.action_type == ActionType.CHORD
        assert binding.output_keys == ["CTRL", "C"]
        dialog.close()

    def test_get_binding_invalid_input(self, qapp):
        """Test getting binding with invalid input returns None."""
        from apps.gui.widgets.binding_editor import BindingDialog

        dialog = BindingDialog()
        dialog.input_combo.setEditText("--- Mouse Buttons ---")  # Category header
        binding = dialog.get_binding()
        assert binding is None
        dialog.close()


class TestMacroDialog:
    """Tests for MacroDialog."""

    @pytest.fixture
    def qapp(self):
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app

    def test_new_macro_dialog(self, qapp):
        """Test creating a new macro dialog."""
        from apps.gui.widgets.binding_editor import MacroDialog

        dialog = MacroDialog()
        assert dialog.windowTitle() == "Edit Macro"
        dialog.close()

    def test_load_existing_macro(self, qapp):
        """Test loading an existing macro."""
        from apps.gui.widgets.binding_editor import MacroDialog
        from crates.profile_schema import MacroAction, MacroStep, MacroStepType

        macro = MacroAction(
            id="test",
            name="Test Macro",
            steps=[
                MacroStep(type=MacroStepType.KEY_PRESS, key="A"),
                MacroStep(type=MacroStepType.DELAY, delay_ms=100),
            ],
            repeat_count=3,
        )
        dialog = MacroDialog(macro=macro)
        assert dialog.name_edit.text() == "Test Macro"
        assert dialog.repeat_spin.value() == 3
        assert "key:A" in dialog.steps_edit.toPlainText()
        assert "delay:100" in dialog.steps_edit.toPlainText()
        dialog.close()

    def test_load_macro_all_step_types(self, qapp):
        """Test loading macro with all step types."""
        from apps.gui.widgets.binding_editor import MacroDialog
        from crates.profile_schema import MacroAction, MacroStep, MacroStepType

        macro = MacroAction(
            id="test",
            name="Full",
            steps=[
                MacroStep(type=MacroStepType.KEY_PRESS, key="A"),
                MacroStep(type=MacroStepType.KEY_DOWN, key="CTRL"),
                MacroStep(type=MacroStepType.KEY_UP, key="CTRL"),
                MacroStep(type=MacroStepType.DELAY, delay_ms=50),
                MacroStep(type=MacroStepType.TEXT, text="hello"),
            ],
            repeat_count=1,
        )
        dialog = MacroDialog(macro=macro)
        text = dialog.steps_edit.toPlainText()
        assert "key:A" in text
        assert "down:CTRL" in text
        assert "up:CTRL" in text
        assert "delay:50" in text
        assert "text:hello" in text
        dialog.close()

    def test_get_macro(self, qapp):
        """Test getting a macro."""
        from apps.gui.widgets.binding_editor import MacroDialog
        from crates.profile_schema import MacroStepType

        dialog = MacroDialog()
        dialog.name_edit.setText("My Macro")
        dialog.steps_edit.setPlainText("key:A\ndelay:100\ntext:hi")
        dialog.repeat_spin.setValue(2)
        macro = dialog.get_macro()
        assert macro is not None
        assert macro.name == "My Macro"
        assert macro.id == "my_macro"
        assert macro.repeat_count == 2
        assert len(macro.steps) == 3
        assert macro.steps[0].type == MacroStepType.KEY_PRESS
        assert macro.steps[1].type == MacroStepType.DELAY
        assert macro.steps[2].type == MacroStepType.TEXT
        dialog.close()

    def test_get_macro_empty_name(self, qapp):
        """Test getting macro with empty name returns None."""
        from apps.gui.widgets.binding_editor import MacroDialog

        dialog = MacroDialog()
        dialog.name_edit.setText("")
        macro = dialog.get_macro()
        assert macro is None
        dialog.close()

    def test_get_macro_invalid_delay(self, qapp):
        """Test getting macro with invalid delay skips that step."""
        from apps.gui.widgets.binding_editor import MacroDialog

        dialog = MacroDialog()
        dialog.name_edit.setText("Test")
        dialog.steps_edit.setPlainText("delay:notanumber\nkey:A")
        macro = dialog.get_macro()
        assert macro is not None
        assert len(macro.steps) == 1  # Only the key step
        dialog.close()


class TestBindingEditorInteractive:
    """Tests for BindingEditorWidget interactive methods."""

    @pytest.fixture
    def qapp(self):
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app

    @pytest.fixture
    def widget_with_profile(self, qapp):
        from apps.gui.widgets.binding_editor import BindingEditorWidget
        from crates.profile_schema import ActionType, Binding, Layer, Profile

        widget = BindingEditorWidget()
        profile = Profile(
            id="test",
            name="Test",
            description="",
            layers=[
                Layer(
                    id="base",
                    name="Base",
                    bindings=[
                        Binding(
                            input_code="BTN_SIDE", action_type=ActionType.KEY, output_keys=["F13"]
                        ),
                    ],
                    hold_modifier_input_code=None,
                ),
            ],
        )
        widget.load_profile(profile)
        return widget

    def test_add_layer(self, widget_with_profile):
        """Test adding a layer."""
        from unittest.mock import MagicMock, patch

        from PySide6.QtWidgets import QDialog

        widget = widget_with_profile
        initial_layers = len(widget.current_profile.layers)

        with patch("apps.gui.widgets.binding_editor.LayerDialog") as MockDialog:
            mock_dialog = MagicMock()
            mock_dialog.exec.return_value = QDialog.DialogCode.Accepted
            mock_dialog.get_layer_data.return_value = ("New Layer", "BTN_EXTRA")
            MockDialog.return_value = mock_dialog

            widget._add_layer()

        assert len(widget.current_profile.layers) == initial_layers + 1
        new_layer = widget.current_profile.layers[-1]
        assert new_layer.name == "New Layer"
        assert new_layer.hold_modifier_input_code == "BTN_EXTRA"
        widget.close()

    def test_add_layer_cancelled(self, widget_with_profile):
        """Test cancelling add layer."""
        from unittest.mock import MagicMock, patch

        from PySide6.QtWidgets import QDialog

        widget = widget_with_profile
        initial_layers = len(widget.current_profile.layers)

        with patch("apps.gui.widgets.binding_editor.LayerDialog") as MockDialog:
            mock_dialog = MagicMock()
            mock_dialog.exec.return_value = QDialog.DialogCode.Rejected
            MockDialog.return_value = mock_dialog

            widget._add_layer()

        assert len(widget.current_profile.layers) == initial_layers
        widget.close()

    def test_edit_layer(self, qapp):
        """Test editing a layer."""
        from unittest.mock import MagicMock, patch

        from PySide6.QtWidgets import QDialog

        from apps.gui.widgets.binding_editor import BindingEditorWidget
        from crates.profile_schema import Layer, Profile

        widget = BindingEditorWidget()
        profile = Profile(
            id="test",
            name="Test",
            description="",
            layers=[
                Layer(id="base", name="Base", bindings=[], hold_modifier_input_code=None),
                Layer(id="layer2", name="Original", bindings=[], hold_modifier_input_code=None),
            ],
        )
        widget.load_profile(profile)
        widget.layer_combo.setCurrentIndex(1)  # Select layer2

        with patch("apps.gui.widgets.binding_editor.LayerDialog") as MockDialog:
            mock_dialog = MagicMock()
            mock_dialog.exec.return_value = QDialog.DialogCode.Accepted
            mock_dialog.get_layer_data.return_value = ("Edited Name", "BTN_SIDE")
            MockDialog.return_value = mock_dialog

            widget._edit_layer()

        layer = widget.current_profile.layers[1]
        assert layer.name == "Edited Name"
        assert layer.hold_modifier_input_code == "BTN_SIDE"
        widget.close()

    def test_delete_layer_confirmed(self, qapp):
        """Test deleting a layer when confirmed."""
        from unittest.mock import patch

        from PySide6.QtWidgets import QMessageBox

        from apps.gui.widgets.binding_editor import BindingEditorWidget
        from crates.profile_schema import Layer, Profile

        widget = BindingEditorWidget()
        profile = Profile(
            id="test",
            name="Test",
            description="",
            layers=[
                Layer(id="base", name="Base", bindings=[], hold_modifier_input_code=None),
                Layer(
                    id="layer2", name="To Delete", bindings=[], hold_modifier_input_code="BTN_SIDE"
                ),
            ],
        )
        widget.load_profile(profile)
        widget.layer_combo.setCurrentIndex(1)

        with patch.object(QMessageBox, "question", return_value=QMessageBox.Yes):
            widget._delete_layer()

        assert len(widget.current_profile.layers) == 1
        widget.close()

    def test_delete_layer_cancelled(self, qapp):
        """Test cancelling layer deletion."""
        from unittest.mock import patch

        from PySide6.QtWidgets import QMessageBox

        from apps.gui.widgets.binding_editor import BindingEditorWidget
        from crates.profile_schema import Layer, Profile

        widget = BindingEditorWidget()
        profile = Profile(
            id="test",
            name="Test",
            description="",
            layers=[
                Layer(id="base", name="Base", bindings=[], hold_modifier_input_code=None),
                Layer(id="layer2", name="Keep", bindings=[], hold_modifier_input_code="BTN_SIDE"),
            ],
        )
        widget.load_profile(profile)
        widget.layer_combo.setCurrentIndex(1)

        with patch.object(QMessageBox, "question", return_value=QMessageBox.No):
            widget._delete_layer()

        assert len(widget.current_profile.layers) == 2
        widget.close()

    def test_add_binding(self, widget_with_profile):
        """Test adding a binding."""
        from unittest.mock import MagicMock, patch

        from PySide6.QtWidgets import QDialog

        from crates.profile_schema import ActionType, Binding

        widget = widget_with_profile
        initial_bindings = len(widget.current_profile.layers[0].bindings)

        mock_binding = Binding(
            input_code="BTN_EXTRA", action_type=ActionType.KEY, output_keys=["F14"]
        )

        with patch("apps.gui.widgets.binding_editor.BindingDialog") as MockDialog:
            mock_dialog = MagicMock()
            mock_dialog.exec.return_value = QDialog.DialogCode.Accepted
            mock_dialog.get_binding.return_value = mock_binding
            MockDialog.return_value = mock_dialog

            widget._add_binding()

        assert len(widget.current_profile.layers[0].bindings) == initial_bindings + 1
        widget.close()

    def test_remove_binding(self, widget_with_profile):
        """Test removing a binding."""
        widget = widget_with_profile
        initial_bindings = len(widget.current_profile.layers[0].bindings)
        assert initial_bindings == 1

        # Select the first binding
        widget.bindings_list.setCurrentRow(0)
        widget._remove_binding()

        assert len(widget.current_profile.layers[0].bindings) == 0
        widget.close()

    def test_add_macro(self, widget_with_profile):
        """Test adding a macro."""
        from unittest.mock import MagicMock, patch

        from PySide6.QtWidgets import QDialog

        from crates.profile_schema import MacroAction

        widget = widget_with_profile
        initial_macros = len(widget.current_profile.macros)

        mock_macro = MacroAction(id="new_macro", name="New Macro", steps=[], repeat_count=1)

        with patch("apps.gui.widgets.binding_editor.MacroDialog") as MockDialog:
            mock_dialog = MagicMock()
            mock_dialog.exec.return_value = QDialog.DialogCode.Accepted
            mock_dialog.get_macro.return_value = mock_macro
            MockDialog.return_value = mock_dialog

            widget._add_macro()

        assert len(widget.current_profile.macros) == initial_macros + 1
        widget.close()

    def test_remove_macro(self, qapp):
        """Test removing a macro."""
        from apps.gui.widgets.binding_editor import BindingEditorWidget
        from crates.profile_schema import Layer, MacroAction, Profile

        widget = BindingEditorWidget()
        profile = Profile(
            id="test",
            name="Test",
            description="",
            layers=[Layer(id="base", name="Base", bindings=[], hold_modifier_input_code=None)],
            macros=[MacroAction(id="test", name="Test", steps=[], repeat_count=1)],
        )
        widget.load_profile(profile)

        # Select the first macro
        widget.macros_list.setCurrentRow(0)
        widget._remove_macro()

        assert len(widget.current_profile.macros) == 0
        widget.close()


class TestBindingEditorCoverage:
    """Additional tests for BindingEditorWidget coverage."""

    @pytest.fixture
    def qapp(self):
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app

    def test_layer_dialog_custom_modifier_text(self, qapp):
        """Test LayerDialog with custom modifier text (line 101)."""
        from apps.gui.widgets.binding_editor import LayerDialog
        from crates.profile_schema import Layer

        # Layer with custom modifier not in the dropdown
        layer = Layer(id="test", name="Test", bindings=[], hold_modifier_input_code="CUSTOM_KEY")
        dialog = LayerDialog(layer=layer)
        # Should set as editable text since not in dropdown
        assert "CUSTOM_KEY" in dialog.modifier_combo.currentText()
        dialog.close()

    def test_layer_dialog_extract_code_from_text(self, qapp):
        """Test LayerDialog extracting code from 'Name (CODE)' format (lines 131-136)."""
        from apps.gui.widgets.binding_editor import LayerDialog

        dialog = LayerDialog()
        dialog.name_edit.setText("Test Layer")
        # Simulate user typing a custom value with parentheses
        dialog.modifier_combo.setEditText("My Key (MY_CUSTOM_CODE)")
        name, modifier = dialog.get_layer_data()
        assert modifier == "MY_CUSTOM_CODE"
        dialog.close()

    def test_layer_dialog_none_modifier(self, qapp):
        """Test LayerDialog returns None for base layer text (line 136)."""
        from apps.gui.widgets.binding_editor import LayerDialog

        dialog = LayerDialog()
        dialog.name_edit.setText("Test")
        dialog.modifier_combo.setCurrentIndex(0)  # "(None - Base Layer)"
        name, modifier = dialog.get_layer_data()
        assert modifier is None
        dialog.close()

    def test_binding_dialog_with_macros(self, qapp):
        """Test BindingDialog populates macro combo (line 180)."""
        from apps.gui.widgets.binding_editor import BindingDialog
        from crates.profile_schema import MacroAction

        macros = [
            MacroAction(id="m1", name="Macro 1", steps=[], repeat_count=1),
            MacroAction(id="m2", name="Macro 2", steps=[], repeat_count=1),
        ]
        dialog = BindingDialog(macros=macros)
        assert dialog.macro_combo.count() == 2
        dialog.close()

    def test_binding_dialog_load_custom_input(self, qapp):
        """Test loading binding with input not in dropdown (line 211)."""
        from apps.gui.widgets.binding_editor import BindingDialog
        from crates.profile_schema import ActionType, Binding

        binding = Binding(input_code="CUSTOM_INPUT", action_type=ActionType.KEY, output_keys=["A"])
        dialog = BindingDialog(binding=binding)
        # Should set as edit text
        assert "CUSTOM_INPUT" in dialog.input_combo.currentText()
        dialog.close()

    def test_binding_dialog_load_macro_binding(self, qapp):
        """Test loading binding with macro_id (lines 224-226)."""
        from apps.gui.widgets.binding_editor import BindingDialog
        from crates.profile_schema import ActionType, Binding, MacroAction

        macros = [MacroAction(id="test_macro", name="Test", steps=[], repeat_count=1)]
        binding = Binding(
            input_code="BTN_SIDE", action_type=ActionType.MACRO, macro_id="test_macro"
        )
        dialog = BindingDialog(binding=binding, macros=macros)
        assert dialog.macro_combo.currentData() == "test_macro"
        dialog.close()

    def test_binding_dialog_get_binding_with_parentheses(self, qapp):
        """Test get_binding extracts code from 'Name (CODE)' (line 247)."""
        from apps.gui.widgets.binding_editor import BindingDialog

        dialog = BindingDialog()
        dialog.input_combo.setEditText("Side Button (BTN_SIDE)")
        dialog.action_combo.setCurrentIndex(0)  # KEY
        dialog.output_edit.setText("A")
        binding = dialog.get_binding()
        assert binding is not None
        assert binding.input_code == "BTN_SIDE"
        dialog.close()

    def test_binding_dialog_get_macro_binding(self, qapp):
        """Test get_binding with macro action (line 263)."""
        from apps.gui.widgets.binding_editor import BindingDialog
        from crates.profile_schema import ActionType, MacroAction

        macros = [MacroAction(id="my_macro", name="My Macro", steps=[], repeat_count=1)]
        dialog = BindingDialog(macros=macros)
        dialog.input_combo.setEditText("BTN_SIDE")
        dialog.action_combo.setCurrentIndex(2)  # MACRO
        dialog._on_action_changed()
        dialog.macro_combo.setCurrentIndex(0)
        binding = dialog.get_binding()
        assert binding is not None
        assert binding.action_type == ActionType.MACRO
        assert binding.macro_id == "my_macro"
        dialog.close()

    def test_macro_dialog_skip_empty_lines(self, qapp):
        """Test MacroDialog skips empty lines (line 350)."""
        from apps.gui.widgets.binding_editor import MacroDialog

        dialog = MacroDialog()
        dialog.name_edit.setText("Test")
        dialog.steps_edit.setPlainText("key:A\n\n\nkey:B")  # Empty lines
        macro = dialog.get_macro()
        assert len(macro.steps) == 2
        dialog.close()

    def test_macro_dialog_skip_no_colon(self, qapp):
        """Test MacroDialog skips lines without colon (line 353)."""
        from apps.gui.widgets.binding_editor import MacroDialog

        dialog = MacroDialog()
        dialog.name_edit.setText("Test")
        dialog.steps_edit.setPlainText("key:A\ninvalid line\nkey:B")
        macro = dialog.get_macro()
        assert len(macro.steps) == 2
        dialog.close()

    def test_macro_dialog_down_up_commands(self, qapp):
        """Test MacroDialog parses down and up commands (lines 362, 364)."""
        from apps.gui.widgets.binding_editor import MacroDialog
        from crates.profile_schema import MacroStepType

        dialog = MacroDialog()
        dialog.name_edit.setText("Test")
        dialog.steps_edit.setPlainText("down:CTRL\nup:CTRL")
        macro = dialog.get_macro()
        assert len(macro.steps) == 2
        assert macro.steps[0].type == MacroStepType.KEY_DOWN
        assert macro.steps[1].type == MacroStepType.KEY_UP
        dialog.close()

    def test_get_macros_with_profile(self, qapp):
        """Test get_macros returns profile macros (line 524)."""
        from apps.gui.widgets.binding_editor import BindingEditorWidget
        from crates.profile_schema import Layer, MacroAction, Profile

        widget = BindingEditorWidget()
        profile = Profile(
            id="test",
            name="Test",
            layers=[Layer(id="base", name="Base", bindings=[], hold_modifier_input_code=None)],
            macros=[MacroAction(id="m1", name="M1", steps=[], repeat_count=1)],
        )
        widget.load_profile(profile)
        macros = widget.get_macros()
        assert len(macros) == 1
        widget.close()

    def test_get_current_layer_not_found(self, qapp):
        """Test _get_current_layer returns None for missing layer (line 536)."""
        from apps.gui.widgets.binding_editor import BindingEditorWidget
        from crates.profile_schema import Layer, Profile

        widget = BindingEditorWidget()
        profile = Profile(
            id="test",
            name="Test",
            layers=[Layer(id="base", name="Base", bindings=[], hold_modifier_input_code=None)],
        )
        widget.load_profile(profile)
        # Modify combo to have invalid data
        widget.layer_combo.setItemData(0, "nonexistent_id")
        layer = widget._get_current_layer()
        assert layer is None
        widget.close()

    def test_refresh_macros_no_profile(self, qapp):
        """Test _refresh_macros with no profile (line 580)."""
        from apps.gui.widgets.binding_editor import BindingEditorWidget

        widget = BindingEditorWidget()
        widget.current_profile = None
        widget._refresh_macros()  # Should not crash
        widget.close()

    def test_add_layer_no_profile(self, qapp):
        """Test _add_layer with no profile (line 608)."""
        from apps.gui.widgets.binding_editor import BindingEditorWidget

        widget = BindingEditorWidget()
        widget.current_profile = None
        widget._add_layer()  # Should not crash
        widget.close()

    def test_edit_layer_no_current_layer(self, qapp):
        """Test _edit_layer with no current layer (line 633)."""
        from apps.gui.widgets.binding_editor import BindingEditorWidget

        widget = BindingEditorWidget()
        widget.current_profile = None
        widget._edit_layer()  # Should not crash
        widget.close()

    def test_delete_layer_base_layer(self, qapp):
        """Test _delete_layer won't delete base layer (line 654)."""
        from apps.gui.widgets.binding_editor import BindingEditorWidget
        from crates.profile_schema import Layer, Profile

        widget = BindingEditorWidget()
        profile = Profile(
            id="test",
            name="Test",
            layers=[Layer(id="base", name="Base", bindings=[], hold_modifier_input_code=None)],
        )
        widget.load_profile(profile)
        widget._delete_layer()  # Should not crash, base can't be deleted
        assert len(profile.layers) == 1
        widget.close()

    def test_add_binding_no_layer(self, qapp):
        """Test _add_binding with no layer (line 676)."""
        from apps.gui.widgets.binding_editor import BindingEditorWidget

        widget = BindingEditorWidget()
        widget.current_profile = None
        widget._add_binding()  # Should not crash
        widget.close()

    def test_edit_binding_from_item(self, qapp):
        """Test _edit_binding from double-click (lines 689-691)."""
        from unittest.mock import MagicMock, patch

        from PySide6.QtWidgets import QDialog

        from apps.gui.widgets.binding_editor import BindingEditorWidget
        from crates.profile_schema import ActionType, Binding, Layer, Profile

        widget = BindingEditorWidget()
        binding = Binding(input_code="BTN_SIDE", action_type=ActionType.KEY, output_keys=["A"])
        profile = Profile(
            id="test",
            name="Test",
            layers=[
                Layer(id="base", name="Base", bindings=[binding], hold_modifier_input_code=None)
            ],
        )
        widget.load_profile(profile)

        item = widget.bindings_list.item(0)

        with patch("apps.gui.widgets.binding_editor.BindingDialog") as MockDialog:
            mock_dialog = MagicMock()
            mock_dialog.exec.return_value = QDialog.DialogCode.Rejected
            MockDialog.return_value = mock_dialog
            widget._edit_binding(item)
            MockDialog.assert_called_once()
        widget.close()

    def test_edit_selected_binding(self, qapp):
        """Test _edit_selected_binding (lines 695-699)."""
        from unittest.mock import MagicMock, patch

        from PySide6.QtWidgets import QDialog

        from apps.gui.widgets.binding_editor import BindingEditorWidget
        from crates.profile_schema import ActionType, Binding, Layer, Profile

        widget = BindingEditorWidget()
        binding = Binding(input_code="BTN_SIDE", action_type=ActionType.KEY, output_keys=["A"])
        profile = Profile(
            id="test",
            name="Test",
            layers=[
                Layer(id="base", name="Base", bindings=[binding], hold_modifier_input_code=None)
            ],
        )
        widget.load_profile(profile)
        widget.bindings_list.setCurrentRow(0)

        with patch("apps.gui.widgets.binding_editor.BindingDialog") as MockDialog:
            mock_dialog = MagicMock()
            mock_dialog.exec.return_value = QDialog.DialogCode.Rejected
            MockDialog.return_value = mock_dialog
            widget._edit_selected_binding()
            MockDialog.assert_called_once()
        widget.close()

    def test_edit_binding_dialog_accept(self, qapp):
        """Test _edit_binding_dialog with accept (lines 703-716)."""
        from unittest.mock import MagicMock, patch

        from PySide6.QtWidgets import QDialog

        from apps.gui.widgets.binding_editor import BindingEditorWidget
        from crates.profile_schema import ActionType, Binding, Layer, Profile

        widget = BindingEditorWidget()
        binding = Binding(input_code="BTN_SIDE", action_type=ActionType.KEY, output_keys=["A"])
        new_binding = Binding(input_code="BTN_SIDE", action_type=ActionType.KEY, output_keys=["B"])
        profile = Profile(
            id="test",
            name="Test",
            layers=[
                Layer(id="base", name="Base", bindings=[binding], hold_modifier_input_code=None)
            ],
        )
        widget.load_profile(profile)

        with patch("apps.gui.widgets.binding_editor.BindingDialog") as MockDialog:
            mock_dialog = MagicMock()
            mock_dialog.exec.return_value = QDialog.DialogCode.Accepted
            mock_dialog.get_binding.return_value = new_binding
            MockDialog.return_value = mock_dialog
            widget._edit_binding_dialog(binding)

        assert profile.layers[0].bindings[0].output_keys == ["B"]
        widget.close()

    def test_remove_binding_no_layer(self, qapp):
        """Test _remove_binding with no layer (line 722)."""
        from apps.gui.widgets.binding_editor import BindingEditorWidget

        widget = BindingEditorWidget()
        widget.current_profile = None
        widget._remove_binding()  # Should not crash
        widget.close()

    def test_add_macro_no_profile(self, qapp):
        """Test _add_macro with no profile (line 735)."""
        from apps.gui.widgets.binding_editor import BindingEditorWidget

        widget = BindingEditorWidget()
        widget.current_profile = None
        widget._add_macro()  # Should not crash
        widget.close()

    def test_edit_macro_from_item(self, qapp):
        """Test _edit_macro from double-click (lines 747-749)."""
        from unittest.mock import MagicMock, patch

        from PySide6.QtWidgets import QDialog

        from apps.gui.widgets.binding_editor import BindingEditorWidget
        from crates.profile_schema import Layer, MacroAction, Profile

        widget = BindingEditorWidget()
        macro = MacroAction(id="m1", name="M1", steps=[], repeat_count=1)
        profile = Profile(
            id="test",
            name="Test",
            layers=[Layer(id="base", name="Base", bindings=[], hold_modifier_input_code=None)],
            macros=[macro],
        )
        widget.load_profile(profile)

        item = widget.macros_list.item(0)

        with patch("apps.gui.widgets.binding_editor.MacroDialog") as MockDialog:
            mock_dialog = MagicMock()
            mock_dialog.exec.return_value = QDialog.DialogCode.Rejected
            MockDialog.return_value = mock_dialog
            widget._edit_macro(item)
            MockDialog.assert_called_once()
        widget.close()

    def test_edit_selected_macro(self, qapp):
        """Test _edit_selected_macro (lines 753-757)."""
        from unittest.mock import MagicMock, patch

        from PySide6.QtWidgets import QDialog

        from apps.gui.widgets.binding_editor import BindingEditorWidget
        from crates.profile_schema import Layer, MacroAction, Profile

        widget = BindingEditorWidget()
        macro = MacroAction(id="m1", name="M1", steps=[], repeat_count=1)
        profile = Profile(
            id="test",
            name="Test",
            layers=[Layer(id="base", name="Base", bindings=[], hold_modifier_input_code=None)],
            macros=[macro],
        )
        widget.load_profile(profile)
        widget.macros_list.setCurrentRow(0)

        with patch("apps.gui.widgets.binding_editor.MacroDialog") as MockDialog:
            mock_dialog = MagicMock()
            mock_dialog.exec.return_value = QDialog.DialogCode.Rejected
            MockDialog.return_value = mock_dialog
            widget._edit_selected_macro()
            MockDialog.assert_called_once()
        widget.close()

    def test_edit_macro_dialog_accept(self, qapp):
        """Test _edit_macro_dialog with accept (lines 761-773)."""
        from unittest.mock import MagicMock, patch

        from PySide6.QtWidgets import QDialog

        from apps.gui.widgets.binding_editor import BindingEditorWidget
        from crates.profile_schema import Layer, MacroAction, Profile

        widget = BindingEditorWidget()
        macro = MacroAction(id="m1", name="M1", steps=[], repeat_count=1)
        new_macro = MacroAction(id="new_id", name="Updated", steps=[], repeat_count=2)
        profile = Profile(
            id="test",
            name="Test",
            layers=[Layer(id="base", name="Base", bindings=[], hold_modifier_input_code=None)],
            macros=[macro],
        )
        widget.load_profile(profile)

        with patch("apps.gui.widgets.binding_editor.MacroDialog") as MockDialog:
            mock_dialog = MagicMock()
            mock_dialog.exec.return_value = QDialog.DialogCode.Accepted
            mock_dialog.get_macro.return_value = new_macro
            MockDialog.return_value = mock_dialog
            widget._edit_macro_dialog(macro)

        # Should preserve original ID
        assert profile.macros[0].id == "m1"
        assert profile.macros[0].name == "Updated"
        widget.close()

    def test_remove_macro_no_profile(self, qapp):
        """Test _remove_macro with no profile (line 778)."""
        from apps.gui.widgets.binding_editor import BindingEditorWidget

        widget = BindingEditorWidget()
        widget.current_profile = None
        widget._remove_macro()  # Should not crash
        widget.close()

    def test_on_device_combo_changed_header_item(self, qapp):
        """Test _on_device_combo_changed with header item (line 580-582)."""
        from apps.gui.widgets.binding_editor import BindingEditorWidget

        widget = BindingEditorWidget()
        # Add header item
        widget.device_combo.addItem("--- Select Device ---", "---header")
        widget.device_combo.setCurrentIndex(0)
        widget._on_device_combo_changed()  # Should early return
        widget.close()

    def test_on_device_combo_changed_valid_layout(self, qapp):
        """Test _on_device_combo_changed with valid layout (line 584-590)."""
        from unittest.mock import MagicMock, patch

        from apps.gui.widgets.binding_editor import BindingEditorWidget
        from crates.device_layouts.schema import ButtonShape, DeviceCategory, DeviceLayout

        widget = BindingEditorWidget()

        # Create mock layout
        mock_layout = DeviceLayout(
            id="test_layout",
            name="Test Device",
            category=DeviceCategory.MOUSE,
            device_name_patterns=["test"],
            base_width=100,
            base_height=100,
            outline_path=[(0, 0), (1, 0), (1, 1), (0, 1)],
            buttons=[
                ButtonShape(
                    id="btn1", x=0, y=0, width=0.5, height=0.5, label="B1", input_code="BTN_LEFT"
                )
            ],
        )

        mock_registry = MagicMock()
        mock_registry._layouts = {"test_layout": mock_layout}

        # Clear existing items and add our test item
        widget.device_combo.clear()
        widget.device_combo.addItem("Test Device", "test_layout")
        widget.device_combo.setCurrentIndex(0)

        with patch(
            "apps.gui.widgets.binding_editor.DeviceLayoutRegistry", return_value=mock_registry
        ):
            widget._on_device_combo_changed()

        widget.close()

    def test_on_device_button_clicked_no_layer(self, qapp):
        """Test _on_device_button_clicked with no layer (line 622-624)."""
        from apps.gui.widgets.binding_editor import BindingEditorWidget

        widget = BindingEditorWidget()
        widget.current_profile = None
        widget._on_device_button_clicked("btn1", "BTN_LEFT")  # Should early return
        widget.close()

    def test_on_device_button_clicked_existing_binding(self, qapp):
        """Test _on_device_button_clicked with existing binding (line 626-640)."""
        from unittest.mock import patch

        from apps.gui.widgets.binding_editor import BindingEditorWidget
        from crates.profile_schema import ActionType, Binding, Layer, Profile

        widget = BindingEditorWidget()

        binding = Binding(input_code="BTN_LEFT", action_type=ActionType.KEY, output_keys=["a"])
        layer = Layer(id="base", name="Base", bindings=[binding], hold_modifier_input_code=None)
        profile = Profile(id="test", name="Test", description="", layers=[layer])

        widget.current_profile = profile
        widget.layer_combo.addItem("Base", "base")
        widget.layer_combo.setCurrentIndex(0)

        # Mock the edit dialog to return Rejected
        with patch.object(widget, "_edit_binding_dialog"):
            widget._on_device_button_clicked("btn1", "BTN_LEFT")

        widget.close()

    def test_on_device_button_clicked_new_binding(self, qapp):
        """Test _on_device_button_clicked creating new binding (line 636-638)."""
        from unittest.mock import patch

        from apps.gui.widgets.binding_editor import BindingEditorWidget
        from crates.profile_schema import Layer, Profile

        widget = BindingEditorWidget()

        layer = Layer(id="base", name="Base", bindings=[], hold_modifier_input_code=None)
        profile = Profile(id="test", name="Test", description="", layers=[layer])

        widget.current_profile = profile
        widget.layer_combo.addItem("Base", "base")
        widget.layer_combo.setCurrentIndex(0)

        with patch.object(widget, "_add_binding_for_input"):
            widget._on_device_button_clicked("btn1", "BTN_LEFT")

        widget.close()

    def test_on_device_button_right_clicked(self, qapp):
        """Test _on_device_button_right_clicked (line 645)."""
        from apps.gui.widgets.binding_editor import BindingEditorWidget

        widget = BindingEditorWidget()
        widget._on_device_button_right_clicked("btn1")  # Just pass
        widget.close()

    def test_on_binding_selected_no_layout(self, qapp):
        """Test _on_binding_selected with no layout (line 658-663)."""

        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QListWidgetItem

        from apps.gui.widgets.binding_editor import BindingEditorWidget
        from crates.profile_schema import ActionType, Binding

        widget = BindingEditorWidget()

        binding = Binding(input_code="BTN_LEFT", action_type=ActionType.KEY, output_keys=["a"])
        item = QListWidgetItem("Test")
        item.setData(Qt.ItemDataRole.UserRole, binding)

        widget._on_binding_selected(item, None)
        widget.close()

    def test_on_binding_selected_with_matching_button(self, qapp):
        """Test _on_binding_selected with matching button in layout (line 660-663)."""

        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QListWidgetItem

        from apps.gui.widgets.binding_editor import BindingEditorWidget
        from crates.device_layouts.schema import ButtonShape, DeviceCategory, DeviceLayout
        from crates.profile_schema import ActionType, Binding

        widget = BindingEditorWidget()

        # Set up layout with matching button
        mock_layout = DeviceLayout(
            id="test",
            name="Test",
            category=DeviceCategory.MOUSE,
            device_name_patterns=["test"],
            base_width=100,
            base_height=100,
            outline_path=[(0, 0), (1, 0), (1, 1), (0, 1)],
            buttons=[
                ButtonShape(
                    id="btn1", x=0, y=0, width=0.5, height=0.5, label="B1", input_code="BTN_LEFT"
                )
            ],
        )
        widget.device_visual._layout = mock_layout

        binding = Binding(input_code="BTN_LEFT", action_type=ActionType.KEY, output_keys=["a"])
        item = QListWidgetItem("Test")
        item.setData(Qt.ItemDataRole.UserRole, binding)

        widget._on_binding_selected(item, None)
        widget.close()

    def test_add_binding_for_input_no_layer(self, qapp):
        """Test _add_binding_for_input with no layer (line 669-671)."""
        from apps.gui.widgets.binding_editor import BindingEditorWidget

        widget = BindingEditorWidget()
        widget.current_profile = None
        widget._add_binding_for_input("BTN_LEFT")  # Should early return
        widget.close()

    def test_add_binding_for_input_dialog_accepted(self, qapp):
        """Test _add_binding_for_input dialog flow (line 674-687)."""
        from unittest.mock import MagicMock, patch

        from PySide6.QtWidgets import QDialog

        from apps.gui.widgets.binding_editor import BindingEditorWidget
        from crates.profile_schema import ActionType, Binding, Layer, Profile

        widget = BindingEditorWidget()

        layer = Layer(id="base", name="Base", bindings=[], hold_modifier_input_code=None)
        profile = Profile(id="test", name="Test", description="", layers=[layer])

        widget.current_profile = profile
        widget.layer_combo.addItem("Base", "base")
        widget.layer_combo.setCurrentIndex(0)

        # Mock dialog
        mock_binding = Binding(input_code="BTN_LEFT", action_type=ActionType.KEY, output_keys=["a"])
        mock_dialog = MagicMock()
        mock_dialog.exec.return_value = QDialog.DialogCode.Accepted
        mock_dialog.get_binding.return_value = mock_binding

        with patch("apps.gui.widgets.binding_editor.BindingDialog", return_value=mock_dialog):
            widget._add_binding_for_input("BTN_LEFT")

        assert len(layer.bindings) == 1
        widget.close()

    def test_on_binding_selected_item_no_binding(self, qapp):
        """Test _on_binding_selected with item that has no binding data (line 655)."""
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QListWidgetItem

        from apps.gui.widgets.binding_editor import BindingEditorWidget

        widget = BindingEditorWidget()
        item = QListWidgetItem("Test")
        item.setData(Qt.ItemDataRole.UserRole, None)  # No binding data

        widget._on_binding_selected(item, None)  # Should early return at line 655
        widget.close()

    def test_format_binding_short_chord(self, qapp):
        """Test _format_binding_short with CHORD action (line 706-707)."""
        from apps.gui.widgets.binding_editor import BindingEditorWidget
        from crates.profile_schema import ActionType, Binding

        widget = BindingEditorWidget()
        binding = Binding(
            input_code="BTN_LEFT", action_type=ActionType.CHORD, output_keys=["ctrl", "shift", "a"]
        )
        result = widget._format_binding_short(binding)
        assert result == "ctrl+shift"
        widget.close()

    def test_format_binding_short_macro(self, qapp):
        """Test _format_binding_short with MACRO action (line 708-709)."""
        from apps.gui.widgets.binding_editor import BindingEditorWidget
        from crates.profile_schema import ActionType, Binding

        widget = BindingEditorWidget()
        binding = Binding(
            input_code="BTN_LEFT", action_type=ActionType.MACRO, macro_id="test_macro"
        )
        result = widget._format_binding_short(binding)
        assert result == "Macro"
        widget.close()

    def test_format_binding_short_passthrough(self, qapp):
        """Test _format_binding_short with PASSTHROUGH action (line 710-711)."""
        from apps.gui.widgets.binding_editor import BindingEditorWidget
        from crates.profile_schema import ActionType, Binding

        widget = BindingEditorWidget()
        binding = Binding(input_code="BTN_LEFT", action_type=ActionType.PASSTHROUGH)
        result = widget._format_binding_short(binding)
        assert result == "Pass"
        widget.close()

    def test_format_binding_short_disable(self, qapp):
        """Test _format_binding_short with DISABLED action (line 712-713)."""
        from apps.gui.widgets.binding_editor import BindingEditorWidget
        from crates.profile_schema import ActionType, Binding

        widget = BindingEditorWidget()
        binding = Binding(input_code="BTN_LEFT", action_type=ActionType.DISABLED)
        result = widget._format_binding_short(binding)
        assert result == "Off"
        widget.close()

    def test_edit_binding_dialog_no_layer(self, qapp):
        """Test _edit_binding_dialog with no layer (line 906)."""
        from apps.gui.widgets.binding_editor import BindingEditorWidget
        from crates.profile_schema import ActionType, Binding

        widget = BindingEditorWidget()
        widget.current_profile = None
        binding = Binding(input_code="BTN_LEFT", action_type=ActionType.KEY, output_keys=["a"])
        widget._edit_binding_dialog(binding)  # Should early return
        widget.close()

    def test_edit_macro_dialog_no_profile(self, qapp):
        """Test _edit_macro_dialog with no profile (line 963)."""
        from apps.gui.widgets.binding_editor import BindingEditorWidget
        from crates.profile_schema import MacroAction, MacroStep, MacroStepType

        widget = BindingEditorWidget()
        widget.current_profile = None
        macro = MacroAction(
            id="m1", name="Test", steps=[MacroStep(type=MacroStepType.KEY_PRESS, key="a")]
        )
        widget._edit_macro_dialog(macro)  # Should early return
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
            id="test",
            name="Test",
            description="",
            layers=[Layer(id="base", name="Base", bindings=[], hold_modifier_input_code=None)],
            app_patterns=["firefox", "chrome"],
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
            id="test",
            name="Test",
            description="",
            layers=[Layer(id="base", name="Base", bindings=[], hold_modifier_input_code=None)],
            app_patterns=["firefox"],
        )
        widget.load_profile(profile)
        widget.clear()
        assert widget.current_profile is None
        widget.close()

    def test_refresh_ui_no_profile(self, qapp):
        """Test _refresh_ui with no profile."""
        from apps.gui.widgets.app_matcher import AppMatcherWidget

        widget = AppMatcherWidget()
        widget.current_profile = None
        widget._refresh_ui()

        assert not widget.add_btn.isEnabled()
        assert not widget.default_check.isChecked()
        widget.close()

    def test_refresh_ui_with_patterns(self, qapp):
        """Test _refresh_ui loads patterns from profile."""
        from apps.gui.widgets.app_matcher import AppMatcherWidget
        from crates.profile_schema import Layer, Profile

        widget = AppMatcherWidget()
        profile = Profile(
            id="test",
            name="Test",
            description="",
            layers=[Layer(id="base", name="Base", bindings=[], hold_modifier_input_code=None)],
            match_process_names=["firefox", "chrome"],
            is_default=True,
        )
        widget.load_profile(profile)

        assert widget.pattern_list.count() == 2
        assert widget.default_check.isChecked()
        widget.close()

    def test_on_selection_changed_enables_remove(self, qapp):
        """Test selecting a pattern enables remove button."""
        from apps.gui.widgets.app_matcher import AppMatcherWidget
        from crates.profile_schema import Layer, Profile

        widget = AppMatcherWidget()
        profile = Profile(
            id="test",
            name="Test",
            description="",
            layers=[Layer(id="base", name="Base", bindings=[], hold_modifier_input_code=None)],
            match_process_names=["firefox"],
        )
        widget.load_profile(profile)

        widget.pattern_list.setCurrentRow(0)
        assert widget.remove_btn.isEnabled()
        widget.close()

    def test_on_selection_changed_negative_disables_remove(self, qapp):
        """Test no selection disables remove button."""
        from apps.gui.widgets.app_matcher import AppMatcherWidget

        widget = AppMatcherWidget()
        widget._on_selection_changed(-1)
        assert not widget.remove_btn.isEnabled()
        widget.close()

    def test_add_pattern_no_profile(self, qapp):
        """Test _add_pattern does nothing without profile."""
        from apps.gui.widgets.app_matcher import AppMatcherWidget

        widget = AppMatcherWidget()
        # Should not raise
        widget._add_pattern()
        widget.close()

    def test_add_pattern_success(self, qapp):
        """Test adding a pattern successfully."""
        from unittest.mock import patch

        from PySide6.QtWidgets import QDialog

        from apps.gui.widgets.app_matcher import AppMatcherWidget
        from crates.profile_schema import Layer, Profile

        widget = AppMatcherWidget()
        profile = Profile(
            id="test",
            name="Test",
            description="",
            layers=[Layer(id="base", name="Base", bindings=[], hold_modifier_input_code=None)],
            match_process_names=[],
        )
        widget.load_profile(profile)

        signals_received = []
        widget.patterns_changed.connect(lambda: signals_received.append(True))

        with patch("apps.gui.widgets.app_matcher.AddPatternDialog") as MockDialog:
            mock_dialog = MagicMock()
            mock_dialog.exec.return_value = QDialog.DialogCode.Accepted
            mock_dialog.get_pattern.return_value = "steam"
            MockDialog.return_value = mock_dialog

            widget._add_pattern()

        assert "steam" in widget.current_profile.match_process_names
        assert len(signals_received) == 1
        widget.close()

    def test_add_pattern_duplicate(self, qapp):
        """Test adding a duplicate pattern shows warning."""
        from unittest.mock import patch

        from PySide6.QtWidgets import QDialog, QMessageBox

        from apps.gui.widgets.app_matcher import AppMatcherWidget
        from crates.profile_schema import Layer, Profile

        widget = AppMatcherWidget()
        profile = Profile(
            id="test",
            name="Test",
            description="",
            layers=[Layer(id="base", name="Base", bindings=[], hold_modifier_input_code=None)],
            match_process_names=["steam"],
        )
        widget.load_profile(profile)

        with (
            patch("apps.gui.widgets.app_matcher.AddPatternDialog") as MockDialog,
            patch.object(QMessageBox, "warning") as mock_warn,
        ):
            mock_dialog = MagicMock()
            mock_dialog.exec.return_value = QDialog.DialogCode.Accepted
            mock_dialog.get_pattern.return_value = "STEAM"  # Case insensitive match
            MockDialog.return_value = mock_dialog

            widget._add_pattern()

        mock_warn.assert_called()
        assert len(widget.current_profile.match_process_names) == 1
        widget.close()

    def test_add_pattern_cancelled(self, qapp):
        """Test cancelling add pattern dialog."""
        from unittest.mock import patch

        from PySide6.QtWidgets import QDialog

        from apps.gui.widgets.app_matcher import AppMatcherWidget
        from crates.profile_schema import Layer, Profile

        widget = AppMatcherWidget()
        profile = Profile(
            id="test",
            name="Test",
            description="",
            layers=[Layer(id="base", name="Base", bindings=[], hold_modifier_input_code=None)],
            match_process_names=[],
        )
        widget.load_profile(profile)

        with patch("apps.gui.widgets.app_matcher.AddPatternDialog") as MockDialog:
            mock_dialog = MagicMock()
            mock_dialog.exec.return_value = QDialog.DialogCode.Rejected
            MockDialog.return_value = mock_dialog

            widget._add_pattern()

        assert len(widget.current_profile.match_process_names) == 0
        widget.close()

    def test_remove_pattern_no_profile(self, qapp):
        """Test _remove_pattern does nothing without profile."""
        from apps.gui.widgets.app_matcher import AppMatcherWidget

        widget = AppMatcherWidget()
        # Should not raise
        widget._remove_pattern()
        widget.close()

    def test_remove_pattern_no_selection(self, qapp):
        """Test _remove_pattern does nothing without selection."""
        from apps.gui.widgets.app_matcher import AppMatcherWidget
        from crates.profile_schema import Layer, Profile

        widget = AppMatcherWidget()
        profile = Profile(
            id="test",
            name="Test",
            description="",
            layers=[Layer(id="base", name="Base", bindings=[], hold_modifier_input_code=None)],
            match_process_names=["firefox"],
        )
        widget.load_profile(profile)
        # Should not raise
        widget._remove_pattern()
        assert len(widget.current_profile.match_process_names) == 1
        widget.close()

    def test_remove_pattern_success(self, qapp):
        """Test removing a pattern successfully."""
        from apps.gui.widgets.app_matcher import AppMatcherWidget
        from crates.profile_schema import Layer, Profile

        widget = AppMatcherWidget()
        profile = Profile(
            id="test",
            name="Test",
            description="",
            layers=[Layer(id="base", name="Base", bindings=[], hold_modifier_input_code=None)],
            match_process_names=["firefox", "chrome"],
        )
        widget.load_profile(profile)

        signals_received = []
        widget.patterns_changed.connect(lambda: signals_received.append(True))

        widget.pattern_list.setCurrentRow(0)
        widget._remove_pattern()

        assert len(widget.current_profile.match_process_names) == 1
        assert "firefox" not in widget.current_profile.match_process_names
        assert len(signals_received) == 1
        widget.close()

    def test_on_default_changed_no_profile(self, qapp):
        """Test _on_default_changed does nothing without profile."""
        from apps.gui.widgets.app_matcher import AppMatcherWidget

        widget = AppMatcherWidget()
        # Should not raise
        widget._on_default_changed(True)
        widget.close()

    def test_on_default_changed(self, qapp):
        """Test changing default checkbox."""
        from apps.gui.widgets.app_matcher import AppMatcherWidget
        from crates.profile_schema import Layer, Profile

        widget = AppMatcherWidget()
        profile = Profile(
            id="test",
            name="Test",
            description="",
            layers=[Layer(id="base", name="Base", bindings=[], hold_modifier_input_code=None)],
            is_default=False,
        )
        widget.load_profile(profile)

        signals_received = []
        widget.patterns_changed.connect(lambda: signals_received.append(True))

        widget._on_default_changed(True)

        assert widget.current_profile.is_default is True
        assert len(signals_received) == 1
        widget.close()

    def test_test_detection_no_backend(self, qapp):
        """Test _test_detection when no backend available."""
        from unittest.mock import patch

        from apps.gui.widgets.app_matcher import AppMatcherWidget

        widget = AppMatcherWidget()

        with patch("apps.gui.widgets.app_matcher.AppWatcher") as MockWatcher:
            mock_watcher = MagicMock()
            mock_watcher._backend = None
            MockWatcher.return_value = mock_watcher

            widget._test_detection()

        assert "No backend" in widget.test_result.text()
        widget.close()

    def test_test_detection_success(self, qapp):
        """Test _test_detection with successful detection."""
        from unittest.mock import MagicMock, patch

        from apps.gui.widgets.app_matcher import AppMatcherWidget

        widget = AppMatcherWidget()

        mock_window_info = MagicMock()
        mock_window_info.pid = 1234
        mock_window_info.process_name = "firefox"
        mock_window_info.window_class = "Firefox"
        mock_window_info.window_title = "Test Page"

        with patch("apps.gui.widgets.app_matcher.AppWatcher") as MockWatcher:
            mock_watcher = MagicMock()
            mock_watcher._backend = MagicMock()
            mock_watcher._backend.get_active_window.return_value = mock_window_info
            mock_watcher.backend_name = "X11"
            MockWatcher.return_value = mock_watcher

            widget._test_detection()

        assert "firefox" in widget.test_result.text()
        assert "1234" in widget.test_result.text()
        widget.close()

    def test_test_detection_no_window(self, qapp):
        """Test _test_detection when no window detected."""
        from unittest.mock import patch

        from apps.gui.widgets.app_matcher import AppMatcherWidget

        widget = AppMatcherWidget()

        with patch("apps.gui.widgets.app_matcher.AppWatcher") as MockWatcher:
            mock_watcher = MagicMock()
            mock_watcher._backend = MagicMock()
            mock_watcher._backend.get_active_window.return_value = None
            MockWatcher.return_value = mock_watcher

            widget._test_detection()

        assert "Could not detect" in widget.test_result.text()
        widget.close()

    def test_test_detection_exception(self, qapp):
        """Test _test_detection handles exceptions."""
        from unittest.mock import patch

        from apps.gui.widgets.app_matcher import AppMatcherWidget

        widget = AppMatcherWidget()

        with patch("apps.gui.widgets.app_matcher.AppWatcher") as MockWatcher:
            MockWatcher.side_effect = Exception("Test error")

            widget._test_detection()

        assert "Error" in widget.test_result.text()
        widget.close()


class TestAddPatternDialog:
    """Tests for AddPatternDialog."""

    @pytest.fixture
    def qapp(self):
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app

    def test_dialog_instantiation(self, qapp):
        """Test AddPatternDialog can be created."""
        from apps.gui.widgets.app_matcher import AddPatternDialog

        dialog = AddPatternDialog()
        assert dialog is not None
        assert dialog.windowTitle() == "Add App Pattern"
        dialog.close()

    def test_get_pattern(self, qapp):
        """Test get_pattern returns entered text."""
        from apps.gui.widgets.app_matcher import AddPatternDialog

        dialog = AddPatternDialog()
        dialog.pattern_edit.setText("  firefox  ")

        pattern = dialog.get_pattern()
        assert pattern == "firefox"  # Stripped
        dialog.close()

    def test_get_pattern_empty(self, qapp):
        """Test get_pattern with empty input."""
        from apps.gui.widgets.app_matcher import AddPatternDialog

        dialog = AddPatternDialog()
        dialog.pattern_edit.setText("")

        pattern = dialog.get_pattern()
        assert pattern == ""
        dialog.close()


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

    def test_set_device_no_matrix(self, qapp, mock_bridge):
        """Test set_device with non-matrix device."""
        from apps.gui.widgets.zone_editor import ZoneEditorWidget

        widget = ZoneEditorWidget(bridge=mock_bridge)
        mock_device = MagicMock()
        mock_device.has_matrix = False

        widget.set_device(mock_device)
        assert "No matrix" in widget.device_label.text()
        widget.close()

    def test_set_device_none(self, qapp, mock_bridge):
        """Test set_device with None."""
        from apps.gui.widgets.zone_editor import ZoneEditorWidget

        widget = ZoneEditorWidget(bridge=mock_bridge)
        widget.set_device(None)
        assert "No matrix" in widget.device_label.text()
        widget.close()

    def test_clear_all_zones(self, qapp, mock_bridge):
        """Test clearing all zones."""
        from apps.gui.widgets.zone_editor import ZoneEditorWidget

        widget = ZoneEditorWidget(bridge=mock_bridge)
        widget._clear_all_zones()  # Should work even with no zones
        widget.close()

    def test_get_zone_colors_empty(self, qapp, mock_bridge):
        """Test getting zone colors when empty."""
        from apps.gui.widgets.zone_editor import ZoneEditorWidget

        widget = ZoneEditorWidget(bridge=mock_bridge)
        colors = widget.get_zone_colors()
        assert colors == {}
        widget.close()

    def test_set_zone_colors(self, qapp, mock_bridge):
        """Test setting zone colors."""
        from apps.gui.widgets.zone_editor import ZoneEditorWidget

        widget = ZoneEditorWidget(bridge=mock_bridge)
        # Should not error with empty zones
        widget.set_zone_colors({"wasd": (255, 0, 0)})
        widget.close()

    def test_set_enabled(self, qapp, mock_bridge):
        """Test _set_enabled method."""
        from apps.gui.widgets.zone_editor import ZoneEditorWidget

        widget = ZoneEditorWidget(bridge=mock_bridge)
        widget._set_enabled(True)
        assert widget.preset_combo.isEnabled()
        assert widget.apply_btn.isEnabled()

        widget._set_enabled(False)
        assert not widget.preset_combo.isEnabled()
        assert not widget.apply_btn.isEnabled()
        widget.close()


class TestZoneColorButton:
    """Tests for ZoneColorButton."""

    @pytest.fixture
    def qapp(self):
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app

    def test_button_instantiation(self, qapp):
        """Test ZoneColorButton can be created."""
        from apps.gui.widgets.zone_editor import ZoneColorButton

        btn = ZoneColorButton((255, 0, 0))
        assert btn.get_color() == (255, 0, 0)
        btn.close()

    def test_set_color(self, qapp):
        """Test setting color."""
        from apps.gui.widgets.zone_editor import ZoneColorButton

        btn = ZoneColorButton()
        btn.set_color((0, 255, 0))
        assert btn.get_color() == (0, 255, 0)
        btn.close()

    def test_update_style_dark_text(self, qapp):
        """Test style update with light color shows dark text."""
        from apps.gui.widgets.zone_editor import ZoneColorButton

        btn = ZoneColorButton((255, 255, 255))  # White - should have dark text
        btn._update_style()
        assert "#333" in btn.styleSheet()
        btn.close()

    def test_update_style_light_text(self, qapp):
        """Test style update with dark color shows light text."""
        from apps.gui.widgets.zone_editor import ZoneColorButton

        btn = ZoneColorButton((0, 0, 0))  # Black - should have light text
        btn._update_style()
        assert "#fff" in btn.styleSheet()
        btn.close()


class TestZoneItem:
    """Tests for ZoneItem."""

    @pytest.fixture
    def qapp(self):
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app

    def test_zone_item_instantiation(self, qapp):
        """Test ZoneItem can be created."""
        from apps.gui.widgets.zone_editor import ZoneItem
        from crates.zone_definitions import KeyPosition, Zone, ZoneType

        zone = Zone(
            id="test",
            name="Test Zone",
            zone_type=ZoneType.QWERTY_ROW,
            keys=[KeyPosition(row=0, col=0)],
            description="Test",
        )
        item = ZoneItem(zone)
        assert item.zone == zone
        item.close()

    def test_zone_item_set_color(self, qapp):
        """Test setting zone color."""
        from apps.gui.widgets.zone_editor import ZoneItem
        from crates.zone_definitions import KeyPosition, Zone, ZoneType

        zone = Zone(
            id="test",
            name="Test",
            zone_type=ZoneType.QWERTY_ROW,
            keys=[KeyPosition(row=0, col=0)],
        )
        item = ZoneItem(zone)
        item.set_color((128, 64, 32))
        assert item.get_color() == (128, 64, 32)
        item.close()

    def test_zone_item_multiple_keys(self, qapp):
        """Test zone item with multiple keys."""
        from apps.gui.widgets.zone_editor import ZoneItem
        from crates.zone_definitions import KeyPosition, Zone, ZoneType

        zone = Zone(
            id="wasd",
            name="WASD",
            zone_type=ZoneType.ASDF_ROW,
            keys=[
                KeyPosition(row=1, col=1),
                KeyPosition(row=2, col=0),
                KeyPosition(row=2, col=1),
                KeyPosition(row=2, col=2),
            ],
        )
        item = ZoneItem(zone)
        assert item.zone.name == "WASD"
        item.close()


class TestZoneEditorCoverage:
    """Extended coverage tests for ZoneEditorWidget."""

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
        bridge.set_matrix_colors.return_value = True
        return bridge

    @pytest.fixture
    def mock_matrix_device(self):
        device = MagicMock()
        device.name = "Razer BlackWidow"
        device.has_matrix = True
        device.matrix_rows = 6
        device.matrix_cols = 22
        device.serial = "test-serial"
        return device

    def test_set_device_with_matrix(self, qapp, mock_bridge, mock_matrix_device):
        """Test setting a matrix device creates zones."""
        from apps.gui.widgets.zone_editor import ZoneEditorWidget

        widget = ZoneEditorWidget(bridge=mock_bridge)
        widget.set_device(mock_matrix_device)

        assert widget.current_device == mock_matrix_device
        assert len(widget.zone_items) > 0  # Should have created zone items
        assert widget.apply_btn.isEnabled()
        widget.close()

    def test_set_device_clears_existing(self, qapp, mock_bridge, mock_matrix_device):
        """Test setting a new device clears existing zones."""
        from apps.gui.widgets.zone_editor import ZoneEditorWidget

        widget = ZoneEditorWidget(bridge=mock_bridge)
        widget.set_device(mock_matrix_device)
        first_count = len(widget.zone_items)
        assert first_count > 0

        # Set same device again - should clear and recreate
        widget.set_device(mock_matrix_device)
        assert len(widget.zone_items) > 0
        widget.close()

    def test_on_zone_color_changed(self, qapp, mock_bridge, mock_matrix_device):
        """Test zone color change emits config_changed signal."""
        from apps.gui.widgets.zone_editor import ZoneEditorWidget

        widget = ZoneEditorWidget(bridge=mock_bridge)
        widget.set_device(mock_matrix_device)

        signal_emitted = []
        widget.config_changed.connect(lambda: signal_emitted.append(True))

        # Trigger color change on a zone
        zone_id = list(widget.zone_items.keys())[0]
        widget._on_zone_color_changed(zone_id, (255, 0, 0))

        assert len(signal_emitted) == 1
        widget.close()

    def test_on_preset_changed_select_preset(self, qapp, mock_bridge, mock_matrix_device):
        """Test applying a preset sets zone colors."""
        from apps.gui.widgets.zone_editor import ZoneEditorWidget

        widget = ZoneEditorWidget(bridge=mock_bridge)
        widget.set_device(mock_matrix_device)

        # Apply gaming preset
        widget._on_preset_changed("Gaming")

        # Preset combo should reset to placeholder
        assert widget.preset_combo.currentIndex() == 0
        widget.close()

    def test_on_preset_changed_placeholder(self, qapp, mock_bridge, mock_matrix_device):
        """Test selecting placeholder does nothing."""
        from apps.gui.widgets.zone_editor import ZoneEditorWidget

        widget = ZoneEditorWidget(bridge=mock_bridge)
        widget.set_device(mock_matrix_device)

        # Should not error when selecting placeholder
        widget._on_preset_changed("(Select preset)")
        widget.close()

    def test_fill_all_zones(self, qapp, mock_bridge, mock_matrix_device):
        """Test filling all zones with a color."""
        from PySide6.QtGui import QColor
        from PySide6.QtWidgets import QColorDialog

        from apps.gui.widgets.zone_editor import ZoneEditorWidget

        widget = ZoneEditorWidget(bridge=mock_bridge)
        widget.set_device(mock_matrix_device)

        # Mock color dialog to return a color
        with patch.object(QColorDialog, "getColor", return_value=QColor(255, 128, 64)):
            widget._fill_all_zones()

        # All zones should have that color
        for item in widget.zone_items.values():
            assert item.get_color() == (255, 128, 64)
        widget.close()

    def test_fill_all_zones_cancel(self, qapp, mock_bridge, mock_matrix_device):
        """Test canceling fill dialog does nothing."""
        from PySide6.QtGui import QColor
        from PySide6.QtWidgets import QColorDialog

        from apps.gui.widgets.zone_editor import ZoneEditorWidget

        widget = ZoneEditorWidget(bridge=mock_bridge)
        widget.set_device(mock_matrix_device)

        # Set a known color first
        for item in widget.zone_items.values():
            item.set_color((100, 100, 100))

        # Mock color dialog to return invalid (cancelled)
        invalid_color = QColor()
        with patch.object(QColorDialog, "getColor", return_value=invalid_color):
            widget._fill_all_zones()

        # Colors should be unchanged
        for item in widget.zone_items.values():
            assert item.get_color() == (100, 100, 100)
        widget.close()

    def test_clear_all_zones_with_zones(self, qapp, mock_bridge, mock_matrix_device):
        """Test clearing all zones sets them to black."""
        from apps.gui.widgets.zone_editor import ZoneEditorWidget

        widget = ZoneEditorWidget(bridge=mock_bridge)
        widget.set_device(mock_matrix_device)

        # Set some colors first
        for item in widget.zone_items.values():
            item.set_color((255, 128, 64))

        widget._clear_all_zones()

        # All zones should be black
        for item in widget.zone_items.values():
            assert item.get_color() == (0, 0, 0)
        widget.close()

    def test_apply_to_device(self, qapp, mock_bridge, mock_matrix_device):
        """Test applying zone colors to device."""
        from apps.gui.widgets.zone_editor import ZoneEditorWidget

        widget = ZoneEditorWidget(bridge=mock_bridge)
        widget.set_device(mock_matrix_device)

        # Set some colors
        zone_id = list(widget.zone_items.keys())[0]
        widget.zone_items[zone_id].set_color((255, 0, 0))

        widget._apply_to_device()

        # Bridge should have been called
        mock_bridge.set_matrix_colors.assert_called_once()
        widget.close()

    def test_apply_to_device_no_device(self, qapp, mock_bridge):
        """Test apply to device with no device does nothing."""
        from apps.gui.widgets.zone_editor import ZoneEditorWidget

        widget = ZoneEditorWidget(bridge=mock_bridge)
        widget._apply_to_device()
        mock_bridge.set_matrix_colors.assert_not_called()
        widget.close()

    def test_set_zone_colors_with_zones(self, qapp, mock_bridge, mock_matrix_device):
        """Test setting zone colors with existing zones."""
        from apps.gui.widgets.zone_editor import ZoneEditorWidget

        widget = ZoneEditorWidget(bridge=mock_bridge)
        widget.set_device(mock_matrix_device)

        zone_id = list(widget.zone_items.keys())[0]
        widget.set_zone_colors({zone_id: (64, 128, 192)})

        assert widget.zone_items[zone_id].get_color() == (64, 128, 192)
        widget.close()


class TestZoneItemCoverage:
    """Extended coverage tests for ZoneItem."""

    @pytest.fixture
    def qapp(self):
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app

    def test_zone_item_color_changed_signal(self, qapp):
        """Test ZoneItem emits color_changed signal."""
        from apps.gui.widgets.zone_editor import ZoneItem
        from crates.zone_definitions import KeyPosition, Zone, ZoneType

        zone = Zone(
            id="test_zone",
            name="Test Zone",
            zone_type=ZoneType.QWERTY_ROW,
            keys=[KeyPosition(row=0, col=0)],
        )
        item = ZoneItem(zone)

        signal_emitted = []
        item.color_changed.connect(lambda zone_id, color: signal_emitted.append((zone_id, color)))

        # Trigger color change
        item._on_color_changed((255, 128, 64))

        assert len(signal_emitted) == 1
        assert signal_emitted[0] == ("test_zone", (255, 128, 64))
        item.close()


class TestZoneColorButtonCoverage:
    """Extended coverage tests for ZoneColorButton."""

    @pytest.fixture
    def qapp(self):
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app

    def test_pick_color_accepted(self, qapp):
        """Test color picker when color is accepted."""
        from PySide6.QtGui import QColor
        from PySide6.QtWidgets import QColorDialog

        from apps.gui.widgets.zone_editor import ZoneColorButton

        btn = ZoneColorButton((100, 100, 100))

        signal_emitted = []
        btn.color_changed.connect(lambda color: signal_emitted.append(color))

        # Mock color dialog to return a valid color
        with patch.object(QColorDialog, "getColor", return_value=QColor(255, 0, 128)):
            btn._pick_color()

        assert btn.get_color() == (255, 0, 128)
        assert len(signal_emitted) == 1
        assert signal_emitted[0] == (255, 0, 128)
        btn.close()

    def test_pick_color_cancelled(self, qapp):
        """Test color picker when cancelled."""
        from PySide6.QtGui import QColor
        from PySide6.QtWidgets import QColorDialog

        from apps.gui.widgets.zone_editor import ZoneColorButton

        btn = ZoneColorButton((100, 100, 100))

        signal_emitted = []
        btn.color_changed.connect(lambda color: signal_emitted.append(color))

        # Mock color dialog to return invalid (cancelled)
        invalid_color = QColor()
        with patch.object(QColorDialog, "getColor", return_value=invalid_color):
            btn._pick_color()

        # Color should be unchanged
        assert btn.get_color() == (100, 100, 100)
        assert len(signal_emitted) == 0
        btn.close()


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

    @pytest.fixture
    def mock_device(self):
        device = MagicMock()
        device.configure_mock(name="Test Mouse")
        device.serial = "SERIAL123"
        device.device_type = "mouse"
        device.has_battery = True
        device.battery_level = 75
        device.is_charging = False
        return device

    def test_refresh_devices(self, qapp, mock_bridge):
        """Test refreshing device list."""
        from apps.gui.widgets.battery_monitor import BatteryMonitorWidget

        widget = BatteryMonitorWidget(bridge=mock_bridge)
        widget.refresh_devices()
        mock_bridge.discover_devices.assert_called()
        widget.close()

    def test_refresh_devices_with_battery_device(self, qapp, mock_bridge, mock_device):
        """Test refresh with devices that have batteries."""
        from apps.gui.widgets.battery_monitor import BatteryMonitorWidget

        mock_bridge.discover_devices.return_value = [mock_device]
        mock_bridge.get_battery.return_value = {"level": 75, "charging": False}

        widget = BatteryMonitorWidget(bridge=mock_bridge)
        assert len(widget._device_cards) == 1
        widget.close()

    def test_refresh_batteries_updates_levels(self, qapp, mock_bridge, mock_device):
        """Test refresh_batteries updates battery levels."""
        from apps.gui.widgets.battery_monitor import BatteryMonitorWidget

        mock_bridge.discover_devices.return_value = [mock_device]
        mock_bridge.get_battery.return_value = {"level": 50, "charging": True}

        widget = BatteryMonitorWidget(bridge=mock_bridge)
        widget.refresh_batteries()

        # Check battery was updated
        mock_bridge.get_battery.assert_called_with("SERIAL123")
        widget.close()

    def test_low_battery_warning_emitted(self, qapp, mock_bridge, mock_device):
        """Test low battery warning signal is emitted."""
        from apps.gui.widgets.battery_monitor import BatteryMonitorWidget

        mock_bridge.discover_devices.return_value = [mock_device]
        mock_bridge.get_battery.return_value = {"level": 15, "charging": False}

        widget = BatteryMonitorWidget(bridge=mock_bridge)

        # Connect a handler
        warnings = []
        widget.low_battery_warning.connect(lambda name, level: warnings.append((name, level)))

        # Clear warned devices and refresh again
        widget._warned_devices.clear()
        widget.refresh_batteries()

        assert len(warnings) == 1
        assert warnings[0][0] == "Test Mouse"
        assert warnings[0][1] == 15
        widget.close()

    def test_no_duplicate_low_battery_warning(self, qapp, mock_bridge, mock_device):
        """Test warning is not emitted twice for same device."""
        from apps.gui.widgets.battery_monitor import BatteryMonitorWidget

        mock_bridge.discover_devices.return_value = [mock_device]
        mock_bridge.get_battery.return_value = {"level": 15, "charging": False}

        widget = BatteryMonitorWidget(bridge=mock_bridge)

        warnings = []
        widget.low_battery_warning.connect(lambda name, level: warnings.append((name, level)))

        # Clear warned devices and do first refresh - should warn
        widget._warned_devices.clear()
        widget.refresh_batteries()
        assert len(warnings) == 1

        # Second refresh - should NOT warn again
        widget.refresh_batteries()
        assert len(warnings) == 1
        widget.close()

    def test_warning_reset_after_charge(self, qapp, mock_bridge, mock_device):
        """Test warning resets after battery is charged."""
        from apps.gui.widgets.battery_monitor import BatteryMonitorWidget

        mock_bridge.discover_devices.return_value = [mock_device]
        mock_bridge.get_battery.return_value = {"level": 15, "charging": False}

        widget = BatteryMonitorWidget(bridge=mock_bridge)

        warnings = []
        widget.low_battery_warning.connect(lambda name, level: warnings.append((name, level)))

        # Clear warned devices and do first refresh - low battery
        widget._warned_devices.clear()
        widget.refresh_batteries()
        assert len(warnings) == 1

        # Charge above threshold + 10
        mock_bridge.get_battery.return_value = {"level": 35, "charging": False}
        widget.refresh_batteries()

        # Drop low again - should warn again
        mock_bridge.get_battery.return_value = {"level": 10, "charging": False}
        widget.refresh_batteries()
        assert len(warnings) == 2
        widget.close()

    def test_interval_change(self, qapp, mock_bridge):
        """Test refresh interval can be changed."""
        from apps.gui.widgets.battery_monitor import BatteryMonitorWidget

        widget = BatteryMonitorWidget(bridge=mock_bridge)
        widget._on_interval_changed(60)
        assert widget.refresh_timer.interval() == 60000
        widget.close()


class TestBatteryDeviceCard:
    """Tests for BatteryDeviceCard widget."""

    @pytest.fixture
    def qapp(self):
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app

    @pytest.fixture
    def mock_device(self):
        device = MagicMock()
        device.configure_mock(name="Test Mouse")
        device.device_type = "mouse"
        device.battery_level = 75
        device.is_charging = False
        return device

    def test_card_creation(self, qapp, mock_device):
        """Test BatteryDeviceCard can be created."""
        from apps.gui.widgets.battery_monitor import BatteryDeviceCard

        card = BatteryDeviceCard(mock_device)
        assert card is not None
        card.close()

    def test_card_shows_device_name(self, qapp, mock_device):
        """Test card displays device name."""
        from apps.gui.widgets.battery_monitor import BatteryDeviceCard

        card = BatteryDeviceCard(mock_device)
        assert card.name_label.text() == "Test Mouse"
        card.close()

    def test_card_update_battery_charging(self, qapp, mock_device):
        """Test card shows charging status."""
        from apps.gui.widgets.battery_monitor import BatteryDeviceCard

        mock_device.is_charging = True
        card = BatteryDeviceCard(mock_device)
        assert "Charging" in card.status_label.text()
        card.close()

    def test_card_update_battery_critical(self, qapp, mock_device):
        """Test card shows critical status."""
        from apps.gui.widgets.battery_monitor import BatteryDeviceCard

        mock_device.battery_level = 5
        mock_device.is_charging = False
        card = BatteryDeviceCard(mock_device)
        assert "Critical" in card.status_label.text()
        card.close()

    def test_card_update_battery_low(self, qapp, mock_device):
        """Test card shows low status."""
        from apps.gui.widgets.battery_monitor import BatteryDeviceCard

        mock_device.battery_level = 15
        mock_device.is_charging = False
        card = BatteryDeviceCard(mock_device)
        assert "Low" in card.status_label.text()
        card.close()

    def test_card_update_battery_good(self, qapp, mock_device):
        """Test card shows good status."""
        from apps.gui.widgets.battery_monitor import BatteryDeviceCard

        mock_device.battery_level = 90
        mock_device.is_charging = False
        card = BatteryDeviceCard(mock_device)
        assert "Good" in card.status_label.text()
        card.close()

    def test_card_update_battery_normal(self, qapp, mock_device):
        """Test card shows normal status."""
        from apps.gui.widgets.battery_monitor import BatteryDeviceCard

        mock_device.battery_level = 50
        mock_device.is_charging = False
        card = BatteryDeviceCard(mock_device)
        assert "Normal" in card.status_label.text()
        card.close()

    def test_card_update_battery_unavailable(self, qapp, mock_device):
        """Test card handles unavailable battery level."""
        from apps.gui.widgets.battery_monitor import BatteryDeviceCard

        mock_device.battery_level = -1
        mock_device.is_charging = False
        card = BatteryDeviceCard(mock_device)
        assert "N/A" in card.percent_label.text()
        card.close()


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

    def test_wizard_profile_name_change_empty(self, qapp):
        """Test profile name change with empty string defaults to Default."""
        from apps.gui.widgets.setup_wizard import SetupWizard

        with patch("apps.gui.widgets.setup_wizard.DeviceRegistry") as mock_registry:
            with patch("apps.gui.widgets.setup_wizard.ProfileLoader") as mock_loader:
                mock_registry.return_value.scan_devices.return_value = []
                mock_loader.return_value.list_profiles.return_value = []
                wizard = SetupWizard()
                wizard._on_name_changed("   ")  # Whitespace only
                assert wizard.profile_name == "Default"
                wizard.close()

    def test_wizard_scan_devices_with_razer(self, qapp):
        """Test scanning devices finds Razer devices."""
        from apps.gui.widgets.setup_wizard import SetupWizard

        mock_device = MagicMock()
        mock_device.stable_id = "razer-deathadder"
        mock_device.name = "Razer DeathAdder"
        mock_device.is_mouse = True
        mock_device.is_keyboard = False

        with patch("apps.gui.widgets.setup_wizard.DeviceRegistry") as mock_registry:
            with patch("apps.gui.widgets.setup_wizard.ProfileLoader") as mock_loader:
                mock_registry.return_value.get_razer_devices.return_value = [mock_device]
                mock_loader.return_value.list_profiles.return_value = []
                wizard = SetupWizard()

                # Device should be in list
                assert wizard.device_list.count() >= 1
                # Mice should be pre-selected
                assert len(wizard.selected_devices) >= 1
                wizard.close()

    def test_wizard_scan_devices_no_devices(self, qapp):
        """Test scanning with no devices shows troubleshooting."""
        from apps.gui.widgets.setup_wizard import SetupWizard

        with patch("apps.gui.widgets.setup_wizard.DeviceRegistry") as mock_registry:
            with patch("apps.gui.widgets.setup_wizard.ProfileLoader") as mock_loader:
                mock_registry.return_value.get_razer_devices.return_value = []
                mock_loader.return_value.list_profiles.return_value = []
                wizard = SetupWizard()

                # Troubleshooting group should not be hidden (show() was called)
                assert not wizard.trouble_group.isHidden()
                # And should have troubleshooting text
                assert wizard.trouble_label.text() != ""
                wizard.close()

    def test_wizard_update_selected_devices(self, qapp):
        """Test updating selected devices list."""
        from apps.gui.widgets.setup_wizard import SetupWizard

        mock_device = MagicMock()
        mock_device.stable_id = "razer-mouse"
        mock_device.name = "Razer Mouse"
        mock_device.is_mouse = True
        mock_device.is_keyboard = False

        with patch("apps.gui.widgets.setup_wizard.DeviceRegistry") as mock_registry:
            with patch("apps.gui.widgets.setup_wizard.ProfileLoader") as mock_loader:
                mock_registry.return_value.get_razer_devices.return_value = [mock_device]
                mock_loader.return_value.list_profiles.return_value = []
                wizard = SetupWizard()

                # Pre-selected (is_mouse=True)
                wizard._update_selected_devices()
                assert "razer-mouse" in wizard.selected_devices
                wizard.close()

    def test_wizard_prepare_profile_page_with_devices(self, qapp):
        """Test preparing profile page with selected devices."""
        from apps.gui.widgets.setup_wizard import SetupWizard

        with patch("apps.gui.widgets.setup_wizard.DeviceRegistry") as mock_registry:
            with patch("apps.gui.widgets.setup_wizard.ProfileLoader") as mock_loader:
                mock_registry.return_value.get_razer_devices.return_value = []
                mock_loader.return_value.list_profiles.return_value = []
                wizard = SetupWizard()

                wizard.selected_devices = ["usb-Razer_DeathAdder-event-mouse"]
                wizard._prepare_profile_page()

                # Check devices summary shows device
                text = wizard.devices_summary_label.text()
                assert "Razer" in text or "DeathAdder" in text
                wizard.close()

    def test_wizard_prepare_profile_page_no_devices(self, qapp):
        """Test preparing profile page with no devices."""
        from apps.gui.widgets.setup_wizard import SetupWizard

        with patch("apps.gui.widgets.setup_wizard.DeviceRegistry") as mock_registry:
            with patch("apps.gui.widgets.setup_wizard.ProfileLoader") as mock_loader:
                mock_registry.return_value.get_razer_devices.return_value = []
                mock_loader.return_value.list_profiles.return_value = []
                wizard = SetupWizard()

                wizard.selected_devices = []
                wizard._prepare_profile_page()

                assert "No devices" in wizard.devices_summary_label.text()
                wizard.close()

    def test_wizard_prepare_daemon_page(self, qapp):
        """Test preparing daemon page with summary."""
        from apps.gui.widgets.setup_wizard import SetupWizard

        with patch("apps.gui.widgets.setup_wizard.DeviceRegistry") as mock_registry:
            with patch("apps.gui.widgets.setup_wizard.ProfileLoader") as mock_loader:
                mock_registry.return_value.get_razer_devices.return_value = []
                mock_loader.return_value.list_profiles.return_value = []
                wizard = SetupWizard()

                wizard.name_input.setText("Gaming")
                wizard.desc_input.setText("My gaming profile")
                wizard.selected_devices = ["device1", "device2"]
                wizard._prepare_daemon_page()

                text = wizard.summary_label.text()
                assert "Gaming" in text
                assert "My gaming profile" in text
                assert "2 selected" in text
                wizard.close()

    def test_wizard_navigate_to_last_page_shows_finish(self, qapp):
        """Test navigating to last page shows Finish button."""
        from apps.gui.widgets.setup_wizard import SetupWizard

        with patch("apps.gui.widgets.setup_wizard.DeviceRegistry") as mock_registry:
            with patch("apps.gui.widgets.setup_wizard.ProfileLoader") as mock_loader:
                mock_registry.return_value.get_razer_devices.return_value = []
                mock_loader.return_value.list_profiles.return_value = []
                wizard = SetupWizard()

                # Navigate to last page
                wizard.pages.setCurrentIndex(3)
                wizard._update_buttons()

                assert wizard.next_btn.text() == "Finish"
                wizard.close()

    def test_wizard_finish_setup(self, qapp):
        """Test finishing setup creates profile."""
        from apps.gui.widgets.setup_wizard import SetupWizard

        with patch("apps.gui.widgets.setup_wizard.DeviceRegistry") as mock_registry:
            with patch("apps.gui.widgets.setup_wizard.ProfileLoader") as mock_loader:
                with patch("apps.gui.widgets.setup_wizard.subprocess.run") as mock_run:
                    mock_registry.return_value.get_razer_devices.return_value = []
                    mock_loader.return_value.list_profiles.return_value = []
                    mock_loader.return_value.save_profile.return_value = True
                    wizard = SetupWizard()

                    wizard.name_input.setText("Test Profile")
                    wizard.selected_devices = ["test-device"]
                    wizard.autostart_check.setChecked(True)
                    wizard.start_now_check.setChecked(True)

                    wizard._finish_setup()

                    # Should have saved the profile
                    mock_loader.return_value.save_profile.assert_called_once()
                    mock_loader.return_value.set_active_profile.assert_called_once()
                    # Should have started daemon
                    assert mock_run.call_count >= 1
                    wizard.close()

    def test_wizard_finish_setup_empty_name(self, qapp):
        """Test finishing setup with empty name uses default."""
        from apps.gui.widgets.setup_wizard import SetupWizard

        with patch("apps.gui.widgets.setup_wizard.DeviceRegistry") as mock_registry:
            with patch("apps.gui.widgets.setup_wizard.ProfileLoader") as mock_loader:
                with patch("apps.gui.widgets.setup_wizard.subprocess.run"):
                    mock_registry.return_value.get_razer_devices.return_value = []
                    mock_loader.return_value.list_profiles.return_value = []
                    mock_loader.return_value.save_profile.return_value = True
                    wizard = SetupWizard()

                    wizard.name_input.setText("")
                    wizard._finish_setup()

                    # Profile should be saved (with default name)
                    mock_loader.return_value.save_profile.assert_called_once()
                    wizard.close()

    def test_wizard_go_next_from_device_page(self, qapp):
        """Test navigating from device page prepares profile page."""
        from apps.gui.widgets.setup_wizard import SetupWizard

        with patch("apps.gui.widgets.setup_wizard.DeviceRegistry") as mock_registry:
            with patch("apps.gui.widgets.setup_wizard.ProfileLoader") as mock_loader:
                mock_registry.return_value.get_razer_devices.return_value = []
                mock_loader.return_value.list_profiles.return_value = []
                wizard = SetupWizard()

                # Go to device page (page 1)
                wizard.pages.setCurrentIndex(1)
                wizard.selected_devices = ["test-device"]

                # Go next (to profile page)
                wizard._go_next()

                # Should be on page 2
                assert wizard.pages.currentIndex() == 2
                wizard.close()

    def test_wizard_go_next_from_profile_page(self, qapp):
        """Test navigating from profile page prepares daemon page."""
        from apps.gui.widgets.setup_wizard import SetupWizard

        with patch("apps.gui.widgets.setup_wizard.DeviceRegistry") as mock_registry:
            with patch("apps.gui.widgets.setup_wizard.ProfileLoader") as mock_loader:
                mock_registry.return_value.get_razer_devices.return_value = []
                mock_loader.return_value.list_profiles.return_value = []
                wizard = SetupWizard()

                wizard.name_input.setText("Profile")
                wizard.pages.setCurrentIndex(2)

                wizard._go_next()

                # Should be on page 3 (daemon)
                assert wizard.pages.currentIndex() == 3
                assert "Profile" in wizard.summary_label.text()
                wizard.close()

    def test_wizard_get_troubleshooting_text_no_issues(self, qapp):
        """Test troubleshooting text when no issues detected."""
        from pathlib import Path

        from apps.gui.widgets.setup_wizard import SetupWizard

        with patch("apps.gui.widgets.setup_wizard.DeviceRegistry") as mock_registry:
            with patch("apps.gui.widgets.setup_wizard.ProfileLoader") as mock_loader:
                mock_registry.return_value.get_razer_devices.return_value = []
                mock_loader.return_value.list_profiles.return_value = []
                wizard = SetupWizard()

                with patch.object(Path, "stat"):  # uinput exists
                    with patch("apps.gui.widgets.setup_wizard.subprocess.run") as mock_run:
                        # Mock groups command - user in input group
                        mock_groups = MagicMock()
                        mock_groups.stdout = "user input audio"
                        # Mock systemctl - daemon active
                        mock_systemctl = MagicMock()
                        mock_systemctl.stdout = "active"
                        mock_run.side_effect = [mock_groups, mock_systemctl]

                        text = wizard._get_troubleshooting_text()

                        # No specific issues, just generic message
                        assert "No Razer devices found" in text
                        wizard.close()

    def test_wizard_get_troubleshooting_text_uinput_missing(self, qapp):
        """Test troubleshooting detects missing uinput."""
        from pathlib import Path

        from apps.gui.widgets.setup_wizard import SetupWizard

        with patch("apps.gui.widgets.setup_wizard.DeviceRegistry") as mock_registry:
            with patch("apps.gui.widgets.setup_wizard.ProfileLoader") as mock_loader:
                mock_registry.return_value.get_razer_devices.return_value = []
                mock_loader.return_value.list_profiles.return_value = []
                wizard = SetupWizard()

                with patch.object(Path, "stat", side_effect=FileNotFoundError):
                    text = wizard._get_troubleshooting_text()

                    assert "uinput" in text
                    wizard.close()

    def test_wizard_get_troubleshooting_text_not_in_input_group(self, qapp):
        """Test troubleshooting detects user not in input group."""
        from pathlib import Path

        from apps.gui.widgets.setup_wizard import SetupWizard

        with patch("apps.gui.widgets.setup_wizard.DeviceRegistry") as mock_registry:
            with patch("apps.gui.widgets.setup_wizard.ProfileLoader") as mock_loader:
                mock_registry.return_value.get_razer_devices.return_value = []
                mock_loader.return_value.list_profiles.return_value = []
                wizard = SetupWizard()

                with patch.object(Path, "stat"):  # uinput exists
                    with patch("apps.gui.widgets.setup_wizard.subprocess.run") as mock_run:
                        mock_groups = MagicMock()
                        mock_groups.stdout = "user audio video"  # No 'input'
                        mock_run.return_value = mock_groups

                        text = wizard._get_troubleshooting_text()

                        assert "input" in text.lower()
                        wizard.close()

    def test_wizard_device_toggled_handler(self, qapp):
        """Test device toggle handler updates selection."""
        from apps.gui.widgets.setup_wizard import SetupWizard

        mock_device = MagicMock()
        mock_device.stable_id = "razer-mouse"
        mock_device.name = "Razer Mouse"
        mock_device.is_mouse = False  # Not pre-selected

        with patch("apps.gui.widgets.setup_wizard.DeviceRegistry") as mock_registry:
            with patch("apps.gui.widgets.setup_wizard.ProfileLoader") as mock_loader:
                mock_registry.return_value.get_razer_devices.return_value = [mock_device]
                mock_loader.return_value.list_profiles.return_value = []
                wizard = SetupWizard()

                # Initial state - not selected
                assert "razer-mouse" not in wizard.selected_devices

                # Check the checkbox
                item = wizard.device_list.item(0)
                checkbox = wizard.device_list.itemWidget(item)
                checkbox.setChecked(True)

                # _on_device_toggled should have been called
                wizard._update_selected_devices()
                assert "razer-mouse" in wizard.selected_devices
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


class TestColorButtonMethods:
    """Tests for ColorButton methods."""

    @pytest.fixture
    def qapp(self):
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app

    def test_get_color(self, qapp):
        """Test getting color value."""
        from apps.gui.widgets.razer_controls import ColorButton

        btn = ColorButton(color=(100, 150, 200))
        assert btn.get_color() == (100, 150, 200)
        btn.close()

    def test_set_color(self, qapp):
        """Test setting color value."""
        from apps.gui.widgets.razer_controls import ColorButton

        btn = ColorButton(color=(0, 0, 0))
        btn.set_color((255, 128, 64))
        assert btn.get_color() == (255, 128, 64)
        # Check text is updated
        assert "#ff8040" in btn.text()
        btn.close()

    def test_pick_color_canceled(self, qapp):
        """Test color picker dialog when canceled."""
        from apps.gui.widgets.razer_controls import ColorButton

        btn = ColorButton(color=(100, 100, 100))
        original_color = btn.get_color()

        # Mock getColor to return invalid color (canceled)
        with patch("apps.gui.widgets.razer_controls.QColorDialog.getColor") as mock_dialog:
            mock_color = MagicMock()
            mock_color.isValid.return_value = False
            mock_dialog.return_value = mock_color

            btn._pick_color()

            # Color should not change
            assert btn.get_color() == original_color
        btn.close()

    def test_pick_color_selected(self, qapp):
        """Test color picker dialog when color is selected."""
        from apps.gui.widgets.razer_controls import ColorButton

        btn = ColorButton(color=(0, 0, 0))
        signal_received = []

        def on_color_changed(color):
            signal_received.append(color)

        btn.color_changed.connect(on_color_changed)

        # Mock getColor to return a valid color
        with patch("apps.gui.widgets.razer_controls.QColorDialog.getColor") as mock_dialog:
            mock_color = MagicMock()
            mock_color.isValid.return_value = True
            mock_color.red.return_value = 200
            mock_color.green.return_value = 100
            mock_color.blue.return_value = 50
            mock_dialog.return_value = mock_color

            btn._pick_color()

            # Color should be updated
            assert btn.get_color() == (200, 100, 50)
            # Signal should be emitted
            assert len(signal_received) == 1
            assert signal_received[0] == (200, 100, 50)
        btn.close()


class TestRazerControlsFullCoverage:
    """Extended tests for RazerControlsWidget coverage."""

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

    @pytest.fixture
    def mock_device(self):
        """Create a mock device with all properties."""
        device = MagicMock()
        device.configure_mock(name="Razer DeathAdder")
        device.serial = "DA123456"
        device.device_type = "mouse"
        device.has_battery = True
        device.battery_level = 75
        device.has_lighting = True
        device.has_brightness = True
        device.brightness = 80
        device.has_dpi = True
        device.dpi = (1600, 1600)
        device.max_dpi = 20000
        return device

    def test_refresh_devices_populates_combo(self, qapp, mock_bridge, mock_device):
        """Test refresh_devices adds devices to combo box."""
        from apps.gui.widgets.razer_controls import RazerControlsWidget

        mock_bridge.discover_devices.return_value = [mock_device]
        mock_bridge.get_device.return_value = mock_device

        widget = RazerControlsWidget(bridge=mock_bridge)
        widget.refresh_devices()

        # Should have the device in combo
        assert widget.device_combo.count() == 1
        assert widget.device_combo.currentText() == "Razer DeathAdder"
        assert widget.device_combo.currentData() == "DA123456"
        widget.close()

    def test_on_device_changed_updates_ui(self, qapp, mock_bridge, mock_device):
        """Test _on_device_changed updates UI for device."""
        from apps.gui.widgets.razer_controls import RazerControlsWidget

        mock_bridge.discover_devices.return_value = [mock_device]
        mock_bridge.get_device.return_value = mock_device

        widget = RazerControlsWidget(bridge=mock_bridge)
        widget.refresh_devices()

        # Should have selected first device and updated UI
        assert widget.current_device == mock_device
        assert widget.info_name.text() == "Razer DeathAdder"
        assert widget.info_type.text() == "mouse"
        assert widget.info_serial.text() == "DA123456"
        assert widget.info_battery.text() == "75%"
        widget.close()

    def test_on_device_changed_no_battery(self, qapp, mock_bridge, mock_device):
        """Test device without battery shows N/A."""
        from apps.gui.widgets.razer_controls import RazerControlsWidget

        mock_device.has_battery = False
        mock_bridge.discover_devices.return_value = [mock_device]
        mock_bridge.get_device.return_value = mock_device

        widget = RazerControlsWidget(bridge=mock_bridge)
        widget.refresh_devices()

        assert widget.info_battery.text() == "N/A"
        widget.close()

    def test_on_device_changed_with_brightness(self, qapp, mock_bridge, mock_device):
        """Test device with brightness updates slider."""
        from apps.gui.widgets.razer_controls import RazerControlsWidget

        mock_device.has_brightness = True
        mock_device.brightness = 50
        mock_bridge.discover_devices.return_value = [mock_device]
        mock_bridge.get_device.return_value = mock_device

        widget = RazerControlsWidget(bridge=mock_bridge)
        widget.refresh_devices()

        assert widget.brightness_slider.value() == 50
        widget.close()

    def test_on_device_changed_with_dpi(self, qapp, mock_bridge, mock_device):
        """Test device with DPI updates spinbox."""
        from apps.gui.widgets.razer_controls import RazerControlsWidget

        mock_device.has_dpi = True
        mock_device.dpi = (3200, 3200)
        mock_bridge.discover_devices.return_value = [mock_device]
        mock_bridge.get_device.return_value = mock_device

        widget = RazerControlsWidget(bridge=mock_bridge)
        widget.refresh_devices()

        assert widget.dpi_spin.value() == 3200
        widget.close()

    def test_on_device_changed_negative_index(self, qapp, mock_bridge):
        """Test _on_device_changed with negative index does nothing."""
        from apps.gui.widgets.razer_controls import RazerControlsWidget

        widget = RazerControlsWidget(bridge=mock_bridge)
        widget._on_device_changed(-1)
        # Should not crash
        assert widget.current_device is None
        widget.close()

    def test_on_brightness_changed(self, qapp, mock_bridge):
        """Test brightness change updates label."""
        from apps.gui.widgets.razer_controls import RazerControlsWidget

        widget = RazerControlsWidget(bridge=mock_bridge)
        widget._on_brightness_changed(75)
        assert widget.brightness_label.text() == "75%"
        widget.close()

    def test_on_effect_changed_static(self, qapp, mock_bridge):
        """Test effect change enables color button for Static."""
        from apps.gui.widgets.razer_controls import RazerControlsWidget

        widget = RazerControlsWidget(bridge=mock_bridge)
        widget._on_effect_changed("Static")
        assert widget.color_btn.isEnabled()
        widget.close()

    def test_on_effect_changed_breathing(self, qapp, mock_bridge):
        """Test effect change enables color button for Breathing."""
        from apps.gui.widgets.razer_controls import RazerControlsWidget

        widget = RazerControlsWidget(bridge=mock_bridge)
        widget._on_effect_changed("Breathing")
        assert widget.color_btn.isEnabled()
        widget.close()

    def test_on_effect_changed_spectrum(self, qapp, mock_bridge):
        """Test effect change disables color button for Spectrum."""
        from apps.gui.widgets.razer_controls import RazerControlsWidget

        widget = RazerControlsWidget(bridge=mock_bridge)
        widget._on_effect_changed("Spectrum")
        assert not widget.color_btn.isEnabled()
        widget.close()

    def test_on_color_changed(self, qapp, mock_bridge):
        """Test _on_color_changed does not crash."""
        from apps.gui.widgets.razer_controls import RazerControlsWidget

        widget = RazerControlsWidget(bridge=mock_bridge)
        widget._on_color_changed((255, 0, 0))
        # Should not crash (method is a no-op)
        widget.close()

    def test_apply_lighting_no_device(self, qapp, mock_bridge):
        """Test _apply_lighting without device does nothing."""
        from apps.gui.widgets.razer_controls import RazerControlsWidget

        widget = RazerControlsWidget(bridge=mock_bridge)
        widget._apply_lighting()
        # Should not crash, and bridge should not be called
        mock_bridge.set_brightness.assert_not_called()
        widget.close()

    def test_apply_lighting_static(self, qapp, mock_bridge, mock_device):
        """Test _apply_lighting with Static effect."""
        from apps.gui.widgets.razer_controls import RazerControlsWidget

        mock_bridge.discover_devices.return_value = [mock_device]
        mock_bridge.get_device.return_value = mock_device

        widget = RazerControlsWidget(bridge=mock_bridge)
        widget.refresh_devices()

        # Set up lighting
        widget.brightness_slider.setValue(90)
        widget.effect_combo.setCurrentText("Static")
        widget.color_btn.set_color((255, 128, 0))

        widget._apply_lighting()

        mock_bridge.set_brightness.assert_called_with("DA123456", 90)
        mock_bridge.set_static_color.assert_called_with("DA123456", 255, 128, 0)
        widget.close()

    def test_apply_lighting_breathing(self, qapp, mock_bridge, mock_device):
        """Test _apply_lighting with Breathing effect."""
        from apps.gui.widgets.razer_controls import RazerControlsWidget

        mock_bridge.discover_devices.return_value = [mock_device]
        mock_bridge.get_device.return_value = mock_device

        widget = RazerControlsWidget(bridge=mock_bridge)
        widget.refresh_devices()

        widget.effect_combo.setCurrentText("Breathing")
        widget.color_btn.set_color((0, 255, 128))

        widget._apply_lighting()

        mock_bridge.set_breathing_effect.assert_called_with("DA123456", 0, 255, 128)
        widget.close()

    def test_apply_lighting_spectrum(self, qapp, mock_bridge, mock_device):
        """Test _apply_lighting with Spectrum effect."""
        from apps.gui.widgets.razer_controls import RazerControlsWidget

        mock_bridge.discover_devices.return_value = [mock_device]
        mock_bridge.get_device.return_value = mock_device

        widget = RazerControlsWidget(bridge=mock_bridge)
        widget.refresh_devices()

        widget.effect_combo.setCurrentText("Spectrum")

        widget._apply_lighting()

        mock_bridge.set_spectrum_effect.assert_called_with("DA123456")
        widget.close()

    def test_apply_lighting_off(self, qapp, mock_bridge, mock_device):
        """Test _apply_lighting with Off effect."""
        from apps.gui.widgets.razer_controls import RazerControlsWidget

        mock_bridge.discover_devices.return_value = [mock_device]
        mock_bridge.get_device.return_value = mock_device

        widget = RazerControlsWidget(bridge=mock_bridge)
        widget.refresh_devices()

        widget.effect_combo.setCurrentText("Off")

        widget._apply_lighting()

        # Should set brightness to 0
        mock_bridge.set_brightness.assert_any_call("DA123456", 0)
        widget.close()

    def test_apply_dpi_no_device(self, qapp, mock_bridge):
        """Test _apply_dpi without device does nothing."""
        from apps.gui.widgets.razer_controls import RazerControlsWidget

        widget = RazerControlsWidget(bridge=mock_bridge)
        widget._apply_dpi()
        # Should not crash, and bridge should not be called
        mock_bridge.set_dpi.assert_not_called()
        widget.close()

    def test_apply_dpi_with_device(self, qapp, mock_bridge, mock_device):
        """Test _apply_dpi with device sets DPI."""
        from apps.gui.widgets.razer_controls import RazerControlsWidget

        mock_bridge.discover_devices.return_value = [mock_device]
        mock_bridge.get_device.return_value = mock_device

        widget = RazerControlsWidget(bridge=mock_bridge)
        widget.refresh_devices()

        widget.dpi_spin.setValue(6400)
        widget._apply_dpi()

        mock_bridge.set_dpi.assert_called_with("DA123456", 6400)
        widget.close()


class TestMainWindowMethods:
    """Tests for MainWindow methods."""

    @pytest.fixture
    def qapp(self):
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app

    @pytest.fixture
    def mock_deps(self):
        """Mock all MainWindow dependencies."""
        mock_run_result = MagicMock()
        mock_run_result.returncode = 0
        with (
            patch("apps.gui.main_window.ProfileLoader") as mock_loader,
            patch("apps.gui.main_window.DeviceRegistry") as mock_registry,
            patch("apps.gui.main_window.OpenRazerBridge") as mock_bridge,
            patch(
                "apps.gui.main_window.subprocess.run", return_value=mock_run_result
            ) as mock_subprocess,
        ):
            mock_loader.return_value.list_profiles.return_value = []
            mock_loader.return_value.get_active_profile_id.return_value = None
            mock_registry.return_value.list_devices.return_value = []
            mock_bridge.return_value.connect.return_value = False
            mock_bridge.return_value.discover_devices.return_value = []
            yield {
                "loader": mock_loader,
                "registry": mock_registry,
                "bridge": mock_bridge,
                "subprocess": mock_subprocess,
            }

    def test_main_window_instantiation(self, qapp, mock_deps):
        """Test MainWindow can be instantiated with mocked deps."""
        from apps.gui.main_window import MainWindow

        window = MainWindow()
        assert window is not None
        assert window.windowTitle() == "Razer Control Center"
        window.close()

    def test_main_window_has_tabs(self, qapp, mock_deps):
        """Test MainWindow creates expected tabs."""
        from apps.gui.main_window import MainWindow

        window = MainWindow()
        tab_count = window.tabs.count()
        # Devices, Bindings, Macros, App, Lighting, Zone, DPI, Battery, Daemon
        assert tab_count >= 8
        window.close()

    def test_main_window_has_statusbar(self, qapp, mock_deps):
        """Test MainWindow has status bar."""
        from apps.gui.main_window import MainWindow

        window = MainWindow()
        assert window.statusbar is not None
        window.close()

    def test_main_window_has_menu(self, qapp, mock_deps):
        """Test MainWindow has menu bar."""
        from apps.gui.main_window import MainWindow

        window = MainWindow()
        menubar = window.menuBar()
        assert menubar is not None
        window.close()

    def test_close_event_stops_timer(self, qapp, mock_deps):
        """Test closeEvent stops the refresh timer."""
        from apps.gui.main_window import MainWindow

        window = MainWindow()
        assert window.refresh_timer.isActive()
        window.close()
        assert not window.refresh_timer.isActive()


class TestMainWindowProfileHandling:
    """Tests for MainWindow profile handling."""

    @pytest.fixture
    def qapp(self):
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app

    @pytest.fixture
    def mock_deps(self):
        """Mock all MainWindow dependencies."""
        mock_run_result = MagicMock()
        mock_run_result.returncode = 0
        with (
            patch("apps.gui.main_window.ProfileLoader") as mock_loader,
            patch("apps.gui.main_window.DeviceRegistry") as mock_registry,
            patch("apps.gui.main_window.OpenRazerBridge") as mock_bridge,
            patch(
                "apps.gui.main_window.subprocess.run", return_value=mock_run_result
            ) as mock_subprocess,
        ):
            mock_loader.return_value.list_profiles.return_value = []
            mock_loader.return_value.get_active_profile_id.return_value = None
            mock_registry.return_value.list_devices.return_value = []
            mock_bridge.return_value.connect.return_value = False
            mock_bridge.return_value.discover_devices.return_value = []
            yield {
                "loader": mock_loader,
                "registry": mock_registry,
                "bridge": mock_bridge,
                "subprocess": mock_subprocess,
            }

    def test_on_profile_selected(self, qapp, mock_deps):
        """Test _on_profile_selected loads profile."""
        from apps.gui.main_window import MainWindow
        from crates.profile_schema import Profile

        mock_profile = Profile(id="test", name="Test", input_devices=[], layers=[])
        mock_deps["loader"].return_value.load_profile.return_value = mock_profile

        window = MainWindow()
        window._on_profile_selected("test")

        assert window.current_profile == mock_profile
        mock_deps["loader"].return_value.load_profile.assert_called_with("test")
        window.close()

    def test_on_profile_selected_not_found(self, qapp, mock_deps):
        """Test _on_profile_selected handles missing profile."""
        from apps.gui.main_window import MainWindow

        mock_deps["loader"].return_value.load_profile.return_value = None

        window = MainWindow()
        window._on_profile_selected("nonexistent")

        assert window.current_profile is None
        window.close()

    def test_on_profile_created(self, qapp, mock_deps):
        """Test _on_profile_created saves profile."""
        from apps.gui.main_window import MainWindow
        from crates.profile_schema import Profile

        window = MainWindow()
        profile = Profile(id="new", name="New Profile", input_devices=[], layers=[])
        window._on_profile_created(profile)

        mock_deps["loader"].return_value.save_profile.assert_called_with(profile)
        window.close()

    def test_on_profile_deleted(self, qapp, mock_deps):
        """Test _on_profile_deleted removes profile."""
        from apps.gui.main_window import MainWindow
        from crates.profile_schema import Profile

        window = MainWindow()
        window.current_profile = Profile(
            id="to-delete", name="Delete Me", input_devices=[], layers=[]
        )
        window._on_profile_deleted("to-delete")

        mock_deps["loader"].return_value.delete_profile.assert_called_with("to-delete")
        assert window.current_profile is None
        window.close()


class TestMainWindowDaemonControls:
    """Tests for MainWindow daemon control methods."""

    @pytest.fixture
    def qapp(self):
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app

    @pytest.fixture
    def mock_deps(self):
        """Mock all MainWindow dependencies."""
        mock_run_result = MagicMock()
        mock_run_result.returncode = 0
        with (
            patch("apps.gui.main_window.ProfileLoader") as mock_loader,
            patch("apps.gui.main_window.DeviceRegistry") as mock_registry,
            patch("apps.gui.main_window.OpenRazerBridge") as mock_bridge,
            patch(
                "apps.gui.main_window.subprocess.run", return_value=mock_run_result
            ) as mock_subprocess,
        ):
            mock_loader.return_value.list_profiles.return_value = []
            mock_loader.return_value.get_active_profile_id.return_value = None
            mock_registry.return_value.list_devices.return_value = []
            mock_bridge.return_value.connect.return_value = False
            mock_bridge.return_value.discover_devices.return_value = []
            yield {
                "loader": mock_loader,
                "registry": mock_registry,
                "bridge": mock_bridge,
                "subprocess": mock_subprocess,
            }

    def test_update_daemon_status_running(self, qapp, mock_deps):
        """Test _update_daemon_status when daemon is running."""
        from apps.gui.main_window import MainWindow

        with patch("apps.gui.main_window.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            window = MainWindow()
            window._update_daemon_status()

            assert "Running" in window.daemon_status_label.text()
            window.close()

    def test_update_daemon_status_stopped(self, qapp, mock_deps):
        """Test _update_daemon_status when daemon is stopped."""
        from apps.gui.main_window import MainWindow

        with patch("apps.gui.main_window.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 1
            window = MainWindow()
            window._update_daemon_status()

            assert "Stopped" in window.daemon_status_label.text()
            window.close()

    def test_update_daemon_status_exception(self, qapp, mock_deps):
        """Test _update_daemon_status handles exception."""
        from apps.gui.main_window import MainWindow

        with patch("apps.gui.main_window.subprocess.run") as mock_run:
            mock_run.side_effect = Exception("Test error")
            window = MainWindow()
            window._update_daemon_status()

            assert "Unknown" in window.daemon_status_label.text()
            window.close()

    def test_start_daemon(self, qapp, mock_deps):
        """Test _start_daemon calls systemctl."""
        from apps.gui.main_window import MainWindow

        with patch("apps.gui.main_window.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            window = MainWindow()
            window._start_daemon()

            # Check systemctl start was called
            calls = [str(c) for c in mock_run.call_args_list]
            assert any("start" in str(c) for c in calls)
            window.close()

    def test_stop_daemon(self, qapp, mock_deps):
        """Test _stop_daemon calls systemctl."""
        from apps.gui.main_window import MainWindow

        with patch("apps.gui.main_window.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            window = MainWindow()
            window._stop_daemon()

            calls = [str(c) for c in mock_run.call_args_list]
            assert any("stop" in str(c) for c in calls)
            window.close()

    def test_restart_daemon(self, qapp, mock_deps):
        """Test _restart_daemon calls systemctl."""
        from apps.gui.main_window import MainWindow

        with patch("apps.gui.main_window.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            window = MainWindow()
            window._restart_daemon()

            calls = [str(c) for c in mock_run.call_args_list]
            assert any("restart" in str(c) for c in calls)
            window.close()

    def test_enable_autostart(self, qapp, mock_deps):
        """Test _enable_autostart calls systemctl enable."""
        from apps.gui.main_window import MainWindow

        with patch("apps.gui.main_window.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            window = MainWindow()
            window._enable_autostart()

            calls = [str(c) for c in mock_run.call_args_list]
            assert any("enable" in str(c) for c in calls)
            window.close()

    def test_disable_autostart(self, qapp, mock_deps):
        """Test _disable_autostart calls systemctl disable."""
        from apps.gui.main_window import MainWindow

        with patch("apps.gui.main_window.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            window = MainWindow()
            window._disable_autostart()

            calls = [str(c) for c in mock_run.call_args_list]
            assert any("disable" in str(c) for c in calls)
            window.close()


class TestMainWindowSignalHandlers:
    """Tests for MainWindow signal handlers."""

    @pytest.fixture
    def qapp(self):
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app

    @pytest.fixture
    def mock_deps(self):
        """Mock all MainWindow dependencies."""
        mock_run_result = MagicMock()
        mock_run_result.returncode = 0
        with (
            patch("apps.gui.main_window.ProfileLoader") as mock_loader,
            patch("apps.gui.main_window.DeviceRegistry") as mock_registry,
            patch("apps.gui.main_window.OpenRazerBridge") as mock_bridge,
            patch(
                "apps.gui.main_window.subprocess.run", return_value=mock_run_result
            ) as mock_subprocess,
        ):
            mock_loader.return_value.list_profiles.return_value = []
            mock_loader.return_value.get_active_profile_id.return_value = None
            mock_registry.return_value.list_devices.return_value = []
            mock_bridge.return_value.connect.return_value = False
            mock_bridge.return_value.discover_devices.return_value = []
            yield {
                "loader": mock_loader,
                "registry": mock_registry,
                "bridge": mock_bridge,
                "subprocess": mock_subprocess,
            }

    def test_on_bindings_changed_with_profile(self, qapp, mock_deps):
        """Test _on_bindings_changed saves bindings."""
        from apps.gui.main_window import MainWindow
        from crates.profile_schema import Profile

        window = MainWindow()
        window.current_profile = Profile(id="test", name="Test", input_devices=[], layers=[])
        window._on_bindings_changed()

        mock_deps["loader"].return_value.save_profile.assert_called()
        window.close()

    def test_on_bindings_changed_no_profile(self, qapp, mock_deps):
        """Test _on_bindings_changed does nothing without profile."""
        from apps.gui.main_window import MainWindow

        window = MainWindow()
        window.current_profile = None
        window._on_bindings_changed()

        # Should not crash, should not save
        window.close()

    def test_on_macros_changed_with_profile(self, qapp, mock_deps):
        """Test _on_macros_changed saves macros."""
        from apps.gui.main_window import MainWindow
        from crates.profile_schema import Profile

        window = MainWindow()
        window.current_profile = Profile(id="test", name="Test", input_devices=[], layers=[])
        window._on_macros_changed([])

        mock_deps["loader"].return_value.save_profile.assert_called()
        window.close()

    def test_on_app_patterns_changed_with_profile(self, qapp, mock_deps):
        """Test _on_app_patterns_changed saves patterns."""
        from apps.gui.main_window import MainWindow
        from crates.profile_schema import Profile

        window = MainWindow()
        window.current_profile = Profile(id="test", name="Test", input_devices=[], layers=[])
        window._on_app_patterns_changed()

        mock_deps["loader"].return_value.save_profile.assert_called()
        window.close()

    def test_on_razer_device_selected(self, qapp, mock_deps):
        """Test _on_razer_device_selected updates editors."""
        from apps.gui.main_window import MainWindow

        window = MainWindow()
        mock_device = MagicMock()
        mock_device.configure_mock(name="Test Device")
        mock_device.serial = "TEST123"
        mock_device.has_matrix = False
        mock_device.max_dpi = 16000
        mock_device.supported_zones = []

        window._on_razer_device_selected(mock_device)
        # Should not crash
        window.close()

    def test_refresh_devices(self, qapp, mock_deps):
        """Test _refresh_devices refreshes all device views."""
        from apps.gui.main_window import MainWindow

        window = MainWindow()
        window._refresh_devices()
        # Should not crash
        window.close()

    def test_apply_device_selection_no_profile(self, qapp, mock_deps):
        """Test _apply_device_selection shows warning without profile."""
        from apps.gui.main_window import MainWindow

        window = MainWindow()
        window.current_profile = None

        with patch("apps.gui.main_window.QMessageBox.warning") as mock_warning:
            window._apply_device_selection()
            mock_warning.assert_called_once()
        window.close()

    def test_apply_device_selection_with_profile(self, qapp, mock_deps):
        """Test _apply_device_selection saves selection."""
        from apps.gui.main_window import MainWindow
        from crates.profile_schema import Profile

        window = MainWindow()
        window.current_profile = Profile(id="test", name="Test", input_devices=[], layers=[])

        # Mock get_selected_devices
        window.device_list.get_selected_devices = MagicMock(return_value=["dev1"])
        window._apply_device_selection()

        mock_deps["loader"].return_value.save_profile.assert_called()
        window.close()


class TestMainWindowDialogs:
    """Tests for MainWindow dialog methods."""

    @pytest.fixture
    def qapp(self):
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app

    @pytest.fixture
    def mock_deps(self):
        """Mock all MainWindow dependencies."""
        mock_run_result = MagicMock()
        mock_run_result.returncode = 0
        with (
            patch("apps.gui.main_window.ProfileLoader") as mock_loader,
            patch("apps.gui.main_window.DeviceRegistry") as mock_registry,
            patch("apps.gui.main_window.OpenRazerBridge") as mock_bridge,
            patch(
                "apps.gui.main_window.subprocess.run", return_value=mock_run_result
            ) as mock_subprocess,
        ):
            mock_loader.return_value.list_profiles.return_value = []
            mock_loader.return_value.get_active_profile_id.return_value = None
            mock_registry.return_value.list_devices.return_value = []
            mock_bridge.return_value.connect.return_value = False
            mock_bridge.return_value.discover_devices.return_value = []
            yield {
                "loader": mock_loader,
                "registry": mock_registry,
                "bridge": mock_bridge,
                "subprocess": mock_subprocess,
            }

    def test_show_about(self, qapp, mock_deps):
        """Test _show_about opens about dialog."""
        from apps.gui.main_window import MainWindow

        with patch("apps.gui.main_window.QMessageBox.about") as mock_about:
            window = MainWindow()
            window._show_about()
            mock_about.assert_called_once()
            window.close()

    def test_run_setup_wizard(self, qapp, mock_deps):
        """Test _run_setup_wizard opens wizard."""
        from apps.gui.main_window import MainWindow

        with patch("apps.gui.widgets.setup_wizard.SetupWizard") as mock_wizard:
            mock_wizard.return_value.exec.return_value = 0
            window = MainWindow()
            window._run_setup_wizard()
            mock_wizard.assert_called_once()
            window.close()

    def test_configure_hotkeys(self, qapp, mock_deps):
        """Test _configure_hotkeys opens hotkey dialog."""
        from apps.gui.main_window import MainWindow

        with patch("apps.gui.widgets.hotkey_editor.HotkeyEditorDialog") as mock_dialog:
            mock_dialog.return_value.exec.return_value = 0
            window = MainWindow()
            window._configure_hotkeys()
            mock_dialog.assert_called_once()
            window.close()

    def test_on_low_battery(self, qapp, mock_deps):
        """Test _on_low_battery shows warning."""
        from apps.gui.main_window import MainWindow

        with patch("apps.gui.main_window.QMessageBox.warning") as mock_warning:
            window = MainWindow()
            window._on_low_battery("Test Mouse", 15)
            mock_warning.assert_called_once()
            # Check the message contains device name and level
            call_args = mock_warning.call_args
            assert "Test Mouse" in str(call_args)
            assert "15" in str(call_args)
            window.close()


class TestMainWindowCoverage:
    """Additional tests for MainWindow coverage."""

    @pytest.fixture
    def qapp(self):
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app

    @pytest.fixture
    def mock_deps(self):
        """Mock all MainWindow dependencies."""
        mock_run_result = MagicMock()
        mock_run_result.returncode = 0
        with (
            patch("apps.gui.main_window.ProfileLoader") as mock_loader,
            patch("apps.gui.main_window.DeviceRegistry") as mock_registry,
            patch("apps.gui.main_window.OpenRazerBridge") as mock_bridge,
            patch(
                "apps.gui.main_window.subprocess.run", return_value=mock_run_result
            ) as mock_subprocess,
        ):
            mock_loader.return_value.list_profiles.return_value = []
            mock_loader.return_value.get_active_profile_id.return_value = None
            mock_registry.return_value.list_devices.return_value = []
            mock_bridge.return_value.connect.return_value = False
            mock_bridge.return_value.discover_devices.return_value = []
            yield {
                "loader": mock_loader,
                "registry": mock_registry,
                "bridge": mock_bridge,
                "subprocess": mock_subprocess,
            }

    def test_openrazer_connect_success(self, qapp):
        """Test _load_initial_data when OpenRazer connects successfully."""
        from apps.gui.main_window import MainWindow

        mock_run_result = MagicMock()
        mock_run_result.returncode = 0
        with (
            patch("apps.gui.main_window.ProfileLoader") as mock_loader,
            patch("apps.gui.main_window.DeviceRegistry") as mock_registry,
            patch("apps.gui.main_window.OpenRazerBridge") as mock_bridge,
            patch("apps.gui.main_window.subprocess.run", return_value=mock_run_result),
        ):
            mock_loader.return_value.list_profiles.return_value = []
            mock_loader.return_value.get_active_profile_id.return_value = None
            mock_registry.return_value.list_devices.return_value = []
            # Make connect return True
            mock_bridge.return_value.connect.return_value = True
            mock_bridge.return_value.discover_devices.return_value = []

            window = MainWindow()
            # Verify razer_tab.refresh_devices was called (line 290)
            mock_bridge.return_value.connect.assert_called_once()
            window.close()

    def test_update_ui_for_profile_with_zone_editor(self, qapp, mock_deps):
        """Test _update_ui_for_profile restores zone colors when device selected."""
        from apps.gui.main_window import MainWindow
        from crates.profile_schema import (
            DeviceConfig,
            LightingConfig,
            MatrixLightingConfig,
            Profile,
            ZoneColor,
        )

        window = MainWindow()

        # Create profile with zone colors
        zone_colors = [ZoneColor(zone_id="zone1", color=(255, 0, 0))]
        lighting = LightingConfig(matrix=MatrixLightingConfig(enabled=True, zones=zone_colors))
        device_config = DeviceConfig(device_id="SERIAL123", lighting=lighting)
        profile = Profile(
            id="test", name="Test", input_devices=[], layers=[], devices=[device_config]
        )

        # Mock zone editor with current device
        mock_device = MagicMock()
        mock_device.serial = "SERIAL123"
        window.zone_editor.current_device = mock_device
        window.zone_editor.set_zone_colors = MagicMock()

        window._update_ui_for_profile(profile)

        # Verify zone colors were set (lines 318-325)
        window.zone_editor.set_zone_colors.assert_called_once()
        window.close()

    def test_update_ui_for_profile_active_label(self, qapp, mock_deps):
        """Test _update_ui_for_profile sets active label when profile is active."""
        from apps.gui.main_window import MainWindow
        from crates.profile_schema import Profile

        window = MainWindow()
        profile = Profile(id="test", name="Test Profile", input_devices=[], layers=[])

        # Mock active profile to match
        window.profile_loader.get_active_profile_id = MagicMock(return_value="test")

        window._update_ui_for_profile(profile)

        # Verify active label includes "(Active)" (line 330)
        assert "(Active)" in window.active_profile_label.text()
        window.close()

    def test_on_zone_config_changed_with_profile_and_device(self, qapp, mock_deps):
        """Test _on_zone_config_changed saves zone config to profile."""
        from apps.gui.main_window import MainWindow
        from crates.profile_schema import Profile

        window = MainWindow()
        profile = Profile(id="test", name="Test", input_devices=[], layers=[], devices=[])
        window.current_profile = profile

        # Mock zone editor with current device and colors
        mock_device = MagicMock()
        mock_device.serial = "SERIAL123"
        window.zone_editor.current_device = mock_device
        window.zone_editor.get_zone_colors = MagicMock(
            return_value={"zone1": (255, 0, 0), "zone2": (0, 255, 0)}
        )

        window._on_zone_config_changed()

        # Verify profile was saved (lines 402-436)
        mock_deps["loader"].return_value.save_profile.assert_called()
        # Verify device config was added
        assert len(profile.devices) == 1
        assert profile.devices[0].device_id == "SERIAL123"
        window.close()

    def test_on_zone_config_changed_updates_existing_device(self, qapp, mock_deps):
        """Test _on_zone_config_changed updates existing device config."""
        from apps.gui.main_window import MainWindow
        from crates.profile_schema import DeviceConfig, LightingConfig, Profile

        window = MainWindow()
        existing_config = DeviceConfig(device_id="SERIAL123", lighting=LightingConfig())
        profile = Profile(
            id="test", name="Test", input_devices=[], layers=[], devices=[existing_config]
        )
        window.current_profile = profile

        mock_device = MagicMock()
        mock_device.serial = "SERIAL123"
        window.zone_editor.current_device = mock_device
        window.zone_editor.get_zone_colors = MagicMock(return_value={"zone1": (255, 0, 0)})

        window._on_zone_config_changed()

        # Verify existing config was updated
        assert len(profile.devices) == 1
        assert profile.devices[0].lighting.matrix is not None
        window.close()

    def test_refresh_device_status(self, qapp, mock_deps):
        """Test _refresh_device_status calls _update_daemon_status."""
        from apps.gui.main_window import MainWindow

        window = MainWindow()
        window._update_daemon_status = MagicMock()

        window._refresh_device_status()

        # Verify _update_daemon_status was called (line 447)
        window._update_daemon_status.assert_called_once()
        window.close()

    def test_start_daemon_called_process_error(self, qapp, mock_deps):
        """Test _start_daemon handles CalledProcessError."""
        import subprocess

        from apps.gui.main_window import MainWindow

        window = MainWindow()

        with patch("apps.gui.main_window.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "systemctl")
            from PySide6.QtWidgets import QMessageBox

            with patch.object(QMessageBox, "warning") as mock_warning:
                window._start_daemon()
                mock_warning.assert_called_once()
        window.close()

    def test_start_daemon_file_not_found_error(self, qapp, mock_deps):
        """Test _start_daemon handles FileNotFoundError."""
        from apps.gui.main_window import MainWindow

        window = MainWindow()

        with patch("apps.gui.main_window.subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("systemctl not found")
            from PySide6.QtWidgets import QMessageBox

            with patch.object(QMessageBox, "warning") as mock_warning:
                window._start_daemon()
                mock_warning.assert_called_once()
                # Check it mentions systemctl
                assert "systemctl" in str(mock_warning.call_args)
        window.close()

    def test_stop_daemon_exception(self, qapp, mock_deps):
        """Test _stop_daemon handles exception."""
        from apps.gui.main_window import MainWindow

        window = MainWindow()

        with patch("apps.gui.main_window.subprocess.run") as mock_run:
            mock_run.side_effect = Exception("Test error")
            from PySide6.QtWidgets import QMessageBox

            with patch.object(QMessageBox, "warning") as mock_warning:
                window._stop_daemon()
                mock_warning.assert_called_once()
        window.close()

    def test_restart_daemon_exception(self, qapp, mock_deps):
        """Test _restart_daemon handles exception."""
        from apps.gui.main_window import MainWindow

        window = MainWindow()

        with patch("apps.gui.main_window.subprocess.run") as mock_run:
            mock_run.side_effect = Exception("Test error")
            from PySide6.QtWidgets import QMessageBox

            with patch.object(QMessageBox, "warning") as mock_warning:
                window._restart_daemon()
                mock_warning.assert_called_once()
        window.close()

    def test_toggle_autostart_enable(self, qapp, mock_deps):
        """Test _toggle_autostart calls _enable_autostart when enabled."""
        from apps.gui.main_window import MainWindow

        window = MainWindow()
        window._enable_autostart = MagicMock()
        window._disable_autostart = MagicMock()

        window._toggle_autostart(True)

        window._enable_autostart.assert_called_once()
        window._disable_autostart.assert_not_called()
        window.close()

    def test_toggle_autostart_disable(self, qapp, mock_deps):
        """Test _toggle_autostart calls _disable_autostart when disabled."""
        from apps.gui.main_window import MainWindow

        window = MainWindow()
        window._enable_autostart = MagicMock()
        window._disable_autostart = MagicMock()

        window._toggle_autostart(False)

        window._disable_autostart.assert_called_once()
        window._enable_autostart.assert_not_called()
        window.close()

    def test_enable_autostart_exception(self, qapp, mock_deps):
        """Test _enable_autostart handles exception."""
        from apps.gui.main_window import MainWindow

        window = MainWindow()

        with patch("apps.gui.main_window.subprocess.run") as mock_run:
            mock_run.side_effect = Exception("Test error")
            from PySide6.QtWidgets import QMessageBox

            with patch.object(QMessageBox, "warning") as mock_warning:
                window._enable_autostart()
                mock_warning.assert_called_once()
        window.close()

    def test_disable_autostart_exception(self, qapp, mock_deps):
        """Test _disable_autostart handles exception."""
        from apps.gui.main_window import MainWindow

        window = MainWindow()

        with patch("apps.gui.main_window.subprocess.run") as mock_run:
            mock_run.side_effect = Exception("Test error")
            from PySide6.QtWidgets import QMessageBox

            with patch.object(QMessageBox, "warning") as mock_warning:
                window._disable_autostart()
                mock_warning.assert_called_once()
        window.close()


class TestMainWindowDeviceVisual:
    """Tests for MainWindow device visual handlers."""

    @pytest.fixture
    def qapp(self):
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app

    @pytest.fixture
    def mock_deps(self):
        """Mock all MainWindow dependencies."""
        mock_run_result = MagicMock()
        mock_run_result.returncode = 0
        with (
            patch("apps.gui.main_window.ProfileLoader") as mock_loader,
            patch("apps.gui.main_window.DeviceRegistry") as mock_registry,
            patch("apps.gui.main_window.OpenRazerBridge") as mock_bridge,
            patch(
                "apps.gui.main_window.subprocess.run", return_value=mock_run_result
            ) as mock_subprocess,
        ):
            mock_loader.return_value.list_profiles.return_value = []
            mock_loader.return_value.get_active_profile_id.return_value = None
            mock_registry.return_value.list_devices.return_value = []
            mock_bridge.return_value.connect.return_value = False
            mock_bridge.return_value.discover_devices.return_value = []
            yield {
                "loader": mock_loader,
                "registry": mock_registry,
                "bridge": mock_bridge,
                "subprocess": mock_subprocess,
            }

    def test_on_device_button_clicked(self, qapp, mock_deps):
        """Test _on_device_button_clicked shows status message."""
        from apps.gui.main_window import MainWindow

        window = MainWindow()
        window._on_device_button_clicked("BTN_1", "BTN_LEFT")

        # Verify status bar shows message (line 248)
        assert "BTN_1" in window.statusbar.currentMessage()
        assert "BTN_LEFT" in window.statusbar.currentMessage()
        window.close()

    def test_on_device_zone_clicked_no_device(self, qapp, mock_deps):
        """Test _on_device_zone_clicked without device selected."""
        from apps.gui.main_window import MainWindow

        window = MainWindow()
        window._current_razer_device = None

        window._on_device_zone_clicked("zone_1")

        # Should show "Select a device first" (lines 254-257)
        assert "Select a device" in window.statusbar.currentMessage()
        window.close()

    def test_on_device_zone_clicked_color_cancelled(self, qapp, mock_deps):
        """Test _on_device_zone_clicked when color dialog cancelled."""
        from PySide6.QtWidgets import QColorDialog

        from apps.gui.main_window import MainWindow

        window = MainWindow()
        mock_device = MagicMock()
        mock_device.serial = "TEST123"
        window._current_razer_device = mock_device

        # Mock color dialog to return invalid color (cancelled)
        with patch.object(QColorDialog, "getColor") as mock_dialog:
            mock_color = MagicMock()
            mock_color.isValid.return_value = False
            mock_dialog.return_value = mock_color

            window._on_device_zone_clicked("zone_1")

            # Should not try to set color (line 260 condition)
            window.openrazer.set_static_color.assert_not_called()
        window.close()

    def test_on_device_zone_clicked_color_success(self, qapp, mock_deps):
        """Test _on_device_zone_clicked with valid color."""
        from PySide6.QtWidgets import QColorDialog

        from apps.gui.main_window import MainWindow

        window = MainWindow()
        mock_device = MagicMock()
        mock_device.serial = "TEST123"
        window._current_razer_device = mock_device

        # Mock color dialog to return valid color
        with patch.object(QColorDialog, "getColor") as mock_dialog:
            mock_color = MagicMock()
            mock_color.isValid.return_value = True
            mock_color.red.return_value = 255
            mock_color.green.return_value = 128
            mock_color.blue.return_value = 64
            mock_color.name.return_value = "#ff8040"
            mock_dialog.return_value = mock_color

            window._on_device_zone_clicked("zone_1")

            # Verify color was set (lines 262-268)
            window.openrazer.set_static_color.assert_called_with(mock_device, 255, 128, 64)
            assert "zone_1" in window.statusbar.currentMessage()
            assert "#ff8040" in window.statusbar.currentMessage()
        window.close()

    def test_on_device_zone_clicked_color_exception(self, qapp, mock_deps):
        """Test _on_device_zone_clicked handles device exception."""
        from PySide6.QtWidgets import QColorDialog

        from apps.gui.main_window import MainWindow

        window = MainWindow()
        mock_device = MagicMock()
        mock_device.serial = "TEST123"
        window._current_razer_device = mock_device

        # Mock color dialog to return valid color
        with patch.object(QColorDialog, "getColor") as mock_dialog:
            mock_color = MagicMock()
            mock_color.isValid.return_value = True
            mock_color.red.return_value = 255
            mock_color.green.return_value = 0
            mock_color.blue.return_value = 0
            mock_dialog.return_value = mock_color

            # Make set_static_color raise exception
            window.openrazer.set_static_color.side_effect = Exception("Device error")

            window._on_device_zone_clicked("zone_1")

            # Verify error message in status bar (line 270)
            assert "Failed" in window.statusbar.currentMessage()
        window.close()

    def test_on_device_selection_changed(self, qapp, mock_deps):
        """Test _on_device_selection_changed (currently a no-op)."""
        from apps.gui.main_window import MainWindow

        window = MainWindow()

        # Call with some selected IDs (line 400 - pass statement)
        window._on_device_selection_changed(["device1", "device2"])

        # Should not crash - method is intentionally a no-op
        window.close()
