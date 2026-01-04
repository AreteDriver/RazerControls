"""Profile panel widget for managing profiles."""

import json
from datetime import datetime
from pathlib import Path

import yaml
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from crates.profile_schema import Layer, Profile, ProfileLoader

# Export format version
EXPORT_VERSION = "1.0"


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
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
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
            layers=[
                Layer(id="base", name="Base Layer", bindings=[], hold_modifier_input_code=None)
            ],
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

        # Buttons row 1: New, Delete
        btn_layout = QHBoxLayout()

        self.new_btn = QPushButton("New")
        self.new_btn.clicked.connect(self._create_profile)
        btn_layout.addWidget(self.new_btn)

        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self._delete_profile)
        self.delete_btn.setEnabled(False)
        btn_layout.addWidget(self.delete_btn)

        group_layout.addLayout(btn_layout)

        # Buttons row 2: Import, Export
        io_layout = QHBoxLayout()

        self.import_btn = QPushButton("Import")
        self.import_btn.clicked.connect(self._import_profile)
        io_layout.addWidget(self.import_btn)

        self.export_btn = QPushButton("Export")
        self.export_btn.clicked.connect(self._export_profile)
        self.export_btn.setEnabled(False)
        io_layout.addWidget(self.export_btn)

        group_layout.addLayout(io_layout)

        # Activate button
        self.activate_btn = QPushButton("Set as Active")
        self.activate_btn.clicked.connect(self._activate_profile)
        self.activate_btn.setEnabled(False)
        group_layout.addWidget(self.activate_btn)

        layout.addWidget(group)

        # Active profile indicator
        self.active_label = QLabel("Active: None")
        self.active_label.setStyleSheet("color: #2da05a; padding: 4px;")
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
                item.setData(Qt.ItemDataRole.UserRole, profile_id)
                if profile_id == active_id:
                    item.setForeground(Qt.GlobalColor.green)
                self.profile_list.addItem(item)

        if not profile_ids:
            self.active_label.setText("Active: None")

    def _on_profile_selected(self, row: int):
        """Handle profile selection."""
        if row < 0:
            self.delete_btn.setEnabled(False)
            self.activate_btn.setEnabled(False)
            self.export_btn.setEnabled(False)
            return

        item = self.profile_list.item(row)
        if item:
            profile_id = item.data(Qt.ItemDataRole.UserRole)
            self.delete_btn.setEnabled(True)
            self.activate_btn.setEnabled(True)
            self.export_btn.setEnabled(True)
            self.profile_selected.emit(profile_id)

    def _create_profile(self):
        """Create a new profile."""
        dialog = NewProfileDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
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
            self,
            "Delete Profile",
            "Are you sure you want to delete this profile?",
            QMessageBox.Yes | QMessageBox.No,
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

    def _import_profile(self):
        """Import a profile from a file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Profile",
            str(Path.home()),
            "Profile Files (*.json *.yaml *.yml);;JSON Files (*.json);;YAML Files (*.yaml *.yml)",
        )

        if not file_path:
            return

        path = Path(file_path)
        try:
            content = path.read_text()
            suffix = path.suffix.lower()

            # Parse based on extension
            if suffix in (".yaml", ".yml"):
                data = yaml.safe_load(content)
            else:
                data = json.loads(content)

            # Handle wrapped format with metadata
            if isinstance(data, dict) and "profile" in data and "_export" in data:
                data = data["profile"]

            profile = Profile.model_validate(data)

            # Check if profile already exists
            if self.profile_loader and self.profile_loader.load_profile(profile.id):
                reply = QMessageBox.question(
                    self,
                    "Profile Exists",
                    f"Profile '{profile.id}' already exists. Overwrite?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return

            # Save the profile
            if self.profile_loader and self.profile_loader.save_profile(profile):
                QMessageBox.information(
                    self,
                    "Import Successful",
                    f"Imported profile: {profile.name}",
                )
                self.load_profiles(self.profile_loader)
                self.profile_created.emit(profile)
            else:
                QMessageBox.warning(self, "Import Failed", "Failed to save the imported profile.")

        except (json.JSONDecodeError, yaml.YAMLError) as e:
            QMessageBox.critical(self, "Import Error", f"Invalid file format:\n{e}")
        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Failed to import profile:\n{e}")

    def _export_profile(self):
        """Export the selected profile to a file."""
        item = self.profile_list.currentItem()
        if not item or not self.profile_loader:
            return

        profile_id = item.data(Qt.ItemDataRole.UserRole)
        profile = self.profile_loader.load_profile(profile_id)
        if not profile:
            return

        # Ask for save location
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export Profile",
            str(Path.home() / f"{profile_id}.json"),
            "JSON Files (*.json);;YAML Files (*.yaml)",
        )

        if not file_path:
            return

        path = Path(file_path)

        # Determine format from extension
        suffix = path.suffix.lower()
        if suffix in (".yaml", ".yml"):
            fmt = "yaml"
        else:
            fmt = "json"
            # Ensure .json extension
            if suffix != ".json":
                path = path.with_suffix(".json")

        try:
            # Build export data with metadata
            data = profile.model_dump(mode="json")
            export_data = {
                "_export": {
                    "version": EXPORT_VERSION,
                    "exported_at": datetime.now().isoformat(),
                    "format": fmt,
                },
                "profile": data,
            }

            # Serialize
            if fmt == "yaml":
                content = yaml.dump(
                    export_data, default_flow_style=False, sort_keys=False, allow_unicode=True
                )
            else:
                content = json.dumps(export_data, indent=2)

            path.write_text(content)

            QMessageBox.information(
                self,
                "Export Successful",
                f"Exported '{profile.name}' to:\n{path}",
            )

        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export profile:\n{e}")
