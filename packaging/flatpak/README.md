# Flatpak Packaging

Build and install Razer Control Center as a Flatpak.

## Prerequisites

```bash
# Install Flatpak and builder
sudo apt install flatpak flatpak-builder

# Add Flathub repo
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo

# Install KDE SDK
flatpak install flathub org.kde.Platform//6.7 org.kde.Sdk//6.7
```

## Build Locally

```bash
cd /path/to/Razer_Controls

# Build the Flatpak
flatpak-builder --force-clean build-dir packaging/flatpak/com.github.AreteDriver.RazerControls.yml

# Install for current user
flatpak-builder --user --install --force-clean build-dir packaging/flatpak/com.github.AreteDriver.RazerControls.yml
```

## Run

```bash
flatpak run com.github.AreteDriver.RazerControls
```

## Uninstall

```bash
flatpak uninstall com.github.AreteDriver.RazerControls
```

## Flathub Submission

To submit to Flathub:

1. Fork [flathub/flathub](https://github.com/flathub/flathub)
2. Create branch `new-pr` with the manifest
3. Copy `com.github.AreteDriver.RazerControls.yml` to the repo root
4. Update source to use git tag instead of local dir:
   ```yaml
   sources:
     - type: git
       url: https://github.com/AreteDriver/Razer_Controls.git
       tag: v1.4.4
   ```
5. Submit PR following [Flathub submission guidelines](https://github.com/flathub/flathub/wiki/App-Submission)

## Files

- `com.github.AreteDriver.RazerControls.yml` - Flatpak manifest
- `com.github.AreteDriver.RazerControls.desktop` - Desktop entry
- `com.github.AreteDriver.RazerControls.metainfo.xml` - AppStream metadata

## Permissions

The Flatpak requires these permissions:

| Permission | Reason |
|------------|--------|
| `--device=all` | Access evdev input devices |
| `--socket=session-bus` | D-Bus for OpenRazer |
| `--socket=system-bus` | System D-Bus access |
| `--filesystem=~/.config/razer-control-center:create` | Store profiles |
| `--talk-name=org.razer` | Communicate with OpenRazer daemon |
