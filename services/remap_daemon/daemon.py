"""Remap daemon - main daemon that grabs devices and runs the remap engine."""

import selectors
import signal
import sys
from pathlib import Path
from typing import Optional

from evdev import InputDevice, UInput, ecodes, list_devices

from crates.profile_schema import ProfileLoader, Profile
from crates.device_registry import DeviceRegistry
from .engine import RemapEngine


class RemapDaemon:
    """Main remap daemon - grabs input devices and remaps events."""

    def __init__(self, config_dir: Optional[Path] = None):
        self.profile_loader = ProfileLoader(config_dir)
        self.device_registry = DeviceRegistry(config_dir)
        self.engine: Optional[RemapEngine] = None
        self.uinput: Optional[UInput] = None
        self.grabbed_devices: dict[str, InputDevice] = {}
        self.selector = selectors.DefaultSelector()
        self.running = False

    def setup(self) -> bool:
        """Set up the daemon - load profile and create uinput."""
        # Load active profile
        profile = self.profile_loader.load_active_profile()
        if not profile:
            print("No active profile found. Creating default profile...")
            profile = self._create_default_profile()
            self.profile_loader.save_profile(profile)
            self.profile_loader.set_active_profile(profile.id)

        # Create remap engine
        self.engine = RemapEngine(profile)

        # Create uinput device
        try:
            # Include all possible keys we might emit
            capabilities = {
                ecodes.EV_KEY: list(range(0, 256)) + list(range(0x110, 0x120)),
                ecodes.EV_REL: [ecodes.REL_X, ecodes.REL_Y, ecodes.REL_WHEEL, ecodes.REL_HWHEEL],
            }
            self.uinput = UInput(capabilities, name="Razer Control Center Virtual Device")
            self.engine.set_uinput(self.uinput)
            print(f"Created virtual device: {self.uinput.name}")
        except Exception as e:
            print(f"Failed to create uinput device: {e}")
            print("Make sure the uinput module is loaded and you have permissions.")
            print("Try: sudo modprobe uinput")
            return False

        # Grab configured devices
        return self._grab_devices(profile)

    def _create_default_profile(self) -> Profile:
        """Create a default profile with no bindings."""
        from crates.profile_schema import Profile, Layer

        # Get available Razer devices
        devices = self.device_registry.get_razer_devices()
        mouse_devices = [d.stable_id for d in devices if d.is_mouse]

        return Profile(
            id="default",
            name="Default Profile",
            description="Default profile - no remapping",
            input_devices=mouse_devices[:1] if mouse_devices else [],
            layers=[
                Layer(id="base", name="Base Layer", bindings=[])
            ],
            is_default=True,
        )

    def _grab_devices(self, profile: Profile) -> bool:
        """Grab the input devices specified in the profile."""
        if not profile.input_devices:
            print("No input devices configured in profile")
            # Scan for Razer devices and show available
            devices = self.device_registry.scan_devices()
            razer_devices = [d for d in devices if "razer" in d.stable_id.lower()]
            if razer_devices:
                print("\nAvailable Razer devices:")
                for d in razer_devices:
                    print(f"  {d.stable_id}")
                    print(f"    Name: {d.name}")
                    print(f"    Path: {d.event_path}")
            return False

        grabbed_any = False
        for stable_id in profile.input_devices:
            event_path = self.device_registry.get_event_path(stable_id)
            if not event_path:
                print(f"Device not found: {stable_id}")
                continue

            try:
                dev = InputDevice(event_path)
                dev.grab()
                self.grabbed_devices[stable_id] = dev
                self.selector.register(dev, selectors.EVENT_READ)
                print(f"Grabbed device: {dev.name} ({stable_id})")
                grabbed_any = True
            except PermissionError:
                print(f"Permission denied for {event_path}")
                print("Add yourself to the 'input' group or run with sudo")
            except Exception as e:
                print(f"Failed to grab {stable_id}: {e}")

        return grabbed_any

    def run(self) -> None:
        """Run the daemon main loop."""
        if not self.engine or not self.grabbed_devices:
            print("Daemon not properly set up")
            return

        # Set up signal handlers
        def handle_signal(signum, frame):
            print("\nShutting down...")
            self.running = False

        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)

        self.running = True
        print("Remap daemon running. Press Ctrl+C to stop.")

        try:
            while self.running:
                events = self.selector.select(timeout=0.1)
                for key, _ in events:
                    device = key.fileobj
                    try:
                        for event in device.read():
                            handled = self.engine.process_event(event)
                            if not handled:
                                # Pass through unhandled events
                                self._passthrough_event(event)
                    except Exception as e:
                        print(f"Error reading device: {e}")
        finally:
            self.cleanup()

    def _passthrough_event(self, event) -> None:
        """Pass through an event to the virtual device."""
        if self.uinput:
            self.uinput.write_event(event)
            if event.type != ecodes.EV_SYN:
                self.uinput.syn()

    def cleanup(self) -> None:
        """Clean up resources."""
        print("Cleaning up...")

        # Release any held keys first (prevent stuck keys)
        if self.engine:
            self.engine.release_all_keys()

        # Ungrab devices
        for stable_id, dev in self.grabbed_devices.items():
            try:
                dev.ungrab()
                print(f"Released: {stable_id}")
            except Exception:
                pass
            try:
                self.selector.unregister(dev)
            except Exception:
                pass

        self.grabbed_devices.clear()

        # Close uinput
        if self.uinput:
            try:
                self.uinput.close()
            except Exception:
                pass
            self.uinput = None

        self.selector.close()

    def reload_profile(self) -> None:
        """Reload the active profile."""
        profile = self.profile_loader.load_active_profile()
        if profile and self.engine:
            self.engine.reload_profile(profile)
            print(f"Reloaded profile: {profile.name}")


def main():
    """Main entry point for the remap daemon."""
    import argparse

    parser = argparse.ArgumentParser(description="Razer Control Center Remap Daemon")
    parser.add_argument(
        "--config-dir",
        type=Path,
        help="Config directory path",
    )
    parser.add_argument(
        "--list-devices",
        action="store_true",
        help="List available input devices and exit",
    )
    args = parser.parse_args()

    if args.list_devices:
        registry = DeviceRegistry(args.config_dir)
        devices = registry.scan_devices()
        print("Available input devices:\n")
        for d in devices:
            device_type = []
            if d.is_mouse:
                device_type.append("mouse")
            if d.is_keyboard:
                device_type.append("keyboard")
            type_str = ", ".join(device_type) if device_type else "other"

            print(f"{d.stable_id}")
            print(f"  Name: {d.name}")
            print(f"  Type: {type_str}")
            print(f"  Path: {d.event_path}")
            print()
        return

    daemon = RemapDaemon(args.config_dir)

    if not daemon.setup():
        print("Failed to set up daemon")
        sys.exit(1)

    daemon.run()


if __name__ == "__main__":
    main()
