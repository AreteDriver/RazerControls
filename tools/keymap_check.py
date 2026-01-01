"""CLI tool for checking keycode mappings and validating profiles.

Usage:
    python -m tools.keymap_check --list                    # List all available keys
    python -m tools.keymap_check --list --category Mouse   # List keys in a category
    python -m tools.keymap_check --info KEY_A              # Get info about a specific key
    python -m tools.keymap_check --validate profile.json   # Validate a profile
    python -m tools.keymap_check --check CTRL+SHIFT+A      # Check if a chord is valid
"""

import argparse
import json
import sys
from pathlib import Path

from crates.keycode_map import (
    get_all_evdev_keys,
    get_all_schema_keys,
    get_key_info,
    get_keys_by_category,
    validate_key,
)


def cmd_list(args):
    """List available keys."""
    if args.category:
        categories = get_keys_by_category()
        if args.category not in categories:
            print(f"Unknown category: {args.category}")
            print(f"Available categories: {', '.join(categories.keys())}")
            return 1

        print(f"\n{args.category} Keys:")
        print("-" * 40)
        for key in categories[args.category]:
            info = get_key_info(key)
            code = info["code"] if info else "?"
            print(f"  {key:<20} (code={code})")
    elif args.evdev:
        print("\nAll evdev key names:")
        print("-" * 40)
        for key in get_all_evdev_keys():
            print(f"  {key}")
        print(f"\nTotal: {len(get_all_evdev_keys())} keys")
    elif args.categories:
        print("\nAvailable categories:")
        print("-" * 40)
        categories = get_keys_by_category()
        for cat, keys in categories.items():
            print(f"  {cat:<15} ({len(keys)} keys)")
    else:
        print("\nAll schema key names (human-friendly):")
        print("-" * 40)
        keys = get_all_schema_keys()
        # Print in columns
        col_width = 20
        cols = 4
        for i in range(0, len(keys), cols):
            row = keys[i : i + cols]
            print("  " + "".join(k.ljust(col_width) for k in row))
        print(f"\nTotal: {len(keys)} keys")

    return 0


def cmd_info(args):
    """Get detailed info about a key."""
    key_name = args.key

    info = get_key_info(key_name)
    if not info:
        valid, msg = validate_key(key_name)
        print(f"Error: {msg}")
        return 1

    print(f"\nKey Information: {key_name}")
    print("-" * 40)
    print(f"  Schema name:  {info['schema_name']}")
    print(f"  evdev name:   {info['evdev_name']}")
    print(f"  Code:         {info['code']}")
    print(f"  Category:     {info['category']}")

    return 0


def cmd_check(args):
    """Check if a key or chord is valid."""
    chord = args.chord

    # Split by + for chords
    keys = [k.strip() for k in chord.split("+")]

    all_valid = True
    print(f"\nChecking: {chord}")
    print("-" * 40)

    for key in keys:
        valid, msg = validate_key(key)
        status = "✓" if valid else "✗"
        print(f"  {status} {key}: {msg}")
        if not valid:
            all_valid = False

    if all_valid:
        print(f"\n✓ Valid chord: {' + '.join(keys)}")
        return 0
    else:
        print("\n✗ Invalid chord")
        return 1


def cmd_validate(args):
    """Validate a profile JSON file."""
    profile_path = Path(args.profile)

    if not profile_path.exists():
        print(f"Error: File not found: {profile_path}")
        return 1

    try:
        with open(profile_path) as f:
            profile = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON: {e}")
        return 1

    errors = []
    warnings = []

    print(f"\nValidating: {profile_path}")
    print("-" * 40)

    # Check profile structure
    if "id" not in profile:
        errors.append("Missing required field: id")
    if "name" not in profile:
        errors.append("Missing required field: name")
    if "layers" not in profile:
        errors.append("Missing required field: layers")

    # Check layers
    layers = profile.get("layers", [])
    if not layers:
        warnings.append("Profile has no layers defined")

    layer_ids = set()
    for i, layer in enumerate(layers):
        layer_id = layer.get("id", f"layer_{i}")
        layer_name = layer.get("name", layer_id)

        if layer_id in layer_ids:
            errors.append(f"Duplicate layer ID: {layer_id}")
        layer_ids.add(layer_id)

        # Check hold modifier
        hold_mod = layer.get("hold_modifier_input_code")
        if hold_mod:
            valid, msg = validate_key(hold_mod)
            if not valid:
                errors.append(f"Layer '{layer_name}' hold modifier: {msg}")

        # Check bindings
        for j, binding in enumerate(layer.get("bindings", [])):
            binding_ctx = f"Layer '{layer_name}' binding {j + 1}"

            # Check input code
            input_code = binding.get("input_code")
            if not input_code:
                errors.append(f"{binding_ctx}: Missing input_code")
            else:
                valid, msg = validate_key(input_code)
                if not valid:
                    errors.append(f"{binding_ctx} input_code: {msg}")

            # Check output keys
            output_keys = binding.get("output_keys", [])
            for key in output_keys:
                valid, msg = validate_key(key)
                if not valid:
                    errors.append(f"{binding_ctx} output_key '{key}': {msg}")

            # Check action type
            action_type = binding.get("action_type")
            valid_types = ["key", "chord", "macro", "passthrough", "disabled"]
            if action_type and action_type not in valid_types:
                warnings.append(f"{binding_ctx}: Unknown action_type '{action_type}'")

            # Check macro reference
            macro_id = binding.get("macro_id")
            if macro_id and action_type == "macro":
                macros = profile.get("macros", [])
                macro_ids = [m.get("id") for m in macros]
                if macro_id not in macro_ids:
                    errors.append(f"{binding_ctx}: Referenced macro '{macro_id}' not found")

    # Check macros
    for i, macro in enumerate(profile.get("macros", [])):
        macro_id = macro.get("id", f"macro_{i}")
        macro_ctx = f"Macro '{macro_id}'"

        if not macro.get("id"):
            errors.append(f"Macro {i + 1}: Missing id")

        for j, step in enumerate(macro.get("steps", [])):
            step_key = step.get("key")
            if step_key:
                valid, msg = validate_key(step_key)
                if not valid:
                    errors.append(f"{macro_ctx} step {j + 1}: {msg}")

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

    # Summary
    print(f"\n{len(errors)} errors, {len(warnings)} warnings")

    return 1 if errors else 0


def main():
    parser = argparse.ArgumentParser(
        description="Keycode mapping checker and profile validator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --list                     List all available schema keys
  %(prog)s --list --categories        List available categories
  %(prog)s --list --category Mouse    List keys in Mouse category
  %(prog)s --list --evdev             List all evdev key names
  %(prog)s --info CTRL                Get info about CTRL key
  %(prog)s --check CTRL+SHIFT+A       Check if a chord is valid
  %(prog)s --validate profile.json    Validate a profile file
""",
    )

    # List command
    parser.add_argument(
        "--list",
        "-l",
        action="store_true",
        help="List available keys",
    )
    parser.add_argument(
        "--category",
        "-c",
        help="Filter list by category (Mouse, Modifiers, Function, etc.)",
    )
    parser.add_argument(
        "--categories",
        action="store_true",
        help="List available categories",
    )
    parser.add_argument(
        "--evdev",
        action="store_true",
        help="List evdev names instead of schema names",
    )

    # Info command
    parser.add_argument(
        "--info",
        "-i",
        metavar="KEY",
        help="Get detailed info about a key",
    )

    # Check command
    parser.add_argument(
        "--check",
        metavar="CHORD",
        help="Check if a key or chord (KEY+KEY+...) is valid",
    )

    # Validate command
    parser.add_argument(
        "--validate",
        "-v",
        metavar="PROFILE",
        help="Validate a profile JSON file",
    )

    args = parser.parse_args()

    # Route to appropriate command
    if args.list or args.categories:
        return cmd_list(args)
    elif args.info:
        args.key = args.info
        return cmd_info(args)
    elif args.check:
        args.chord = args.check
        return cmd_check(args)
    elif args.validate:
        args.profile = args.validate
        return cmd_validate(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
