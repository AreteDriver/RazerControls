"""Profile panel widget for managing profiles."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QLineEdit, QDialog, QFormLayout, QTextEdit,
    QDialogButtonBox, QMessageBox, QGroupBox
)
from PySide6.QtCore import Qt, Signal

from crates.profile_schema import ProfileLoader, Profile, Layer


class NewProfileDialog(QDialog):
    """Dialog for creating a new profile."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Profile")
        self.setMinimumWidth(300)

        layout = QFormLayout(self)

        self.name_edit = QLineEdit()
        layout.addRow("Name:", self.name_edit)

        self.desc_edit = QTextEdit()
        self.desc_edit.setMaximumHeight(80)
        layout.addRow("Description:", self.desc_edit)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addRow(self.buttons)

    def get_profile(self) -> Profile | None:
        """Get the created profile."""
        name = self.name_edit.text().strip()
        if not name:
            return None

        # Generate ID from name
        profile_id = name.lower().replace(" ", "_")

        return Profile(
            id=profile_id,
            name=name,
            description=self.desc_edit.toPlainText().strip(),
            layers=[Layer(id="base", name="Base Layer", bindings=[])],
        )


class ProfilePanel(QWidget):
    """Panel for managing profiles."""

    profile_selected = Signal(str)  # Emits profile ID
    profile_created = Signal(object)  # Emits Profile
    profile_deleted = Signal(str)  # Emits profile ID

    def __init__(self, parent=None):
        super().__init__(parent)
        self.profile_loader: ProfileLoader | None = None
        self._setup_ui()

    def _setup_ui(self):
        """Set up the widget UI."""
        layout = QVBoxLayout(self)

        # Profile list group
        group = QGroupBox("Profiles")
        group_layout = QVBoxLayout(group)

        self.profile_list = QListWidget()
        self.profile_list.currentRowChanged.connect(self._on_profile_selected)
        group_layout.addWidget(self.profile_list)

        # Buttons
        btn_layout = QHBoxLayout()

        self.new_btn = QPushButton("New")
        self.new_btn.clicked.connect(self._create_profile)
        btn_layout.addWidget(self.new_btn)

        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self._delete_profile)
        self.delete_btn.setEnabled(False)
        btn_layout.addWidget(self.delete_btn)

        group_layout.addLayout(btn_layout)

        # Activate button
        self.activate_btn = QPushButton("Set as Active")
        self.activate_btn.clicked.connect(self._activate_profile)
        self.activate_btn.setEnabled(False)
        group_layout.addWidget(self.activate_btn)

        layout.addWidget(group)

        # Active profile indicator
        self.active_label = QLabel("Active: None")
        self.active_label.setStyleSheet("color: #44d72c; padding: 4px;")
        layout.addWidget(self.active_label)

    def load_profiles(self, loader: ProfileLoader):
        """Load profiles from the loader."""
        self.profile_loader = loader
        self.profile_list.clear()

        active_id = loader.get_active_profile_id()
        profile_ids = loader.list_profiles()

        for profile_id in profile_ids:
            profile = loader.load_profile(profile_id)
            if profile:
                display_name = profile.name
                if profile_id == active_id:
                    display_name += " [Active]"
                    self.active_label.setText(f"Active: {profile.name}")

                item = QListWidgetItem(display_name)
                item.setData(Qt.UserRole, profile_id)
                if profile_id == active_id:
                    item.setForeground(Qt.green)
                self.profile_list.addItem(item)

        if not profile_ids:
            self.active_label.setText("Active: None")

    def _on_profile_selected(self, row: int):
        """Handle profile selection."""
        if row < 0:
            self.delete_btn.setEnabled(False)
            self.activate_btn.setEnabled(False)
            return

        item = self.profile_list.item(row)
        if item:
            profile_id = item.data(Qt.UserRole)
            self.delete_btn.setEnabled(True)
            self.activate_btn.setEnabled(True)
            self.profile_selected.emit(profile_id)

    def _create_profile(self):
        """Create a new profile."""
        dialog = NewProfileDialog(self)
        if dialog.exec() == QDialog.Accepted:
            profile = dialog.get_profile()
            if profile:
                self.profile_created.emit(profile)

    def _delete_profile(self):
        """Delete the selected profile."""
        item = self.profile_list.currentItem()
        if not item:
            return

        profile_id = item.data(Qt.UserRole)
        reply = QMessageBox.question(
            self, "Delete Profile",
            f"Are you sure you want to delete this profile?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.profile_deleted.emit(profile_id)
            if self.profile_loader:
                self.load_profiles(self.profile_loader)

    def _activate_profile(self):
        """Set the selected profile as active."""
        item = self.profile_list.currentItem()
        if not item or not self.profile_loader:
            return

        profile_id = item.data(Qt.UserRole)
        self.profile_loader.set_active_profile(profile_id)
        self.load_profiles(self.profile_loader)
