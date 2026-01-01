"""Remap daemon - main daemon that grabs devices and runs the remap engine."""

import logging
import selectors
import signal
import sys
from pathlib import Path

from evdev import InputDevice, UInput, ecodes

from crates.device_registry import DeviceRegistry
from crates.profile_schema import Profile, ProfileLoader
from services.app_watcher import AppWatcher

from .engine import RemapEngine

logger = logging.getLogger(__name__)


class RemapDaemon:
    """Main remap daemon - grabs input devices and remaps events."""

    def __init__(self, config_dir: Path | None = None, enable_app_watcher: bool = False):
        self.config_dir = config_dir
        self.profile_loader = ProfileLoader(config_dir)
        self.device_registry = DeviceRegistry(config_dir)
        self.engine: RemapEngine | None = None
        self.uinput: UInput | None = None
        self.grabbed_devices: dict[str, InputDevice] = {}
        self.selector = selectors.DefaultSelector()
        self.running = False
        self.enable_app_watcher = enable_app_watcher
        self.app_watcher: AppWatcher | None = None

    def setup(self) -> bool:
        """Set up the daemon - load profile and create uinput."""
        # Load active profile
        profile = self.profile_loader.load_active_profile()
        if not profile:
            logger.info("No active profile found. Creating default profile...")
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
            self.uinput = UInput(
                capabilities,  # type: ignore[arg-type]
                name="Razer Control Center Virtual Device",
            )
            self.engine.set_uinput(self.uinput)
            logger.info("Created virtual device: %s", self.uinput.name)
        except PermissionError as e:
            logger.error("Permission denied creating uinput device: %s", e)
            logger.error("Make sure the uinput module is loaded and you have permissions.")
            logger.error("Try: sudo modprobe uinput")
            return False
        except OSError as e:
            logger.error("Failed to create uinput device: %s", e)
            logger.error("Try: sudo modprobe uinput")
            return False

        # Grab configured devices
        return self._grab_devices(profile)

    def _create_default_profile(self) -> Profile:
        """Create a default profile with no bindings."""
        from crates.profile_schema import Layer, Profile

        # Get available Razer devices
        devices = self.device_registry.get_razer_devices()
        mouse_devices = [d.stable_id for d in devices if d.is_mouse]

        return Profile(
            id="default",
            name="Default Profile",
            description="Default profile - no remapping",
            input_devices=mouse_devices[:1] if mouse_devices else [],
            layers=[
                Layer(id="base", name="Base Layer", bindings=[], hold_modifier_input_code=None)
            ],
            is_default=True,
        )

    def _grab_devices(self, profile: Profile) -> bool:
        """Grab the input devices specified in the profile."""
        if not profile.input_devices:
            logger.warning("No input devices configured in profile")
            # Scan for Razer devices and show available
            devices = self.device_registry.scan_devices()
            razer_devices = [d for d in devices if "razer" in d.stable_id.lower()]
            if razer_devices:
                logger.info("Available Razer devices:")
                for d in razer_devices:
                    logger.info("  %s", d.stable_id)
                    logger.info("    Name: %s", d.name)
                    logger.info("    Path: %s", d.event_path)
            return False

        grabbed_any = False
        for stable_id in profile.input_devices:
            event_path = self.device_registry.get_event_path(stable_id)
            if not event_path:
                logger.warning("Device not found: %s", stable_id)
                continue

            try:
                dev = InputDevice(event_path)
                dev.grab()
                self.grabbed_devices[stable_id] = dev
                self.selector.register(dev, selectors.EVENT_READ)
                logger.info("Grabbed device: %s (%s)", dev.name, stable_id)
                grabbed_any = True
            except PermissionError:
                logger.error("Permission denied for %s", event_path)
                logger.error("Add yourself to the 'input' group or run with sudo")
            except OSError as e:
                logger.error("Failed to grab %s: %s", stable_id, e)

        return grabbed_any

    def run(self) -> None:
        """Run the daemon main loop."""
        if not self.engine or not self.grabbed_devices:
            logger.error("Daemon not properly set up")
            return

        # Set up signal handlers
        def handle_signal(signum, frame):
            logger.info("Received signal %s, shutting down...", signum)
            self.running = False

        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)

        self.running = True

        # Start app watcher if enabled
        self._start_app_watcher()

        logger.info("Remap daemon running. Press Ctrl+C to stop.")

        try:
            while self.running:
                events = self.selector.select(timeout=0.1)
                for key, _ in events:
                    device = key.fileobj
                    try:
                        for event in device.read():  # type: ignore[union-attr]
                            handled = self.engine.process_event(event)
                            if not handled:
                                # Pass through unhandled events
                                self._passthrough_event(event)
                    except OSError as e:
                        logger.error("Error reading device: %s", e)
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
        logger.info("Cleaning up...")

        # Stop app watcher
        self._stop_app_watcher()

        # Release any held keys first (prevent stuck keys)
        if self.engine:
            self.engine.release_all_keys()

        # Ungrab devices
        for stable_id, dev in self.grabbed_devices.items():
            try:
                dev.ungrab()
                logger.info("Released: %s", stable_id)
            except OSError:
                pass
            try:
                self.selector.unregister(dev)
            except (KeyError, ValueError):
                pass

        self.grabbed_devices.clear()

        # Close uinput
        if self.uinput:
            try:
                self.uinput.close()
            except OSError:
                pass
            self.uinput = None

        self.selector.close()

    def reload_profile(self) -> None:
        """Reload the active profile."""
        profile = self.profile_loader.load_active_profile()
        if profile and self.engine:
            self.engine.reload_profile(profile)
            logger.info("Reloaded profile: %s", profile.name)

    def switch_profile(self, profile: Profile) -> None:
        """Switch to a different profile."""
        if not self.engine:
            return

        # Update the active profile
        self.profile_loader.set_active_profile(profile.id)

        # Reload the engine with new profile
        self.engine.reload_profile(profile)
        logger.info("Switched to profile: %s", profile.name)

    def _start_app_watcher(self) -> None:
        """Start the app watcher if enabled."""
        if not self.enable_app_watcher:
            return

        self.app_watcher = AppWatcher(self.config_dir)
        self.app_watcher.on_profile_change = self.switch_profile

        if self.app_watcher.start():
            logger.info("App watcher enabled (backend: %s)", self.app_watcher.backend_name)
        else:
            logger.warning("App watcher could not start - no backend available")
            self.app_watcher = None

    def _stop_app_watcher(self) -> None:
        """Stop the app watcher if running."""
        if self.app_watcher:
            self.app_watcher.stop()
            self.app_watcher = None


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
    parser.add_argument(
        "--app-watcher",
        action="store_true",
        help="Enable automatic profile switching based on active application",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose (debug) logging",
    )
    args = parser.parse_args()

    # Configure logging for systemd compatibility
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(levelname)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

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

    daemon = RemapDaemon(args.config_dir, enable_app_watcher=args.app_watcher)

    if not daemon.setup():
        logger.error("Failed to set up daemon")
        sys.exit(1)

    daemon.run()


if __name__ == "__main__":
    main()
