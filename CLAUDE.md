# Razer_Controls - Project Instructions

## Project Overview
Linux control center for Razer peripherals — profiles, macros, RGB lighting, and per-application switching.

**Stack**: Python, PySide6, D-Bus
**Target**: Razer mice, keyboards, and accessories on Linux

---

## Architecture

### Components
- **apps/gui/** — PySide6 GUI application
- **services/** — Background services (app watcher, profile switcher)
- **tools/** — CLI utilities (device_cli, macro_cli, profile_cli)

---

## Development Workflow

```bash
# Setup
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Run GUI
python -m apps.gui

# Test
pytest

# Lint
ruff check .
ruff format .
```

---

## Code Conventions
- PySide6 signal/slot architecture
- Type hints required (use collections.abc for Callable)
- ruff for linting and formatting
- Keep GUI logic separate from device communication

---

## Adding Device Visuals

To make a device render with its actual appearance in the GUI:

### 1. Create Device Image
Add an SVG (preferred) or PNG to `data/device_images/{category}/`:
```
data/device_images/
├── mice/           # 200x400 base dimensions
├── keyboards/      # 800x300 base dimensions
└── keypads/        # 300x400 base dimensions
```

### 2. Create Device Layout
Add a JSON file to `data/device_layouts/{category}/{device}.json`:
```json
{
  "id": "razer_device_name",
  "name": "Razer Device Name",
  "category": "mouse",
  "device_name_patterns": [".*device.*name.*", ".*DeviceName.*"],
  "base_width": 200,
  "base_height": 400,
  "image_path": "device_images/mice/device_name.svg",
  "buttons": [
    {
      "id": "left_click",
      "label": "Left",
      "x": 0.1,
      "y": 0.05,
      "width": 0.35,
      "height": 0.30,
      "shape_type": "rect",
      "input_code": "BTN_LEFT"
    }
  ]
}
```

### Layout Coordinates
- All coordinates are **normalized (0.0–1.0)** relative to base dimensions
- `x`, `y` = top-left corner of the button
- `shape_type`: `"rect"`, `"ellipse"`, or `"polygon"`
- `is_zone: true` for RGB lighting zones (clickable for color picker)

### Testing
Run the GUI and select your device in the Device View tab to verify alignment.
