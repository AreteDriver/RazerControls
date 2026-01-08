"""Visual representation of Razer devices with interactive buttons."""

import logging
from pathlib import Path
from typing import Any

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import (
    QAction,
    QBrush,
    QColor,
    QMouseEvent,
    QPainter,
    QPen,
    QPixmap,
    QPolygonF,
)
from PySide6.QtWidgets import (
    QColorDialog,
    QMenu,
    QSizePolicy,
    QWidget,
)

from crates.device_layouts import (
    ButtonShape,
    DeviceLayout,
    DeviceLayoutRegistry,
    get_fallback_layout,
)
from crates.device_layouts.schema import ShapeType

# Base path for device images
_DATA_DIR = Path(__file__).parent.parent.parent.parent.parent / "data"

logger = logging.getLogger(__name__)


class DeviceVisualWidget(QWidget):
    """Widget that displays a visual representation of a Razer device.

    Renders the device outline and all buttons/zones using QPainter.
    Supports mouse interaction for button clicks.

    Signals:
        button_clicked: Emitted when a button is clicked (button_id, input_code)
        button_right_clicked: Emitted on right-click (button_id) for config popup
        zone_clicked: Emitted when an RGB zone is clicked (zone_id)
    """

    button_clicked = Signal(str, str)  # button_id, input_code
    button_right_clicked = Signal(str)  # button_id
    zone_clicked = Signal(str)  # zone_id

    # Color scheme
    COLOR_BODY = QColor(40, 40, 45)
    COLOR_BODY_OUTLINE = QColor(60, 60, 65)
    COLOR_BUTTON = QColor(55, 55, 60)
    COLOR_BUTTON_OUTLINE = QColor(80, 80, 85)
    COLOR_BUTTON_HOVER = QColor(70, 70, 75)
    COLOR_BUTTON_SELECTED = QColor(0, 200, 100)
    COLOR_ZONE = QColor(0, 150, 80, 100)
    COLOR_ZONE_OUTLINE = QColor(0, 200, 100)
    COLOR_TEXT = QColor(180, 180, 180)
    COLOR_TEXT_HOVER = QColor(255, 255, 255)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._layout: DeviceLayout | None = None
        self._registry = DeviceLayoutRegistry()
        self._registry.load_layouts()

        self._hovered_button: str | None = None
        self._selected_button: str | None = None
        self._zone_colors: dict[str, QColor] = {}
        self._button_bindings: dict[str, str] = {}  # button_id -> key binding

        # Device image support
        self._device_image: QPixmap | None = None
        self._image_cache: dict[str, QPixmap] = {}  # path -> pixmap cache

        # Enable mouse tracking for hover effects
        self.setMouseTracking(True)

        # Size policy
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(150, 200)

    def set_device(
        self,
        device_name: str,
        device_type: str | None = None,
        matrix_cols: int | None = None,
    ) -> None:
        """Set the device to display.

        Finds the best matching layout or falls back to a generic layout.

        Args:
            device_name: Name of the device
            device_type: Optional device type for fallback
            matrix_cols: Optional matrix columns for fallback
        """
        # Try to find a matching layout
        layout = self._registry.get_layout_for_device(device_name, device_type, matrix_cols)

        if layout is None:
            # Use fallback
            layout = get_fallback_layout(device_type, matrix_cols)
            logger.info(f"Using fallback layout for {device_name}: {layout.id}")
        else:
            logger.info(f"Found layout for {device_name}: {layout.id}")

        self._layout = layout
        self._hovered_button = None
        self._selected_button = None
        self._load_device_image()
        self.update()

    def set_layout(self, layout: DeviceLayout) -> None:
        """Set the layout directly."""
        self._layout = layout
        self._hovered_button = None
        self._selected_button = None
        self._load_device_image()
        self.update()

    def _load_device_image(self) -> None:
        """Load the device image if specified in layout."""
        self._device_image = None

        if not self._layout or not self._layout.image_path:
            return

        # Check cache first
        if self._layout.image_path in self._image_cache:
            self._device_image = self._image_cache[self._layout.image_path]
            return

        # Resolve image path (relative to data/ directory)
        image_path = _DATA_DIR / self._layout.image_path

        if not image_path.exists():
            logger.warning(f"Device image not found: {image_path}")
            return

        pixmap = QPixmap(str(image_path))
        if pixmap.isNull():
            logger.warning(f"Failed to load device image: {image_path}")
            return

        self._device_image = pixmap
        self._image_cache[self._layout.image_path] = pixmap
        logger.info(f"Loaded device image: {image_path}")

    def set_zone_color(self, zone_id: str, color: QColor) -> None:
        """Set the color for an RGB zone."""
        self._zone_colors[zone_id] = color
        self.update()

    def clear_zone_colors(self) -> None:
        """Clear all zone colors."""
        self._zone_colors.clear()
        self.update()

    def get_layout(self) -> DeviceLayout | None:
        """Get the current layout."""
        return self._layout

    def get_selected_button(self) -> str | None:
        """Get the currently selected button ID."""
        return self._selected_button

    def select_button(self, button_id: str | None) -> None:
        """Programmatically select a button."""
        self._selected_button = button_id
        self.update()

    def paintEvent(self, event: Any) -> None:
        """Render the device layout."""
        if self._layout is None:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # Calculate scaling to fit widget
        widget_rect = self.rect()
        padding = 4  # Minimal padding
        available_width = widget_rect.width() - 2 * padding
        available_height = widget_rect.height() - 2 * padding

        # Maintain aspect ratio
        aspect = self._layout.base_width / self._layout.base_height
        if available_width / available_height > aspect:
            # Height constrained
            scale_height = available_height
            scale_width = scale_height * aspect
        else:
            # Width constrained
            scale_width = available_width
            scale_height = scale_width / aspect

        # Center the device
        offset_x = (widget_rect.width() - scale_width) / 2
        offset_y = (widget_rect.height() - scale_height) / 2

        # Draw device image if available, otherwise draw outline
        if self._device_image:
            self._draw_device_image(painter, offset_x, offset_y, scale_width, scale_height)
        else:
            self._draw_outline(painter, offset_x, offset_y, scale_width, scale_height)

        # Draw buttons and zones as overlays
        for button in self._layout.buttons:
            self._draw_button(painter, button, offset_x, offset_y, scale_width, scale_height)

        painter.end()

    def _draw_device_image(
        self,
        painter: QPainter,
        offset_x: float,
        offset_y: float,
        width: float,
        height: float,
    ) -> None:
        """Draw the device background image."""
        if not self._device_image:
            return

        # Scale image to fit the device area
        target_rect = QRectF(offset_x, offset_y, width, height)
        painter.drawPixmap(target_rect.toRect(), self._device_image)

    def _draw_outline(
        self,
        painter: QPainter,
        offset_x: float,
        offset_y: float,
        width: float,
        height: float,
    ) -> None:
        """Draw the device body outline."""
        if not self._layout or not self._layout.outline_path:
            # Simple rectangle fallback
            rect = QRectF(offset_x, offset_y, width, height)
            painter.setBrush(QBrush(self.COLOR_BODY))
            painter.setPen(QPen(self.COLOR_BODY_OUTLINE, 2))
            painter.drawRoundedRect(rect, 10, 10)
            return

        # Create polygon from outline path
        polygon = QPolygonF()
        for x, y in self._layout.outline_path:
            polygon.append(QPointF(offset_x + x * width, offset_y + y * height))

        # Draw filled polygon
        painter.setBrush(QBrush(self.COLOR_BODY))
        painter.setPen(QPen(self.COLOR_BODY_OUTLINE, 2))
        painter.drawPolygon(polygon)

    def _draw_button(
        self,
        painter: QPainter,
        button: ButtonShape,
        offset_x: float,
        offset_y: float,
        scale_width: float,
        scale_height: float,
    ) -> None:
        """Draw a single button or zone."""
        # Calculate absolute position
        x = offset_x + button.x * scale_width
        y = offset_y + button.y * scale_height
        w = button.width * scale_width
        h = button.height * scale_height
        rect = QRectF(x, y, w, h)

        # Determine colors based on state
        is_hovered = button.id == self._hovered_button
        is_selected = button.id == self._selected_button
        has_image = self._device_image is not None

        if button.is_zone:
            # RGB zone - use custom color if set
            fill_color = self._zone_colors.get(button.id, self.COLOR_ZONE)
            outline_color = self.COLOR_BUTTON_SELECTED if is_selected else self.COLOR_ZONE_OUTLINE
            outline_width = 3 if is_selected else 1
        else:
            # Physical button
            if is_selected:
                fill_color = QColor(self.COLOR_BUTTON_SELECTED)
            elif is_hovered:
                fill_color = QColor(self.COLOR_BUTTON_HOVER)
            else:
                fill_color = QColor(self.COLOR_BUTTON)
            outline_color = self.COLOR_BUTTON_SELECTED if is_selected else self.COLOR_BUTTON_OUTLINE
            outline_width = 2 if is_selected else 1

            # Make buttons semi-transparent when image is present (except selected)
            if has_image and not is_selected:
                if is_hovered:
                    fill_color.setAlpha(180)  # More visible on hover
                else:
                    fill_color.setAlpha(80)  # Subtle overlay to show hotspots

        painter.setBrush(QBrush(fill_color))
        painter.setPen(QPen(outline_color, outline_width))

        # Draw shape
        if button.shape_type == ShapeType.ELLIPSE:
            painter.drawEllipse(rect)
        elif button.shape_type == ShapeType.POLYGON and button.polygon_points:
            polygon = QPolygonF()
            for px, py in button.polygon_points:
                polygon.append(
                    QPointF(
                        offset_x + px * scale_width,
                        offset_y + py * scale_height,
                    )
                )
            painter.drawPolygon(polygon)
        else:
            # Rectangle (default)
            painter.drawRoundedRect(rect, 3, 3)

        # Draw label if space allows
        if w > 30 and h > 15:
            text_color = self.COLOR_TEXT_HOVER if is_hovered else self.COLOR_TEXT
            painter.setPen(QPen(text_color))

            # Use smaller font for small buttons
            font = painter.font()
            if w < 50 or h < 25:
                font.setPointSize(7)
            else:
                font.setPointSize(9)
            painter.setFont(font)

            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, button.label)

    def _button_at(self, pos: QPointF) -> ButtonShape | None:
        """Find the button at the given position."""
        if not self._layout:
            return None

        # Calculate same scaling as paintEvent
        widget_rect = self.rect()
        padding = 10
        available_width = widget_rect.width() - 2 * padding
        available_height = widget_rect.height() - 2 * padding

        aspect = self._layout.base_width / self._layout.base_height
        if available_width / available_height > aspect:
            scale_height = available_height
            scale_width = scale_height * aspect
        else:
            scale_width = available_width
            scale_height = scale_width / aspect

        offset_x = (widget_rect.width() - scale_width) / 2
        offset_y = (widget_rect.height() - scale_height) / 2

        # Check each button (reverse order for z-order)
        for button in reversed(self._layout.buttons):
            x = offset_x + button.x * scale_width
            y = offset_y + button.y * scale_height
            w = button.width * scale_width
            h = button.height * scale_height

            if button.shape_type == ShapeType.ELLIPSE:
                # Ellipse hit test
                cx = x + w / 2
                cy = y + h / 2
                rx = w / 2
                ry = h / 2
                dx = (pos.x() - cx) / rx
                dy = (pos.y() - cy) / ry
                if dx * dx + dy * dy <= 1:
                    return button
            else:
                # Rectangle hit test
                if x <= pos.x() <= x + w and y <= pos.y() <= y + h:
                    return button

        return None

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Handle mouse move for hover effects."""
        pos = event.position()
        button = self._button_at(pos)

        old_hover = self._hovered_button
        self._hovered_button = button.id if button else None

        if old_hover != self._hovered_button:
            self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle mouse click on buttons."""
        pos = event.position()
        button = self._button_at(pos)

        if button is None:
            return

        if event.button() == Qt.MouseButton.LeftButton:
            self._selected_button = button.id
            self.update()

            if button.is_zone:
                self.zone_clicked.emit(button.id)
            else:
                input_code = button.input_code or ""
                self.button_clicked.emit(button.id, input_code)

        elif event.button() == Qt.MouseButton.RightButton:
            self.button_right_clicked.emit(button.id)
            self._show_context_menu(event.globalPosition().toPoint(), button)

    def _show_context_menu(self, pos: Any, button: ButtonShape) -> None:
        """Show context menu for button configuration."""
        menu = QMenu(self)

        if button.is_zone:
            # Zone-specific actions
            set_color_action = QAction("Set Zone Color...", self)
            set_color_action.triggered.connect(lambda: self._set_zone_color(button.id))
            menu.addAction(set_color_action)

            clear_color_action = QAction("Reset Zone Color", self)
            clear_color_action.triggered.connect(lambda: self._clear_zone_color(button.id))
            menu.addAction(clear_color_action)
        else:
            # Button-specific actions
            configure_action = QAction("Configure Binding...", self)
            configure_action.triggered.connect(lambda: self._configure_binding(button))
            menu.addAction(configure_action)

            # Show current binding if set
            current_binding = self._button_bindings.get(button.id)
            if current_binding:
                menu.addSeparator()
                current_label = QAction(f"Current: {current_binding}", self)
                current_label.setEnabled(False)
                menu.addAction(current_label)

                clear_action = QAction("Clear Binding", self)
                clear_action.triggered.connect(lambda: self._clear_binding(button.id))
                menu.addAction(clear_action)

        menu.exec(pos)

    def _set_zone_color(self, zone_id: str) -> None:
        """Open color picker for zone."""
        current_color = self._zone_colors.get(zone_id, QColor(0, 200, 100))
        color = QColorDialog.getColor(current_color, self, f"Set Color for {zone_id}")
        if color.isValid():
            self.set_zone_color(zone_id, color)
            self.zone_clicked.emit(zone_id)

    def _clear_zone_color(self, zone_id: str) -> None:
        """Reset zone to default color."""
        if zone_id in self._zone_colors:
            del self._zone_colors[zone_id]
            self.update()

    def _configure_binding(self, button: ButtonShape) -> None:
        """Open binding configuration dialog."""
        from apps.gui.widgets.device_visual.button_binding_dialog import (
            ButtonBindingDialog,
        )

        dialog = ButtonBindingDialog(button, self._button_bindings.get(button.id), self)
        if dialog.exec():
            binding = dialog.get_binding()
            if binding:
                self._button_bindings[button.id] = binding
            elif button.id in self._button_bindings:
                del self._button_bindings[button.id]
            self.update()

    def _clear_binding(self, button_id: str) -> None:
        """Clear binding for a button."""
        if button_id in self._button_bindings:
            del self._button_bindings[button_id]
            self.update()

    def get_button_bindings(self) -> dict[str, str]:
        """Get all button bindings."""
        return self._button_bindings.copy()

    def set_button_bindings(self, bindings: dict[str, str]) -> None:
        """Set button bindings from a dict."""
        self._button_bindings = bindings.copy()
        self.update()

    def leaveEvent(self, event: Any) -> None:
        """Clear hover state when mouse leaves."""
        self._hovered_button = None
        self.update()

    def sizeHint(self) -> QSize:
        """Suggest a reasonable default size."""
        if self._layout:
            # Use layout dimensions as hint
            return QSize(
                int(self._layout.base_width * 2),
                int(self._layout.base_height * 2),
            )
        return QSize(200, 300)
