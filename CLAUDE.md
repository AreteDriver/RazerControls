# Razer_Controls - Project Instructions

## Project Overview
Linux control center for Razer peripherals — profiles, macros, RGB lighting, and per-application switching.

**Stack**: Python, PyQt6, D-Bus
**Target**: Razer mice, keyboards, and accessories on Linux

---

## Architecture

### Components
- **apps/gui/** — PyQt6 GUI application
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
- PyQt6 signal/slot architecture
- Type hints required (use collections.abc for Callable)
- ruff for linting and formatting
- Keep GUI logic separate from device communication
