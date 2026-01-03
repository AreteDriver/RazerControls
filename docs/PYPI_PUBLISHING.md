# Publishing Razer Control Center to PyPI

This guide covers everything you need to publish your Razer Control Center to PyPI (Python Package Index).

## Prerequisites

1. **PyPI Account**: Create accounts on both:
   - [PyPI](https://pypi.org/account/register/) (production)
   - [TestPyPI](https://test.pypi.org/account/register/) (testing)

2. **API Tokens**: Generate API tokens for secure uploads:
   - Go to Account Settings → API tokens
   - Create a token with "Entire account" scope (or project-specific after first upload)
   - Save these tokens securely

## Project Structure Changes

Your current project structure needs to be reorganized to follow the `src` layout for PyPI:

```
Razer_Controls/
├── src/
│   └── razer_control_center/      # Main package (rename from current structure)
│       ├── __init__.py            # Package init with version
│       ├── apps/
│       │   └── gui/               # Your existing GUI code
│       ├── services/
│       │   ├── remap_daemon/
│       │   ├── openrazer_bridge/
│       │   ├── app_watcher/
│       │   └── macro_engine/
│       ├── crates/
│       │   ├── profile_schema/
│       │   ├── device_registry/
│       │   └── keycode_map/
│       ├── tools/
│       ├── resources/
│       └── icons/
├── tests/
├── docs/
├── packaging/
├── pyproject.toml                  # Updated for PyPI
├── MANIFEST.in                     # New - for source distribution
├── README.md
├── LICENSE
└── CHANGELOG.md
```

## Step-by-Step Migration

### 1. Create the src layout

```bash
cd ~/projects/Razer_Controls

# Create src directory
mkdir -p src/razer_control_center

# Move your code (adjust based on your actual structure)
mv apps src/razer_control_center/
mv services src/razer_control_center/
mv crates src/razer_control_center/
mv tools src/razer_control_center/

# Create package __init__.py
cat > src/razer_control_center/__init__.py << 'EOF'
"""
Razer Control Center for Linux

A Synapse-like control center for Razer devices on Linux.
Configure button remapping, macros, RGB lighting, and DPI settings.
"""

__version__ = "1.5.0"
__author__ = "AreteDriver"
__license__ = "MIT"

__all__ = ["__version__", "__author__", "__license__"]
EOF
```

### 2. Update imports in your code

After moving to the src layout, update all internal imports:

```python
# Before
from apps.gui import main
from services.remap_daemon import RemapDaemon

# After
from razer_control_center.apps.gui import main
from razer_control_center.services.remap_daemon import RemapDaemon
```

### 3. Replace pyproject.toml

Replace your existing `pyproject.toml` with the provided one. Key changes:
- Added `[build-system]` for setuptools
- Added full `[project]` metadata
- Added `[project.scripts]` for CLI entry points
- Added `[tool.setuptools]` for src layout

### 4. Add MANIFEST.in

Copy the provided `MANIFEST.in` to include non-Python files in your source distribution.

### 5. Create entry point scripts

Ensure your entry points exist. For example:

**src/razer_control_center/apps/gui/main.py:**
```python
def main():
    """Entry point for the GUI application."""
    from razer_control_center.apps.gui.app import RazerControlCenter
    app = RazerControlCenter()
    app.run()

if __name__ == "__main__":
    main()
```

**src/razer_control_center/services/remap_daemon/main.py:**
```python
def main():
    """Entry point for the remap daemon."""
    from razer_control_center.services.remap_daemon.daemon import RemapDaemon
    daemon = RemapDaemon()
    daemon.run()

if __name__ == "__main__":
    main()
```

## Building and Testing

### Build Locally

```bash
# Install build tools
pip install build twine

# Build the package
python -m build

# This creates:
#   dist/razer_control_center-1.5.0.tar.gz  (source distribution)
#   dist/razer_control_center-1.5.0-py3-none-any.whl  (wheel)
```

### Test Installation Locally

```bash
# Create a test virtual environment
python -m venv test_env
source test_env/bin/activate

# Install from the built wheel
pip install dist/razer_control_center-1.5.0-py3-none-any.whl

# Test the CLI commands
razer-control-center --help
razer-remap-daemon --help

# Cleanup
deactivate
rm -rf test_env
```

### Verify Package

```bash
# Check for common issues
python -m twine check dist/*
```

## Publishing

### Configure API Tokens

Create `~/.pypirc`:

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-YOUR-API-TOKEN-HERE

[testpypi]
username = __token__
password = pypi-YOUR-TESTPYPI-TOKEN-HERE
```

Protect the file:
```bash
chmod 600 ~/.pypirc
```

### Publish to TestPyPI First

```bash
# Upload to TestPyPI
python -m twine upload --repository testpypi dist/*

# Test installation from TestPyPI
pip install --index-url https://test.pypi.org/simple/ \
    --extra-index-url https://pypi.org/simple/ \
    razer-control-center
```

### Publish to Production PyPI

```bash
# Upload to PyPI (production)
python -m twine upload dist/*
```

Or use the provided script:
```bash
chmod +x publish.sh
./publish.sh --test   # TestPyPI first
./publish.sh          # Production PyPI
```

## Updating the Package

When releasing a new version:

1. Update version in `src/razer_control_center/__init__.py`
2. Update version in `pyproject.toml`
3. Update `CHANGELOG.md`
4. Clean, build, and upload:

```bash
rm -rf dist/ build/ src/*.egg-info/
python -m build
python -m twine upload dist/*
```

## GitHub Actions (Optional)

Add automatic publishing on release. Create `.github/workflows/publish.yml`:

```yaml
name: Publish to PyPI

on:
  release:
    types: [published]

permissions:
  contents: read

jobs:
  publish:
    runs-on: ubuntu-latest
    environment: pypi
    permissions:
      id-token: write  # Trusted publishing
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install build
      
      - name: Build package
        run: python -m build
      
      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
```

For this to work, configure "Trusted Publishing" on PyPI:
1. Go to your project on PyPI
2. Settings → Publishing
3. Add publisher: GitHub Actions
4. Enter your repository details

## Troubleshooting

### "Package name already exists"
- Choose a unique name (check PyPI first)
- Consider prefixes like `razer-control-center-linux`

### "Invalid distribution"
- Check `pyproject.toml` syntax
- Ensure README.md exists and is valid markdown
- Run `twine check dist/*`

### Import errors after install
- Verify all `__init__.py` files exist
- Check import paths match the new structure
- Ensure entry points reference correct module paths

### Missing files in installation
- Check `MANIFEST.in` for non-Python files
- Verify `[tool.setuptools.package-data]` in pyproject.toml

## Resources

- [Python Packaging User Guide](https://packaging.python.org/)
- [PyPI Help](https://pypi.org/help/)
- [setuptools Documentation](https://setuptools.pypa.io/)
- [Trusted Publishing](https://docs.pypi.org/trusted-publishers/)
