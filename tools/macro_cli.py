"""CLI tool for recording and playing macros.

Usage:
    razer-macro record                     # Record a new macro
    razer-macro play <macro.json>          # Play a macro file
    razer-macro list                       # List macros in active profile
    razer-macro show <macro_id>            # Show macro details
    razer-macro add <macro.json>           # Add macro to active profile
    razer-macro remove <macro_id>          # Remove macro from profile
    razer-macro test                       # Interactive macro testing
"""

import argparse
import json
import select
import sys
import time
from pathlib import Path

from evdev import InputDevice, ecodes, list_devices

from crates.keycode_map import schema_to_evdev_code, validate_key
from crates.profile_schema import (
    MacroAction,
    MacroStep,
    MacroStepType,
    ProfileLoader,
)
from services.macro_engine import MacroPlayer, MacroRecorder


def find_keyboard_device() -> str | None:
    """Find a keyboard device to record from."""
    for path in list_devices():
        try:
            dev = InputDevice(path)
            caps = dev.capabilities()

            # Check if it has key events and looks like a keyboard
            if ecodes.EV_KEY in caps:
                keys = caps[ecodes.EV_KEY]
                # Keyboards have letter keys
                if ecodes.KEY_A in keys and ecodes.KEY_Z in keys:
                    return path
        except OSError:
            continue
    return None


def cmd_record(args) -> int:
    """Record a new macro."""
    # Find device to record from
    device_path = args.device
    if not device_path:
        device_path = find_keyboard_device()
        if not device_path:
            print("Error: No keyboard device found.")
            print("Specify a device with --device /dev/input/eventX")
            return 1

    try:
        dev = InputDevice(device_path)
        print(f"Recording from: {dev.name}")
    except Exception as e:
        print(f"Error: Could not open device: {e}")
        return 1

    print(f"\nPress keys to record. Press {args.stop_key} to finish.")
    print("Recording will start in 2 seconds...")
    time.sleep(2)
    print("Recording started!\n")

    # Set up recorder
    recorder = MacroRecorder(
        min_delay_ms=args.min_delay,
        max_delay_ms=args.max_delay,
        record_delays=not args.no_delays,
        merge_press_release=not args.no_merge,
    )

    def on_event(event):
        action = "↓" if event.value == 1 else "↑"
        print(f"  {action} {event.key_name}")

    recorder.set_event_callback(on_event)

    # Record
    stop_key_code = schema_to_evdev_code(args.stop_key.upper())

    try:
        dev.grab()
        recorder.start()

        start_time = time.time()

        while recorder.is_recording():
            # Check timeout
            if time.time() - start_time > args.timeout:
                print("\nTimeout reached.")
                break

            # Wait for events
            r, _, _ = select.select([dev.fd], [], [], 0.1)
            if not r:
                continue

            for event in dev.read():
                if event.type != ecodes.EV_KEY:
                    continue

                # Check for stop key
                if event.code == stop_key_code and event.value == 1:
                    print(f"\n{args.stop_key} pressed - stopping recording.")
                    macro = recorder.stop()
                    break

                recorder.record_event(event)
            else:
                continue
            break

    finally:
        try:
            dev.ungrab()
        except (OSError, AttributeError):
            pass

    if recorder.is_recording():
        macro = recorder.stop()

    # Show results
    print(f"\nRecorded {len(macro.steps)} steps:")
    for i, step in enumerate(macro.steps):
        print(f"  {i + 1}. {_format_step(step)}")

    # Save macro
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = Path(f"macro_{int(time.time())}.json")

    # Set macro metadata
    macro.id = args.name.lower().replace(" ", "_") if args.name else output_path.stem
    macro.name = args.name or "Recorded Macro"

    data = macro.model_dump(mode="json")
    output_path.write_text(json.dumps(data, indent=2))
    print(f"\nSaved to: {output_path}")

    return 0


def cmd_play(args) -> int:
    """Play a macro from file."""
    # Load macro
    path = Path(args.file)
    if not path.exists():
        print(f"Error: File not found: {path}")
        return 1

    try:
        data = json.loads(path.read_text())
        macro = MacroAction.model_validate(data)
    except Exception as e:
        print(f"Error: Invalid macro file: {e}")
        return 1

    print(f"Playing macro: {macro.name}")
    print(f"  Steps: {len(macro.steps)}")
    print(f"  Repeat: {macro.repeat_count}x")
    if args.speed != 1.0:
        print(f"  Speed: {args.speed}x")

    if not args.yes:
        print("\nPress Enter to play, Ctrl+C to cancel...")
        try:
            input()
        except KeyboardInterrupt:
            print("\nCancelled.")
            return 0

    # Play
    player = MacroPlayer()

    def on_step(step, index):
        if args.verbose:
            print(f"  {index + 1}. {_format_step(step)}")

    player.set_step_callback(on_step)

    try:
        success = player.play(macro, args.speed)
        if success:
            print("Done.")
        else:
            print("Cancelled.")
        return 0 if success else 1
    except KeyboardInterrupt:
        player.cancel()
        print("\nCancelled.")
        return 1
    finally:
        player.close()


def cmd_list(args) -> int:
    """List macros in the active profile."""
    loader = ProfileLoader(args.config_dir)
    profile = loader.load_active_profile()

    if not profile:
        print("No active profile.")
        return 1

    print(f"\nMacros in profile: {profile.name}")
    print("-" * 50)

    if not profile.macros:
        print("  (no macros defined)")
        return 0

    for macro in profile.macros:
        print(f"\n  {macro.id}")
        print(f"    Name: {macro.name}")
        print(f"    Steps: {len(macro.steps)}")
        print(f"    Repeat: {macro.repeat_count}x")

    print(f"\n{len(profile.macros)} macro(s) found.")
    return 0


def cmd_show(args) -> int:
    """Show details of a macro."""
    loader = ProfileLoader(args.config_dir)
    profile = loader.load_active_profile()

    if not profile:
        print("No active profile.")
        return 1

    # Find macro
    macro = None
    for m in profile.macros:
        if m.id == args.macro_id:
            macro = m
            break

    if not macro:
        print(f"Error: Macro '{args.macro_id}' not found in profile.")
        return 1

    print(f"\nMacro: {macro.name}")
    print(f"ID: {macro.id}")
    print(f"Repeat: {macro.repeat_count}x")
    if macro.repeat_delay_ms:
        print(f"Repeat Delay: {macro.repeat_delay_ms}ms")

    print(f"\nSteps ({len(macro.steps)}):")
    for i, step in enumerate(macro.steps):
        print(f"  {i + 1}. {_format_step(step)}")

    return 0


def cmd_add(args) -> int:
    """Add a macro to the active profile."""
    loader = ProfileLoader(args.config_dir)
    profile = loader.load_active_profile()

    if not profile:
        print("No active profile.")
        return 1

    # Load macro file
    path = Path(args.file)
    if not path.exists():
        print(f"Error: File not found: {path}")
        return 1

    try:
        data = json.loads(path.read_text())
        macro = MacroAction.model_validate(data)
    except Exception as e:
        print(f"Error: Invalid macro file: {e}")
        return 1

    # Check for duplicate
    for existing in profile.macros:
        if existing.id == macro.id:
            if not args.force:
                print(f"Error: Macro '{macro.id}' already exists. Use --force to replace.")
                return 1
            profile.macros.remove(existing)
            break

    profile.macros.append(macro)

    if loader.save_profile(profile):
        print(f"Added macro '{macro.id}' to profile '{profile.name}'")
        return 0
    else:
        print("Error: Failed to save profile.")
        return 1


def cmd_remove(args) -> int:
    """Remove a macro from the active profile."""
    loader = ProfileLoader(args.config_dir)
    profile = loader.load_active_profile()

    if not profile:
        print("No active profile.")
        return 1

    # Find and remove macro
    found = False
    for macro in profile.macros:
        if macro.id == args.macro_id:
            profile.macros.remove(macro)
            found = True
            break

    if not found:
        print(f"Error: Macro '{args.macro_id}' not found.")
        return 1

    if loader.save_profile(profile):
        print(f"Removed macro '{args.macro_id}' from profile '{profile.name}'")
        return 0
    else:
        print("Error: Failed to save profile.")
        return 1


def cmd_test(args) -> int:
    """Interactive macro testing - type and play back."""
    print("Interactive Macro Test")
    print("=" * 50)
    print("Commands:")
    print("  type <text>     - Play text as keystrokes")
    print("  key <key>       - Press a single key")
    print("  chord <k1+k2>   - Press keys simultaneously")
    print("  delay <ms>      - Wait for milliseconds")
    print("  quit            - Exit")
    print()

    player = MacroPlayer()

    try:
        while True:
            try:
                line = input("macro> ").strip()
            except EOFError:
                break

            if not line:
                continue

            parts = line.split(maxsplit=1)
            cmd = parts[0].lower()
            arg = parts[1] if len(parts) > 1 else ""

            if cmd == "quit" or cmd == "exit":
                break

            elif cmd == "type":
                if not arg:
                    print("Usage: type <text>")
                    continue
                steps = [MacroStep(type=MacroStepType.TEXT, text=arg)]
                print(f"Typing: {arg}")
                player.play_steps(steps)

            elif cmd == "key":
                if not arg:
                    print("Usage: key <keyname>")
                    continue
                valid, msg = validate_key(arg.upper())
                if not valid:
                    print(f"Invalid key: {msg}")
                    continue
                steps = [MacroStep(type=MacroStepType.KEY_PRESS, key=arg.upper())]
                print(f"Pressing: {arg.upper()}")
                player.play_steps(steps)

            elif cmd == "chord":
                if not arg:
                    print("Usage: chord <key1+key2+...>")
                    continue
                keys = [k.strip().upper() for k in arg.split("+")]
                for k in keys:
                    valid, msg = validate_key(k)
                    if not valid:
                        print(f"Invalid key '{k}': {msg}")
                        break
                else:
                    steps = []
                    # Press all keys
                    for k in keys:
                        steps.append(MacroStep(type=MacroStepType.KEY_DOWN, key=k))
                    # Release in reverse order
                    for k in reversed(keys):
                        steps.append(MacroStep(type=MacroStepType.KEY_UP, key=k))
                    print(f"Chord: {' + '.join(keys)}")
                    player.play_steps(steps)

            elif cmd == "delay":
                try:
                    ms = int(arg)
                    steps = [MacroStep(type=MacroStepType.DELAY, delay_ms=ms)]
                    print(f"Waiting {ms}ms...")
                    player.play_steps(steps)
                except ValueError:
                    print("Usage: delay <milliseconds>")

            else:
                print(f"Unknown command: {cmd}")

    finally:
        player.close()

    print("Goodbye!")
    return 0


def cmd_create(args) -> int:
    """Create a macro from command line arguments."""
    steps = []

    for step_str in args.steps:
        step = _parse_step(step_str)
        if step is None:
            print(f"Error: Invalid step format: {step_str}")
            print("Formats: key:A, down:CTRL, up:CTRL, delay:100, text:hello")
            return 1
        steps.append(step)

    if not steps:
        print("Error: No steps provided.")
        return 1

    macro = MacroAction(
        id=args.name.lower().replace(" ", "_"),
        name=args.name,
        steps=steps,
        repeat_count=args.repeat,
        repeat_delay_ms=args.repeat_delay,
    )

    # Save
    output_path = Path(args.output) if args.output else Path(f"{macro.id}.json")
    data = macro.model_dump(mode="json")
    output_path.write_text(json.dumps(data, indent=2))

    print(f"Created macro: {macro.name}")
    print(f"  Steps: {len(steps)}")
    print(f"  Saved to: {output_path}")
    return 0


def _parse_step(step_str: str) -> MacroStep | None:
    """Parse a step from string format."""
    if ":" not in step_str:
        return None

    type_str, value = step_str.split(":", 1)
    type_str = type_str.lower()

    if type_str == "key" or type_str == "press":
        return MacroStep(type=MacroStepType.KEY_PRESS, key=value.upper())
    elif type_str == "down":
        return MacroStep(type=MacroStepType.KEY_DOWN, key=value.upper())
    elif type_str == "up":
        return MacroStep(type=MacroStepType.KEY_UP, key=value.upper())
    elif type_str == "delay" or type_str == "wait":
        try:
            ms = int(value)
            return MacroStep(type=MacroStepType.DELAY, delay_ms=ms)
        except ValueError:
            return None
    elif type_str == "text" or type_str == "type":
        return MacroStep(type=MacroStepType.TEXT, text=value)

    return None


def _format_step(step: MacroStep) -> str:
    """Format a step for display."""
    if step.type == MacroStepType.KEY_DOWN:
        return f"↓ {step.key}"
    elif step.type == MacroStepType.KEY_UP:
        return f"↑ {step.key}"
    elif step.type == MacroStepType.KEY_PRESS:
        return f"⇅ {step.key}"
    elif step.type == MacroStepType.DELAY:
        return f"⏱ {step.delay_ms}ms"
    elif step.type == MacroStepType.TEXT:
        text_val = step.text or ""
        text = text_val[:30] + "..." if len(text_val) > 30 else text_val
        return f'📝 "{text}"'
    return str(step)


def main():
    parser = argparse.ArgumentParser(
        prog="razer-macro",
        description="Record and play macros",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s record                          Record a macro interactively
  %(prog)s record -o my_macro.json         Record and save to file
  %(prog)s play my_macro.json              Play a macro
  %(prog)s play my_macro.json --speed 2    Play at 2x speed
  %(prog)s list                            List macros in profile
  %(prog)s show copy_paste                 Show macro details
  %(prog)s add my_macro.json               Add macro to profile
  %(prog)s test                            Interactive testing mode
  %(prog)s create "My Macro" key:CTRL down:C up:C

Step formats for create:
  key:A          Press and release A
  down:CTRL      Press down CTRL
  up:CTRL        Release CTRL
  delay:100      Wait 100ms
  text:hello     Type "hello"
""",
    )

    parser.add_argument(
        "--config-dir",
        "-c",
        type=Path,
        help="Config directory",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command")

    # record
    sub_record = subparsers.add_parser("record", help="Record a macro")
    sub_record.add_argument("-o", "--output", help="Output file path")
    sub_record.add_argument("-n", "--name", help="Macro name")
    sub_record.add_argument("-d", "--device", help="Input device path")
    sub_record.add_argument("--stop-key", default="ESC", help="Key to stop recording")
    sub_record.add_argument("--timeout", type=int, default=60, help="Recording timeout (seconds)")
    sub_record.add_argument("--min-delay", type=int, default=10, help="Min delay to record (ms)")
    sub_record.add_argument("--max-delay", type=int, default=5000, help="Max delay to record (ms)")
    sub_record.add_argument("--no-delays", action="store_true", help="Don't record delays")
    sub_record.add_argument("--no-merge", action="store_true", help="Don't merge press+release")
    sub_record.set_defaults(func=cmd_record)

    # play
    sub_play = subparsers.add_parser("play", help="Play a macro")
    sub_play.add_argument("file", help="Macro JSON file")
    sub_play.add_argument("-s", "--speed", type=float, default=1.0, help="Speed multiplier")
    sub_play.add_argument("-y", "--yes", action="store_true", help="Skip confirmation")
    sub_play.add_argument("-v", "--verbose", action="store_true", help="Show steps as played")
    sub_play.set_defaults(func=cmd_play)

    # list
    sub_list = subparsers.add_parser("list", help="List macros in profile")
    sub_list.set_defaults(func=cmd_list)

    # show
    sub_show = subparsers.add_parser("show", help="Show macro details")
    sub_show.add_argument("macro_id", help="Macro ID")
    sub_show.set_defaults(func=cmd_show)

    # add
    sub_add = subparsers.add_parser("add", help="Add macro to profile")
    sub_add.add_argument("file", help="Macro JSON file")
    sub_add.add_argument("-f", "--force", action="store_true", help="Replace if exists")
    sub_add.set_defaults(func=cmd_add)

    # remove
    sub_remove = subparsers.add_parser("remove", help="Remove macro from profile")
    sub_remove.add_argument("macro_id", help="Macro ID")
    sub_remove.set_defaults(func=cmd_remove)

    # test
    sub_test = subparsers.add_parser("test", help="Interactive macro testing")
    sub_test.set_defaults(func=cmd_test)

    # create
    sub_create = subparsers.add_parser("create", help="Create macro from steps")
    sub_create.add_argument("name", help="Macro name")
    sub_create.add_argument("steps", nargs="+", help="Steps (key:A, delay:100, text:hello)")
    sub_create.add_argument("-o", "--output", help="Output file")
    sub_create.add_argument("-r", "--repeat", type=int, default=1, help="Repeat count")
    sub_create.add_argument(
        "--repeat-delay", type=int, default=0, help="Delay between repeats (ms)"
    )
    sub_create.set_defaults(func=cmd_create)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
