"""CLI tool for managing Razer Control Center profiles.

Usage:
    razer-profile list                     # List all profiles
    razer-profile show <profile_id>        # Show profile details
    razer-profile new <name>               # Create a new profile
    razer-profile activate <profile_id>    # Set as active profile
    razer-profile delete <profile_id>      # Delete a profile
    razer-profile copy <source> <dest>     # Copy a profile
    razer-profile export <profile_id>      # Export to stdout
    razer-profile import <file>            # Import from file
"""

import argparse
import json
import sys
from pathlib import Path

from crates.device_registry import DeviceRegistry
from crates.keycode_map import validate_key
from crates.profile_schema import (
    ActionType,
    Layer,
    Profile,
    ProfileLoader,
)


def get_loader(config_dir: Path | None = None) -> ProfileLoader:
    """Get a profile loader instance."""
    return ProfileLoader(config_dir)


def cmd_list(args) -> int:
    """List all profiles."""
    loader = get_loader(args.config_dir)
    profiles = loader.list_profiles()
    active_id = loader.get_active_profile_id()

    if not profiles:
        print("No profiles found.")
        print(f"\nProfiles directory: {loader.profiles_dir}")
        print("Use 'razer-profile new <name>' to create one.")
        return 0

    print(f"\n{'ID':<20} {'Name':<30} {'Layers':<8} {'Status'}")
    print("-" * 70)

    for pid in profiles:
        profile = loader.load_profile(pid)
        if profile:
            status = ""
            if pid == active_id:
                status = "[ACTIVE]"
            elif profile.is_default:
                status = "[default]"

            print(f"{pid:<20} {profile.name:<30} {len(profile.layers):<8} {status}")

    print(f"\n{len(profiles)} profile(s) found.")
    return 0


def cmd_show(args) -> int:
    """Show detailed profile information."""
    loader = get_loader(args.config_dir)
    profile = loader.load_profile(args.profile_id)

    if not profile:
        print(f"Error: Profile '{args.profile_id}' not found.")
        return 1

    active_id = loader.get_active_profile_id()
    is_active = profile.id == active_id

    print(f"\n{'=' * 60}")
    print(f"Profile: {profile.name}")
    print(f"{'=' * 60}")
    print(f"ID:          {profile.id}")
    print(f"Description: {profile.description or '(none)'}")
    print(f"Active:      {'Yes' if is_active else 'No'}")
    print(f"Default:     {'Yes' if profile.is_default else 'No'}")

    # Input devices
    print(f"\nInput Devices ({len(profile.input_devices)}):")
    if profile.input_devices:
        for dev in profile.input_devices:
            print(f"  - {dev}")
    else:
        print("  (none configured)")

    # Layers
    print(f"\nLayers ({len(profile.layers)}):")
    for layer in profile.layers:
        hold_code = layer.hold_modifier_input_code
        modifier = f" [hold: {hold_code}]" if hold_code else ""
        print(f"\n  {layer.name} (id: {layer.id}){modifier}")
        print(f"  {'-' * 40}")

        if layer.bindings:
            for binding in layer.bindings:
                action = binding.action_type.value
                if binding.output_keys:
                    output = " + ".join(binding.output_keys)
                elif binding.macro_id:
                    output = f"macro:{binding.macro_id}"
                else:
                    output = "(none)"
                print(f"    {binding.input_code:<15} -> [{action:<10}] {output}")
        else:
            print("    (no bindings)")

    # Macros
    if profile.macros:
        print(f"\nMacros ({len(profile.macros)}):")
        for macro in profile.macros:
            print(f"  - {macro.id}: {macro.name} ({len(macro.steps)} steps)")

    # Process matching
    if profile.match_process_names:
        print("\nAuto-activate for processes:")
        for proc in profile.match_process_names:
            print(f"  - {proc}")

    print()
    return 0


def cmd_new(args) -> int:
    """Create a new profile."""
    loader = get_loader(args.config_dir)

    # Generate ID from name
    profile_id = args.name.lower().replace(" ", "_")
    profile_id = "".join(c for c in profile_id if c.isalnum() or c == "_")

    # Check if exists
    if loader.load_profile(profile_id):
        print(f"Error: Profile '{profile_id}' already exists.")
        return 1

    # Get available devices if requested
    input_devices = []
    if args.auto_detect:
        registry = DeviceRegistry(args.config_dir)
        devices = registry.get_razer_devices()
        mouse_devices = [d.stable_id for d in devices if d.is_mouse]
        if mouse_devices:
            input_devices = mouse_devices[:1]
            print(f"Auto-detected device: {input_devices[0]}")

    # Create profile
    profile = Profile(
        id=profile_id,
        name=args.name,
        description=args.description or "",
        input_devices=input_devices,
        layers=[Layer(id="base", name="Base Layer", bindings=[])],
        is_default=args.default,
    )

    if loader.save_profile(profile):
        print(f"Created profile: {profile_id}")
        print(f"  Name: {profile.name}")
        print(f"  Path: {loader.profiles_dir / f'{profile_id}.json'}")

        if args.activate:
            loader.set_active_profile(profile_id)
            print("  Status: ACTIVE")

        return 0
    else:
        print("Error: Failed to save profile.")
        return 1


def cmd_activate(args) -> int:
    """Set a profile as active."""
    loader = get_loader(args.config_dir)

    # Check profile exists
    profile = loader.load_profile(args.profile_id)
    if not profile:
        print(f"Error: Profile '{args.profile_id}' not found.")
        return 1

    loader.set_active_profile(args.profile_id)
    print(f"Activated profile: {profile.name} ({args.profile_id})")

    # Hint about reloading daemon
    print("\nNote: Restart the remap daemon to apply changes:")
    print("  systemctl --user restart razer-remap-daemon")

    return 0


def cmd_delete(args) -> int:
    """Delete a profile."""
    loader = get_loader(args.config_dir)

    # Check profile exists
    profile = loader.load_profile(args.profile_id)
    if not profile:
        print(f"Error: Profile '{args.profile_id}' not found.")
        return 1

    # Confirmation
    if not args.force:
        print(f"Delete profile '{profile.name}' ({args.profile_id})? [y/N] ", end="")
        response = input().strip().lower()
        if response not in ("y", "yes"):
            print("Cancelled.")
            return 0

    # Check if active
    active_id = loader.get_active_profile_id()
    if args.profile_id == active_id:
        print("Warning: Deleting the active profile.")

    if loader.delete_profile(args.profile_id):
        print(f"Deleted profile: {args.profile_id}")
        return 0
    else:
        print("Error: Failed to delete profile.")
        return 1


def cmd_copy(args) -> int:
    """Copy a profile to a new ID."""
    loader = get_loader(args.config_dir)

    # Load source
    source = loader.load_profile(args.source_id)
    if not source:
        print(f"Error: Source profile '{args.source_id}' not found.")
        return 1

    # Check dest doesn't exist
    if loader.load_profile(args.dest_id):
        print(f"Error: Destination profile '{args.dest_id}' already exists.")
        return 1

    # Create copy
    copy_data = source.model_dump()
    copy_data["id"] = args.dest_id
    copy_data["name"] = args.name or f"{source.name} (Copy)"
    copy_data["is_default"] = False

    copy_profile = Profile.model_validate(copy_data)

    if loader.save_profile(copy_profile):
        print(f"Copied '{args.source_id}' to '{args.dest_id}'")
        return 0
    else:
        print("Error: Failed to save copied profile.")
        return 1


def cmd_export(args) -> int:
    """Export a profile to stdout as JSON."""
    loader = get_loader(args.config_dir)

    profile = loader.load_profile(args.profile_id)
    if not profile:
        print(f"Error: Profile '{args.profile_id}' not found.", file=sys.stderr)
        return 1

    data = profile.model_dump(mode="json")
    print(json.dumps(data, indent=2))
    return 0


def cmd_import(args) -> int:
    """Import a profile from a JSON file."""
    loader = get_loader(args.config_dir)

    # Read file
    try:
        if args.file == "-":
            data = json.load(sys.stdin)
        else:
            path = Path(args.file)
            if not path.exists():
                print(f"Error: File not found: {args.file}")
                return 1
            data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON: {e}")
        return 1

    # Validate
    try:
        profile = Profile.model_validate(data)
    except Exception as e:
        print(f"Error: Invalid profile data: {e}")
        return 1

    # Check for existing
    if loader.load_profile(profile.id) and not args.force:
        print(f"Error: Profile '{profile.id}' already exists. Use --force to overwrite.")
        return 1

    if loader.save_profile(profile):
        print(f"Imported profile: {profile.id}")
        print(f"  Name: {profile.name}")
        return 0
    else:
        print("Error: Failed to save profile.")
        return 1


def cmd_validate(args) -> int:
    """Validate a profile's bindings."""
    loader = get_loader(args.config_dir)

    profile = loader.load_profile(args.profile_id)
    if not profile:
        print(f"Error: Profile '{args.profile_id}' not found.")
        return 1

    errors = []
    warnings = []

    print(f"\nValidating: {profile.name} ({profile.id})")
    print("-" * 50)

    # Check input devices
    if not profile.input_devices:
        warnings.append("No input devices configured")

    # Check layers
    for layer in profile.layers:
        for binding in layer.bindings:
            # Validate input code
            valid, msg = validate_key(binding.input_code)
            if not valid:
                errors.append(f"Layer '{layer.name}': {msg}")

            # Validate output keys
            for key in binding.output_keys:
                valid, msg = validate_key(key)
                if not valid:
                    errors.append(
                        f"Layer '{layer.name}' binding {binding.input_code}: output key {msg}"
                    )

            # Check macro references
            if binding.action_type == ActionType.MACRO and binding.macro_id:
                macro_ids = [m.id for m in profile.macros]
                if binding.macro_id not in macro_ids:
                    errors.append(f"Layer '{layer.name}': macro '{binding.macro_id}' not found")

        # Validate hold modifier
        if layer.hold_modifier_input_code:
            valid, msg = validate_key(layer.hold_modifier_input_code)
            if not valid:
                errors.append(f"Layer '{layer.name}' hold modifier: {msg}")

    # Print results
    if errors:
        print("\nErrors:")
        for err in errors:
            print(f"  ✗ {err}")

    if warnings:
        print("\nWarnings:")
        for warn in warnings:
            print(f"  ⚠ {warn}")

    if not errors and not warnings:
        print("  ✓ Profile is valid")

    print(f"\n{len(errors)} errors, {len(warnings)} warnings")
    return 1 if errors else 0


def cmd_devices(args) -> int:
    """List available input devices."""
    registry = DeviceRegistry(args.config_dir)
    devices = registry.scan_devices()

    razer_devices = [d for d in devices if "razer" in d.stable_id.lower()]

    if not razer_devices:
        print("No Razer devices found.")
        print("\nAll input devices:")
        for d in devices[:10]:
            print(f"  {d.stable_id}")
        return 0

    print("\nRazer Devices:")
    print("-" * 60)

    for d in razer_devices:
        device_type = []
        if d.is_mouse:
            device_type.append("mouse")
        if d.is_keyboard:
            device_type.append("keyboard")
        type_str = ", ".join(device_type) if device_type else "other"

        print(f"\n  {d.stable_id}")
        print(f"    Name: {d.name}")
        print(f"    Type: {type_str}")
        print(f"    Path: {d.event_path}")

    print(f"\n{len(razer_devices)} Razer device(s) found.")
    return 0


def main():
    parser = argparse.ArgumentParser(
        prog="razer-profile",
        description="Manage Razer Control Center profiles",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s list                          List all profiles
  %(prog)s show default                  Show details of 'default' profile
  %(prog)s new "Gaming Profile"          Create a new profile
  %(prog)s new "FPS" --activate          Create and activate a profile
  %(prog)s activate gaming               Set 'gaming' as active
  %(prog)s delete old_profile            Delete a profile
  %(prog)s copy gaming gaming_backup     Copy a profile
  %(prog)s export gaming > backup.json   Export to file
  %(prog)s import backup.json            Import from file
  %(prog)s validate gaming               Validate bindings
  %(prog)s devices                       List available devices
""",
    )

    parser.add_argument(
        "--config-dir",
        "-c",
        type=Path,
        help="Config directory (default: ~/.config/razer-control-center)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # list
    sub_list = subparsers.add_parser("list", help="List all profiles")
    sub_list.set_defaults(func=cmd_list)

    # show
    sub_show = subparsers.add_parser("show", help="Show profile details")
    sub_show.add_argument("profile_id", help="Profile ID to show")
    sub_show.set_defaults(func=cmd_show)

    # new
    sub_new = subparsers.add_parser("new", help="Create a new profile")
    sub_new.add_argument("name", help="Profile name")
    sub_new.add_argument("--description", "-d", help="Profile description")
    sub_new.add_argument("--activate", "-a", action="store_true", help="Activate after creation")
    sub_new.add_argument("--default", action="store_true", help="Set as default profile")
    sub_new.add_argument("--auto-detect", action="store_true", help="Auto-detect Razer devices")
    sub_new.set_defaults(func=cmd_new)

    # activate
    sub_activate = subparsers.add_parser("activate", help="Set profile as active")
    sub_activate.add_argument("profile_id", help="Profile ID to activate")
    sub_activate.set_defaults(func=cmd_activate)

    # delete
    sub_delete = subparsers.add_parser("delete", help="Delete a profile")
    sub_delete.add_argument("profile_id", help="Profile ID to delete")
    sub_delete.add_argument("--force", "-f", action="store_true", help="Skip confirmation")
    sub_delete.set_defaults(func=cmd_delete)

    # copy
    sub_copy = subparsers.add_parser("copy", help="Copy a profile")
    sub_copy.add_argument("source_id", help="Source profile ID")
    sub_copy.add_argument("dest_id", help="Destination profile ID")
    sub_copy.add_argument("--name", "-n", help="Name for the copy")
    sub_copy.set_defaults(func=cmd_copy)

    # export
    sub_export = subparsers.add_parser("export", help="Export profile to JSON")
    sub_export.add_argument("profile_id", help="Profile ID to export")
    sub_export.set_defaults(func=cmd_export)

    # import
    sub_import = subparsers.add_parser("import", help="Import profile from JSON")
    sub_import.add_argument("file", help="JSON file to import (use - for stdin)")
    sub_import.add_argument("--force", "-f", action="store_true", help="Overwrite existing")
    sub_import.set_defaults(func=cmd_import)

    # validate
    sub_validate = subparsers.add_parser("validate", help="Validate profile bindings")
    sub_validate.add_argument("profile_id", help="Profile ID to validate")
    sub_validate.set_defaults(func=cmd_validate)

    # devices
    sub_devices = subparsers.add_parser("devices", help="List available input devices")
    sub_devices.set_defaults(func=cmd_devices)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
