# Contributing to Razer Control Center

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## How to Contribute

### Reporting Issues

If you find a bug or have a suggestion:

1. Check if the issue already exists in [GitHub Issues](https://github.com/AreteDriver/Razer_Controls/issues)
2. If not, create a new issue with:
   - Clear description of the problem or suggestion
   - Steps to reproduce (for bugs)
   - Your Linux distribution and version
   - Python version and OpenRazer version
   - Any relevant error messages

### Submitting Changes

1. **Fork and clone**
   ```bash
   git clone https://github.com/AreteDriver/Razer_Controls.git
   cd Razer_Controls
   ```

2. **Set up development environment**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e ".[dev]"
   ```

3. **Create a branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

4. **Make your changes**
   - Follow the existing code style
   - Add tests for new functionality
   - Update documentation as needed

5. **Run tests and linting**
   ```bash
   pytest
   ruff check .
   ruff format .
   ```

6. **Commit and push**
   ```bash
   git add .
   git commit -m "Description of changes"
   git push origin feature/your-feature-name
   ```

7. **Create a Pull Request**

## Code Style

- Use `ruff` for linting and formatting
- Follow PEP 8 guidelines
- Use type hints for all functions
- Add docstrings to classes and public methods
- Use `collections.abc.Callable` instead of `typing.Callable`

## Testing

- Write tests for new functionality
- Ensure all existing tests pass (290+ tests)
- Test coverage target: 80%+
- Run tests with: `pytest -v`

## Project Structure

```
Razer_Controls/
├── apps/gui/           # PySide6 GUI application
│   ├── widgets/        # Reusable GUI widgets
│   └── main_window.py  # Main application window
├── crates/             # Core modules
│   ├── profile_schema.py   # Profile data structures
│   ├── keycode_map.py      # Key code mappings
│   └── remap_engine.py     # Input remapping logic
├── services/           # Background services
│   ├── openrazer_bridge/   # OpenRazer D-Bus integration
│   ├── macro_player/       # Macro execution
│   └── app_watcher/        # App-based profile switching
├── tools/              # CLI utilities
└── tests/              # Test suite
```

## Areas for Contribution

### High Priority
- Per-key RGB lighting editor
- Keyboard layout visualizer
- Profile import/export (JSON/YAML)
- More device support

### Medium Priority
- Macro recording from device
- Tray icon with quick profile switching
- Multi-device sync
- Backup/restore functionality

### Nice to Have
- Theme customization
- Localization/translations
- Plugin system
- Cloud sync

## Development Tips

### Running the GUI
```bash
python -m apps.gui
```

### Testing without hardware
The OpenRazer bridge has mock support. Tests run without physical devices.

### Adding a new widget
1. Create widget in `apps/gui/widgets/`
2. Export in `apps/gui/widgets/__init__.py`
3. Add to `apps/gui/main_window.py`
4. Write tests in `tests/test_gui_widgets.py`

## Questions?

- Open an issue for questions
- Check existing issues and discussions

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow

Thank you for contributing!
