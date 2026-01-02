#!/bin/bash
# Razer Control Center installation script

set -e

echo "=== Razer Control Center Installation ==="
echo

# Check for required system packages
echo "Checking system dependencies..."

check_command() {
    if ! command -v "$1" &> /dev/null; then
        echo "  ✗ $1 not found"
        return 1
    else
        echo "  ✓ $1 found"
        return 0
    fi
}

MISSING=0
check_command python3 || MISSING=1
check_command pip3 || MISSING=1

# Check for python3-gi (required for DBus/OpenRazer)
if python3 -c "import gi" 2>/dev/null; then
    echo "  ✓ python3-gi found"
else
    echo "  ✗ python3-gi not found"
    MISSING=1
fi

if [ $MISSING -eq 1 ]; then
    echo
    echo "Please install missing dependencies first."
    echo "On Ubuntu/Debian: sudo apt install python3 python3-pip python3-venv python3-gi"
    exit 1
fi

# Check for uinput module
echo
echo "Checking uinput module..."
if ! lsmod | grep -q uinput; then
    echo "  Loading uinput module..."
    sudo modprobe uinput
fi
echo "  ✓ uinput module loaded"

# Check for input group membership
echo
echo "Checking permissions..."
if groups | grep -q input; then
    echo "  ✓ User is in 'input' group"
else
    echo "  ! User is not in 'input' group"
    echo "  Adding user to input group..."
    sudo usermod -aG input "$USER"
    echo "  You may need to log out and back in for this to take effect."
fi

# Create virtual environment (with system packages for PyGObject/DBus)
echo
echo "Creating Python virtual environment..."
python3 -m venv --system-site-packages .venv
source .venv/bin/activate

# Install package
echo
echo "Installing Razer Control Center..."
pip install -e .

# Create config directory
echo
echo "Creating config directory..."
mkdir -p ~/.config/razer-control-center/profiles

# Install systemd service
echo
echo "Installing systemd user service..."
mkdir -p ~/.config/systemd/user
cp packaging/systemd/razer-remap-daemon.service ~/.config/systemd/user/

# Create wrapper script that uses the venv
INSTALL_DIR="$(pwd)"
mkdir -p ~/.local/bin

cat > ~/.local/bin/razer-remap-daemon << EOF
#!/bin/bash
source "$INSTALL_DIR/.venv/bin/activate"
exec python -m services.remap_daemon.daemon "\$@"
EOF
chmod +x ~/.local/bin/razer-remap-daemon

cat > ~/.local/bin/razer-control-center << EOF
#!/bin/bash
source "$INSTALL_DIR/.venv/bin/activate"
exec python -m apps.gui.main "\$@"
EOF
chmod +x ~/.local/bin/razer-control-center

# Create tray wrapper script
cat > ~/.local/bin/razer-tray << EOF
#!/bin/bash
source "$INSTALL_DIR/.venv/bin/activate"
exec python -m apps.tray.main "\$@"
EOF
chmod +x ~/.local/bin/razer-tray

# Reload systemd
systemctl --user daemon-reload

# Install desktop entries
echo
echo "Installing desktop entries..."
mkdir -p ~/.local/share/applications
cp packaging/razer-control-center.desktop ~/.local/share/applications/
cp packaging/razer-tray.desktop ~/.local/share/applications/

# Install tray autostart entry
mkdir -p ~/.config/autostart
cp packaging/razer-tray.desktop ~/.config/autostart/

# Update desktop database
if command -v update-desktop-database &> /dev/null; then
    update-desktop-database ~/.local/share/applications 2>/dev/null || true
fi

echo "  ✓ Desktop entries installed"

echo
echo "=== Installation Complete ==="
echo
echo "Commands installed:"
echo "  razer-control-center  - Start the GUI"
echo "  razer-tray            - Start the system tray app"
echo "  razer-remap-daemon    - Start the remap daemon (usually via systemd)"
echo
echo "Desktop entries installed:"
echo "  Razer Control Center  - Available in your applications menu"
echo "  Razer Tray            - Starts automatically on login"
echo
echo "To start the daemon:"
echo "  systemctl --user start razer-remap-daemon"
echo
echo "To enable on login:"
echo "  systemctl --user enable razer-remap-daemon"
echo
echo "To start the GUI:"
echo "  razer-control-center"
echo
