# Razer Control Center for Linux

[![Version](https://img.shields.io/badge/version-1.3.0-blue.svg)](https://github.com/AreteDriver/Razer_Controls/releases)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Linux-orange.svg)]()

A Synapse-like control center for Razer devices on Linux. Configure button remapping, macros, RGB lighting, and DPI settings.

## Features

- **Button Remapping**: Remap mouse buttons and keyboard keys to different keys, chords, or macros
- **Macro Support**: Create and execute macro sequences with key presses, delays, and text input
- **Multi-Layer Bindings**: Support for multiple binding layers with hold-to-shift (Hypershift-like)
- **Profile Management**: Multiple profiles with per-application auto-switching
- **App Watcher**: Automatic profile switching when applications gain focus (X11/GNOME Wayland)
- **OpenRazer Integration**: Control RGB lighting, brightness, and DPI via OpenRazer
- **Wayland Compatible**: Uses evdev/uinput for reliable input remapping under Wayland and X11

## Requirements

- Python 3.10+
- OpenRazer daemon (for lighting/DPI control)
- Linux with evdev and uinput support
- PySide6 (for GUI)

## Installation

### 1. Install OpenRazer

```bash
# Ubuntu/Debian
sudo add-apt-repository ppa:openrazer/stable
sudo apt update
sudo apt install openrazer-daemon openrazer-driver-dkms

# Add yourself to the plugdev group
sudo gpasswd -a $USER plugdev
```

### 2. Install Razer Control Center

```bash
cd ~/projects/Razer_Controls
./install.sh
```

The install script will:
- Create a Python virtual environment
- Install all dependencies
- Set up the systemd user service
- Configure permissions

### 3. Start the Application

```bash
# Start the GUI
razer-control-center

# Or start just the remap daemon
systemctl --user start razer-remap-daemon
```

## Usage

### GUI Overview

1. **Profiles Panel** (left): Create, select, and manage profiles
2. **Devices Tab**: Select which input devices to remap
3. **Bindings Tab**: Configure key/button bindings and macros
4. **Lighting & DPI Tab**: Control OpenRazer device settings
5. **Daemon Tab**: Start/stop the remap daemon service

### Creating a Binding

1. Select a profile (or create a new one)
2. Go to the Bindings tab
3. Click "Add Binding"
4. Select the input key/button (e.g., BTN_SIDE for mouse side button)
5. Choose an action type:
   - **Key**: Output a different key
   - **Chord**: Output multiple keys pressed together
   - **Macro**: Execute a macro sequence
   - **Passthrough**: Pass the original key through
   - **Disabled**: Block the key entirely

### Creating a Macro

1. Go to the Macros sub-tab in Bindings
2. Click "Add Macro"
3. Enter macro steps in the format:
   - `key:A` - Press and release A
   - `down:CTRL` - Hold Ctrl
   - `up:CTRL` - Release Ctrl
   - `delay:100` - Wait 100ms
   - `text:hello` - Type "hello"

### Automatic Profile Switching (App Watcher)

The app watcher automatically switches profiles when you focus different applications.

1. Add `match_process_names` to your profile JSON:
   ```json
   {
     "name": "Gaming",
     "match_process_names": ["steam", "*.exe", "lutris", "wine*"],
     "is_default": false
   }
   ```

2. Set one profile as default (fallback when no match):
   ```json
   {
     "name": "Default",
     "is_default": true
   }
   ```

3. Start the daemon with app watcher enabled:
   ```bash
   razer-remap-daemon --app-watcher
   ```

Pattern matching supports:
- Exact match: `firefox`
- Wildcards: `*.exe`, `steam*`
- Substring: `chrome` matches `com.google.chrome`
- Case-insensitive: `Firefox` matches `firefox`

**Supported backends:**
- X11 (requires `xdotool`)
- GNOME Wayland (uses DBus)

## Architecture

```
razer-control-center/
├── apps/gui/              # PySide6 GUI application
├── services/
│   ├── remap_daemon/      # evdev->uinput remapping engine
│   ├── openrazer_bridge/  # DBus communication with OpenRazer
│   ├── app_watcher/       # Per-app profile switching
│   └── macro_engine/      # Macro recording and playback
├── crates/
│   ├── profile_schema/    # Profile data model
│   ├── device_registry/   # Stable device identification
│   └── keycode_map/       # Key code mapping tables
└── packaging/
    └── systemd/           # Systemd user service
```

## Configuration

Profiles are stored in `~/.config/razer-control-center/profiles/` as JSON files.

## Troubleshooting

### "Permission denied" when grabbing devices

Add yourself to the `input` group:
```bash
sudo usermod -aG input $USER
```
Then log out and back in.

### uinput not available

Load the uinput kernel module:
```bash
sudo modprobe uinput
```

To load automatically on boot, add to `/etc/modules-load.d/uinput.conf`:
```
uinput
```

### OpenRazer not detecting devices

Make sure the OpenRazer daemon is running:
```bash
systemctl --user status openrazer-daemon
```

## License

MIT License
