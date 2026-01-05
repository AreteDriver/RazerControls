"""Tests for device visual widget and button binding dialog."""

import os
from unittest.mock import MagicMock, patch

import pytest

# Set offscreen platform before any Qt imports
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QKeyEvent, QMouseEvent
from PySide6.QtWidgets import QApplication, QDialog

from apps.gui.widgets.device_visual import ButtonBindingDialog, DeviceVisualWidget
from apps.gui.widgets.device_visual.button_binding_dialog import (
    COMMON_KEYS,
    QT_TO_EVDEV,
    KeyCaptureWidget,
)
from crates.device_layouts.schema import ButtonShape, DeviceCategory, DeviceLayout, ShapeType


@pytest.fixture(scope="module")
def qapp():
    """Create QApplication for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def sample_button():
    """Create a sample button for testing."""
    return ButtonShape(
        id="left_click",
        label="Left Click",
        x=0.1,
        y=0.1,
        width=0.2,
        height=0.1,
        shape_type=ShapeType.RECT,
        input_code="BTN_LEFT",
        is_zone=False,
    )


@pytest.fixture
def sample_zone():
    """Create a sample zone for testing."""
    return ButtonShape(
        id="zone_logo",
        label="Logo",
        x=0.4,
        y=0.4,
        width=0.2,
        height=0.2,
        shape_type=ShapeType.ELLIPSE,
        is_zone=True,
    )


@pytest.fixture
def sample_polygon_button():
    """Create a sample polygon button for testing."""
    return ButtonShape(
        id="scroll_wheel",
        label="Scroll",
        x=0.3,
        y=0.2,
        width=0.1,
        height=0.15,
        shape_type=ShapeType.POLYGON,
        polygon_points=[(0.3, 0.2), (0.4, 0.2), (0.35, 0.35)],
        input_code="REL_WHEEL",
    )


@pytest.fixture
def sample_layout(sample_button, sample_zone, sample_polygon_button):
    """Create a sample device layout for testing."""
    return DeviceLayout(
        id="test_mouse",
        name="Test Mouse",
        category=DeviceCategory.MOUSE,
        device_name_patterns=["Test.*Mouse"],
        base_width=100,
        base_height=200,
        outline_path=[(0, 0), (1, 0), (1, 1), (0, 1)],
        buttons=[sample_button, sample_zone, sample_polygon_button],
    )


@pytest.fixture
def layout_no_outline(sample_button):
    """Create a layout without outline path."""
    return DeviceLayout(
        id="no_outline",
        name="No Outline",
        category=DeviceCategory.MOUSE,
        device_name_patterns=[],
        base_width=100,
        base_height=200,
        outline_path=[],
        buttons=[sample_button],
    )


class TestKeyCaptureWidget:
    """Tests for KeyCaptureWidget."""

    def test_init(self, qapp):
        """Test widget initialization."""
        widget = KeyCaptureWidget()
        assert widget.isReadOnly()
        assert widget._captured_key is None
        assert widget.placeholderText() == "Click and press a key..."

    def test_key_press_letter(self, qapp):
        """Test capturing a letter key."""
        widget = KeyCaptureWidget()

        # Simulate pressing 'A'
        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_A, Qt.KeyboardModifier.NoModifier, "A")
        widget.keyPressEvent(event)

        assert widget._captured_key == "KEY_A"
        assert widget.text() == "KEY_A"

    def test_key_press_number(self, qapp):
        """Test capturing a number key."""
        widget = KeyCaptureWidget()

        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_5, Qt.KeyboardModifier.NoModifier, "5")
        widget.keyPressEvent(event)

        assert widget._captured_key == "KEY_5"

    def test_key_press_control_modifier(self, qapp):
        """Test capturing control key."""
        widget = KeyCaptureWidget()

        event = QKeyEvent(
            QKeyEvent.Type.KeyPress, Qt.Key.Key_Control, Qt.KeyboardModifier.ControlModifier
        )
        widget.keyPressEvent(event)

        assert widget._captured_key == "KEY_LEFTCTRL"

    def test_key_press_shift_modifier(self, qapp):
        """Test capturing shift key."""
        widget = KeyCaptureWidget()

        event = QKeyEvent(
            QKeyEvent.Type.KeyPress, Qt.Key.Key_Shift, Qt.KeyboardModifier.ShiftModifier
        )
        widget.keyPressEvent(event)

        assert widget._captured_key == "KEY_LEFTSHIFT"

    def test_key_press_alt_modifier(self, qapp):
        """Test capturing alt key."""
        widget = KeyCaptureWidget()

        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Alt, Qt.KeyboardModifier.AltModifier)
        widget.keyPressEvent(event)

        assert widget._captured_key == "KEY_LEFTALT"

    def test_key_press_meta_modifier(self, qapp):
        """Test capturing meta/super key."""
        widget = KeyCaptureWidget()

        event = QKeyEvent(
            QKeyEvent.Type.KeyPress, Qt.Key.Key_Meta, Qt.KeyboardModifier.MetaModifier
        )
        widget.keyPressEvent(event)

        assert widget._captured_key == "KEY_LEFTMETA"

    def test_key_press_mapped_key(self, qapp):
        """Test capturing a key in QT_TO_EVDEV mapping."""
        widget = KeyCaptureWidget()

        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier)
        widget.keyPressEvent(event)

        assert widget._captured_key == "KEY_ESC"

    def test_key_press_f1(self, qapp):
        """Test capturing F1 key."""
        widget = KeyCaptureWidget()

        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_F1, Qt.KeyboardModifier.NoModifier)
        widget.keyPressEvent(event)

        assert widget._captured_key == "KEY_F1"

    def test_key_press_space(self, qapp):
        """Test capturing space key."""
        widget = KeyCaptureWidget()

        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Space, Qt.KeyboardModifier.NoModifier, " ")
        widget.keyPressEvent(event)

        assert widget._captured_key == "KEY_SPACE"

    def test_key_press_unmapped_key_no_text(self, qapp):
        """Test pressing an unmapped key with no text."""
        widget = KeyCaptureWidget()
        widget._captured_key = "PREVIOUS"  # Set initial value

        # Key with no text representation (like Print Screen without mapping)
        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_unknown, Qt.KeyboardModifier.NoModifier, "")
        widget.keyPressEvent(event)

        # Should not change - no valid capture
        assert widget._captured_key == "PREVIOUS"

    def test_key_press_unmapped_non_alnum(self, qapp):
        """Test pressing unmapped key with non-alphanumeric text."""
        widget = KeyCaptureWidget()
        widget._captured_key = "PREVIOUS"

        # Special character
        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_unknown, Qt.KeyboardModifier.NoModifier, "@")
        widget.keyPressEvent(event)

        # Should not change - @ is not alphanumeric
        assert widget._captured_key == "PREVIOUS"

    def test_get_key(self, qapp):
        """Test get_key method."""
        widget = KeyCaptureWidget()
        assert widget.get_key() is None

        widget._captured_key = "KEY_A"
        assert widget.get_key() == "KEY_A"

    def test_set_key(self, qapp):
        """Test set_key method."""
        widget = KeyCaptureWidget()

        widget.set_key("KEY_B")
        assert widget._captured_key == "KEY_B"
        assert widget.text() == "KEY_B"

        widget.set_key(None)
        assert widget._captured_key is None
        assert widget.text() == ""


class TestButtonBindingDialog:
    """Tests for ButtonBindingDialog."""

    def test_init_without_binding(self, qapp, sample_button):
        """Test dialog initialization without current binding."""
        dialog = ButtonBindingDialog(sample_button)

        assert dialog._button == sample_button
        assert dialog._binding is None
        assert dialog.windowTitle() == f"Configure: {sample_button.label}"
        assert dialog.minimumWidth() == 400

    def test_init_with_binding(self, qapp, sample_button):
        """Test dialog initialization with current binding."""
        dialog = ButtonBindingDialog(sample_button, current_binding="KEY_X")

        assert dialog._binding == "KEY_X"
        assert dialog._manual_input.text() == "KEY_X"

    def test_init_button_without_input_code(self, qapp):
        """Test dialog with button that has no input_code."""
        button = ButtonShape(
            id="custom",
            label="Custom Button",
            x=0.1,
            y=0.1,
            width=0.1,
            height=0.1,
        )
        dialog = ButtonBindingDialog(button)

        # Should not crash
        assert dialog._button == button

    def test_update_key_list(self, qapp, sample_button):
        """Test category combo changes update key list."""
        dialog = ButtonBindingDialog(sample_button)

        # Check initial category
        initial_category = dialog._category_combo.currentText()
        assert initial_category in COMMON_KEYS

        # Change category
        dialog._category_combo.setCurrentText("Modifiers")
        dialog._update_key_list("Modifiers")

        # Key combo should have modifier keys
        assert dialog._key_combo.count() == len(COMMON_KEYS["Modifiers"])
        assert dialog._key_combo.itemData(0) == "KEY_LEFTCTRL"

    def test_update_key_list_empty_category(self, qapp, sample_button):
        """Test update_key_list with invalid category."""
        dialog = ButtonBindingDialog(sample_button)

        # Unknown category should result in empty combo
        dialog._update_key_list("NonExistent")
        assert dialog._key_combo.count() == 0

    def test_use_common_binding(self, qapp, sample_button):
        """Test using a common binding."""
        dialog = ButtonBindingDialog(sample_button)

        # Set category and key
        dialog._category_combo.setCurrentText("Mouse")
        dialog._update_key_list("Mouse")
        dialog._key_combo.setCurrentIndex(0)  # Left Click -> BTN_LEFT

        dialog._use_common_binding()

        assert dialog._binding == "BTN_LEFT"
        assert dialog._current_label.text() == "BTN_LEFT"
        assert dialog._manual_input.text() == "BTN_LEFT"

    def test_use_common_binding_no_selection(self, qapp, sample_button):
        """Test use_common_binding with empty combo."""
        dialog = ButtonBindingDialog(sample_button)

        # Clear the combo
        dialog._key_combo.clear()
        dialog._use_common_binding()

        # Should not crash, binding unchanged
        assert dialog._binding is None

    def test_use_captured_binding(self, qapp, sample_button):
        """Test using a captured key binding."""
        dialog = ButtonBindingDialog(sample_button)

        # Simulate key capture
        dialog._key_capture._captured_key = "KEY_F5"
        dialog._key_capture.setText("KEY_F5")

        dialog._use_captured_binding()

        assert dialog._binding == "KEY_F5"
        assert dialog._current_label.text() == "KEY_F5"
        assert dialog._manual_input.text() == "KEY_F5"

    def test_use_captured_binding_no_key(self, qapp, sample_button):
        """Test use_captured_binding with no captured key."""
        dialog = ButtonBindingDialog(sample_button)

        dialog._use_captured_binding()

        # Should not crash, binding unchanged
        assert dialog._binding is None

    def test_clear_binding(self, qapp, sample_button):
        """Test clearing the binding."""
        dialog = ButtonBindingDialog(sample_button, current_binding="KEY_A")

        dialog._clear_binding()

        assert dialog._binding is None
        assert dialog._current_label.text() == "(none)"
        assert dialog._manual_input.text() == ""
        assert dialog._key_capture.get_key() is None

    def test_on_accept_with_manual_input(self, qapp, sample_button):
        """Test accepting with manual input."""
        dialog = ButtonBindingDialog(sample_button)
        dialog._binding = "KEY_OLD"

        # Set manual input
        dialog._manual_input.setText("KEY_MANUAL")

        dialog._on_accept()

        assert dialog._binding == "KEY_MANUAL"

    def test_on_accept_without_manual_input(self, qapp, sample_button):
        """Test accepting without manual input uses existing binding."""
        dialog = ButtonBindingDialog(sample_button)
        dialog._binding = "KEY_EXISTING"
        dialog._manual_input.clear()

        dialog._on_accept()

        assert dialog._binding == "KEY_EXISTING"

    def test_on_accept_manual_whitespace_only(self, qapp, sample_button):
        """Test accepting with whitespace-only manual input."""
        dialog = ButtonBindingDialog(sample_button)
        dialog._binding = "KEY_OLD"
        dialog._manual_input.setText("   ")

        dialog._on_accept()

        # Should keep old binding
        assert dialog._binding == "KEY_OLD"

    def test_get_binding(self, qapp, sample_button):
        """Test get_binding method."""
        dialog = ButtonBindingDialog(sample_button)
        assert dialog.get_binding() is None

        dialog._binding = "KEY_Z"
        assert dialog.get_binding() == "KEY_Z"


class TestDeviceVisualWidget:
    """Tests for DeviceVisualWidget."""

    def test_init(self, qapp):
        """Test widget initialization."""
        widget = DeviceVisualWidget()

        assert widget._layout is None
        assert widget._hovered_button is None
        assert widget._selected_button is None
        assert widget._zone_colors == {}
        assert widget._button_bindings == {}
        assert widget.hasMouseTracking()

    def test_set_device_with_matching_layout(self, qapp, sample_layout):
        """Test set_device when registry finds a layout."""
        widget = DeviceVisualWidget()

        with patch.object(
            widget._registry, "get_layout_for_device", return_value=sample_layout
        ):
            widget.set_device("Test Mouse", "mouse", 1)

        assert widget._layout == sample_layout

    def test_set_device_with_fallback(self, qapp):
        """Test set_device using fallback layout."""
        widget = DeviceVisualWidget()

        with patch.object(widget._registry, "get_layout_for_device", return_value=None), patch(
            "apps.gui.widgets.device_visual.device_visual_widget.get_fallback_layout"
        ) as mock_fallback:
            mock_layout = MagicMock()
            mock_layout.id = "fallback"
            mock_fallback.return_value = mock_layout

            widget.set_device("Unknown Device", "mouse", 2)

            mock_fallback.assert_called_once_with("mouse", 2)
            assert widget._layout == mock_layout

    def test_set_layout(self, qapp, sample_layout):
        """Test set_layout method."""
        widget = DeviceVisualWidget()
        widget._hovered_button = "something"
        widget._selected_button = "other"

        widget.set_layout(sample_layout)

        assert widget._layout == sample_layout
        assert widget._hovered_button is None
        assert widget._selected_button is None

    def test_set_zone_color(self, qapp):
        """Test set_zone_color method."""
        widget = DeviceVisualWidget()
        color = QColor(255, 0, 0)

        widget.set_zone_color("zone_1", color)

        assert widget._zone_colors["zone_1"] == color

    def test_clear_zone_colors(self, qapp):
        """Test clear_zone_colors method."""
        widget = DeviceVisualWidget()
        widget._zone_colors = {"zone_1": QColor(255, 0, 0), "zone_2": QColor(0, 255, 0)}

        widget.clear_zone_colors()

        assert widget._zone_colors == {}

    def test_get_layout(self, qapp, sample_layout):
        """Test get_layout method."""
        widget = DeviceVisualWidget()
        assert widget.get_layout() is None

        widget._layout = sample_layout
        assert widget.get_layout() == sample_layout

    def test_get_selected_button(self, qapp):
        """Test get_selected_button method."""
        widget = DeviceVisualWidget()
        assert widget.get_selected_button() is None

        widget._selected_button = "btn_1"
        assert widget.get_selected_button() == "btn_1"

    def test_select_button(self, qapp):
        """Test select_button method."""
        widget = DeviceVisualWidget()

        widget.select_button("btn_2")
        assert widget._selected_button == "btn_2"

        widget.select_button(None)
        assert widget._selected_button is None

    def test_paint_event_no_layout(self, qapp):
        """Test paintEvent with no layout."""
        widget = DeviceVisualWidget()
        widget.resize(200, 300)

        # Should not crash
        widget.repaint()

    def test_paint_event_with_layout(self, qapp, sample_layout):
        """Test paintEvent with layout."""
        widget = DeviceVisualWidget()
        widget.resize(200, 300)
        widget.set_layout(sample_layout)

        # Should not crash
        widget.repaint()

    def test_paint_event_with_hover_and_selection(self, qapp, sample_layout):
        """Test paintEvent with hovered and selected buttons."""
        widget = DeviceVisualWidget()
        widget.resize(200, 300)
        widget.set_layout(sample_layout)
        widget._hovered_button = "left_click"
        widget._selected_button = "zone_logo"

        # Should render with different colors for hover/selection
        widget.repaint()

    def test_paint_event_width_constrained(self, qapp, sample_layout):
        """Test paintEvent when width is constraining factor."""
        widget = DeviceVisualWidget()
        widget.resize(100, 400)  # Narrow and tall
        widget.set_layout(sample_layout)

        widget.repaint()

    def test_draw_outline_with_path(self, qapp, sample_layout):
        """Test _draw_outline with outline_path defined."""
        widget = DeviceVisualWidget()
        widget.resize(200, 300)
        widget.set_layout(sample_layout)

        widget.repaint()  # Should use polygon outline

    def test_draw_outline_without_path(self, qapp, layout_no_outline):
        """Test _draw_outline without outline_path (rectangle fallback)."""
        widget = DeviceVisualWidget()
        widget.resize(200, 300)
        widget.set_layout(layout_no_outline)

        widget.repaint()  # Should use rectangle fallback

    def test_draw_button_rect(self, qapp, sample_layout):
        """Test drawing rectangle button."""
        widget = DeviceVisualWidget()
        widget.resize(200, 300)
        widget.set_layout(sample_layout)
        widget.repaint()

    def test_draw_button_ellipse(self, qapp, sample_layout):
        """Test drawing ellipse button (zone)."""
        widget = DeviceVisualWidget()
        widget.resize(200, 300)
        widget.set_layout(sample_layout)
        widget.repaint()

    def test_draw_button_polygon(self, qapp, sample_layout):
        """Test drawing polygon button."""
        widget = DeviceVisualWidget()
        widget.resize(200, 300)
        widget.set_layout(sample_layout)
        widget.repaint()

    def test_draw_button_zone_with_custom_color(self, qapp, sample_layout):
        """Test drawing zone with custom color."""
        widget = DeviceVisualWidget()
        widget.resize(200, 300)
        widget.set_layout(sample_layout)
        widget.set_zone_color("zone_logo", QColor(255, 0, 255))
        widget.repaint()

    def test_draw_button_small_no_label(self, qapp):
        """Test drawing small button without label."""
        small_button = ButtonShape(
            id="tiny",
            label="T",
            x=0.1,
            y=0.1,
            width=0.01,  # Very small
            height=0.01,
        )
        layout = DeviceLayout(
            id="test",
            name="Test",
            category=DeviceCategory.MOUSE,
            device_name_patterns=[],
            base_width=100,
            base_height=200,
            outline_path=[],
            buttons=[small_button],
        )
        widget = DeviceVisualWidget()
        widget.resize(200, 300)
        widget.set_layout(layout)
        widget.repaint()

    def test_button_at_no_layout(self, qapp):
        """Test _button_at with no layout."""
        widget = DeviceVisualWidget()
        widget.resize(200, 300)

        result = widget._button_at(QPointF(100, 150))
        assert result is None

    def test_button_at_rectangle_hit(self, qapp, sample_layout):
        """Test _button_at hitting a rectangle button."""
        widget = DeviceVisualWidget()
        widget.resize(200, 300)
        widget.set_layout(sample_layout)

        # The left_click button is at x=0.1, y=0.1, w=0.2, h=0.1
        # Widget is 200x300, layout is 100x200 (aspect 0.5)
        # Height constrained: scale_height=280, scale_width=140
        # offset_x = (200-140)/2 = 30, offset_y = (300-280)/2 = 10
        # Button rect: x=30+0.1*140=44, y=10+0.1*280=38, w=0.2*140=28, h=0.1*280=28
        button = widget._button_at(QPointF(50, 45))
        assert button is not None
        assert button.id == "left_click"

    def test_button_at_ellipse_hit(self, qapp, sample_layout):
        """Test _button_at hitting an ellipse button."""
        widget = DeviceVisualWidget()
        widget.resize(200, 300)
        widget.set_layout(sample_layout)

        # zone_logo is ellipse at x=0.4, y=0.4, w=0.2, h=0.2
        # Center at x=0.5, y=0.5
        # With scale: cx = 30 + 0.5*140 = 100, cy = 10 + 0.5*280 = 150
        button = widget._button_at(QPointF(100, 150))
        assert button is not None
        assert button.id == "zone_logo"

    def test_button_at_miss(self, qapp, sample_layout):
        """Test _button_at missing all buttons."""
        widget = DeviceVisualWidget()
        widget.resize(200, 300)
        widget.set_layout(sample_layout)

        # Far corner - should miss all buttons
        button = widget._button_at(QPointF(5, 5))
        assert button is None

    def test_mouse_move_event_hover(self, qapp, sample_layout):
        """Test mouseMoveEvent for hover effects."""
        widget = DeviceVisualWidget()
        widget.resize(200, 300)
        widget.set_layout(sample_layout)

        # Move over a button
        event = MagicMock(spec=QMouseEvent)
        event.position.return_value = QPointF(50, 45)  # Over left_click

        widget.mouseMoveEvent(event)

        assert widget._hovered_button == "left_click"

    def test_mouse_move_event_hover_change(self, qapp, sample_layout):
        """Test mouseMoveEvent when hover changes."""
        widget = DeviceVisualWidget()
        widget.resize(200, 300)
        widget.set_layout(sample_layout)
        widget._hovered_button = "left_click"

        # Move away from button
        event = MagicMock(spec=QMouseEvent)
        event.position.return_value = QPointF(5, 5)  # Not over any button

        widget.mouseMoveEvent(event)

        assert widget._hovered_button is None

    def test_mouse_press_left_button(self, qapp, sample_layout):
        """Test left click on physical button."""
        widget = DeviceVisualWidget()
        widget.resize(200, 300)
        widget.set_layout(sample_layout)

        signal_received = []
        widget.button_clicked.connect(lambda bid, code: signal_received.append((bid, code)))

        event = MagicMock(spec=QMouseEvent)
        event.position.return_value = QPointF(50, 45)  # Over left_click
        event.button.return_value = Qt.MouseButton.LeftButton

        widget.mousePressEvent(event)

        assert widget._selected_button == "left_click"
        assert len(signal_received) == 1
        assert signal_received[0] == ("left_click", "BTN_LEFT")

    def test_mouse_press_left_zone(self, qapp, sample_layout):
        """Test left click on zone."""
        widget = DeviceVisualWidget()
        widget.resize(200, 300)
        widget.set_layout(sample_layout)

        signal_received = []
        widget.zone_clicked.connect(lambda zid: signal_received.append(zid))

        event = MagicMock(spec=QMouseEvent)
        event.position.return_value = QPointF(100, 150)  # Over zone_logo
        event.button.return_value = Qt.MouseButton.LeftButton

        widget.mousePressEvent(event)

        assert widget._selected_button == "zone_logo"
        assert len(signal_received) == 1
        assert signal_received[0] == "zone_logo"

    def test_mouse_press_left_miss(self, qapp, sample_layout):
        """Test left click missing all buttons."""
        widget = DeviceVisualWidget()
        widget.resize(200, 300)
        widget.set_layout(sample_layout)

        event = MagicMock(spec=QMouseEvent)
        event.position.return_value = QPointF(5, 5)  # Not over any button
        event.button.return_value = Qt.MouseButton.LeftButton

        widget.mousePressEvent(event)

        assert widget._selected_button is None

    def test_mouse_press_right_button(self, qapp, sample_layout):
        """Test right click on button."""
        widget = DeviceVisualWidget()
        widget.resize(200, 300)
        widget.set_layout(sample_layout)

        signal_received = []
        widget.button_right_clicked.connect(lambda bid: signal_received.append(bid))

        event = MagicMock(spec=QMouseEvent)
        event.position.return_value = QPointF(50, 45)  # Over left_click
        event.button.return_value = Qt.MouseButton.RightButton
        event.globalPosition.return_value.toPoint.return_value = MagicMock()

        with patch.object(widget, "_show_context_menu"):
            widget.mousePressEvent(event)

        assert len(signal_received) == 1
        assert signal_received[0] == "left_click"

    def test_show_context_menu_zone(self, qapp, sample_zone):
        """Test context menu for zone."""
        widget = DeviceVisualWidget()

        with patch("apps.gui.widgets.device_visual.device_visual_widget.QMenu") as mock_menu:
            mock_menu_instance = MagicMock()
            mock_menu.return_value = mock_menu_instance

            widget._show_context_menu(MagicMock(), sample_zone)

            # Should have zone-specific actions
            calls = mock_menu_instance.addAction.call_args_list
            action_names = [str(call) for call in calls]
            assert any("Set Zone Color" in str(c) for c in calls)
            assert any("Reset Zone Color" in str(c) for c in calls)

    def test_show_context_menu_button(self, qapp, sample_button):
        """Test context menu for button."""
        widget = DeviceVisualWidget()

        with patch("apps.gui.widgets.device_visual.device_visual_widget.QMenu") as mock_menu:
            mock_menu_instance = MagicMock()
            mock_menu.return_value = mock_menu_instance

            widget._show_context_menu(MagicMock(), sample_button)

            calls = mock_menu_instance.addAction.call_args_list
            assert any("Configure Binding" in str(c) for c in calls)

    def test_show_context_menu_button_with_binding(self, qapp, sample_button):
        """Test context menu for button with existing binding."""
        widget = DeviceVisualWidget()
        widget._button_bindings["left_click"] = "KEY_A"

        with patch("apps.gui.widgets.device_visual.device_visual_widget.QMenu") as mock_menu:
            mock_menu_instance = MagicMock()
            mock_menu.return_value = mock_menu_instance

            widget._show_context_menu(MagicMock(), sample_button)

            calls = mock_menu_instance.addAction.call_args_list
            assert any("Current: KEY_A" in str(c) for c in calls)
            assert any("Clear Binding" in str(c) for c in calls)

    def test_set_zone_color_via_dialog(self, qapp):
        """Test _set_zone_color opens color dialog."""
        widget = DeviceVisualWidget()

        with patch(
            "apps.gui.widgets.device_visual.device_visual_widget.QColorDialog.getColor"
        ) as mock_dialog:
            mock_dialog.return_value = QColor(255, 128, 0)

            signal_received = []
            widget.zone_clicked.connect(lambda zid: signal_received.append(zid))

            widget._set_zone_color("zone_1")

            assert widget._zone_colors["zone_1"] == QColor(255, 128, 0)
            assert "zone_1" in signal_received

    def test_set_zone_color_cancelled(self, qapp):
        """Test _set_zone_color when dialog cancelled."""
        widget = DeviceVisualWidget()

        with patch(
            "apps.gui.widgets.device_visual.device_visual_widget.QColorDialog.getColor"
        ) as mock_dialog:
            invalid_color = QColor()  # Invalid color
            mock_dialog.return_value = invalid_color

            widget._set_zone_color("zone_1")

            assert "zone_1" not in widget._zone_colors

    def test_clear_zone_color(self, qapp):
        """Test _clear_zone_color method."""
        widget = DeviceVisualWidget()
        widget._zone_colors["zone_1"] = QColor(255, 0, 0)

        widget._clear_zone_color("zone_1")

        assert "zone_1" not in widget._zone_colors

    def test_clear_zone_color_not_set(self, qapp):
        """Test _clear_zone_color when zone not in dict."""
        widget = DeviceVisualWidget()

        # Should not crash
        widget._clear_zone_color("nonexistent")

    def test_configure_binding_accepted(self, qapp, sample_button):
        """Test _configure_binding when dialog accepted."""
        widget = DeviceVisualWidget()

        with patch(
            "apps.gui.widgets.device_visual.button_binding_dialog.ButtonBindingDialog"
        ) as mock_dialog_cls:
            mock_dialog = MagicMock()
            mock_dialog.exec.return_value = True
            mock_dialog.get_binding.return_value = "KEY_NEW"
            mock_dialog_cls.return_value = mock_dialog

            widget._configure_binding(sample_button)

            assert widget._button_bindings["left_click"] == "KEY_NEW"

    def test_configure_binding_cleared(self, qapp, sample_button):
        """Test _configure_binding when binding cleared."""
        widget = DeviceVisualWidget()
        widget._button_bindings["left_click"] = "KEY_OLD"

        with patch(
            "apps.gui.widgets.device_visual.button_binding_dialog.ButtonBindingDialog"
        ) as mock_dialog_cls:
            mock_dialog = MagicMock()
            mock_dialog.exec.return_value = True
            mock_dialog.get_binding.return_value = None  # Cleared
            mock_dialog_cls.return_value = mock_dialog

            widget._configure_binding(sample_button)

            assert "left_click" not in widget._button_bindings

    def test_configure_binding_cancelled(self, qapp, sample_button):
        """Test _configure_binding when dialog cancelled."""
        widget = DeviceVisualWidget()

        with patch(
            "apps.gui.widgets.device_visual.button_binding_dialog.ButtonBindingDialog"
        ) as mock_dialog_cls:
            mock_dialog = MagicMock()
            mock_dialog.exec.return_value = False
            mock_dialog_cls.return_value = mock_dialog

            widget._configure_binding(sample_button)

            assert "left_click" not in widget._button_bindings

    def test_clear_binding(self, qapp):
        """Test _clear_binding method."""
        widget = DeviceVisualWidget()
        widget._button_bindings["btn_1"] = "KEY_A"

        widget._clear_binding("btn_1")

        assert "btn_1" not in widget._button_bindings

    def test_clear_binding_not_set(self, qapp):
        """Test _clear_binding when binding not set."""
        widget = DeviceVisualWidget()

        # Should not crash
        widget._clear_binding("nonexistent")

    def test_get_button_bindings(self, qapp):
        """Test get_button_bindings returns copy."""
        widget = DeviceVisualWidget()
        widget._button_bindings = {"btn_1": "KEY_A", "btn_2": "KEY_B"}

        result = widget.get_button_bindings()

        assert result == {"btn_1": "KEY_A", "btn_2": "KEY_B"}
        # Should be a copy
        result["btn_3"] = "KEY_C"
        assert "btn_3" not in widget._button_bindings

    def test_set_button_bindings(self, qapp):
        """Test set_button_bindings."""
        widget = DeviceVisualWidget()
        bindings = {"btn_1": "KEY_A", "btn_2": "KEY_B"}

        widget.set_button_bindings(bindings)

        assert widget._button_bindings == bindings
        # Should be a copy
        bindings["btn_3"] = "KEY_C"
        assert "btn_3" not in widget._button_bindings

    def test_leave_event(self, qapp):
        """Test leaveEvent clears hover state."""
        widget = DeviceVisualWidget()
        widget._hovered_button = "some_button"

        widget.leaveEvent(None)

        assert widget._hovered_button is None

    def test_size_hint_with_layout(self, qapp, sample_layout):
        """Test sizeHint with layout."""
        widget = DeviceVisualWidget()
        widget.set_layout(sample_layout)

        hint = widget.sizeHint()

        # base_width=100, base_height=200, multiplied by 2
        assert hint.width() == 200
        assert hint.height() == 400

    def test_size_hint_without_layout(self, qapp):
        """Test sizeHint without layout."""
        widget = DeviceVisualWidget()

        hint = widget.sizeHint()

        assert hint.width() == 200
        assert hint.height() == 300

    def test_button_no_input_code(self, qapp):
        """Test button click when button has no input_code."""
        button = ButtonShape(
            id="no_code",
            label="No Code",
            x=0.1,
            y=0.1,
            width=0.2,
            height=0.1,
        )
        layout = DeviceLayout(
            id="test",
            name="Test",
            category=DeviceCategory.MOUSE,
            device_name_patterns=[],
            base_width=100,
            base_height=200,
            outline_path=[],
            buttons=[button],
        )
        widget = DeviceVisualWidget()
        widget.resize(200, 300)
        widget.set_layout(layout)

        signal_received = []
        widget.button_clicked.connect(lambda bid, code: signal_received.append((bid, code)))

        event = MagicMock(spec=QMouseEvent)
        event.position.return_value = QPointF(50, 45)
        event.button.return_value = Qt.MouseButton.LeftButton

        widget.mousePressEvent(event)

        assert len(signal_received) == 1
        assert signal_received[0] == ("no_code", "")  # Empty string for no input_code


class TestDeviceVisualWidgetPainting:
    """Tests for DeviceVisualWidget painting methods - direct invocation."""

    def test_paint_event_direct_no_layout(self, qapp):
        """Test paintEvent returns early with no layout."""
        widget = DeviceVisualWidget()
        widget.resize(200, 300)

        # Create a mock paint event
        from PySide6.QtGui import QPaintEvent

        event = QPaintEvent(widget.rect())
        widget.paintEvent(event)  # Should return early

    def test_paint_event_direct_with_layout(self, qapp, sample_layout):
        """Test paintEvent with layout - direct invocation."""
        widget = DeviceVisualWidget()
        widget.resize(200, 300)
        widget.set_layout(sample_layout)

        from PySide6.QtGui import QPaintEvent

        event = QPaintEvent(widget.rect())
        widget.paintEvent(event)

    def test_paint_event_height_constrained(self, qapp, sample_layout):
        """Test paintEvent when height is constraining factor."""
        widget = DeviceVisualWidget()
        widget.resize(400, 200)  # Wide and short
        widget.set_layout(sample_layout)

        from PySide6.QtGui import QPaintEvent

        event = QPaintEvent(widget.rect())
        widget.paintEvent(event)

    def test_draw_outline_direct_no_path(self, qapp, layout_no_outline):
        """Test _draw_outline without outline path (rectangle fallback)."""
        widget = DeviceVisualWidget()
        widget.resize(200, 300)
        widget.set_layout(layout_no_outline)

        from PySide6.QtGui import QPaintEvent

        event = QPaintEvent(widget.rect())
        widget.paintEvent(event)

    def test_draw_button_all_states(self, qapp, sample_layout):
        """Test drawing buttons in different states."""
        widget = DeviceVisualWidget()
        widget.resize(200, 300)
        widget.set_layout(sample_layout)

        # Set hover and selection to cover different code paths
        widget._hovered_button = "left_click"
        widget._selected_button = "zone_logo"

        from PySide6.QtGui import QPaintEvent

        event = QPaintEvent(widget.rect())
        widget.paintEvent(event)

    def test_draw_button_with_zone_color(self, qapp, sample_layout):
        """Test drawing zone with custom color."""
        widget = DeviceVisualWidget()
        widget.resize(200, 300)
        widget.set_layout(sample_layout)
        widget.set_zone_color("zone_logo", QColor(128, 64, 255))

        from PySide6.QtGui import QPaintEvent

        event = QPaintEvent(widget.rect())
        widget.paintEvent(event)

    def test_draw_button_medium_size(self, qapp):
        """Test drawing medium-sized button with smaller font."""
        button = ButtonShape(
            id="medium",
            label="MED",
            x=0.1,
            y=0.1,
            width=0.08,  # Medium width (30-50px when scaled)
            height=0.05,  # Medium height
        )
        layout = DeviceLayout(
            id="test",
            name="Test",
            category=DeviceCategory.MOUSE,
            device_name_patterns=[],
            base_width=400,  # Larger base for scaling
            base_height=400,
            outline_path=[],
            buttons=[button],
        )
        widget = DeviceVisualWidget()
        widget.resize(400, 400)
        widget.set_layout(layout)

        from PySide6.QtGui import QPaintEvent

        event = QPaintEvent(widget.rect())
        widget.paintEvent(event)

    def test_button_at_width_constrained(self, qapp, sample_layout):
        """Test _button_at when width is constraining."""
        widget = DeviceVisualWidget()
        widget.resize(100, 400)  # Narrow, tall
        widget.set_layout(sample_layout)

        # Miss all buttons
        button = widget._button_at(QPointF(5, 5))
        assert button is None

    def test_draw_selected_physical_button(self, qapp):
        """Test drawing a selected physical button (not zone)."""
        button = ButtonShape(
            id="physical_btn",
            label="Click",
            x=0.1,
            y=0.1,
            width=0.3,
            height=0.2,
            is_zone=False,
        )
        layout = DeviceLayout(
            id="test",
            name="Test",
            category=DeviceCategory.MOUSE,
            device_name_patterns=[],
            base_width=200,
            base_height=200,
            outline_path=[],
            buttons=[button],
        )
        widget = DeviceVisualWidget()
        widget.resize(200, 200)
        widget.set_layout(layout)
        widget._selected_button = "physical_btn"  # Select the physical button

        from PySide6.QtGui import QPaintEvent

        event = QPaintEvent(widget.rect())
        widget.paintEvent(event)

    def test_draw_large_button_with_normal_font(self, qapp):
        """Test drawing a large button that uses normal font size."""
        button = ButtonShape(
            id="large_btn",
            label="Large Button",
            x=0.1,
            y=0.1,
            width=0.4,  # Large width (>50px when scaled)
            height=0.3,  # Large height (>25px when scaled)
        )
        layout = DeviceLayout(
            id="test",
            name="Test",
            category=DeviceCategory.MOUSE,
            device_name_patterns=[],
            base_width=200,
            base_height=200,
            outline_path=[],
            buttons=[button],
        )
        widget = DeviceVisualWidget()
        widget.resize(300, 300)  # Large widget to ensure button is big
        widget.set_layout(layout)

        from PySide6.QtGui import QPaintEvent

        event = QPaintEvent(widget.rect())
        widget.paintEvent(event)


class TestKeyCaptureWidgetEdgeCases:
    """Additional edge case tests for KeyCaptureWidget."""

    def test_key_press_unmapped_with_text_fallback(self, qapp):
        """Test capturing key not in QT_TO_EVDEV that produces text."""
        widget = KeyCaptureWidget()

        # Use a key that's not in QT_TO_EVDEV but produces alphanumeric text
        # Qt.Key.Key_unknown with lowercase letter text
        event = QKeyEvent(
            QKeyEvent.Type.KeyPress,
            Qt.Key.Key_unknown,
            Qt.KeyboardModifier.NoModifier,
            "x"  # lowercase letter
        )
        widget.keyPressEvent(event)

        assert widget._captured_key == "KEY_X"

    def test_key_press_unmapped_digit_text(self, qapp):
        """Test capturing key with digit text through fallback path."""
        widget = KeyCaptureWidget()

        # Simulate a key not in QT_TO_EVDEV that produces digit text
        # This covers the text.isdigit() branch
        event = QKeyEvent(
            QKeyEvent.Type.KeyPress,
            Qt.Key.Key_unknown,  # Not in QT_TO_EVDEV
            Qt.KeyboardModifier.NoModifier,
            "7"  # digit text
        )
        widget.keyPressEvent(event)

        assert widget._captured_key == "KEY_7"


class TestModuleExports:
    """Test that module exports are correct."""

    def test_init_exports(self, qapp):
        """Test __init__.py exports."""
        from apps.gui.widgets.device_visual import ButtonBindingDialog, DeviceVisualWidget

        assert ButtonBindingDialog is not None
        assert DeviceVisualWidget is not None

    def test_common_keys_structure(self):
        """Test COMMON_KEYS has expected structure."""
        assert "Mouse" in COMMON_KEYS
        assert "Modifiers" in COMMON_KEYS
        assert "Function" in COMMON_KEYS

        # Each entry should be (label, code) tuple
        for category, keys in COMMON_KEYS.items():
            for label, code in keys:
                assert isinstance(label, str)
                assert isinstance(code, str)
                assert code.startswith("KEY_") or code.startswith("BTN_")

    def test_qt_to_evdev_mapping(self):
        """Test QT_TO_EVDEV has expected mappings."""
        assert Qt.Key.Key_A in QT_TO_EVDEV
        assert QT_TO_EVDEV[Qt.Key.Key_A] == "KEY_A"

        assert Qt.Key.Key_Escape in QT_TO_EVDEV
        assert QT_TO_EVDEV[Qt.Key.Key_Escape] == "KEY_ESC"

        assert Qt.Key.Key_F1 in QT_TO_EVDEV
        assert QT_TO_EVDEV[Qt.Key.Key_F1] == "KEY_F1"
