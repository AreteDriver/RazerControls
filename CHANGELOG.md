# Changelog

All notable changes to Razer Control Center will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.9.8] - 2026-01-08

### Fixed
- Flatpak build now works (updated KDE runtime to 6.9, added PySide6/PyYAML deps, included data directory)
- OpenRazer bridge now properly detects zone-specific lighting on mice (logo, scroll wheel)
- Lighting controls work on devices like Basilisk V2 that use zone-specific methods

## [1.3.0] - 2025-12-31

### Added
- **Macro Editor Widget** - Visual macro creation and editing
  - Step editor dialog (key press/down/up, delay, text)
  - Drag-drop step reordering
  - Macro properties (name, repeat count, delay)
  - Test macro preview
- **Battery Monitor Widget** - Wireless device battery status
  - Real-time battery level with color-coded progress bars
  - Charging state detection
  - Low battery warnings (configurable threshold)
  - Auto-refresh every 30 seconds
- **DPI Stage Editor Widget** - Visual DPI configuration
  - Configure up to 5 DPI stages with slider/spinbox
  - Preset configurations (Gaming, Productivity, High Precision)
  - Color-coded DPI levels (blue/green/yellow/red)
  - Active stage selector with visual highlighting
- 46 new unit tests for GUI widget logic (252 total tests)

## [1.2.1] - 2025-12-30

### Changed
- Code quality improvements with ruff formatting
- 23 files reformatted for consistency

### Added
- 90 new unit tests for core services (206 total tests)
  - RemapEngine: bindings, layers, macros, state tracking
  - MacroPlayer: all step types, cancellation, speed multiplier
  - OpenRazerBridge: DBus communication, lighting, DPI, battery

## [1.2.0] - 2025-12-30

### Added
- **App Watcher Service** - Automatic profile switching based on active application
  - X11 backend using xdotool
  - GNOME Wayland backend using DBus
  - Pattern matching with wildcards (e.g., `*.exe`, `steam*`)
  - Case-insensitive and substring matching
  - Enable with `--app-watcher` flag on daemon
- **GUI App Matcher** - Visual interface for app-to-profile mapping
- 19 new unit tests for app watcher (62 total tests)

### Usage
Configure profiles with `match_process_names` to enable auto-switching:
```json
{
  "name": "Gaming",
  "match_process_names": ["steam", "*.exe", "lutris"],
  "is_default": false
}
```

Start daemon with app watcher:
```bash
razer-remap-daemon --app-watcher
```

## [1.0.0] - 2025-12-30

### Added
- **Button Remapping Engine** - evdev/uinput-based input remapping
  - Remap mouse buttons and keyboard keys
  - Support for key chords (multiple keys pressed together)
  - Passthrough and disable options
- **Macro System** - Full macro recording and playback
  - Key press/release sequences
  - Configurable delays
  - Text input support
  - Repeat count and delay between repeats
- **Multi-Layer Bindings** - Hypershift-style layer support
  - Hold-to-activate secondary layers
  - Per-layer binding configurations
- **Profile Management** - JSON-based profile system
  - Multiple profiles with easy switching
  - Per-device configurations
  - CLI tool for profile management (`razer-profile`)
- **OpenRazer Integration** - DBus bridge for hardware control
  - RGB lighting effects (spectrum, static, breathing, wave, reactive)
  - DPI adjustment
  - Poll rate control
  - Battery status monitoring
- **System Tray App** - Quick access controls
  - Profile switching
  - Device status monitoring
  - Daemon start/stop
- **GUI Application** - Full PySide6 interface
  - Profile panel with create/edit/delete
  - Device selection and configuration
  - Binding editor with macro support
  - Lighting and DPI controls
- **CLI Tools** - Command-line utilities
  - `razer-profile` - Profile management
  - `razer-device` - Device information and control
  - `razer-macro` - Macro creation and testing
  - `razer-keymap` - Key code reference
- **Comprehensive Key Mapping** - 200+ keys supported
  - Mouse buttons (side, extra, forward, back)
  - All keyboard keys including media keys
  - Numpad keys
  - Function keys F1-F24
- **Wayland Compatible** - Works on both X11 and Wayland

### Technical
- 43 unit tests for key mapping module
- Systemd user service for daemon
- Install script with automatic setup

[Unreleased]: https://github.com/AreteDriver/Razer_Controls/compare/v1.2.0...HEAD
[1.2.0]: https://github.com/AreteDriver/Razer_Controls/compare/v1.0.0...v1.2.0
[1.0.0]: https://github.com/AreteDriver/Razer_Controls/releases/tag/v1.0.0
