"""Dark theme for the GUI."""

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPalette, QColor
from PySide6.QtCore import Qt


def apply_dark_theme(app: QApplication) -> None:
    """Apply a Razer-inspired dark theme."""
    palette = QPalette()

    # Base colors - dark with Razer green accents
    dark_bg = QColor(30, 30, 30)
    darker_bg = QColor(20, 20, 20)
    light_bg = QColor(45, 45, 45)
    text_color = QColor(220, 220, 220)
    disabled_text = QColor(120, 120, 120)
    razer_green = QColor(68, 215, 44)  # Razer's signature green
    highlight = razer_green
    link_color = QColor(100, 200, 100)

    # Window
    palette.setColor(QPalette.Window, dark_bg)
    palette.setColor(QPalette.WindowText, text_color)

    # Base (for text inputs, etc.)
    palette.setColor(QPalette.Base, darker_bg)
    palette.setColor(QPalette.AlternateBase, light_bg)

    # Text
    palette.setColor(QPalette.Text, text_color)
    palette.setColor(QPalette.BrightText, Qt.white)
    palette.setColor(QPalette.Disabled, QPalette.Text, disabled_text)

    # Buttons
    palette.setColor(QPalette.Button, light_bg)
    palette.setColor(QPalette.ButtonText, text_color)
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, disabled_text)

    # Highlights
    palette.setColor(QPalette.Highlight, highlight)
    palette.setColor(QPalette.HighlightedText, Qt.black)

    # Links
    palette.setColor(QPalette.Link, link_color)
    palette.setColor(QPalette.LinkVisited, QColor(80, 160, 80))

    # Tooltips
    palette.setColor(QPalette.ToolTipBase, dark_bg)
    palette.setColor(QPalette.ToolTipText, text_color)

    app.setPalette(palette)

    # Additional stylesheet for finer control
    app.setStyleSheet("""
        QMainWindow {
            background-color: #1e1e1e;
        }
        QGroupBox {
            border: 1px solid #3d3d3d;
            border-radius: 4px;
            margin-top: 8px;
            padding-top: 8px;
            font-weight: bold;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px;
            color: #44d72c;
        }
        QPushButton {
            background-color: #2d2d2d;
            border: 1px solid #3d3d3d;
            border-radius: 4px;
            padding: 6px 16px;
            min-width: 80px;
        }
        QPushButton:hover {
            background-color: #3d3d3d;
            border-color: #44d72c;
        }
        QPushButton:pressed {
            background-color: #44d72c;
            color: black;
        }
        QPushButton:disabled {
            background-color: #1a1a1a;
            color: #666666;
        }
        QLineEdit, QSpinBox, QComboBox {
            background-color: #141414;
            border: 1px solid #3d3d3d;
            border-radius: 4px;
            padding: 4px;
        }
        QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
            border-color: #44d72c;
        }
        QListWidget, QTreeWidget, QTableWidget {
            background-color: #141414;
            border: 1px solid #3d3d3d;
            border-radius: 4px;
        }
        QListWidget::item:selected, QTreeWidget::item:selected {
            background-color: #44d72c;
            color: black;
        }
        QListWidget::item:hover, QTreeWidget::item:hover {
            background-color: #2d2d2d;
        }
        QTabWidget::pane {
            border: 1px solid #3d3d3d;
            border-radius: 4px;
        }
        QTabBar::tab {
            background-color: #2d2d2d;
            border: 1px solid #3d3d3d;
            padding: 8px 16px;
            margin-right: 2px;
        }
        QTabBar::tab:selected {
            background-color: #44d72c;
            color: black;
        }
        QTabBar::tab:hover:!selected {
            background-color: #3d3d3d;
        }
        QSlider::groove:horizontal {
            background-color: #2d2d2d;
            height: 6px;
            border-radius: 3px;
        }
        QSlider::handle:horizontal {
            background-color: #44d72c;
            width: 16px;
            margin: -5px 0;
            border-radius: 8px;
        }
        QSlider::sub-page:horizontal {
            background-color: #44d72c;
            border-radius: 3px;
        }
        QScrollBar:vertical {
            background-color: #1a1a1a;
            width: 12px;
            border-radius: 6px;
        }
        QScrollBar::handle:vertical {
            background-color: #3d3d3d;
            min-height: 20px;
            border-radius: 6px;
        }
        QScrollBar::handle:vertical:hover {
            background-color: #44d72c;
        }
        QStatusBar {
            background-color: #141414;
            color: #888888;
        }
    """)
